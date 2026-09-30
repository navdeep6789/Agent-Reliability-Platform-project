import pytest
from app.cost.pricing import CostEngine

def test_cost_calculation_known_model():
    engine = CostEngine()
    # gpt-4o: $2.50 / 1M in, $10.00 / 1M out
    res = engine.calculate_cost("gpt-4o", "openai", 1000000, 500000)
    assert res.pricing_available is True
    assert res.input_cost_usd == 2.50
    assert res.output_cost_usd == 5.00
    assert res.total_cost_usd == 7.50

def test_cost_calculation_unknown_model():
    engine = CostEngine()
    res = engine.calculate_cost("unregistered-custom-fine-tuned-model", "local", 5000, 1000)
    # Prompt rule: if pricing unavailable, display Cost unavailable, do NOT invent cost!
    assert res.pricing_available is False
    assert res.total_cost_usd == 0.0

def test_custom_pricing_update():
    engine = CostEngine()
    engine.set_model_pricing("my-deepseek-r1", "deepseek", 0.55, 2.19)
    res = engine.calculate_cost("my-deepseek-r1", "deepseek", 1000000, 1000000)
    assert res.pricing_available is True
    assert res.total_cost_usd == 2.74
