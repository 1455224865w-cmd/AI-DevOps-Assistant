"""保存诊断历史。接口没有执行命令的入口。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from devops_assistant.analyze import analyze_log, correlate
from devops_assistant.i18n import install, localize_error, negotiate, translate_payload
from devops_assistant.mcp_server import mount


class DiagnoseIn(BaseModel):
    log: str = Field(max_length=2_000_000)
    provider: str = "github-actions"
    repository: str = ""


def _mount_console(app: FastAPI) -> None:
    web = Path(__file__).resolve().parent / "web"

    @app.get("/", include_in_schema=False)
    def console_page():
        return FileResponse(web / "index.html")

    app.mount("/assets", StaticFiles(directory=web), name="assets")


def create_app(db_path: str = ":memory:") -> FastAPI:
    app = FastAPI(title="AI DevOps Assistant", version="0.1.8")
    install(app)
    mount(app)
    _mount_console(app)
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

    @app.get("/api/diagnoses/{diagnosis_id}")
    def detail(diagnosis_id: str, request: Request):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        row = conn.execute("SELECT payload_json FROM diagnoses WHERE id=?", (diagnosis_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="诊断记录不存在")
        report = json.loads(row["payload_json"])
        return translate_payload({"id": diagnosis_id, "report": report}, locale)

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
