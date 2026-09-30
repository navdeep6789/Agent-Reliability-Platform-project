"use client";

import React from "react";
import {
  LayoutDashboard,
  GitBranch,
  Bot,
  AlertTriangle,
  ClipboardCheck,
  ShieldAlert,
  Coins,
  Cpu
} from "lucide-react";

export type TabType =
  | "overview"
  | "traces"
  | "agents"
  | "findings"
  | "evaluations"
  | "policies"
  | "models"
  | "system";

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  violationsCount?: number;
  findingsCount?: number;
}

export function Sidebar({ currentTab, onSelectTab, violationsCount = 0, findingsCount = 0 }: SidebarProps) {
  const items = [
    { id: "overview" as TabType, label: "Overview", icon: LayoutDashboard },
    { id: "traces" as TabType, label: "Traces & Waterfall", icon: GitBranch },
    { id: "agents" as TabType, label: "Agent Health", icon: Bot },
    { id: "findings" as TabType, label: "Reliability Findings", icon: AlertTriangle, badge: findingsCount > 0 ? findingsCount : undefined, badgeColor: "bg-amber-900/60 text-amber-300 border-amber-700/60" },
    { id: "evaluations" as TabType, label: "Evaluations & Regressions", icon: ClipboardCheck },
    { id: "policies" as TabType, label: "Policies & Violations", icon: ShieldAlert, badge: violationsCount > 0 ? violationsCount : undefined, badgeColor: "bg-rose-900/60 text-rose-300 border-rose-700/60" },
    { id: "models" as TabType, label: "Models & Cost Accounting", icon: Coins },
    { id: "system" as TabType, label: "Platform Observability", icon: Cpu }
  ];

  return (
    <aside className="w-64 border-r border-surface-border bg-surface flex flex-col shrink-0 min-h-[calc(100vh-3.5rem)]">
      <div className="p-4 space-y-1">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 px-3 py-2">
          Workstation Navigation
        </div>
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-xs font-medium transition ${
                isActive
                  ? "bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-elevated/70"
              }`}
            >
              <div className="flex items-center space-x-2.5">
                <Icon className={`w-4 h-4 ${isActive ? "text-accent-cyan" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${item.badgeColor}`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-auto p-4 border-t border-surface-border text-xs text-slate-500 font-mono space-y-1">
        <div className="text-[11px] text-slate-400 font-semibold">Deterministic Engine</div>
        <div className="text-[10px] text-slate-500">
          OTel GenAI Telemetry Normalization
        </div>
        <div className="text-[10px] text-slate-500">
          ClickHouse / DuckDB Analytics
        </div>
      </div>
    </aside>
  );
}
