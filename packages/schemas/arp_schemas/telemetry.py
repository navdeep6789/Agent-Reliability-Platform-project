from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

# OpenTelemetry GenAI Semantic Conventions + ARP Namespaced Attributes
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
GEN_AI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"

# ARP Namespaced Attributes
ARP_SPAN_TYPE = "arp.span.type"
ARP_RUN_ID = "arp.run.id"
ARP_AGENT_NAME = "arp.agent.name"
ARP_AGENT_VERSION = "arp.agent.version"
ARP_ENVIRONMENT = "arp.environment"
ARP_PROJECT_ID = "arp.project.id"

ARP_TOOL_NAME = "arp.tool.name"
ARP_TOOL_CALL_ID = "arp.tool.call_id"
ARP_TOOL_ARGUMENTS = "arp.tool.arguments"
ARP_TOOL_RESULT = "arp.tool.result"
ARP_TOOL_STATUS = "arp.tool.status"
ARP_TOOL_ERROR_TYPE = "arp.tool.error_type"
ARP_TOOL_RETRY_COUNT = "arp.tool.retry_count"

ARP_COST_USD = "arp.cost.usd"
ARP_LATENCY_MS = "arp.latency.ms"
ARP_CONTENT_CAPTURE_ENABLED = "arp.content.capture_enabled"
ARP_REDACTION_APPLIED = "arp.redaction.applied"

class SpanType(str, Enum):
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"
    RETRIEVAL = "retrieval"
    EMBEDDING = "embedding"
    HTTP = "http"
    DATABASE = "database"
    CUSTOM = "custom"

class ToolErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    PROVIDER_ERROR = "provider_error"
    APPLICATION_ERROR = "application_error"
    UNKNOWN = "unknown"

class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"

class TelemetryPrivacyConfig(BaseModel):
    capture_prompt_content: bool = False
    capture_completion_content: bool = False
    capture_tool_arguments: bool = False
    capture_tool_results: bool = False
    redact_api_keys: bool = True
    redact_emails: bool = True
    redact_auth_headers: bool = True
    sensitive_keys: List[str] = Field(default_factory=lambda: [
        "authorization", "api_key", "password", "secret", "token", "ssn", "credit_card"
    ])
