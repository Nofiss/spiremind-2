from __future__ import annotations

from dataclasses import dataclass

from spiremind.domain.models import Confidence, RiskLevel, RunState


@dataclass(slots=True)
class PathCandidate:
    id: str
    elite_nodes: int
    rest_nodes: int
    shop_nodes: int
    event_nodes: int


@dataclass(slots=True)
class PathRecommendation:
    id: str
    score_total: float
    confidence: Confidence
    risk_level: RiskLevel
    reasons: list[str]


class PathPlannerEngine:
    def recommend(
        self,
        run_state: RunState,
        candidates: list[PathCandidate],
    ) -> list[PathRecommendation]:
        run_state.validate()
        results: list[PathRecommendation] = []
        hp_ratio = run_state.current_hp / run_state.max_hp

        for path in candidates:
            value = path.elite_nodes * 10 + path.shop_nodes * 7 + path.event_nodes * 4
            risk = path.elite_nodes * 11
            safety = path.rest_nodes * 9

            if run_state.gold >= 180:
                value += path.shop_nodes * 4
            if run_state.current_hp / run_state.max_hp > 0.7:
                value += path.elite_nodes * 2
            if hp_ratio < 0.4:
                risk += path.elite_nodes * 8
                safety += path.rest_nodes * 5
            elif hp_ratio < 0.55:
                risk += path.elite_nodes * 4
                safety += path.rest_nodes * 3

            score = max(0.0, min(100.0, 40 + value - risk + safety))
            risk_level = (
                RiskLevel.HIGH
                if risk > 20
                else RiskLevel.MEDIUM
                if risk > 10
                else RiskLevel.LOW
            )
            reasons = [
                f"Elite: {path.elite_nodes}, Rest: {path.rest_nodes}, Shop: {path.shop_nodes}",
                "Bilanciamento rischio/valore coerente con HP attuale",
            ]
            confidence = Confidence.HIGH if abs(value - risk) > 8 else Confidence.MEDIUM
            results.append(
                PathRecommendation(
                    id=path.id,
                    score_total=round(score, 2),
                    confidence=confidence,
                    risk_level=risk_level,
                    reasons=reasons,
                )
            )

        return sorted(results, key=lambda x: x.score_total, reverse=True)
