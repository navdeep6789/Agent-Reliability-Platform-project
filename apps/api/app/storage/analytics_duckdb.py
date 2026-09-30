import os
import json
import logging
import duckdb
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..config import settings

logger = logging.getLogger("arp.analytics")

class DuckDBAnalytics:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DUCKDB_PATH
        try:
            self.con = duckdb.connect(self.db_path)
            self._init_tables()
        except duckdb.IOException:
            try:
                self.con = duckdb.connect(self.db_path, read_only=True)
            except Exception:
                self.con = duckdb.connect(":memory:")
                self._init_tables()

    def _init_tables(self):
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id VARCHAR PRIMARY KEY,
                trace_id VARCHAR,
                project_id VARCHAR,
                environment VARCHAR,
                agent_name VARCHAR,
                agent_version VARCHAR,
                prompt_version VARCHAR,
                status VARCHAR,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_ms DOUBLE,
                input_tokens BIGINT,
                output_tokens BIGINT,
                total_tokens BIGINT,
                cost_usd DOUBLE,
                error_count INTEGER,
                retry_count INTEGER,
                created_at TIMESTAMP
            );
        """)

        self.con.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id VARCHAR PRIMARY KEY,
                trace_id VARCHAR,
                run_id VARCHAR,
                parent_span_id VARCHAR,
                name VARCHAR,
                span_type VARCHAR,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_ms DOUBLE,
                status VARCHAR,
                status_message VARCHAR,
                model_name VARCHAR,
                provider VARCHAR,
                tool_name VARCHAR,
                input_tokens BIGINT,
                output_tokens BIGINT,
                cost_usd DOUBLE
            );
        """)

    def insert_run(self, run: Dict[str, Any]):
        try:
            self.con.execute("""
                INSERT OR REPLACE INTO runs VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, [
                run.get("run_id"),
                run.get("trace_id"),
                run.get("project_id", "proj_default_production"),
                run.get("environment", "production"),
                run.get("agent_name"),
                run.get("agent_version", "1.0.0"),
                run.get("prompt_version"),
                run.get("status", "SUCCESS"),
                run.get("start_time"),
                run.get("end_time"),
                float(run.get("duration_ms") or 0.0),
                int(run.get("input_tokens") or 0),
                int(run.get("output_tokens") or 0),
                int(run.get("total_tokens") or 0),
                float(run.get("cost_usd") or 0.0),
                int(run.get("error_count") or 0),
                int(run.get("retry_count") or 0),
                datetime.utcnow()
            ])
        except Exception as e:
            logger.error(f"Error inserting run into DuckDB: {e}")

    def insert_span(self, span: Dict[str, Any]):
        try:
            attrs = span.get("attributes", {})
            if isinstance(attrs, str):
                try:
                    attrs = json.loads(attrs)
                except Exception:
                    attrs = {}

            model = attrs.get("gen_ai.request.model") or attrs.get("model")
            provider = attrs.get("gen_ai.system") or attrs.get("provider")
            tool_name = attrs.get("arp.tool.name") or attrs.get("tool.name")
            in_tokens = int(attrs.get("gen_ai.usage.input_tokens") or 0)
            out_tokens = int(attrs.get("gen_ai.usage.output_tokens") or 0)
            cost = float(attrs.get("arp.cost.usd") or 0.0)

            self.con.execute("""
                INSERT OR REPLACE INTO spans VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, [
                span.get("span_id"),
                span.get("trace_id"),
                span.get("run_id"),
                span.get("parent_span_id"),
                span.get("name"),
                span.get("span_type", "custom"),
                span.get("start_time"),
                span.get("end_time"),
                float(span.get("duration_ms") or 0.0),
                span.get("status", "ok"),
                span.get("status_message"),
                model,
                provider,
                tool_name,
                in_tokens,
                out_tokens,
                cost
            ])
        except Exception as e:
            logger.error(f"Error inserting span into DuckDB: {e}")

    def get_agent_health(self, project_id: str, environment: str) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                agent_name,
                COUNT(*) as total_runs,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN status != 'SUCCESS' THEN 1 ELSE 0 END) as error_count,
                ROUND(AVG(duration_ms), 1) as avg_duration_ms,
                ROUND(QUANTILE_CONT(duration_ms, 0.95), 1) as p95_duration_ms,
                ROUND(AVG(cost_usd), 4) as avg_cost_usd,
                SUM(total_tokens) as total_tokens,
                SUM(retry_count) as total_retries
            FROM runs
            WHERE project_id = ? AND environment = ?
            GROUP BY agent_name
            ORDER BY total_runs DESC
        """
        results = self.con.execute(query, [project_id, environment]).fetchall()
        cols = ["agent_name", "total_runs", "success_count", "error_count", "avg_duration_ms", "p95_duration_ms", "avg_cost_usd", "total_tokens", "total_retries"]
        
        health_list = []
        for row in results:
            item = dict(zip(cols, row))
            total = item["total_runs"] or 1
            item["error_rate"] = round((item["error_count"] / total) * 100.0, 2)
            item["success_rate"] = round((item["success_count"] / total) * 100.0, 2)
            health_list.append(item)
        return health_list

    def get_timeseries_metrics(self, project_id: str, environment: str) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                strftime(start_time, '%Y-%m-%d %H:00') as time_bucket,
                COUNT(*) as runs_count,
                SUM(CASE WHEN status != 'SUCCESS' THEN 1 ELSE 0 END) as error_count,
                ROUND(QUANTILE_CONT(duration_ms, 0.95), 1) as p95_latency,
                ROUND(SUM(cost_usd), 4) as total_cost,
                SUM(total_tokens) as total_tokens
            FROM runs
            WHERE project_id = ? AND environment = ?
            GROUP BY time_bucket
            ORDER BY time_bucket ASC
            LIMIT 48
        """
        results = self.con.execute(query, [project_id, environment]).fetchall()
        cols = ["time_bucket", "runs_count", "error_count", "p95_latency", "total_cost", "total_tokens"]
        return [dict(zip(cols, row)) for row in results]

    def get_model_comparisons(self, project_id: str, environment: str) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                s.model_name,
                s.provider,
                COUNT(*) as call_count,
                ROUND(AVG(s.duration_ms), 1) as avg_latency_ms,
                ROUND(QUANTILE_CONT(s.duration_ms, 0.95), 1) as p95_latency_ms,
                ROUND(AVG(s.input_tokens), 0) as avg_input_tokens,
                ROUND(AVG(s.output_tokens), 0) as avg_output_tokens,
                ROUND(SUM(s.cost_usd), 4) as total_cost_usd
            FROM spans s
            JOIN runs r ON s.run_id = r.run_id
            WHERE r.project_id = ? AND r.environment = ? AND s.model_name IS NOT NULL
            GROUP BY s.model_name, s.provider
            ORDER BY call_count DESC
        """
        results = self.con.execute(query, [project_id, environment]).fetchall()
        cols = ["model_name", "provider", "call_count", "avg_latency_ms", "p95_latency_ms", "avg_input_tokens", "avg_output_tokens", "total_cost_usd"]
        return [dict(zip(cols, row)) for row in results]

# Global analytics instance
analytics = DuckDBAnalytics()
