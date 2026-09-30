"use client";

import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { Sidebar, TabType } from "../components/Sidebar";
import { TraceWaterfall } from "../components/TraceWaterfall";
import { ReliabilityReportView } from "../components/ReliabilityReportView";
import { ScenarioRunnerModal } from "../components/ScenarioRunnerModal";
import { RegressionComparisonModal } from "../components/RegressionComparisonModal";
import { api } from "../lib/api";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock,
  Coins,
  Cpu,
  ExternalLink,
  GitBranch,
  Layers,
  Play,
  RefreshCw,
  Repeat,
  ShieldAlert,
  Sliders,
  TrendingDown,
  TrendingUp,
  X
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar
} from "recharts";

export default function Dashboard() {
  const [currentTab, setCurrentTab] = useState<TabType>("overview");
  const [loading, setLoading] = useState(true);

  // Core Data States
  const [runs, setRuns] = useState<any[]>([]);
  const [traces, setTraces] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [findings, setFindings] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [violations, setViolations] = useState<any[]>([]);
  const [evalRuns, setEvalRuns] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [pricing, setPricing] = useState<any[]>([]);
  const [timeseries, setTimeseries] = useState<any[]>([]);
  const [observability, setObservability] = useState<any>(null);

  // Active Selections
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [waterfallData, setWaterfallData] = useState<any>(null);
  const [selectedRunReport, setSelectedRunReport] = useState<any>(null);

  // Modals
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);
  const [isRegressionModalOpen, setIsRegressionModalOpen] = useState(false);

  // Filter states
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [
        runsRes,
        tracesRes,
        agentsRes,
        findingsRes,
        policiesRes,
        violationsRes,
        evalRunsRes,
        modelsRes,
        pricingRes,
        timeseriesRes,
        obsRes
      ] = await Promise.all([
        api.getRuns().catch(() => ({ runs: [] })),
        api.getTraces().catch(() => ({ traces: [] })),
        api.getAgents().catch(() => ({ agents: [] })),
        api.getFindings().catch(() => ({ findings: [] })),
        api.getPolicies().catch(() => ({ policies: [] })),
        api.getPolicyViolations().catch(() => ({ violations: [] })),
        api.getEvalRuns().catch(() => ({ runs: [] })),
        api.getModelComparisons().catch(() => ({ models: [] })),
        api.getPricing().catch(() => ({ pricing: [] })),
        api.getTimeseriesMetrics().catch(() => ({ points: [] })),
        api.getSystemObservability().catch(() => null)
      ]);

      setRuns(runsRes.runs || []);
      setTraces(tracesRes.traces || []);
      setAgents(agentsRes.agents || []);
      setFindings(findingsRes.findings || []);
      setPolicies(policiesRes.policies || []);
      setViolations(violationsRes.violations || []);
      setEvalRuns(evalRunsRes.runs || []);
      setModels(modelsRes.models || []);
      setPricing(pricingRes.pricing || []);
      setTimeseries(timeseriesRes.points || []);
      setObservability(obsRes);

      // Auto-select first trace if available
      if (tracesRes.traces && tracesRes.traces.length > 0 && !selectedTraceId) {
        selectTrace(tracesRes.traces[0].trace_id, tracesRes.traces[0].run_id);
      }
    } catch (e) {
      console.error("Error loading dashboard data:", e);
    } finally {
      setLoading(false);
    }
  };

  const selectTrace = async (traceId: string, runId?: string) => {
    setSelectedTraceId(traceId);
    try {
      const [wf, rep] = await Promise.all([
        api.getTraceWaterfall(traceId),
        runId ? api.getRunReport(runId) : Promise.resolve(null)
      ]);
      setWaterfallData(wf);
      setSelectedRunReport(rep);
    } catch (e) {
      console.error("Error loading trace detail:", e);
    }
  };

  // High-level aggregates
  const totalRuns = runs.length;
  const failedRuns = runs.filter((r) => r.status !== "SUCCESS").length;
  const failureRate = totalRuns > 0 ? ((failedRuns / totalRuns) * 100).toFixed(1) : "0.0";
  const totalCost = runs.reduce((acc, r) => acc + (r.cost_usd || 0), 0);
  const totalTokens = runs.reduce((acc, r) => acc + (r.total_tokens || 0), 0);
  const p95Latency =
    runs.length > 0
      ? [...runs]
          .sort((a, b) => a.duration_ms - b.duration_ms)[Math.floor(runs.length * 0.95)]
          ?.duration_ms?.toFixed(0) || "0"
      : "0";

  return (
    <div className="min-h-screen bg-background flex flex-col font-sans">
      <Navbar
        onOpenDemoModal={() => setIsScenarioModalOpen(true)}
        onRefreshData={loadAllData}
      />

      <div className="flex-1 flex">
        <Sidebar
          currentTab={currentTab}
          onSelectTab={setCurrentTab}
          violationsCount={violations.length}
          findingsCount={findings.length}
        />

        <main className="flex-1 p-6 overflow-y-auto max-h-[calc(100vh-3.5rem)]">
          {/* ===================== TAB 1: OVERVIEW ===================== */}
          {currentTab === "overview" && (
            <div className="space-y-6">
              {/* Aggregates Header */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Total Runs</span>
                  <div className="mt-1 font-mono text-2xl font-bold text-white">{totalRuns}</div>
                  <span className="text-[10px] text-slate-500 font-mono">Captured telemetry</span>
                </div>

                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Failure Rate</span>
                  <div className={`mt-1 font-mono text-2xl font-bold ${Number(failureRate) > 10 ? "text-rose-400" : "text-emerald-400"}`}>
                    {failureRate}%
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">{failedRuns} failed runs</span>
                </div>

                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">p95 Latency</span>
                  <div className="mt-1 font-mono text-2xl font-bold text-amber-400">{p95Latency} ms</div>
                  <span className="text-[10px] text-slate-500 font-mono">95th percentile</span>
                </div>

                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Total Spend</span>
                  <div className="mt-1 font-mono text-2xl font-bold text-emerald-400">
                    ${totalCost.toFixed(4)}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Token accounting</span>
                </div>

                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Total Tokens</span>
                  <div className="mt-1 font-mono text-2xl font-bold text-cyan-400">
                    {totalTokens.toLocaleString()}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Prompt + Completion</span>
                </div>

                <div className="p-3.5 rounded-lg border border-surface-border bg-surface">
                  <span className="text-[11px] font-mono text-slate-500 uppercase block">Policy Violations</span>
                  <div className={`mt-1 font-mono text-2xl font-bold ${violations.length > 0 ? "text-rose-400" : "text-slate-300"}`}>
                    {violations.length}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Active thresholds</span>
                </div>
              </div>

              {/* Time Series Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-white font-semibold uppercase">Operational Latency (p95 ms)</span>
                    <span className="text-slate-500">Hourly Aggregation</span>
                  </div>
                  <div className="h-44 w-full">
                    {timeseries.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={timeseries}>
                          <defs>
                            <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#06B6D4" stopOpacity={0.0} />
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="time_bucket" stroke="#64748B" fontSize={10} />
                          <YAxis stroke="#64748B" fontSize={10} />
                          <Tooltip
                            contentStyle={{ background: "#0F172A", border: "1px solid #334155", fontSize: 11 }}
                          />
                          <Area type="monotone" dataKey="p95_latency" stroke="#06B6D4" fill="url(#latencyGradient)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                        No time-series telemetry recorded yet.
                      </div>
                    )}
                  </div>
                </div>

                <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-white font-semibold uppercase">Token Usage Over Time</span>
                    <span className="text-slate-500">Hourly Aggregation</span>
                  </div>
                  <div className="h-44 w-full">
                    {timeseries.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={timeseries}>
                          <XAxis dataKey="time_bucket" stroke="#64748B" fontSize={10} />
                          <YAxis stroke="#64748B" fontSize={10} />
                          <Tooltip
                            contentStyle={{ background: "#0F172A", border: "1px solid #334155", fontSize: 11 }}
                          />
                          <Bar dataKey="total_tokens" fill="#6366F1" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-full flex items-center justify-center text-xs text-slate-500 font-mono">
                        No token telemetry recorded yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Recent Runs Table */}
              <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <GitBranch className="w-4 h-4 text-accent-cyan" />
                    <span className="font-semibold text-sm text-white font-mono uppercase">
                      Recent Ingested Runs & Telemetry
                    </span>
                  </div>
                  <button
                    onClick={() => setCurrentTab("traces")}
                    className="text-xs text-accent-cyan hover:underline font-mono"
                  >
                    View All Traces →
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-surface-elevated text-slate-400 border-b border-surface-border uppercase text-[10px]">
                      <tr>
                        <th className="py-2.5 px-3">Run ID</th>
                        <th className="py-2.5 px-3">Agent</th>
                        <th className="py-2.5 px-3">Version</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Duration</th>
                        <th className="py-2.5 px-3">Tokens</th>
                        <th className="py-2.5 px-3">Cost</th>
                        <th className="py-2.5 px-3">Retries</th>
                        <th className="py-2.5 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border/50 text-slate-300">
                      {runs.slice(0, 8).map((r) => (
                        <tr
                          key={r.run_id}
                          className="hover:bg-surface-elevated/70 transition cursor-pointer"
                          onClick={() => {
                            selectTrace(r.trace_id, r.run_id);
                            setCurrentTab("traces");
                          }}
                        >
                          <td className="py-2.5 px-3 text-white font-semibold truncate max-w-[140px]">{r.run_id}</td>
                          <td className="py-2.5 px-3">{r.agent_name}</td>
                          <td className="py-2.5 px-3 text-slate-400">v{r.agent_version}</td>
                          <td className="py-2.5 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${
                                r.status === "SUCCESS"
                                  ? "bg-emerald-950/70 text-emerald-400 border-emerald-800"
                                  : r.status === "VIOLATION"
                                  ? "bg-amber-950/70 text-amber-400 border-amber-800"
                                  : "bg-rose-950/70 text-rose-400 border-rose-800"
                              }`}
                            >
                              {r.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-200">{(r.duration_ms / 1000.0).toFixed(2)}s</td>
                          <td className="py-2.5 px-3 text-cyan-400">{r.total_tokens.toLocaleString()}</td>
                          <td className="py-2.5 px-3 text-emerald-400">${(r.cost_usd || 0).toFixed(4)}</td>
                          <td className="py-2.5 px-3">{r.retry_count}</td>
                          <td className="py-2.5 px-3 text-right">
                            <span className="text-accent-cyan hover:underline text-[11px]">Inspect Waterfall →</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ===================== TAB 2: TRACES & WATERFALL ===================== */}
          {currentTab === "traces" && (
            <div className="space-y-6">
              {/* Trace Selector & Filters */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-surface-border bg-surface">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono text-slate-400">Trace:</span>
                  <select
                    value={selectedTraceId || ""}
                    onChange={(e) => {
                      const t = traces.find((tr) => tr.trace_id === e.target.value);
                      if (t) selectTrace(t.trace_id, t.run_id);
                    }}
                    className="bg-surface-elevated border border-surface-border rounded text-xs font-mono text-white px-2.5 py-1.5 focus:outline-none focus:border-accent-cyan"
                  >
                    {traces.map((tr) => (
                      <option key={tr.trace_id} value={tr.trace_id}>
                        {tr.agent_name} ({tr.status}) — {(tr.duration_ms / 1000.0).toFixed(2)}s — {tr.trace_id.slice(0, 16)}...
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
                  <span>Selected Run ID:</span>
                  <span className="text-accent-cyan font-bold">{selectedRunReport?.run_id || "N/A"}</span>
                  <button
                    onClick={() => setIsScenarioModalOpen(true)}
                    className="px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition"
                  >
                    + Run New Scenario
                  </button>
                </div>
              </div>

              {/* Waterfall Hierarchy Visualization */}
              {waterfallData ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                      <GitBranch className="w-4 h-4 text-accent-cyan" />
                      <span>Trace Execution Waterfall</span>
                    </h3>
                    <span className="text-xs text-slate-400 font-mono">
                      Total Duration: <strong className="text-emerald-400">{waterfallData.total_duration_ms.toFixed(1)}ms</strong>
                    </span>
                  </div>

                  <TraceWaterfall waterfallData={waterfallData} />
                </div>
              ) : (
                <div className="p-12 text-center text-xs text-slate-500 font-mono">
                  Loading trace waterfall hierarchy...
                </div>
              )}

              {/* Reliability Analysis for Selected Run */}
              {selectedRunReport && (
                <div className="pt-4 border-t border-surface-border">
                  <h3 className="font-semibold text-sm text-white font-mono uppercase mb-4 flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-accent-cyan" />
                    <span>Run Reliability & Diagnostics Report</span>
                  </h3>
                  <ReliabilityReportView report={selectedRunReport} />
                </div>
              )}
            </div>
          )}

          {/* ===================== TAB 3: AGENTS HEALTH ===================== */}
          {currentTab === "agents" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                    <Bot className="w-4 h-4 text-accent-cyan" />
                    <span>Monitored Agents Operational Health</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5 font-mono">
                    Real aggregation calculated across actual telemetry traces in DuckDB
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {agents.map((ag) => (
                  <div
                    key={ag.name}
                    className="p-4 rounded-lg border border-surface-border bg-surface space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        <Bot className="w-5 h-5 text-accent-cyan" />
                        <div>
                          <h4 className="font-semibold text-sm text-white">{ag.name}</h4>
                          <span className="text-[10px] text-slate-500 font-mono">{ag.id}</span>
                        </div>
                      </div>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-bold border ${
                          ag.error_rate > 10
                            ? "bg-rose-950/70 text-rose-400 border-rose-800"
                            : "bg-emerald-950/70 text-emerald-400 border-emerald-800"
                        }`}
                      >
                        {ag.error_rate > 10 ? "Degraded" : "Healthy"}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed min-h-[32px]">
                      {ag.description || `Autonomous agent '${ag.name}'`}
                    </p>

                    <div className="grid grid-cols-2 gap-2 bg-surface-elevated/70 p-2.5 rounded border border-surface-border font-mono text-xs">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Total Runs</span>
                        <span className="text-white font-bold">{ag.total_runs}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Success Rate</span>
                        <span className="text-emerald-400 font-bold">{ag.success_rate || 100}%</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">p95 Latency</span>
                        <span className="text-amber-400 font-bold">{ag.p95_duration_ms || 0} ms</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Avg Cost</span>
                        <span className="text-cyan-400 font-bold">${(ag.avg_cost_usd || 0).toFixed(4)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ===================== TAB 4: RELIABILITY FINDINGS ===================== */}
          {currentTab === "findings" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 text-accent-cyan" />
                    <span>Reliability Findings Repository ({findings.length})</span>
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    Deterministic findings computed strictly from span latency contributions, tool errors, loops, and context growth.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {findings.map((f) => (
                  <div
                    key={f.id}
                    className="p-4 rounded-lg border border-surface-border bg-surface space-y-2.5 hover:border-slate-600 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded border text-slate-300 bg-surface-elevated border-surface-border">
                        {f.finding_type}
                      </span>
                      <span
                        className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                          f.severity === "CRITICAL"
                            ? "bg-rose-950 text-rose-300 border-rose-800"
                            : f.severity === "HIGH"
                            ? "bg-orange-950 text-orange-300 border-orange-800"
                            : "bg-amber-950 text-amber-300 border-amber-800"
                        }`}
                      >
                        {f.severity}
                      </span>
                    </div>

                    <h4 className="font-semibold text-sm text-white">{f.title}</h4>
                    <p className="text-xs text-slate-300 leading-relaxed">{f.description}</p>

                    <div className="flex items-center justify-between text-[11px] font-mono bg-surface-elevated/70 p-2 rounded border border-surface-border">
                      <span className="text-slate-400">Observed Metric:</span>
                      <span className="text-accent-cyan font-bold">{f.observed_metric || "N/A"}</span>
                    </div>

                    {f.suggested_actions && f.suggested_actions.length > 0 && (
                      <div className="pt-2 border-t border-surface-border/60">
                        <div className="text-[10px] text-slate-500 font-mono uppercase mb-1">
                          Actionable Investigation Area
                        </div>
                        <ul className="text-xs text-slate-300 space-y-1">
                          {f.suggested_actions.map((act: string, idx: number) => (
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
            </div>
          )}

          {/* ===================== TAB 5: EVALUATIONS & REGRESSIONS ===================== */}
          {currentTab === "evaluations" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-accent-cyan" />
                    <span>Evaluation Runs & Regression Testing</span>
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    Benchmark test cases evaluating schema correctness, tool selection, citations, and response bounds.
                  </p>
                </div>

                <button
                  onClick={() => setIsRegressionModalOpen(true)}
                  className="flex items-center space-x-1.5 text-xs font-mono font-medium bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded transition"
                >
                  <span>Compare Versions A vs B</span>
                </button>
              </div>

              {/* Evaluation Runs Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {evalRuns.map((er) => (
                  <div
                    key={er.id}
                    className="p-4 rounded-lg border border-surface-border bg-surface space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-[10px] text-slate-500 font-mono uppercase">{er.dataset_name}</span>
                        <h4 className="font-semibold text-sm text-white">
                          {er.agent_name} <span className="text-accent-cyan font-mono">(v{er.agent_version})</span>
                        </h4>
                      </div>
                      <span
                        className={`font-mono text-xs font-bold px-2 py-0.5 rounded border uppercase ${
                          er.pass_rate >= 90
                            ? "bg-emerald-950/70 text-emerald-400 border-emerald-800"
                            : "bg-rose-950/70 text-rose-400 border-rose-800"
                        }`}
                      >
                        {er.pass_rate}% Pass Rate
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 bg-surface-elevated/70 p-2.5 rounded border border-surface-border font-mono text-xs">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Passed Cases</span>
                        <span className="text-white font-bold">{er.passed_cases} / {er.total_cases}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Avg Latency</span>
                        <span className="text-amber-400 font-bold">{er.average_latency_ms} ms</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Total Cost</span>
                        <span className="text-emerald-400 font-bold">${er.total_cost_usd}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ===================== TAB 6: POLICIES & VIOLATIONS ===================== */}
          {currentTab === "policies" && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                    <ShieldAlert className="w-4 h-4 text-accent-cyan" />
                    <span>Reliability Policies & Thresholds</span>
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    Deterministic guardrails marking runs violating latency, cost, retry, or context limits.
                  </p>
                </div>
              </div>

              {/* Policy List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {policies.map((p) => (
                  <div
                    key={p.id}
                    className="p-4 rounded-lg border border-surface-border bg-surface flex items-start justify-between space-x-4"
                  >
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-white">{p.name}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-elevated border border-surface-border text-slate-400">
                          {p.rule_type}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">{p.description}</p>
                      <div className="mt-2 text-xs font-mono text-slate-300">
                        Threshold: <strong className="text-accent-cyan">{p.threshold} {p.unit}</strong>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                        p.violation_count > 0 ? "bg-rose-950 text-rose-400 border-rose-800" : "bg-emerald-950 text-emerald-400 border-emerald-800"
                      }`}>
                        {p.violation_count} Violations
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Violations Log */}
              {violations.length > 0 && (
                <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-3">
                  <h4 className="font-semibold text-xs text-white font-mono uppercase">Recent Violations Log</h4>
                  <div className="divide-y divide-surface-border/50 text-xs font-mono">
                    {violations.map((v) => (
                      <div key={v.id} className="py-2.5 flex items-center justify-between">
                        <div className="space-y-0.5">
                          <span className="text-rose-400 font-semibold">{v.message}</span>
                          <div className="text-[11px] text-slate-500">
                            Run: {v.run_id} | Observed: {v.observed_value} {v.unit} (Limit: {v.threshold_value})
                          </div>
                        </div>
                        <span className="text-[10px] text-slate-500">{new Date(v.created_at).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ===================== TAB 7: MODELS & COSTS ===================== */}
          {currentTab === "models" && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                  <Coins className="w-4 h-4 text-accent-cyan" />
                  <span>Model Comparison & Cost Accounting</span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Values calculated strictly from actual recorded model spans. No overall winner declared; evidence presented directly.
                </p>
              </div>

              {/* Model Comparison Table */}
              <div className="overflow-x-auto rounded-lg border border-surface-border bg-surface">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-surface-elevated text-slate-400 border-b border-surface-border uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Model</th>
                      <th className="py-2.5 px-3">Provider</th>
                      <th className="py-2.5 px-3">Call Count</th>
                      <th className="py-2.5 px-3">Avg Latency</th>
                      <th className="py-2.5 px-3">p95 Latency</th>
                      <th className="py-2.5 px-3">Avg In Tokens</th>
                      <th className="py-2.5 px-3">Avg Out Tokens</th>
                      <th className="py-2.5 px-3">Total Cost</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border/50 text-slate-300">
                    {models.map((m) => (
                      <tr key={m.model_name} className="hover:bg-surface-elevated/70 transition">
                        <td className="py-2.5 px-3 font-semibold text-white">{m.model_name}</td>
                        <td className="py-2.5 px-3 text-slate-400">{m.provider}</td>
                        <td className="py-2.5 px-3">{m.call_count}</td>
                        <td className="py-2.5 px-3">{m.avg_latency_ms} ms</td>
                        <td className="py-2.5 px-3 text-amber-400">{m.p95_latency_ms} ms</td>
                        <td className="py-2.5 px-3">{m.avg_input_tokens}</td>
                        <td className="py-2.5 px-3">{m.avg_output_tokens}</td>
                        <td className="py-2.5 px-3 text-emerald-400 font-bold">${m.total_cost_usd.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pricing Registry Table */}
              <div className="p-4 rounded-lg border border-surface-border bg-surface space-y-3">
                <h4 className="font-semibold text-xs text-white font-mono uppercase">Configured Model Pricing Table ($ / 1M Tokens)</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-surface-elevated text-slate-400 border-b border-surface-border uppercase text-[10px]">
                      <tr>
                        <th className="py-2 px-3">Model</th>
                        <th className="py-2 px-3">Provider</th>
                        <th className="py-2 px-3">Input Price / 1M</th>
                        <th className="py-2 px-3">Output Price / 1M</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border/50 text-slate-300">
                      {pricing.map((pr) => (
                        <tr key={pr.model}>
                          <td className="py-2 px-3 text-white">{pr.model}</td>
                          <td className="py-2 px-3 text-slate-400">{pr.provider}</td>
                          <td className="py-2 px-3 text-emerald-400">${pr.input_price_per_million.toFixed(2)}</td>
                          <td className="py-2 px-3 text-emerald-400">${pr.output_price_per_million.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ===================== TAB 8: PLATFORM OBSERVABILITY ===================== */}
          {currentTab === "system" && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold text-sm text-white font-mono uppercase flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-accent-cyan" />
                  <span>Platform Self-Observability & Telemetry Performance</span>
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Recursive telemetry measuring the latency, throughput, and reliability of the Agent Reliability Platform itself.
                </p>
              </div>

              {observability && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono text-xs">
                  <div className="p-4 rounded-lg border border-surface-border bg-surface">
                    <span className="text-slate-500 uppercase text-[10px] block">Ingestion Throughput</span>
                    <span className="text-2xl font-bold text-white block mt-1">
                      {observability.ingestion_throughput_spans_per_sec} spans/s
                    </span>
                    <span className="text-[10px] text-slate-500">Total: {observability.total_spans_ingested} spans</span>
                  </div>

                  <div className="p-4 rounded-lg border border-surface-border bg-surface">
                    <span className="text-slate-500 uppercase text-[10px] block">Ingestion Latency (p95)</span>
                    <span className="text-2xl font-bold text-emerald-400 block mt-1">
                      {observability.ingestion_latency.p95_ms} ms
                    </span>
                    <span className="text-[10px] text-slate-500">Avg: {observability.ingestion_latency.avg_ms} ms</span>
                  </div>

                  <div className="p-4 rounded-lg border border-surface-border bg-surface">
                    <span className="text-slate-500 uppercase text-[10px] block">Dashboard Query (p95)</span>
                    <span className="text-2xl font-bold text-cyan-400 block mt-1">
                      {observability.query_latency.p95_ms} ms
                    </span>
                    <span className="text-[10px] text-slate-500">Total queries: {observability.total_queries_served}</span>
                  </div>

                  <div className="p-4 rounded-lg border border-surface-border bg-surface">
                    <span className="text-slate-500 uppercase text-[10px] block">System Uptime</span>
                    <span className="text-2xl font-bold text-slate-200 block mt-1">
                      {observability.uptime_seconds.toFixed(0)} s
                    </span>
                    <span className="text-[10px] text-emerald-400 font-bold uppercase">Status: {observability.status}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Scenario Runner Modal */}
      <ScenarioRunnerModal
        isOpen={isScenarioModalOpen}
        onClose={() => setIsScenarioModalOpen(false)}
        onScenarioCompleted={loadAllData}
      />

      {/* Regression Comparison Modal */}
      <RegressionComparisonModal
        isOpen={isRegressionModalOpen}
        onClose={() => setIsRegressionModalOpen(false)}
      />
    </div>
  );
}
