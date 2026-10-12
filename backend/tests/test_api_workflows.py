"""Integration tests crossing the HTTP boundary for core API workflows."""

import pytest


def test_health_and_info_endpoints(client):
    """Verify health and metadata info endpoints."""
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    info_resp = client.get("/api/info")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["name"] == "lumen-station-alan-vo"
    assert info_data["auth"] == "oidc-keycloak-saml-broker"


def test_full_sandbox_execution_and_search_workflow(client):
    """Verify session creation, sandboxed execution, search, and detail retrieval."""
    # 1. Create Session
    sess_resp = client.post("/api/sessions", json={
        "platform": "antigravity",
        "working_dir": ".",
        "os_name": "linux",
        "quiet_mode": False,
    })
    assert sess_resp.status_code == 200
    session_id = sess_resp.json()["id"]

    # 2. Run Tool Execution
    exec_resp = client.post("/api/sandbox/execute", json={
        "session_id": session_id,
        "command": "python3 -c \"print('Workflow execution line 1'); print('SEARCHABLE_TOKEN_ABC'); print('Workflow execution line 3')\"",
        "timeout_seconds": 15,
        "head_lines": 5,
        "tail_lines": 5,
    })
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    execution_id = exec_data["id"]
    assert exec_data["status"] == "completed"
    assert exec_data["exit_code"] == 0

    # 3. Retrieve Execution Detail
    detail_resp = client.get(f"/api/sandbox/executions/{execution_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == execution_id
    assert "SEARCHABLE_TOKEN_ABC" in detail_data["raw_output"]
    assert detail_data["chunk_count"] >= 1

    # 4. Search via FTS5
    search_resp = client.post("/api/search", json={
        "query": "SEARCHABLE_TOKEN_ABC",
        "session_id": session_id,
    })
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_matches"] >= 1
    assert any(m["execution_id"] == execution_id for m in search_data["results"])

    # 5. Get Session Guidance
    guidance_resp = client.post("/api/sessions/guidance", json={
        "session_id": session_id,
        "session_mode": "investigate",
    })
    assert guidance_resp.status_code == 200
    assert "<tool_guidance>" in guidance_resp.json()["injected_block"]

    # 6. Global Analytics and Export
    export_resp = client.get("/api/analytics/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert export_data["policy_verification"]["part_whole_invariant"] is True
