import React, { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { PageHeader } from "@/components/Common";
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await adminApi.logs();
        setLogs(res.data.logs || []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div data-testid="admin-logs-page">
      <PageHeader
        overline="Compliance"
        title="Audit trail"
        description="Every API request to SentinelAI is logged with a correlation ID, actor, status, and duration."
      />
      {loading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="border border-border bg-card overflow-x-auto max-h-[70vh] scrollbar-thin">
          <table className="w-full text-xs font-mono">
            <thead className="bg-muted sticky top-0">
              <tr className="text-[10px] tracking-overline uppercase text-muted-foreground">
                <th className="text-left font-semibold px-3 py-2">Timestamp</th>
                <th className="text-left font-semibold px-3 py-2">Request ID</th>
                <th className="text-left font-semibold px-3 py-2">User</th>
                <th className="text-left font-semibold px-3 py-2">Method</th>
                <th className="text-left font-semibold px-3 py-2">Path</th>
                <th className="text-right font-semibold px-3 py-2">Status</th>
                <th className="text-right font-semibold px-3 py-2">Duration</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-border hover:bg-muted/40">
                  <td className="px-3 py-1.5 whitespace-nowrap text-muted-foreground">{new Date(l.timestamp).toLocaleTimeString()}</td>
                  <td className="px-3 py-1.5 text-primary">{l.request_id?.slice(0, 8)}</td>
                  <td className="px-3 py-1.5">{l.user_email || "—"}</td>
                  <td className="px-3 py-1.5 font-bold">{l.method}</td>
                  <td className="px-3 py-1.5">{l.path}</td>
                  <td className={`px-3 py-1.5 text-right font-bold ${l.status_code < 400 ? "text-success" : "text-destructive"}`}>{l.status_code}</td>
                  <td className="px-3 py-1.5 text-right">{l.duration_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
