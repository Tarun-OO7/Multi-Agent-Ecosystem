import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { dashboardApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader, KpiCard, StatusBadge, VerdictBadge } from "@/components/Common";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowUpRight, PlayCircle, FileText, AlertTriangle } from "lucide-react";

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const nav = useNavigate();

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await dashboardApi.summary();
        if (active) setSummary(res.data);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  const verdictBreakdown = summary?.verdicts || {};
  const recent = summary?.recent_audits || [];

  const riskAccent = (score) => {
    if (score >= 70) return "danger";
    if (score >= 40) return "warning";
    if (score >= 15) return "primary";
    return "success";
  };

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        overline="Command Center"
        title={`Good day, ${user?.full_name?.split(" ")[0] || "Auditor"}.`}
        description="Real-time overview of your audit operations. Every number is a live signal from the SentinelAI agent grid."
        action={
          <Button
            data-testid="dashboard-new-audit-btn"
            onClick={() => nav("/upload")}
            className="rounded-sm h-11 px-6 bg-primary text-white hover:bg-primary/90 font-semibold"
            disabled={user?.role === "viewer"}
          >
            <PlayCircle className="w-4 h-4 mr-2" />
            New Audit
          </Button>
        }
      />

      {/* KPI grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          <KpiCard
            label="Average Risk Score"
            value={summary?.average_risk_score ?? 0}
            sub={`Across ${summary?.completed ?? 0} completed audits`}
            accent={riskAccent(summary?.average_risk_score || 0)}
            testid="kpi-risk-score"
          />
          <KpiCard
            label="Audits Total"
            value={summary?.total_audits ?? 0}
            sub={`${summary?.completed ?? 0} done · ${summary?.running ?? 0} running`}
            testid="kpi-total-audits"
          />
          <KpiCard
            label="Datasets Ingested"
            value={summary?.total_datasets ?? 0}
            sub="CSV / PDF financial files"
            accent="primary"
            testid="kpi-datasets"
          />
          <KpiCard
            label="Failed"
            value={summary?.failed ?? 0}
            sub="Workflow execution errors"
            accent={summary?.failed > 0 ? "danger" : "default"}
            testid="kpi-failed"
          />
        </div>
      )}

      {/* Verdict breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 border border-border bg-card p-6" data-testid="recent-audits-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading text-xl font-semibold">Recent audits</h2>
            <button
              onClick={() => nav("/audits")}
              className="text-xs tracking-overline uppercase text-primary font-semibold hover:underline"
              data-testid="view-all-audits-btn"
            >
              View all →
            </button>
          </div>
          {recent.length === 0 ? (
            <div className="text-center py-12 border border-dashed border-border">
              <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No audits yet.</p>
              <Button
                onClick={() => nav("/upload")}
                className="mt-4 rounded-sm bg-primary text-white hover:bg-primary/90"
                disabled={user?.role === "viewer"}
                data-testid="empty-state-upload-btn"
              >
                Start first audit
              </Button>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] tracking-overline uppercase text-muted-foreground border-b border-border">
                  <th className="text-left font-semibold py-2">Title</th>
                  <th className="text-left font-semibold py-2">Status</th>
                  <th className="text-left font-semibold py-2">Verdict</th>
                  <th className="text-right font-semibold py-2">Risk</th>
                  <th className="text-right font-semibold py-2"></th>
                </tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.id} className="border-b border-border hover:bg-muted/40 transition-colors">
                    <td className="py-3 font-medium" data-testid={`audit-title-${a.id}`}>{a.title}</td>
                    <td className="py-3"><StatusBadge status={a.status} /></td>
                    <td className="py-3"><VerdictBadge verdict={a.overall_verdict} /></td>
                    <td className="py-3 text-right font-mono">{a.overall_risk_score ?? "—"}</td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => nav(`/audits/${a.id}`)}
                        className="text-primary text-xs font-semibold hover:underline"
                        data-testid={`open-audit-${a.id}`}
                      >
                        Open <ArrowUpRight className="w-3 h-3 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="border border-border bg-card p-6" data-testid="verdict-breakdown-card">
          <h2 className="font-heading text-xl font-semibold mb-4">Verdict breakdown</h2>
          {Object.keys(verdictBreakdown).length === 0 ? (
            <div className="text-sm text-muted-foreground py-8 text-center">
              No verdicts yet.
            </div>
          ) : (
            <div className="space-y-4">
              {["CLEAR", "MINOR_FOLLOWUP", "ELEVATED_REVIEW", "CRITICAL_ESCALATE"].map((v) => {
                const count = verdictBreakdown[v] || 0;
                const total = Object.values(verdictBreakdown).reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={v} data-testid={`verdict-row-${v}`}>
                    <div className="flex items-center justify-between mb-1">
                      <VerdictBadge verdict={v} />
                      <span className="text-sm font-mono font-semibold">{count}</span>
                    </div>
                    <div className="h-1.5 bg-muted">
                      <div
                        className={`h-full ${
                          v === "CLEAR" ? "bg-success" :
                          v === "MINOR_FOLLOWUP" ? "bg-warning" :
                          v === "ELEVATED_REVIEW" ? "bg-orange-500" :
                          "bg-destructive"
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-8 pt-6 border-t border-border text-xs text-muted-foreground space-y-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-warning mt-0.5 shrink-0" />
              <span>Verdicts are produced by the Decision Agent using LLM-aggregated agent outputs.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
