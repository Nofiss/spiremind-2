from spiremind.bootstrap import bootstrap
from spiremind.storage.catalog import CatalogStore, SCHEMA_VERSION


def test_bootstrap_sets_schema_version(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = bootstrap(db_path)
    assert store.get_schema_version() == SCHEMA_VERSION


def test_schema_includes_image_url_columns(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()

    with store.connect() as conn:
        card_cols = conn.execute("PRAGMA table_info(cards_catalog)").fetchall()
        event_cols = conn.execute("PRAGMA table_info(events_catalog)").fetchall()

    assert "image_url" in {row["name"] for row in card_cols}
    assert "image_url" in {row["name"] for row in event_cols}


def test_review_sets_discovery_resolution_state(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()

    event = store.discover_event("Unknown Event", ["Take", "Leave"], "run-1", 5)
    store.review_event(event.id, ["safe"])

    with store.connect() as conn:
        row = conn.execute(
            """
            SELECT resolution_state FROM discovery_log
            WHERE game_id = 'STS2' AND entity_type = 'event' AND normalized_input = 'unknown event'
            """
        ).fetchone()

    assert row is not None
    assert row["resolution_state"] == "reviewed"
