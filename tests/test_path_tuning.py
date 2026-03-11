from spiremind.domain.models import Character, GameId, RunState
from spiremind.engine.path_planner import PathCandidate, PathPlannerEngine


def _run_state(current_hp: int, max_hp: int, gold: int) -> RunState:
    return RunState(
        game_id=GameId.STS2,
        run_id="path-run",
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=10,
        current_hp=current_hp,
        max_hp=max_hp,
        gold=gold,
    )


def test_path_tuning_prefers_shop_when_gold_high_and_risk_equal() -> None:
    engine = PathPlannerEngine()
    ranked = engine.recommend(
        _run_state(current_hp=60, max_hp=80, gold=250),
        [
            PathCandidate(
                "ShopPath", elite_nodes=1, rest_nodes=1, shop_nodes=2, event_nodes=0
            ),
            PathCandidate(
                "EventPath", elite_nodes=1, rest_nodes=1, shop_nodes=0, event_nodes=2
            ),
        ],
    )
    assert ranked[0].id == "ShopPath"
