from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .telemetry import SpanType, SpanStatus, ToolErrorType

class SpanEvent(BaseModel):
    name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = Field(default_factory=dict)

class Span(BaseModel):
    span_id: str
    trace_id: str
    run_id: str
    parent_span_id: Optional[str] = None
    name: str
    span_type: SpanType = SpanType.CUSTOM
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.OK
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[SpanEvent] = Field(default_factory=list)

class LLMCallDetails(BaseModel):
    span_id: str
    provider: Optional[str] = "unknown"
    model: Optional[str] = "unknown"
    operation: Optional[str] = "chat"
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Optional[float] = None
    duration_ms: float = 0.0
    finish_reason: Optional[str] = None
    prompt_content: Optional[str] = None
    completion_content: Optional[str] = None
    content_capture_enabled: bool = False

class ToolCallDetails(BaseModel):
    span_id: str
    tool_name: str
    tool_call_id: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    duration_ms: float = 0.0
    status: SpanStatus = SpanStatus.OK
    error_type: Optional[ToolErrorType] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    content_capture_enabled: bool = False

class RunStatus(str):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    VIOLATION = "VIOLATION"

class Run(BaseModel):
    run_id: str
    trace_id: str
    project_id: str = "proj_default_production"
    environment: str = "production"
    agent_name: str
    agent_version: str = "1.0.0"
    prompt_version: Optional[str] = None
    status: str = "SUCCESS"
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    total_spans: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: Optional[float] = 0.0
    error_count: int = 0
    retry_count: int = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    input_payload: Optional[Dict[str, Any]] = None
    output_payload: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TraceWaterfallSpan(BaseModel):
    span_id: str
    parent_span_id: Optional[str] = None
    name: str
    span_type: SpanType
    start_offset_ms: float
    duration_ms: float
    contribution_percent: float = 0.0
    status: SpanStatus
    attributes: Dict[str, Any] = Field(default_factory=dict)
    children: List['TraceWaterfallSpan'] = Field(default_factory=list)

class TraceWaterfall(BaseModel):
    trace_id: str
    run_id: str
    total_duration_ms: float
    root_spans: List[TraceWaterfallSpan] = Field(default_factory=list)
