"""
Website spider/crawler for discovering internal links.
Uses BFS with concurrent workers for faster crawling.
"""
import logging
import time
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

from src.config import (
    CRAWL_DELAY,
    CRAWL_MAX_DEPTH,
    CRAWL_MAX_PAGES,
    CRAWL_TIMEOUT,
    CRAWL_USER_AGENT,
    CRAWL_WORKERS,
)
from src.crawler.parser import is_crawlable_url, normalize_url, parse_page
from src.gsc.models import LinkEdge, Page

logger = logging.getLogger(__name__)


class SiteSpider:
    """
    BFS-based web crawler with concurrent workers for mapping
    internal link structure.
    """

    def __init__(
        self,
        site_url: str,
        max_depth: int = CRAWL_MAX_DEPTH,
        max_pages: int = CRAWL_MAX_PAGES,
        delay: float = CRAWL_DELAY,
        num_workers: int = CRAWL_WORKERS,
    ):
        self.site_url = site_url.rstrip("/")
        self.domain = urlparse(self.site_url).netloc.replace("www.", "")
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay = delay
        self.num_workers = max(1, num_workers)

        # State (thread-safe)
        self._lock = threading.Lock()
        self.pages: dict[str, Page] = {}
        self.edges: list[LinkEdge] = []
        self.visited: set[str] = set()
        self._stop_requested = False

    def _make_session(self) -> requests.Session:
        """Create a new session for each worker thread."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": CRAWL_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        })
        return session

    def stop(self):
        """Request the crawler to stop."""
        self._stop_requested = True

    def classify_page_type(self, url: str, title: str = "") -> str:
        """Classify a page type based on URL patterns."""
        path = urlparse(url).path.lower().rstrip("/")

        if path == "" or path == "/":
            return "homepage"

        category_patterns = [
            "/kategori", "/category", "/urunler", "/products",
            "/koleksiyon", "/collection",
        ]
        product_patterns = [
            "/urun/", "/product/", "/shop/",
        ]
        blog_patterns = [
            "/blog", "/haber", "/makale", "/article",
            "/post", "/news",
        ]

        for pat in category_patterns:
            if pat in path:
                return "category"
        for pat in product_patterns:
            if pat in path:
                return "product"
        for pat in blog_patterns:
            if pat in path:
                return "blog"

        segments = [s for s in path.split("/") if s]
        if len(segments) >= 3:
            return "product"
        elif len(segments) == 1:
            return "category"

        return "other"

    def _fetch_one(self, url: str, depth: int, session: requests.Session):
        """
        Fetch and parse a single URL. Returns discovered links.
        Thread-safe: writes to self.pages/edges under lock.
        """
        if self._stop_requested:
            return []

        try:
            response = session.get(
                url, timeout=CRAWL_TIMEOUT, allow_redirects=True,
            )
            status_code = response.status_code

            if status_code != 200:
                logger.warning(f"HTTP {status_code} for {url}")
                with self._lock:
                    self.pages[url] = Page(
                        url=url, status_code=status_code, crawled=True,
                    )
                return []

            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return []

            parsed = parse_page(response.text, url, self.domain)
            page_type = self.classify_page_type(url, parsed["title"])

            internal_link_urls = list(set(
                u for u, _ in parsed["internal_links"]
            ))
            anchor_texts = {}
            for link_url, anchor in parsed["internal_links"]:
                if anchor:
                    anchor_texts[link_url] = anchor

            page = Page(
                url=url,
                title=parsed["title"],
                page_type=page_type,
                status_code=status_code,
                internal_links_out=internal_link_urls,
                external_links=list(set(parsed["external_links"])),
                anchor_texts_out=anchor_texts,
                meta_description=parsed["meta_description"],
                crawled=True,
            )

            new_edges = [
                LinkEdge(
                    source_url=url,
                    target_url=link_url,
                    anchor_text=anchor,
                    is_internal=True,
                )
                for link_url, anchor in parsed["internal_links"]
            ]

            with self._lock:
                self.pages[url] = page
                self.edges.extend(new_edges)

            logger.info(
                f"[{len(self.pages)}/{self.max_pages}] "
                f"Crawled: {url} ({len(parsed['internal_links'])} links)"
            )

            # Return new URLs to add to queue
            return [(link_url, depth + 1) for link_url, _ in parsed["internal_links"]]

        except requests.Timeout:
            logger.warning(f"Timeout for {url}")
            with self._lock:
                self.pages[url] = Page(url=url, status_code=408, crawled=True)
        except requests.RequestException as e:
            logger.error(f"Error crawling {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")

        return []

    def crawl(self, progress_callback=None) -> tuple[dict[str, Page], list[LinkEdge]]:
        """
        Crawl the site using concurrent workers.

        Args:
            progress_callback: Optional callback(current, total, message).

        Returns:
            Tuple of (pages dict, edges list).
        """
        start_url = normalize_url(self.site_url + "/", self.site_url)
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        self.visited = {start_url}
        self._stop_requested = False
        self.pages = {}
        self.edges = []

        if progress_callback:
            progress_callback(0, 0, f"Tarama başlatılıyor ({self.num_workers} spider)...")

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            while (queue or executor._work_queue.qsize() > 0) and not self._stop_requested:
                # Submit a batch of URLs
                futures = {}
                session_pool = [self._make_session() for _ in range(self.num_workers)]

                batch_size = min(len(queue), self.num_workers)
                if batch_size == 0:
                    # No URLs in queue right now, wait a bit for inflight
                    time.sleep(0.1)
                    continue

                for i in range(batch_size):
                    if not queue:
                        break

                    with self._lock:
                        if len(self.pages) >= self.max_pages:
                            break

                    current_url, depth = queue.popleft()
                    if depth > self.max_depth:
                        continue

                    session = session_pool[i % len(session_pool)]
                    future = executor.submit(
                        self._fetch_one, current_url, depth, session
                    )
                    futures[future] = current_url

                # Collect results and add new URLs to queue
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        new_links = future.result()
                        for link_url, link_depth in new_links:
                            if link_url not in self.visited:
                                self.visited.add(link_url)
                                queue.append((link_url, link_depth))
                    except Exception as e:
                        logger.error(f"Worker error for {url}: {e}")

                    if progress_callback:
                        progress_callback(
                            len(self.pages),
                            min(len(self.pages) + len(queue), self.max_pages),
                            f"[{self.num_workers} spider] Taranan: {len(self.pages)} sayfa"
                        )

                with self._lock:
                    if len(self.pages) >= self.max_pages:
                        break

                time.sleep(self.delay)

        # Calculate incoming links
        self._calculate_incoming_links()

        if progress_callback:
            progress_callback(
                len(self.pages), len(self.pages),
                f"Tarama tamamlandı! {len(self.pages)} sayfa bulundu."
            )

        logger.info(
            f"Crawl complete: {len(self.pages)} pages, {len(self.edges)} edges "
            f"(workers: {self.num_workers})"
        )
        return self.pages, self.edges

    def _calculate_incoming_links(self):
        """Calculate incoming links for each page."""
        for page in self.pages.values():
            page.internal_links_in = []

        for edge in self.edges:
            if edge.target_url in self.pages:
                target_page = self.pages[edge.target_url]
                if edge.source_url not in target_page.internal_links_in:
                    target_page.internal_links_in.append(edge.source_url)

    def crawl_urls(
        self,
        urls: list[str],
        progress_callback=None,
    ) -> tuple[dict[str, "Page"], list["LinkEdge"]]:
        """
        Crawl a specific list of URLs (no BFS — just these pages).
        Used for scanning GSC-only pages that the spider missed.

        Args:
            urls: List of URLs to crawl.
            progress_callback: Optional callback(current, total, message).

        Returns:
            Tuple of (pages dict, edges list).
        """
        self._stop_requested = False
        self.pages = {}
        self.edges = []
        total = len(urls)

        if progress_callback:
            progress_callback(0, total, f"Eksik sayfalar taranıyor ({self.num_workers} spider)...")

        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {}
            session_pool = [self._make_session() for _ in range(self.num_workers)]

            for i, url in enumerate(urls):
                if self._stop_requested:
                    break
                session = session_pool[i % len(session_pool)]
                future = executor.submit(self._fetch_one, url, 0, session)
                futures[future] = url

            for future in as_completed(futures):
                url = futures[future]
                try:
                    future.result()  # edges/pages written inside _fetch_one
                except Exception as e:
                    logger.error(f"Worker error for {url}: {e}")

                if progress_callback:
                    progress_callback(
                        len(self.pages), total,
                        f"Eksik sayfalar: {len(self.pages)}/{total}"
                    )

        self._calculate_incoming_links()

        if progress_callback:
            progress_callback(
                len(self.pages), total,
                f"Tamamlandi! {len(self.pages)} eksik sayfa tarandiI."
            )

        logger.info(
            f"URL crawl complete: {len(self.pages)} pages, {len(self.edges)} edges"
        )
        return self.pages, self.edges

