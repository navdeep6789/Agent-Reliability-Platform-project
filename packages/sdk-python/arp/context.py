import uuid
from contextvars import ContextVar
from typing import Optional, List, Dict, Any

_current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_current_run_id: ContextVar[Optional[str]] = ContextVar("current_run_id", default=None)
_current_span_stack: ContextVar[List[str]] = ContextVar("current_span_stack", default=[])
_current_run_metadata: ContextVar[Dict[str, Any]] = ContextVar("current_run_metadata", default={})

def generate_id(prefix: str = "") -> str:
    hex_id = uuid.uuid4().hex
    return f"{prefix}{hex_id}" if prefix else hex_id

def get_trace_id() -> Optional[str]:
    return _current_trace_id.get()

def set_trace_id(trace_id: str) -> None:
    _current_trace_id.set(trace_id)

def get_run_id() -> Optional[str]:
    return _current_run_id.get()

def set_run_id(run_id: str) -> None:
    _current_run_id.set(run_id)

def get_parent_span_id() -> Optional[str]:
    stack = _current_span_stack.get()
    return stack[-1] if stack else None

def push_span_id(span_id: str) -> None:
    stack = list(_current_span_stack.get())
    stack.append(span_id)
    _current_span_stack.set(stack)

def pop_span_id() -> Optional[str]:
    stack = list(_current_span_stack.get())
    if stack:
        val = stack.pop()
        _current_span_stack.set(stack)
        return val
    return None

def set_run_context(metadata: Dict[str, Any]) -> None:
    _current_run_metadata.set(metadata)

def get_run_context() -> Dict[str, Any]:
    return _current_run_metadata.get()
