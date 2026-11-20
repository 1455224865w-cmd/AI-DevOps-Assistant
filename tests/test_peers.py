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


def test_annotations_and_fingerprint_groups():
    from devops_assistant.analyze import correlate

    log = "::error file=src/order/Order.java,line=12::AssertionError\nFAILED tests/OrderTest.testTotal\n"
    report = analyze_log(log)
    assert {"path": "src/order/Order.java", "line": 12} in report["files"]
    assert report["commands_executed"] is False
    groups = correlate([
        {"id": "a", "primary": "test", "tests": ["one"], "fingerprint": "same"},
        {"id": "b", "primary": "build", "tests": ["two"], "fingerprint": "same"},
        {"id": "c", "primary": "test", "tests": ["three"], "fingerprint": "other"},
    ])
    assert {"fingerprint": "same", "ids": ["a", "b"], "certainty": "pattern"} in groups
    assert all(item.get("fingerprint") != "other" for item in groups)


def test_ci_error_marker_does_not_run_commands():
    report = analyze_log("##[error]Process completed with exit code 1.\nrm -rf /")
    assert report["primary"] == "ci-error"
    assert report["commands_executed"] is False
    assert report["untrusted_commands"]
