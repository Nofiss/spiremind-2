from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Character(str, Enum):
    IRONCLAD = "IRONCLAD"


class GameId(str, Enum):
    STS2 = "STS2"


class Confidence(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RunStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ABANDONED = "ABANDONED"
    COMPLETED = "COMPLETED"


class CardType(str, Enum):
    ATTACK = "ATTACK"
    SKILL = "SKILL"
    POWER = "POWER"
    STATUS = "STATUS"
    CURSE = "CURSE"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class RunState:
    game_id: GameId
    run_id: str
    character: Character
    ascension: int
    act: int
    floor: int
    current_hp: int
    max_hp: int
    gold: int
    relics: list[str] = field(default_factory=list)
    deck_tags: dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        if self.game_id != GameId.STS2:
            raise ValueError("MVP currently supports only STS2")
        if self.character != Character.IRONCLAD:
            raise ValueError("MVP currently supports only IRONCLAD profile")
        if not (0 <= self.current_hp <= self.max_hp):
            raise ValueError("current_hp must be between 0 and max_hp")
        if self.max_hp <= 0:
            raise ValueError("max_hp must be > 0")
        if self.ascension < 0:
            raise ValueError("ascension must be >= 0")
        if self.act < 1:
            raise ValueError("act must be >= 1")
        if self.floor < 0:
            raise ValueError("floor must be >= 0")
        if self.gold < 0:
            raise ValueError("gold must be >= 0")


@dataclass(slots=True)
class CardOptionInput:
    name: str
    energy_cost: int
    card_type: CardType
    effect_text: str = ""

    def normalized_name(self) -> str:
        return normalize_name(self.name)


@dataclass(slots=True)
class CardRecommendationOption:
    id: str
    name: str
    score_total: float
    confidence: Confidence
    risk_level: RiskLevel
    reasons: list[str]
    entity_status: str


@dataclass(slots=True)
class CardRecommendationResult:
    top_choice: CardRecommendationOption
    ranked_options: list[CardRecommendationOption]
    overall_confidence: Confidence
    caution_note: str


def normalize_name(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(normalized.split())


def clamp_score(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return round(value, 2)
