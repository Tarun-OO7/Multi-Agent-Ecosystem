import React from "react";

export function PageHeader({ overline, title, description, action }) {
  return (
    <div className="flex items-start justify-between gap-6 mb-8 pb-6 border-b border-border">
      <div>
        {overline && (
          <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">
            {overline}
          </div>
        )}
        <h1 className="font-heading text-4xl font-bold tracking-tight text-foreground">
          {title}
        </h1>
        {description && (
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function KpiCard({ label, value, sub, accent = "default", testid }) {
  const accentMap = {
    default: "text-foreground",
    primary: "text-primary",
    success: "text-success",
    warning: "text-warning",
    danger: "text-destructive",
  };
  return (
    <div
      className="border border-border bg-card p-6 transition-all hover:-translate-y-0.5 hover:shadow-md"
      data-testid={testid}
    >
      <div className="text-xs tracking-overline uppercase text-muted-foreground font-semibold">
        {label}
      </div>
      <div className={`mt-3 font-heading text-5xl font-black tracking-tight ${accentMap[accent]}`}>
        {value}
      </div>
      {sub && <div className="text-xs text-muted-foreground mt-2">{sub}</div>}
    </div>
  );
}

export function StatusBadge({ status }) {
  const map = {
    completed: "bg-success text-white",
    running: "bg-primary text-white agent-pulse",
    pending: "bg-muted text-muted-foreground border border-border",
    queued: "bg-muted text-muted-foreground border border-border",
    failed: "bg-destructive text-white",
    retrying: "bg-warning text-black",
    skipped: "bg-muted text-muted-foreground",
  };
  const cls = map[status] || "bg-muted text-muted-foreground border border-border";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[10px] font-bold uppercase tracking-overline ${cls}`}
    >
      {status}
    </span>
  );
}

export function VerdictBadge({ verdict }) {
  if (!verdict) return <span className="text-muted-foreground text-xs">—</span>;
  const map = {
    CLEAR: "bg-success text-white",
    MINOR_FOLLOWUP: "bg-warning text-black",
    ELEVATED_REVIEW: "bg-orange-500 text-white",
    CRITICAL_ESCALATE: "bg-destructive text-white",
  };
  const cls = map[verdict] || "bg-muted text-foreground";
  return (
    <span
      className={`inline-flex items-center px-3 py-1 text-xs font-bold uppercase tracking-overline ${cls}`}
      data-testid={`verdict-${verdict}`}
    >
      {verdict.replace(/_/g, " ")}
    </span>
  );
}
