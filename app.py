from __future__ import annotations

import uuid

import streamlit as st

from spiremind.domain.models import (
    CardOptionInput,
    CardType,
    Character,
    GameId,
    RunState,
)
from spiremind.bootstrap import bootstrap
from spiremind.engine.card_picker import CardPickerEngine
from spiremind.engine.event_advisor import EventAdvisorEngine
from spiremind.engine.path_planner import PathCandidate, PathPlannerEngine


def _build_run_state() -> RunState:
    if "run_id" not in st.session_state:
        st.session_state.run_id = str(uuid.uuid4())

    current_hp = st.number_input("Current HP", min_value=1, max_value=200, value=70)
    max_hp = st.number_input("Max HP", min_value=1, max_value=200, value=80)
    act = st.number_input("Act", min_value=1, max_value=4, value=1)
    floor = st.number_input("Floor", min_value=0, max_value=60, value=1)
    gold = st.number_input("Gold", min_value=0, max_value=9999, value=99)

    return RunState(
        game_id=GameId.STS2,
        run_id=st.session_state.run_id,
        character=Character.IRONCLAD,
        ascension=0,
        act=int(act),
        floor=int(floor),
        current_hp=int(current_hp),
        max_hp=int(max_hp),
        gold=int(gold),
        relics=[],
        deck_tags={},
    )


def _card_input(prefix: str) -> CardOptionInput:
    name = st.text_input(f"{prefix} - Name", value="")
    energy_cost = st.number_input(f"{prefix} - Cost", min_value=0, max_value=5, value=1)
    card_type_raw = st.selectbox(
        f"{prefix} - Type",
        [card_type.value for card_type in CardType],
        index=0,
    )
    effect_text = st.text_input(f"{prefix} - Effect text (optional)", value="")
    return CardOptionInput(
        name=name or "Unknown Card",
        energy_cost=int(energy_cost),
        card_type=CardType(card_type_raw),
        effect_text=effect_text,
    )


def main() -> None:
    st.set_page_config(page_title="SpireMind STS2", page_icon="S", layout="wide")
    st.title("SpireMind MVP - Slay the Spire 2")
    st.caption("Suggerimenti carta, path, eventi e discovery progressiva")
    st.info(
        "MVP STS2 (Ironclad): quando una carta/evento e sconosciuto, il sistema usa fallback conservativo e abbassa la confidence."
    )

    catalog = bootstrap("spiremind.db")

    run_state = _build_run_state()

    card_engine = CardPickerEngine(catalog)
    path_engine = PathPlannerEngine()
    event_engine = EventAdvisorEngine(catalog)

    tabs = st.tabs(
        [
            "Card Picker",
            "Path Planner",
            "Event Advisor",
            "Knowledge Review",
            "KPI Dashboard",
        ]
    )

    with tabs[0]:
        st.subheader("Card options")
        c1 = _card_input("Card 1")
        c2 = _card_input("Card 2")
        c3 = _card_input("Card 3")
        skip = CardOptionInput(name="Skip", energy_cost=0, card_type=CardType.SKILL)

        if st.button("Recommend card"):
            started_at = catalog.measure_latency()
            result = card_engine.recommend(run_state, [c1, c2, c3, skip])
            latency_ms = catalog.elapsed_ms(started_at)
            catalog.log_metric("card", result.overall_confidence.value, latency_ms)
            st.success(
                f"Top choice: {result.top_choice.name} ({result.top_choice.score_total})"
            )
            st.write(f"Overall confidence: {result.overall_confidence.value}")
            st.write(f"Latency: {latency_ms} ms")
            st.write(result.caution_note)
            if result.overall_confidence.value == "LOW":
                st.warning(
                    "Confidence LOW: valuta review di carte/eventi sconosciuti nella tab Knowledge Review."
                )
            for item in result.ranked_options:
                st.markdown(
                    f"- **{item.name}** | score {item.score_total} | confidence {item.confidence.value} | status {item.entity_status}"
                )
                for reason in item.reasons:
                    st.write(f"  - {reason}")

    with tabs[1]:
        st.subheader("Path candidates")
        p1 = PathCandidate(
            id="Path A",
            elite_nodes=st.number_input(
                "Path A elites", min_value=0, max_value=5, value=1
            ),
            rest_nodes=st.number_input(
                "Path A rests", min_value=0, max_value=5, value=1
            ),
            shop_nodes=st.number_input(
                "Path A shops", min_value=0, max_value=5, value=1
            ),
            event_nodes=st.number_input(
                "Path A events", min_value=0, max_value=5, value=1
            ),
        )
        p2 = PathCandidate(
            id="Path B",
            elite_nodes=st.number_input(
                "Path B elites", min_value=0, max_value=5, value=0
            ),
            rest_nodes=st.number_input(
                "Path B rests", min_value=0, max_value=5, value=2
            ),
            shop_nodes=st.number_input(
                "Path B shops", min_value=0, max_value=5, value=1
            ),
            event_nodes=st.number_input(
                "Path B events", min_value=0, max_value=5, value=2
            ),
        )
        if st.button("Recommend path"):
            started_at = catalog.measure_latency()
            ranked = path_engine.recommend(run_state, [p1, p2])
            latency_ms = catalog.elapsed_ms(started_at)
            catalog.log_metric("path", ranked[0].confidence.value, latency_ms)
            st.success(f"Top path: {ranked[0].id} ({ranked[0].score_total})")
            st.write(f"Latency: {latency_ms} ms")
            if ranked[0].confidence.value == "LOW":
                st.warning(
                    "Path confidence LOW: preferisci percorso con piu margine di sicurezza."
                )
            for path in ranked:
                st.markdown(
                    f"- **{path.id}** | score {path.score_total} | confidence {path.confidence.value} | risk {path.risk_level.value}"
                )
                for reason in path.reasons:
                    st.write(f"  - {reason}")

    with tabs[2]:
        st.subheader("Event options")
        event_name = st.text_input("Event name", value="Strange Device")
        e1 = st.text_input("Option 1", value="Touch it")
        e2 = st.text_input("Option 2", value="Leave")
        e3 = st.text_input("Option 3 (optional)", value="")
        options = [opt for opt in [e1, e2, e3] if opt.strip()]

        if st.button("Recommend event option"):
            started_at = catalog.measure_latency()
            event_result = event_engine.recommend(run_state, event_name, options)
            latency_ms = catalog.elapsed_ms(started_at)
            catalog.log_metric("event", event_result.confidence.value, latency_ms)
            st.success(f"Recommended: {event_result.recommended_option}")
            st.write(f"Confidence: {event_result.confidence.value}")
            st.write(f"Risk: {event_result.risk_level.value}")
            st.write(f"Latency: {latency_ms} ms")
            st.write(f"Status: {event_result.entity_status}")
            if event_result.entity_status == "discovered":
                st.warning(
                    "Evento non ancora reviewato: la raccomandazione privilegia opzioni conservative."
                )
            for reason in event_result.reasons:
                st.write(f"- {reason}")

    with tabs[3]:
        st.subheader("Discovered entities")
        st.caption("Review rapido di carte/eventi scoperti per aumentare affidabilita")

        discovered_cards = catalog.list_discovered_cards()
        discovered_events = catalog.list_discovered_events()

        st.markdown("### Cards")
        only_frequent_cards = st.checkbox(
            "Show cards seen at least 2 times", value=False
        )
        if not discovered_cards:
            st.write("Nessuna carta scoperta da revisionare.")
        filtered_cards = [
            c
            for c in discovered_cards
            if (not only_frequent_cards or c.times_seen >= 2)
        ]
        if discovered_cards and not filtered_cards:
            st.write("Nessuna carta corrisponde al filtro corrente.")
        for card in filtered_cards:
            with st.expander(f"{card.name} [{card.status}]"):
                st.caption(f"Times seen: {card.times_seen}")
                tags_text = st.text_input(
                    "Tags (comma separated)",
                    value=", ".join(card.tags),
                    key=f"card_tags_{card.id}",
                )
                effect_text = st.text_input(
                    "Effect text",
                    value=card.effect_text,
                    key=f"card_effect_{card.id}",
                )
                if st.button("Mark card as reviewed", key=f"review_card_{card.id}"):
                    tags = [t.strip() for t in tags_text.split(",") if t.strip()]
                    catalog.review_card(card.id, tags, effect_text)
                    st.success("Card reviewed")

        st.markdown("### Events")
        only_frequent_events = st.checkbox(
            "Show events seen at least 2 times", value=False
        )
        if not discovered_events:
            st.write("Nessun evento scoperto da revisionare.")
        filtered_events = [
            e
            for e in discovered_events
            if (not only_frequent_events or e.times_seen >= 2)
        ]
        if discovered_events and not filtered_events:
            st.write("Nessun evento corrisponde al filtro corrente.")
        for event in filtered_events:
            with st.expander(f"{event.name} [{event.status}]"):
                st.caption(f"Times seen: {event.times_seen}")
                tags_text = st.text_input(
                    "Impact tags (comma separated)",
                    value=", ".join(event.impact_tags),
                    key=f"event_tags_{event.id}",
                )
                if st.button("Mark event as reviewed", key=f"review_event_{event.id}"):
                    tags = [t.strip() for t in tags_text.split(",") if t.strip()]
                    catalog.review_event(event.id, tags)
                    st.success("Event reviewed")

    with tabs[4]:
        st.subheader("KPI snapshot")
        snapshot = catalog.get_kpi_snapshot()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("p95 latency (ms)", snapshot["p95_latency_ms"])
        c2.metric("Low confidence %", snapshot["low_confidence_pct"])
        c3.metric("Reviewed %", snapshot["reviewed_pct"])
        c4.metric("Recommendation samples", int(snapshot["samples"]))

        st.markdown("### Target MVP")
        st.write("- p95 latency < 300 ms")
        st.write("- Low confidence in calo nel tempo")
        st.write("- Reviewed % in crescita")

        if snapshot["samples"] == 0:
            st.info(
                "Nessun dato KPI ancora disponibile. Genera alcune raccomandazioni."
            )
        elif snapshot["p95_latency_ms"] > 300:
            st.warning("p95 latency sopra target MVP (300 ms).")
        else:
            st.success("p95 latency entro target MVP.")


if __name__ == "__main__":
    main()
