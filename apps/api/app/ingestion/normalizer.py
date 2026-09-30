import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from arp_schemas import SpanType, SpanStatus, ToolErrorType

def parse_iso_or_timestamp(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # Nanoseconds or milliseconds or seconds
        if val > 1e16: # nanoseconds
            return datetime.utcfromtimestamp(val / 1e9)
        elif val > 1e11: # milliseconds
            return datetime.utcfromtimestamp(val / 1e3)
        return datetime.utcfromtimestamp(val)
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.utcnow()

MAX_ATTRIBUTE_COUNT = 128
MAX_ATTRIBUTE_KEY_LENGTH = 128
MAX_ATTRIBUTE_VALUE_LENGTH = 16384

def sanitize_attributes(attrs: Any) -> Dict[str, Any]:
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except Exception:
            attrs = {"raw_text": attrs[:MAX_ATTRIBUTE_VALUE_LENGTH]}
    if not isinstance(attrs, dict):
        return {}

    sanitized = {}
    for i, (k, v) in enumerate(attrs.items()):
        if i >= MAX_ATTRIBUTE_COUNT:
            break
        safe_key = str(k)[:MAX_ATTRIBUTE_KEY_LENGTH]
        if isinstance(v, str):
            if len(v) > MAX_ATTRIBUTE_VALUE_LENGTH:
                safe_val = v[:MAX_ATTRIBUTE_VALUE_LENGTH] + "... [TRUNCATED]"
            else:
                safe_val = v
        elif isinstance(v, (int, float, bool)) or v is None:
            safe_val = v
        elif isinstance(v, (dict, list)):
            v_str = json.dumps(v)
            if len(v_str) > MAX_ATTRIBUTE_VALUE_LENGTH:
                safe_val = v_str[:MAX_ATTRIBUTE_VALUE_LENGTH] + "... [TRUNCATED]"
            else:
                safe_val = v
        else:
            safe_val = str(v)[:MAX_ATTRIBUTE_VALUE_LENGTH]
        sanitized[safe_key] = safe_val
    return sanitized

class SpanNormalizer:
    @staticmethod
    def normalize_sdk_span(raw_span: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize span dictionary sent directly from ARP SDK."""
        start_time = parse_iso_or_timestamp(raw_span.get("start_time"))
        end_time = parse_iso_or_timestamp(raw_span.get("end_time")) if raw_span.get("end_time") else None
        
        duration_ms = float(raw_span.get("duration_ms") or 0.0)
        if duration_ms == 0.0 and end_time and start_time:
            duration_ms = (end_time - start_time).total_seconds() * 1000.0

        # Prevent negative durations from clock skew or out-of-order timestamps
        duration_ms = max(duration_ms, 0.0)

        attrs = sanitize_attributes(raw_span.get("attributes", {}))

        span_id = str(raw_span.get("span_id") or f"span_{int(datetime.utcnow().timestamp()*1000)}")
        trace_id = str(raw_span.get("trace_id") or f"trace_{int(datetime.utcnow().timestamp()*1000)}")
        run_id = str(raw_span.get("run_id") or trace_id)

        span_type = raw_span.get("span_type")
        name = str(raw_span.get("name") or "span")[:256]

        # Infer span_type if custom
        if not span_type or span_type == "custom":
            if name.startswith("agent."):
                span_type = "agent"
            elif name.startswith("llm."):
                span_type = "llm"
            elif name.startswith("tool."):
                span_type = "tool"
            elif name.startswith("retrieval."):
                span_type = "retrieval"
            else:
                span_type = "custom"

        status = raw_span.get("status", "ok")
        if status not in ("ok", "error", "unset"):
            status = "error" if "fail" in str(status).lower() or "err" in str(status).lower() else "ok"

        return {
            "span_id": span_id,
            "trace_id": trace_id,
            "run_id": run_id,
            "parent_span_id": raw_span.get("parent_span_id"),
            "name": name,
            "span_type": span_type,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "status_message": str(raw_span.get("status_message") or "")[:1024] if raw_span.get("status_message") else None,
            "attributes": attrs,
            "events": raw_span.get("events", []) if isinstance(raw_span.get("events"), list) else []
        }

    @staticmethod
    def normalize_otlp_span(otlp_span: Dict[str, Any], resource_attrs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Normalize standard OTLP JSON span format (from OpenTelemetry Collector)."""
        span_id = otlp_span.get("spanId") or otlp_span.get("span_id")
        trace_id = otlp_span.get("traceId") or otlp_span.get("trace_id")
        parent_id = otlp_span.get("parentSpanId") or otlp_span.get("parent_span_id")
        name = otlp_span.get("name", "span")

        start_time_unix = otlp_span.get("startTimeUnixNano") or otlp_span.get("start_time_unix_nano")
        end_time_unix = otlp_span.get("endTimeUnixNano") or otlp_span.get("end_time_unix_nano")

        start_time = parse_iso_or_timestamp(start_time_unix) if start_time_unix else datetime.utcnow()
        end_time = parse_iso_or_timestamp(end_time_unix) if end_time_unix else datetime.utcnow()
        raw_dur = (end_time - start_time).total_seconds() * 1000.0
        duration_ms = max(raw_dur, 0.0)

        # Unpack OTLP key-value attributes list
        attributes = dict(resource_attrs or {})
        raw_attrs = otlp_span.get("attributes", [])
        if isinstance(raw_attrs, list):
            for item in raw_attrs:
                key = item.get("key")
                val_dict = item.get("value", {})
                for v_type, v in val_dict.items():
                    attributes[key] = v
        elif isinstance(raw_attrs, dict):
            attributes.update(raw_attrs)

        attributes = sanitize_attributes(attributes)

        span_id = str(span_id or f"span_{int(datetime.utcnow().timestamp()*1000)}")
        trace_id = str(trace_id or f"trace_{int(datetime.utcnow().timestamp()*1000)}")

        run_id = attributes.get("arp.run.id") or trace_id
        span_type = attributes.get("arp.span.type")

        if not span_type:
            if "gen_ai.system" in attributes or name.startswith("llm."):
                span_type = "llm"
            elif "arp.tool.name" in attributes or name.startswith("tool."):
                span_type = "tool"
            elif name.startswith("agent."):
                span_type = "agent"
            else:
                span_type = "custom"

        status_obj = otlp_span.get("status", {})
        status_code = status_obj.get("code", 0) # 1 = OK, 2 = ERROR
        status = "error" if status_code == 2 else "ok"
        status_message = status_obj.get("message")

        return {
            "span_id": span_id,
            "trace_id": trace_id,
            "run_id": run_id,
            "parent_span_id": parent_id,
            "name": name,
            "span_type": span_type,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "status_message": status_message,
            "attributes": attributes,
            "events": otlp_span.get("events", [])
        }
