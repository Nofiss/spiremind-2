import uuid

from spiremind.domain.models import Character, GameId, RunState
from spiremind.storage.catalog import CatalogStore


def _state(run_id: str, floor: int) -> RunState:
    return RunState(
        game_id=GameId.STS2,
        run_id=run_id,
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=floor,
        current_hp=50,
        max_hp=80,
        gold=100,
        relics=[],
        deck_tags={},
    )


def test_kpi_snapshot_can_filter_by_run_and_last_n(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_a = str(uuid.uuid4())
    run_b = str(uuid.uuid4())
    store.create_run(run_a, Character.IRONCLAD)
    store.log_metric("card", "LOW", 100.0, run_id=run_a)
    store.log_metric("path", "HIGH", 40.0, run_id=run_a)
    store.complete_run(run_a)

    store.create_run(run_b, Character.IRONCLAD)
    store.log_metric("event", "MEDIUM", 60.0, run_id=run_b)

    scoped = store.get_kpi_snapshot(run_id=run_b)
    assert scoped["samples"] == 1.0
    assert scoped["low_confidence_pct"] == 0.0

    limited = store.get_kpi_snapshot(last_n=2)
    assert limited["samples"] == 2.0


def test_acceptance_stats_scope_and_csv_exports(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id = str(uuid.uuid4())
    store.create_run(run_id, Character.IRONCLAD)

    d1 = store.save_decision(run_id, "card", "Fortify", {"c": 1})
    d2 = store.save_decision(run_id, "event", "Leave", {"c": 2})
    store.update_decision_feedback(d1, "Fortify", True)
    store.update_decision_feedback(d2, "Leave", False)
    store.save_snapshot(run_id, _state(run_id, 3), {"type": "card"})

    stats = store.get_acceptance_stats(run_id=run_id, last_n=2)
    assert stats["feedback_samples"] == 2.0
    assert stats["overall_acceptance_pct"] == 50.0

    decisions_csv = store.export_decisions_csv(run_id)
    snapshots_csv = store.export_snapshots_csv(run_id)
    assert "decision_type" in decisions_csv
    assert "Fortify" in decisions_csv
    assert "payload_json" in snapshots_csv
    assert "card" in snapshots_csv
