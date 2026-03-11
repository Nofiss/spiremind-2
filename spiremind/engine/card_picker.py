from __future__ import annotations

from dataclasses import dataclass

from spiremind.domain.models import (
    CardOptionInput,
    CardRecommendationOption,
    CardRecommendationResult,
    CardType,
    Confidence,
    GameId,
    RiskLevel,
    RunState,
    clamp_score,
)
from spiremind.storage.catalog import CatalogCard, CatalogStore


@dataclass(slots=True)
class ScoredCard:
    option: CardRecommendationOption
    raw_score: float


class CardPickerEngine:
    def __init__(self, catalog: CatalogStore) -> None:
        self.catalog = catalog

    def recommend(
        self,
        run_state: RunState,
        card_options: list[CardOptionInput],
    ) -> CardRecommendationResult:
        run_state.validate()
        if len(card_options) != 4:
            raise ValueError("Card picker requires 4 options (3 cards + skip)")

        scored: list[ScoredCard] = []
        for option in card_options:
            catalog_card, is_unknown = self._resolve_or_discover(run_state, option)
            score, reasons = self._score_option(
                run_state, option, catalog_card, is_unknown
            )
            confidence = self._confidence_from_score(
                score,
                is_unknown,
                bool(option.effect_text.strip()),
            )
            scored.append(
                ScoredCard(
                    option=CardRecommendationOption(
                        id=option.normalized_name(),
                        name=option.name,
                        score_total=clamp_score(score),
                        confidence=confidence,
                        risk_level=self._risk_from_run(run_state),
                        reasons=reasons,
                        entity_status=catalog_card.status,
                    ),
                    raw_score=score,
                )
            )

        ranked = sorted(scored, key=lambda item: item.option.score_total, reverse=True)
        top = ranked[0].option
        overall_confidence = self._overall_confidence(ranked)
        caution_note = (
            "Valutazione standard."
            if overall_confidence != Confidence.LOW
            else "Valutazione conservativa: opzioni vicine o dati incompleti."
        )
        return CardRecommendationResult(
            top_choice=top,
            ranked_options=[item.option for item in ranked],
            overall_confidence=overall_confidence,
            caution_note=caution_note,
        )

    def _resolve_or_discover(
        self, run_state: RunState, option: CardOptionInput
    ) -> tuple[CatalogCard, bool]:
        if option.name.strip().lower() == "skip":
            return (
                CatalogCard(
                    id=-1,
                    game_id=GameId.STS2,
                    name="Skip",
                    normalized_name="skip",
                    energy_cost=0,
                    card_type=CardType.SKILL,
                    tags=["skip"],
                    effect_text="",
                    image_url="",
                    status="known",
                    confidence_catalog="HIGH",
                    source="system",
                ),
                False,
            )
        record = self.catalog.get_card_by_normalized_name(option.normalized_name())
        if record:
            self.catalog.discover_card(option, run_state.run_id, run_state.floor)
            return record, record.status == "discovered"
        discovered = self.catalog.discover_card(
            option, run_state.run_id, run_state.floor
        )
        return discovered, True

    def _score_option(
        self,
        run_state: RunState,
        option: CardOptionInput,
        catalog_card: CatalogCard,
        is_unknown: bool,
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        if option.name.strip().lower() == "skip":
            base = 36.0
            if run_state.current_hp / run_state.max_hp < 0.4:
                base += 8
                reasons.append("Skip prudente: HP basso, priorita sopravvivenza")
            else:
                reasons.append("Skip accettabile se il deck e gia coerente")
            return base, reasons

        score = 45.0
        tags = set(catalog_card.tags)
        hp_ratio = run_state.current_hp / run_state.max_hp

        if option.card_type == CardType.SKILL:
            score += 4
            reasons.append("Skill migliora consistenza difensiva")
        if option.card_type == CardType.POWER:
            score += 3
            reasons.append("Power utile per valore progressivo nei fight lunghi")
        if option.card_type == CardType.ATTACK:
            score += 2
            reasons.append("Attack aumenta danno immediato")

        if "block" in tags and hp_ratio < 0.6:
            score += 12
            reasons.append("Sinergia difensiva forte con HP non pieno")
        if "aoe" in tags and run_state.act == 1:
            score += 8
            reasons.append("Copertura AoE utile nelle fasi iniziali")
        if "scaling" in tags and run_state.act >= 2:
            score += 8
            reasons.append("Scaling utile nei fight lunghi")
        if "consistency" in tags:
            score += 6
            reasons.append("Migliora consistenza generale del deck")
        if "draw" in tags:
            score += 6
            reasons.append("Piu draw aumenta stabilita delle mani")

        if is_unknown:
            score -= 12
            reasons.insert(0, "Carta nuova non profilata: valutazione parziale")
            if not option.effect_text.strip():
                score -= 4
                reasons.append("Nessun testo effetto: confidenza ridotta")
            kw_bonus, kw_reason = self._unknown_keyword_bonus(option.effect_text)
            score += kw_bonus
            if kw_reason:
                reasons.append(kw_reason)

        if (
            hp_ratio < 0.35
            and option.card_type == CardType.ATTACK
            and "block" not in tags
        ):
            score -= 6
            reasons.append("Rischio alto: priorita difesa su danno puro")

        while len(reasons) < 2:
            reasons.append("Scelta coerente con stato run corrente")

        return score, reasons[:4]

    def _unknown_keyword_bonus(self, effect_text: str) -> tuple[float, str]:
        text = effect_text.lower()
        if not text:
            return 0.0, ""
        score = 0.0
        reasons: list[str] = []
        if "block" in text or "shield" in text:
            score += 4.0
            reasons.append("difesa")
        if "draw" in text:
            score += 3.0
            reasons.append("cycling")
        if "strength" in text or "scaling" in text:
            score += 3.0
            reasons.append("scaling")
        if "all enemies" in text or "aoe" in text:
            score += 4.0
            reasons.append("aoe")
        if not reasons:
            return 0.0, ""
        reason_text = ", ".join(reasons[:2])
        return min(score, 8.0), f"Testo suggerisce {reason_text}"

    def _confidence_from_score(
        self,
        score: float,
        is_unknown: bool,
        has_effect_text: bool,
    ) -> Confidence:
        if is_unknown:
            if not has_effect_text:
                return Confidence.LOW
            return Confidence.LOW if score < 65 else Confidence.MEDIUM
        if score >= 70:
            return Confidence.HIGH
        if score >= 55:
            return Confidence.MEDIUM
        return Confidence.LOW

    def _overall_confidence(self, ranked: list[ScoredCard]) -> Confidence:
        if len(ranked) < 2:
            return Confidence.LOW
        if ranked[0].option.confidence == Confidence.LOW:
            return Confidence.LOW
        margin = ranked[0].option.score_total - ranked[1].option.score_total
        if margin >= 10 and ranked[0].option.confidence == Confidence.HIGH:
            return Confidence.HIGH
        if margin >= 5:
            return Confidence.MEDIUM
        return Confidence.LOW

    def _risk_from_run(self, run_state: RunState) -> RiskLevel:
        hp_ratio = run_state.current_hp / run_state.max_hp
        if hp_ratio < 0.35:
            return RiskLevel.HIGH
        if hp_ratio < 0.65:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
