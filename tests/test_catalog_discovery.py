from spiremind.domain.models import CardOptionInput, CardType
from spiremind.storage.catalog import CatalogStore


def test_discover_unknown_card_creates_discovered_record(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()

    card = CardOptionInput(
        name="Custom Slam",
        energy_cost=2,
        card_type=CardType.ATTACK,
        effect_text="Deal 14 damage",
        image_url="https://example.com/custom-slam.png",
    )

    discovered = store.discover_card(card, run_id="r1", floor=3)
    assert discovered.status == "discovered"

    lookup = store.get_card_by_normalized_name(card.normalized_name())
    assert lookup is not None
    assert lookup.name == "Custom Slam"
    assert lookup.image_url == "https://example.com/custom-slam.png"


def test_discovery_log_increments_for_repeated_seen(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()

    card = CardOptionInput(
        name="Repeat Card",
        energy_cost=1,
        card_type=CardType.SKILL,
    )

    store.discover_card(card, run_id="r1", floor=1)
    store.discover_card(card, run_id="r1", floor=2)

    with store.connect() as conn:
        row = conn.execute(
            "SELECT times_seen FROM discovery_log WHERE entity_type = 'card' AND normalized_input = ?",
            (card.normalized_name(),),
        ).fetchone()
    assert row is not None
    assert row["times_seen"] == 2


def test_seed_contains_sts2_micro_seed_card(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()
    store.seed_initial_cards()

    card = store.get_card_by_normalized_name("guarded strike")
    assert card is not None
    assert card.source == "micro_seed"


def test_discover_event_persists_image_url(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    store = CatalogStore(db_path)
    store.init_db()

    event = store.discover_event(
        "Mystery Fountain",
        ["Drink", "Leave"],
        "r1",
        6,
        image_url="https://example.com/fountain.png",
    )

    assert event.image_url == "https://example.com/fountain.png"

    lookup = store.get_event_by_normalized_name("mystery fountain")
    assert lookup is not None
    assert lookup.image_url == "https://example.com/fountain.png"


def test_cleanup_orphaned_uploaded_images_keeps_referenced(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    keep_path = upload_dir / "keep.png"
    keep_path.write_bytes(b"ok")
    orphan_path = upload_dir / "orphan.png"
    orphan_path.write_bytes(b"orphan")

    store = CatalogStore(db_path)
    store.init_db()
    card = CardOptionInput(
        name="Image Card",
        energy_cost=1,
        card_type=CardType.SKILL,
        image_url=str(keep_path).replace("\\", "/"),
    )
    store.discover_card(card, run_id="r1", floor=1)

    stats = store.cleanup_orphaned_uploaded_images(upload_dir)

    assert stats["removed"] == 1
    assert stats["kept"] == 1
    assert keep_path.exists()
    assert not orphan_path.exists()
