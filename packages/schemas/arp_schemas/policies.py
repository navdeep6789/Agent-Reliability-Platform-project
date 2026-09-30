from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class PolicyRuleType(str, Enum):
    MAX_RUN_LATENCY = "MAX_RUN_LATENCY"
    MAX_RUN_COST = "MAX_RUN_COST"
    MAX_TOOL_RETRIES = "MAX_TOOL_RETRIES"
    MAX_TOOL_LATENCY = "MAX_TOOL_LATENCY"
    MIN_EVAL_SCORE = "MIN_EVAL_SCORE"
    MAX_CONTEXT_TOKENS = "MAX_CONTEXT_TOKENS"

class PolicySeverity(str, Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class Policy(BaseModel):
    id: str
    project_id: str = "proj_default_production"
    name: str
    rule_type: PolicyRuleType
    threshold: float
    unit: str # "seconds", "usd", "retries", "score", "tokens"
    severity: PolicySeverity = PolicySeverity.CRITICAL
    enabled: bool = True
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PolicyViolation(BaseModel):
    id: str
    run_id: str
    trace_id: str
    policy_id: str
    rule_type: PolicyRuleType
    severity: PolicySeverity
    threshold_value: float
    observed_value: float
    unit: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
