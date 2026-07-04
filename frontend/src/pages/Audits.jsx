import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { auditApi } from "@/lib/api";
import { PageHeader, StatusBadge, VerdictBadge } from "@/components/Common";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { PlayCircle, ArrowUpRight } from "lucide-react";

export default function Audits() {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await auditApi.list();
        if (active) setAudits(res.data.audits || []);
      } finally {
        if (active) setLoading(false);
      }
    })();
    const t = setInterval(async () => {
      try {
        const res = await auditApi.list();
        setAudits(res.data.audits || []);
      } catch {}
    }, 5000);
    return () => { active = false; clearInterval(t); };
  }, []);

  return (
    <div data-testid="audits-page">
      <PageHeader
        overline="History"
        title="All audits"
        description="Every audit execution. Click into one to inspect the agent timeline, findings, and export the executive report."
        action={
          user?.role !== "viewer" && (
            <Button
              onClick={() => nav("/upload")}
              data-testid="audits-new-btn"
              className="rounded-sm h-11 px-6 bg-primary text-white hover:bg-primary/90 font-semibold"
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              New audit
            </Button>
          )
        }
      />

      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14" />)}
        </div>
      ) : audits.length === 0 ? (
        <div className="border border-dashed border-border py-20 text-center" data-testid="audits-empty">
          <p className="text-muted-foreground mb-4">No audits have been executed yet.</p>
          {user?.role !== "viewer" && (
            <Button
              onClick={() => nav("/upload")}
              className="rounded-sm bg-primary text-white hover:bg-primary/90"
            >
              Start your first audit
            </Button>
          )}
        </div>
      ) : (
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-sm" data-testid="audits-table">
            <thead className="bg-muted">
              <tr className="text-[10px] tracking-overline uppercase text-muted-foreground border-b border-border">
                <th className="text-left font-semibold px-4 py-3">Title</th>
                <th className="text-left font-semibold px-4 py-3">Owner</th>
                <th className="text-left font-semibold px-4 py-3">Scope</th>
                <th className="text-left font-semibold px-4 py-3">Status</th>
                <th className="text-left font-semibold px-4 py-3">Verdict</th>
                <th className="text-right font-semibold px-4 py-3">Risk</th>
                <th className="text-left font-semibold px-4 py-3">Created</th>
                <th className="text-right font-semibold px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {audits.map((a) => (
                <tr key={a.id} className="border-b border-border last:border-b-0 hover:bg-muted/40 transition-colors">
                  <td className="px-4 py-3 font-medium">{a.title}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{a.user_email || "—"}</td>
                  <td className="px-4 py-3 text-xs">
                    {(a.scope || []).slice(0, 3).map((s) => (
                      <span key={s} className="mr-1 px-1.5 py-0.5 bg-muted text-[10px] uppercase tracking-wide">
                        {s}
                      </span>
                    ))}
                    {(a.scope || []).length > 3 && <span className="text-xs text-muted-foreground">+{a.scope.length - 3}</span>}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-3"><VerdictBadge verdict={a.overall_verdict} /></td>
                  <td className="px-4 py-3 text-right font-mono font-semibold">{a.overall_risk_score ?? "—"}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground font-mono">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => nav(`/audits/${a.id}`)}
                      className="text-primary font-semibold text-xs hover:underline"
                      data-testid={`audit-open-${a.id}`}
                    >
                      Open <ArrowUpRight className="w-3 h-3 inline" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
