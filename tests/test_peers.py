from devops_assistant.analyze import analyze_log, fingerprint

TOKEN = "ghp_" + "a" * 36


def test_fingerprint_ignores_time_and_secrets():
    first = "2020-01-01T00:00:00Z FAILED tests/test_order.py::test_total\n" + TOKEN
    second = "2024-05-01T01:02:03Z FAILED tests/test_order.py::test_total\ngithub_pat_" + "b" * 22
    other = "2024-05-01T01:02:03Z FAILED tests/test_order.py::test_other"
    assert fingerprint(first) == fingerprint(second)
    assert fingerprint(first) != fingerprint(other)
    report = analyze_log(first)
    assert report["fingerprint"] == fingerprint(first)
    assert TOKEN not in report["redacted_log"]
    assert report["commands_executed"] is False
