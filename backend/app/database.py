from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .models import AuditEvent, Claim, ClaimCreate, DecisionRequest, RiskFactor
from .risk import extract_invoice_amount, score_claim


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimRepository:
    def __init__(self, db_path: str | None = None):
        configured = db_path or os.getenv("CLAIMLENS_DB_PATH", "./claimlens.db")
        self.db_path = configured
        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False) if configured == ":memory:" else None
        if self._memory_connection:
            self._memory_connection.row_factory = sqlite3.Row
        self.init_schema()

    @contextmanager
    def connect(self):
        if self._memory_connection:
            yield self._memory_connection
            self._memory_connection.commit()
            return
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    id TEXT PRIMARY KEY,
                    claimant TEXT NOT NULL,
                    policy_number TEXT NOT NULL,
                    incident_description TEXT NOT NULL,
                    damage_description TEXT NOT NULL,
                    claimed_amount REAL NOT NULL,
                    extracted_invoice_amount REAL,
                    risk_score INTEGER NOT NULL,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_factors TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (claim_id) REFERENCES claims(id)
                );
                CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_level, risk_score DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_claim ON audit_events(claim_id, created_at);
                """
            )

    def create(self, payload: ClaimCreate) -> Claim:
        claim_id = str(uuid4())
        created_at = utc_now()
        invoice_amount = extract_invoice_amount(payload.invoice_text)
        score, level, factors = score_claim(payload, invoice_amount)
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    claim_id,
                    payload.claimant,
                    payload.policy_number,
                    payload.incident_description,
                    payload.damage_description,
                    payload.claimed_amount,
                    invoice_amount,
                    score,
                    level,
                    "review",
                    json.dumps([factor.model_dump() for factor in factors]),
                    created_at,
                ),
            )
            conn.execute(
                "INSERT INTO audit_events (claim_id, event_type, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (claim_id, "CLAIM_CREATED", "system", f"Risk score calculated: {score}/100 ({level}).", created_at),
            )
        return self.get(claim_id)

    def list(self) -> list[Claim]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM claims ORDER BY created_at DESC").fetchall()
        return [self._to_claim(row) for row in rows]

    def get(self, claim_id: str) -> Claim | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        return self._to_claim(row) if row else None

    def decide(self, claim_id: str, decision: DecisionRequest) -> Claim | None:
        if not self.get(claim_id):
            return None
        created_at = utc_now()
        with self.connect() as conn:
            conn.execute("UPDATE claims SET status = ? WHERE id = ?", (decision.decision, claim_id))
            conn.execute(
                "INSERT INTO audit_events (claim_id, event_type, actor, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (claim_id, "DECISION_RECORDED", decision.reviewer, f"{decision.decision}: {decision.note}", created_at),
            )
        return self.get(claim_id)

    def audit(self, claim_id: str) -> list[AuditEvent]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM audit_events WHERE claim_id = ? ORDER BY created_at DESC", (claim_id,)).fetchall()
        return [AuditEvent(**dict(row)) for row in rows]

    @staticmethod
    def _to_claim(row: sqlite3.Row) -> Claim:
        data = dict(row)
        data["risk_factors"] = [RiskFactor(**factor) for factor in json.loads(data["risk_factors"])]
        return Claim(**data)

