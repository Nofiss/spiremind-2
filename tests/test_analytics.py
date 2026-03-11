import uuid

from spiremind.domain.models import Character
from spiremind.storage.catalog import CatalogStore


def test_daily_trends_and_run_summaries(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    run_id = str(uuid.uuid4())
    store.create_run(run_id, Character.IRONCLAD)
    store.log_metric("card", "LOW", 120.0, run_id=run_id)
    store.log_metric("path", "HIGH", 60.0, run_id=run_id)

    d1 = store.save_decision(run_id, "card", "Fortify", {})
    d2 = store.save_decision(run_id, "event", "Leave", {})
    store.update_decision_feedback(d1, "Fortify", True)
    store.update_decision_feedback(d2, "Leave", False)
    store.complete_run(run_id)

    trends = store.get_daily_trends(days_limit=7)
    assert len(trends) >= 1
    assert trends[0].recommendation_count >= 2
    assert trends[0].avg_latency_ms >= 60.0

    summaries = store.get_recent_run_summaries(limit=5)
    assert len(summaries) >= 1
    top = summaries[0]
    assert top.run_id == run_id
    assert top.status == "COMPLETED"
    assert top.decision_count == 2
    assert top.acceptance_pct == 50.0
