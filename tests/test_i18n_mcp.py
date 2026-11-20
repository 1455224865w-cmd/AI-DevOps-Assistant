import json
from pathlib import Path

from fastapi.testclient import TestClient

from devops_assistant.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_mcp_redacts_token_and_does_not_run_commands():
    client = TestClient(create_app(":memory:"))
    token = "ghp_" + "d" * 36
    log = "FAILED tests/test_order.py::test_total - AssertionError\n" + token + "\nrm -rf /"
    called = client.post("/mcp", json={
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "devops_analyze_log", "arguments": {"log": log, "locale": "en"}},
    })
    raw = called.json()["result"]["content"][0]["text"]
    assert token not in raw
    payload = json.loads(raw)
    assert payload["commands_executed"] is False
    assert payload["primary"] == "test"
    assert "pattern match" in payload["summary"]
    assert payload["untrusted_commands"]
    spring = (ROOT / "spring-ai" / "pom-snippet.xml").read_text(encoding="utf-8")
    assert "spring-ai-starter-mcp-client" in spring
    bootstrap = (ROOT / "spring-ai" / "application-mcp.yml").read_text(encoding="utf-8")
    sample = (ROOT / "nacos" / "spring-mcp.yaml").read_text(encoding="utf-8")
    assert "nacos:" in bootstrap
    assert "127.0.0.1" not in bootstrap
    assert "${MCP_SERVICE_URL}" in sample
