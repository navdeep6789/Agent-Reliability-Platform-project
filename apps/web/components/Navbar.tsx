"use client";

import React, { useEffect, useState } from "react";
import { Activity, ShieldCheck, Play, Server, RefreshCw } from "lucide-react";
import { api } from "../lib/api";

interface NavbarProps {
  onOpenDemoModal: () => void;
  onRefreshData?: () => void;
}

export function Navbar({ onOpenDemoModal, onRefreshData }: NavbarProps) {
  const [healthStatus, setHealthStatus] = useState<string>("checking");
  const [throughput, setThroughput] = useState<number>(0);

  useEffect(() => {
    async function loadHealth() {
      try {
        const obs = await api.getSystemObservability();
        setHealthStatus(obs.status || "healthy");
        setThroughput(obs.ingestion_throughput_spans_per_sec || 0);
      } catch (e) {
        setHealthStatus("offline");
      }
    }
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 border-b border-surface-border bg-surface/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded bg-accent-cyan/10 border border-accent-cyan/40 flex items-center justify-center text-accent-cyan font-mono font-bold text-sm">
            ARP
          </div>
          <div>
            <span className="font-semibold tracking-tight text-white text-sm">
              AGENT RELIABILITY PLATFORM
            </span>
            <span className="ml-2 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-surface-elevated text-slate-400 border border-surface-border">
              v1.0.0
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center space-x-2 text-xs text-slate-400 border-l border-surface-border pl-4">
          <span className="text-slate-500">Project:</span>
          <span className="font-mono text-slate-200 bg-surface-elevated px-2 py-0.5 rounded border border-surface-border">
            proj_default_production
          </span>
          <span className="font-mono text-emerald-400 bg-emerald-950/50 border border-emerald-800/60 px-1.5 py-0.5 rounded text-[11px]">
            production
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {onRefreshData && (
          <button
            onClick={onRefreshData}
            title="Refresh Telemetry"
            className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-surface-elevated border border-transparent hover:border-surface-border transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        )}

        <div className="hidden sm:flex items-center space-x-2 text-xs font-mono bg-surface-elevated/70 px-2.5 py-1 rounded border border-surface-border text-slate-300">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${healthStatus === 'healthy' ? 'bg-emerald-400' : 'bg-rose-400'} opacity-75`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${healthStatus === 'healthy' ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
          </span>
          <span className="text-slate-400">Collector:</span>
          <span className="text-emerald-400 font-semibold uppercase">{healthStatus}</span>
        </div>

        <button
          onClick={onOpenDemoModal}
          className="flex items-center space-x-1.5 text-xs font-medium bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded transition shadow-sm"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Execute Demo Scenario</span>
        </button>
      </div>
    </header>
  );
}
