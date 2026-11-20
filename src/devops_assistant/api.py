"""保存诊断历史。接口没有执行命令的入口。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

from devops_assistant.analyze import analyze_log


class DiagnoseIn(BaseModel):
    log: str = Field(max_length=2_000_000)
    provider: str = "github-actions"
    repository: str = ""


def create_app(db_path: str = ":memory:") -> FastAPI:
    app = FastAPI(title="AI DevOps Assistant", version="0.1.0")
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
    def create(body: DiagnoseIn):
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
        return {"id": row["id"], "report": report}

    @app.get("/api/diagnoses")
    def listing():
        rows = conn.execute("SELECT id, repository, provider, primary_cause, summary, created_at FROM diagnoses ORDER BY created_at DESC")
        return [dict(row) for row in rows]

    return app


app = create_app("devops-assistant.sqlite3")
