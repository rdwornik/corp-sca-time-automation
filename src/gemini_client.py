"""
Gemini Flash API client for intelligent text generation.
"""

from google import genai
from src.config import get_env, get_settings


def get_client():
    """Initialize and return Gemini client."""
    api_key = get_env("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    return genai.Client(api_key=api_key)


def call_gemini(prompt: str) -> str:
    """Call Gemini Flash API with prompt."""
    try:
        settings = get_settings()
        model = settings["ai"]["model"]

        client = get_client()
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API error: {e}")
        return ""


def detect_client_with_context(
    title: str, external_domains: str, company_names: list[str]
) -> str:
    """
    Use Gemini AI to detect client from meeting title and external domains.

    This is the primary client detection function that uses external_domains as hints.

    Args:
        title: Meeting title
        external_domains: Comma-separated list of external email domains (hint for detection)
        company_names: List of company names from project_codes.xlsx

    Returns:
        Client name from the list, or empty string if no match
    """
    if not title or not company_names:
        return ""

    # Build prompt with external domains as hint
    domain_hint = ""
    if external_domains:
        domain_hint = f"\nExternal attendee domains: {external_domains}"

    prompt = f"""Meeting title: '{title}'{domain_hint}
Known clients: {", ".join(company_names)}

Which client is this meeting most likely about? Consider:
- Domain names often contain client name (e.g., michelin.com -> Michelin, veronesi.it -> Veronesi)
- Language hints in title (Italian words -> Italian clients, German words -> German clients)
- Company name mentions or abbreviations in title
- Context clues in the meeting title

Reply with ONLY the client name from the list, or 'Unknown' if not clear.
No explanation, just the name."""

    result = call_gemini(prompt)

    # Validate result is in the list (case-insensitive)
    result_lower = result.strip().lower()
    for client in company_names:
        if client.lower() == result_lower:
            return client

    return ""


def detect_client_from_comment(comment: str, project_codes: list[str]) -> str:
    """
    Use Gemini AI to match comment/title to most likely client from project codes.

    Deprecated: Use detect_client_with_context instead for better results.

    Args:
        comment: Meeting title or comment text
        project_codes: List of company names from project codes

    Returns:
        Client name from the list, or empty string if no match
    """
    return detect_client_with_context(comment, "", project_codes)


def generate_autofill_comment(category: str, client: str, week_context: str) -> str:
    """Generate a realistic comment for autofilled time entry."""
    prompt = f"""Generate a brief, professional time entry comment for:
- Category: {category}
- Client: {client if client else "Internal"}
- Week activities: {week_context}

Reply with ONLY a short comment (5-15 words) describing typical work.
No quotes, no explanation."""

    return call_gemini(prompt) or f"{category} work"
