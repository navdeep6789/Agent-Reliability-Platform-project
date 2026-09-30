"use client";

import React, { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Clock,
  Terminal,
  Cpu,
  Wrench,
  Search,
  AlertCircle,
  CheckCircle2,
  X
} from "lucide-react";

export interface WaterfallSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  span_type: string;
  start_offset_ms: number;
  duration_ms: number;
  contribution_percent: number;
  status: string;
  status_message?: string;
  attributes: Record<string, any>;
  children: WaterfallSpan[];
}

interface TraceWaterfallProps {
  waterfallData: {
    trace_id: string;
    total_duration_ms: number;
    root_spans: WaterfallSpan[];
  };
}

export function TraceWaterfall({ waterfallData }: TraceWaterfallProps) {
  const [selectedSpan, setSelectedSpan] = useState<WaterfallSpan | null>(null);
  const [collapsedSpans, setCollapsedSpans] = useState<Record<string, boolean>>({});

  const totalDuration = waterfallData.total_duration_ms || 1.0;

  const toggleCollapse = (spanId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedSpans((prev) => ({ ...prev, [spanId]: !prev[spanId] }));
  };

  const getSpanColor = (type: string, status: string) => {
    if (status === "error") return "bg-rose-500/80 border-rose-400";
    switch (type) {
      case "agent":
        return "bg-indigo-600/80 border-indigo-400";
      case "llm":
        return "bg-cyan-500/80 border-cyan-400";
      case "tool":
        return "bg-amber-500/80 border-amber-400";
      case "retrieval":
        return "bg-emerald-500/80 border-emerald-400";
      default:
        return "bg-slate-500/80 border-slate-400";
    }
  };

  const getSpanIcon = (type: string) => {
    switch (type) {
      case "llm":
        return <Cpu className="w-3.5 h-3.5 text-cyan-400" />;
      case "tool":
        return <Wrench className="w-3.5 h-3.5 text-amber-400" />;
      case "retrieval":
        return <Search className="w-3.5 h-3.5 text-emerald-400" />;
      default:
        return <Terminal className="w-3.5 h-3.5 text-indigo-400" />;
    }
  };

  const renderSpanRow = (span: WaterfallSpan, depth: number = 0) => {
    const isCollapsed = collapsedSpans[span.span_id];
    const hasChildren = span.children && span.children.length > 0;
    const isSelected = selectedSpan?.span_id === span.span_id;

    // Calculate proportional waterfall offsets
    const leftPercent = Math.min(Math.max((span.start_offset_ms / totalDuration) * 100.0, 0), 98);
    const widthPercent = Math.max(Math.min((span.duration_ms / totalDuration) * 100.0, 100 - leftPercent), 1.5);

    return (
      <React.Fragment key={span.span_id}>
        <div
          onClick={() => setSelectedSpan(span)}
          className={`flex items-center text-xs py-2 px-3 border-b border-surface-border cursor-pointer transition select-none hover:bg-surface-elevated/80 ${
            isSelected ? "bg-surface-elevated border-l-2 border-l-accent-cyan" : ""
          }`}
        >
          {/* Left: Tree Label Column */}
          <div className="w-80 shrink-0 flex items-center space-x-1.5" style={{ paddingLeft: `${depth * 18}px` }}>
            {hasChildren ? (
              <button
                onClick={(e) => toggleCollapse(span.span_id, e)}
                className="p-0.5 text-slate-400 hover:text-white"
              >
                {isCollapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            ) : (
              <span className="w-3.5" />
            )}

            {getSpanIcon(span.span_type)}

            <span className="font-mono text-slate-200 truncate" title={span.name}>
              {span.name}
            </span>

            {span.status === "error" && (
              <span title={span.status_message || "Error"}>
                <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              </span>
            )}
          </div>

          {/* Middle: Duration & Contribution Metric */}
          <div className="w-32 shrink-0 font-mono text-[11px] text-slate-400 text-right pr-4">
            <span className="text-slate-200 font-semibold">{span.duration_ms.toFixed(1)}ms</span>
            <span className="ml-1.5 text-slate-500">({span.contribution_percent}%)</span>
          </div>

          {/* Right: Waterfall Visual Bar */}
          <div className="flex-1 relative h-5 bg-surface-elevated/40 rounded overflow-hidden">
            <div
              className={`absolute top-1 bottom-1 rounded border shadow-sm transition-all ${getSpanColor(
                span.span_type,
                span.status
              )}`}
              style={{
                left: `${leftPercent}%`,
                width: `${widthPercent}%`
              }}
              title={`${span.name}: ${span.duration_ms.toFixed(1)}ms (${span.contribution_percent}% of total)`}
            />
          </div>
        </div>

        {/* Nested Children */}
        {!isCollapsed && hasChildren && span.children.map((child) => renderSpanRow(child, depth + 1))}
      </React.Fragment>
    );
  };

  return (
    <div className="flex border border-surface-border rounded-lg bg-surface overflow-hidden min-h-[480px]">
      {/* Waterfall Table & Timeline */}
      <div className="flex-1 overflow-x-auto flex flex-col">
        {/* Header timeline */}
        <div className="flex items-center text-[11px] font-mono uppercase tracking-wider text-slate-400 py-2.5 px-3 border-b border-surface-border bg-surface-elevated/50">
          <div className="w-80 shrink-0">Span Hierarchy</div>
          <div className="w-32 shrink-0 text-right pr-4">Duration (%)</div>
          <div className="flex-1 flex justify-between px-1 text-slate-500">
            <span>0ms</span>
            <span>{(totalDuration * 0.25).toFixed(0)}ms</span>
            <span>{(totalDuration * 0.5).toFixed(0)}ms</span>
            <span>{(totalDuration * 0.75).toFixed(0)}ms</span>
            <span>{totalDuration.toFixed(0)}ms</span>
          </div>
        </div>

        {/* Tree rows */}
        <div className="divide-y divide-surface-border/40 overflow-y-auto max-h-[600px]">
          {waterfallData.root_spans.map((root) => renderSpanRow(root))}
        </div>
      </div>

      {/* Side Inspector Drawer */}
      {selectedSpan && (
        <div className="w-96 border-l border-surface-border bg-surface-elevated/95 p-4 flex flex-col overflow-y-auto max-h-[640px]">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border">
            <div className="flex items-center space-x-2">
              {getSpanIcon(selectedSpan.span_type)}
              <span className="font-semibold text-xs text-white uppercase font-mono">{selectedSpan.span_type} Call</span>
            </div>
            <button
              onClick={() => setSelectedSpan(null)}
              className="text-slate-400 hover:text-white p-1 rounded hover:bg-surface"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-3 space-y-4 text-xs">
            {/* Span Identification */}
            <div>
              <div className="text-slate-500 font-mono text-[10px] uppercase">Span Name</div>
              <div className="font-mono text-white text-sm font-semibold break-all">{selectedSpan.name}</div>
            </div>

            {/* Metrics Breakdown */}
            <div className="grid grid-cols-2 gap-2 bg-surface p-2.5 rounded border border-surface-border font-mono">
              <div>
                <span className="text-[10px] text-slate-500 block">Duration</span>
                <span className="text-emerald-400 font-semibold">{selectedSpan.duration_ms.toFixed(1)} ms</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Contribution</span>
                <span className="text-accent-cyan font-semibold">{selectedSpan.contribution_percent}%</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Start Offset</span>
                <span className="text-slate-300">+{selectedSpan.start_offset_ms.toFixed(1)} ms</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 block">Status</span>
                <span className={`font-semibold uppercase ${selectedSpan.status === "ok" ? "text-emerald-400" : "text-rose-400"}`}>
                  {selectedSpan.status}
                </span>
              </div>
            </div>

            {/* LLM Details if LLM */}
            {selectedSpan.span_type === "llm" && (
              <div className="space-y-2 bg-surface p-2.5 rounded border border-surface-border">
                <div className="text-[11px] font-semibold text-cyan-400 uppercase font-mono">GenAI Attributes</div>
                <div className="space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Model:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["gen_ai.request.model"] || "unknown"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Provider:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["gen_ai.system"] || "unknown"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Input Tokens:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["gen_ai.usage.input_tokens"] || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Output Tokens:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["gen_ai.usage.output_tokens"] || 0}</span>
                  </div>
                  {selectedSpan.attributes["arp.cost.usd"] !== undefined && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Estimated Cost:</span>
                      <span>${Number(selectedSpan.attributes["arp.cost.usd"]).toFixed(6)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tool Details if Tool */}
            {selectedSpan.span_type === "tool" && (
              <div className="space-y-2 bg-surface p-2.5 rounded border border-surface-border">
                <div className="text-[11px] font-semibold text-amber-400 uppercase font-mono">Tool Execution</div>
                <div className="space-y-1 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Tool Name:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["arp.tool.name"] || selectedSpan.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Retry Count:</span>
                    <span className="text-slate-200">{selectedSpan.attributes["arp.tool.retry_count"] || 0}</span>
                  </div>
                  {selectedSpan.attributes["arp.tool.error_type"] && (
                    <div className="flex justify-between text-rose-400">
                      <span>Error Category:</span>
                      <span className="uppercase">{selectedSpan.attributes["arp.tool.error_type"]}</span>
                    </div>
                  )}
                </div>

                {selectedSpan.attributes["arp.tool.arguments"] && (
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block mt-2">Arguments</span>
                    <pre className="p-2 rounded bg-background text-[11px] font-mono text-slate-300 overflow-x-auto">
                      {JSON.stringify(selectedSpan.attributes["arp.tool.arguments"], null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Raw Attributes */}
            <div>
              <div className="text-slate-500 font-mono text-[10px] uppercase mb-1">Span Attributes</div>
              <pre className="p-2 rounded bg-surface border border-surface-border font-mono text-[10px] text-slate-300 overflow-x-auto max-h-48">
                {JSON.stringify(selectedSpan.attributes, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
