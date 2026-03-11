from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from spiremind.domain.models import CardOptionInput, CardType, GameId, normalize_name

SCHEMA_VERSION = "2"


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
    status: str
    confidence_catalog: str
    source: str
    times_seen: int = 0


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
                    metric_type TEXT NOT NULL,
                    confidence TEXT,
                    latency_ms REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

    def log_metric(self, metric_type: str, confidence: str, latency_ms: float) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO metrics_log(game_id, metric_type, confidence, latency_ms)
                VALUES (?, ?, ?, ?)
                """,
                (GameId.STS2.value, metric_type, confidence, float(latency_ms)),
            )

    def measure_latency(self) -> float:
        return time.perf_counter()

    def elapsed_ms(self, started_at: float) -> float:
        return round((time.perf_counter() - started_at) * 1000.0, 2)

    def get_kpi_snapshot(self) -> dict[str, float]:
        with self.connect() as conn:
            p95_row = conn.execute(
                """
                SELECT latency_ms FROM metrics_log
                WHERE game_id = ?
                ORDER BY latency_ms ASC
                """,
                (GameId.STS2.value,),
            ).fetchall()
            total_row = conn.execute(
                "SELECT COUNT(*) AS count FROM metrics_log WHERE game_id = ?",
                (GameId.STS2.value,),
            ).fetchone()
            low_row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM metrics_log
                WHERE game_id = ? AND confidence = 'LOW'
                """,
                (GameId.STS2.value,),
            ).fetchone()
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

        total = int(total_row["count"]) if total_row else 0
        low = int(low_row["count"]) if low_row else 0
        discovered = int(discovered_row["discovered"]) if discovered_row else 0
        reviewed = int(reviewed_row["reviewed"]) if reviewed_row else 0

        p95 = 0.0
        if p95_row:
            idx = max(0, int(len(p95_row) * 0.95) - 1)
            p95 = float(p95_row[idx]["latency_ms"])

        low_pct = (low / total * 100.0) if total else 0.0
        reviewed_pct = (reviewed / discovered * 100.0) if discovered else 0.0
        return {
            "p95_latency_ms": round(p95, 2),
            "low_confidence_pct": round(low_pct, 2),
            "reviewed_pct": round(reviewed_pct, 2),
            "samples": float(total),
        }

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
                         effect_text, status, confidence_catalog, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GameId.STS2.value,
                        card["name"],
                        normalize_name(card["name"]),
                        card["energy_cost"],
                        card["card_type"],
                        json.dumps(card["tags"]),
                        card["effect_text"],
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
                         status, confidence_catalog, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GameId.STS2.value,
                        event["name"],
                        normalize_name(event["name"]),
                        json.dumps(event["options"]),
                        json.dumps(event["impact_tags"]),
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
                     effect_text, status, confidence_catalog, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GameId.STS2.value,
                    card_input.name,
                    normalized,
                    card_input.energy_cost,
                    card_input.card_type.value,
                    json.dumps([]),
                    card_input.effect_text,
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
                     status, confidence_catalog, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GameId.STS2.value,
                    event_name,
                    normalized,
                    json.dumps(options),
                    json.dumps([]),
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
                status=row["status"],
                confidence_catalog=row["confidence_catalog"],
                source=row["source"],
                times_seen=int(row["seen_count"]),
            )
            for row in rows
        ]

    def review_card(self, card_id: int, tags: list[str], effect_text: str) -> None:
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
                SET tags_json = ?, effect_text = ?, status = 'reviewed',
                    confidence_catalog = 'MEDIUM', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(tags), effect_text, card_id),
            )
            conn.execute(
                """
                UPDATE discovery_log
                SET resolution_state = 'reviewed'
                WHERE game_id = ? AND entity_type = 'card' AND normalized_input = ?
                """,
                (row["game_id"], row["normalized_name"]),
            )

    def review_event(self, event_id: int, impact_tags: list[str]) -> None:
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
                SET impact_tags_json = ?, status = 'reviewed',
                    confidence_catalog = 'MEDIUM', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(impact_tags), event_id),
            )
            conn.execute(
                """
                UPDATE discovery_log
                SET resolution_state = 'reviewed'
                WHERE game_id = ? AND entity_type = 'event' AND normalized_input = ?
                """,
                (row["game_id"], row["normalized_name"]),
            )

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
