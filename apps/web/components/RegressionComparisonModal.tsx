"use client";

import React, { useEffect, useState } from "react";
import { GitCompare, ArrowRight, AlertTriangle, CheckCircle, X, Loader2 } from "lucide-react";
import { api } from "../lib/api";

interface RegressionModalProps {
  isOpen: boolean;
  onClose: () => void;
  baselineRunId?: string;
  candidateRunId?: string;
}

export function RegressionComparisonModal({
  isOpen,
  onClose,
  baselineRunId = "eval_run_baseline_v1",
  candidateRunId = "eval_run_candidate_v2"
}: RegressionModalProps) {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && baselineRunId && candidateRunId) {
      loadComparison();
    }
  }, [isOpen, baselineRunId, candidateRunId]);

  const loadComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.compareEvalRuns(baselineRunId, candidateRunId);
      setReport(data);
    } catch (err: any) {
      setError(err.message || "Failed to compare versions");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-surface border border-surface-border rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-surface-elevated/50">
          <div className="flex items-center space-x-2">
            <GitCompare className="w-4 h-4 text-accent-cyan" />
            <h3 className="font-semibold text-sm text-white">Agent Version Regression Analysis</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-surface transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-12 space-x-2 text-slate-400 font-mono text-xs">
              <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
              <span>Analyzing evaluation runs for regression...</span>
            </div>
          ) : error ? (
            <div className="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300 text-xs font-mono">
              {error}
            </div>
          ) : report ? (
            <div className="space-y-4">
              {/* Regression Alert Banner */}
              {report.has_regression ? (
                <div className="p-3 rounded bg-rose-950/30 border border-rose-800/80 space-y-2">
                  <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs font-mono uppercase">
                    <AlertTriangle className="w-4 h-4" />
                    <span>Potential Version Regression Detected</span>
                  </div>
                  <ul className="text-xs text-rose-200 space-y-1 list-disc list-inside">
                    {report.reasons.map((r: string, idx: number) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="p-3 rounded bg-emerald-950/30 border border-emerald-800/80 flex items-center space-x-2 text-emerald-300 text-xs font-mono">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>No regression detected across monitored metrics and benchmark cases.</span>
                </div>
              )}

              {/* Version Comparison Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-surface-elevated border border-surface-border space-y-2">
                  <div className="text-[10px] text-slate-400 uppercase font-bold">
                    Baseline (v{report.baseline_version})
                  </div>
                  <div className="space-y-1 text-slate-300 text-[11px]">
                    <div>Run ID: <span className="text-white">{report.baseline_run_id}</span></div>
                    <div>Agent: <span className="text-white">{report.agent_name}</span></div>
                  </div>
                </div>

                <div className="p-3 rounded bg-surface-elevated border border-surface-border space-y-2">
                  <div className="text-[10px] text-accent-cyan uppercase font-bold">
                    Candidate (v{report.candidate_version})
                  </div>
                  <div className="space-y-1 text-slate-300 text-[11px]">
                    <div>Run ID: <span className="text-white">{report.candidate_run_id}</span></div>
                    <div>Agent: <span className="text-white">{report.agent_name}</span></div>
                  </div>
                </div>
              </div>

              {/* Metric Deltas */}
              <div className="p-3 rounded bg-surface border border-surface-border space-y-3 font-mono text-xs">
                <div className="text-[10px] text-slate-400 uppercase font-semibold">Observed Metric Deltas</div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-2 rounded bg-surface-elevated border border-surface-border">
                    <span className="text-[10px] text-slate-500 block">Pass Rate Delta</span>
                    <span className={`text-sm font-bold ${report.pass_rate_delta < 0 ? "text-rose-400" : "text-emerald-400"}`}>
                      {report.pass_rate_delta > 0 ? `+${report.pass_rate_delta}%` : `${report.pass_rate_delta}%`}
                    </span>
                  </div>

                  <div className="p-2 rounded bg-surface-elevated border border-surface-border">
                    <span className="text-[10px] text-slate-500 block">Score Delta</span>
                    <span className={`text-sm font-bold ${report.score_delta < 0 ? "text-rose-400" : "text-emerald-400"}`}>
                      {report.score_delta > 0 ? `+${report.score_delta}` : `${report.score_delta}`}
                    </span>
                  </div>

                  <div className="p-2 rounded bg-surface-elevated border border-surface-border">
                    <span className="text-[10px] text-slate-500 block">Latency Delta</span>
                    <span className={`text-sm font-bold ${report.latency_delta_ms > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                      {report.latency_delta_ms > 0 ? `+${report.latency_delta_ms}ms` : `${report.latency_delta_ms}ms`}
                    </span>
                  </div>

                  <div className="p-2 rounded bg-surface-elevated border border-surface-border">
                    <span className="text-[10px] text-slate-500 block">Cost Delta</span>
                    <span className={`text-sm font-bold ${report.cost_delta_usd > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {report.cost_delta_usd > 0 ? `+$${report.cost_delta_usd}` : `-$${Math.abs(report.cost_delta_usd)}`}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
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
