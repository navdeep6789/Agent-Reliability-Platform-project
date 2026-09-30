"use client";

import React, { useState } from "react";
import { Play, Check, AlertCircle, X, Loader2, Sparkles, Clock, Repeat, ShieldAlert, Cpu } from "lucide-react";
import { api } from "../lib/api";

interface ScenarioRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onScenarioCompleted: () => void;
}

export function ScenarioRunnerModal({ isOpen, onClose, onScenarioCompleted }: ScenarioRunnerModalProps) {
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const scenarios = [
    {
      id: "slow_tool",
      name: "Slow Tool Latency Analysis",
      description: "CRM tool takes 2.5s, dominating > 60% of total run latency. Generates exact TOOL_LATENCY finding.",
      icon: Clock,
      badge: "Interview Demo"
    },
    {
      id: "tool_failure",
      name: "Tool Transient Failure & Retry",
      description: "CRM tool encounters timeouts twice before succeeding on retry #2. Generates RETRY_LOOP analysis.",
      icon: Repeat,
      badge: "Retry Analysis"
    },
    {
      id: "retry_loop",
      name: "Retry Storm & Policy Violation",
      description: "Tool fails 3 times, exceeding configured MAX_TOOL_RETRIES policy threshold (limit: 2).",
      icon: ShieldAlert,
      badge: "Policy Violation"
    },
    {
      id: "expensive_context",
      name: "Explosive Context Growth (+1,225%)",
      description: "Sequential calls suffer rapid prompt inflation: 2,400 → 31,800 tokens (13.3x). Triggers MAX_CONTEXT_TOKENS.",
      icon: Cpu,
      badge: "Context Blowup"
    },
    {
      id: "invalid_tool_arguments",
      name: "Tool Schema Validation Error",
      description: "Agent supplies malformed arguments to SQL engine causing controlled validation failure.",
      icon: AlertCircle,
      badge: "Validation Error"
    },
    {
      id: "operation_loop",
      name: "Cyclic Execution Loop",
      description: "Agent gets stuck executing the same tool sequence 4 times consecutively without progressing.",
      icon: Repeat,
      badge: "Loop Detection"
    },
    {
      id: "provider_failure",
      name: "Model Provider Outage (503)",
      description: "Simulates model provider HTTP 503 gateway timeout, triggering PROVIDER_FAILURE finding.",
      icon: AlertCircle,
      badge: "Provider Failure"
    },
    {
      id: "missing_telemetry",
      name: "Missing Telemetry & Orphan Span",
      description: "Trace contains an orphaned child span referencing a non-existent parent span.",
      icon: AlertCircle,
      badge: "Telemetry Integrity"
    },
    {
      id: "seed_all",
      name: "Run Complete Demo Suite",
      description: "Executes all 3 standard agents (Support, Research, Data) plus all 8 failure scenarios in batch.",
      icon: Sparkles,
      badge: "Batch Seed"
    }
  ];

  const handleRun = async (scenarioId: string) => {
    setRunningScenario(scenarioId);
    setErrorMsg(null);
    setLastResult(null);

    try {
      const res = await api.runDemoScenario(scenarioId);
      setLastResult(res);
      onScenarioCompleted();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to trigger scenario");
    } finally {
      setRunningScenario(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-surface border border-surface-border rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-surface-elevated/50">
          <div className="flex items-center space-x-2">
            <Play className="w-4 h-4 text-accent-cyan fill-current" />
            <h3 className="font-semibold text-sm text-white">Execute Live Telemetry Scenarios</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-surface transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto space-y-3">
          <p className="text-xs text-slate-400">
            Select a reproducible failure scenario to execute against live instrumented demo agents. Real telemetry will be emitted through OpenTelemetry semantic conventions, normalized, analyzed by the Reliability Engine, and displayed in real-time.
          </p>

          {errorMsg && (
            <div className="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono">
              {errorMsg}
            </div>
          )}

          {lastResult && (
            <div className="p-3 rounded bg-emerald-950/40 border border-emerald-800 text-emerald-300 text-xs font-mono flex items-center justify-between">
              <span>Scenario '{lastResult.scenario}' executed successfully! Telemetry updated.</span>
              <Check className="w-4 h-4" />
            </div>
          )}

          <div className="grid grid-cols-1 gap-2 pt-1">
            {scenarios.map((sc) => {
              const Icon = sc.icon;
              const isRunning = runningScenario === sc.id;

              return (
                <div
                  key={sc.id}
                  className="p-3 rounded-lg border border-surface-border bg-surface-elevated/40 hover:bg-surface-elevated hover:border-slate-600 transition flex items-center justify-between"
                >
                  <div className="flex items-start space-x-3 pr-4">
                    <div className="p-2 rounded bg-surface border border-surface-border mt-0.5">
                      <Icon className="w-4 h-4 text-accent-cyan" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-xs text-white">{sc.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface border border-surface-border text-slate-400">
                          {sc.badge}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{sc.description}</p>
                    </div>
                  </div>

                  <button
                    disabled={runningScenario !== null}
                    onClick={() => handleRun(sc.id)}
                    className="shrink-0 flex items-center space-x-1.5 text-xs font-mono font-medium bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white px-3 py-1.5 rounded transition"
                  >
                    {isRunning ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Running...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>Run</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-surface-border bg-surface-elevated/40 flex justify-end">
          <button
            onClick={onClose}
            className="text-xs font-mono text-slate-300 hover:text-white px-4 py-1.5 rounded bg-surface border border-surface-border hover:bg-surface-elevated transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
