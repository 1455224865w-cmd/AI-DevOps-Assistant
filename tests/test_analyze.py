import subprocess

from fastapi.testclient import TestClient

from devops_assistant.analyze import analyze_log
from devops_assistant.api import create_app

LOG = """
##[group]Run pytest
FAILED tests/test_order.py::test_total - AssertionError: expected 3
src/order/service.py:42: in total
E   AssertionError
password=super-secret token: ghp_abcdefghijklmnopqrstuvwxyz123456
rm -rf /
There were test failures
"""


def test_log_is_redacted_and_commands_are_not_run(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("日志里的命令不应该被执行")

    monkeypatch.setattr(subprocess, "run", fail_if_called)
    report = analyze_log(LOG)
    assert report["primary"] == "test"
    assert report["certainty"] == "pattern"
    assert report["commands_executed"] is False
    assert "super-secret" not in report["redacted_log"]
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in report["redacted_log"]
    assert report["files"][0] == {"path": "src/order/service.py", "line": 42}
    assert "tests/test_order.py::test_total" in report["tests"]
    assert any(item.startswith("rm -rf") for item in report["untrusted_commands"])


def test_gitlab_job_log_is_classified_without_running_commands():
    report = analyze_log(
        "Running with gitlab-runner 16.0\nERROR: Job failed: exit status 1\nglpat-abcdefghijklmnopqrst\n",
        "gitlab-ci",
    )
    assert report["provider"] == "gitlab-ci"
    assert report["primary"] == "job-failed"
    assert report["commands_executed"] is False
    assert "glpat-abcdefghijklmnopqrst" not in report["redacted_log"]


def test_python_traceback_file_is_recorded():
    report = analyze_log('Traceback (most recent call last):\n  File "src/order/service.py", line 42, in total\nAssertionError\n')
    assert {"path": "src/order/service.py", "line": 42} in report["files"]


def test_jenkins_stays_unsupported():
    report = analyze_log("Build step 'Execute shell' marked build as failure", "jenkins")
    assert report["primary"] == "unsupported"


def test_unknown_log_is_not_guessed():
    report = analyze_log("all checks completed\nno error marker")
    assert report["primary"] == "unknown"
    assert report["certainty"] == "unknown"


def test_history_api(tmp_path):
    client = TestClient(create_app(str(tmp_path / "history.sqlite3")))
    created = client.post("/api/diagnoses", json={"log": LOG, "repository": "demo/app"})
    assert created.status_code == 200
    assert created.json()["report"]["commands_executed"] is False
    rows = client.get("/api/diagnoses").json()
    assert rows[0]["primary_cause"] == "test"
