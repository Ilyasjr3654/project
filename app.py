from html import escape
from pathlib import Path

import streamlit as st

from src.config import get_settings
from src.presentation.renderers import render_presentation
from src.services.reporting_service import ReportingResult, run_reporting, run_simple_reporting
from src.sql.executor import database_exists


APP_ROOT = Path(__file__).resolve().parent
APP_VERSION = "2026-07-31-reporting-fallback"
settings = get_settings()

st.set_page_config(
    page_title="ReportIQ | Reporting commercial",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _load_styles() -> None:
    stylesheet = APP_ROOT / "assets" / "styles.css"
    st.markdown(f"<style>{stylesheet.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


_load_styles()


MODE_LABELS = {
    "simple": "Mode simple",
    "langchain": "IA + RAG",
}

SUGGESTED_QUESTIONS = [
    ("Chiffre d'affaires total", "Quel est le chiffre d'affaires total ?", ":material/payments:"),
    ("CA par région", "Quel est le chiffre d'affaires par région ?", ":material/map:"),
    ("Top 5 clients", "Quels sont les 5 meilleurs clients ?", ":material/leaderboard:"),
    (
        "Produits les plus vendus",
        "Quels sont les produits les plus vendus ?",
        ":material/inventory_2:",
    ),
    ("Ventes mensuelles", "Montre-moi les ventes par mois.", ":material/calendar_month:"),
    ("Panier moyen", "Quel est le panier moyen ?", ":material/shopping_cart:"),
]


def _conversation_history(entries: list[dict]) -> list[dict]:
    context: list[dict] = []
    for entry in entries:
        result: ReportingResult = entry["result"]
        generation = result.sql_generation
        context.append(
            {
                "question": result.question,
                "title": result.title,
                "answer": result.answer,
                "used_tables": generation.used_tables if generation else [],
            }
        )
    return context


def _render_rag_documents(result: ReportingResult, include_metadata: bool) -> None:
    if not result.rag:
        return

    for document in result.rag.documents:
        document_type = document.metadata.get("type", "source")
        document_name = document.metadata.get("name", "document")
        label = f"{document_type} · {document_name}"
        if document.score is not None:
            label += f" · pertinence {document.score:.3f}"
        st.markdown(f"**{label}**")
        if include_metadata:
            st.json(document.metadata)
        st.text(document.content)


def _render_result_summary(result: ReportingResult) -> None:
    generation = result.sql_generation
    confidence = generation.confidence if generation else 0.0
    total_ms = (
        (result.rag.duration_ms if result.rag else 0.0)
        + result.generation_ms
        + result.sql_ms
        + result.interpretation_ms
    )

    metrics = st.columns(3)
    metrics[0].metric("Lignes analysées", result.row_count)
    metrics[1].metric("Confiance", f"{confidence:.0%}")
    metrics[2].metric("Temps de réponse", f"{total_ms / 1000:.1f} s")


def _render_traceability(result: ReportingResult) -> None:
    generation = result.sql_generation
    if not generation:
        return

    with st.expander(
        "Traçabilité de l'analyse",
        expanded=False,
        icon=":material/fact_check:",
    ):
        details = st.columns(2)
        with details[0]:
            st.markdown("**Tables utilisées**")
            st.write(", ".join(generation.used_tables) or "Aucune")
        with details[1]:
            st.markdown("**Règles métier appliquées**")
            if generation.applied_business_rules:
                for rule in generation.applied_business_rules:
                    st.markdown(f"- {rule}")
            else:
                st.write("Aucune")


def _render_result(result: ReportingResult, index: int, entry_mode: str) -> None:
    st.markdown(
        f"<div class='response-meta'><span>{escape(MODE_LABELS[entry_mode])}</span>"
        f"<span>Analyse {index + 1:02d}</span></div>",
        unsafe_allow_html=True,
    )

    status_renderers = {
        "clarification": st.info,
        "out_of_scope": st.warning,
        "error": st.error,
    }
    status_renderer = status_renderers.get(result.status)
    if status_renderer:
        status_renderer(result.answer)

    if result.status == "ready" and result.presentation and result.dataframe is not None:
        if result.dataframe.empty:
            st.info("La requête n'a retourné aucune ligne.")
        else:
            render_presentation(result.dataframe, result.presentation)
            _render_result_summary(result)

            csv_data = result.dataframe.to_csv(index=False).encode("utf-8-sig")
            actions = st.columns([1.15, 1.15, 3.7])
            with actions[0]:
                st.download_button(
                    "Exporter CSV",
                    data=csv_data,
                    file_name=f"reporting_analyse_{index + 1}.csv",
                    mime="text/csv",
                    key=f"download_csv_{index}",
                    icon=":material/download:",
                    use_container_width=True,
                )
            with actions[1]:
                if result.sql:
                    st.button(
                        "SQL validé",
                        key=f"sql_status_{index}",
                        icon=":material/verified:",
                        disabled=True,
                        use_container_width=True,
                    )

    _render_traceability(result)

    if result.sql:
        with st.expander(
            "Requête SQL générée",
            expanded=False,
            icon=":material/code:",
        ):
            st.code(result.sql, language="sql")

    if result.rag:
        with st.expander(
            "Sources métier utilisées",
            expanded=False,
            icon=":material/library_books:",
        ):
            _render_rag_documents(result, include_metadata=False)

    if result.dataframe is not None:
        with st.expander(
            "Données brutes",
            expanded=False,
            icon=":material/table_view:",
        ):
            st.dataframe(result.dataframe, use_container_width=True, hide_index=True)

def _provider_status(mode: str) -> tuple[str, str, str]:
    if mode == "simple":
        return "is-ready", "Moteur prêt", "Règles locales · aucun appel LLM"
    if settings.llm_provider == "openai" and not settings.has_openai_key:
        return "is-warning", "Configuration requise", "Clé OpenAI absente"
    if settings.llm_provider == "ollama":
        return "is-ready", "Moteur local prêt", settings.active_chat_model
    return "is-ready", "OpenAI configuré", settings.active_chat_model


if not database_exists():
    st.error(
        "Base de données introuvable. Exécutez d'abord : "
        "python database/create_database.py"
    )
    st.stop()


if st.session_state.get("app_version") != APP_VERSION:
    st.session_state.reporting_history = []
    st.session_state.app_version = APP_VERSION

history = st.session_state.get("reporting_history", [])
if history and any("result" not in entry for entry in history):
    history = []
st.session_state.reporting_history = history

suggested_question: str | None = None

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">R</div>
            <div class="brand-copy">
                <strong>ReportIQ</strong>
                <span>Business intelligence</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="sidebar-section">Mode d’analyse</p>', unsafe_allow_html=True)
    mode = st.segmented_control(
        "Mode d'analyse",
        options=list(MODE_LABELS),
        default=settings.default_mode,
        format_func=MODE_LABELS.get,
        label_visibility="collapsed",
        key="analysis_mode",
    )
    mode = mode or settings.default_mode

    status_class, status_title, status_detail = _provider_status(mode)
    st.markdown(
        f"""
        <div class="engine-status {status_class}">
            <span class="status-dot"></span>
            <div><strong>{escape(status_title)}</strong><span>{escape(status_detail)}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="sidebar-section">Questions suggérées</p>', unsafe_allow_html=True)
    for question_index, (label, full_question, icon) in enumerate(SUGGESTED_QUESTIONS):
        if st.button(
            label,
            key=f"suggestion_{question_index}",
            icon=icon,
            type="tertiary",
            use_container_width=True,
        ):
            suggested_question = full_question

    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    if st.button(
        "Nouvelle analyse",
        icon=":material/add:",
        type="secondary",
        use_container_width=True,
        disabled=not history,
    ):
        st.session_state.reporting_history = []
        st.rerun()

    st.markdown(
        "<p class='sidebar-footer'>Base SQLite · 4 tables commerciales</p>",
        unsafe_allow_html=True,
    )


header_mode = MODE_LABELS[mode]
st.markdown(
    f"""
    <div class="workspace-header">
        <div>
            <p class="workspace-kicker">ESPACE ANALYTIQUE</p>
            <h1>Reporting commercial</h1>
            <p class="workspace-subtitle">Pilotez vos indicateurs clients, ventes et produits.</p>
        </div>
        <div class="workspace-status">
            <span class="connection-dot"></span>
            <div><strong>Base connectée</strong><span>SQLite · {escape(header_mode)}</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not history:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-mark">01</div>
            <h2>Nouvelle analyse</h2>
            <p>Chiffre d’affaires, clients, produits et tendances commerciales.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

typed_question = st.chat_input("Posez une question sur vos données commerciales")
question = typed_question or suggested_question

if question:
    if mode == "langchain" and settings.llm_provider == "openai" and not settings.has_openai_key:
        st.error("Ajoutez OPENAI_API_KEY dans le fichier .env ou sélectionnez le mode simple.")
    else:
        with st.spinner("Analyse des données en cours..."):
            if mode == "simple":
                result = run_simple_reporting(question, settings=settings)
            else:
                result = run_reporting(
                    question,
                    history=_conversation_history(history),
                    settings=settings,
                )
        history.append({"mode": mode, "result": result})
        st.session_state.reporting_history = history

for index, entry in enumerate(history):
    result = entry["result"]
    with st.chat_message("user", avatar=":material/person:"):
        st.write(result.question)
    with st.chat_message("assistant", avatar=":material/monitoring:"):
        _render_result(result, index, entry["mode"])
