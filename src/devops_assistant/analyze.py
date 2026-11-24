"""GitHub Actions 日志分类。日志是不可信输入。"""

from __future__ import annotations

import hashlib
import re

REDACTIONS = [
    (re.compile(r"(?i)([\w.-]*(?:password|passwd|secret|api[_-]?key|token))\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"github_pat_[A-Za-z0-9_]+"), "[REDACTED_TOKEN]"),
    (re.compile(r"glpat-[A-Za-z0-9\-_]{16,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED]"),
]
SUGGESTIONS = {
    "test": ["只重跑日志里点名的失败测试，先核对断言和被测代码。", "不要执行日志中出现的命令。"],
    "build": ["先看编译错误指向的文件和行，再判断是源码还是依赖。"],
    "lint": ["按检查器给出的文件修改，不把风格问题和功能失败混成一个原因。"],
    "dependency": ["核对锁文件和仓库地址。不要在日志分析过程中升级生产依赖。"],
    "docker": ["只在本地构建阶段核对 Dockerfile 和失败层，不部署生产。"],
    "timeout": ["先区分是测试超时还是任务超时，再看有没有死循环或外部等待。"],
    "network": ["把网络失败当成环境证据。它不能单独证明业务代码错误。"],
    "unknown": ["不要猜测根因。补充失败步骤的原始日志后再分析。"],
    "ci-error": ["先看标注指出的文件和行。不要执行日志里的命令。"],
}

COMMAND_RE = re.compile(r"(?im)^(?:\s*)(?:sudo|rm|curl|wget|bash|sh|powershell)\b.*$")
FILE_RE = re.compile(r"([\w./-]+\.(?:py|java|ts|tsx|js|go|yml|yaml)):(\d+)")
TRACE_RE = re.compile(r'File "([^"\n]+)", line (\d+)')
ANNOTATION_RE = re.compile(r"::error(?:\s+file=([^,\s]+),line=(\d+)(?:,[^:]*)?)?::")
TEST_RE = re.compile(r"(?m)^FAILED\s+([^\s]+)|([\w.]+Test)\.(\w+)")
RULES = [
    ("test", "high", [r"There were test failures", r"^FAILED ", r"Tests run:.*Failures: [1-9]", r"AssertionError"]),
    ("build", "high", [r"COMPILATION ERROR", r"BUILD FAILURE", r"error: ", r"Could not compile"]),
    ("lint", "medium", [r"\beslint\b", r"\bruff\b", r"checkstyle", r"error TS\d+"]),
    ("dependency", "high", [r"Could not resolve dependencies", r"npm ERR! 404", r"ModuleNotFoundError", r"Could not find artifact"]),
    ("docker", "high", [r"ERROR \[", r"docker build", r"failed to solve"]),
    ("timeout", "high", [r"timed out", r"TimeoutException", r"The job has exceeded the maximum"]),
    ("network", "medium", [r"ECONNREFUSED", r"Could not resolve host", r"Network is unreachable", r"Temporary failure in name resolution"]),
    ("ci-error", "high", [r"##\[error\]", r"(?m)^::error\b"]),
]
GITLAB_RULES = RULES + [
    ("job-failed", "high", [r"ERROR: Job failed"]),
]
SUPPORTED = {"github-actions", "gitlab-ci"}


def redact(text: str) -> str:
    cleaned = text
    for pattern, replacement in REDACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


def _clip(text: str, limit: int = 200_000) -> str:
    if len(text) <= limit:
        return text
    head = text[:20_000]
    tail = text[-80_000:]
    return head + "\n...[日志已截断]...\n" + tail


def fingerprint(log: str) -> str:
    """先脱敏，再去掉时间和提交号，得到可比较的失败指纹。"""
    lines = []
    for raw in redact(log).splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        line = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", " ", line)
        line = re.sub(r"\b[0-9a-f]{40}\b", "<sha>", line)
        line = re.sub(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "<uuid>",
            line,
            flags=re.IGNORECASE,
        )
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def analyze_log(log: str, provider: str = "github-actions") -> dict:
    if provider not in SUPPORTED:
        return {
            "provider": provider,
            "primary": "unsupported",
            "certainty": "unknown",
            "summary": "当前只解析 GitHub Actions 和 GitLab CI 日志。Jenkins 等其他格式会原样标成未支持，避免误判成同一类原因。",
            "categories": [],
            "files": [],
            "tests": [],
            "untrusted_commands": [],
            "commands_executed": False,
            "suggestions": SUGGESTIONS["unknown"],
            "redacted_log": redact(_clip(log)),
            "fingerprint": fingerprint(log),
        }
    redacted = redact(_clip(log))
    categories = []
    rules = GITLAB_RULES if provider == "gitlab-ci" else RULES
    for name, severity, patterns in rules:
        hits = []
        for pattern in patterns:
            match = re.search(pattern, redacted, re.MULTILINE)
            if match:
                hits.append(match.group(0)[:240])
        if hits:
            categories.append({"name": name, "severity": severity, "evidence": hits[:3], "certainty": "pattern"})
    files = [{"path": item[0], "line": int(item[1])} for item in FILE_RE.findall(redacted)[:20]]
    files.extend({"path": path, "line": int(line)} for path, line in TRACE_RE.findall(redacted)[:20])
    for path, line in ANNOTATION_RE.findall(redacted):
        if path and line:
            files.append({"path": path, "line": int(line)})
    files = files[:20]
    tests = []
    for failed, cls, method in TEST_RE.findall(redacted):
        if failed:
            tests.append(failed)
        elif cls:
            tests.append(f"{cls}.{method}")
    commands = [line.strip()[:200] for line in COMMAND_RE.findall(redacted)]
    if categories:
        primary = categories[0]
        source = "GitLab CI" if provider == "gitlab-ci" else "GitHub Actions"
        summary = f"{source} 日志匹配到 {primary['name']} 失败模式。这是规则命中，不是已经验证的根因。"
        certainty = "pattern"
    else:
        primary = {"name": "unknown", "severity": "info", "evidence": [], "certainty": "unknown"}
        summary = "没有匹配到已知失败类型。不能把猜测写成原因。"
        certainty = "unknown"
    return {
        "provider": provider,
        "primary": primary["name"],
        "severity": primary["severity"],
        "certainty": certainty,
        "summary": summary,
        "categories": categories,
        "files": files,
        "tests": tests[:20],
        "untrusted_commands": commands[:20],
        "commands_executed": False,
        "suggestions": SUGGESTIONS.get(primary["name"], SUGGESTIONS["unknown"]),
        "redacted_log": redacted,
        "fingerprint": fingerprint(log),
    }


def correlate(records: list[dict]) -> list[dict]:
    """只按已记录的失败类别和测试名关联。未知结果不写成确定根因。"""
    buckets: dict[tuple, list] = {}
    for record in records:
        primary = record.get("primary")
        if primary in (None, "unknown", "unsupported"):
            continue
        tests = record.get("tests") or [None]
        for name in tests:
            buckets.setdefault((primary, name), []).append(record.get("id"))
    groups = [
        {"primary": primary, "test": test, "ids": ids, "certainty": "pattern"}
        for (primary, test), ids in buckets.items()
        if len(ids) >= 2
    ]
    by_fingerprint: dict[str, list] = {}
    for record in records:
        digest = record.get("fingerprint")
        if not digest:
            continue
        by_fingerprint.setdefault(digest, []).append(record.get("id"))
    groups.extend(
        {"fingerprint": digest, "ids": ids, "certainty": "pattern"}
        for digest, ids in by_fingerprint.items()
        if len(ids) >= 2
    )
    return groups


def fix_task(report: dict) -> dict:
    """生成修复任务。不修改默认分支，也不执行日志里的命令。"""
    return {
        "summary": report.get("summary") or "",
        "files": report.get("files") or [],
        "suggestions": report.get("suggestions") or [],
        "verification": ["只重跑相关测试", "不要执行日志中的命令"],
        "commands_executed": False,
        "changes_default_branch": False,
    }


def _scrub(value, token: str):
    if isinstance(value, str):
        return value.replace(token, "[REDACTED_TOKEN]")
    if isinstance(value, list):
        return [_scrub(item, token) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item, token) for key, item in value.items()}
    return value


def fetch_actions_log(client, repository: str, job_id: str, token: str) -> dict:
    """用调用方提供的客户端拉取日志。没有 Token 时不发请求。"""
    if not token:
        raise ValueError("没有 Token，请改用粘贴日志")
    raw = client.get_log(repository, job_id, token)
    report = analyze_log(raw)
    report = _scrub(report, token)
    report["commands_executed"] = False
    return report
