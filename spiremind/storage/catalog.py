from __future__ import annotations

import json
import sqlite3
import time
from csv import DictWriter
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from spiremind.domain.models import (
    CardOptionInput,
    CardType,
    Character,
    GameId,
    RunState,
    RunStatus,
    normalize_name,
)

SCHEMA_VERSION = "4"


@dataclass(slots=True)
class CatalogCard:
    id: int
    game_id: GameId
    name: str
    normalized_name: str
    energy_cost: int
    card_type: CardType
    tags: list[str]
    effect_text: str
    image_url: str
    status: str
    confidence_catalog: str
    source: str
    times_seen: int = 0


@dataclass(slots=True)
class CatalogEvent:
    id: int
    game_id: GameId
    name: str
    normalized_name: str
    options: list[str]
    impact_tags: list[str]
    image_url: str
    status: str
    confidence_catalog: str
    source: str
    times_seen: int = 0


@dataclass(slots=True)
class RunRecord:
    run_id: str
    game_id: GameId
    character: Character
    status: RunStatus
    created_at: str
    ended_at: str | None
    end_reason: str | None


@dataclass(slots=True)
class DecisionRecord:
    id: int
    run_id: str
    decision_type: str
    recommended: str
    chosen: str | None
    accepted: bool | None
    created_at: str


@dataclass(slots=True)
class DailyTrendRecord:
    day: str
    recommendation_count: int
    avg_latency_ms: float
    low_confidence_pct: float


@dataclass(slots=True)
class RunSummaryRecord:
    run_id: str
    status: str
    created_at: str
    ended_at: str | None
    decision_count: int
    acceptance_pct: float


class CatalogStore:
    def __init__(self, db_path: str | Path = "spiremind.db") -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        self._init_metadata_table()
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cards_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL DEFAULT 'STS2',
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    energy_cost INTEGER NOT NULL,
                    card_type TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    effect_text TEXT NOT NULL,
                    image_url TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    confidence_catalog TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (game_id, normalized_name)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_cards_game_normalized
                ON cards_catalog (game_id, normalized_name)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL DEFAULT 'STS2',
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    impact_tags_json TEXT NOT NULL,
                    image_url TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    confidence_catalog TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (game_id, normalized_name)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_events_game_normalized
                ON events_catalog (game_id, normalized_name)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS discovery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL DEFAULT 'STS2',
                    entity_type TEXT NOT NULL,
                    raw_input TEXT NOT NULL,
                    normalized_input TEXT NOT NULL,
                    run_id TEXT,
                    floor INTEGER,
                    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    times_seen INTEGER NOT NULL DEFAULT 1,
                    resolution_state TEXT NOT NULL DEFAULT 'open',
                    UNIQUE (game_id, entity_type, normalized_input)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL DEFAULT 'STS2',
                    run_id TEXT,
                    metric_type TEXT NOT NULL,
                    confidence TEXT,
                    latency_ms REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL DEFAULT 'STS2',
                    character TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    ended_at TEXT,
                    end_reason TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    floor INTEGER NOT NULL,
                    act INTEGER NOT NULL,
                    hp INTEGER NOT NULL,
                    gold INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    decision_type TEXT NOT NULL,
                    recommended TEXT NOT NULL,
                    chosen TEXT,
                    accepted INTEGER,
                    context_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_discovery_game_entity_norm
                ON discovery_log (game_id, entity_type, normalized_input)
                """
            )

        self._run_migrations()
        self._set_schema_version(SCHEMA_VERSION)

    def _init_metadata_table(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def _run_migrations(self) -> None:
        self._ensure_column_exists(
            "cards_catalog", "game_id", "TEXT NOT NULL DEFAULT 'STS2'"
        )
        self._ensure_column_exists(
            "events_catalog", "game_id", "TEXT NOT NULL DEFAULT 'STS2'"
        )
        self._ensure_column_exists(
            "discovery_log", "game_id", "TEXT NOT NULL DEFAULT 'STS2'"
        )
        self._ensure_column_exists("metrics_log", "run_id", "TEXT")
        self._ensure_column_exists(
            "cards_catalog", "image_url", "TEXT NOT NULL DEFAULT ''"
        )
        self._ensure_column_exists(
            "events_catalog", "image_url", "TEXT NOT NULL DEFAULT ''"
        )

    def _ensure_column_exists(
        self, table_name: str, column_name: str, column_def: str
    ) -> None:
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            columns = {row["name"] for row in rows}
            if column_name not in columns:
                conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"
                )

    def _set_schema_version(self, version: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO app_metadata(key, value) VALUES('schema_version', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (version,),
            )

    def get_schema_version(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_metadata WHERE key = 'schema_version'"
            ).fetchone()
        if not row:
            return None
        return str(row["value"])

    def log_metric(
        self,
        metric_type: str,
        confidence: str,
        latency_ms: float,
        run_id: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO metrics_log(game_id, run_id, metric_type, confidence, latency_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (GameId.STS2.value, run_id, metric_type, confidence, float(latency_ms)),
            )

    def measure_latency(self) -> float:
        return time.perf_counter()

    def elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000.0, 2)

    def get_kpi_snapshot(
        self,
        run_id: str | None = None,
        last_n: int | None = None,
    ) -> dict[str, float]:
        with self.connect() as conn:
            metric_params: list[Any] = [GameId.STS2.value]
            metric_where = ["game_id = ?"]
            if run_id:
                metric_where.append("run_id = ?")
                metric_params.append(run_id)
            metric_scope = f"SELECT latency_ms, confidence FROM metrics_log WHERE {' AND '.join(metric_where)} ORDER BY id DESC"
            if last_n is not None and last_n > 0:
                metric_scope += " LIMIT ?"
                metric_params.append(last_n)
            metric_rows = conn.execute(metric_scope, tuple(metric_params)).fetchall()
            reviewed_row = conn.execute(
                """
                SELECT COUNT(*) AS reviewed FROM (
                    SELECT id FROM cards_catalog WHERE game_id = ? AND status = 'reviewed'
                    UNION ALL
                    SELECT id FROM events_catalog WHERE game_id = ? AND status = 'reviewed'
                )
                """,
                (GameId.STS2.value, GameId.STS2.value),
            ).fetchone()
            discovered_row = conn.execute(
                """
                SELECT COUNT(*) AS discovered FROM (
                    SELECT id FROM cards_catalog WHERE game_id = ? AND status IN ('discovered', 'reviewed')
                    UNION ALL
                    SELECT id FROM events_catalog WHERE game_id = ? AND status IN ('discovered', 'reviewed')
                )
                """,
                (GameId.STS2.value, GameId.STS2.value),
            ).fetchone()

        total = len(metric_rows)
        low = sum(1 for row in metric_rows if row["confidence"] == "LOW")
        discovered = int(discovered_row["discovered"]) if discovered_row else 0
        reviewed = int(reviewed_row["reviewed"]) if reviewed_row else 0

        p95 = 0.0
        if metric_rows:
            sorted_rows = sorted(metric_rows, key=lambda row: float(row["latency_ms"]))
            idx = max(0, int(len(sorted_rows) * 0.95) - 1)
            p95 = float(sorted_rows[idx]["latency_ms"])

        low_pct = (low / total * 100.0) if total else 0.0
        reviewed_pct = (reviewed / discovered * 100.0) if discovered else 0.0
        return {
            "p95_latency_ms": round(p95, 2),
            "low_confidence_pct": round(low_pct, 2),
            "reviewed_pct": round(reviewed_pct, 2),
            "samples": float(total),
        }

    def get_acceptance_stats(
        self,
        run_id: str | None = None,
        last_n: int | None = None,
    ) -> dict[str, float]:
        with self.connect() as conn:
            params: list[Any] = [GameId.STS2.value]
            where = ["r.game_id = ?"]
            if run_id:
                where.append("d.run_id = ?")
                params.append(run_id)
            scope = f"SELECT d.* FROM decisions d JOIN runs r ON r.run_id = d.run_id WHERE {' AND '.join(where)} ORDER BY d.id DESC"
            if last_n is not None and last_n > 0:
                scope += " LIMIT ?"
                params.append(last_n)
            scoped_rows = conn.execute(scope, tuple(params)).fetchall()

        stats: dict[str, float] = {
            "overall_acceptance_pct": 0.0,
            "card_acceptance_pct": 0.0,
            "path_acceptance_pct": 0.0,
            "event_acceptance_pct": 0.0,
            "feedback_samples": 0.0,
        }
        total_accepted = 0
        total_feedback = 0
        counters: dict[str, dict[str, int]] = {
            "card": {"accepted": 0, "feedback": 0},
            "path": {"accepted": 0, "feedback": 0},
            "event": {"accepted": 0, "feedback": 0},
        }
        for row in scoped_rows:
            decision_type = str(row["decision_type"])
            if decision_type not in counters:
                continue
            accepted_raw = row["accepted"]
            if accepted_raw is None:
                continue
            counters[decision_type]["feedback"] += 1
            if int(accepted_raw) == 1:
                counters[decision_type]["accepted"] += 1

        for decision_type, counts in counters.items():
            total_feedback += counts["feedback"]
            total_accepted += counts["accepted"]
            pct = (
                counts["accepted"] / counts["feedback"] * 100.0
                if counts["feedback"]
                else 0.0
            )
            stats[f"{decision_type}_acceptance_pct"] = round(pct, 2)

        stats["overall_acceptance_pct"] = (
            round(total_accepted / total_feedback * 100.0, 2) if total_feedback else 0.0
        )
        stats["feedback_samples"] = float(total_feedback)
        return stats

    def list_recent_decisions(
        self, run_id: str, limit: int = 10
    ) -> list[DecisionRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, run_id, decision_type, recommended, chosen, accepted, created_at
                FROM decisions
                WHERE run_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (run_id, max(1, limit)),
            ).fetchall()
        results: list[DecisionRecord] = []
        for row in rows:
            accepted_raw = row["accepted"]
            accepted = None if accepted_raw is None else bool(accepted_raw)
            results.append(
                DecisionRecord(
                    id=int(row["id"]),
                    run_id=str(row["run_id"]),
                    decision_type=str(row["decision_type"]),
                    recommended=str(row["recommended"]),
                    chosen=row["chosen"],
                    accepted=accepted,
                    created_at=str(row["created_at"]),
                )
            )
        return results

    def export_decisions_csv(self, run_id: str, limit: int | None = None) -> str:
        with self.connect() as conn:
            query = """
                SELECT id, run_id, decision_type, recommended, chosen, accepted, created_at
                FROM decisions
                WHERE run_id = ?
                ORDER BY id DESC
            """
            params: list[Any] = [run_id]
            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            rows = conn.execute(query, tuple(params)).fetchall()

        buf = StringIO()
        writer = DictWriter(
            buf,
            fieldnames=[
                "id",
                "run_id",
                "decision_type",
                "recommended",
                "chosen",
                "accepted",
                "created_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "decision_type": row["decision_type"],
                    "recommended": row["recommended"],
                    "chosen": row["chosen"] or "",
                    "accepted": "" if row["accepted"] is None else int(row["accepted"]),
                    "created_at": row["created_at"],
                }
            )
        return buf.getvalue()

    def export_snapshots_csv(self, run_id: str, limit: int | None = None) -> str:
        with self.connect() as conn:
            query = """
                SELECT id, run_id, floor, act, hp, gold, payload_json, created_at
                FROM run_snapshots
                WHERE run_id = ?
                ORDER BY id DESC
            """
            params: list[Any] = [run_id]
            if limit is not None and limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            rows = conn.execute(query, tuple(params)).fetchall()

        buf = StringIO()
        writer = DictWriter(
            buf,
            fieldnames=[
                "id",
                "run_id",
                "floor",
                "act",
                "hp",
                "gold",
                "payload_json",
                "created_at",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row["id"],
                    "run_id": row["run_id"],
                    "floor": row["floor"],
                    "act": row["act"],
                    "hp": row["hp"],
                    "gold": row["gold"],
                    "payload_json": row["payload_json"],
                    "created_at": row["created_at"],
                }
            )
        return buf.getvalue()

    def get_daily_trends(self, days_limit: int = 14) -> list[DailyTrendRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT DATE(created_at) AS day,
                       COUNT(*) AS recommendation_count,
                       AVG(latency_ms) AS avg_latency_ms,
                       SUM(CASE WHEN confidence = 'LOW' THEN 1 ELSE 0 END) AS low_count
                FROM metrics_log
                WHERE game_id = ?
                GROUP BY DATE(created_at)
                ORDER BY day DESC
                LIMIT ?
                """,
                (GameId.STS2.value, max(1, days_limit)),
            ).fetchall()
        results: list[DailyTrendRecord] = []
        for row in rows:
            recommendation_count = int(row["recommendation_count"] or 0)
            low_count = int(row["low_count"] or 0)
            low_pct = (
                round(low_count / recommendation_count * 100.0, 2)
                if recommendation_count
                else 0.0
            )
            results.append(
                DailyTrendRecord(
                    day=str(row["day"]),
                    recommendation_count=recommendation_count,
                    avg_latency_ms=round(float(row["avg_latency_ms"] or 0.0), 2),
                    low_confidence_pct=low_pct,
                )
            )
        return results

    def get_recent_run_summaries(self, limit: int = 10) -> list[RunSummaryRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT r.run_id,
                       r.status,
                       r.created_at,
                       r.ended_at,
                       COUNT(d.id) AS decision_count,
                       SUM(CASE WHEN d.accepted = 1 THEN 1 ELSE 0 END) AS accepted_count,
                       SUM(CASE WHEN d.accepted IS NOT NULL THEN 1 ELSE 0 END) AS feedback_count
                FROM runs r
                LEFT JOIN decisions d ON d.run_id = r.run_id
                WHERE r.game_id = ?
                GROUP BY r.run_id, r.status, r.created_at, r.ended_at
                ORDER BY r.created_at DESC
                LIMIT ?
                """,
                (GameId.STS2.value, max(1, limit)),
            ).fetchall()
        results: list[RunSummaryRecord] = []
        for row in rows:
            feedback_count = int(row["feedback_count"] or 0)
            accepted_count = int(row["accepted_count"] or 0)
            acceptance_pct = (
                round(accepted_count / feedback_count * 100.0, 2)
                if feedback_count
                else 0.0
            )
            results.append(
                RunSummaryRecord(
                    run_id=str(row["run_id"]),
                    status=str(row["status"]),
                    created_at=str(row["created_at"]),
                    ended_at=row["ended_at"],
                    decision_count=int(row["decision_count"] or 0),
                    acceptance_pct=acceptance_pct,
                )
            )
        return results

    def get_active_run(self) -> RunRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM runs
                WHERE game_id = ? AND status = 'ACTIVE'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (GameId.STS2.value,),
            ).fetchone()
        if not row:
            return None
        return RunRecord(
            run_id=row["run_id"],
            game_id=GameId(row["game_id"]),
            character=Character(row["character"]),
            status=RunStatus(row["status"]),
            created_at=row["created_at"],
            ended_at=row["ended_at"],
            end_reason=row["end_reason"],
        )

    def create_run(self, run_id: str, character: Character) -> RunRecord:
        active = self.get_active_run()
        if active:
            raise ValueError("An active run already exists")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO runs(run_id, game_id, character, status)
                VALUES (?, ?, ?, ?)
                """,
                (run_id, GameId.STS2.value, character.value, RunStatus.ACTIVE.value),
            )
            row = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            raise RuntimeError("Failed to create run")
        return RunRecord(
            run_id=row["run_id"],
            game_id=GameId(row["game_id"]),
            character=Character(row["character"]),
            status=RunStatus(row["status"]),
            created_at=row["created_at"],
            ended_at=row["ended_at"],
            end_reason=row["end_reason"],
        )

    def abandon_run(self, run_id: str, reason: str = "") -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, ended_at = CURRENT_TIMESTAMP, end_reason = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    RunStatus.ABANDONED.value,
                    reason.strip() or "user_abandoned",
                    run_id,
                    RunStatus.ACTIVE.value,
                ),
            )

    def complete_run(self, run_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, ended_at = CURRENT_TIMESTAMP, end_reason = ?
                WHERE run_id = ? AND status = ?
                """,
                (
                    RunStatus.COMPLETED.value,
                    "run_completed",
                    run_id,
                    RunStatus.ACTIVE.value,
                ),
            )

    def save_snapshot(
        self,
        run_id: str,
        run_state: RunState,
        payload: dict[str, Any],
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO run_snapshots(run_id, floor, act, hp, gold, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    run_state.floor,
                    run_state.act,
                    run_state.current_hp,
                    run_state.gold,
                    json.dumps(payload),
                ),
            )

    def save_decision(
        self,
        run_id: str,
        decision_type: str,
        recommended: str,
        context: dict[str, Any],
        chosen: str | None = None,
        accepted: bool | None = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO decisions(run_id, decision_type, recommended, chosen, accepted, context_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    decision_type,
                    recommended,
                    chosen,
                    None if accepted is None else int(accepted),
                    json.dumps(context),
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to save decision")
            return int(cursor.lastrowid)

    def update_decision_feedback(
        self,
        decision_id: int,
        chosen: str,
        accepted: bool,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE decisions
                SET chosen = ?, accepted = ?
                WHERE id = ?
                """,
                (chosen, int(accepted), decision_id),
            )

    def seed_initial_cards(self) -> None:
        seed_cards = [
            {
                "name": "Guarded Strike",
                "energy_cost": 1,
                "card_type": "ATTACK",
                "tags": ["damage", "block"],
                "effect_text": "Deal damage and gain a small amount of block.",
            },
            {
                "name": "Steady Focus",
                "energy_cost": 1,
                "card_type": "SKILL",
                "tags": ["draw", "consistency"],
                "effect_text": "Draw cards and improve hand quality.",
            },
            {
                "name": "Fortify",
                "energy_cost": 1,
                "card_type": "SKILL",
                "tags": ["block", "survival"],
                "effect_text": "Gain a medium amount of block.",
            },
            {
                "name": "Momentum",
                "energy_cost": 1,
                "card_type": "POWER",
                "tags": ["scaling", "long_fight"],
                "effect_text": "Gain scaling value across turns.",
            },
            {
                "name": "Arc Sweep",
                "energy_cost": 1,
                "card_type": "ATTACK",
                "tags": ["aoe", "damage"],
                "effect_text": "Deal damage to all enemies.",
            },
        ]
        with self.connect() as conn:
            for card in seed_cards:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cards_catalog
                        (game_id, name, normalized_name, energy_cost, card_type, tags_json,
                         effect_text, image_url, status, confidence_catalog, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GameId.STS2.value,
                        card["name"],
                        normalize_name(card["name"]),
                        card["energy_cost"],
                        card["card_type"],
                        json.dumps(card["tags"]),
                        card["effect_text"],
                        "",
                        "known",
                        "MEDIUM",
                        "micro_seed",
                    ),
                )

    def seed_initial_events(self) -> None:
        seed_events = [
            {
                "name": "Strange Device",
                "options": ["Touch it", "Leave it"],
                "impact_tags": ["power_gain", "risk_unknown"],
            },
            {
                "name": "Old Map Fragment",
                "options": ["Study map", "Ignore"],
                "impact_tags": ["path_info", "low_risk"],
            },
            {
                "name": "Shifting Merchant",
                "options": ["Trade gold", "Leave"],
                "impact_tags": ["economy", "deck_quality"],
            },
        ]
        with self.connect() as conn:
            for event in seed_events:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO events_catalog
                        (game_id, name, normalized_name, options_json, impact_tags_json,
                         image_url, status, confidence_catalog, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GameId.STS2.value,
                        event["name"],
                        normalize_name(event["name"]),
                        json.dumps(event["options"]),
                        json.dumps(event["impact_tags"]),
                        "",
                        "known",
                        "MEDIUM",
                        "micro_seed",
                    ),
                )

    def get_card_by_normalized_name(self, normalized_name: str) -> CatalogCard | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM cards_catalog
                WHERE game_id = ? AND normalized_name = ?
                """,
                (GameId.STS2.value, normalized_name),
            ).fetchone()
        if not row:
            return None
        return CatalogCard(
            id=row["id"],
            game_id=GameId(row["game_id"]),
            name=row["name"],
            normalized_name=row["normalized_name"],
            energy_cost=row["energy_cost"],
            card_type=CardType(row["card_type"])
            if row["card_type"] in CardType._value2member_map_
            else CardType.UNKNOWN,
            tags=json.loads(row["tags_json"]),
            effect_text=row["effect_text"],
            image_url=row["image_url"],
            status=row["status"],
            confidence_catalog=row["confidence_catalog"],
            source=row["source"],
            times_seen=0,
        )

    def discover_card(
        self, card_input: CardOptionInput, run_id: str, floor: int
    ) -> CatalogCard:
        normalized = card_input.normalized_name()
        existing = self.get_card_by_normalized_name(normalized)
        if existing:
            self._increment_discovery(
                "card", card_input.name, normalized, run_id, floor
            )
            return existing

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO cards_catalog
                    (game_id, name, normalized_name, energy_cost, card_type, tags_json,
                     effect_text, image_url, status, confidence_catalog, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GameId.STS2.value,
                    card_input.name,
                    normalized,
                    card_input.energy_cost,
                    card_input.card_type.value,
                    json.dumps([]),
                    card_input.effect_text,
                    card_input.image_url,
                    "discovered",
                    "LOW",
                    "user_discovery",
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert discovered card")
            new_id = int(cursor.lastrowid)
        self._increment_discovery("card", card_input.name, normalized, run_id, floor)
        return CatalogCard(
            id=new_id,
            game_id=GameId.STS2,
            name=card_input.name,
            normalized_name=normalized,
            energy_cost=card_input.energy_cost,
            card_type=card_input.card_type,
            tags=[],
            effect_text=card_input.effect_text,
            image_url=card_input.image_url,
            status="discovered",
            confidence_catalog="LOW",
            source="user_discovery",
            times_seen=1,
        )

    def get_event_by_normalized_name(self, normalized_name: str) -> CatalogEvent | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM events_catalog
                WHERE game_id = ? AND normalized_name = ?
                """,
                (GameId.STS2.value, normalized_name),
            ).fetchone()
        if not row:
            return None
        return CatalogEvent(
            id=row["id"],
            game_id=GameId(row["game_id"]),
            name=row["name"],
            normalized_name=row["normalized_name"],
            options=json.loads(row["options_json"]),
            impact_tags=json.loads(row["impact_tags_json"]),
            image_url=row["image_url"],
            status=row["status"],
            confidence_catalog=row["confidence_catalog"],
            source=row["source"],
            times_seen=0,
        )

    def discover_event(
        self,
        event_name: str,
        options: list[str],
        run_id: str,
        floor: int,
        image_url: str = "",
    ) -> CatalogEvent:
        normalized = normalize_name(event_name)
        existing = self.get_event_by_normalized_name(normalized)
        if existing:
            self._increment_discovery("event", event_name, normalized, run_id, floor)
            return existing

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events_catalog
                    (game_id, name, normalized_name, options_json, impact_tags_json,
                     image_url, status, confidence_catalog, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GameId.STS2.value,
                    event_name,
                    normalized,
                    json.dumps(options),
                    json.dumps([]),
                    image_url,
                    "discovered",
                    "LOW",
                    "user_discovery",
                ),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("Failed to insert discovered event")
            new_id = int(cursor.lastrowid)
        self._increment_discovery("event", event_name, normalized, run_id, floor)
        return CatalogEvent(
            id=new_id,
            game_id=GameId.STS2,
            name=event_name,
            normalized_name=normalized,
            options=options,
            impact_tags=[],
            image_url=image_url,
            status="discovered",
            confidence_catalog="LOW",
            source="user_discovery",
            times_seen=1,
        )

    def list_discovered_cards(self) -> list[CatalogCard]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, COALESCE(dl.times_seen, 0) AS seen_count
                FROM cards_catalog c
                LEFT JOIN discovery_log dl
                    ON dl.game_id = c.game_id
                    AND dl.entity_type = 'card'
                    AND dl.normalized_input = c.normalized_name
                WHERE c.game_id = ? AND c.status = 'discovered'
                ORDER BY seen_count DESC, c.updated_at DESC, c.id DESC
                """,
                (GameId.STS2.value,),
            ).fetchall()
        return [
            CatalogCard(
                id=row["id"],
                game_id=GameId(row["game_id"]),
                name=row["name"],
                normalized_name=row["normalized_name"],
                energy_cost=row["energy_cost"],
                card_type=CardType(row["card_type"])
                if row["card_type"] in CardType._value2member_map_
                else CardType.UNKNOWN,
                tags=json.loads(row["tags_json"]),
                effect_text=row["effect_text"],
                image_url=row["image_url"],
                status=row["status"],
                confidence_catalog=row["confidence_catalog"],
                source=row["source"],
                times_seen=int(row["seen_count"]),
            )
            for row in rows
        ]

    def list_discovered_events(self) -> list[CatalogEvent]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*, COALESCE(dl.times_seen, 0) AS seen_count
                FROM events_catalog e
                LEFT JOIN discovery_log dl
                    ON dl.game_id = e.game_id
                    AND dl.entity_type = 'event'
                    AND dl.normalized_input = e.normalized_name
                WHERE e.game_id = ? AND e.status = 'discovered'
                ORDER BY seen_count DESC, e.updated_at DESC, e.id DESC
                """,
                (GameId.STS2.value,),
            ).fetchall()
        return [
            CatalogEvent(
                id=row["id"],
                game_id=GameId(row["game_id"]),
                name=row["name"],
                normalized_name=row["normalized_name"],
                options=json.loads(row["options_json"]),
                impact_tags=json.loads(row["impact_tags_json"]),
                image_url=row["image_url"],
                status=row["status"],
                confidence_catalog=row["confidence_catalog"],
                source=row["source"],
                times_seen=int(row["seen_count"]),
            )
            for row in rows
        ]

    def review_card(
        self,
        card_id: int,
        tags: list[str],
        effect_text: str,
        image_url: str = "",
    ) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT game_id, normalized_name FROM cards_catalog WHERE id = ?",
                (card_id,),
            ).fetchone()
            if not row:
                return
            conn.execute(
                """
                UPDATE cards_catalog
                SET tags_json = ?, effect_text = ?, image_url = ?, status = 'reviewed',
                    confidence_catalog = 'MEDIUM', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(tags), effect_text, image_url, card_id),
            )
            conn.execute(
                """
                UPDATE discovery_log
                SET resolution_state = 'reviewed'
                WHERE game_id = ? AND entity_type = 'card' AND normalized_input = ?
                """,
                (row["game_id"], row["normalized_name"]),
            )

    def review_event(
        self,
        event_id: int,
        impact_tags: list[str],
        image_url: str = "",
    ) -> None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT game_id, normalized_name FROM events_catalog WHERE id = ?",
                (event_id,),
            ).fetchone()
            if not row:
                return
            conn.execute(
                """
                UPDATE events_catalog
                SET impact_tags_json = ?, image_url = ?, status = 'reviewed',
                    confidence_catalog = 'MEDIUM', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(impact_tags), image_url, event_id),
            )
            conn.execute(
                """
                UPDATE discovery_log
                SET resolution_state = 'reviewed'
                WHERE game_id = ? AND entity_type = 'event' AND normalized_input = ?
                """,
                (row["game_id"], row["normalized_name"]),
            )

    def cleanup_orphaned_uploaded_images(
        self,
        upload_dir: str | Path = "assets/uploads",
    ) -> dict[str, int]:
        upload_path = Path(upload_dir)
        if not upload_path.exists():
            return {"removed": 0, "kept": 0}

        with self.connect() as conn:
            card_rows = conn.execute(
                "SELECT image_url FROM cards_catalog WHERE image_url <> ''"
            ).fetchall()
            event_rows = conn.execute(
                "SELECT image_url FROM events_catalog WHERE image_url <> ''"
            ).fetchall()

        referenced_names = {
            Path(str(row["image_url"])).name
            for row in [*card_rows, *event_rows]
            if row["image_url"]
        }

        image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        removed = 0
        kept = 0
        for file_path in upload_path.iterdir():
            if (
                not file_path.is_file()
                or file_path.suffix.lower() not in image_suffixes
            ):
                continue
            if file_path.name in referenced_names:
                kept += 1
                continue
            file_path.unlink(missing_ok=True)
            removed += 1

        return {"removed": removed, "kept": kept}

    def _increment_discovery(
        self,
        entity_type: str,
        raw_input: str,
        normalized_input: str,
        run_id: str,
        floor: int,
    ) -> None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, times_seen FROM discovery_log
                WHERE game_id = ? AND entity_type = ? AND normalized_input = ?
                """,
                (GameId.STS2.value, entity_type, normalized_input),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE discovery_log SET times_seen = ? WHERE id = ?",
                    (row["times_seen"] + 1, row["id"]),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO discovery_log
                        (game_id, entity_type, raw_input, normalized_input, run_id, floor)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GameId.STS2.value,
                        entity_type,
                        raw_input,
                        normalized_input,
                        run_id,
                        floor,
                    ),
                )
