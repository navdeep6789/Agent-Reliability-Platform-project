import time
import functools
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager

from .context import (
    generate_id,
    get_trace_id,
    set_trace_id,
    get_run_id,
    set_run_id,
    get_parent_span_id,
    push_span_id,
    pop_span_id,
    set_run_context,
    get_run_context
)
from .redaction import RedactionPipeline
from .exporter import TelemetryExporter

class SpanContext:
    def __init__(
        self,
        span_id: str,
        name: str,
        span_type: str,
        trace_id: str,
        run_id: str,
        parent_span_id: Optional[str] = None
    ):
        self.span_id = span_id
        self.name = name
        self.span_type = span_type
        self.trace_id = trace_id
        self.run_id = run_id
        self.parent_span_id = parent_span_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_ms: float = 0.0
        self.status: str = "ok"
        self.status_message: Optional[str] = None
        self.attributes: Dict[str, Any] = {}
        self.events: List[Dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, attrs: Dict[str, Any]) -> None:
        self.attributes.update(attrs)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {}
        })

    def set_status(self, status: str, message: Optional[str] = None) -> None:
        self.status = status
        if message:
            self.status_message = message

    def finish(self) -> None:
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events
        }

class Observer:
    def __init__(self):
        self.exporter: Optional[TelemetryExporter] = None
        self.redaction = RedactionPipeline()
        self.capture_prompt_content = False
        self.capture_completion_content = False
        self.capture_tool_arguments = False
        self.capture_tool_results = False
        self.project_id = "proj_default_production"
        self.environment = "production"

    def init(
        self,
        endpoint: str = "http://localhost:8000/api/v1/ingest/spans",
        api_key: Optional[str] = None,
        project_id: str = "proj_default_production",
        environment: str = "production",
        capture_prompt_content: bool = False,
        capture_completion_content: bool = False,
        capture_tool_arguments: bool = False,
        capture_tool_results: bool = False,
        redact_keys: bool = True,
        redact_emails: bool = True,
        fail_closed: bool = False,
        direct_handler: Optional[Any] = None
    ) -> None:
        self.project_id = project_id
        self.environment = environment
        self.capture_prompt_content = capture_prompt_content
        self.capture_completion_content = capture_completion_content
        self.capture_tool_arguments = capture_tool_arguments
        self.capture_tool_results = capture_tool_results
        self.fail_closed = fail_closed
        self.redaction = RedactionPipeline(redact_keys=redact_keys, redact_emails=redact_emails)
        self.exporter = TelemetryExporter(
            endpoint=endpoint,
            api_key=api_key,
            project_id=project_id,
            environment=environment,
            fail_closed=fail_closed,
            direct_handler=direct_handler
        )

    def _get_exporter(self) -> TelemetryExporter:
        if self.exporter is None:
            self.exporter = TelemetryExporter(
                project_id=self.project_id,
                environment=self.environment,
                fail_closed=self.fail_closed
            )
        return self.exporter

    @contextmanager
    def agent(
        self,
        name: str,
        version: str = "1.0.0",
        prompt_version: Optional[str] = None,
        run_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        active_trace_id = trace_id or generate_id()
        active_run_id = run_id or generate_id("run_")
        span_id = generate_id()

        set_trace_id(active_trace_id)
        set_run_id(active_run_id)
        set_run_context({
            "agent_name": name,
            "agent_version": version,
            "prompt_version": prompt_version,
            "project_id": self.project_id,
            "environment": self.environment
        })

        span = SpanContext(
            span_id=span_id,
            name=f"agent.{name}",
            span_type="agent",
            trace_id=active_trace_id,
            run_id=active_run_id,
            parent_span_id=None
        )
        span.set_attributes({
            "arp.agent.name": name,
            "arp.agent.version": version,
            "arp.prompt.version": prompt_version or "1.0.0",
            "arp.project.id": self.project_id,
            "arp.environment": self.environment,
            "user.id": user_id,
            "session.id": session_id,
            **(metadata or {})
        })

        push_span_id(span_id)
        try:
            yield span
        except Exception as exc:
            span.set_status("error", str(exc))
            span.add_event("exception", {
                "exception.type": type(exc).__name__,
                "exception.message": str(exc),
                "exception.stacktrace": traceback.format_exc()
            })
            raise
        finally:
            span.finish()
            pop_span_id()
            try:
                self._get_exporter().enqueue_span(span.to_dict())
                self._get_exporter().flush()
            except Exception as e:
                if getattr(self._get_exporter(), "fail_closed", False):
                    raise
                # Graceful fail-open: never crash user agent if observability export fails

    @contextmanager
    def llm(
        self,
        model: str,
        provider: str = "openai",
        operation: str = "chat",
        prompt: Optional[str] = None
    ):
        trace_id = get_trace_id() or generate_id()
        run_id = get_run_id() or generate_id("run_")
        parent_id = get_parent_span_id()
        span_id = generate_id()

        span = SpanContext(
            span_id=span_id,
            name=f"llm.{provider}.{model}",
            span_type="llm",
            trace_id=trace_id,
            run_id=run_id,
            parent_span_id=parent_id
        )
        span.set_attributes({
            "gen_ai.system": provider,
            "gen_ai.request.model": model,
            "gen_ai.operation.name": operation,
            "arp.content.capture_enabled": self.capture_prompt_content
        })

        if self.capture_prompt_content and prompt:
            sanitized = self.redaction.redact_text(prompt)
            span.set_attribute("gen_ai.prompt", sanitized)

        push_span_id(span_id)
        try:
            yield span
        except Exception as exc:
            span.set_status("error", str(exc))
            span.add_event("exception", {
                "exception.type": type(exc).__name__,
                "exception.message": str(exc)
            })
            raise
        finally:
            span.finish()
            pop_span_id()
            try:
                self._get_exporter().enqueue_span(span.to_dict())
            except Exception as e:
                if getattr(self._get_exporter(), "fail_closed", False):
                    raise
                # Fail-open: preserve user execution

    @contextmanager
    def tool(
        self,
        name: str,
        tool_call_id: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ):
        trace_id = get_trace_id() or generate_id()
        run_id = get_run_id() or generate_id("run_")
        parent_id = get_parent_span_id()
        span_id = generate_id()

        span = SpanContext(
            span_id=span_id,
            name=f"tool.{name}",
            span_type="tool",
            trace_id=trace_id,
            run_id=run_id,
            parent_span_id=parent_id
        )
        span.set_attributes({
            "arp.tool.name": name,
            "arp.tool.call_id": tool_call_id or generate_id("call_"),
            "arp.tool.retry_count": retry_count,
            "arp.content.capture_enabled": self.capture_tool_arguments
        })

        if self.capture_tool_arguments and arguments:
            sanitized = self.redaction.redact_dict(arguments)
            span.set_attribute("arp.tool.arguments", sanitized)

        push_span_id(span_id)
        try:
            yield span
        except Exception as exc:
            span.set_status("error", str(exc))
            span.set_attribute("arp.tool.status", "failed")
            span.set_attribute("arp.tool.error_type", self._classify_error(exc))
            span.add_event("exception", {
                "exception.type": type(exc).__name__,
                "exception.message": str(exc)
            })
            raise
        finally:
            span.finish()
            pop_span_id()
            try:
                self._get_exporter().enqueue_span(span.to_dict())
            except Exception as e:
                if getattr(self._get_exporter(), "fail_closed", False):
                    raise
                # Fail-open: preserve user execution

    def _classify_error(self, exc: Exception) -> str:
        msg = str(exc).lower()
        exc_name = type(exc).__name__.lower()
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "validation" in msg or "valueerror" in exc_name or "schema" in msg:
            return "validation_error"
        if "rate limit" in msg or "429" in msg:
            return "rate_limit"
        if "unauthorized" in msg or "auth" in msg or "401" in msg or "403" in msg:
            return "authentication_error"
        if "503" in msg or "unavailable" in msg or "connection" in msg:
            return "unavailable"
        return "application_error"

    def record_llm_usage(
        self,
        span: SpanContext,
        input_tokens: int,
        output_tokens: int,
        finish_reason: Optional[str] = "stop",
        completion: Optional[str] = None
    ) -> None:
        span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
        span.set_attribute("gen_ai.response.finish_reason", finish_reason)
        if self.capture_completion_content and completion:
            sanitized = self.redaction.redact_text(completion)
            span.set_attribute("gen_ai.completion", sanitized)

    def record_tool_result(
        self,
        span: SpanContext,
        result: Any,
        status: str = "ok"
    ) -> None:
        span.set_attribute("arp.tool.status", status)
        if self.capture_tool_results and result is not None:
            sanitized = self.redaction.redact_dict(result) if isinstance(result, (dict, list)) else self.redaction.redact_text(str(result))
            span.set_attribute("arp.tool.result", sanitized)

    def retrieval(
        self,
        name: str = "retrieval",
        query: Optional[str] = None,
        documents_count: int = 0,
        latency_ms: float = 0.0
    ) -> None:
        trace_id = get_trace_id() or generate_id()
        run_id = get_run_id() or generate_id("run_")
        parent_id = get_parent_span_id()
        span_id = generate_id()

        span = SpanContext(
            span_id=span_id,
            name=f"retrieval.{name}",
            span_type="retrieval",
            trace_id=trace_id,
            run_id=run_id,
            parent_span_id=parent_id
        )
        span.duration_ms = latency_ms
        span.set_attributes({
            "retrieval.documents_count": documents_count,
            "retrieval.query": self.redaction.redact_text(query) if (self.capture_prompt_content and query) else "[REDACTED]"
        })
        span.finish()
        try:
            self._get_exporter().enqueue_span(span.to_dict())
        except Exception as e:
            if getattr(self._get_exporter(), "fail_closed", False):
                raise
            # Fail-open

    def flush(self) -> None:
        if self.exporter:
            self.exporter.flush()

# Global singleton
observe = Observer()
