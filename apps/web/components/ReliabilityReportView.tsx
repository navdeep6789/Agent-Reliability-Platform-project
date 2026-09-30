"use client";

import React from "react";
import {
  AlertTriangle,
  Clock,
  Coins,
  Cpu,
  Layers,
  Repeat,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  HelpCircle
} from "lucide-react";

interface ReliabilityFinding {
  id: string;
  finding_type: string;
  severity: "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  title: string;
  description: string;
  target_entity?: string;
  observed_metric?: string;
  trace_contribution_percent?: number;
  details?: Record<string, any>;
  suggested_actions?: string[];
}

interface ReliabilityReportViewProps {
  report: {
    run_id: string;
    trace_id: string;
    agent_name: string;
    total_duration_ms: number;
    total_cost_usd?: number;
    total_tokens: number;
    error_count: number;
    retry_count: number;
    findings: ReliabilityFinding[];
    retries?: any[];
    context_growth?: any;
    policy_violations?: any[];
    suggested_investigations?: string[];
  };
}

export function ReliabilityReportView({ report }: ReliabilityReportViewProps) {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-950/80 text-rose-300 border-rose-800/80";
      case "HIGH":
        return "bg-orange-950/80 text-orange-300 border-orange-800/80";
      case "MEDIUM":
        return "bg-amber-950/80 text-amber-300 border-amber-800/80";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-6">
      {/* Run Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <Clock className="w-3.5 h-3.5" />
            <span>Total Latency</span>
          </div>
          <div className="mt-1 font-mono text-lg font-bold text-white">
            {(report.total_duration_ms / 1000.0).toFixed(2)}s
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            {report.total_duration_ms.toFixed(0)} ms
          </div>
        </div>

        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <Coins className="w-3.5 h-3.5" />
            <span>Est. Cost</span>
          </div>
          <div className="mt-1 font-mono text-lg font-bold text-emerald-400">
            {report.total_cost_usd !== undefined ? `$${report.total_cost_usd.toFixed(4)}` : "N/A"}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Actual token spend
          </div>
        </div>

        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <Cpu className="w-3.5 h-3.5" />
            <span>Total Tokens</span>
          </div>
          <div className="mt-1 font-mono text-lg font-bold text-cyan-400">
            {report.total_tokens.toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            In + Out tokens
          </div>
        </div>

        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <Repeat className="w-3.5 h-3.5" />
            <span>Retries</span>
          </div>
          <div className={`mt-1 font-mono text-lg font-bold ${report.retry_count > 0 ? "text-amber-400" : "text-slate-300"}`}>
            {report.retry_count}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Tool re-executions
          </div>
        </div>

        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Errors</span>
          </div>
          <div className={`mt-1 font-mono text-lg font-bold ${report.error_count > 0 ? "text-rose-400" : "text-slate-300"}`}>
            {report.error_count}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Span failures
          </div>
        </div>

        <div className="p-3 rounded-lg border border-surface-border bg-surface">
          <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-mono uppercase">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Violations</span>
          </div>
          <div className={`mt-1 font-mono text-lg font-bold ${report.policy_violations && report.policy_violations.length > 0 ? "text-rose-400" : "text-slate-300"}`}>
            {report.policy_violations?.length || 0}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Policies triggered
          </div>
        </div>
      </div>

      {/* Policy Violations Alert Banner */}
      {report.policy_violations && report.policy_violations.length > 0 && (
        <div className="border border-rose-900/60 bg-rose-950/20 rounded-lg p-4 space-y-2">
          <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs font-mono uppercase">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>Deterministic Policy Violations Detected ({report.policy_violations.length})</span>
          </div>
          <div className="space-y-1.5">
            {report.policy_violations.map((v, i) => (
              <div key={i} className="flex items-start justify-between text-xs font-mono bg-rose-950/40 p-2 rounded border border-rose-900/40">
                <span className="text-rose-200">{v.message}</span>
                <span className="text-[10px] uppercase font-bold text-rose-400 border border-rose-700/60 px-1.5 py-0.5 rounded">
                  {v.rule_type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reliability Findings */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-accent-cyan" />
            <span className="font-semibold text-sm text-white font-mono uppercase">
              Reliability Findings ({report.findings.length})
            </span>
          </div>
          <span className="text-xs text-slate-500 font-mono">
            Calculated from actual span metrics
          </span>
        </div>

        {report.findings.length === 0 ? (
          <div className="p-6 rounded-lg border border-surface-border bg-surface text-center text-xs text-slate-400 font-mono">
            No reliability defects detected. All span execution timings and parameters operated within nominal bounds.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {report.findings.map((f) => (
              <div
                key={f.id}
                className="p-4 rounded-lg border border-surface-border bg-surface hover:border-slate-600 transition flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-start justify-between">
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded border uppercase text-slate-300 bg-surface-elevated border-surface-border">
                      {f.finding_type}
                    </span>
                    <span className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getSeverityBadge(f.severity)}`}>
                      {f.severity}
                    </span>
                  </div>

                  <h4 className="mt-2.5 font-semibold text-sm text-white">
                    {f.title}
                  </h4>
                  <p className="mt-1 text-xs text-slate-300 leading-relaxed">
                    {f.description}
                  </p>

                  {/* Highlights / Contribution */}
                  {f.trace_contribution_percent !== undefined && (
                    <div className="mt-3 bg-surface-elevated/70 p-2 rounded border border-surface-border flex items-center justify-between font-mono text-xs">
                      <span className="text-slate-400">Trace Contribution:</span>
                      <span className="text-accent-cyan font-bold">{f.trace_contribution_percent}%</span>
                    </div>
                  )}
                </div>

                {/* Suggested Investigation Actions */}
                {f.suggested_actions && f.suggested_actions.length > 0 && (
                  <div className="pt-2 border-t border-surface-border/60">
                    <div className="text-[10px] text-slate-500 font-mono uppercase mb-1">
                      Investigation Guidance
                    </div>
                    <ul className="text-xs text-slate-300 space-y-1">
                      {f.suggested_actions.map((act, idx) => (
                        <li key={idx} className="flex items-start space-x-1.5">
                          <ArrowRight className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />
                          <span>{act}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Context Growth Analysis Card (if abnormal growth detected) */}
      {report.context_growth && (
        <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-3">
          <div className="flex items-center space-x-2 text-cyan-400 text-xs font-mono uppercase font-semibold">
            <TrendingUp className="w-4 h-4" />
            <span>Context Growth Breakdown (+{report.context_growth.growth_percent}%)</span>
          </div>
          <p className="text-xs text-slate-300">
            Initial prompt context: <strong className="text-white font-mono">{report.context_growth.initial_tokens.toLocaleString()}</strong> tokens → Peak invocation: <strong className="text-rose-400 font-mono">{report.context_growth.peak_tokens.toLocaleString()}</strong> tokens ({report.context_growth.growth_multiplier}x inflation).
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
            {report.context_growth.steps.map((st: any, idx: number) => (
              <div key={idx} className="p-2 rounded bg-surface-elevated border border-surface-border">
                <span className="text-[10px] text-slate-500 block">Call #{st.call_index}</span>
                <span className="text-white font-bold">{st.input_tokens.toLocaleString()}</span>
                <span className="text-[10px] text-accent-cyan ml-1">({st.delta_percent > 0 ? `+${st.delta_percent}%` : "0%"})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Investigation Areas Summary */}
      {report.suggested_investigations && report.suggested_investigations.length > 0 && (
        <div className="p-4 rounded-lg border border-surface-border bg-surface-elevated/40 space-y-2">
          <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-slate-300 uppercase">
            <HelpCircle className="w-4 h-4 text-cyan-400" />
            <span>Summary of Key Investigation Areas</span>
          </div>
          <ul className="text-xs text-slate-300 space-y-1 font-mono">
            {report.suggested_investigations.map((item, idx) => (
              <li key={idx} className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
