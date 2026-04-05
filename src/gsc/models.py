"""
Data models for the SEO Planner application.
"""
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class KeywordData:
    """Represents a single keyword's GSC metrics for a page."""
    query: str
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    position: float = 0.0

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "clicks": self.clicks,
            "impressions": self.impressions,
            "ctr": self.ctr,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KeywordData":
        return cls(
            query=data["query"],
            clicks=data.get("clicks", 0),
            impressions=data.get("impressions", 0),
            ctr=data.get("ctr", 0.0),
            position=data.get("position", 0.0),
        )


@dataclass
class LinkEdge:
    """Represents a link between two pages."""
    source_url: str
    target_url: str
    anchor_text: str = ""
    is_internal: bool = True
    shared_keywords: list[str] = field(default_factory=list)
    is_skeleton: bool = False

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "target_url": self.target_url,
            "anchor_text": self.anchor_text,
            "is_internal": self.is_internal,
            "shared_keywords": self.shared_keywords,
            "is_skeleton": self.is_skeleton,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LinkEdge":
        return cls(
            source_url=data["source_url"],
            target_url=data["target_url"],
            anchor_text=data.get("anchor_text", ""),
            is_internal=data.get("is_internal", True),
            shared_keywords=data.get("shared_keywords", []),
            is_skeleton=data.get("is_skeleton", False),
        )


@dataclass
class Page:
    """Represents a single page with crawl data and GSC metrics."""
    url: str
    title: str = ""
    page_type: str = "other"  # homepage, category, product, blog, other
    status_code: int = 200
    internal_links_out: list[str] = field(default_factory=list)
    internal_links_in: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    anchor_texts_out: dict[str, str] = field(default_factory=dict)  # url -> anchor
    gsc_keywords: list[KeywordData] = field(default_factory=list)
    total_clicks: int = 0
    total_impressions: int = 0
    avg_position: float = 0.0
    avg_ctr: float = 0.0
    crawled: bool = False
    meta_description: str = ""

    @property
    def in_degree(self) -> int:
        return len(self.internal_links_in)

    @property
    def out_degree(self) -> int:
        return len(self.internal_links_out)

    @property
    def short_url(self) -> str:
        """Return short display URL (path only)."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        path = parsed.path.rstrip("/")
        return path if path else "/"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "page_type": self.page_type,
            "status_code": self.status_code,
            "internal_links_out": self.internal_links_out,
            "internal_links_in": self.internal_links_in,
            "external_links": self.external_links,
            "anchor_texts_out": self.anchor_texts_out,
            "gsc_keywords": [kw.to_dict() for kw in self.gsc_keywords],
            "total_clicks": self.total_clicks,
            "total_impressions": self.total_impressions,
            "avg_position": self.avg_position,
            "avg_ctr": self.avg_ctr,
            "crawled": self.crawled,
            "meta_description": self.meta_description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Page":
        keywords = [KeywordData.from_dict(kw) for kw in data.get("gsc_keywords", [])]
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            page_type=data.get("page_type", "other"),
            status_code=data.get("status_code", 200),
            internal_links_out=data.get("internal_links_out", []),
            internal_links_in=data.get("internal_links_in", []),
            external_links=data.get("external_links", []),
            anchor_texts_out=data.get("anchor_texts_out", {}),
            gsc_keywords=keywords,
            total_clicks=data.get("total_clicks", 0),
            total_impressions=data.get("total_impressions", 0),
            avg_position=data.get("avg_position", 0.0),
            avg_ctr=data.get("avg_ctr", 0.0),
            crawled=data.get("crawled", False),
            meta_description=data.get("meta_description", ""),
        )


@dataclass
class SiteData:
    """Holds the entire site's crawl and GSC data."""
    site_url: str
    pages: dict[str, Page] = field(default_factory=dict)
    edges: list[LinkEdge] = field(default_factory=list)
    crawl_timestamp: str = ""
    gsc_timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "site_url": self.site_url,
            "pages": {url: page.to_dict() for url, page in self.pages.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "crawl_timestamp": self.crawl_timestamp,
            "gsc_timestamp": self.gsc_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SiteData":
        pages = {url: Page.from_dict(p) for url, p in data.get("pages", {}).items()}
        edges = [LinkEdge.from_dict(e) for e in data.get("edges", [])]
        return cls(
            site_url=data["site_url"],
            pages=pages,
            edges=edges,
            crawl_timestamp=data.get("crawl_timestamp", ""),
            gsc_timestamp=data.get("gsc_timestamp", ""),
        )

    def save_to_file(self, filepath: str) -> None:
        """Save site data to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "SiteData":
        """Load site data from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
