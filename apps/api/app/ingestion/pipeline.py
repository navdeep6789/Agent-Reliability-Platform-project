import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..storage.database import SessionLocal
from ..storage.models import (
    RunModel, SpanModel, ReliabilityFindingModel, PolicyViolationModel, AgentModel
)
from ..storage.analytics_duckdb import analytics
from ..cost.pricing import cost_engine
from ..reliability.engine import reliability_engine
from ..policies.engine import policy_engine
from ..observability.platform_metrics import platform_metrics
from .normalizer import SpanNormalizer

import threading
logger = logging.getLogger("arp.pipeline")

class IngestionPipeline:
    def __init__(self):
        self._lock = threading.Lock()

    def process_spans(
        self,
        raw_spans: List[Dict[str, Any]],
        project_id: str = "proj_default_production",
        environment: str = "production"
    ) -> Dict[str, Any]:
        start_ts = time.time()
        normalized_spans = []

        for item in raw_spans:
            try:
                norm = SpanNormalizer.normalize_sdk_span(item)
                normalized_spans.append(norm)
            except Exception as e:
                logger.error(f"Failed to normalize span: {e}")

        if not normalized_spans:
            return {"status": "ok", "spans_processed": 0}

        with self._lock:
            db: Session = SessionLocal()
            try:
                # Group spans by run_id
                runs_map: Dict[str, List[Dict[str, Any]]] = {}
                for s in normalized_spans:
                    r_id = s.get("run_id") or s.get("trace_id")
                    runs_map.setdefault(r_id, []).append(s)

                for run_id, spans in runs_map.items():
                    self._process_run_batch(db, run_id, spans, project_id, environment)

                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Error in ingestion pipeline: {e}")
                raise
            finally:
                db.close()

        elapsed_ms = (time.time() - start_ts) * 1000.0
        platform_metrics.record_ingestion(len(normalized_spans), elapsed_ms)

        return {
            "status": "ok",
            "spans_processed": len(normalized_spans),
            "processing_time_ms": round(elapsed_ms, 2)
        }

    def process_otlp_payload(
        self,
        otlp_dict: Dict[str, Any],
        project_id: str = "proj_default_production",
        environment: str = "production"
    ) -> Dict[str, Any]:
        resource_spans = otlp_dict.get("resourceSpans", [])
        normalized_spans = []

        for r_span in resource_spans:
            res_attrs = {}
            for a in r_span.get("resource", {}).get("attributes", []):
                key = a.get("key")
                val_dict = a.get("value", {})
                for _, v in val_dict.items():
                    res_attrs[key] = v

            scope_spans = r_span.get("scopeSpans", [])
            for s_span in scope_spans:
                for span in s_span.get("spans", []):
                    try:
                        norm = SpanNormalizer.normalize_otlp_span(span, res_attrs)
                        normalized_spans.append(norm)
                    except Exception as e:
                        logger.error(f"Failed to normalize OTLP span: {e}")

        return self.process_spans(normalized_spans, project_id, environment)

    def _process_run_batch(
        self,
        db: Session,
        run_id: str,
        spans: List[Dict[str, Any]],
        project_id: str,
        environment: str
    ):
        # 1. Fetch or create Run
        run = db.query(RunModel).filter(RunModel.run_id == run_id).first()
        trace_id = spans[0].get("trace_id") if spans else run_id

        # Determine agent metadata from spans
        agent_name = "default_agent"
        agent_version = "1.0.0"
        prompt_version = None

        for s in spans:
            attrs = s.get("attributes", {})
            if s.get("name", "").startswith("agent."):
                parts = s.get("name", "").split(".", 1)
                if len(parts) > 1:
                    agent_name = parts[1]
            if attrs.get("arp.agent.name"):
                agent_name = attrs.get("arp.agent.name")
            if attrs.get("arp.agent.version"):
                agent_version = attrs.get("arp.agent.version")
            if attrs.get("arp.prompt.version"):
                prompt_version = attrs.get("arp.prompt.version")

        # Register agent in metadata table if not present
        existing_agent = db.query(AgentModel).filter(AgentModel.name == agent_name).first()
        if not existing_agent:
            try:
                new_agent = AgentModel(
                    id=f"agent_{agent_name}",
                    project_id=project_id,
                    name=agent_name,
                    description=f"Agent '{agent_name}' registered from live telemetry"
                )
                db.add(new_agent)
                db.flush()
            except Exception:
                db.rollback()

        # 2. Enrich spans & compute run aggregations
        batch_input_tokens = 0
        batch_output_tokens = 0
        batch_cost = 0.0
        batch_errors = 0
        batch_retries = 0

        for s in spans:
            attrs = s.get("attributes", {})
            dur = float(s.get("duration_ms", 0.0))

            if s.get("status") == "error":
                batch_errors += 1

            # Tool retries
            retry_cnt = int(attrs.get("arp.tool.retry_count") or 0)
            if retry_cnt > 0:
                batch_retries += retry_cnt

            # LLM span token accounting and cost estimation
            if s.get("span_type") == "llm" or "gen_ai.system" in attrs:
                in_tok = int(attrs.get("gen_ai.usage.input_tokens") or 0)
                out_tok = int(attrs.get("gen_ai.usage.output_tokens") or 0)
                model = attrs.get("gen_ai.request.model") or attrs.get("model")
                provider = attrs.get("gen_ai.system") or attrs.get("provider")

                cost_res = cost_engine.calculate_cost(model, provider, in_tok, out_tok)
                if cost_res.pricing_available:
                    attrs["arp.cost.usd"] = cost_res.total_cost_usd
                    batch_cost += cost_res.total_cost_usd

                batch_input_tokens += in_tok
                batch_output_tokens += out_tok

            # Store Span in DB
            db_span = db.query(SpanModel).filter(SpanModel.span_id == s.get("span_id")).first()
            if not db_span:
                db_span = SpanModel(
                    span_id=s.get("span_id"),
                    trace_id=s.get("trace_id"),
                    run_id=run_id,
                    parent_span_id=s.get("parent_span_id"),
                    name=s.get("name"),
                    span_type=s.get("span_type", "custom"),
                    start_time=s.get("start_time"),
                    end_time=s.get("end_time"),
                    duration_ms=dur,
                    status=s.get("status", "ok"),
                    status_message=s.get("status_message"),
                    attributes_json=json.dumps(attrs),
                    events_json=json.dumps(s.get("events", []))
                )
                db.add(db_span)

            # Sync span to DuckDB analytics
            analytics.insert_span({**s, "attributes": attrs})

        # 3. Update or create Run
        run = db.query(RunModel).filter(RunModel.run_id == run_id).first()
        if not run:
            min_start = min(s.get("start_time") for s in spans)
            max_end = max((s.get("end_time") or s.get("start_time")) for s in spans)
            run_dur = (max_end - min_start).total_seconds() * 1000.0

            run = RunModel(
                run_id=run_id,
                trace_id=trace_id,
                project_id=project_id,
                environment=environment,
                agent_name=agent_name,
                agent_version=agent_version,
                prompt_version=prompt_version,
                status="FAILED" if batch_errors > 0 else "SUCCESS",
                start_time=min_start,
                end_time=max_end,
                duration_ms=round(run_dur, 2),
                input_tokens=batch_input_tokens,
                output_tokens=batch_output_tokens,
                total_tokens=batch_input_tokens + batch_output_tokens,
                cost_usd=round(batch_cost, 6),
                error_count=batch_errors,
                retry_count=batch_retries
            )
            db.add(run)
            db.flush()
        else:
            run.input_tokens += batch_input_tokens
            run.output_tokens += batch_output_tokens
            run.total_tokens = run.input_tokens + run.output_tokens
            run.cost_usd = round((run.cost_usd or 0.0) + batch_cost, 6)
            run.error_count += batch_errors
            run.retry_count += batch_retries
            if batch_errors > 0:
                run.status = "FAILED"
            db.flush()

        # 4. Fetch all spans for run to pass into Reliability and Policy Engines
        all_db_spans = db.query(SpanModel).filter(SpanModel.run_id == run_id).all()
        all_spans_dicts = []
        for s in all_db_spans:
            try:
                a_json = json.loads(s.attributes_json or "{}")
            except Exception:
                a_json = {}
            all_spans_dicts.append({
                "span_id": s.span_id,
                "trace_id": s.trace_id,
                "run_id": s.run_id,
                "parent_span_id": s.parent_span_id,
                "name": s.name,
                "span_type": s.span_type,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "duration_ms": s.duration_ms,
                "status": s.status,
                "status_message": s.status_message,
                "attributes": a_json
            })

        run_dict = {
            "run_id": run.run_id,
            "trace_id": run.trace_id,
            "project_id": run.project_id,
            "environment": run.environment,
            "agent_name": run.agent_name,
            "agent_version": run.agent_version,
            "prompt_version": run.prompt_version,
            "status": run.status,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "duration_ms": run.duration_ms,
            "input_tokens": run.input_tokens,
            "output_tokens": run.output_tokens,
            "total_tokens": run.total_tokens,
            "cost_usd": run.cost_usd,
            "error_count": run.error_count,
            "retry_count": run.retry_count
        }

        # Sync run to DuckDB analytics
        analytics.insert_run(run_dict)

        # 5. Evaluate Policies
        violations = policy_engine.evaluate_run(run_dict, all_spans_dicts)
        for v in violations:
            existing_v = db.query(PolicyViolationModel).filter(
                PolicyViolationModel.run_id == run_id,
                PolicyViolationModel.rule_type == v.rule_type
            ).first()
            if not existing_v:
                db_v = PolicyViolationModel(
                    id=v.id,
                    run_id=run_id,
                    trace_id=trace_id,
                    project_id=project_id,
                    policy_id=v.policy_id,
                    rule_type=v.rule_type,
                    severity=v.severity,
                    threshold_value=v.threshold_value,
                    observed_value=v.observed_value,
                    unit=v.unit,
                    message=v.message
                )
                db.add(db_v)
                if run.status != "FAILED":
                    run.status = "VIOLATION"

        # 6. Run Reliability Analysis
        violations_dicts = [v.model_dump() for v in violations]
        report = reliability_engine.analyze_run(run_dict, all_spans_dicts, violations_dicts)
        for f in report.findings:
            existing_f = db.query(ReliabilityFindingModel).filter(
                ReliabilityFindingModel.run_id == run_id,
                ReliabilityFindingModel.id == f.id
            ).first()
            if not existing_f:
                db_f = ReliabilityFindingModel(
                    id=f.id,
                    run_id=run_id,
                    trace_id=trace_id,
                    project_id=project_id,
                    finding_type=f.finding_type,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    target_entity=f.target_entity,
                    observed_metric=f.observed_metric,
                    contribution_percent=f.trace_contribution_percent,
                    details_json=json.dumps(f.details),
                    suggested_actions_json=json.dumps(f.suggested_actions)
                )
                db.add(db_f)

# Global pipeline instance
pipeline = IngestionPipeline()
