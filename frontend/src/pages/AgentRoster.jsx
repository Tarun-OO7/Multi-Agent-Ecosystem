import React, { useEffect, useState } from "react";
import { dashboardApi } from "@/lib/api";
import { PageHeader } from "@/components/Common";
import {
  Network, FileSearch, ShieldCheck, BarChart3, Lock, Activity, Brain, Sparkles,
} from "lucide-react";

const ICONS = {
  coordinator: Network,
  fraud_detection: FileSearch,
  compliance: ShieldCheck,
  financial_analysis: BarChart3,
  cybersecurity: Lock,
  risk_assessment: Activity,
  decision: Brain,
  report_generation: Sparkles,
};

export default function AgentRoster() {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const res = await dashboardApi.agents();
        setAgents(res.data.agents || []);
      } catch {}
    })();
  }, []);

  return (
    <div data-testid="agents-page">
      <PageHeader
        overline="System Architecture"
        title="The agent roster"
        description="Eight specialized agents orchestrated via a graph-based workflow engine. Each agent has a single responsibility and communicates only through structured JSON. The Decision Agent is the sole aggregator."
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {agents.map((a, i) => {
          const Icon = ICONS[a.id] || Sparkles;
          return (
            <div
              key={a.id}
              className="border border-border bg-card p-6 flex gap-5 hover:-translate-y-0.5 hover:shadow-md transition-all"
              data-testid={`agent-roster-${a.id}`}
            >
              <div className="w-12 h-12 bg-primary text-white flex items-center justify-center shrink-0">
                <Icon className="w-6 h-6" strokeWidth={2} />
              </div>
              <div className="flex-1">
                <div className="flex items-baseline justify-between mb-1">
                  <div className="text-[10px] tracking-overline uppercase text-muted-foreground font-bold">
                    Agent {i + 1} of {agents.length}
                  </div>
                  <span className="font-mono text-[10px] text-primary">{a.id}</span>
                </div>
                <h3 className="font-heading text-lg font-bold mb-1">{a.name}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{a.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-10 border border-border bg-card p-6">
        <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">Architecture Principles</div>
        <h2 className="font-heading text-2xl font-bold mb-4">Why eight agents?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
          {[
            ["Single responsibility", "Each agent owns one analytical concern. No business logic in the Coordinator."],
            ["Read-only context", "Agents receive immutable dataset context. Outputs are new JSON, never mutations."],
            ["Sole aggregator", "Only the Decision Agent integrates results — preventing chained hallucinations."],
            ["Graph-based workflow", "Specialized agents run in parallel; Decision → Report runs after they complete."],
            ["Retry + timeout", "Per-agent exponential backoff, 60s timeout, graceful degradation on failure."],
            ["Streaming progress", "SSE events stream status, duration, and partial results to the dashboard in real time."],
          ].map(([t, d]) => (
            <div key={t} className="flex gap-3">
              <span className="text-primary text-lg leading-none mt-0.5">▸</span>
              <div>
                <div className="font-semibold text-foreground">{t}</div>
                <div className="text-muted-foreground text-xs mt-0.5">{d}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
