"""保存诊断历史。接口没有执行命令的入口。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from devops_assistant.analyze import analyze_log, correlate
from devops_assistant.i18n import install, localize_error, negotiate, translate_payload
from devops_assistant.mcp_server import mount


class DiagnoseIn(BaseModel):
    log: str = Field(max_length=2_000_000)
    provider: str = "github-actions"
    repository: str = ""


def create_app(db_path: str = ":memory:") -> FastAPI:
    app = FastAPI(title="AI DevOps Assistant", version="0.1.6")
    install(app)
    mount(app)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS diagnoses (
          id TEXT PRIMARY KEY, repository TEXT NOT NULL, provider TEXT NOT NULL,
          primary_cause TEXT NOT NULL, summary TEXT NOT NULL, payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    app.state.conn = conn

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/diagnoses")
    def create(body: DiagnoseIn, request: Request):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        report = analyze_log(body.log, body.provider)
        row = {
            "id": uuid.uuid4().hex,
            "repository": body.repository.strip(),
            "provider": body.provider,
            "primary_cause": report["primary"],
            "summary": report["summary"],
            "payload_json": json.dumps(report, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        conn.execute(
            "INSERT INTO diagnoses VALUES (:id,:repository,:provider,:primary_cause,:summary,:payload_json,:created_at)",
            row,
        )
        conn.commit()
        return translate_payload({"id": row["id"], "report": report}, locale)

    @app.get("/api/diagnoses/groups")
    def groups():
        records = []
        rows = conn.execute("SELECT id, payload_json FROM diagnoses ORDER BY created_at")
        for row in rows:
            payload = json.loads(row["payload_json"])
            records.append(
                {
                    "id": row["id"],
                    "primary": payload.get("primary"),
                    "tests": payload.get("tests") or [],
                    "fingerprint": payload.get("fingerprint"),
                }
            )
        return correlate(records)

    @app.get("/api/diagnoses")
    def listing(request: Request):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        rows = conn.execute("SELECT id, repository, provider, primary_cause, summary, created_at FROM diagnoses ORDER BY created_at DESC")
        items = []
        for row in rows:
            item = dict(row)
            item["summary"] = localize_error(item["summary"], locale)
            items.append(item)
        return items

    return app


app = create_app("devops-assistant.sqlite3")
