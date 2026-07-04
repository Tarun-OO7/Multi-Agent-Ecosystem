# SentinelAI — Multi-Agent Financial Intelligence Audit Framework

SentinelAI is an advanced multi-agent system designed for automated financial auditing. Powered by Google Gemini and a suite of 8 specialized AI agents, it intelligently scans raw datasets (CSV/PDF) to identify financial anomalies, segregation of duties (SoD) violations, duplicate invoices, and suspicious vendor activity.

## Architecture

SentinelAI follows a modern full-stack decoupled architecture:

- **Frontend**: React 18, Vite, Tailwind CSS, shadcn/ui.
- **Backend**: FastAPI, Async Python 3.11.
- **Database**: MongoDB (persistence for users, audits, logs).
- **AI Engine**: Google GenAI SDK (Gemini) orchestrated through custom prompt chains and deterministic workflows.

### Agent Workflow
1. **Data Parsing**: Extracts and normalizes data into an in-memory Pandas DataFrame.
2. **Specialized Agents**: 8 parallel agents assess different risk vectors (Duplicates, Benford's Law, Sanctions, SoD, Policy, Missing Docs, Odd Hours).
3. **Decision Agent**: Aggregates findings and issues a final risk verdict.
4. **Report Agent**: Generates a finalized HTML/PDF executive summary.

---

## Folder Structure

```
├── backend/               # FastAPI backend
│   ├── agents.py          # AI agent definitions
│   ├── server.py          # Core REST/SSE endpoints
│   ├── models.py          # Pydantic data schemas
│   ├── file_processor.py  # Pandas CSV/PDF ingestion
│   ├── workflow.py        # Agent orchestration
│   ├── auth.py            # JWT and RBAC logic
│   └── tests/             # Pytest suite
├── frontend/              # React frontend
│   ├── src/pages/         # React Views (Admin, AuditDetail)
│   ├── src/components/    # shadcn/ui shared components
│   └── src/lib/           # Axios interceptors & Utils
├── docker-compose.yml     # Local orchestration
└── README.md              # Project documentation
```

---

## Technology Stack

- **Frontend**: React, Vite, Axios, Tailwind, Lucide Icons, Sonner.
- **Backend**: Python 3.11, FastAPI, Uvicorn, Pandas, PyMongo/Motor, ReportLab.
- **Data**: MongoDB.
- **AI Model**: Google Gemini (`gemini-2.5-flash`).

---

## Environment Variables

### Backend (`backend/.env`)
```ini
MONGO_URL=mongodb://localhost:27017
DB_NAME=sentinelai
JWT_SECRET=your_super_secret_key_change_in_production
GEMINI_API_KEY=your_gemini_api_key
CORS_ORIGINS=http://localhost:5173,http://localhost
```

### Frontend (`frontend/.env`)
```ini
VITE_API_URL=http://localhost:8000/api
```

---

## Local Development Startup

### 1. Database
Ensure MongoDB is running locally on port 27017.

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## Docker Usage (Production Ready)

To start the entire stack (MongoDB, Backend, Frontend) with a single command:

```bash
docker-compose up --build -d
```

- **Frontend UI**: `http://localhost:80`
- **Backend API**: `http://localhost:8000`
- **MongoDB**: `localhost:27017`

---

## API Overview

- `POST /api/auth/register` - Create an account.
- `POST /api/auth/token` - OAuth2 login.
- `POST /api/datasets` - Upload financial data.
- `POST /api/audits` - Dispatch multi-agent audit.
- `GET /api/audits/{id}/stream` - SSE endpoint for live agent logs.
- `GET /api/audits/{id}/report.pdf` - Download Executive PDF.
- `PATCH /api/admin/users/{id}` - Admin RBAC controls.

## Authentication

SentinelAI uses **JWT Bearer tokens** with an active `refresh` flow mechanism. 
Tokens expire after 1 hour, and the frontend automatically intercepts `401 Unauthorized` requests to transparently refresh access via `/api/auth/refresh`.

Role-Based Access Control (RBAC) supports:
- `admin`: Full system access, audit logs, and user management.
- `auditor`: Can upload datasets, start audits, and view reports.
- `viewer`: Read-only access to completed reports.

---

## Running Tests

To run the Pytest suite for the backend (with mocked AI and database connections):

```bash
cd backend
pip install pytest pytest-asyncio httpx
python -m pytest tests/test_api.py -v
```

---

## Deployment & Troubleshooting

- **MongoDB Indexes**: Handled idempotently at backend startup. If startup fails, verify DB connectivity.
- **Memory Leaks**: Handled automatically. The server uses reference-counted caching to flush heavy DataFrames (`_dataframe_cache_refs`) once SSE queues shut down.
- **Empty Reports**: Check the `GEMINI_API_KEY` quota if agents fail silently.
