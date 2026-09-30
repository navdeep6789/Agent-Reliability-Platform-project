from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
import sys
import os

# Ensure demo is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))
from demo.scenarios_runner import ScenariosRunner

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.post("/run-scenario")
def trigger_scenario(
    scenario: str = Query(..., description="Scenario name: slow_tool, tool_failure, retry_loop, expensive_context, invalid_tool_arguments, operation_loop, provider_failure, missing_telemetry, seed_all")
):
    runners = {
        "slow_tool": ScenariosRunner.run_slow_tool,
        "tool_failure": ScenariosRunner.run_tool_failure,
        "retry_loop": ScenariosRunner.run_retry_loop,
        "expensive_context": ScenariosRunner.run_expensive_context,
        "invalid_tool_arguments": ScenariosRunner.run_invalid_tool_arguments,
        "operation_loop": ScenariosRunner.run_operation_loop,
        "provider_failure": ScenariosRunner.run_provider_failure,
        "missing_telemetry": ScenariosRunner.run_missing_telemetry,
        "seed_all": ScenariosRunner.run_all
    }

    if scenario not in runners:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{scenario}'. Available: {list(runners.keys())}")

    res = runners[scenario]()
    return {"scenario": scenario, "result": res}
