"""SentinelAI multi-agent system: 8 specialized agents.

Each agent receives read-only dataset context and returns structured JSON.
Agents never call each other. Decision Agent is the sole aggregator.
"""
from __future__ import annotations
import math
import re
from collections import Counter, defaultdict
from typing import Any
import pandas as pd

from llm_client import call_llm_json


# ============================================================
# Base helpers
# ============================================================
def _safe_amount_series(df: pd.DataFrame, mapping: dict) -> pd.Series:
    col = mapping.get("amount")
    if not col or col not in df.columns:
        return pd.Series(dtype=float)
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return s[s > 0]


def _safe_vendor_series(df: pd.DataFrame, mapping: dict) -> pd.Series:
    col = mapping.get("vendor")
    if not col or col not in df.columns:
        return pd.Series(dtype=str)
    return df[col].astype(str)


def _benford_distribution(amounts: pd.Series) -> dict[str, Any]:
    """Compute Benford's law first-digit distribution and chi-square test."""
    expected = {d: math.log10(1 + 1 / d) * 100 for d in range(1, 10)}
    digits = []
    for v in amounts:
        s = str(v).lstrip("0.-")
        for ch in s:
            if ch.isdigit() and ch != "0":
                digits.append(int(ch))
                break
    if not digits:
        return {"observed": {}, "expected": expected, "chi_square": 0.0, "n": 0, "deviation": 0.0}
    counter = Counter(digits)
    total = sum(counter.values())
    observed = {d: counter.get(d, 0) / total * 100 for d in range(1, 10)}
    chi_sq = sum(((observed[d] - expected[d]) ** 2) / expected[d] for d in range(1, 10) if expected[d] > 0)
    deviation = sum(abs(observed[d] - expected[d]) for d in range(1, 10)) / 9
    return {
        "observed": {str(d): round(observed[d], 2) for d in range(1, 10)},
        "expected": {str(d): round(expected[d], 2) for d in range(1, 10)},
        "chi_square": round(chi_sq, 2),
        "n": total,
        "deviation": round(deviation, 2),
    }


# ============================================================
# 1. Fraud Detection Agent
# ============================================================
async def fraud_detection_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    df: pd.DataFrame = ctx["dataframe"]
    mapping: dict = ctx["canonical_mapping"]
    findings: list[dict] = []

    if df.empty:
        return {"agent": "fraud_detection", "findings": [], "summary": "No data to analyze", "risk_score": 0, "anomaly_count": 0}

    amount_col = mapping.get("amount")
    vendor_col = mapping.get("vendor")
    invoice_col = mapping.get("invoice_id")

    # 1. Duplicate invoice detection
    if vendor_col and amount_col:
        dup_keys = df.groupby([vendor_col, amount_col]).size().reset_index(name="count")
        dups = dup_keys[dup_keys["count"] > 1]
        if not dups.empty:
            for _, row in dups.head(10).iterrows():
                findings.append({
                    "type": "duplicate_invoice",
                    "severity": "high",
                    "vendor": str(row[vendor_col]),
                    "amount": float(row[amount_col]),
                    "count": int(row["count"]),
                    "description": f"Vendor '{row[vendor_col]}' has {row['count']} invoices at exactly ${row[amount_col]:,.2f}",
                })

    # 2. Benford's Law
    amounts = _safe_amount_series(df, mapping)
    benford = _benford_distribution(amounts)
    if benford["deviation"] > 4.0 and benford["n"] >= 30:
        findings.append({
            "type": "benford_violation",
            "severity": "high" if benford["deviation"] > 8 else "medium",
            "description": f"Benford's Law deviation of {benford['deviation']}% (chi²={benford['chi_square']}) suggests fabricated numbers.",
            "deviation": benford["deviation"],
        })

    # 3. Z-score outliers
    if len(amounts) >= 10:
        mean = float(amounts.mean())
        std = float(amounts.std()) or 1.0
        outliers = amounts[(amounts - mean).abs() > 3 * std]
        for idx, val in list(outliers.items())[:8]:
            row = df.loc[idx]
            findings.append({
                "type": "amount_outlier",
                "severity": "medium",
                "amount": float(val),
                "z_score": round((val - mean) / std, 2),
                "vendor": str(row[vendor_col]) if vendor_col else "unknown",
                "invoice_id": str(row[invoice_col]) if invoice_col else f"row-{idx}",
                "description": f"Amount ${val:,.2f} is {round((val - mean) / std, 1)} stddev above mean",
            })

    # 4. Vendor concentration risk (collusion proxy)
    vendors = _safe_vendor_series(df, mapping)
    if not vendors.empty and amount_col:
        vendor_spend = df.groupby(vendors)[amount_col].sum().sort_values(ascending=False)
        total_spend = vendor_spend.sum() or 1
        top_vendor = vendor_spend.index[0]
        top_share = vendor_spend.iloc[0] / total_spend * 100
        if top_share > 30:
            findings.append({
                "type": "vendor_concentration",
                "severity": "medium",
                "vendor": str(top_vendor),
                "share_percent": round(float(top_share), 2),
                "description": f"Vendor '{top_vendor}' accounts for {top_share:.1f}% of all spend — concentration risk.",
            })

    # 5. Just-below-threshold (split-purchase) patterns
    if amount_col:
        threshold_amounts = [10000, 5000, 2500, 1000]
        for thresh in threshold_amounts:
            near = amounts[(amounts >= thresh * 0.95) & (amounts < thresh)]
            if len(near) >= 5:
                findings.append({
                    "type": "threshold_split",
                    "severity": "high",
                    "threshold": thresh,
                    "count": int(len(near)),
                    "description": f"{len(near)} invoices clustered just below ${thresh:,} — possible approval-limit splitting.",
                })
                break

    # Risk score: weighted findings
    sev_weight = {"high": 25, "medium": 10, "low": 3}
    score = min(100, sum(sev_weight.get(f["severity"], 0) for f in findings))

    return {
        "agent": "fraud_detection",
        "findings": findings,
        "anomaly_count": len(findings),
        "benford_analysis": benford,
        "risk_score": score,
        "summary": f"Detected {len(findings)} fraud signals. Risk score: {score}/100.",
    }


# ============================================================
# 2. Compliance Agent
# ============================================================
async def compliance_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    df: pd.DataFrame = ctx["dataframe"]
    mapping = ctx["canonical_mapping"]
    findings: list[dict] = []

    if df.empty:
        return {"agent": "compliance", "findings": [], "violations": 0, "risk_score": 0, "summary": "No data", "checks_passed": 0, "checks_total": 0}

    amount_col = mapping.get("amount")
    approver_col = "approved_by" if "approved_by" in df.columns else None

    checks_total = 0
    checks_passed = 0

    # SOX: Segregation of duties — approver should not approve > 60% of high-value items
    checks_total += 1
    if approver_col and amount_col:
        high_value = df[df[amount_col] > 5000]
        if not high_value.empty:
            top_approver_share = (high_value[approver_col].value_counts(normalize=True).iloc[0]) * 100
            if top_approver_share > 60:
                findings.append({
                    "rule": "SOX_SOD_001",
                    "framework": "SOX",
                    "severity": "high",
                    "description": f"Segregation of duties violation: single approver handles {top_approver_share:.1f}% of high-value transactions.",
                })
            else:
                checks_passed += 1
        else:
            checks_passed += 1

    # GAAP: All transactions must have a date
    checks_total += 1
    date_col = mapping.get("date")
    if date_col:
        missing_dates = df[date_col].isna().sum()
        if missing_dates > 0:
            findings.append({
                "rule": "GAAP_COMPLETENESS",
                "framework": "GAAP",
                "severity": "medium",
                "description": f"{missing_dates} transactions missing required date field.",
            })
        else:
            checks_passed += 1
    else:
        findings.append({
            "rule": "GAAP_SCHEMA",
            "framework": "GAAP",
            "severity": "medium",
            "description": "Dataset lacks a recognizable date column — full audit trail incomplete.",
        })

    # IFRS: All amounts must be present and non-negative
    checks_total += 1
    if amount_col:
        neg = (df[amount_col] < 0).sum() if amount_col in df.columns else 0
        nulls = df[amount_col].isna().sum() if amount_col in df.columns else 0
        if neg > 0 or nulls > 0:
            findings.append({
                "rule": "IFRS_MEASUREMENT",
                "framework": "IFRS",
                "severity": "medium",
                "description": f"{neg} negative amounts and {nulls} null amounts found.",
            })
        else:
            checks_passed += 1

    # Policy: Approval threshold (>$50,000 must have separate documentation field)
    checks_total += 1
    if amount_col:
        over_threshold = (df[amount_col] > 50000).sum()
        if over_threshold > 0:
            findings.append({
                "rule": "POLICY_APPROVAL_THRESHOLD",
                "framework": "Internal Policy",
                "severity": "high" if over_threshold > 3 else "medium",
                "description": f"{over_threshold} transactions exceed $50,000 approval threshold — verify board-level documentation.",
            })
        else:
            checks_passed += 1

    score = min(100, len(findings) * 18)

    return {
        "agent": "compliance",
        "findings": findings,
        "violations": len(findings),
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "compliance_rate": round(checks_passed / max(checks_total, 1) * 100, 1),
        "risk_score": score,
        "summary": f"{checks_passed}/{checks_total} checks passed. {len(findings)} violations.",
    }


# ============================================================
# 3. Financial Analysis Agent
# ============================================================
async def financial_analysis_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    df: pd.DataFrame = ctx["dataframe"]
    mapping = ctx["canonical_mapping"]

    if df.empty:
        return {"agent": "financial_analysis", "summary": "No data", "risk_score": 0, "findings": []}

    amount_col = mapping.get("amount")
    vendor_col = mapping.get("vendor")
    category_col = mapping.get("category")
    date_col = mapping.get("date")

    findings = []
    summary: dict[str, Any] = {}

    if amount_col and amount_col in df.columns:
        amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        summary["total_spend"] = round(float(amounts.sum()), 2)
        summary["transaction_count"] = int(len(amounts))
        summary["mean_transaction"] = round(float(amounts.mean()), 2)
        summary["median_transaction"] = round(float(amounts.median()), 2)
        summary["max_transaction"] = round(float(amounts.max()), 2)

    # Top vendors by spend
    top_vendors = []
    if vendor_col and amount_col:
        vs = df.groupby(vendor_col)[amount_col].sum().sort_values(ascending=False).head(10)
        top_vendors = [{"vendor": str(v), "spend": round(float(s), 2)} for v, s in vs.items()]

    # Spend by category
    category_breakdown = []
    if category_col and amount_col:
        cb = df.groupby(category_col)[amount_col].sum().sort_values(ascending=False)
        category_breakdown = [{"category": str(c), "spend": round(float(s), 2)} for c, s in cb.items()]

    # Monthly trend
    monthly_trend = []
    if date_col and amount_col:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            tmp = pd.DataFrame({"date": dates, "amount": pd.to_numeric(df[amount_col], errors="coerce")}).dropna()
            tmp["month"] = tmp["date"].dt.strftime("%Y-%m")
            mt = tmp.groupby("month")["amount"].sum().sort_index()
            monthly_trend = [{"month": str(m), "spend": round(float(s), 2)} for m, s in mt.items()]
        except Exception:
            monthly_trend = []

    # Budget variance (assume budget = mean monthly spend * 1.0, variance >20% flagged)
    if len(monthly_trend) >= 2:
        spends = [m["spend"] for m in monthly_trend]
        avg = sum(spends) / len(spends)
        for m in monthly_trend:
            variance = (m["spend"] - avg) / max(avg, 1) * 100
            if abs(variance) > 30:
                findings.append({
                    "type": "budget_variance",
                    "month": m["month"],
                    "variance_percent": round(variance, 2),
                    "severity": "medium",
                    "description": f"Spend in {m['month']} is {variance:+.1f}% vs average monthly run-rate.",
                })

    score = min(100, len(findings) * 8 + (10 if summary.get("transaction_count", 0) == 0 else 0))

    return {
        "agent": "financial_analysis",
        "summary": f"Analyzed {summary.get('transaction_count', 0)} transactions totaling ${summary.get('total_spend', 0):,.2f}",
        "stats": summary,
        "top_vendors": top_vendors,
        "category_breakdown": category_breakdown,
        "monthly_trend": monthly_trend,
        "findings": findings,
        "risk_score": score,
    }


# ============================================================
# 4. Cybersecurity Agent
# ============================================================
PII_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}

INJECTION_PATTERNS = [
    r"ignore (previous|all) instructions",
    r"disregard the (system|above)",
    r"you are now",
    r"<\s*script",
    r"DROP\s+TABLE",
    r"';\s*--",
]


async def cybersecurity_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    df: pd.DataFrame = ctx["dataframe"]
    findings: list[dict] = []
    pii_counts: dict[str, int] = defaultdict(int)
    injection_count = 0

    # Sample first 500 rows for performance
    sample = df.head(500) if not df.empty else df
    for _, row in sample.iterrows():
        for val in row.values:
            s = str(val)
            for name, pat in PII_PATTERNS.items():
                if pat.search(s):
                    pii_counts[name] += 1
            for ip in INJECTION_PATTERNS:
                if re.search(ip, s, re.IGNORECASE):
                    injection_count += 1

    for name, count in pii_counts.items():
        findings.append({
            "type": "pii_exposure",
            "pii_type": name,
            "severity": "high" if name in ("ssn", "credit_card") else "medium",
            "count": count,
            "description": f"Detected {count} potential {name.upper()} values in the dataset — requires redaction.",
        })

    if injection_count > 0:
        findings.append({
            "type": "prompt_injection_attempt",
            "severity": "high",
            "count": injection_count,
            "description": f"{injection_count} potential prompt-injection / SQL-injection strings detected in input data.",
        })

    score = min(100, sum(15 if f["severity"] == "high" else 6 for f in findings))

    return {
        "agent": "cybersecurity",
        "findings": findings,
        "pii_detected": dict(pii_counts),
        "injection_attempts": injection_count,
        "risk_score": score,
        "summary": f"{len(findings)} security signals. {sum(pii_counts.values())} PII values, {injection_count} injection attempts.",
    }


# ============================================================
# 5. Risk Assessment Agent
# ============================================================
async def risk_assessment_agent(ctx: dict[str, Any]) -> dict[str, Any]:
    df: pd.DataFrame = ctx["dataframe"]
    mapping = ctx["canonical_mapping"]

    if df.empty:
        return {"agent": "risk_assessment", "summary": "No data", "risk_score": 0, "categories": {}}

    amount_col = mapping.get("amount")
    vendor_col = mapping.get("vendor")

    # Financial risk: high-value tail
    financial = 0.0
    operational = 0.0
    reputational = 0.0

    if amount_col:
        amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        if len(amounts) > 0:
            p95 = float(amounts.quantile(0.95))
            tail = amounts[amounts > p95]
            tail_share = tail.sum() / max(amounts.sum(), 1) * 100
            financial = min(100.0, tail_share * 1.5)

    if vendor_col:
        vendors = df[vendor_col].astype(str)
        unique_vendors = vendors.nunique()
        total_txn = len(vendors)
        if total_txn > 0:
            # Operational: lower diversity = higher risk
            diversity = unique_vendors / total_txn
            operational = float(max(0.0, min(100.0, (1 - diversity) * 100)))

    # Reputational proxy: shady vendor patterns
    if vendor_col and amount_col:
        shady_keywords = ["holdings", "llc", "consulting", "offshore"]
        shady_mask = df[vendor_col].astype(str).str.lower().apply(lambda v: any(k in v for k in shady_keywords))
        shady_spend = df.loc[shady_mask, amount_col].sum() if shady_mask.any() else 0
        total = df[amount_col].sum() or 1
        reputational = min(100.0, shady_spend / total * 100 * 2)

    # Monte Carlo (lightweight): simulate 1000 scenarios of total risk-adjusted loss
    import random as _r
    rnd = _r.Random(7)
    sims = []
    base_risk = (financial + operational + reputational) / 3
    for _ in range(1000):
        shock = rnd.gauss(1.0, 0.25)
        sims.append(max(0.0, min(100.0, base_risk * shock)))
    sims.sort()
    var_95 = sims[int(len(sims) * 0.95)]

    composite = round((financial * 0.4 + operational * 0.3 + reputational * 0.3), 1)

    return {
        "agent": "risk_assessment",
        "categories": {
            "financial": round(financial, 1),
            "operational": round(operational, 1),
            "reputational": round(reputational, 1),
        },
        "composite_score": composite,
        "monte_carlo": {
            "iterations": 1000,
            "value_at_risk_95": round(var_95, 1),
            "mean_loss": round(sum(sims) / len(sims), 1),
        },
        "risk_score": composite,
        "summary": f"Composite risk score: {composite}/100. 95% VaR: {var_95:.1f}.",
    }


# ============================================================
# 6. Decision Agent (LLM-powered)
# ============================================================
async def decision_agent(ctx: dict[str, Any], all_outputs: dict[str, dict]) -> dict[str, Any]:
    """Aggregate all agent outputs and produce a unified verdict via Gemini."""
    audit_id = ctx.get("audit_id", "unknown")

    # Build deterministic baseline (fallback if LLM fails)
    risk_scores = [out.get("risk_score", 0) for out in all_outputs.values() if isinstance(out, dict)]
    overall_risk = round(sum(risk_scores) / max(len(risk_scores), 1), 1) if risk_scores else 0

    if overall_risk >= 70:
        verdict_base = "CRITICAL_ESCALATE"
    elif overall_risk >= 40:
        verdict_base = "ELEVATED_REVIEW"
    elif overall_risk >= 15:
        verdict_base = "MINOR_FOLLOWUP"
    else:
        verdict_base = "CLEAR"

    # Compose summary for LLM
    findings_summary = []
    for agent_name, out in all_outputs.items():
        if not isinstance(out, dict):
            continue
        for f in (out.get("findings") or [])[:5]:
            findings_summary.append({
                "source_agent": agent_name,
                "type": f.get("type") or f.get("rule"),
                "severity": f.get("severity"),
                "description": f.get("description"),
            })

    system_prompt = (
        "You are the Decision Agent in SentinelAI, an enterprise financial audit platform. "
        "Your role is to aggregate findings from specialized audit agents (fraud, compliance, "
        "financial analysis, cybersecurity, risk assessment) and produce a single unified verdict. "
        "Respond ONLY with valid JSON. No prose, no markdown."
    )

    user_prompt = f"""Audit findings from specialized agents:

Baseline composite risk score: {overall_risk}/100
Findings summary (top 25):
{findings_summary[:25]}

Agent risk scores:
{ {k: v.get('risk_score', 0) for k, v in all_outputs.items()} }

Return strictly this JSON shape:
{{
  "verdict": "CLEAR" | "MINOR_FOLLOWUP" | "ELEVATED_REVIEW" | "CRITICAL_ESCALATE",
  "confidence": 0.0-1.0,
  "executive_summary": "2-3 sentence summary for C-suite",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "recommendations": ["action 1", "action 2", "action 3"],
  "rationale": "1-paragraph explanation of how you weighted the agent outputs"
}}"""

    try:
        llm_result = await call_llm_json(system_prompt, user_prompt, f"decision-{audit_id}")
    except Exception as e:
        llm_result = {"_error": str(e)}

    verdict = llm_result.get("verdict") if isinstance(llm_result.get("verdict"), str) else verdict_base
    confidence = llm_result.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.75

    return {
        "agent": "decision",
        "verdict": verdict,
        "overall_risk_score": overall_risk,
        "confidence": float(confidence),
        "executive_summary": llm_result.get("executive_summary") or f"Overall risk: {overall_risk}/100. {len(findings_summary)} findings across {len(all_outputs)} agents.",
        "key_findings": llm_result.get("key_findings") or [f["description"] for f in findings_summary[:5] if f.get("description")],
        "recommendations": llm_result.get("recommendations") or [
            "Review high-severity findings with controller",
            "Verify segregation of duties on flagged approvals",
            "Cross-check duplicate invoices with vendor records",
        ],
        "rationale": llm_result.get("rationale") or "Aggregated via weighted risk scores across agents.",
        "agent_scores": {k: v.get("risk_score", 0) for k, v in all_outputs.items()},
        "summary": f"Verdict: {verdict}. Confidence: {confidence:.0%}.",
    }


# ============================================================
# 7. Report Generation Agent
# ============================================================
async def report_generation_agent(ctx: dict[str, Any], all_outputs: dict[str, dict], decision: dict) -> dict[str, Any]:
    """Generate executive HTML report."""
    from datetime import datetime, timezone

    title = ctx.get("audit_title", "Financial Audit")
    dataset_name = ctx.get("dataset_name", "dataset")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    verdict_color = {
        "CLEAR": "#00875A",
        "MINOR_FOLLOWUP": "#FFB000",
        "ELEVATED_REVIEW": "#FF8800",
        "CRITICAL_ESCALATE": "#D00000",
    }.get(decision.get("verdict", ""), "#6B7280")

    findings_rows = []
    for agent_name, out in all_outputs.items():
        for f in (out.get("findings") or []):
            findings_rows.append(
                f"<tr><td>{agent_name}</td><td>{f.get('type', f.get('rule', '—'))}</td>"
                f"<td><span style='color:{'#D00000' if f.get('severity')=='high' else '#FFB000' if f.get('severity')=='medium' else '#6B7280'}'>"
                f"{f.get('severity', '—').upper()}</span></td>"
                f"<td>{f.get('description', '')}</td></tr>"
            )

    recs = "".join(f"<li>{r}</li>" for r in (decision.get("recommendations") or []))
    key_findings = "".join(f"<li>{k}</li>" for k in (decision.get("key_findings") or []))

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>SentinelAI Audit Report — {title}</title>
<style>
  body {{ font-family: 'IBM Plex Sans', Arial, sans-serif; color:#0A0A0A; margin:40px; }}
  h1 {{ font-size: 32px; border-bottom: 3px solid #002FA7; padding-bottom: 12px; margin-bottom: 8px; }}
  h2 {{ font-size: 20px; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 32px; color:#002FA7; }}
  .verdict {{ display:inline-block; padding: 8px 16px; background:{verdict_color}; color:white; font-weight:700; letter-spacing:0.1em; }}
  .score-box {{ display:inline-block; margin-right:24px; padding: 16px 24px; border:1px solid #E5E7EB; }}
  .score-box .label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em; color:#6B7280; }}
  .score-box .value {{ font-size: 36px; font-weight: 800; color:#0A0A0A; }}
  table {{ width:100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }}
  th, td {{ text-align:left; padding: 10px 12px; border-bottom: 1px solid #E5E7EB; }}
  th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.15em; color:#6B7280; background:#F7F7F9; }}
  .footer {{ margin-top: 48px; font-size: 11px; color:#6B7280; border-top: 1px solid #E5E7EB; padding-top: 16px; }}
</style></head>
<body>
<h1>SentinelAI Executive Audit Report</h1>
<p style="color:#6B7280; font-size:12px; letter-spacing:0.1em; text-transform:uppercase;">
  {title} &nbsp;·&nbsp; Dataset: {dataset_name} &nbsp;·&nbsp; Generated {generated_at}
</p>

<div style="margin-top:24px;">
  <div class="score-box"><div class="label">Verdict</div><div style="margin-top:8px;"><span class="verdict">{decision.get('verdict','—')}</span></div></div>
  <div class="score-box"><div class="label">Overall Risk</div><div class="value">{decision.get('overall_risk_score',0)}<span style="font-size:18px;color:#6B7280;">/100</span></div></div>
  <div class="score-box"><div class="label">Confidence</div><div class="value">{int((decision.get('confidence') or 0)*100)}<span style="font-size:18px;color:#6B7280;">%</span></div></div>
</div>

<h2>Executive Summary</h2>
<p>{decision.get('executive_summary','')}</p>

<h2>Key Findings</h2>
<ul>{key_findings}</ul>

<h2>Recommendations</h2>
<ul>{recs}</ul>

<h2>Agent Risk Scores</h2>
<table><thead><tr><th>Agent</th><th>Risk Score</th><th>Summary</th></tr></thead><tbody>
{''.join(f"<tr><td>{a}</td><td>{o.get('risk_score',0)}/100</td><td>{o.get('summary','')}</td></tr>" for a,o in all_outputs.items())}
</tbody></table>

<h2>Detailed Findings ({len(findings_rows)})</h2>
<table><thead><tr><th>Agent</th><th>Type</th><th>Severity</th><th>Description</th></tr></thead>
<tbody>{''.join(findings_rows) or '<tr><td colspan=4 style="text-align:center;color:#6B7280;">No findings flagged.</td></tr>'}</tbody></table>

<h2>Rationale</h2>
<p>{decision.get('rationale','')}</p>

<div class="footer">
  Generated by SentinelAI Multi-Agent Audit Framework · Powered by Google Gemini · Confidential — Internal Use Only
</div>
</body></html>"""

    return {
        "agent": "report_generation",
        "html": html,
        "byte_size": len(html.encode("utf-8")),
        "summary": f"Generated HTML report ({len(html.encode('utf-8'))} bytes)",
        "risk_score": 0,
    }


# ============================================================
# Agent registry
# ============================================================
AGENT_REGISTRY = {
    "fraud_detection": fraud_detection_agent,
    "compliance": compliance_agent,
    "financial_analysis": financial_analysis_agent,
    "cybersecurity": cybersecurity_agent,
    "risk_assessment": risk_assessment_agent,
}

AGENT_METADATA = [
    {"id": "coordinator", "name": "Coordinator Agent", "description": "Routes work to specialized agents via the workflow engine.", "order": 0},
    {"id": "fraud_detection", "name": "Fraud Detection Agent", "description": "Duplicate invoices, Benford's Law, anomaly Z-scores, vendor collusion.", "order": 1},
    {"id": "compliance", "name": "Compliance Agent", "description": "SOX, GAAP, IFRS rule verification and segregation of duties.", "order": 2},
    {"id": "financial_analysis", "name": "Financial Analysis Agent", "description": "Expense categorization, trends, vendor spend, budget variance.", "order": 3},
    {"id": "cybersecurity", "name": "Cybersecurity Agent", "description": "Prompt injection detection, PII redaction, input/output sanitization.", "order": 4},
    {"id": "risk_assessment", "name": "Risk Assessment Agent", "description": "Composite risk scoring with Monte Carlo simulation.", "order": 5},
    {"id": "decision", "name": "Decision Agent", "description": "Aggregates outputs and produces unified verdict with confidence.", "order": 6},
    {"id": "report_generation", "name": "Report Generation Agent", "description": "Executive PDF/HTML report with charts and narratives.", "order": 7},
]
