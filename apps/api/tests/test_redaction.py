import pytest
from arp.redaction import RedactionPipeline

def test_redact_api_keys():
    pipeline = RedactionPipeline()
    raw = "Here is my secret sk-proj-1234567890abcdef1234567890 and Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    redacted = pipeline.redact_text(raw)
    assert "sk-proj-1234567890abcdef1234567890" not in redacted
    assert "[REDACTED_SECRET]" in redacted

def test_redact_emails():
    pipeline = RedactionPipeline()
    raw = "Customer email is customer.service@enterprise-corp.com in the ticket."
    redacted = pipeline.redact_text(raw)
    assert "customer.service@enterprise-corp.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted

def test_redact_sensitive_dict_fields():
    pipeline = RedactionPipeline()
    data = {
        "user_id": "usr_123",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-secret-token",
        "nested": {
            "auth_token": "token_val",
            "safe_field": "visible_data"
        }
    }
    redacted = pipeline.redact_dict(data)
    assert redacted["password"] == "[REDACTED_FIELD]"
    assert redacted["api_key"] == "[REDACTED_FIELD]"
    assert redacted["nested"]["auth_token"] == "[REDACTED_FIELD]"
    assert redacted["nested"]["safe_field"] == "visible_data"
