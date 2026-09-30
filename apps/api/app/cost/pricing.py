from typing import Dict, Optional, Tuple
from datetime import datetime
from arp_schemas import ModelPricing, CostBreakdown

DEFAULT_PRICING_TABLE: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"provider": "openai", "input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"provider": "openai", "input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"provider": "openai", "input": 10.00, "output": 30.00},
    "o1-preview": {"provider": "openai", "input": 15.00, "output": 60.00},
    "o1-mini": {"provider": "openai", "input": 3.00, "output": 12.00},
    
    # Anthropic
    "claude-3-5-sonnet-20241022": {"provider": "anthropic", "input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"provider": "anthropic", "input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"provider": "anthropic", "input": 15.00, "output": 75.00},
    
    # Google
    "gemini-1.5-pro": {"provider": "google", "input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"provider": "google", "input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"provider": "google", "input": 0.10, "output": 0.40},

    # Meta / Open-source (Hosted inference rates)
    "llama-3.1-70b": {"provider": "meta", "input": 0.60, "output": 0.80},
    "llama-3.1-8b": {"provider": "meta", "input": 0.10, "output": 0.10}
}

class CostEngine:
    def __init__(self):
        self.pricing_registry: Dict[str, Dict[str, float]] = dict(DEFAULT_PRICING_TABLE)

    def set_model_pricing(self, model: str, provider: str, input_per_million: float, output_per_million: float):
        self.pricing_registry[model.lower()] = {
            "provider": provider.lower(),
            "input": input_per_million,
            "output": output_per_million
        }

    def get_pricing(self, model: str) -> Optional[Dict[str, float]]:
        if not model:
            return None
        m_lower = model.lower()
        # Direct match or substring match
        if m_lower in self.pricing_registry:
            return self.pricing_registry[m_lower]
        for key, val in self.pricing_registry.items():
            if key in m_lower or m_lower in key:
                return val
        return None

    def calculate_cost(
        self,
        model: Optional[str],
        provider: Optional[str],
        input_tokens: int,
        output_tokens: int
    ) -> CostBreakdown:
        pricing = self.get_pricing(model) if model else None
        if not pricing:
            return CostBreakdown(
                provider=provider or "unknown",
                model=model or "unknown",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                input_cost_usd=0.0,
                output_cost_usd=0.0,
                total_cost_usd=0.0,
                pricing_available=False
            )

        input_cost = (input_tokens / 1_000_000.0) * pricing["input"]
        output_cost = (output_tokens / 1_000_000.0) * pricing["output"]
        total_cost = round(input_cost + output_cost, 6)

        return CostBreakdown(
            provider=pricing.get("provider", provider or "unknown"),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_usd=round(input_cost, 6),
            output_cost_usd=round(output_cost, 6),
            total_cost_usd=total_cost,
            pricing_available=True
        )

# Global cost engine singleton
cost_engine = CostEngine()
