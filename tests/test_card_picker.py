from spiremind.domain.models import (
    CardOptionInput,
    CardType,
    Character,
    GameId,
    RunState,
)
from spiremind.engine.card_picker import CardPickerEngine
from spiremind.storage.catalog import CatalogStore


def _run_state() -> RunState:
    return RunState(
        game_id=GameId.STS2,
        run_id="run-1",
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=5,
        current_hp=45,
        max_hp=80,
        gold=120,
    )


def test_known_card_beats_skip_in_common_case(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()
    store.seed_initial_cards()

    engine = CardPickerEngine(store)
    result = engine.recommend(
        _run_state(),
        [
            CardOptionInput("Fortify", 1, CardType.SKILL, "Gain block."),
            CardOptionInput("Random New", 1, CardType.ATTACK, "Deal 8 damage."),
            CardOptionInput("Another New", 2, CardType.POWER, "Gain something."),
            CardOptionInput("Skip", 0, CardType.SKILL, ""),
        ],
    )
    assert result.top_choice.name != "Skip"
    assert len(result.ranked_options) == 4


def test_unknown_card_is_discovered_and_low_or_medium_confidence(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    engine = CardPickerEngine(store)
    result = engine.recommend(
        _run_state(),
        [
            CardOptionInput("Mystery Card", 1, CardType.SKILL, "Gain 8 block."),
            CardOptionInput("Mystery Card 2", 1, CardType.ATTACK, "Deal 7 damage."),
            CardOptionInput("Mystery Card 3", 1, CardType.POWER, "Gain 1 strength."),
            CardOptionInput("Skip", 0, CardType.SKILL, ""),
        ],
    )

    first = result.ranked_options[0]
    assert first.entity_status in {"discovered", "known"}
    assert result.top_choice.confidence.value in {"LOW", "MEDIUM", "HIGH"}


def test_skip_option_does_not_create_catalog_entry(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()

    engine = CardPickerEngine(store)
    engine.recommend(
        _run_state(),
        [
            CardOptionInput("Unknown A", 1, CardType.ATTACK, "Deal 8 damage."),
            CardOptionInput("Unknown B", 1, CardType.SKILL, "Gain 6 block."),
            CardOptionInput("Unknown C", 2, CardType.POWER, "Gain scaling."),
            CardOptionInput("Skip", 0, CardType.SKILL, ""),
        ],
    )

    skip_record = store.get_card_by_normalized_name("skip")
    assert skip_record is None


def test_unknown_without_effect_text_stays_low_confidence(tmp_path) -> None:
    store = CatalogStore(tmp_path / "test.db")
    store.init_db()
    engine = CardPickerEngine(store)

    result = engine.recommend(
        _run_state(),
        [
            CardOptionInput("Mystery No Text", 1, CardType.SKILL, ""),
            CardOptionInput("Mystery Damage", 1, CardType.ATTACK, "Deal 7 damage."),
            CardOptionInput("Mystery Power", 1, CardType.POWER, "Gain scaling."),
            CardOptionInput("Skip", 0, CardType.SKILL, ""),
        ],
    )

    target = next(
        item for item in result.ranked_options if item.name == "Mystery No Text"
    )
    assert target.confidence.value == "LOW"
