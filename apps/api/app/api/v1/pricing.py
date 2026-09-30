from typing import Dict, Any
from fastapi import APIRouter, Depends, Body
from ...cost.pricing import cost_engine
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/pricing", tags=["Pricing"])

@router.get("")
def get_pricing_registry(
    auth: dict = Depends(verify_api_key)
):
    items = []
    for model, cfg in cost_engine.pricing_registry.items():
        items.append({
            "model": model,
            "provider": cfg.get("provider", "unknown"),
            "input_price_per_million": cfg.get("input", 0.0),
            "output_price_per_million": cfg.get("output", 0.0)
        })
    return {"pricing": items}

@router.post("")
def update_model_pricing(
    payload: Dict[str, Any] = Body(...),
    auth: dict = Depends(verify_api_key)
):
    model = payload.get("model")
    provider = payload.get("provider", "unknown")
    input_price = float(payload.get("input_price_per_million", 0.0))
    output_price = float(payload.get("output_price_per_million", 0.0))

    cost_engine.set_model_pricing(model, provider, input_price, output_price)
    return {"status": "updated", "model": model, "provider": provider}
