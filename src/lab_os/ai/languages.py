"""The assistant's languages, set per device (⚙ → This device → "Assistant language", quick job 33):
what speech-to-text should expect, and what the answers are in. "" = any (the services decide)."""

LANGUAGES = {"en": "English"}  # code (ISO 639-1, as the speech services take it) → name; more later


def clean_language(code) -> str | None:
    """A language code this brain knows, or None (= any)."""
    code = str(code or "").strip().lower()
    return code if code in LANGUAGES else None
