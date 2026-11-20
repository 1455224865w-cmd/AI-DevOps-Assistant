import subprocess

from devops_assistant.analyze import analyze_log, correlate, fetch_actions_log, fix_task

LOG = """
FAILED tests/test_order.py::test_total - AssertionError
rm -rf /
password=secret
"""


class Client:
    def __init__(self):
        self.called = False

    def get_log(self, repository, job_id, token):
        self.called = True
        return LOG + "\n" + token


def test_correlate_unknown_is_not_a_confirmed_cause():
    groups = correlate([
        {"id": "a", "primary": "test", "tests": ["tests/test_order.py::test_total"]},
        {"id": "b", "primary": "test", "tests": ["tests/test_order.py::test_total"]},
        {"id": "c", "primary": "unknown", "tests": ["tests/test_order.py::test_total"]},
    ])
    assert groups == [{
        "primary": "test",
        "test": "tests/test_order.py::test_total",
        "ids": ["a", "b"],
        "certainty": "pattern",
    }]


def test_fix_task_and_fetch_do_not_run_commands(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不应执行命令")))
    report = analyze_log(LOG)
    task = fix_task(report)
    assert task["commands_executed"] is False
    assert task["changes_default_branch"] is False
    client = Client()
    with_token = fetch_actions_log(client, "demo/app", "1", "ghp_abcdefghijklmnopqrstuvwxyz123456")
    assert client.called is True
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in str(with_token)
    assert with_token["commands_executed"] is False
    client.called = False
    try:
        fetch_actions_log(client, "demo/app", "1", "")
    except ValueError:
        assert client.called is False
    else:
        raise AssertionError("没有 Token 时不应请求日志")
