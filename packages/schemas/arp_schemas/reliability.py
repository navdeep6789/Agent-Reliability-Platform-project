from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class FindingType(str, Enum):
    TOOL_LATENCY = "TOOL_LATENCY"
    RETRY_LOOP = "RETRY_LOOP"
    RETRY_STORM = "RETRY_STORM"
    FAILED_TOOL = "FAILED_TOOL"
    CONTEXT_GROWTH = "CONTEXT_GROWTH"
    EXPENSIVE_CALL = "EXPENSIVE_CALL"
    REPEATED_SEQUENCE = "REPEATED_SEQUENCE"
    MISSING_TELEMETRY = "MISSING_TELEMETRY"
    TOOL_VALIDATION_ERROR = "TOOL_VALIDATION_ERROR"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"

class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReliabilityFinding(BaseModel):
    id: str
    run_id: str
    trace_id: str
    finding_type: FindingType
    severity: Severity
    title: str
    description: str
    target_entity: Optional[str] = None # e.g. "crm.lookup_customer" or "llm.gpt-4"
    observed_metric: Optional[str] = None # e.g. "1.91s" or "+1,225%"
    trace_contribution_percent: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    suggested_actions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RetryStep(BaseModel):
    attempt: int
    span_id: str
    duration_ms: float
    status: str
    error_message: Optional[str] = None

class RetryAnalysis(BaseModel):
    tool_name: str
    total_retries: int
    total_retry_latency_ms: float
    final_status: str # SUCCESS, FAILED
    retry_reasons: List[str] = Field(default_factory=list)
    steps: List[RetryStep] = Field(default_factory=list)

class LoopAnalysis(BaseModel):
    pattern: List[str] # e.g. ["search", "search", "search"]
    repetitions: int
    duration_ms: float
    severity: Severity

class ContextGrowthStep(BaseModel):
    call_index: int
    span_id: str
    model: str
    input_tokens: int
    output_tokens: int
    delta_percent: float

class ContextGrowthAnalysis(BaseModel):
    initial_tokens: int
    peak_tokens: int
    growth_multiplier: float # e.g. 13.3x
    growth_percent: float # e.g. +1225%
    steps: List[ContextGrowthStep] = Field(default_factory=list)
    is_abnormal: bool = False

class ReliabilityReport(BaseModel):
    run_id: str
    trace_id: str
    agent_name: str
    total_duration_ms: float
    total_cost_usd: Optional[float]
    total_tokens: int
    error_count: int
    retry_count: int
    findings: List[ReliabilityFinding] = Field(default_factory=list)
    retries: List[RetryAnalysis] = Field(default_factory=list)
    context_growth: Optional[ContextGrowthAnalysis] = None
    loops: List[LoopAnalysis] = Field(default_factory=list)
    policy_violations: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_investigations: List[str] = Field(default_factory=list)
