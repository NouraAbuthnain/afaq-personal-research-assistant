"""Speech-to-text and text-to-speech utilities."""

from __future__ import annotations

from io import BytesIO

from openai import OpenAI

from config import (
    OPENAI_STT_MODEL,
    OPENAI_TTS_MODEL,
    OPENAI_TTS_VOICE,
)


client = OpenAI()


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "recording.wav",
    language: str | None = None,
) -> str:
    """Convert recorded audio into text."""

    if not audio_bytes:
        raise ValueError("No audio was provided.")

    audio_file = BytesIO(audio_bytes)
    audio_file.name = filename

    request: dict[str, object] = {
        "model": OPENAI_STT_MODEL,
        "file": audio_file,
    }

    if language:
        request["language"] = language

    transcript = client.audio.transcriptions.create(
        **request,
    )

    text = transcript.text.strip()

    if not text:
        raise RuntimeError(
            "The transcription service returned empty text."
        )

    return text


def synthesize_speech(
    text: str,
    instructions: str | None = None,
) -> bytes:
    """Convert assistant text into MP3 speech."""

    clean_text = text.strip()

    if not clean_text:
        raise ValueError(
            "No assistant text was provided for speech generation."
        )

    # The speech endpoint accepts up to 4096 characters.
    clean_text = clean_text[:4096]

    request: dict[str, object] = {
        "model": OPENAI_TTS_MODEL,
        "voice": OPENAI_TTS_VOICE,
        "input": clean_text,
        "response_format": "mp3",
    }

    if instructions:
        request["instructions"] = instructions

    response = client.audio.speech.create(
        **request,
    )

    return response.read()