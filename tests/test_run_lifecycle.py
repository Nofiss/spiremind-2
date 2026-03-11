import uuid

import pytest

from spiremind.domain.models import Character, GameId, RunState
from spiremind.storage.catalog import CatalogStore


def test_single_active_run_enforced(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id_1 = str(uuid.uuid4())
    store.create_run(run_id_1, Character.IRONCLAD)

    with pytest.raises(ValueError):
        store.create_run(str(uuid.uuid4()), Character.IRONCLAD)


def test_abandon_and_create_new_run(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id_1 = str(uuid.uuid4())
    store.create_run(run_id_1, Character.IRONCLAD)
    store.abandon_run(run_id_1, "test abandon")
    assert store.get_active_run() is None

    run_id_2 = str(uuid.uuid4())
    created = store.create_run(run_id_2, Character.IRONCLAD)
    assert created.run_id == run_id_2


def test_save_snapshot_and_decision_with_feedback(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id = str(uuid.uuid4())
    store.create_run(run_id, Character.IRONCLAD)
    state = RunState(
        game_id=GameId.STS2,
        run_id=run_id,
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=3,
        current_hp=45,
        max_hp=80,
        gold=100,
        relics=[],
        deck_tags={},
    )

    store.save_snapshot(run_id, state, {"kind": "card"})
    decision_id = store.save_decision(
        run_id,
        "card",
        "Fortify",
        {"confidence": "MEDIUM"},
    )
    store.update_decision_feedback(decision_id, "Fortify", True)

    with store.connect() as conn:
        snapshot_row = conn.execute(
            "SELECT COUNT(*) AS count FROM run_snapshots WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        decision_row = conn.execute(
            "SELECT accepted, chosen FROM decisions WHERE id = ?",
            (decision_id,),
        ).fetchone()

    assert snapshot_row is not None
    assert snapshot_row["count"] == 1
    assert decision_row is not None
    assert decision_row["accepted"] == 1
    assert decision_row["chosen"] == "Fortify"
