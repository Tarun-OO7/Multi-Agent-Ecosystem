"""Pydantic models for the SentinelAI platform."""
from datetime import datetime, timezone
from typing import Any, Optional
import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_id() -> str:
    return str(uuid.uuid4())


# ============ USER ============
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="viewer", pattern="^(admin|auditor|viewer)$")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    full_name: str
    role: str
    created_at: str
    active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str


# ============ FILES & DATASETS ============
class DatasetMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    user_id: str
    filename: str
    file_type: str  # csv | pdf
    row_count: int = 0
    column_count: int = 0
    columns: list[str] = []
    preview: list[dict[str, Any]] = []
    uploaded_at: str = Field(default_factory=utc_now_iso)
    size_bytes: int = 0
    status: str = "ready"  # ready | failed
    error: Optional[str] = None


# ============ AUDIT ============
class AuditCreate(BaseModel):
    dataset_id: str
    scope: list[str] = Field(default_factory=lambda: ["fraud", "compliance", "financial", "risk", "cybersecurity"])
    title: str = "Untitled Audit"


class AgentExecution(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent: str
    status: str = "pending"  # pending | running | completed | failed | skipped
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    tokens_used: int = 0
    retries: int = 0


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    user_id: str
    user_email: str
    dataset_id: str
    title: str
    scope: list[str]
    status: str = "queued"  # queued | running | completed | failed
    created_at: str = Field(default_factory=utc_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    agents: list[AgentExecution] = []
    decision: Optional[dict[str, Any]] = None
    report_html: Optional[str] = None
    overall_risk_score: Optional[float] = None  # 0-100
    overall_verdict: Optional[str] = None
    confidence: Optional[float] = None


# ============ AUDIT LOG ============
class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=gen_id)
    request_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource: Optional[str] = None
    status_code: int
    method: str
    path: str
    duration_ms: int = 0
