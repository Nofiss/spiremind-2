import uuid

from spiremind.domain.models import Character
from spiremind.storage.catalog import CatalogStore


def test_acceptance_stats_by_decision_type(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id = str(uuid.uuid4())
    store.create_run(run_id, Character.IRONCLAD)

    d1 = store.save_decision(run_id, "card", "Fortify", {"k": 1})
    d2 = store.save_decision(run_id, "card", "Arc Sweep", {"k": 2})
    d3 = store.save_decision(run_id, "path", "Path A", {"k": 3})
    d4 = store.save_decision(run_id, "event", "Leave", {"k": 4})

    store.update_decision_feedback(d1, "Fortify", True)
    store.update_decision_feedback(d2, "Skip", False)
    store.update_decision_feedback(d3, "Path A", True)
    store.update_decision_feedback(d4, "Leave", True)

    stats = store.get_acceptance_stats()
    assert stats["overall_acceptance_pct"] == 75.0
    assert stats["card_acceptance_pct"] == 50.0
    assert stats["path_acceptance_pct"] == 100.0
    assert stats["event_acceptance_pct"] == 100.0
    assert stats["feedback_samples"] == 4.0


def test_list_recent_decisions(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id = str(uuid.uuid4())
    store.create_run(run_id, Character.IRONCLAD)

    first = store.save_decision(run_id, "card", "Fortify", {})
    second = store.save_decision(run_id, "event", "Leave", {})
    store.update_decision_feedback(second, "Leave", True)

    rows = store.list_recent_decisions(run_id, limit=2)
    assert len(rows) == 2
    assert rows[0].id == second
    assert rows[0].accepted is True
    assert rows[1].id == first
    assert rows[1].accepted is None
