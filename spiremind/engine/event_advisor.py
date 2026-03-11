from __future__ import annotations

from dataclasses import dataclass

from spiremind.domain.models import Confidence, RiskLevel, RunState
from spiremind.storage.catalog import CatalogStore


@dataclass(slots=True)
class EventRecommendation:
    event_name: str
    recommended_option: str
    confidence: Confidence
    risk_level: RiskLevel
    reasons: list[str]
    entity_status: str


class EventAdvisorEngine:
    def __init__(self, catalog: CatalogStore) -> None:
        self.catalog = catalog

    def recommend(
        self,
        run_state: RunState,
        event_name: str,
        options: list[str],
        image_url: str = "",
    ) -> EventRecommendation:
        run_state.validate()
        record = self.catalog.discover_event(
            event_name,
            options,
            run_state.run_id,
            run_state.floor,
            image_url=image_url,
        )
        hp_ratio = run_state.current_hp / run_state.max_hp

        if record.status == "known":
            if hp_ratio < 0.4 and len(options) > 1:
                safe_option = options[-1]
                return EventRecommendation(
                    event_name=event_name,
                    recommended_option=safe_option,
                    confidence=Confidence.MEDIUM,
                    risk_level=RiskLevel.MEDIUM,
                    reasons=[
                        "HP basso: priorita opzione meno rischiosa",
                        "Evento noto ma stato run richiede prudenza",
                    ],
                    entity_status=record.status,
                )
            return EventRecommendation(
                event_name=event_name,
                recommended_option=options[0] if options else "Leave",
                confidence=Confidence.MEDIUM,
                risk_level=RiskLevel.MEDIUM,
                reasons=[
                    "Evento noto STS2: scelta baseline di valore",
                    "Trade-off compatibile con stato run",
                ],
                entity_status=record.status,
            )

        safe_option = options[-1] if options else "Leave"
        return EventRecommendation(
            event_name=event_name,
            recommended_option=safe_option,
            confidence=Confidence.LOW,
            risk_level=RiskLevel.MEDIUM if hp_ratio >= 0.4 else RiskLevel.HIGH,
            reasons=[
                "Evento nuovo non profilato: uso fallback conservativo",
                "Priorita a opzione con rischio minimo immediato",
            ],
            entity_status=record.status,
        )
