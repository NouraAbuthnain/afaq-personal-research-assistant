"""Central configuration for the Personal Research Assistant."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
WORKSPACE_DIR = BASE_DIR / "workspace"
REPORTS_DIR = WORKSPACE_DIR / "reports"


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------
load_dotenv(BASE_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_STT_MODEL = os.getenv("OPENAI_STT_MODEL")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE")


# ---------------------------------------------------------------------------
# Workflow limits
# ---------------------------------------------------------------------------
MAX_STEPS = 10
MAX_ERRORS = 3


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------
def validate_config() -> None:
    """Validate required settings and create local project directories."""

    missing_variables: list[str] = []

    if not OPENAI_API_KEY:
        missing_variables.append("OPENAI_API_KEY")

    if not OPENAI_MODEL:
        missing_variables.append("OPENAI_MODEL")

    if not OPENAI_STT_MODEL:
        missing_variables.append("OPENAI_STT_MODEL")

    if not OPENAI_TTS_MODEL:
        missing_variables.append("OPENAI_TTS_MODEL")

    if not OPENAI_TTS_VOICE:
        missing_variables.append("OPENAI_TTS_VOICE")

    if missing_variables:
        missing_text = ", ".join(missing_variables)
        raise RuntimeError(
            f"Missing required environment variable(s): {missing_text}. "
            "Add them to the .env file."
        )

    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)