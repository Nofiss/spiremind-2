from __future__ import annotations

import uuid
from typing import Any

import streamlit as st

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
from spiremind.ui.image_assets import (
    list_recent_uploaded_assets,
    resolve_image_source,
    validate_uploaded_image,
)


def _inject_base_styles() -> None:
    st.markdown(
        """
        <style>
        .sm-card {
            border: 1px solid #dbe3ea;
            border-radius: 14px;
            padding: 14px;
            background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
            box-shadow: 0 6px 18px rgba(26, 43, 60, 0.08);
            margin-bottom: 12px;
        }
        .sm-title {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 700;
            color: #1b3348;
        }
        .sm-meta {
            margin: 6px 0 0 0;
            color: #44586a;
            font-size: 0.9rem;
        }
        .sm-badge {
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 4px 8px;
            border-radius: 999px;
            margin-right: 6px;
            margin-top: 4px;
            color: #133248;
            background: #dceff9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_active_run(catalog) -> str:
    active = catalog.get_active_run()
    if active:
        st.session_state.run_id = active.run_id
        return active.run_id

    if "run_id" not in st.session_state:
        st.session_state.run_id = str(uuid.uuid4())
    run_id = st.session_state.run_id
    try:
        catalog.create_run(run_id, Character.IRONCLAD)
    except ValueError:
        active = catalog.get_active_run()
        if active:
            st.session_state.run_id = active.run_id
            return active.run_id
        raise
    return run_id


def _build_run_state(active_run_id: str) -> RunState:
    current_hp = st.number_input("Current HP", min_value=1, max_value=200, value=70)
    max_hp = st.number_input("Max HP", min_value=1, max_value=200, value=80)
    act = st.number_input("Act", min_value=1, max_value=4, value=1)
    floor = st.number_input("Floor", min_value=0, max_value=60, value=1)
    gold = st.number_input("Gold", min_value=0, max_value=9999, value=99)

    return RunState(
        game_id=GameId.STS2,
        run_id=active_run_id,
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


def _show_image_preview(url: str, caption: str) -> None:
    cleaned = url.strip()
    if not cleaned:
        st.caption("No image URL yet")
        return
    try:
        st.image(cleaned, caption=caption, use_container_width=True)
    except Exception:
        st.caption("Image preview unavailable. Check URL.")


def _resolve_image_source(
    image_url: str,
    uploaded_file: Any | None,
    scope: str,
    entity_name: str,
) -> str:
    try:
        return resolve_image_source(image_url, uploaded_file, scope, entity_name)
    except ValueError as error:
        st.warning(str(error))
        return image_url.strip()


def _image_uploader(label: str, key: str) -> Any | None:
    uploaded_file = st.file_uploader(
        label,
        type=["png", "jpg", "jpeg", "webp", "gif"],
        key=key,
    )
    if uploaded_file is None:
        return None
    validation_error = validate_uploaded_image(uploaded_file)
    if validation_error:
        st.warning(validation_error)
        return None
    return uploaded_file


def _card_with_resolved_image(
    card_input: CardOptionInput,
    uploaded_file: Any | None,
    scope: str,
) -> CardOptionInput:
    return CardOptionInput(
        name=card_input.name,
        energy_cost=card_input.energy_cost,
        card_type=card_input.card_type,
        effect_text=card_input.effect_text,
        image_url=_resolve_image_source(
            card_input.image_url,
            uploaded_file,
            scope,
            card_input.name,
        ),
    )


def _card_input(prefix: str, key_prefix: str) -> tuple[CardOptionInput, Any | None]:
    st.markdown(
        f"<div class='sm-card'><p class='sm-title'>{prefix}</p><p class='sm-meta'>Card details and artwork URL</p></div>",
        unsafe_allow_html=True,
    )
    name = st.text_input("Name", value="", key=f"{key_prefix}_name")
    energy_cost = st.number_input(
        "Cost", min_value=0, max_value=5, value=1, key=f"{key_prefix}_cost"
    )
    card_type_raw = st.selectbox(
        "Type",
        [card_type.value for card_type in CardType],
        index=0,
        key=f"{key_prefix}_type",
    )
    effect_text = st.text_input(
        "Effect text (optional)", value="", key=f"{key_prefix}_effect"
    )
    image_url = st.text_input(
        "Image URL (optional)",
        value="",
        placeholder="https://...",
        key=f"{key_prefix}_image_url",
    )
    uploaded_image = _image_uploader(
        "Fallback upload (optional)",
        key=f"{key_prefix}_image_upload",
    )
    if uploaded_image is not None:
        st.image(
            uploaded_image, caption=f"{prefix} upload preview", use_container_width=True
        )
    else:
        _show_image_preview(image_url, caption=f"{prefix} preview")
    return (
        CardOptionInput(
            name=name or "Unknown Card",
            energy_cost=int(energy_cost),
            card_type=CardType(card_type_raw),
            effect_text=effect_text,
            image_url=image_url.strip(),
        ),
        uploaded_image,
    )


def _render_card_results(result, latency_ms: float) -> None:
    st.success(
        f"Top choice: {result.top_choice.name} ({result.top_choice.score_total})"
    )
    st.markdown(
        f"""
        <div class='sm-card'>
            <p class='sm-title'>Recommendation Summary</p>
            <p class='sm-meta'>Overall confidence: {result.overall_confidence.value} | Latency: {latency_ms} ms</p>
            <p class='sm-meta'>{result.caution_note}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for item in result.ranked_options:
        badges = (
            f"<span class='sm-badge'>score {item.score_total}</span>"
            f"<span class='sm-badge'>{item.confidence.value}</span>"
            f"<span class='sm-badge'>{item.risk_level.value}</span>"
            f"<span class='sm-badge'>{item.entity_status}</span>"
        )
        st.markdown(
            f"<div class='sm-card'><p class='sm-title'>{item.name}</p>{badges}</div>",
            unsafe_allow_html=True,
        )
        for reason in item.reasons:
            st.write(f"- {reason}")


def _render_event_results(event_result, latency_ms: float) -> None:
    st.success(f"Recommended: {event_result.recommended_option}")
    st.markdown(
        f"""
        <div class='sm-card'>
            <p class='sm-title'>{event_result.event_name}</p>
            <span class='sm-badge'>{event_result.confidence.value}</span>
            <span class='sm-badge'>{event_result.risk_level.value}</span>
            <span class='sm-badge'>{event_result.entity_status}</span>
            <p class='sm-meta'>Latency: {latency_ms} ms</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for reason in event_result.reasons:
        st.write(f"- {reason}")


def _render_recent_asset_gallery() -> None:
    st.markdown("### Recent uploaded images")
    recent_assets = list_recent_uploaded_assets(limit=8)
    if not recent_assets:
        st.caption("No local uploads yet")
        return
    if st.button("Open upload folder path", key="open_upload_folder_path"):
        st.code("assets/uploads")
    columns = st.columns(4)
    for idx, asset in enumerate(recent_assets):
        col = columns[idx % 4]
        with col:
            st.image(asset, use_container_width=True)
            st.caption(asset.split("/")[-1])


def _render_asset_maintenance(catalog) -> None:
    st.markdown("### Asset maintenance")
    if st.button("Cleanup orphan uploads", key="cleanup_orphan_uploads"):
        stats = catalog.cleanup_orphaned_uploaded_images("assets/uploads")
        st.success(
            f"Cleanup done. Removed: {stats['removed']} | Kept referenced: {stats['kept']}"
        )


def _run_controls(catalog) -> str | None:
    st.subheader("Run Control")
    active = catalog.get_active_run()
    if active:
        st.success(f"Active run: `{active.run_id}` ({active.character.value})")
    else:
        st.info("No active run")

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("New Run"):
        if active:
            st.warning(
                "Esiste gia una run attiva. Completa o abbandona prima di crearne una nuova."
            )
        else:
            new_id = str(uuid.uuid4())
            catalog.create_run(new_id, Character.IRONCLAD)
            st.session_state.run_id = new_id
            st.success("Nuova run creata")
            st.rerun()

    if c2.button("Resume Active Run"):
        if active:
            st.session_state.run_id = active.run_id
            st.success("Run attiva ripresa")
            st.rerun()
        else:
            st.info("Nessuna run attiva da riprendere")

    abandon_reason = c3.text_input("Abandon reason", value="", key="abandon_reason")
    if c3.button("Abandon Run"):
        if active:
            catalog.abandon_run(active.run_id, abandon_reason)
            st.session_state.pop("run_id", None)
            st.warning("Run abbandonata")
            st.rerun()
        else:
            st.info("Nessuna run attiva")

    if c4.button("Complete Run"):
        if active:
            catalog.complete_run(active.run_id)
            st.session_state.pop("run_id", None)
            st.success("Run completata")
            st.rerun()
        else:
            st.info("Nessuna run attiva")

    current = catalog.get_active_run()
    return current.run_id if current else None


def _decision_feedback_ui(catalog, key_prefix: str) -> None:
    decision_id = st.session_state.get(f"{key_prefix}_decision_id")
    recommended = st.session_state.get(f"{key_prefix}_recommended")
    if not decision_id or not recommended:
        return

    st.markdown("### Feedback")
    accepted = st.button("Accepted", key=f"{key_prefix}_accepted")
    rejected = st.button("Not accepted", key=f"{key_prefix}_rejected")
    if accepted:
        catalog.update_decision_feedback(decision_id, recommended, True)
        st.success("Feedback salvato: accepted")
    if rejected:
        chosen = st.text_input(
            "Chosen option", value="", key=f"{key_prefix}_chosen_text"
        )
        if chosen:
            catalog.update_decision_feedback(decision_id, chosen, False)
            st.success("Feedback salvato: not accepted")


def main() -> None:
    st.set_page_config(page_title="SpireMind STS2", page_icon="S", layout="wide")
    _inject_base_styles()
    st.title("SpireMind MVP - Slay the Spire 2")
    st.caption("Suggerimenti carta, path, eventi e discovery progressiva")
    st.info(
        "MVP STS2 (Ironclad): quando una carta/evento e sconosciuto, il sistema usa fallback conservativo e abbassa la confidence."
    )

    catalog = bootstrap("spiremind.db")

    active_run_id = _run_controls(catalog)
    if not active_run_id:
        st.stop()

    run_state = _build_run_state(active_run_id)
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
            "Analytics",
        ]
    )

    with tabs[0]:
        st.subheader("Card options")
        input_col, result_col = st.columns([1.5, 1.2])
        with input_col:
            c1_input, c1_upload = _card_input("Card 1", "card_1")
            c2_input, c2_upload = _card_input("Card 2", "card_2")
            c3_input, c3_upload = _card_input("Card 3", "card_3")
        skip = CardOptionInput(name="Skip", energy_cost=0, card_type=CardType.SKILL)

        if input_col.button("Recommend card", type="primary"):
            c1 = _card_with_resolved_image(c1_input, c1_upload, "card")
            c2 = _card_with_resolved_image(c2_input, c2_upload, "card")
            c3 = _card_with_resolved_image(c3_input, c3_upload, "card")
            started_at = catalog.measure_latency()
            result = card_engine.recommend(run_state, [c1, c2, c3, skip])
            latency_ms = catalog.elapsed_ms(started_at)
            catalog.log_metric(
                "card",
                result.overall_confidence.value,
                latency_ms,
                run_id=active_run_id,
            )
            catalog.save_snapshot(
                active_run_id,
                run_state,
                {
                    "type": "card",
                    "options": [c1.name, c2.name, c3.name, "Skip"],
                    "top_choice": result.top_choice.name,
                },
            )
            decision_id = catalog.save_decision(
                active_run_id,
                "card",
                result.top_choice.name,
                {
                    "confidence": result.overall_confidence.value,
                    "latency_ms": latency_ms,
                },
            )
            st.session_state["card_decision_id"] = decision_id
            st.session_state["card_recommended"] = result.top_choice.name

            st.session_state["card_last_result"] = result
            st.session_state["card_last_latency"] = latency_ms

        with result_col:
            card_last = st.session_state.get("card_last_result")
            card_latency = st.session_state.get("card_last_latency")
            if card_last and card_latency is not None:
                _render_card_results(card_last, float(card_latency))

        if st.session_state.get("card_last_result"):
            result = st.session_state["card_last_result"]
            if result.overall_confidence.value == "LOW":
                st.warning(
                    "Confidence LOW: valuta review di carte/eventi sconosciuti nella tab Knowledge Review."
                )

        _decision_feedback_ui(catalog, "card")

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
            catalog.log_metric(
                "path", ranked[0].confidence.value, latency_ms, run_id=active_run_id
            )
            catalog.save_snapshot(
                active_run_id,
                run_state,
                {
                    "type": "path",
                    "options": [p1.id, p2.id],
                    "top_choice": ranked[0].id,
                },
            )
            decision_id = catalog.save_decision(
                active_run_id,
                "path",
                ranked[0].id,
                {
                    "confidence": ranked[0].confidence.value,
                    "latency_ms": latency_ms,
                },
            )
            st.session_state["path_decision_id"] = decision_id
            st.session_state["path_recommended"] = ranked[0].id

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

        _decision_feedback_ui(catalog, "path")

    with tabs[2]:
        st.subheader("Event options")
        input_col, result_col = st.columns([1.5, 1.2])
        with input_col:
            st.markdown(
                "<div class='sm-card'><p class='sm-title'>Event details</p><p class='sm-meta'>Name, image and options</p></div>",
                unsafe_allow_html=True,
            )
            event_name = st.text_input("Event name", value="Strange Device")
            event_image_url = st.text_input(
                "Event image URL (optional)",
                value="",
                placeholder="https://...",
            )
            event_image_upload = _image_uploader(
                "Fallback upload (optional)",
                key="event_image_upload",
            )
            if event_image_upload is not None:
                st.image(
                    event_image_upload,
                    caption="Event upload preview",
                    use_container_width=True,
                )
            else:
                _show_image_preview(event_image_url, caption="Event preview")
            e1 = st.text_input("Option 1", value="Touch it")
            e2 = st.text_input("Option 2", value="Leave")
            e3 = st.text_input("Option 3 (optional)", value="")
            options = [opt for opt in [e1, e2, e3] if opt.strip()]

        if input_col.button("Recommend event option", type="primary"):
            resolved_event_image = _resolve_image_source(
                event_image_url,
                event_image_upload,
                "event",
                event_name,
            )
            started_at = catalog.measure_latency()
            event_result = event_engine.recommend(
                run_state,
                event_name,
                options,
                image_url=resolved_event_image,
            )
            latency_ms = catalog.elapsed_ms(started_at)
            catalog.log_metric(
                "event", event_result.confidence.value, latency_ms, run_id=active_run_id
            )
            catalog.save_snapshot(
                active_run_id,
                run_state,
                {
                    "type": "event",
                    "event_name": event_name,
                    "options": options,
                    "top_choice": event_result.recommended_option,
                },
            )
            decision_id = catalog.save_decision(
                active_run_id,
                "event",
                event_result.recommended_option,
                {
                    "confidence": event_result.confidence.value,
                    "latency_ms": latency_ms,
                },
            )
            st.session_state["event_decision_id"] = decision_id
            st.session_state["event_recommended"] = event_result.recommended_option

            st.session_state["event_last_result"] = event_result
            st.session_state["event_last_latency"] = latency_ms

        with result_col:
            event_last = st.session_state.get("event_last_result")
            event_latency = st.session_state.get("event_last_latency")
            if event_last and event_latency is not None:
                _render_event_results(event_last, float(event_latency))

        if st.session_state.get("event_last_result"):
            event_result = st.session_state["event_last_result"]
            if event_result.entity_status == "discovered":
                st.warning(
                    "Evento non ancora reviewato: la raccomandazione privilegia opzioni conservative."
                )

        _decision_feedback_ui(catalog, "event")
        _render_recent_asset_gallery()
        _render_asset_maintenance(catalog)

    with tabs[3]:
        st.subheader("Discovered entities")
        st.caption("Review rapido di carte/eventi scoperti per aumentare affidabilita")
        discovered_cards = catalog.list_discovered_cards()
        discovered_events = catalog.list_discovered_events()

        st.markdown("### Cards")
        only_frequent_cards = st.checkbox(
            "Show cards seen at least 2 times", value=False
        )
        filtered_cards = [
            c
            for c in discovered_cards
            if (not only_frequent_cards or c.times_seen >= 2)
        ]
        if not discovered_cards:
            st.write("Nessuna carta scoperta da revisionare.")
        elif not filtered_cards:
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
                image_url = st.text_input(
                    "Image URL",
                    value=card.image_url,
                    key=f"card_image_{card.id}",
                )
                uploaded_image = _image_uploader(
                    "Fallback upload",
                    key=f"card_upload_{card.id}",
                )
                if uploaded_image is not None:
                    st.image(
                        uploaded_image,
                        caption=f"{card.name} upload preview",
                        use_container_width=True,
                    )
                else:
                    _show_image_preview(image_url, caption=card.name)
                if st.button("Mark card as reviewed", key=f"review_card_{card.id}"):
                    tags = [t.strip() for t in tags_text.split(",") if t.strip()]
                    resolved_image = _resolve_image_source(
                        image_url,
                        uploaded_image,
                        "review-card",
                        card.name,
                    )
                    catalog.review_card(card.id, tags, effect_text, resolved_image)
                    st.success("Card reviewed")

        st.markdown("### Events")
        only_frequent_events = st.checkbox(
            "Show events seen at least 2 times", value=False
        )
        filtered_events = [
            e
            for e in discovered_events
            if (not only_frequent_events or e.times_seen >= 2)
        ]
        if not discovered_events:
            st.write("Nessun evento scoperto da revisionare.")
        elif not filtered_events:
            st.write("Nessun evento corrisponde al filtro corrente.")
        for event in filtered_events:
            with st.expander(f"{event.name} [{event.status}]"):
                st.caption(f"Times seen: {event.times_seen}")
                tags_text = st.text_input(
                    "Impact tags (comma separated)",
                    value=", ".join(event.impact_tags),
                    key=f"event_tags_{event.id}",
                )
                image_url = st.text_input(
                    "Image URL",
                    value=event.image_url,
                    key=f"event_image_{event.id}",
                )
                uploaded_image = _image_uploader(
                    "Fallback upload",
                    key=f"event_upload_{event.id}",
                )
                if uploaded_image is not None:
                    st.image(
                        uploaded_image,
                        caption=f"{event.name} upload preview",
                        use_container_width=True,
                    )
                else:
                    _show_image_preview(image_url, caption=event.name)
                if st.button("Mark event as reviewed", key=f"review_event_{event.id}"):
                    tags = [t.strip() for t in tags_text.split(",") if t.strip()]
                    resolved_image = _resolve_image_source(
                        image_url,
                        uploaded_image,
                        "review-event",
                        event.name,
                    )
                    catalog.review_event(event.id, tags, resolved_image)
                    st.success("Event reviewed")

    with tabs[4]:
        st.subheader("KPI snapshot")
        scope_col, lastn_col = st.columns(2)
        kpi_scope = scope_col.selectbox(
            "Scope",
            ["All runs", "Active run only"],
            index=1,
        )
        last_n = int(
            lastn_col.number_input(
                "Last N recommendations (0 = all)",
                min_value=0,
                max_value=2000,
                value=100,
                step=10,
            )
        )
        scope_run_id = active_run_id if kpi_scope == "Active run only" else None
        scoped_last_n = None if last_n == 0 else last_n

        snapshot = catalog.get_kpi_snapshot(run_id=scope_run_id, last_n=scoped_last_n)
        acceptance = catalog.get_acceptance_stats(
            run_id=scope_run_id,
            last_n=scoped_last_n,
        )

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("p95 latency (ms)", snapshot["p95_latency_ms"])
        k2.metric("Low confidence %", snapshot["low_confidence_pct"])
        k3.metric("Reviewed %", snapshot["reviewed_pct"])
        k4.metric("Recommendation samples", int(snapshot["samples"]))

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Overall acceptance %", acceptance["overall_acceptance_pct"])
        a2.metric("Card acceptance %", acceptance["card_acceptance_pct"])
        a3.metric("Path acceptance %", acceptance["path_acceptance_pct"])
        a4.metric("Event acceptance %", acceptance["event_acceptance_pct"])
        st.write(f"Feedback samples: {int(acceptance['feedback_samples'])}")

        st.markdown("### Recent decisions (active run)")
        recent = catalog.list_recent_decisions(active_run_id, limit=8)
        if not recent:
            st.write("Nessuna decisione salvata per la run attiva.")
        else:
            for item in recent:
                accepted_label = (
                    "pending"
                    if item.accepted is None
                    else "accepted"
                    if item.accepted
                    else "not accepted"
                )
                chosen = item.chosen or "-"
                st.write(
                    f"- [{item.decision_type}] rec: {item.recommended} | chosen: {chosen} | {accepted_label}"
                )

        st.markdown("### Export CSV")
        export_limit = int(
            st.number_input(
                "Export last N rows (0 = all)",
                min_value=0,
                max_value=5000,
                value=200,
                step=50,
            )
        )
        export_n = None if export_limit == 0 else export_limit
        decisions_csv = catalog.export_decisions_csv(active_run_id, limit=export_n)
        snapshots_csv = catalog.export_snapshots_csv(active_run_id, limit=export_n)
        st.download_button(
            "Download decisions CSV",
            data=decisions_csv,
            file_name=f"spiremind_decisions_{active_run_id}.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download snapshots CSV",
            data=snapshots_csv,
            file_name=f"spiremind_snapshots_{active_run_id}.csv",
            mime="text/csv",
        )

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

    with tabs[5]:
        st.subheader("Analytics")
        trend_days = int(
            st.number_input(
                "Trend days",
                min_value=1,
                max_value=90,
                value=14,
                step=1,
            )
        )
        daily = catalog.get_daily_trends(days_limit=trend_days)
        st.markdown("### Daily trends")
        if not daily:
            st.write("Nessun dato trend disponibile.")
        else:
            for row in daily:
                st.write(
                    f"- {row.day} | recs: {row.recommendation_count} | avg latency: {row.avg_latency_ms} ms | low confidence: {row.low_confidence_pct}%"
                )

        run_limit = int(
            st.number_input(
                "Recent run summaries",
                min_value=1,
                max_value=50,
                value=10,
                step=1,
            )
        )
        summaries = catalog.get_recent_run_summaries(limit=run_limit)
        st.markdown("### Runs")
        if not summaries:
            st.write("Nessuna run trovata.")
        else:
            for run in summaries:
                ended = run.ended_at or "-"
                st.write(
                    f"- {run.run_id} | {run.status} | decisions: {run.decision_count} | acceptance: {run.acceptance_pct}% | start: {run.created_at} | end: {ended}"
                )


if __name__ == "__main__":
    main()
