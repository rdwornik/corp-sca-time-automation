"""
Text utilities for handling special characters.
"""

UMLAUT_MAP = {
    "ü": "u",
    "ä": "a",
    "ö": "o",
    "ß": "ss",
    "é": "e",
    "è": "e",
    "ê": "e",
    "à": "a",
    "ç": "c",
}


def normalize_text(text: str) -> str:
    """Normalize text - lowercase and replace umlauts."""
    text = text.lower()
    for umlaut, replacement in UMLAUT_MAP.items():
        text = text.replace(umlaut, replacement)
    return text
