# SentinelAI: A Multi-Agent Financial Intelligence Audit Framework

Building an Explainable Enterprise Audit Platform Using Google Gemini, Custom Multi-Agent Orchestration, MCP, and Responsible AI

• **Track**: Agents for Business
• **Project Repository**: https://github.com/Tarun-OO7/Multi-Agent-Ecosystem

---

## Overview

Financial auditing is a high-stakes corporate function responsible for protecting institutional integrity, detecting fraud, and ensuring regulatory compliance. Despite decades of investment in enterprise resource planning systems, most audit teams still rely on manual, sample-based spot-checks — a structural bottleneck that leaves organizations exposed to fraud patterns buried deep inside massive transactional datasets.

SentinelAI takes a different approach: instead of sampling a fraction of the ledger, it interrogates all of it.

Rather than routing an entire audit through a single, fragile LLM prompt, SentinelAI splits the work across a set of specialized, purpose-built agents — each responsible for one analytical lens — coordinated by a custom orchestration engine we built ourselves rather than adopting off-the-shelf agent tooling. The result is a system where deterministic math, rule-based compliance checks, and LLM-driven synthesis each do the part they're actually good at.

---

## Problem Statement

A real audit engagement demands expertise across several disconnected domains at once:

• Algorithmic fraud detection
• Statistical financial analysis
• Regulatory frameworks (SOX, GAAP, IFRS)
• Quantitative risk modeling
• Data security and privacy
• Executive-level communication

Reviewing 100% of an enterprise's transactions by hand is not feasible for any human team. LLMs promise to close that gap, but a single monolithic prompt asked to reason over an entire ledger introduces three problems we were not willing to accept:

• **No explainability** — There's no way to trace a finding back to the row that produced it.
• **Unreliable arithmetic** — Autoregressive models are not calculators, and financial audits cannot tolerate approximate math.
• **Fragile prompts** — A single giant instruction set degrades unpredictably every time you touch it.

---

## Why We Didn't Build "One Prompt to Rule Them All"

SentinelAI treats an audit as a structured, collaborative workflow, not a single generation call. Each agent owns one operational domain and produces a structured JSON payload, not conversational text. This buys us:

• **Independent iteration** — an agent's internals can change without touching the rest of the system.
• **True concurrency** — the specialized agents run in parallel, not one after another.
• **Deterministic guardrails** — every number in the final report is computed by ordinary Python (pandas, regex, statistics) before any LLM ever sees it.
• **Traceable lineage** — every insight maps back to the specific record that triggered it.

This mirrors how a real audit team works: domain specialists analyze their slice independently, then a principal auditor synthesizes the findings into one verdict.

---

## System Architecture

![](https://www.googleapis.com/download/storage/v1/b/kaggle-user-content/o/inbox%2F32127457%2F7da09289af8c58144545e1c8878461aa%2FArchitecture%20diagram.png?generation=1783205700414460&alt=media)

**Platform Architecture Overview**

• **Frontend** (React 19, CRA/CRACO, Tailwind CSS, shadcn/ui): Handles authentication, file upload, and live audit visualization through Recharts. A dedicated SSE connection streams agent progress to the dashboard in real time.
• **Backend API** (FastAPI, Python 3.11+): Async request handling, JWT access/refresh token auth, Role-Based Access Control, and Pydantic v2 validation on every payload.
• **Orchestration Engine**: A custom asyncio-based execution engine — not built on an external agent framework. It runs the specialized agents concurrently via `asyncio.gather`, wraps every call in retry-with-backoff and timeout logic, and streams progress events over SSE as agents complete.
• **Data Layer** (MongoDB): Persists users, audit records, datasets, and system logs.

We evaluated Google's Agent Development Kit for this orchestration layer. ADK's current release requires FastAPI ≥0.133, while our authentication and RBAC layer is built and tested against FastAPI 0.110.1. Upgrading FastAPI two days before a submission deadline, purely to gain a framework we could build ourselves in a few hundred lines, was a risk we chose not to take with a working, tested authentication system.

We're documenting that decision here deliberately: a custom orchestrator that we understand completely, and can debug at 2am, beat an unfamiliar framework wired in under time pressure.

---

## Integrated Agent Workflow

![](https://www.googleapis.com/download/storage/v1/b/kaggle-user-content/o/inbox%2F32127457%2F7e2b685504d5b5c579eccc8f9f945b69%2Fagent%20workflow.png?generation=1783205737711033&alt=media)

**Ingestion to Verdict Pipeline**

1. **Ingestion & Parsing.** A user uploads a raw CSV or PDF ledger. `file_processor.py` normalizes column names, maps them to canonical financial fields (amount, vendor, date, invoice ID, category) using a hint-based matcher, and coerces currency strings into numeric types.
2. **Orchestration.** The custom engine builds a run context (`ctx`) containing the parsed dataframe, dataset metadata, and audit ID, then dispatches it to the specialized agents concurrently.
3. **Parallel Agent Execution.**
   • **Fraud Detection Agent** — duplicate invoice detection, Benford's Law variance, vendor concentration, and threshold-splitting patterns designed to dodge approval limits.
   • **Compliance Agent** — SOX segregation-of-duties checks, GAAP/IFRS consistency rules.
   • **Financial Analysis Agent** — spending trend, budget variance, and category distribution analysis, all computed deterministically.
   • **Cybersecurity Agent** — scans the dataset for exposed PII (SSNs, credit cards, emails, phone numbers via regex) and prompt-injection / SQL-injection strings, running as one of the parallel agents rather than as a pre-filtering gate. In our own test dataset, this agent correctly flagged a planted SSN, an email address, and an injection attempt reading "ignore previous instructions," producing a risk score built directly from those findings.
   • **Risk Assessment Agent** — Monte Carlo VaR estimation, vendor diversity indexing, tail-risk scoring.
4. **Aggregation & Verdict.** All outputs are compiled into a single structured payload and handed to the **Decision Agent**, which is the only agent in the system that calls an LLM. It weighs the composite risk score, cross-references findings across agents, and produces a verdict (CLEAR → CRITICAL_ESCALATE), a confidence score, and specific recommendations — all returned as validated JSON. If the LLM call fails or times out, the Decision Agent falls back to a deterministic verdict computed from the raw risk scores, so a verdict is never blocked by an API outage.
5. **Reporting.** A Report Generation Agent turns the decision and underlying findings into a formatted executive HTML/PDF report.

---

## Google Gemini's Role — and Where We Draw the Line

Gemini never touches arithmetic in this system. Every score, percentage, and dollar figure is computed by ordinary Python before it ever reaches a prompt. Gemini's only job is semantic synthesis inside the Decision Agent: given multiple agents' worth of structured findings, decide what they mean together, and explain that to a human in plain language.

We originally built this on `google-generativeai`. Midway through development, Google formally deprecated that SDK in favor of `google-genai`, so we migrated the Decision Agent's LLM client over — same JSON-enforced response contract, same fallback behavior, just running on the SDK Google is actually still maintaining. Small change, but it's the kind of thing that matters six months after a hackathon ends.

---

## MCP: Making One Capability Independently Usable

Beyond the core application, we exposed the Cybersecurity Agent as a standalone MCP (Model Context Protocol) tool. `backend/mcp_server.py` runs as a fully separate process over stdio transport — it does not boot FastAPI, does not touch MongoDB, and imports the exact same cybersecurity_agent and CSV parser the main application uses, so there's no duplicated logic to drift out of sync.

The point isn't just to check a box — it's that PII/injection scanning is a capability worth having outside the context of a full audit run. Any MCP-compatible client (Claude, another agent framework, a CI pipeline) can hand this tool a CSV and get back structured findings, without ever standing up the rest of SentinelAI.

We tested it directly against the MCP Inspector with a planted SSN, email, and injection string, and it correctly returned all three findings with a computed risk score, confirming the tool is genuinely wired to live logic rather than a stub.

---

## Technical Stack

• **Frontend** — React 19, Tailwind CSS, shadcn/ui, Recharts → Dashboard, ingestion UI, live monitoring
• **Backend** — FastAPI, Python 3.11+, Pydantic v2 → REST APIs, auth, orchestration, reporting
• **Data** — MongoDB, Motor (async driver) → Users, audits, datasets, logs
• **AI** — Google Gemini (`gemini-2.5-flash`) via `google-genai` → Decision synthesis, confidence scoring
• **Orchestration** — Custom asyncio engine, Server-Sent Events → Parallel execution, retries, live streaming
• **External Interop** — MCP server (stdio) → Standalone cybersecurity scanning tool
• **Security** — JWT, refresh tokens, RBAC → Authentication and authorization

---

## Responsible AI & Enterprise Guardrails

• **Human-in-the-loop.** SentinelAI never auto-executes a financial decision. Every finding carries its source agent, severity, and description, so a human auditor retains final sign-off.
• **Data ephemerality.** Uploaded financial data lives only in transient application memory during processing; once a report is generated and persisted, the underlying dataframe is released.
• **Injection defense.** The Cybersecurity Agent's pattern matching runs against every dataset before its findings reach the Decision Agent's prompt, reducing the chance that adversarial content in an uploaded ledger reaches the LLM unfiltered.

---

## Empirical Performance Results — Verified on Current Code

Rather than carry forward estimated or historical figures, we benchmarked the current codebase directly against a synthetic 563-row ledger: 500 baseline transactions plus 63 deliberately planted anomalies — 10 duplicate invoices, 5 threshold-split transactions, 3 SSNs, 3 emails, 2 injection strings, and a 40-row Benford's Law cluster.

**End-to-end pipeline timing** (ingestion → parallel agents → Decision Agent → report generation), averaged over 3 runs:
• Min: 8.30s / Max: 9.59s / Average: 8.93s

**Detection accuracy:**
• Threshold-split transactions: 5/5 (100%)
• Planted SSNs: 3/3 (100%)
• Planted emails: 3/3 (100%)
• Prompt-injection strings: 1/2 (One planted string didn't match either of our two registered injection patterns. We're treating this as a known limitation to grow our pattern library, not a hidden one.)
• Duplicate invoices: The agent reports up to 10 groups by design, a deliberate cap to keep executive report output readable rather than a detection ceiling.

**Numerical consistency:** Confirmed directly. In this run, the Decision Agent's `overall_risk_score` matched the arithmetic average of the specialized agents' individual risk scores exactly — Gemini never touched the math, it only interpreted numbers Python had already computed.

**LLM synthesis, verified live:** With a real Gemini API key configured, the Decision Agent returned a verdict of `CRITICAL_ESCALATE` with `0.95` confidence, sourced from the LLM's own JSON response rather than the deterministic fallback. Its executive summary and rationale were generated fresh from the aggregated findings, correctly prioritizing the duplicate-invoice fraud signal and a PII exposure finding as the drivers of the escalation.

**A bug we found and fixed along the way:** Benchmarking surfaced a real issue in the Cybersecurity Agent: its credit-card regex was matching digit sequences inside floating-point decimals (e.g., pulling a false "card number" out of 1035.2421262733214), and a row-count cap meant to keep the agent fast was silently excluding every planted anomaly past row 500. Both are fixed in the current code, verified by this benchmark, and covered by our existing test suite (4/4 passing). We're including this here on purpose — catching and fixing a real detection bug through our own benchmarking is a more convincing demonstration of a working system than a report that never got tested hard enough to find one.

---

## What We Actually Verified — Not Just Claimed

Before finalizing this writeup, we ran our own internal audit of it: every architectural claim here was checked directly against the codebase and the test suite, not written from memory of the original design. Concretely:

• All backend tests pass (`pytest tests/ -v`)
• The MCP server was verified against the MCP Inspector with a real, planted-data test case
• The `google-genai` migration was confirmed to remove the prior SDK's deprecation warning without changing any downstream contract
• The decision to defer ADK was made only after confirming the exact dependency conflict, not assumed
• Every empirical figure above came from an actual run of the current code, not an earlier build

We'd rather submit a writeup that matches our code exactly than one that reads better and doesn't.

---

## Future Roadmap

• **Policy RAG** — connect internal compliance documentation to the Compliance Agent via vector search for company-specific rule checking.
• **ADK migration** — revisit once our FastAPI stack is upgraded past 0.133, so the Decision Agent can run on ADK's LlmAgent without destabilizing authentication.
• **Distributed workers** — move orchestration from in-process asyncio to Redis/Celery for horizontal scaling.
• **Tracing** — add OpenTelemetry instrumentation across every agent for latency visibility.

---

## Repository Setup and Usage

### Folder Structure

```
├── backend/               # FastAPI backend
│   ├── agents.py          # AI agent definitions
│   ├── server.py          # Core REST/SSE endpoints
│   ├── models.py          # Pydantic data schemas
│   ├── file_processor.py  # Pandas CSV/PDF ingestion
│   ├── workflow.py        # Agent orchestration
│   ├── auth.py            # JWT and RBAC logic
│   ├── mcp_server.py      # Standalone MCP implementation
│   └── tests/             # Pytest suite
├── frontend/              # React frontend
│   ├── src/pages/         # React Views (Admin, AuditDetail)
│   ├── src/components/    # shadcn/ui shared components
│   └── src/lib/           # Axios interceptors & Utils
├── docker-compose.yml     # Local orchestration
└── README.md              # Project documentation
```

### Environment Variables

**Backend** (`backend/.env`)
```ini
MONGO_URL=mongodb://localhost:27017
DB_NAME=sentinelai
JWT_SECRET=your_super_secret_key_change_in_production
GOOGLE_API_KEY=your_gemini_api_key
CORS_ORIGINS=http://localhost:5173,http://localhost
```

**Frontend** (`frontend/.env`)
```ini
VITE_API_URL=http://localhost:8000/api
```

### Local Development Startup

**1. Database**
Ensure MongoDB is running locally on port 27017.

**2. Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

**3. Frontend**
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

The app will be available at `http://localhost:5173`.

### Docker Usage (Production Ready)

To start the entire stack (MongoDB, Backend, Frontend) with a single command:

```bash
docker-compose up --build -d
```

- **Frontend UI**: `http://localhost:80`
- **Backend API**: `http://localhost:8000`
- **MongoDB**: `localhost:27017`

### API Overview

- `POST /api/auth/register` - Create an account.
- `POST /api/auth/token` - OAuth2 login.
- `POST /api/datasets` - Upload financial data.
- `POST /api/audits` - Dispatch multi-agent audit.
- `GET /api/audits/{id}/stream` - SSE endpoint for live agent logs.
- `GET /api/audits/{id}/report.pdf` - Download Executive PDF.
- `PATCH /api/admin/users/{id}` - Admin RBAC controls.

### Authentication

SentinelAI uses **JWT Bearer tokens** with an active `refresh` flow mechanism. 
Tokens expire after 1 hour, and the frontend automatically intercepts `401 Unauthorized` requests to transparently refresh access via `/api/auth/refresh`.

Role-Based Access Control (RBAC) supports:
- `admin`: Full system access, audit logs, and user management.
- `auditor`: Can upload datasets, start audits, and view reports.
- `viewer`: Read-only access to completed reports.

### Running Tests

To run the Pytest suite for the backend (with mocked AI and database connections):

```bash
cd backend
pip install pytest pytest-asyncio httpx
python -m pytest tests/test_api.py -v
```

### Deployment & Troubleshooting

- **MongoDB Indexes**: Handled idempotently at backend startup. If startup fails, verify DB connectivity.
- **Memory Leaks**: Handled automatically. The server uses reference-counted caching to flush heavy DataFrames (`_dataframe_cache_refs`) once SSE queues shut down.
- **Empty Reports**: Check the `GOOGLE_API_KEY` quota if agents fail silently.

---

## Conclusion

SentinelAI's core bet is that reliable financial AI comes from discipline, not cleverness: deterministic math stays deterministic, an LLM only ever synthesizes what humans still have to sign off on, and every claim in this writeup is one we actually went back and checked against the running code. We think that's a more honest demonstration of "agents for business" than a system that looks impressive in a demo and falls apart under a second look — and we built it that way on purpose.
