import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { auditApi, downloadPdf, API_BASE } from "@/lib/api";
import { PageHeader, StatusBadge, VerdictBadge, KpiCard } from "@/components/Common";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line,
  ComposedChart, Legend,
} from "recharts";
import {
  Download, Loader2, AlertTriangle, ShieldCheck, FileSearch, Brain, ChartBar, Activity,
  Network, Lock, Sparkles,
} from "lucide-react";
import { toast } from "sonner";

const AGENT_VIS = [
  { id: "coordinator", label: "Coordinator", icon: Network },
  { id: "fraud_detection", label: "Fraud Detection", icon: FileSearch },
  { id: "compliance", label: "Compliance", icon: ShieldCheck },
  { id: "financial_analysis", label: "Financial Analysis", icon: ChartBar },
  { id: "cybersecurity", label: "Cybersecurity", icon: Lock },
  { id: "risk_assessment", label: "Risk Assessment", icon: Activity },
  { id: "decision", label: "Decision", icon: Brain },
  { id: "report_generation", label: "Report Generation", icon: Sparkles },
];

export default function AuditDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [audit, setAudit] = useState(null);
  const [agentStates, setAgentStates] = useState({});
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [reportHtml, setReportHtml] = useState("");
  const esRef = useRef(null);

  useEffect(() => {
    if (audit?.status === "completed") {
      auditApi.reportHtml(id).then(res => setReportHtml(res.data)).catch(() => setReportHtml("<html><body><h3 style='color:red;'>Failed to load report</h3></body></html>"));
    }
  }, [audit, id]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await auditApi.detail(id);
        if (active) {
          setAudit(res.data);
          const init = {};
          (res.data.agents || []).forEach((a) => {
            init[a.agent] = { status: a.status, duration_ms: a.duration_ms, summary: a.output?.summary, risk_score: a.output?.risk_score };
          });
          setAgentStates(init);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [id]);

  // SSE stream for running audits
  useEffect(() => {
    if (!audit || (audit.status !== "running" && audit.status !== "queued")) return;
    const url = auditApi.streamUrl(id);
    const es = new EventSource(url);
    esRef.current = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "agent_status") {
          setAgentStates((s) => ({
            ...s,
            [data.agent]: {
              status: data.status,
              duration_ms: data.duration_ms,
              summary: data.summary,
              risk_score: data.risk_score,
              verdict: data.verdict,
            },
          }));
        } else if (data.type === "workflow_status" && data.status === "completed") {
          // Refresh
          auditApi.detail(id).then((res) => setAudit(res.data));
        } else if (data.type === "done") {
          es.close();
          auditApi.detail(id).then((res) => setAudit(res.data));
        } else if (data.type === "snapshot") {
          // No-op
        }
      } catch (e) {
        // ignore parse errors
      }
    };
    es.onerror = () => {
      es.close();
    };
    return () => es.close();
  }, [audit, id]);

  const onDownload = async () => {
    setDownloading(true);
    try {
      await downloadPdf(id, `sentinelai-audit-${audit.title.replace(/\s+/g, "_")}.pdf`);
      toast.success("PDF downloaded");
    } catch (e) {
      toast.error("Download failed");
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <div className="p-8" data-testid="audit-loading">Loading audit…</div>;
  }
  if (!audit) {
    return <div className="p-8" data-testid="audit-not-found">Audit not found.</div>;
  }

  // Pull aggregated findings and outputs
  const allFindings = [];
  let benford = null;
  let financialStats = null;
  let topVendors = [];
  let monthlyTrend = [];
  let riskCategories = null;

  for (const a of audit.agents || []) {
    const out = a.output || {};
    if (out.findings) {
      for (const f of out.findings) allFindings.push({ ...f, agent: a.agent });
    }
    if (a.agent === "fraud_detection") benford = out.benford_analysis;
    if (a.agent === "financial_analysis") {
      financialStats = out.stats;
      topVendors = out.top_vendors || [];
      monthlyTrend = out.monthly_trend || [];
    }
    if (a.agent === "risk_assessment") riskCategories = out.categories;
  }

  const decision = audit.decision || {};

  return (
    <div data-testid="audit-detail-page">
      <PageHeader
        overline={`Audit · ${id.slice(0, 8)}`}
        title={audit.title}
        description={`Scope: ${(audit.scope || []).join(", ")} · Created ${new Date(audit.created_at).toLocaleString()}`}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => nav("/audits")}
              className="rounded-sm border-foreground"
              data-testid="back-to-audits-btn"
            >
              ← All audits
            </Button>
            {audit.status === "completed" && (
              <Button
                onClick={onDownload}
                disabled={downloading}
                className="rounded-sm h-10 px-5 bg-primary text-white hover:bg-primary/90 font-semibold"
                data-testid="download-pdf-btn"
              >
                {downloading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
                Download PDF
              </Button>
            )}
          </div>
        }
      />

      {/* Status + verdict row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="border border-border bg-card p-6" data-testid="audit-status-card">
          <div className="text-xs tracking-overline uppercase text-muted-foreground font-semibold mb-2">Status</div>
          <StatusBadge status={audit.status} />
        </div>
        <KpiCard
          label="Overall Risk"
          value={`${decision.overall_risk_score ?? audit.overall_risk_score ?? "—"}`}
          sub={"/ 100"}
          accent={(decision.overall_risk_score ?? 0) >= 70 ? "danger" : (decision.overall_risk_score ?? 0) >= 40 ? "warning" : "success"}
          testid="audit-risk-kpi"
        />
        <div className="border border-border bg-card p-6" data-testid="audit-verdict-card">
          <div className="text-xs tracking-overline uppercase text-muted-foreground font-semibold mb-2">Verdict</div>
          <div className="mt-2"><VerdictBadge verdict={decision.verdict || audit.overall_verdict} /></div>
        </div>
        <KpiCard
          label="Confidence"
          value={`${Math.round((decision.confidence || audit.confidence || 0) * 100)}%`}
          sub="Decision Agent"
          accent="primary"
          testid="audit-confidence-kpi"
        />
      </div>

      {/* Agent timeline */}
      <div className="border border-border bg-card p-6 mb-8" data-testid="agent-timeline">
        <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">Workflow Engine</div>
        <h2 className="font-heading text-2xl font-bold mb-6">Agent execution timeline</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {AGENT_VIS.map((a, idx) => {
            const st = agentStates[a.id] || {};
            const Icon = a.icon;
            const status = st.status || "pending";
            const colorClass =
              status === "completed" ? "border-success bg-success/5" :
              status === "running" ? "border-primary bg-primary/5 agent-pulse" :
              status === "failed" ? "border-destructive bg-destructive/5" :
              status === "retrying" ? "border-warning bg-warning/5" :
              "border-border bg-muted/20";
            return (
              <div
                key={a.id}
                className={`border-2 p-4 transition-all ${colorClass}`}
                data-testid={`agent-card-${a.id}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="text-[10px] tracking-overline uppercase font-bold text-muted-foreground">
                    Agent {idx + 1}
                  </div>
                  <StatusBadge status={status} />
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4 text-foreground" strokeWidth={2} />
                  <div className="font-semibold text-sm">{a.label}</div>
                </div>
                {st.duration_ms && (
                  <div className="text-[11px] font-mono text-muted-foreground">
                    {(st.duration_ms / 1000).toFixed(2)}s · risk {st.risk_score ?? "—"}
                  </div>
                )}
                {st.summary && (
                  <div className="text-[11px] text-muted-foreground line-clamp-2 mt-1">
                    {st.summary}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Results tabs */}
      {audit.status === "completed" && (
        <Tabs defaultValue="findings" data-testid="results-tabs">
          <TabsList className="rounded-sm bg-muted">
            <TabsTrigger value="findings" data-testid="tab-findings">Findings ({allFindings.length})</TabsTrigger>
            <TabsTrigger value="decision" data-testid="tab-decision">Decision</TabsTrigger>
            <TabsTrigger value="financial" data-testid="tab-financial">Financial Analysis</TabsTrigger>
            <TabsTrigger value="benford" data-testid="tab-benford">Benford</TabsTrigger>
            <TabsTrigger value="risk" data-testid="tab-risk">Risk</TabsTrigger>
            <TabsTrigger value="report" data-testid="tab-report">Report</TabsTrigger>
          </TabsList>

          <TabsContent value="findings" className="mt-6">
            <div className="border border-border bg-card overflow-x-auto">
              <table className="w-full text-sm" data-testid="findings-table">
                <thead className="bg-muted">
                  <tr className="text-[10px] tracking-overline uppercase text-muted-foreground border-b border-border">
                    <th className="text-left font-semibold px-4 py-3">Agent</th>
                    <th className="text-left font-semibold px-4 py-3">Type</th>
                    <th className="text-left font-semibold px-4 py-3">Severity</th>
                    <th className="text-left font-semibold px-4 py-3">Description</th>
                  </tr>
                </thead>
                <tbody>
                  {allFindings.length === 0 ? (
                    <tr><td colSpan={4} className="py-12 text-center text-muted-foreground">No findings flagged.</td></tr>
                  ) : allFindings.map((f, i) => (
                    <tr key={i} className="border-b border-border last:border-b-0 hover:bg-muted/30">
                      <td className="px-4 py-2.5 font-mono text-xs">{f.agent}</td>
                      <td className="px-4 py-2.5 text-xs">{f.type || f.rule || "—"}</td>
                      <td className="px-4 py-2.5">
                        <span className={`text-[10px] font-bold uppercase tracking-overline px-2 py-0.5 ${
                          f.severity === "high" ? "bg-destructive text-white" :
                          f.severity === "medium" ? "bg-warning text-black" :
                          "bg-muted text-muted-foreground"
                        }`}>{f.severity || "—"}</span>
                      </td>
                      <td className="px-4 py-2.5 text-xs">{f.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="decision" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 border border-border bg-card p-6" data-testid="decision-summary">
                <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">Executive Summary</div>
                <h2 className="font-heading text-2xl font-bold mb-4">Decision Agent verdict</h2>
                <p className="text-sm leading-relaxed mb-6">{decision.executive_summary}</p>

                <div className="text-xs tracking-overline uppercase text-muted-foreground font-semibold mb-2">Key findings</div>
                <ul className="space-y-2 mb-6 text-sm">
                  {(decision.key_findings || []).map((k, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">▸</span>
                      <span>{k}</span>
                    </li>
                  ))}
                </ul>

                <div className="text-xs tracking-overline uppercase text-muted-foreground font-semibold mb-2">Recommendations</div>
                <ul className="space-y-2 mb-6 text-sm">
                  {(decision.recommendations || []).map((r, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-primary mt-0.5">→</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>

                {decision.rationale && (
                  <div className="border-t border-border pt-4 text-xs text-muted-foreground italic">
                    <span className="font-semibold not-italic">Rationale: </span>{decision.rationale}
                  </div>
                )}
              </div>

              <div className="border border-border bg-card p-6" data-testid="agent-scores">
                <h3 className="font-heading text-lg font-semibold mb-4">Agent risk scores</h3>
                <div className="space-y-3">
                  {Object.entries(decision.agent_scores || {}).map(([agent, score]) => (
                    <div key={agent}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-medium">{agent.replace(/_/g, " ")}</span>
                        <span className="font-mono font-semibold">{score}/100</span>
                      </div>
                      <div className="h-1.5 bg-muted">
                        <div
                          className={`h-full ${score >= 70 ? "bg-destructive" : score >= 40 ? "bg-warning" : "bg-primary"}`}
                          style={{ width: `${Math.min(score, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="financial" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {financialStats && (
                <>
                  <KpiCard label="Total Spend" value={`$${(financialStats.total_spend || 0).toLocaleString()}`} sub={`${financialStats.transaction_count} transactions`} accent="primary" testid="fin-total-spend" />
                  <KpiCard label="Mean Transaction" value={`$${(financialStats.mean_transaction || 0).toLocaleString()}`} sub={`Median $${(financialStats.median_transaction || 0).toLocaleString()}`} testid="fin-mean-txn" />
                  <KpiCard label="Max Transaction" value={`$${(financialStats.max_transaction || 0).toLocaleString()}`} sub="Largest single charge" accent="warning" testid="fin-max-txn" />
                </>
              )}
            </div>

            {monthlyTrend.length > 0 && (
              <div className="border border-border bg-card p-6 mt-6">
                <h3 className="font-heading text-lg font-semibold mb-4">Monthly spend trend</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={monthlyTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="spend" stroke="#002FA7" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {topVendors.length > 0 && (
              <div className="border border-border bg-card p-6 mt-6">
                <h3 className="font-heading text-lg font-semibold mb-4">Top vendors by spend</h3>
                <ResponsiveContainer width="100%" height={Math.max(220, topVendors.length * 30)}>
                  <BarChart data={topVendors} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis dataKey="vendor" type="category" tick={{ fontSize: 11 }} width={150} />
                    <Tooltip />
                    <Bar dataKey="spend" fill="#002FA7" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </TabsContent>

          <TabsContent value="benford" className="mt-6">
            {benford && benford.n > 0 ? (
              <div className="border border-border bg-card p-6" data-testid="benford-card">
                <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">Statistical Forensics</div>
                <h3 className="font-heading text-2xl font-bold mb-1">Benford's Law analysis</h3>
                <p className="text-sm text-muted-foreground mb-6">
                  Observed first-digit distribution vs. expected (logarithmic). n={benford.n}, χ²={benford.chi_square}, mean deviation={benford.deviation}%.
                </p>
                <ResponsiveContainer width="100%" height={320}>
                  <ComposedChart
                    data={Object.keys(benford.observed).map((d) => ({
                      digit: d,
                      observed: benford.observed[d],
                      expected: benford.expected[d],
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                    <XAxis dataKey="digit" tick={{ fontSize: 11 }} label={{ value: "First Digit", position: "insideBottom", offset: -5 }} />
                    <YAxis tick={{ fontSize: 11 }} label={{ value: "%", angle: -90, position: "insideLeft" }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="observed" fill="#002FA7" name="Observed %" />
                    <Line dataKey="expected" stroke="#D00000" strokeWidth={2} name="Expected (Benford)" dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="border border-border bg-card p-12 text-center text-muted-foreground">
                Benford analysis unavailable — insufficient numeric data.
              </div>
            )}
          </TabsContent>

          <TabsContent value="risk" className="mt-6">
            {riskCategories ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard label="Financial Risk" value={riskCategories.financial} sub="Tail concentration" accent={riskCategories.financial >= 50 ? "warning" : "success"} testid="risk-financial" />
                <KpiCard label="Operational Risk" value={riskCategories.operational} sub="Vendor diversity" accent={riskCategories.operational >= 50 ? "warning" : "success"} testid="risk-operational" />
                <KpiCard label="Reputational Risk" value={riskCategories.reputational} sub="Shady vendor exposure" accent={riskCategories.reputational >= 50 ? "danger" : "success"} testid="risk-reputational" />
              </div>
            ) : (
              <div className="border border-border bg-card p-12 text-center text-muted-foreground">
                Risk Assessment Agent did not run for this audit.
              </div>
            )}
          </TabsContent>

          <TabsContent value="report" className="mt-6">
            <div className="border border-border bg-card p-6" data-testid="report-tab">
              <h3 className="font-heading text-lg font-semibold mb-2">Executive HTML report</h3>
              <p className="text-sm text-muted-foreground mb-4">Inline preview of the generated HTML report. Use the download button above for PDF export.</p>
              <iframe
                srcDoc={reportHtml || "<html><body><h3 style='font-family:sans-serif;color:#666;'>Loading report...</h3></body></html>"}
                title="Audit Report"
                className="w-full h-[600px] border border-border bg-white"
                data-testid="report-iframe"
                sandbox=""
                onLoad={() => {}}
              />
              <div className="text-[11px] text-muted-foreground mt-2">
                Note: If the preview is blank, download the PDF — the HTML viewer requires session storage support.
              </div>
            </div>
          </TabsContent>
        </Tabs>
      )}

      {audit.status === "failed" && (
        <div className="border border-destructive bg-destructive/5 p-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-destructive">Audit failed</div>
            <div className="text-sm text-muted-foreground mt-1">{audit.error || "Workflow engine reported an error."}</div>
          </div>
        </div>
      )}
    </div>
  );
}
