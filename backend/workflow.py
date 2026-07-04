"""Workflow engine for SentinelAI multi-agent orchestration.

Features:
- Dependency graph (specialized agents in parallel, then decision, then report)
- Retry with exponential backoff
- Per-agent timeout
- Real-time event streaming via asyncio.Queue
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable

from agents import AGENT_REGISTRY, decision_agent, report_generation_agent


SCOPE_TO_AGENTS = {
    "fraud": ["fraud_detection"],
    "compliance": ["compliance"],
    "financial": ["financial_analysis"],
    "cybersecurity": ["cybersecurity"],
    "risk": ["risk_assessment"],
}

DEFAULT_TIMEOUT_S = 60
MAX_RETRIES = 2


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_with_retry(agent_fn: Callable, ctx: dict, name: str, on_event) -> dict:
    """Run a single agent with retry + timeout. Emits status events."""
    attempt = 0
    last_error: str | None = None
    started = time.time()
    await on_event({"type": "agent_status", "agent": name, "status": "running", "ts": utc_iso()})

    while attempt <= MAX_RETRIES:
        try:
            output = await asyncio.wait_for(agent_fn(ctx), timeout=DEFAULT_TIMEOUT_S)
            duration_ms = int((time.time() - started) * 1000)
            await on_event({
                "type": "agent_status", "agent": name, "status": "completed",
                "duration_ms": duration_ms, "risk_score": output.get("risk_score", 0),
                "summary": output.get("summary", ""), "ts": utc_iso(),
            })
            return {
                "agent": name, "status": "completed", "duration_ms": duration_ms,
                "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
                "completed_at": utc_iso(), "output": output, "retries": attempt,
            }
        except asyncio.TimeoutError:
            last_error = "timeout"
        except Exception as e:
            last_error = str(e)

        attempt += 1
        if attempt <= MAX_RETRIES:
            await on_event({"type": "agent_status", "agent": name, "status": "retrying",
                            "attempt": attempt, "error": last_error, "ts": utc_iso()})
            await asyncio.sleep(0.5 * (2 ** attempt))

    duration_ms = int((time.time() - started) * 1000)
    await on_event({"type": "agent_status", "agent": name, "status": "failed",
                    "error": last_error, "ts": utc_iso()})
    return {
        "agent": name, "status": "failed", "duration_ms": duration_ms,
        "started_at": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        "completed_at": utc_iso(), "output": None, "error": last_error, "retries": attempt,
    }


async def execute_audit(ctx: dict, scope: list[str], event_queue: asyncio.Queue) -> dict:
    """Run the full audit workflow.

    ctx: { dataframe, canonical_mapping, audit_id, audit_title, dataset_name, ... }
    scope: list of scope keys (fraud, compliance, financial, risk, cybersecurity)
    """
    started_at = time.time()
    agent_executions: list[dict] = []

    async def emit(ev: dict):
        await event_queue.put(ev)

    await emit({"type": "workflow_status", "status": "running", "ts": utc_iso()})
    await emit({"type": "agent_status", "agent": "coordinator", "status": "running", "ts": utc_iso()})

    # Resolve which specialized agents to run
    agent_ids: list[str] = []
    for s in scope:
        for aid in SCOPE_TO_AGENTS.get(s, []):
            if aid not in agent_ids:
                agent_ids.append(aid)
    if not agent_ids:
        agent_ids = list(AGENT_REGISTRY.keys())

    await emit({"type": "agent_status", "agent": "coordinator", "status": "completed",
                "summary": f"Routing to {len(agent_ids)} specialized agents.", "ts": utc_iso()})

    # Run specialized agents in parallel
    tasks = [run_with_retry(AGENT_REGISTRY[aid], ctx, aid, emit) for aid in agent_ids]
    results = await asyncio.gather(*tasks)
    agent_executions.extend(results)

    # Build outputs dict for downstream agents
    all_outputs = {r["agent"]: (r["output"] or {}) for r in results if r["status"] == "completed"}

    # Decision agent
    decision_started = time.time()
    await emit({"type": "agent_status", "agent": "decision", "status": "running", "ts": utc_iso()})
    try:
        decision_out = await asyncio.wait_for(decision_agent(ctx, all_outputs), timeout=90)
        decision_duration = int((time.time() - decision_started) * 1000)
        agent_executions.append({
            "agent": "decision", "status": "completed", "duration_ms": decision_duration,
            "started_at": datetime.fromtimestamp(decision_started, timezone.utc).isoformat(),
            "completed_at": utc_iso(), "output": decision_out, "retries": 0,
        })
        await emit({"type": "agent_status", "agent": "decision", "status": "completed",
                    "duration_ms": decision_duration, "summary": decision_out.get("summary", ""),
                    "verdict": decision_out.get("verdict"), "ts": utc_iso()})
    except Exception as e:
        decision_out = {"verdict": "ELEVATED_REVIEW", "overall_risk_score": 50, "confidence": 0.5,
                        "executive_summary": "Decision Agent failed; fallback verdict used.",
                        "key_findings": [], "recommendations": [], "rationale": str(e)}
        agent_executions.append({
            "agent": "decision", "status": "failed", "duration_ms": int((time.time() - decision_started) * 1000),
            "started_at": datetime.fromtimestamp(decision_started, timezone.utc).isoformat(),
            "completed_at": utc_iso(), "output": decision_out, "error": str(e), "retries": 0,
        })
        await emit({"type": "agent_status", "agent": "decision", "status": "failed", "error": str(e), "ts": utc_iso()})

    # Report generation agent
    report_started = time.time()
    await emit({"type": "agent_status", "agent": "report_generation", "status": "running", "ts": utc_iso()})
    try:
        report_out = await asyncio.wait_for(report_generation_agent(ctx, all_outputs, decision_out), timeout=30)
        report_duration = int((time.time() - report_started) * 1000)
        agent_executions.append({
            "agent": "report_generation", "status": "completed", "duration_ms": report_duration,
            "started_at": datetime.fromtimestamp(report_started, timezone.utc).isoformat(),
            "completed_at": utc_iso(), "output": {"summary": report_out["summary"], "byte_size": report_out["byte_size"]},
            "retries": 0,
        })
        await emit({"type": "agent_status", "agent": "report_generation", "status": "completed",
                    "duration_ms": report_duration, "summary": report_out["summary"], "ts": utc_iso()})
    except Exception as e:
        report_out = {"html": "<html><body><h1>Report generation failed</h1></body></html>", "byte_size": 0}
        agent_executions.append({
            "agent": "report_generation", "status": "failed", "error": str(e),
            "duration_ms": int((time.time() - report_started) * 1000),
            "started_at": datetime.fromtimestamp(report_started, timezone.utc).isoformat(),
            "completed_at": utc_iso(), "output": None, "retries": 0,
        })
        await emit({"type": "agent_status", "agent": "report_generation", "status": "failed", "error": str(e), "ts": utc_iso()})

    duration_ms = int((time.time() - started_at) * 1000)
    final = {
        "status": "completed",
        "duration_ms": duration_ms,
        "agents": agent_executions,
        "decision": decision_out,
        "report_html": report_out["html"],
        "overall_risk_score": decision_out.get("overall_risk_score", 0),
        "overall_verdict": decision_out.get("verdict"),
        "confidence": decision_out.get("confidence"),
        "agent_outputs": all_outputs,
    }
    await emit({"type": "workflow_status", "status": "completed", "duration_ms": duration_ms,
                "verdict": decision_out.get("verdict"),
                "overall_risk_score": decision_out.get("overall_risk_score", 0),
                "ts": utc_iso()})
    await emit({"type": "done"})
    return final
