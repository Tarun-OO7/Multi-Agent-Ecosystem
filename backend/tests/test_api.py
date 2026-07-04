import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import app
from auth import create_access_token

client = TestClient(app)

def get_admin_token():
    return create_access_token("admin123", "admin@test.com", "admin")

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()

@patch("server.users_col.find_one", new_callable=AsyncMock)
def test_authentication(mock_find_one):
    mock_find_one.return_value = {
        "id": "admin123",
        "email": "admin@test.com",
        "full_name": "Admin",
        "role": "admin",
        "active": True
    }
    
    # Missing token
    res = client.get("/api/auth/me")
    assert res.status_code == 401

    # Valid token
    token = get_admin_token()
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "admin@test.com"

@patch("agents.call_llm_json", new_callable=AsyncMock)
def test_report_generation(mock_call_llm_json):
    from agents import decision_agent, report_generation_agent
    
    mock_call_llm_json.return_value = {
        "verdict": "MINOR_FOLLOWUP",
        "overall_risk_score": 45,
        "executive_summary": "Test Summary",
        "key_findings": ["Test Finding"],
        "recommendations": ["Test Rec"],
        "rationale": "Test Rationale"
    }
    
    outputs = {
        "Duplicate Invoice Agent": {"risk_score": 50, "findings": [{"severity": "medium", "description": "dup"}]}
    }
    
    async def run():
        decision = await decision_agent({"audit_title": "Test"}, outputs, "audit_id")
        report = await report_generation_agent({"audit_title": "Test"}, outputs, decision)
        return decision, report
        
    decision, report = asyncio.run(run())
    assert decision["verdict"] == "MINOR_FOLLOWUP"
    assert "html" in report
    assert "Test Summary" in report["html"]
    assert "MINOR_FOLLOWUP" in report["html"]

@patch("server.datasets_col.find_one", new_callable=AsyncMock)
@patch("server.audits_col.find")
def test_api_endpoints(mock_find, mock_find_one):
    mock_find_one.return_value = {"id": "ds1", "user_id": "admin123"}
    
    class MockCursor:
        def sort(self, *args, **kwargs): return self
        def limit(self, *args, **kwargs): return self
        async def to_list(self, length): return [{"id": "audit1", "status": "completed"}]
        
    mock_find.return_value = MockCursor()
    
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/audits", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["audits"]) == 1
