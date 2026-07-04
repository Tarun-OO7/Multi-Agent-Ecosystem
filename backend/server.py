"""SentinelAI — Multi-Agent Financial Intelligence Audit Framework.

FastAPI backend with JWT auth, 8 specialized agents, MongoDB persistence,
SSE streaming of agent progress, and PDF report export.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from dotenv import load_dotenv
from fastapi import (
    APIRouter, BackgroundTasks, Depends, FastAPI, File, Form, HTTPException,
    Request, UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import (  # noqa: E402
    TokenData, create_access_token, create_refresh_token, decode_token,
    get_current_user, hash_password, require_role, verify_password,
)
from agents import AGENT_METADATA  # noqa: E402
from file_processor import parse_csv, parse_pdf  # noqa: E402
from models import (  # noqa: E402
    AuditCreate, AuditLogEntry, AuditRecord, DatasetMeta, RefreshRequest,
    TokenResponse, UserCreate, UserLogin, UserPublic, gen_id, utc_now_iso,
)
from pdf_export import build_pdf  # noqa: E402
from sample_data import generate_sample_csv_bytes  # noqa: E402
from workflow import execute_audit  # noqa: E402


# ============================================================
# Logging
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger("sentinelai")


# ============================================================
# MongoDB
# ============================================================
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_col = db["users"]
datasets_col = db["datasets"]
audits_col = db["audits"]
audit_logs_col = db["audit_logs"]

# In-memory dataframe cache (parsed datasets - not persisted to mongo for size)
_dataframe_cache: dict[str, Any] = {}
_dataframe_cache_refs: dict[str, int] = {}

# In-memory SSE event queues (per audit_id)
_audit_queues: dict[str, asyncio.Queue] = {}

# Token-bucket rate limit (per user_id)
_rate_buckets: dict[str, dict[str, float]] = {}
RATE_LIMIT_TOKENS = 60
RATE_LIMIT_WINDOW = 60  # seconds


# ============================================================
# App + middleware
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", msg="Ensuring MongoDB indexes")
    try:
        await users_col.create_index("email", unique=True)
        await users_col.create_index("id", unique=True)
        await datasets_col.create_index("id", unique=True)
        await datasets_col.create_index("user_id")
        await audits_col.create_index("id", unique=True)
        await audits_col.create_index("user_id")
        await audits_col.create_index("status")
        await audit_logs_col.create_index("audit_id")
        await audit_logs_col.create_index([("timestamp", -1)])
        log.info("startup", msg="MongoDB indexes created successfully")
    except Exception as e:
        log.error("startup_failed", error=str(e), msg="Failed to create MongoDB indexes")
        raise e
        
    yield
    client.close()

app = FastAPI(title="SentinelAI Audit Framework", version="1.0.0", lifespan=lifespan)
api = APIRouter(prefix="/api")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        duration = int((time.time() - started) * 1000)
        log.error("request_failed", request_id=request_id, path=request.url.path, error=str(e), duration_ms=duration)
        raise
    duration = int((time.time() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    # Persist audit log asynchronously
    try:
        if request.url.path.startswith("/api"):
            entry = AuditLogEntry(
                request_id=request_id,
                user_id=getattr(request.state, "user_id", None),
                user_email=getattr(request.state, "user_email", None),
                action=f"{request.method} {request.url.path}",
                resource=request.url.path,
                status_code=response.status_code,
                method=request.method,
                path=request.url.path,
                duration_ms=duration,
            )
            await audit_logs_col.insert_one(entry.model_dump())
    except Exception:
        pass
    return response


# ============================================================
# Helpers
# ============================================================
def _strip_id(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


async def _rate_limit(user_id: str):
    now = time.time()
    bucket = _rate_buckets.get(user_id)
    if not bucket or now - bucket["start"] > RATE_LIMIT_WINDOW:
        _rate_buckets[user_id] = {"start": now, "count": 1}
        return
    bucket["count"] += 1
    if bucket["count"] > RATE_LIMIT_TOKENS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded — slow down.")


# ============================================================
# Auth routes
# ============================================================
class MessageOut(BaseModel):
    message: str


@api.post("/auth/register", response_model=UserPublic, status_code=201)
async def register(payload: UserCreate):
    existing = await users_col.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    # First user becomes admin
    user_count = await users_col.count_documents({})
    role = "admin" if user_count == 0 else payload.role
    user_doc = {
        "id": gen_id(),
        "email": payload.email,
        "full_name": payload.full_name,
        "role": role,
        "password_hash": hash_password(payload.password),
        "created_at": utc_now_iso(),
        "active": True,
    }
    await users_col.insert_one(user_doc)
    log.info("user_registered", user_id=user_doc["id"], email=payload.email, role=role)
    return UserPublic(**user_doc)


@api.post("/auth/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    user = await users_col.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    access = create_access_token(user["id"], user["email"], user["role"])
    refresh = create_refresh_token(user["id"], user["email"], user["role"])
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        user=UserPublic(**_strip_id(user)),
    )


@api.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest):
    td = decode_token(payload.refresh_token)
    if td.type != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    user = await users_col.find_one({"id": td.sub})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"], user["role"]),
        refresh_token=create_refresh_token(user["id"], user["email"], user["role"]),
        user=UserPublic(**_strip_id(user)),
    )


@api.get("/auth/me", response_model=UserPublic)
async def me(user: TokenData = Depends(get_current_user)):
    doc = await users_col.find_one({"id": user.sub})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**_strip_id(doc))


# ============================================================
# Agent metadata
# ============================================================
@api.get("/agents")
async def list_agents():
    return {"agents": AGENT_METADATA}


# ============================================================
# Dataset upload
# ============================================================
@api.post("/datasets/upload", response_model=DatasetMeta)
async def upload_dataset(
    file: UploadFile = File(...),
    user: TokenData = Depends(require_role("auditor")),
):
    await _rate_limit(user.sub)

    content = await file.read()
    size = len(content)
    if size > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    filename = file.filename or "unnamed"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in ("csv", "pdf"):
        raise HTTPException(status_code=400, detail="Only .csv and .pdf supported")

    if ext == "csv":
        result = parse_csv(content)
    else:
        result = parse_pdf(content)

    if not result.get("ok"):
        meta = DatasetMeta(
            user_id=user.sub, filename=filename, file_type=ext,
            size_bytes=size, status="failed", error=result.get("error", "parse failed"),
        )
        await datasets_col.insert_one(meta.model_dump())
        raise HTTPException(status_code=400, detail=result.get("error", "Parse failed"))

    meta = DatasetMeta(
        user_id=user.sub,
        filename=filename,
        file_type=ext,
        row_count=result["row_count"],
        column_count=result["column_count"],
        columns=result["columns"],
        preview=result["preview"],
        size_bytes=size,
    )
    # Cache the dataframe in memory for audits
    _dataframe_cache[meta.id] = {
        "dataframe": result["dataframe"],
        "canonical_mapping": result["canonical_mapping"],
        "filename": filename,
    }
    await datasets_col.insert_one(meta.model_dump())
    log.info("dataset_uploaded", dataset_id=meta.id, rows=meta.row_count, user=user.email)
    return meta


@api.post("/datasets/sample", response_model=DatasetMeta)
async def create_sample_dataset(user: TokenData = Depends(require_role("auditor"))):
    """Generate and ingest a synthetic financial dataset for demos."""
    content = generate_sample_csv_bytes(250)
    result = parse_csv(content)
    meta = DatasetMeta(
        user_id=user.sub,
        filename="sentinelai_sample_invoices.csv",
        file_type="csv",
        row_count=result["row_count"],
        column_count=result["column_count"],
        columns=result["columns"],
        preview=result["preview"],
        size_bytes=len(content),
    )
    _dataframe_cache[meta.id] = {
        "dataframe": result["dataframe"],
        "canonical_mapping": result["canonical_mapping"],
        "filename": meta.filename,
    }
    await datasets_col.insert_one(meta.model_dump())
    return meta


@api.get("/datasets")
async def list_datasets(user: TokenData = Depends(get_current_user)):
    cursor = datasets_col.find({"user_id": user.sub}, {"_id": 0}).sort("uploaded_at", -1).limit(50)
    return {"datasets": await cursor.to_list(length=50)}


@api.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, user: TokenData = Depends(get_current_user)):
    doc = await datasets_col.find_one({"id": dataset_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return doc


# ============================================================
# Audit execution
# ============================================================
async def _run_audit_task(audit_id: str, ctx: dict, scope: list[str], queue: asyncio.Queue):
    """Background task to execute the audit workflow."""
    started_at = utc_now_iso()
    await audits_col.update_one(
        {"id": audit_id},
        {"$set": {"status": "running", "started_at": started_at}},
    )
    dataset_id = ctx.get("dataset_id")
    try:
        result = await execute_audit(ctx, scope, queue)
        completed_at = utc_now_iso()
        await audits_col.update_one(
            {"id": audit_id},
            {"$set": {
                "status": "completed",
                "completed_at": completed_at,
                "duration_ms": result["duration_ms"],
                "agents": result["agents"],
                "decision": result["decision"],
                "report_html": result["report_html"],
                "overall_risk_score": result["overall_risk_score"],
                "overall_verdict": result["overall_verdict"],
                "confidence": result["confidence"],
                "agent_outputs": result["agent_outputs"],
            }},
        )
    except Exception as e:
        log.error("audit_failed", audit_id=audit_id, error=str(e))
        await audits_col.update_one(
            {"id": audit_id},
            {"$set": {"status": "failed", "error": str(e), "completed_at": utc_now_iso()}},
        )
        await queue.put({"type": "workflow_status", "status": "failed", "error": str(e)})
        await queue.put({"type": "done"})
    finally:
        if dataset_id:
            _dataframe_cache_refs[dataset_id] = _dataframe_cache_refs.get(dataset_id, 1) - 1
            if _dataframe_cache_refs.get(dataset_id, 0) <= 0:
                _dataframe_cache.pop(dataset_id, None)
                _dataframe_cache_refs.pop(dataset_id, None)


@api.post("/audits", status_code=201)
async def create_audit(
    payload: AuditCreate,
    bg: BackgroundTasks,
    user: TokenData = Depends(require_role("auditor")),
):
    await _rate_limit(user.sub)

    ds_doc = await datasets_col.find_one({"id": payload.dataset_id}, {"_id": 0})
    if not ds_doc:
        raise HTTPException(status_code=404, detail="Dataset not found")

    cached = _dataframe_cache.get(payload.dataset_id)
    if not cached:
        raise HTTPException(
            status_code=410,
            detail="Dataset content expired — please re-upload to run audit.",
        )

    audit = AuditRecord(
        user_id=user.sub,
        user_email=user.email,
        dataset_id=payload.dataset_id,
        title=payload.title,
        scope=payload.scope,
        status="queued",
    )
    await audits_col.insert_one(audit.model_dump())

    _dataframe_cache_refs[payload.dataset_id] = _dataframe_cache_refs.get(payload.dataset_id, 0) + 1

    queue: asyncio.Queue = asyncio.Queue()
    _audit_queues[audit.id] = queue

    ctx = {
        "audit_id": audit.id,
        "audit_title": audit.title,
        "dataset_id": payload.dataset_id,
        "dataset_name": cached["filename"],
        "dataframe": cached["dataframe"],
        "canonical_mapping": cached["canonical_mapping"],
    }
    bg.add_task(_run_audit_task, audit.id, ctx, payload.scope, queue)
    log.info("audit_created", audit_id=audit.id, user=user.email, scope=payload.scope)
    return {"audit_id": audit.id, "status": "queued"}


@api.get("/audits")
async def list_audits(user: TokenData = Depends(get_current_user)):
    q = {} if user.role == "admin" else {"user_id": user.sub}
    cursor = audits_col.find(q, {"_id": 0, "report_html": 0, "agent_outputs": 0}).sort("created_at", -1).limit(100)
    return {"audits": await cursor.to_list(length=100)}


@api.get("/audits/{audit_id}")
async def get_audit(audit_id: str, user: TokenData = Depends(get_current_user)):
    doc = await audits_col.find_one({"id": audit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Audit not found")
    if user.role != "admin" and doc.get("user_id") != user.sub:
        raise HTTPException(status_code=403, detail="Forbidden")
    # Don't ship report_html in detail (use export endpoint)
    doc.pop("report_html", None)
    return doc


@api.get("/audits/{audit_id}/stream")
async def stream_audit(audit_id: str, request: Request, token: Optional[str] = None):
    """SSE stream of agent execution events. Token passed as query param for EventSource."""
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    td = decode_token(token)
    if td.type != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    doc = await audits_col.find_one({"id": audit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Audit not found")
    if td.role != "admin" and doc.get("user_id") != td.sub:
        raise HTTPException(status_code=403, detail="Forbidden")

    queue = _audit_queues.get(audit_id)

    async def event_gen():
        try:
            # If audit already finished, replay terminal state
            if not queue:
                current = await audits_col.find_one({"id": audit_id}, {"_id": 0})
                yield f"data: {json.dumps({'type': 'snapshot', 'audit': {k: v for k, v in (current or {}).items() if k != 'report_html' and k != 'agent_outputs'}})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=10)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("type") == "done":
                    break
        finally:
            _audit_queues.pop(audit_id, None)

    return StreamingResponse(
        event_gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@api.get("/audits/{audit_id}/report.pdf")
async def export_audit_pdf(audit_id: str, user: TokenData = Depends(get_current_user)):
    doc = await audits_col.find_one({"id": audit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Audit not found")
    if user.role != "admin" and doc.get("user_id") != user.sub:
        raise HTTPException(status_code=403, detail="Forbidden")
    if doc.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Audit not completed")
    pdf_bytes = build_pdf(doc)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sentinelai-audit-{audit_id}.pdf"'},
    )


@api.get("/audits/{audit_id}/report.html", response_class=Response)
async def export_audit_html(audit_id: str, user: TokenData = Depends(get_current_user)):
    doc = await audits_col.find_one({"id": audit_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Audit not found")
    if user.role != "admin" and doc.get("user_id") != user.sub:
        raise HTTPException(status_code=403, detail="Forbidden")
    html = doc.get("report_html") or "<html><body><h1>No report</h1></body></html>"
    return Response(content=html, media_type="text/html")


# ============================================================
# Admin
# ============================================================
@api.get("/admin/users")
async def admin_list_users(user: TokenData = Depends(require_role("admin"))):
    cursor = users_col.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).limit(200)
    return {"users": await cursor.to_list(length=200)}


@api.patch("/admin/users/{user_id}")
async def admin_update_user(
    user_id: str,
    role: Optional[str] = Form(None),
    active: Optional[bool] = Form(None),
    user: TokenData = Depends(require_role("admin")),
):
    updates: dict[str, Any] = {}
    if role is not None:
        if role not in ("admin", "auditor", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role")
        updates["role"] = role
    if active is not None:
        updates["active"] = active
    if not updates:
        raise HTTPException(status_code=400, detail="No updates")
    result = await users_col.update_one({"id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}


@api.get("/admin/audit-logs")
async def admin_list_logs(user: TokenData = Depends(require_role("admin"))):
    cursor = audit_logs_col.find({}, {"_id": 0}).sort("timestamp", -1).limit(200)
    return {"logs": await cursor.to_list(length=200)}


# ============================================================
# Health & metrics
# ============================================================
@api.get("/health")
async def health():
    try:
        await db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False
    return {
        "status": "ok" if mongo_ok else "degraded",
        "mongo": mongo_ok,
        "version": "1.0.0",
        "timestamp": utc_now_iso(),
    }


@api.get("/metrics")
async def metrics(user: TokenData = Depends(require_role("admin"))):
    return {
        "total_users": await users_col.count_documents({}),
        "total_datasets": await datasets_col.count_documents({}),
        "total_audits": await audits_col.count_documents({}),
        "audits_completed": await audits_col.count_documents({"status": "completed"}),
        "audits_running": await audits_col.count_documents({"status": "running"}),
        "audits_failed": await audits_col.count_documents({"status": "failed"}),
    }


# ============================================================
# Dashboard summary
# ============================================================
@api.get("/dashboard/summary")
async def dashboard_summary(user: TokenData = Depends(get_current_user)):
    q = {} if user.role == "admin" else {"user_id": user.sub}
    total = await audits_col.count_documents(q)
    completed = await audits_col.count_documents({**q, "status": "completed"})
    running = await audits_col.count_documents({**q, "status": "running"})
    failed = await audits_col.count_documents({**q, "status": "failed"})
    recent = await audits_col.find(q, {"_id": 0, "report_html": 0, "agent_outputs": 0, "agents": 0}).sort("created_at", -1).limit(5).to_list(length=5)

    # Average risk score of completed audits
    pipeline = [
        {"$match": {**q, "status": "completed", "overall_risk_score": {"$ne": None}}},
        {"$group": {"_id": None, "avg": {"$avg": "$overall_risk_score"}, "count": {"$sum": 1}}},
    ]
    agg = await audits_col.aggregate(pipeline).to_list(length=1)
    avg_risk = round(agg[0]["avg"], 1) if agg else 0

    # Verdict breakdown
    vp = [{"$match": {**q, "overall_verdict": {"$ne": None}}}, {"$group": {"_id": "$overall_verdict", "count": {"$sum": 1}}}]
    verdicts_agg = await audits_col.aggregate(vp).to_list(length=10)
    verdicts = {v["_id"]: v["count"] for v in verdicts_agg}

    return {
        "total_audits": total,
        "completed": completed,
        "running": running,
        "failed": failed,
        "average_risk_score": avg_risk,
        "verdicts": verdicts,
        "recent_audits": recent,
        "total_datasets": await datasets_col.count_documents(q),
    }


# ============================================================
# Mount router + CORS
# ============================================================
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.get("/")
async def root_redirect():
    return {"service": "SentinelAI", "version": "1.0.0", "docs": "/docs"}
