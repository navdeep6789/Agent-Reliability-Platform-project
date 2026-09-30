import re
import json
from typing import Dict, Any, List, Optional
from arp_schemas import EvaluatorType

class EvaluatorResult:
    def __init__(self, passed: bool, score: float, failure_reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.passed = passed
        self.score = score
        self.failure_reason = failure_reason
        self.details = details or {}

class ExactMatchEvaluator:
    @staticmethod
    def evaluate(actual: str, expected: str) -> EvaluatorResult:
        if not expected:
            return EvaluatorResult(True, 1.0)
        norm_actual = (actual or "").strip().lower()
        norm_expected = expected.strip().lower()
        passed = norm_actual == norm_expected
        return EvaluatorResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            failure_reason=None if passed else f"Expected exact match '{norm_expected}', got '{norm_actual[:50]}...'"
        )

class JsonSchemaEvaluator:
    @staticmethod
    def evaluate(actual: str, expected_schema: Optional[Dict[str, Any]] = None) -> EvaluatorResult:
        if not actual:
            return EvaluatorResult(False, 0.0, "Empty JSON response")
        try:
            # Parse json or extract json from markdown codeblocks
            clean = actual
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0]
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0]
            parsed = json.loads(clean.strip())
        except Exception as e:
            return EvaluatorResult(False, 0.0, f"Malformed JSON: {str(e)}")

        if not expected_schema:
            return EvaluatorResult(True, 1.0, details={"parsed": parsed})

        # Verify required keys
        required_keys = expected_schema.get("required", [])
        missing = [k for k in required_keys if k not in parsed]
        if missing:
            return EvaluatorResult(
                False,
                max(0.0, 1.0 - (len(missing) / max(len(required_keys), 1))),
                f"Missing required JSON schema keys: {missing}",
                details={"missing": missing, "parsed": parsed}
            )

        return EvaluatorResult(True, 1.0, details={"parsed": parsed})

class ToolSelectionEvaluator:
    @staticmethod
    def evaluate(called_tools: List[str], expected_tools: List[str]) -> EvaluatorResult:
        if not expected_tools:
            return EvaluatorResult(True, 1.0)
        
        called_set = set(called_tools)
        expected_set = set(expected_tools)
        intersection = called_set.intersection(expected_set)

        score = len(intersection) / len(expected_set)
        passed = score == 1.0
        missing = list(expected_set - called_set)

        return EvaluatorResult(
            passed=passed,
            score=score,
            failure_reason=None if passed else f"Agent failed to invoke required tools: {missing}",
            details={"called": list(called_set), "expected": list(expected_set), "missing": missing}
        )

class CitationPresenceEvaluator:
    @staticmethod
    def evaluate(actual: str, required_citations: List[str]) -> EvaluatorResult:
        if not required_citations:
            return EvaluatorResult(True, 1.0)

        found = [cite for cite in required_citations if cite.lower() in (actual or "").lower()]
        score = len(found) / len(required_citations)
        passed = score == 1.0
        missing = [c for c in required_citations if c not in found]

        return EvaluatorResult(
            passed=passed,
            score=score,
            failure_reason=None if passed else f"Missing citations or source references: {missing}",
            details={"found": found, "missing": missing}
        )

class ResponseLengthEvaluator:
    @staticmethod
    def evaluate(actual: str, min_chars: int = 10, max_chars: int = 5000) -> EvaluatorResult:
        length = len(actual or "")
        if length < min_chars:
            return EvaluatorResult(False, 0.0, f"Response too short ({length} chars, min {min_chars})")
        if length > max_chars:
            return EvaluatorResult(False, 0.5, f"Response exceeded max limit ({length} chars, max {max_chars})")
        return EvaluatorResult(True, 1.0, details={"length": length})

class RegexPatternEvaluator:
    @staticmethod
    def evaluate(actual: str, pattern: str) -> EvaluatorResult:
        match = re.search(pattern, actual or "", re.IGNORECASE)
        passed = bool(match)
        return EvaluatorResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            failure_reason=None if passed else f"Response did not match expected regex pattern: '{pattern}'"
        )
