import pytest

from spiremind.domain.models import Character, GameId, RunState


def test_run_state_validation_ok() -> None:
    state = RunState(
        game_id=GameId.STS2,
        run_id="r1",
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=1,
        current_hp=50,
        max_hp=80,
        gold=100,
    )
    state.validate()


def test_run_state_validation_rejects_invalid_hp() -> None:
    state = RunState(
        game_id=GameId.STS2,
        run_id="r1",
        character=Character.IRONCLAD,
        ascension=0,
        act=1,
        floor=1,
        current_hp=90,
        max_hp=80,
        gold=100,
    )
    with pytest.raises(ValueError):
        state.validate()
