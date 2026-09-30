import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import (
    RunModel, SpanModel, ReliabilityFindingModel, PolicyViolationModel,
    EvaluationRunModel, EvaluationCaseResultModel
)
from .analytics_duckdb import analytics
from ..config import settings

logger = logging.getLogger("arp.retention")

class DataRetentionManager:
    def __init__(self, default_retention_days: Optional[int] = None):
        self.default_retention_days = default_retention_days or settings.TRACE_RETENTION_DAYS

    def purge_expired_records(
        self,
        retention_days: Optional[int] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deletes telemetry and analytical data older than retention_days.
        Enforces both Relational Metadata and DuckDB Analytical storage consistency.
        """
        days = retention_days if retention_days is not None else self.default_retention_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        db: Session = SessionLocal()
        purged_stats = {
            "retention_days": days,
            "cutoff_date": cutoff_iso,
            "purged_runs": 0,
            "purged_spans": 0,
            "purged_findings": 0,
            "purged_violations": 0,
            "purged_eval_runs": 0
        }

        try:
            # 1. Query expired runs
            run_query = db.query(RunModel).filter(RunModel.start_time < cutoff_date)
            if project_id:
                run_query = run_query.filter(RunModel.project_id == project_id)
            
            expired_runs = run_query.all()
            expired_run_ids = [r.run_id for r in expired_runs]
            expired_trace_ids = [r.trace_id for r in expired_runs]

            if expired_run_ids:
                # 2. Delete child findings
                f_query = db.query(ReliabilityFindingModel).filter(ReliabilityFindingModel.run_id.in_(expired_run_ids))
                purged_stats["purged_findings"] = f_query.delete(synchronize_session=False)

                # 3. Delete policy violations
                v_query = db.query(PolicyViolationModel).filter(PolicyViolationModel.run_id.in_(expired_run_ids))
                purged_stats["purged_violations"] = v_query.delete(synchronize_session=False)

                # 4. Delete spans
                s_query = db.query(SpanModel).filter(SpanModel.run_id.in_(expired_run_ids))
                purged_stats["purged_spans"] = s_query.delete(synchronize_session=False)

                # 5. Delete runs
                purged_stats["purged_runs"] = len(expired_run_ids)
                db.query(RunModel).filter(RunModel.run_id.in_(expired_run_ids)).delete(synchronize_session=False)

            # 6. Delete expired evaluation runs
            eval_query = db.query(EvaluationRunModel).filter(EvaluationRunModel.created_at < cutoff_date)
            if project_id:
                eval_query = eval_query.filter(EvaluationRunModel.project_id == project_id)
            expired_evals = eval_query.all()
            expired_eval_ids = [e.id for e in expired_evals]
            if expired_eval_ids:
                db.query(EvaluationCaseResultModel).filter(
                    EvaluationCaseResultModel.eval_run_id.in_(expired_eval_ids)
                ).delete(synchronize_session=False)
                purged_stats["purged_eval_runs"] = len(expired_eval_ids)
                db.query(EvaluationRunModel).filter(EvaluationRunModel.id.in_(expired_eval_ids)).delete(synchronize_session=False)

            db.commit()

            # 7. Purge corresponding DuckDB analytical records
            try:
                where_clause = f"start_time < TIMESTAMP '{cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}'"
                if project_id:
                    where_clause += f" AND project_id = '{project_id}'"
                analytics.con.execute(f"DELETE FROM runs WHERE {where_clause}")
                analytics.con.execute(f"DELETE FROM spans WHERE {where_clause}")
            except Exception as d_err:
                logger.warning(f"DuckDB retention cleanup warning: {d_err}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to execute data retention purge: {e}")
            raise
        finally:
            db.close()

        logger.info(f"Data retention purge completed: {purged_stats}")
        return purged_stats

retention_manager = DataRetentionManager()
