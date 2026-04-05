"""
Keyword mapper for analyzing shared keywords between pages.
"""
import logging
from collections import defaultdict

from src.gsc.models import Page

logger = logging.getLogger(__name__)


class KeywordMapper:
    """Maps and analyzes keywords across pages."""

    def __init__(self):
        self.keyword_to_pages: dict[str, list[str]] = defaultdict(list)

    def build_keyword_index(self, pages: dict[str, Page]) -> None:
        """
        Build an inverted index from keywords to pages.

        Args:
            pages: Dict of URL -> Page with keyword data populated.
        """
        self.keyword_to_pages.clear()

        for url, page in pages.items():
            for kw in page.gsc_keywords:
                if kw.query not in self.keyword_to_pages.get(kw.query, []):
                    self.keyword_to_pages[kw.query].append(url)

        logger.info(
            f"Keyword index built: {len(self.keyword_to_pages)} unique keywords"
        )

    def find_shared_keywords(
        self, url_a: str, url_b: str, pages: dict[str, Page]
    ) -> list[str]:
        """
        Find keywords shared between two pages.

        Args:
            url_a: First page URL.
            url_b: Second page URL.
            pages: Dict of URL -> Page.

        Returns:
            List of shared keyword strings.
        """
        if url_a not in pages or url_b not in pages:
            return []

        kw_a = {kw.query for kw in pages[url_a].gsc_keywords}
        kw_b = {kw.query for kw in pages[url_b].gsc_keywords}
        return sorted(kw_a & kw_b)

    def get_keyword_clusters(
        self,
        pages: dict[str, Page],
        min_shared: int = 3,
    ) -> list[tuple[str, str, list[str]]]:
        """
        Find page pairs with significant keyword overlap.

        Args:
            pages: Dict of URL -> Page.
            min_shared: Minimum shared keywords threshold.

        Returns:
            List of (url_a, url_b, shared_keywords) tuples.
        """
        clusters = []
        page_urls = list(pages.keys())

        for i in range(len(page_urls)):
            for j in range(i + 1, len(page_urls)):
                shared = self.find_shared_keywords(
                    page_urls[i], page_urls[j], pages
                )
                if len(shared) >= min_shared:
                    clusters.append((page_urls[i], page_urls[j], shared))

        clusters.sort(key=lambda c: len(c[2]), reverse=True)
        return clusters
