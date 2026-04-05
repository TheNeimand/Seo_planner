"""
Application configuration and constants.
"""
import os
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# ─── GSC API Settings ────────────────────────────────────────────────────────
GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
GSC_DEFAULT_DAYS = 28  # Default date range: last N days
GSC_ROW_LIMIT = 25000  # Max rows per request
GSC_API_DELAY = 0.1  # Seconds between API calls

# ─── Crawler Settings ────────────────────────────────────────────────────────
CRAWL_DELAY = 0.3  # Seconds between requests per worker
CRAWL_MAX_DEPTH = 5  # Maximum crawl depth
CRAWL_TIMEOUT = 10  # Request timeout in seconds
CRAWL_USER_AGENT = "SeoPlanner/1.0 (+https://github.com/seoplanner)"
CRAWL_MAX_PAGES = 500  # Maximum pages to crawl
CRAWL_WORKERS = 5  # Default number of concurrent spiders

# ─── UI Theme Colors ─────────────────────────────────────────────────────────
COLORS = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#1C2128",
    "border": "#30363D",
    "border_light": "#3D444D",
    "accent_blue": "#58A6FF",
    "accent_green": "#3FB950",
    "accent_orange": "#F0883E",
    "accent_red": "#F85149",
    "accent_purple": "#BC8CFF",
    "accent_yellow": "#E3B341",
    "text_primary": "#C9D1D9",
    "text_secondary": "#8B949E",
    "text_muted": "#484F58",
    "hover": "#1F2937",
    "selected": "#1A3A5C",
}

# ─── Graph Node Colors (by page type) ────────────────────────────────────────
NODE_COLORS = {
    "homepage": "#F0883E",
    "category": "#58A6FF",
    "product": "#3FB950",
    "blog": "#BC8CFF",
    "other": "#8B949E",
}

NODE_SIZES = {
    "homepage": 30,
    "category": 22,
    "product": 16,
    "blog": 16,
    "other": 12,
}

# ─── Cache Settings ──────────────────────────────────────────────────────────
CACHE_EXPIRY_HOURS = 24

# ─── User Settings ───────────────────────────────────────────────────────────
SETTINGS_FILE = DATA_DIR / "settings.json"
