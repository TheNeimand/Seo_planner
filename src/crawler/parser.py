"""
HTML parser for extracting links and metadata from web pages.
"""
import logging
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def normalize_url(url: str, base_url: str = "") -> str:
    """
    Normalize a URL by resolving relative paths, removing fragments,
    and unifying www vs non-www variants.

    Args:
        url: The URL to normalize.
        base_url: The base URL for resolving relative URLs.

    Returns:
        Normalized absolute URL.
    """
    if not url:
        return ""

    # Resolve relative URLs
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Skip non-http(s) URLs
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return ""

    # Normalize hostname: always use www
    netloc = parsed.netloc.lower()
    if netloc and not netloc.startswith("www."):
        netloc = "www." + netloc

    # Clean the path to remove redundant segments
    path = parsed.path
    path = path.replace("/public/index.php", "")
    path = path.replace("/index.php", "")
    path = path.rstrip("/") or "/"

    # Remove fragment and query, clean path
    cleaned = urlunparse((
        parsed.scheme.lower() if parsed.scheme else "https",
        netloc,
        path,
        parsed.params,
        "",  # Remove query params for cleaner graph
        "",  # Remove fragment
    ))

    return cleaned


def is_internal_url(url: str, site_domain: str) -> bool:
    """Check if a URL belongs to the given site domain."""
    parsed = urlparse(url)
    url_domain = parsed.netloc.lower().replace("www.", "")
    site_domain = site_domain.lower().replace("www.", "")
    return url_domain == site_domain


def is_crawlable_url(url: str) -> bool:
    """Check if a URL should be crawled (skip images, files, etc.)."""
    skip_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar",
        ".mp3", ".mp4", ".avi", ".mov", ".css", ".js", ".xml",
        ".json", ".woff", ".woff2", ".ttf", ".eot",
    )
    parsed = urlparse(url)
    path = parsed.path.lower()
    return not any(path.endswith(ext) for ext in skip_extensions)


def parse_page(html_content: str, page_url: str, site_domain: str) -> dict:
    """
    Parse an HTML page and extract links and metadata.

    Args:
        html_content: The raw HTML content.
        page_url: The URL of the page being parsed.
        site_domain: The domain of the site for internal link detection.

    Returns:
        Dict with keys:
            - title: Page title
            - meta_description: Meta description
            - internal_links: List of (target_url, anchor_text) tuples
            - external_links: List of external URLs
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Extract meta description
    meta_description = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_description = meta_tag.get("content", "")

    # Extract links
    internal_links: list[tuple[str, str]] = []
    external_links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        anchor_text = a_tag.get_text(strip=True)

        # Normalize URL
        normalized = normalize_url(href, page_url)
        if not normalized:
            continue

        # Skip self-links
        if normalize_url(page_url) == normalized:
            continue

        if is_internal_url(normalized, site_domain):
            if is_crawlable_url(normalized):
                internal_links.append((normalized, anchor_text))
        else:
            external_links.append(normalized)

    return {
        "title": title,
        "meta_description": meta_description,
        "internal_links": internal_links,
        "external_links": external_links,
    }
