"""中英文切换。默认中文，已有调用不传语言时行为不变。"""

from __future__ import annotations

import os

import re
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

current_locale: ContextVar[str] = ContextVar("locale", default="zh")
LOCALES = ("zh", "en")
TEXT_FIELDS = {
    "name", "summary", "message", "detail", "reason", "impact", "direction",
    "risk", "verification", "answer", "error", "prompt",
}

def negotiate(header: str | None, query: str | None = None) -> str:
    if query in LOCALES:
        return query
    if header:
        for part in header.split(","):
            token = part.split(";", 1)[0].strip().lower().replace("_", "-")
            if token.startswith("en"):
                return "en"
            if token.startswith("zh"):
                return "zh"
    fallback = os.environ.get("APP_LOCALE", "zh").strip().lower()
    return fallback if fallback in LOCALES else "zh"


def localize_error(message: str, locale: str) -> str:
    if locale != "en":
        return message
    if message in EN:
        return EN[message]
    for pattern, template in PATTERNS:
        matched = pattern.fullmatch(message)
        if matched:
            return template.format(*matched.groups())
    return message


def text(key: str, locale: str) -> str:
    table = TEXT.get(locale) or TEXT["zh"]
    return table.get(key) or TEXT["zh"][key]


def translate_payload(value, locale: str):
    if locale != "en":
        return value
    if isinstance(value, dict):
        translated = {}
        for key, item in value.items():
            if key == "suggestions" and isinstance(item, list):
                translated[key] = [
                    localize_error(piece, "en") if isinstance(piece, str) else translate_payload(piece, "en")
                    for piece in item
                ]
            elif key in TEXT_FIELDS and isinstance(item, str):
                translated[key] = localize_error(item, "en")
            else:
                translated[key] = translate_payload(item, "en")
        return translated
    if isinstance(value, list):
        return [translate_payload(item, "en") for item in value]
    return value


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def bind_locale(request: Request, call_next):
        token = current_locale.set(negotiate(request.headers.get("accept-language"), request.query_params.get("lang")))
        try:
            return await call_next(request)
        finally:
            current_locale.reset(token)

    @app.exception_handler(HTTPException)
    async def translate_http(request: Request, exc: HTTPException):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        detail = exc.detail
        if isinstance(detail, str):
            detail = localize_error(detail, locale)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.get("/api/meta")
    def meta(request: Request):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        return {
            "locale": locale,
            "locales": list(LOCALES),
            "mcp": "/mcp",
            "springAi": "streamable-http",
            "message": text("meta.ready", locale),
        }


EN = {
    "未知工具": "Unknown tool",
    "日志不能为空": "A log is required",
    "日志超过长度限制": "The log exceeds the length limit",
    "没有 Token，请改用粘贴日志": "No token is available; paste the log instead",
    "没有匹配到已知失败类型。不能把猜测写成原因。": "No known failure type matched. A guess cannot be written down as the cause.",
    "MVP 只解析 GitHub Actions 日志，避免把其他 CI 的格式误判成同一类原因。": "Only GitHub Actions logs are parsed, so another CI format is not given the same conclusion.",
    "只重跑日志里点名的失败测试，先核对断言和被测代码。": "Rerun only the named failing test and check the assertion and the code under test.",
    "不要执行日志中出现的命令。": "Do not execute commands that appear in the log.",
    "先看编译错误指向的文件和行，再判断是源码还是依赖。": "Read the file and line in the compile error before deciding whether the cause is source or a dependency.",
    "按检查器给出的文件修改，不把风格问题和功能失败混成一个原因。": "Change the file named by the linter. Do not merge style issues and functional failures into one cause.",
    "核对锁文件和仓库地址。不要在日志分析过程中升级生产依赖。": "Check the lockfile and repository address. Do not upgrade production dependencies while reading the log.",
    "只在本地构建阶段核对 Dockerfile 和失败层，不部署生产。": "Check the Dockerfile and the failed layer locally. Do not deploy to production.",
    "先区分是测试超时还是任务超时，再看有没有死循环或外部等待。": "Separate a test timeout from a job timeout, then look for a loop or an external wait.",
    "把网络失败当成环境证据。它不能单独证明业务代码错误。": "Treat a network failure as environment evidence. It does not by itself prove a product defect.",
    "不要猜测根因。补充失败步骤的原始日志后再分析。": "Do not guess the root cause. Add the raw log of the failed step before analyzing it.",
    "先看标注指出的文件和行。不要执行日志里的命令。": "Read the file and line in the annotation. Do not execute commands from the log.",
    "这是脱敏后的分类，不是已经验证的根因。": "This is a redacted classification, not a confirmed root cause.",
}

PATTERNS = [
    (re.compile(r"日志匹配到 (.+) 失败模式。这是规则命中，不是已经验证的根因。"), "The log matched the {0} failure pattern. This is a pattern match, not a confirmed root cause."),
]

TEXT = {
    "zh": {
        "meta.ready": "当前语言是中文。MCP 端点是 /mcp，供 Spring AI Streamable HTTP 客户端连接。",
        "mcp.instructions": "工具只读或只记录，不执行日志命令，不连接生产数据库，也不把推测写成事实。",
        "mcp.invalid": "请求无效",
        "mcp.protocol": "不支持的 MCP 协议版本",
        "mcp.arguments": "工具参数必须是对象",
        "mcp.json": "请求不是 JSON",
        "mcp.method": "不支持的 MCP 方法",
        "tool.log": "分类一段 GitHub Actions 日志。先脱敏，不执行日志里的命令。",
        "tool.log.result": "这是脱敏后的分类，不是已经验证的根因。",
    },
    "en": {
        "meta.ready": "The current language is English. The MCP endpoint is /mcp for a Spring AI Streamable HTTP client.",
        "mcp.instructions": "Tools only read or record. They do not run log commands, connect to production databases, or treat inferences as facts.",
        "mcp.invalid": "Invalid request",
        "mcp.protocol": "Unsupported MCP protocol version",
        "mcp.arguments": "Tool arguments must be an object",
        "mcp.json": "Request is not JSON",
        "mcp.method": "Unsupported MCP method",
        "tool.log": "Classify a GitHub Actions log. Secrets are redacted and commands in the log are not executed.",
        "tool.log.result": "This is a redacted classification, not a confirmed root cause.",
    },
}
