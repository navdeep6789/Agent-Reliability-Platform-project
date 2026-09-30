from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class EvaluatorType(str, Enum):
    EXACT_MATCH = "exact_match"
    JSON_SCHEMA = "json_schema"
    TOOL_SELECTION = "tool_selection"
    CITATION_PRESENCE = "citation_presence"
    RESPONSE_LENGTH = "response_length"
    REGEX_PATTERN = "regex_pattern"
    LLM_JUDGE = "llm_judge"

class EvaluationCase(BaseModel):
    id: str
    dataset_id: str
    name: str
    input: Dict[str, Any]
    expected_output: Optional[str] = None
    expected_tools: Optional[List[str]] = None
    required_citations: Optional[List[str]] = None
    expected_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EvaluationDataset(BaseModel):
    id: str
    project_id: str = "proj_default_production"
    name: str
    description: Optional[str] = None
    agent_target: str
    version: str = "1.0.0"
    total_cases: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CaseResult(BaseModel):
    case_id: str
    case_name: str
    run_id: Optional[str] = None
    passed: bool
    score: float # 0.0 to 1.0
    evaluator_type: EvaluatorType
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    failure_reason: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: Optional[float] = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)

class EvaluationRun(BaseModel):
    id: str
    dataset_id: str
    dataset_name: str
    agent_name: str
    agent_version: str
    prompt_version: Optional[str] = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float # 0.0 to 100.0%
    average_score: float # 0.0 to 1.0
    average_latency_ms: float
    total_cost_usd: float
    failure_breakdown: Dict[str, int] = Field(default_factory=dict)
    cases: List[CaseResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RegressionReport(BaseModel):
    baseline_version: str
    candidate_version: str
    agent_name: str
    pass_rate_delta: float
    score_delta: float
    latency_delta_ms: float
    cost_delta_usd: float
    has_regression: bool
    reasons: List[str] = Field(default_factory=list)
    baseline_run_id: str
    candidate_run_id: str
