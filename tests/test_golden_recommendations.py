from spiremind.bootstrap import bootstrap
from spiremind.domain.models import (
    CardOptionInput,
    CardType,
    Character,
    GameId,
    RunState,
)
from spiremind.engine.card_picker import CardPickerEngine
from spiremind.engine.event_advisor import EventAdvisorEngine
from spiremind.engine.path_planner import PathCandidate, PathPlannerEngine


def _run_state(current_hp: int = 55, max_hp: int = 80) -> RunState:
    return RunState(
        game_id=GameId.STS2,
        run_id="golden-run",
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=7,
        current_hp=current_hp,
        max_hp=max_hp,
        gold=120,
    )


def test_golden_card_picker_prefers_defense_on_low_hp(tmp_path) -> None:
    store = bootstrap(tmp_path / "golden.db")
    engine = CardPickerEngine(store)

    result = engine.recommend(
        _run_state(current_hp=18, max_hp=80),
        [
            CardOptionInput("Fortify", 1, CardType.SKILL, "Gain block."),
            CardOptionInput(
                "Arc Sweep", 1, CardType.ATTACK, "Deal damage to all enemies."
            ),
            CardOptionInput("Unknown Fury", 1, CardType.ATTACK, "Deal 9 damage."),
            CardOptionInput("Skip", 0, CardType.SKILL, ""),
        ],
    )

    assert result.top_choice.name == "Fortify"


def test_golden_path_prefers_safer_route_on_low_hp() -> None:
    engine = PathPlannerEngine()
    ranked = engine.recommend(
        _run_state(current_hp=20, max_hp=80),
        [
            PathCandidate(
                id="Aggro", elite_nodes=2, rest_nodes=0, shop_nodes=1, event_nodes=1
            ),
            PathCandidate(
                id="Safe", elite_nodes=0, rest_nodes=2, shop_nodes=1, event_nodes=1
            ),
        ],
    )

    assert ranked[0].id == "Safe"


def test_golden_unknown_event_falls_back_to_last_option(tmp_path) -> None:
    store = bootstrap(tmp_path / "golden.db")
    engine = EventAdvisorEngine(store)

    result = engine.recommend(
        _run_state(current_hp=30, max_hp=80),
        "Strange New Shrine",
        ["Pay HP for buff", "Leave"],
    )

    assert result.recommended_option == "Leave"
    assert result.confidence.value == "LOW"
