"""
Google Search Console API client.
Fetches keyword/page performance data.
"""
import logging
import time
from datetime import datetime, timedelta

from src.config import (
    GSC_API_DELAY,
    GSC_DEFAULT_DAYS,
    GSC_ROW_LIMIT,
)
from src.gsc.models import KeywordData, Page
from src.crawler.parser import normalize_url

logger = logging.getLogger(__name__)


class GSCClient:
    """Client for interacting with the Google Search Console API."""

    def __init__(self, service, site_url: str):
        self.service = service
        self.site_url = site_url

    def _get_date_range(self, days: int | None = None) -> tuple[str, str]:
        """Get start and end date strings for the API query."""
        days = days or GSC_DEFAULT_DAYS
        end_date = datetime.now() - timedelta(days=3)  # GSC data has ~3 day delay
        start_date = end_date - timedelta(days=days)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def fetch_all_pages(
        self,
        days: int | None = None,
        progress_callback=None,
    ) -> dict[str, Page]:
        """
        Fetch performance data for all pages.

        Args:
            days: Number of days to look back.
            progress_callback: Optional callback(current, total, message).

        Returns:
            Dict of URL -> Page with aggregated metrics.
        """
        start_date, end_date = self._get_date_range(days)
        pages: dict[str, Page] = {}
        start_row = 0
        total_rows = 0

        if progress_callback:
            progress_callback(0, 0, "GSC sayfa verileri çekiliyor...")

        while True:
            try:
                request_body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["page"],
                    "rowLimit": GSC_ROW_LIMIT,
                    "startRow": start_row,
                }
                response = (
                    self.service.searchanalytics()
                    .query(siteUrl=self.site_url, body=request_body)
                    .execute()
                )

                rows = response.get("rows", [])
                if not rows:
                    break

                for row in rows:
                    raw_url = row["keys"][0]
                    url = normalize_url(raw_url)
                    if not url:
                        url = raw_url
                    # Merge duplicates
                    if url in pages:
                        pages[url].total_clicks += int(row.get("clicks", 0))
                        pages[url].total_impressions += int(row.get("impressions", 0))
                    else:
                        pages[url] = Page(
                            url=url,
                            total_clicks=int(row.get("clicks", 0)),
                            total_impressions=int(row.get("impressions", 0)),
                            avg_ctr=round(row.get("ctr", 0.0), 4),
                            avg_position=round(row.get("position", 0.0), 1),
                        )

                total_rows += len(rows)
                start_row += len(rows)

                if progress_callback:
                    progress_callback(total_rows, 0, f"{total_rows} sayfa verisi çekildi...")

                logger.info(f"Fetched {total_rows} page rows so far.")

                if len(rows) < GSC_ROW_LIMIT:
                    break

                time.sleep(GSC_API_DELAY)

            except Exception as e:
                logger.error(f"Error fetching page data: {e}")
                break

        logger.info(f"Total pages fetched: {len(pages)}")
        return pages

    def fetch_keywords_for_page(
        self,
        page_url: str,
        days: int | None = None,
        progress_callback=None,
    ) -> list[KeywordData]:
        """
        Fetch keyword data for a specific page.

        Args:
            page_url: The URL of the page.
            days: Number of days to look back.
            progress_callback: Optional callback(current, total, message).

        Returns:
            List of KeywordData for the page.
        """
        start_date, end_date = self._get_date_range(days)
        keywords: list[KeywordData] = []
        start_row = 0

        if progress_callback:
            progress_callback(0, 0, f"Anahtar kelimeler çekiliyor: {page_url[:60]}...")

        while True:
            try:
                request_body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["query"],
                    "dimensionFilterGroups": [
                        {
                            "filters": [
                                {
                                    "dimension": "page",
                                    "operator": "equals",
                                    "expression": page_url,
                                }
                            ]
                        }
                    ],
                    "rowLimit": GSC_ROW_LIMIT,
                    "startRow": start_row,
                }
                response = (
                    self.service.searchanalytics()
                    .query(siteUrl=self.site_url, body=request_body)
                    .execute()
                )

                rows = response.get("rows", [])
                if not rows:
                    break

                for row in rows:
                    keywords.append(
                        KeywordData(
                            query=row["keys"][0],
                            clicks=int(row.get("clicks", 0)),
                            impressions=int(row.get("impressions", 0)),
                            ctr=round(row.get("ctr", 0.0), 4),
                            position=round(row.get("position", 0.0), 1),
                        )
                    )

                start_row += len(rows)

                if len(rows) < GSC_ROW_LIMIT:
                    break

                time.sleep(GSC_API_DELAY)

            except Exception as e:
                logger.error(f"Error fetching keywords for {page_url}: {e}")
                break

        # Sort by clicks descending
        keywords.sort(key=lambda k: k.clicks, reverse=True)

        if progress_callback:
            progress_callback(
                len(keywords), len(keywords),
                f"{len(keywords)} anahtar kelime bulundu."
            )

        logger.info(f"Fetched {len(keywords)} keywords for {page_url}")
        return keywords

    def fetch_all_keywords(
        self,
        pages: dict[str, Page],
        progress_callback=None,
    ) -> dict[str, Page]:
        """
        Fetch keywords for all pages in the dictionary.

        Args:
            pages: Dict of URL -> Page.
            progress_callback: Optional callback(current, total, message).

        Returns:
            Updated dict with keyword data populated.
        """
        total = len(pages)
        for idx, (url, page) in enumerate(pages.items()):
            if progress_callback:
                progress_callback(
                    idx + 1, total,
                    f"[{idx + 1}/{total}] Anahtar kelimeler: {page.short_url}"
                )

            page.gsc_keywords = self.fetch_keywords_for_page(url)
            time.sleep(GSC_API_DELAY)

        return pages
