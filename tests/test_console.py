from fastapi.testclient import TestClient

from devops_assistant.api import create_app


def test_console_opens_one_diagnosis_without_running_commands():
    client = TestClient(create_app(":memory:"))
    page = client.get("/")
    assert page.status_code == 200
    assert 'data-shell="studio"' in page.text
    created = client.post("/api/diagnoses", json={"log": "FAILED tests/test_api.py::test_health\nAssertionError: expected 200", "repository": "demo/app"})
    assert created.status_code == 200
    detail = client.get("/api/diagnoses/" + created.json()["id"])
    assert detail.status_code == 200
    assert detail.json()["report"]["commands_executed"] is False
    missing = client.get("/api/diagnoses/missing", headers={"Accept-Language": "en"})
    assert missing.json()["detail"] == "Diagnosis record does not exist"
