"""Streamlit interface for Afaq Personal Research Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st
from langgraph.types import Command

from graph import graph
from state import create_initial_state

from tools.speech_tools import (
    synthesize_speech,
    transcribe_audio,
)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
APP_NAME = "Afaq"
APP_NAME_AR = "آفاق"
APP_SUBTITLE = "Personal Research Assistant"
APP_SLOGAN = "See Beyond the Horizon."

BASE_DIR = Path(__file__).resolve().parent
PAGE_ICON_PATH = BASE_DIR / "assets" / "page_icon.png"
LOGO_PATH = BASE_DIR / "assets" / "afaq_logo.png"

st.set_page_config(
    page_title=f"{APP_NAME} | {APP_SUBTITLE}",
    page_icon=str(PAGE_ICON_PATH) if PAGE_ICON_PATH.exists() else "🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

PRIMARY = "#3b76c4"
NAVY = "#0f1c37"
LIGHT_BACKGROUND = "#f5fff9"
LIGHT_SECONDARY = "#c8d9ee"

SUCCESS = "#2f9e64"
WARNING = "#d68a1f"
ERROR = "#d84a5b"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def initialize_session() -> None:
    """Initialize values that must persist across Streamlit reruns."""

    defaults: dict[str, Any] = {
        "thread_id": f"afaq-{uuid4()}",
        "chat_history": [],
        "workflow_state": None,
        "pending_interrupt": None,
        "workflow_status": "ready",
        "active_route": "",
        "saved_path": "",
        "show_stt": False,
        "transcribed_text": "",
        "processed_audio_id": None,
        "generated_audio": {},
        "speech_error": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()


# ---------------------------------------------------------------------------
# Theme styling
# ---------------------------------------------------------------------------

def apply_theme() -> None:
    """Apply the light interface colors."""

    background = LIGHT_BACKGROUND
    secondary_background = "#e8f1fa"
    text_color = NAVY
    muted_text = "#53657d"
    card_background = "#ffffff"
    border_color = LIGHT_SECONDARY
    input_background = "#ffffff"

    st.markdown(
        f"""
        <style>
            :root {{
                --afaq-primary: {PRIMARY};
                --afaq-navy: {NAVY};
                --afaq-background: {background};
                --afaq-secondary: {secondary_background};
                --afaq-text: {text_color};
                --afaq-muted: {muted_text};
                --afaq-card: {card_background};
                --afaq-border: {border_color};
                --afaq-input: {input_background};
                --afaq-success: {SUCCESS};
                --afaq-warning: {WARNING};
                --afaq-error: {ERROR};
            }}

            .stApp {{
                background: var(--afaq-background);
                color: var(--afaq-text);
            }}

            [data-testid="stSidebar"] {{
                background: var(--afaq-secondary);
                border-right: 1px solid var(--afaq-border);
            }}

            [data-testid="stSidebar"] * {{
                color: var(--afaq-text);
            }}

            h1, h2, h3, h4, h5, h6, p, label {{
                color: var(--afaq-text);
            }}

            .afaq-sidebar-logo {{
                display: flex;
                justify-content: center;
                padding: 0.5rem 0 0.25rem 0;
            }}

            .afaq-sidebar-title {{
                text-align: center;
                font-size: 1.4rem;
                font-weight: 750;
                color: var(--afaq-navy);
                margin-top: 0.4rem;
            }}

            .afaq-sidebar-tagline {{
                text-align: center;
                margin-top: 0.3rem;
                margin-bottom: 0.6rem;
            }}

            .afaq-sidebar-slogan {{
                font-size: 0.88rem;
                font-style: italic;
                font-weight: 600;
                color: var(--afaq-primary);
                line-height: 1.3;
            }}

            .afaq-sidebar-subtitle {{
                font-size: 0.78rem;
                color: var(--afaq-muted);
                letter-spacing: 0.02rem;
                margin-top: 0.15rem;
            }}

            .afaq-welcome {{
                padding: 1.25rem;
                background: var(--afaq-card);
                border: 1px solid var(--afaq-border);
                border-radius: 16px;
                margin-bottom: 1rem;
            }}

            .afaq-welcome-title {{
                color: var(--afaq-text);
                font-size: 1.25rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }}

            .afaq-welcome-text {{
                color: var(--afaq-muted);
                margin: 0;
                line-height: 1.6;
            }}

            [class*="st-key-example-card-"] {{
                border-radius: 16px !important;
                border-color: var(--afaq-border) !important;
                background: var(--afaq-card);
                transition: box-shadow 0.15s ease, transform 0.15s ease;
                height: 100%;
            }}

            [class*="st-key-example-card-"]:hover {{
                box-shadow: 0 8px 20px rgba(15, 28, 55, 0.10);
                transform: translateY(-2px);
                border-color: var(--afaq-primary) !important;
            }}

            [class*="st-key-example-card-"] [data-testid="stVerticalBlock"] {{
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 190px;
            }}

            .afaq-example-icon {{
                font-size: 1.6rem;
                line-height: 1;
                margin-bottom: 0.5rem;
            }}

            .afaq-example-title {{
                font-weight: 700;
                font-size: 1.02rem;
                color: var(--afaq-text);
                margin-bottom: 0.35rem;
            }}

            .afaq-example-text {{
                color: var(--afaq-muted);
                font-size: 0.88rem;
                line-height: 1.5;
                margin-bottom: 0.9rem;
            }}

            [class*="st-key-tts-message-"] button {{
                background: transparent;
                border: 1px solid var(--afaq-border);
                border-radius: 999px;
                color: var(--afaq-muted);
                font-size: 0.78rem;
                font-weight: 600;
                padding: 0.1rem 0.7rem;
                min-height: 1.9rem;
            }}

            [class*="st-key-tts-message-"] button:hover {{
                border-color: var(--afaq-primary);
                color: var(--afaq-primary);
                background: rgba(59, 118, 196, 0.06);
            }}

            [class*="st-key-stt-toggle"]:not([class*="st-key-stt-toggle-active"]) button {{
                border-radius: 999px;
                border: 1px solid var(--afaq-border);
                background: var(--afaq-card);
                color: var(--afaq-text);
                font-weight: 650;
            }}

            [class*="st-key-stt-toggle"]:not([class*="st-key-stt-toggle-active"]) button:hover {{
                border-color: var(--afaq-primary);
                color: var(--afaq-primary);
            }}

            [class*="st-key-stt-toggle-active"] button {{
                border-radius: 999px;
                border: 1px solid {ERROR};
                background: rgba(216, 74, 91, 0.10);
                color: {ERROR};
                font-weight: 650;
                animation: afaq-pulse 1.6s ease-in-out infinite;
            }}

            @keyframes afaq-pulse {{
                0%, 100% {{ box-shadow: 0 0 0 0 rgba(216, 74, 91, 0.25); }}
                50% {{ box-shadow: 0 0 0 6px rgba(216, 74, 91, 0); }}
            }}

            .afaq-status-card {{
                padding: 0.8rem 0.9rem;
                background: var(--afaq-card);
                border: 1px solid var(--afaq-border);
                border-radius: 12px;
                margin-bottom: 0.75rem;
            }}

            .afaq-status-label {{
                color: var(--afaq-muted);
                font-size: 0.76rem;
                text-transform: uppercase;
                letter-spacing: 0.05rem;
            }}

            .afaq-status-value {{
                color: var(--afaq-text);
                font-weight: 650;
                margin-top: 0.2rem;
            }}

            .afaq-success {{
                padding: 0.8rem 1rem;
                border-radius: 12px;
                border-left: 5px solid {SUCCESS};
                background: rgba(47, 158, 100, 0.12);
                color: var(--afaq-text);
                margin: 0.8rem 0;
            }}

            .afaq-warning {{
                padding: 0.8rem 1rem;
                border-radius: 12px;
                border-left: 5px solid {WARNING};
                background: rgba(214, 138, 31, 0.13);
                color: var(--afaq-text);
                margin: 0.8rem 0;
            }}

            .afaq-error {{
                padding: 0.8rem 1rem;
                border-radius: 12px;
                border-left: 5px solid {ERROR};
                background: rgba(216, 74, 91, 0.13);
                color: var(--afaq-text);
                margin: 0.8rem 0;
            }}

            [data-testid="stChatMessage"] {{
                background: var(--afaq-card);
                border: 1px solid var(--afaq-border);
                border-radius: 16px;
                padding: 0.7rem;
                margin-bottom: 0.75rem;
            }}

            [data-testid="stChatInput"] {{
                background: var(--afaq-input);
                border-radius: 16px;
            }}

            div.stButton > button {{
                border-radius: 10px;
                border: 1px solid var(--afaq-border);
                font-weight: 600;
            }}

            div.stButton > button[kind="primary"] {{
                background: {PRIMARY};
                color: white;
                border-color: {PRIMARY};
            }}

            .afaq-footer {{
                color: var(--afaq-muted);
                text-align: center;
                font-size: 0.78rem;
                padding-top: 1rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_theme()


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------
def graph_config() -> dict[str, dict[str, str]]:
    """Return the LangGraph configuration for this conversation."""

    return {
        "configurable": {
            "thread_id": st.session_state.thread_id,
        }
    }


def extract_interrupt(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract an interrupt payload from a LangGraph result."""

    interrupts = result.get("__interrupt__", [])

    if not interrupts:
        return None

    interrupt_item = interrupts[0]
    value = getattr(interrupt_item, "value", None)

    if isinstance(value, dict):
        return value

    return {
        "type": "confirmation",
        "message": str(value or "Approval is required."),
    }


def append_message(
    role: str,
    content: str,
    **metadata: Any,
) -> None:
    """Append one message to the interface history."""

    st.session_state.chat_history.append(
        {
            "role": role,
            "content": content,
            **metadata,
        }
    )


def process_graph_result(result: dict[str, Any]) -> None:
    """Store a completed or interrupted LangGraph result."""

    st.session_state.workflow_state = result
    st.session_state.workflow_status = result.get(
        "workflow_status",
        "completed",
    )

    st.session_state.active_route = result.get(
        "intent",
        "",
    )

    st.session_state.saved_path = result.get(
        "saved_path",
        "",
    )

    interrupt_payload = extract_interrupt(result)

    if interrupt_payload:
        st.session_state.pending_interrupt = interrupt_payload

        message = interrupt_payload.get(
            "message",
            "Your approval is required before continuing.",
        )

        append_message(
            "assistant",
            message,
            message_type="warning",
        )

        return

    st.session_state.pending_interrupt = None

    final_response = result.get(
        "final_response",
        "",
    ).strip()

    if not final_response:
        final_response = (
            "The workflow finished, but no final response was returned."
        )

    message_type = (
        "error"
        if result.get("errors")
        else "success"
        if result.get("saved_path")
        else "normal"
    )

    append_message(
        "assistant",
        final_response,
        message_type=message_type,
        saved_path=result.get("saved_path", ""),
    )


def run_request(user_request: str) -> None:
    """Send a new user request through the complete LangGraph."""

    append_message("user", user_request)
    st.session_state.workflow_status = "running"
    st.session_state.saved_path = ""
    st.session_state.pending_interrupt = None

    try:
        with st.spinner("Afaq is working on your request..."):
            initial_state = create_initial_state(user_request)

            result = graph.invoke(
                initial_state,
                config=graph_config(),
            )

        process_graph_result(result)

    except Exception as error:
        st.session_state.workflow_status = "failed"

        append_message(
            "assistant",
            f"I could not complete the request: {error}",
            message_type="error",
        )


def resume_graph(approved: bool) -> None:
    """Resume a workflow paused for human approval."""

    st.session_state.workflow_status = "running"

    response = "yes" if approved else "no"

    try:
        with st.spinner("Resuming the workflow..."):
            result = graph.invoke(
                Command(resume=response),
                config=graph_config(),
            )

        process_graph_result(result)

    except Exception as error:
        st.session_state.workflow_status = "failed"
        st.session_state.pending_interrupt = None

        append_message(
            "assistant",
            f"I could not resume the workflow: {error}",
            message_type="error",
        )


def start_new_conversation() -> None:
    """Reset the UI and start with a new LangGraph thread."""

    st.session_state.thread_id = f"afaq-{uuid4()}"
    st.session_state.chat_history = []
    st.session_state.workflow_state = None
    st.session_state.pending_interrupt = None
    st.session_state.workflow_status = "ready"
    st.session_state.active_route = ""
    st.session_state.saved_path = ""
    st.session_state.transcribed_text = ""
    st.session_state.processed_audio_id = None
    st.session_state.generated_audio = {}
    st.session_state.speech_error = ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    if LOGO_PATH.exists():
        logo_b64 = __import__("base64").b64encode(
            LOGO_PATH.read_bytes()
        ).decode()

        st.markdown(
            f"""
            <div class="afaq-sidebar-logo">
                <img src="data:image/png;base64,{logo_b64}" width="180"
                     alt="Afaq logo">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:center;font-size:3.2rem;">🔭</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="afaq-sidebar-tagline">
            <div class="afaq-sidebar-slogan">{APP_SLOGAN}</div>
            <div class="afaq-sidebar-subtitle">{APP_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    if st.button(
        "＋ New conversation",
        use_container_width=True,
        type="primary",
    ):
        start_new_conversation()
        st.rerun()

    st.divider()

    status = st.session_state.workflow_status.replace(
        "_",
        " ",
    ).title()

    st.markdown(
        f"""
        <div class="afaq-status-card">
            <div class="afaq-status-label">Workflow status</div>
            <div class="afaq-status-value">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    active_route = (
        st.session_state.active_route.replace("_", " ").title()
        or "Not selected"
    )

    st.markdown(
        f"""
        <div class="afaq-status-card">
            <div class="afaq-status-label">Active route</div>
            <div class="afaq-status-value">{active_route}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.saved_path:
        st.markdown(
            f"""
            <div class="afaq-success">
                <strong>Saved successfully</strong><br>
                workspace/{st.session_state.saved_path}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Supported requests"):
        st.markdown(
            """
            - Ask a general question
            - Search personal notes or PDFs
            - Research an external topic
            - Generate and save a report
            - List, read, create, or update workspace files
            """
        )

    st.caption(
        f"Thread: {st.session_state.thread_id[-8:]}"
    )


# ---------------------------------------------------------------------------
# Welcome state
# ---------------------------------------------------------------------------
if not st.session_state.chat_history:
    st.markdown(
        """
        <div class="afaq-welcome">
            <div class="afaq-welcome-title">
                How can Afaq help you?
            </div>
            <p class="afaq-welcome-text">
                Ask about your personal notes, research an external topic,
                compare multiple subjects, or create and save a report.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    example_columns = st.columns(3)

    examples = [
        (
            "💡",
            "Personal knowledge",
            "What is in my note about last week's meeting?",
        ),
        (
            "🌐",
            "External research",
            "Look up the Model Context Protocol and summarize it.",
        ),
        (
            "📄",
            "Generate a report",
            (
                "Research and compare PostgreSQL, MySQL, and MongoDB, "
                "then save a Markdown report to "
                "reports/database-comparison.md."
            ),
        ),
    ]

    for index, (column, (icon, title, example)) in enumerate(
        zip(example_columns, examples)
    ):
        with column:
            with st.container(
                border=True,
                key=f"example-card-{index}",
            ):
                st.markdown(
                    f"""
                    <div class="afaq-example-icon">{icon}</div>
                    <div class="afaq-example-title">{title}</div>
                    <div class="afaq-example-text">{example}</div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    "Use example",
                    key=f"example-{title}",
                    use_container_width=True,
                ):
                    run_request(example)
                    st.rerun()


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for index, message in enumerate(
    st.session_state.chat_history
):
    role = message["role"]
    content = message["content"]

    avatar = "🔭" if role == "assistant" else "👤"
    audio_bytes = None

    with st.chat_message(
        role,
        avatar=avatar,
    ):
        st.markdown(content)

        message_type = message.get(
            "message_type",
            "normal",
        )

        if message_type == "error":
            st.error("The workflow did not complete successfully.")

        elif message_type == "success":
            saved_path = message.get("saved_path", "")

            if saved_path:
                st.success(
                    f"Saved to workspace/{saved_path}"
                )

        if role == "assistant":
            tts_key = f"tts-message-{index}"

            _, tts_column = st.columns([5, 1])

            with tts_column:
                with st.container(key=tts_key):
                    if st.button(
                        "🔊 Listen",
                        key=f"{tts_key}-btn",
                        help="Listen to this response.",
                        use_container_width=True,
                    ):
                        try:
                            with st.spinner("Generating speech..."):
                                generated = synthesize_speech(
                                    content,
                                    instructions=(
                                        "Speak clearly, naturally, and professionally. "
                                        "Use a calm and helpful tone."
                                    ),
                                )

                            st.session_state.generated_audio[index] = (
                                generated
                            )
                            st.session_state.speech_error = ""

                        except Exception as error:
                            st.session_state.speech_error = (
                                f"Text-to-speech failed: {error}"
                            )

            audio_bytes = st.session_state.generated_audio.get(
                index
            )

            if audio_bytes:
                st.audio(
                    audio_bytes,
                    format="audio/mp3",
                    autoplay=True,
                )

if st.session_state.speech_error:
    st.error(st.session_state.speech_error)


# ---------------------------------------------------------------------------
# Human approval
# ---------------------------------------------------------------------------
if st.session_state.pending_interrupt:
    pending = st.session_state.pending_interrupt
    pending_path = pending.get("file_path", "")

    st.markdown(
        f"""
        <div class="afaq-warning">
            <strong>Approval required</strong><br>
            The file <code>{pending_path}</code> already exists.
            Approve only when you want to replace its current content.
        </div>
        """,
        unsafe_allow_html=True,
    )

    approve_column, reject_column, _ = st.columns(
        [1, 1, 3]
    )

    with approve_column:
        if st.button(
            "Approve overwrite",
            type="primary",
            use_container_width=True,
        ):
            resume_graph(True)
            st.rerun()

    with reject_column:
        if st.button(
            "Reject",
            use_container_width=True,
        ):
            resume_graph(False)
            st.rerun()


# ---------------------------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------------------------
stt_key = (
    "stt-toggle-active"
    if st.session_state.show_stt
    else "stt-toggle"
)

tool_column, info_column = st.columns(
    [1, 5],
    vertical_alignment="center",
)

with tool_column:
    with st.container(key=stt_key):
        stt_label = (
            "✕ Close recorder"
            if st.session_state.show_stt
            else "🎙️ Voice input"
        )

        if st.button(
            stt_label,
            key=f"{stt_key}-btn",
            use_container_width=True,
            help="Record a spoken request — it's transcribed automatically.",
        ):
            st.session_state.show_stt = (
                not st.session_state.show_stt
            )
            st.session_state.speech_error = ""
            st.rerun()

with info_column:
    st.caption(
        "Stop recording and it's transcribed automatically — "
        "review it below, then send."
        if st.session_state.show_stt
        else "You may type your request or use voice input."
    )

# Only show the recorder itself until a transcript is ready. Once we
# have one, collapse the recorder so only the review step is visible.
if st.session_state.show_stt and not st.session_state.transcribed_text:
    audio_recording = st.audio_input(
        "Record your request",
        sample_rate=16000,
        key="stt_audio",
    )

    if audio_recording:
        recorded_bytes = audio_recording.getvalue()
        audio_id = hash(recorded_bytes)

        if st.session_state.processed_audio_id != audio_id:
            try:
                with st.spinner("Transcribing your request..."):
                    transcript = transcribe_audio(
                        audio_bytes=recorded_bytes,
                        filename=(
                            audio_recording.name or "recording.wav"
                        ),
                    )

                st.session_state.transcribed_text = transcript
                st.session_state.processed_audio_id = audio_id
                st.session_state.speech_error = ""
                st.rerun()

            except Exception as error:
                st.session_state.speech_error = (
                    f"Speech-to-text failed: {error}"
                )

if st.session_state.transcribed_text:
    st.markdown("#### Transcribed request")

    edited_transcript = st.text_area(
        "Review or edit the transcription",
        value=st.session_state.transcribed_text,
        key="transcript-editor",
        label_visibility="collapsed",
    )

    send_column, redo_column, _ = st.columns(
        [1, 1, 3]
    )

    with send_column:
        if st.button(
            "Send request",
            type="primary",
            use_container_width=True,
            key="send-transcript",
            disabled=not edited_transcript.strip(),
        ):
            request_text = edited_transcript.strip()

            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_id = None
            st.session_state.show_stt = False

            run_request(request_text)
            st.rerun()

    with redo_column:
        if st.button(
            "Re-record",
            use_container_width=True,
            key="clear-transcript",
        ):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_id = None
            st.session_state.speech_error = ""
            st.rerun()

if st.session_state.speech_error:
    st.error(st.session_state.speech_error)


# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
chat_disabled = (
    st.session_state.pending_interrupt is not None
    or st.session_state.workflow_status == "running"
    or bool(st.session_state.transcribed_text)
)

prompt = st.chat_input(
    (
        "Approve or reject the pending action first..."
        if st.session_state.pending_interrupt
        else (
            "Review or send the transcribed request above..."
            if st.session_state.transcribed_text
            else "Ask Afaq anything..."
        )
    ),
    disabled=chat_disabled,
)

if prompt:
    run_request(prompt)
    st.rerun()


st.markdown(
    """
    <div class="afaq-footer">
        Afaq Personal Research Assistant · Built with LangGraph, MCP,
        OpenAI, and Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)