"""
Category and client mapping.

Uses project_codes.xlsx as single source of truth for client/company information.
Client detection uses Gemini AI with fallback to simple keyword matching.
"""

from src.config import get_category_mapping
from src.text_utils import normalize_text


def map_category(outlook_category: str) -> str | None:
    """Map Outlook category to SharePoint category."""
    mapping = get_category_mapping()["mapping"]
    return mapping.get(outlook_category.upper())


def extract_client_from_title_keywords(
    title: str, company_names: list[str]
) -> str | None:
    """
    Extract client name from event title using simple keyword matching.
    Fallback when Gemini AI is not available.

    Args:
        title: Event title to search
        company_names: List of company names from project_codes.xlsx

    Returns:
        Matched company name or None
    """
    title_normalized = normalize_text(title)

    for company in company_names:
        company_normalized = normalize_text(company)
        # Check if company name (or significant part) appears in title
        if company_normalized in title_normalized:
            return company
        # Also check individual words for partial matches (e.g., "Wurth" in "Wurthindustry")
        for word in company_normalized.split():
            if len(word) > 3 and word in title_normalized:
                return company

    return None


def detect_client(event: dict, use_ai: bool = True) -> str | None:
    """
    Detect client from event using Gemini AI with fallback to keyword matching.

    Uses project_codes.xlsx as the single source of truth for company names.
    External domains are passed as hints to Gemini for better detection.

    Args:
        event: Calendar event with title and external_domains
        use_ai: If True, try Gemini AI first. If False, use keyword matching only.

    Returns:
        Client name or None
    """
    from src.gemini_client import detect_client_with_context
    from src.project_codes import load_project_codes
    from src.config import get_settings

    title = event.get("title", "")
    external_domains = event.get("external_domains", "")

    if not title:
        return None

    try:
        # Load project codes and extract company names
        project_codes_df = load_project_codes()
        company_names = project_codes_df["company"].unique().tolist()

        if not company_names:
            return None

        # Check if AI is enabled in config and requested
        settings = get_settings()
        ai_enabled = settings["ai"]["enabled"] and use_ai

        # Try Gemini AI first if enabled (with external_domains as hint)
        if ai_enabled:
            try:
                ai_client = detect_client_with_context(
                    title, external_domains, company_names
                )
                if ai_client:
                    return ai_client
            except Exception:
                # Gemini not available, fall through to keyword matching
                pass

        # Fallback to simple keyword matching from company names
        keyword_client = extract_client_from_title_keywords(title, company_names)
        if keyword_client:
            return keyword_client

    except Exception:
        # Silently fail if project codes cannot be loaded
        pass

    return None
