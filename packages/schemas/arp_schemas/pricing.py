from typing import Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class ModelPricing(BaseModel):
    provider: str # e.g. "openai", "anthropic", "google", "meta"
    model: str # e.g. "gpt-4o", "claude-3-5-sonnet-20241022", "gemini-1.5-pro"
    input_price_per_million: float # price in USD per 1M input tokens
    output_price_per_million: float # price in USD per 1M output tokens
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

class CostBreakdown(BaseModel):
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    pricing_available: bool = True
