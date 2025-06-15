from urllib.parse import urlparse


def is_safe_url(target: str) -> bool:
    """Return True if the URL targets this host."""
    if not target:
        return False
    return urlparse(target).netloc == ''
