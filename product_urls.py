import re
from urllib.parse import urlparse

PLACEHOLDER_HOSTS = {
    "a.com",
    "b.com",
    "c.com",
    "example.com",
    "example.org",
    "example.net",
    "test.com",
    "placeholder.com",
    "localhost",
}

PLACEHOLDER_PATH_MARKERS = (
    "/example/",
    "/example-",
    "/placeholder",
    "/product/example",
)

SEARCH_ONLY_PATTERNS = (
    re.compile(r"amazon\.com/s\?", re.I),
    re.compile(r"walmart\.com/search", re.I),
    re.compile(r"costco\.com/CatalogSearch", re.I),
    re.compile(r"bestbuy\.com/site/searchpage", re.I),
    re.compile(r"target\.com/s\?", re.I),
    re.compile(r"homedepot\.com/s/", re.I),
    re.compile(r"lowes\.com/search", re.I),
    re.compile(r"ebay\.com/sch/", re.I),
)


def normalize_product_url(url):
    if url is None:
        return None
    cleaned = str(url).strip()
    if not cleaned or cleaned.lower() in {"#", "null", "none", "n/a"}:
        return None
    if cleaned.lower().startswith("javascript:"):
        return None
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned.lstrip('/')}"
    return cleaned


def is_placeholder_product_url(url):
    normalized = normalize_product_url(url)
    if not normalized:
        return True

    parsed = urlparse(normalized)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    if not host:
        return True
    if host in PLACEHOLDER_HOSTS:
        return True
    if host.endswith(".example") or host.endswith(".test") or host.endswith(".local"):
        return True

    path = (parsed.path or "").lower()
    for marker in PLACEHOLDER_PATH_MARKERS:
        if marker in path:
            return True

    for pattern in SEARCH_ONLY_PATTERNS:
        if pattern.search(normalized):
            return True

    return False


def is_usable_product_url(url):
    normalized = normalize_product_url(url)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return not is_placeholder_product_url(normalized)


def stored_product_url(url):
    """Return a validated URL from a price_entries row, or None."""
    if is_usable_product_url(url):
        return normalize_product_url(url)
    return None
