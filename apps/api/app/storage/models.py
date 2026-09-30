import json
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Index
)
from .database import Base

class ProjectModel(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), index=True)
    environment = Column(String, default="production")
    name = Column(String, nullable=False)
    hashed_key = Column(String, nullable=False, unique=True)
    prefix = Column(String, nullable=False) # e.g. "arp_live_..."
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentModel(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentVersionModel(Base):
    __tablename__ = "agent_versions"
    id = Column(String, primary_key=True)
    agent_name = Column(String, index=True)
    version = Column(String, nullable=False)
    prompt_version = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RunModel(Base):
    __tablename__ = "runs"
    run_id = Column(String, primary_key=True)
    trace_id = Column(String, index=True)
    project_id = Column(String, index=True)
    environment = Column(String, default="production", index=True)
    agent_name = Column(String, index=True)
    agent_version = Column(String, default="1.0.0")
    prompt_version = Column(String, nullable=True)
    status = Column(String, default="SUCCESS", index=True) # SUCCESS, FAILED, RUNNING, VIOLATION
    start_time = Column(DateTime, default=datetime.utcnow, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, default=0.0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    input_payload = Column(Text, nullable=True)
    output_payload = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_run_agent_time", "agent_name", "start_time"),
        Index("idx_run_proj_env", "project_id", "environment"),
    )

class SpanModel(Base):
    __tablename__ = "spans"
    span_id = Column(String, primary_key=True)
    trace_id = Column(String, index=True)
    run_id = Column(String, index=True)
    parent_span_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False)
    span_type = Column(String, default="custom", index=True) # agent, llm, tool, retrieval, embedding, http, database, custom
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Float, default=0.0)
    status = Column(String, default="ok", index=True) # ok, error, unset
    status_message = Column(Text, nullable=True)
    attributes_json = Column(Text, default="{}")
    events_json = Column(Text, default="[]")

    __table_args__ = (
        Index("idx_span_trace_run", "trace_id", "run_id"),
        Index("idx_span_type_time", "span_type", "start_time"),
    )

class ReliabilityFindingModel(Base):
    __tablename__ = "reliability_findings"
    id = Column(String, primary_key=True)
    run_id = Column(String, index=True)
    trace_id = Column(String, index=True)
    project_id = Column(String, index=True)
    finding_type = Column(String, index=True) # TOOL_LATENCY, RETRY_LOOP, etc.
    severity = Column(String, index=True) # INFO, LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    target_entity = Column(String, nullable=True)
    observed_metric = Column(String, nullable=True)
    contribution_percent = Column(Float, nullable=True)
    details_json = Column(Text, default="{}")
    suggested_actions_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class PolicyModel(Base):
    __tablename__ = "policies"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    name = Column(String, nullable=False)
    rule_type = Column(String, index=True) # MAX_RUN_LATENCY, MAX_RUN_COST, etc.
    threshold = Column(Float, nullable=False)
    unit = Column(String, default="")
    severity = Column(String, default="CRITICAL")
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PolicyViolationModel(Base):
    __tablename__ = "policy_violations"
    id = Column(String, primary_key=True)
    run_id = Column(String, index=True)
    trace_id = Column(String, index=True)
    project_id = Column(String, index=True)
    policy_id = Column(String, ForeignKey("policies.id"))
    rule_type = Column(String, index=True)
    severity = Column(String, default="CRITICAL")
    threshold_value = Column(Float, nullable=False)
    observed_value = Column(Float, nullable=False)
    unit = Column(String, default="")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class EvaluationDatasetModel(Base):
    __tablename__ = "evaluation_datasets"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    agent_target = Column(String, nullable=False, index=True)
    version = Column(String, default="1.0.0")
    total_cases = Column(Integer, default=0)
    cases_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"
    id = Column(String, primary_key=True)
    dataset_id = Column(String, ForeignKey("evaluation_datasets.id"), index=True)
    dataset_name = Column(String, nullable=False)
    project_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    agent_version = Column(String, nullable=False)
    prompt_version = Column(String, nullable=True)
    total_cases = Column(Integer, default=0)
    passed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    pass_rate = Column(Float, default=0.0)
    average_score = Column(Float, default=0.0)
    average_latency_ms = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    failure_breakdown_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class EvaluationCaseResultModel(Base):
    __tablename__ = "evaluation_case_results"
    id = Column(String, primary_key=True)
    eval_run_id = Column(String, ForeignKey("evaluation_runs.id"), index=True)
    case_id = Column(String, nullable=False)
    case_name = Column(String, nullable=False)
    run_id = Column(String, nullable=True)
    passed = Column(Boolean, default=True)
    score = Column(Float, default=1.0)
    evaluator_type = Column(String, nullable=False)
    actual_output = Column(Text, nullable=True)
    expected_output = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    latency_ms = Column(Float, default=0.0)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

class ModelPricingModel(Base):
    __tablename__ = "model_pricing"
    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False, index=True, unique=True)
    input_price_per_million = Column(Float, nullable=False)
    output_price_per_million = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
