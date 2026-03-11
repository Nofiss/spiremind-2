from spiremind.bootstrap import bootstrap


def test_kpi_snapshot_updates_from_logged_metrics(tmp_path) -> None:
    store = bootstrap(tmp_path / "metrics.db")
    store.log_metric("card", "LOW", 120.0)
    store.log_metric("card", "MEDIUM", 80.0)
    store.log_metric("path", "HIGH", 40.0)

    snapshot = store.get_kpi_snapshot()
    assert snapshot["samples"] == 3.0
    assert snapshot["low_confidence_pct"] > 0
    assert snapshot["p95_latency_ms"] >= 80.0
