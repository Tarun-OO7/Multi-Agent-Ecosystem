import React, { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { datasetApi, auditApi } from "@/lib/api";
import { PageHeader } from "@/components/Common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { UploadCloud, FileText, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const SCOPES = [
  { id: "fraud", label: "Fraud Detection", desc: "Duplicate invoices, Benford's Law, anomaly Z-scores" },
  { id: "compliance", label: "Compliance", desc: "SOX / GAAP / IFRS rule verification" },
  { id: "financial", label: "Financial Analysis", desc: "Trends, vendor spend, budget variance" },
  { id: "cybersecurity", label: "Cybersecurity", desc: "PII detection, prompt-injection guard" },
  { id: "risk", label: "Risk Assessment", desc: "Monte Carlo composite risk scoring" },
];

export default function Upload() {
  const [dataset, setDataset] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [creatingSample, setCreatingSample] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [title, setTitle] = useState("Q1 2026 Audit");
  const [scope, setScope] = useState(SCOPES.map((s) => s.id));
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef(null);
  const nav = useNavigate();

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await datasetApi.upload(file);
      setDataset(res.data);
      toast.success(`Parsed ${res.data.row_count} rows`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  const onSampleClick = async () => {
    setCreatingSample(true);
    try {
      const res = await datasetApi.sample();
      setDataset(res.data);
      toast.success("Synthetic invoice dataset generated.");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to generate sample");
    } finally {
      setCreatingSample(false);
    }
  };

  const toggleScope = (id) => {
    setScope((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  };

  const startAudit = async () => {
    if (!dataset) return;
    setSubmitting(true);
    try {
      const res = await auditApi.create({ dataset_id: dataset.id, scope, title });
      toast.success("Audit queued");
      nav(`/audits/${res.data.audit_id}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed to create audit");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-testid="upload-page">
      <PageHeader
        overline="Ingest"
        title="Upload financial data"
        description="Drop a CSV or PDF of invoices, expenses, or ledger entries. SentinelAI will normalize columns, detect schemas, and stage the dataset for the agent grid."
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: upload */}
        <div className="lg:col-span-3 space-y-6">
          <div
            data-testid="dropzone"
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) handleFile(f);
            }}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed p-16 text-center cursor-pointer transition-all bg-muted/30 ${
              dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
            }`}
          >
            <input
              type="file"
              ref={inputRef}
              className="hidden"
              accept=".csv,.pdf"
              onChange={(e) => handleFile(e.target.files?.[0])}
              data-testid="file-input"
            />
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-10 h-10 text-primary animate-spin" />
                <div className="text-sm font-medium">Parsing file…</div>
              </div>
            ) : (
              <>
                <UploadCloud className="w-12 h-12 text-primary mx-auto mb-4" strokeWidth={1.5} />
                <div className="font-heading text-2xl font-semibold mb-1">Drop file here</div>
                <div className="text-sm text-muted-foreground mb-4">
                  CSV or PDF · Max 25MB · UTF-8 encoded
                </div>
                <Button
                  variant="outline"
                  className="rounded-sm border-foreground"
                  data-testid="browse-files-btn"
                  type="button"
                >
                  Browse files
                </Button>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-border" />
            <span className="text-[10px] tracking-overline uppercase text-muted-foreground font-semibold">
              or
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <Button
            onClick={onSampleClick}
            disabled={creatingSample}
            className="w-full rounded-sm h-12 bg-[#0A0A0A] text-white hover:bg-[#0A0A0A]/90 font-semibold"
            data-testid="generate-sample-btn"
          >
            {creatingSample ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Sparkles className="w-4 h-4 mr-2" />
            )}
            Generate synthetic invoice dataset (demo)
          </Button>

          {dataset && (
            <div className="border border-border bg-card p-5" data-testid="dataset-preview">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-5 h-5 text-success" />
                  <div>
                    <div className="font-semibold text-sm">{dataset.filename}</div>
                    <div className="text-xs text-muted-foreground">
                      {dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns · {(dataset.size_bytes / 1024).toFixed(1)} KB
                    </div>
                  </div>
                </div>
                <span className="text-[10px] tracking-overline uppercase font-semibold text-success bg-success/10 px-2 py-1">
                  Ready
                </span>
              </div>

              {dataset.preview?.length > 0 && (
                <div className="overflow-x-auto border-t border-border -mx-5 -mb-5 mt-3">
                  <table className="w-full text-xs font-mono">
                    <thead className="bg-muted">
                      <tr>
                        {dataset.columns.slice(0, 6).map((c) => (
                          <th key={c} className="text-left px-3 py-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground border-r border-border last:border-r-0">
                            {c}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {dataset.preview.slice(0, 5).map((row, i) => (
                        <tr key={i} className="border-t border-border">
                          {dataset.columns.slice(0, 6).map((c) => (
                            <td key={c} className="px-3 py-2 border-r border-border last:border-r-0 truncate max-w-[180px]">
                              {String(row[c] ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: scope config */}
        <div className="lg:col-span-2 space-y-6">
          <div className="border border-border bg-card p-6 sticky top-6">
            <div className="text-xs tracking-overline uppercase text-primary font-semibold mb-2">
              Audit Configuration
            </div>
            <h2 className="font-heading text-2xl font-bold mb-4">Configure audit scope</h2>

            <div className="space-y-3 mb-6">
              <Label className="text-xs tracking-overline uppercase font-semibold">Audit title</Label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Q1 2026 Vendor Audit"
                className="rounded-sm h-10"
                data-testid="audit-title-input"
              />
            </div>

            <Label className="text-xs tracking-overline uppercase font-semibold mb-3 block">
              Specialized agents
            </Label>
            <div className="space-y-2 mb-6">
              {SCOPES.map((s) => {
                const checked = scope.includes(s.id);
                return (
                  <label
                    key={s.id}
                    className={`flex items-start gap-3 p-3 border cursor-pointer transition-colors ${
                      checked ? "border-primary bg-primary/5" : "border-border hover:bg-muted/50"
                    }`}
                    data-testid={`scope-${s.id}`}
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={() => toggleScope(s.id)}
                      className="mt-0.5"
                      data-testid={`scope-checkbox-${s.id}`}
                    />
                    <div>
                      <div className="font-semibold text-sm">{s.label}</div>
                      <div className="text-xs text-muted-foreground">{s.desc}</div>
                    </div>
                  </label>
                );
              })}
            </div>

            <Button
              onClick={startAudit}
              disabled={!dataset || scope.length === 0 || submitting}
              data-testid="start-audit-btn"
              className="w-full h-12 rounded-sm bg-primary text-white hover:bg-primary/90 font-semibold"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <FileText className="w-4 h-4 mr-2" />
              )}
              Execute Audit
            </Button>

            <div className="text-[11px] text-muted-foreground mt-4 leading-relaxed">
              Coordinator will route the dataset to the {scope.length} selected agent(s) in parallel.
              The Decision Agent will aggregate outputs and the Report Generator will produce a PDF.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
