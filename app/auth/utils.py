from urllib.parse import urlparse


def is_safe_url(target: str) -> bool:
    """Return True if ``target`` is a relative URL using HTTP(S)."""
    if not target:
        return False

    parsed = urlparse(target)
    if parsed.netloc:
        return False

    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return False

    return True
