import re
from typing import Any, Dict, List, Union

API_KEY_REGEX = re.compile(r'(?:sk-[a-zA-Z0-9_-]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]{20,}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[a-zA-Z0-9\-]{10,})')
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PASSWORD_FIELD_REGEX = re.compile(r'(password|passwd|secret|api_key|token|access_token|auth|credential)', re.IGNORECASE)

class RedactionPipeline:
    def __init__(
        self,
        redact_keys: bool = True,
        redact_emails: bool = True,
        sensitive_field_names: List[str] = None
    ):
        self.redact_keys = redact_keys
        self.redact_emails = redact_emails
        self.sensitive_field_names = sensitive_field_names or [
            "password", "secret", "token", "authorization", "api_key", "access_token"
        ]

    def redact_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        result = text
        if self.redact_keys:
            result = API_KEY_REGEX.sub("[REDACTED_SECRET]", result)
        if self.redact_emails:
            result = EMAIL_REGEX.sub("[REDACTED_EMAIL]", result)
        return result

    def redact_dict(self, data: Any) -> Any:
        if isinstance(data, dict):
            redacted = {}
            for k, v in data.items():
                if any(k.lower() == sensitive.lower() or sensitive.lower() in k.lower() for sensitive in self.sensitive_field_names):
                    redacted[k] = "[REDACTED_FIELD]"
                else:
                    redacted[k] = self.redact_dict(v)
            return redacted
        elif isinstance(data, list):
            return [self.redact_dict(item) for item in data]
        elif isinstance(data, str):
            return self.redact_text(data)
        return data
