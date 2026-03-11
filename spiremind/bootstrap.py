from __future__ import annotations

from pathlib import Path

from spiremind.storage.catalog import CatalogStore


def bootstrap(db_path: str | Path = "spiremind.db") -> CatalogStore:
    catalog = CatalogStore(db_path)
    catalog.init_db()
    catalog.seed_initial_cards()
    catalog.seed_initial_events()
    return catalog
