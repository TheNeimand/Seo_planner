"""
Main application window for SEO Planner.
Orchestrates the graph view, sidebar, toolbar, and data operations.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QFileDialog, QApplication,
    QMessageBox, QFrame, QScrollArea, QTextBrowser,
)

from src.config import (
    COLORS, DATA_DIR,
)
from src.gsc.auth import get_gsc_service, verify_site_access
from src.gsc.client import GSCClient
from src.gsc.models import Page, SiteData, LinkEdge
from src.crawler.spider import SiteSpider
from src.analysis.link_graph import LinkGraph
from src.analysis.keyword_mapper import KeywordMapper
from src.ui.components.graph_view import GraphView
from src.ui.components.sidebar import Sidebar
from src.ui.components.toolbar import Toolbar
from src.ui.components.dialogs import ProgressDialog, ErrorDialog, SettingsDialog, load_settings, FilterDialog
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ─── Worker threads ───────────────────────────────────────────────────────────

class CrawlWorker(QObject):
    """Worker thread for site crawling."""

    progress = Signal(int, int, str)
    finished = Signal(dict, list)  # pages, edges
    error = Signal(str)

    def __init__(self, site_url: str, settings: dict | None = None):
        super().__init__()
        settings = settings or {}
        self.spider = SiteSpider(
            site_url,
            num_workers=settings.get("crawl_workers", 5),
            delay=settings.get("crawl_delay", 0.3),
            max_depth=settings.get("crawl_max_depth", 5),
            max_pages=settings.get("crawl_max_pages", 500),
        )

    @Slot()
    def run(self):
        try:
            pages, edges = self.spider.crawl(
                progress_callback=self._on_progress
            )
            self.finished.emit(
                {url: p for url, p in pages.items()},
                edges,
            )
        except Exception as e:
            logger.error(f"Crawl error: {e}")
            self.error.emit(str(e))

    def _on_progress(self, current, total, message):
        self.progress.emit(current, total, message)

    def stop(self):
        self.spider.stop()


class MissingPagesWorker(QObject):
    """Worker thread for crawling specific missing pages."""

    progress = Signal(int, int, str)
    finished = Signal(dict, list)  # pages, edges
    error = Signal(str)

    def __init__(self, urls: list[str], site_url: str, settings: dict | None = None):
        super().__init__()
        self.urls = urls
        settings = settings or {}
        self.spider = SiteSpider(
            site_url,
            num_workers=settings.get("crawl_workers", 5),
            delay=settings.get("crawl_delay", 0.3),
        )

    @Slot()
    def run(self):
        try:
            pages, edges = self.spider.crawl_urls(
                self.urls,
                progress_callback=self._on_progress
            )
            self.finished.emit(
                {url: p for url, p in pages.items()},
                edges,
            )
        except Exception as e:
            logger.error(f"Missing pages crawl error: {e}")
            self.error.emit(str(e))

    def stop(self):
        self.spider.stop()

    def _on_progress(self, current: int, total: int, message: str):
        self.progress.emit(current, total, message)


class GSCWorker(QObject):
    """Worker thread for GSC API calls."""

    progress = Signal(int, int, str)
    pages_fetched = Signal(dict)  # pages dict
    keywords_fetched = Signal(str, list)  # url, keywords
    error = Signal(str)

    def __init__(self, gsc_client: GSCClient, mode: str = "pages", page_url: str = ""):
        super().__init__()
        self.client = gsc_client
        self.mode = mode
        self.page_url = page_url

    @Slot()
    def run(self):
        try:
            if self.mode == "pages":
                pages = self.client.fetch_all_pages(
                    progress_callback=self._on_progress
                )
                self.pages_fetched.emit(
                    {url: p for url, p in pages.items()}
                )
            elif self.mode == "keywords":
                keywords = self.client.fetch_keywords_for_page(
                    self.page_url,
                    progress_callback=self._on_progress,
                )
                self.keywords_fetched.emit(self.page_url, keywords)
        except Exception as e:
            logger.error(f"GSC error: {e}")
            self.error.emit(str(e))

    def _on_progress(self, current, total, message):
        self.progress.emit(current, total, message)


# ─── Welcome Screen ────────────────────────────────────────────────────────────

class WelcomeScreen(QWidget):
    """
    Screen shown when no sites are configured.
    Provides instructions on how to add a site.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {COLORS['bg_primary']};")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Wrap in a ScrollArea to support smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background: {COLORS['bg_primary']};")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.setContentsMargins(40, 40, 40, 40)

        container = QFrame()
        container.setFixedWidth(700)
        container.setStyleSheet(f"background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 20px;")
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(15)

        title = QLabel("SEO Planner'a Hoş Geldiniz! 🚀")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(title)

        # Main explanation and step-by-step guide
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setFrameShape(QFrame.Shape.NoFrame)
        browser.setStyleSheet(f"background: transparent; color: {COLORS['text_secondary']}; font-size: 14px;")
        
        # HTML content for the guide
        html_content = f"""
        <style>
            h2 {{ color: #ffffff; margin-top: 20px; }}
            ul {{ margin-left: 15px; margin-bottom: 10px; }}
            li {{ margin-bottom: 8px; color: {COLORS['text_secondary']}; }}
            .step {{ font-weight: bold; color: {COLORS['accent_blue']}; }}
            .warning {{ color: {COLORS['accent_orange']}; font-weight: bold; background: rgba(255, 165, 0, 0.1); padding: 10px; border-radius: 6px; }}
            .code {{ font-family: monospace; background: #2D333B; padding: 2px 4px; border-radius: 4px; }}
        </style>
        <p>Analize başlamak için yeni bir proje eklemeniz ve Google Search Console'a ait <b>Hizmet Hesabı (JSON)</b> dosyasını tanıtmanız gerekmektedir.</p>
        
        <h2>🛠 Hizmet Hesabı (JSON) Nasıl Alınır?</h2>
        <ul>
            <li><span class="step">Adım 1:</span> <a href="https://console.cloud.google.com/">Google Cloud Console</a>'da yeni bir proje oluşturun veya mevcut projenizi seçin.</li>
            <li><span class="step">Adım 2:</span><b>API & Hizmetler > Kitaplık</b> (Library) bölümüne gidin ve <b>Google Search Console API</b>'yi bulup etkinleştirin.</li>
            <li><span class="step">Adım 3:</span> <b>API & Hizmetler > Kimlik Bilgileri</b> (Credentials) sekmesine gelerek <b>Kimlik Bilgisi Oluştur > Hizmet Hesabı</b> (Service Account) deyin.</li>
            <li><span class="step">Adım 4:</span> Hesabı oluşturduktan sonra hesaba tıklayın ve <b>Anahtarlar</b> (Keys) sekmesine gidin.</li>
            <li><span class="step">Adım 5:</span> <b>Anahtar Ekle > Yeni anahtar oluştur</b> diyerek <b>JSON</b> formatını seçin ve indirin.</li>
        </ul>
        <div class="warning">
            ⚠️ <b>KRİTİK ADIM:</b> İndirdiğiniz JSON dosyasındaki <code>client_email</code> adresini kopyalayın. Google Search Console'a (Ayarlar > Kullanıcılar) gidin ve bu adresi mülkünüze <b>Tam Yetki</b> ile kullanıcı olarak ekleyin.
        </div>

        <h2>🚀 Projeyi Nasıl Tanımlarım?</h2>
        <ul>
            <li>Sağ üstteki <b>⚙ Ayarlar</b> simgesine tıklayın.</li>
            <li><b>Siteler</b> sekmesine geçin.</li>
            <li><b>+ Site Ekle</b> butonuna basarak yukarıdaki bilgileri doldurun ve JSON dosyasını seçin.</li>
            <li>Listeden eklediğiniz siteyi seçin ve <b>Aktif Yap</b> butonuna basın.</li>
        </ul>
        """
        browser.setHtml(html_content)
        # Increase minimum height to show most content without scrolling inside browser
        browser.setMinimumHeight(450)
        c_layout.addWidget(browser)

        content_layout.addWidget(container)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """
    The main application window.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SEO Planner — Site Haritası ve Anahtar Kelime Analizi")
        self.setMinimumSize(1280, 800)
        self.resize(1600, 900)

        # Settings
        self.app_settings = load_settings()

        # Data placeholders (initialized in _load_site_config)
        self.site_data = None
        self.gsc_service = None
        self.gsc_client = None
        
        self.link_graph = LinkGraph()
        self.keyword_mapper = KeywordMapper()
        self.current_layout = "smart_tree"
        self.hidden_categories = set()
        self.hidden_urls = set()

        # Worker threads
        self._crawl_thread = None
        self._gsc_thread = None

        # UI
        self._setup_ui()
        self._connect_signals()
        self._load_stylesheet()

        # Status bar
        self.stats_label = QLabel("")
        self.statusBar().addPermanentWidget(self.stats_label)
        
        # Site config loading
        self._load_site_config()

    def _get_active_site(self):
        active_id = self.app_settings.get("active_site_id")
        for s in self.app_settings.get("sites", []):
            if s["id"] == active_id:
                return s
        return None

    def _load_site_config(self):
        """Loads or reloads the configuration based on the active site."""
        site = self._get_active_site()
        self.toolbar.refresh_sites(self.app_settings.get("sites", []), self.app_settings.get("active_site_id"))
        
        if not site:
            self.welcome_screen.show()
            self.splitter.hide()
            self.toolbar.crawl_btn.setEnabled(False)
            self.toolbar.gsc_btn.setEnabled(False)
            self.statusBar().showMessage("Lütfen bir site ekleyerek başlayın.")
            self.site_data = SiteData(site_url="")
            return

        self.welcome_screen.hide()
        self.splitter.show()
        self.toolbar.crawl_btn.setEnabled(True)
        self.toolbar.gsc_btn.setEnabled(True)

        # Set specific site data
        self.site_data = SiteData(site_url=site["url"])
        self._init_gsc(site["creds_path"], site["gsc_property"])
        
        # Load cache
        cache_path = DATA_DIR / f"site_cache_{site['id']}.json"
        self._try_load_cache(cache_path)
        
        self.statusBar().showMessage(f"Aktif Site: {site['name']} ({site['url']})")

    def _save_cache(self):
        """Save site data to cache."""
        site = self._get_active_site()
        if not site: return
        
        try:
            cache_path = DATA_DIR / f"site_cache_{site['id']}.json"
            self.site_data.save_to_file(str(cache_path))
            logger.info(f"Cache saved to {cache_path}")
        except Exception as e:
            logger.error(f"Cache save failed: {e}")

    def _setup_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        self.toolbar = Toolbar()
        main_layout.addWidget(self.toolbar)

        # Content area
        content_stack = QWidget()
        content_stack_layout = QVBoxLayout(content_stack)
        content_stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # Welcome Screen
        self.welcome_screen = WelcomeScreen()
        content_stack_layout.addWidget(self.welcome_screen)
        self.welcome_screen.hide()

        # Graph + Sidebar Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Graph View
        self.graph_view = GraphView()
        self.splitter.addWidget(self.graph_view)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.hide()
        self.splitter.addWidget(self.sidebar)

        # Splitter proportions
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)

        content_stack_layout.addWidget(self.splitter)
        main_layout.addWidget(content_stack)

    def _connect_signals(self):
        """Connect signals between components."""
        # Toolbar
        self.toolbar.crawl_requested.connect(self.start_crawl)
        self.toolbar.gsc_fetch_requested.connect(self.start_gsc_fetch)
        self.toolbar.layout_changed.connect(self.change_layout)
        self.toolbar.search_submitted.connect(self.search_node)
        self.toolbar.zoom_in_requested.connect(self.graph_view.zoom_in)
        self.toolbar.zoom_out_requested.connect(self.graph_view.zoom_out)
        self.toolbar.zoom_fit_requested.connect(self.graph_view.zoom_fit)
        self.toolbar.export_requested.connect(self.export_data)
        self.toolbar.settings_requested.connect(self.open_settings)
        self.toolbar.clear_requested.connect(self.clear_all_data)
        self.toolbar.crawl_missing_requested.connect(self.start_crawl_missing)
        self.toolbar.filter_requested.connect(self.open_filter_dialog)
        self.toolbar.site_changed.connect(self._on_site_changed)

        # Graph View
        self.graph_view.node_clicked.connect(self.on_node_clicked)

        # Sidebar
        self.sidebar.keyword_fetch_requested.connect(
            self.fetch_keywords_for_page
        )
        self.sidebar.page_link_clicked.connect(self._on_sidebar_link_clicked)
        self.sidebar.hide_page_requested.connect(self.hide_specific_page)

    def _load_stylesheet(self):
        """Load the QSS stylesheet."""
        qss_path = Path(__file__).parent / "styles" / "theme.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            logger.info("Stylesheet loaded.")
        else:
            logger.warning(f"Stylesheet not found: {qss_path}")

    def _init_gsc(self, creds_path: str, gsc_property: str):
        """Initialize the GSC service."""
        try:
            creds_file = Path(creds_path)
            if creds_file.exists():
                self.gsc_service = get_gsc_service(creds_file)
                self.gsc_client = GSCClient(self.gsc_service, gsc_property)
                self.statusBar().showMessage(
                    "✅ GSC bağlantısı başarılı!"
                )
            else:
                self.statusBar().showMessage(
                    "⚠️ GSC kimlik bilgisi dosyası bulunamadı."
                )
        except Exception as e:
            logger.error(f"GSC init failed: {e}")
            self.statusBar().showMessage(f"❌ GSC bağlantı hatası: {e}")

    def _try_load_cache(self, cache_path: Path):
        """Try to load cached site data."""
        # Clear current graph first
        self.graph_view.scene_.clear()
        self.graph_view.nodes.clear()
        self.sidebar.hide()
        
        if cache_path.exists():
            try:
                self.site_data = SiteData.load_from_file(str(cache_path))
                self._rebuild_graph()
                self.statusBar().showMessage(
                    f"📦 Önbellekten yüklendi: {len(self.site_data.pages)} sayfa"
                )
            except Exception as e:
                logger.error(f"Cache load failed: {e}")
        else:
            self.site_data = SiteData(site_url=self._get_active_site()["url"])
            self.statusBar().showMessage("Yeni proje: Taramaya hazır.")

    def _save_cache(self):
        """Save site data to cache."""
        try:
            self.site_data.save_to_file(str(CACHE_FILE))
            logger.info("Cache saved.")
        except Exception as e:
            logger.error(f"Cache save failed: {e}")

    # ── Crawl Operations ──────────────────────────────────────────────────

    def start_crawl(self):
        """Start crawling the site."""
        self.progress_dialog = ProgressDialog("🔍 Site Taranıyor", self)
        self.progress_dialog.show()

        self.toolbar.set_loading(True, "Taranıyor...")

        worker = CrawlWorker(self.site_data.site_url, settings=self.app_settings)
        thread = QThread()
        worker.moveToThread(thread)

        worker.progress.connect(self.progress_dialog.update_progress)
        worker.finished.connect(self._on_crawl_finished)
        worker.error.connect(self._on_crawl_error)
        thread.started.connect(worker.run)

        self.progress_dialog.cancel_requested.connect(worker.stop)

        self._crawl_thread = thread
        self._crawl_worker = worker
        thread.start()

    def _on_crawl_finished(self, pages: dict, edges: list):
        """Handle crawl completion."""
        self.site_data.pages = {
            url: Page.from_dict(p.to_dict()) if isinstance(p, Page) else p
            for url, p in pages.items()
        }
        self.site_data.edges = edges
        self.site_data.crawl_timestamp = datetime.now().isoformat()

        self._rebuild_graph()
        self._save_cache()

        self.toolbar.set_loading(False)
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.finish(
                f"✅ Tarama tamamlandı! {len(pages)} sayfa bulundu."
            )
            QTimer.singleShot(1500, self.progress_dialog.close)

        self._cleanup_thread("crawl")

        self.statusBar().showMessage(
            f"✅ {len(pages)} sayfa tarandı, {len(edges)} bağlantı bulundu."
        )
        self._update_stats()

    def _on_crawl_error(self, message: str):
        """Handle crawl error."""
        self._cleanup_thread("crawl")
        ErrorDialog.show(self, "Tarama Hatası", message)

    def start_crawl_missing(self):
        """Find non-crawled pages (detected via GSC) and crawl them."""
        # Find pages that haven't been crawled yet
        missing_urls = [
            url for url, page in self.site_data.pages.items()
            if getattr(page, "crawled", False) is False
        ]

        if not missing_urls:
            QMessageBox.information(
                self,
                "Eksik Sayfa Yok",
                "Su an icin taranmamis veya GSC'de yeni bulunmus bir sayfa yok. "
                "Tum sayfalar zaten taranmis durumda."
            )
            return

        reply = QMessageBox.question(
            self,
            "Eksik Sayfalari Tara",
            f"GSC verileri iskenirken fark edilmis ama icerigi taranmamis "
            f"{len(missing_urls)} adet sayfa bulundu.\n\n"
            f"Bu sayfalarin baglantilarini da ogrenmek icin simdi taransin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.progress_dialog = ProgressDialog("🔍 Eksik Sayfalar Taraniyor", self)
        self.progress_dialog.show()
        self.toolbar.set_loading(True, "Sayfalar İnceleniyor...")

        worker = MissingPagesWorker(missing_urls, self.site_data.site_url, settings=self.app_settings)
        thread = QThread()
        worker.moveToThread(thread)

        worker.progress.connect(self.progress_dialog.update_progress)
        worker.finished.connect(self._on_crawl_missing_finished)
        worker.error.connect(self._on_crawl_error)
        thread.started.connect(worker.run)

        self.progress_dialog.cancel_requested.connect(worker.stop)

        self._crawl_thread = thread
        self._crawl_worker = worker
        thread.start()

    def _on_crawl_missing_finished(self, new_pages: dict, new_edges: list):
        """Merge newly crawled missing pages into the existing graph."""
        for url, new_page in new_pages.items():
            # If we already had this page just via GSC, preserve GSC stats
            if url in self.site_data.pages:
                existing = self.site_data.pages[url]
                # Update but keep Google Search Console data (clicks, etc.)
                new_page.gsc_keywords = existing.gsc_keywords
                new_page.total_clicks = existing.total_clicks
                new_page.total_impressions = existing.total_impressions
                new_page.avg_ctr = existing.avg_ctr
                new_page.avg_position = existing.avg_position
            
            self.site_data.pages[url] = new_page

        self.site_data.edges.extend(new_edges)
        self.site_data.crawl_timestamp = datetime.now().isoformat()

        self._rebuild_graph()
        self._save_cache()

        self._cleanup_thread("crawl")
        self.progress_dialog.finish(f"✅ {len(new_pages)} yeni sayfa eklendi!")
        QTimer.singleShot(1500, self.progress_dialog.close)


    # ── GSC Operations ────────────────────────────────────────────────────

    def start_gsc_fetch(self):
        """Start fetching GSC data."""
        if not self.gsc_client:
            ErrorDialog.show(
                self, "GSC Hatası",
                "GSC bağlantısı kurulamadı. Kimlik bilgisi dosyasını kontrol edin."
            )
            return

        if not self.site_data.pages:
            ErrorDialog.show(
                self, "Veri Yok",
                "Önce siteyi taramanız gerekiyor. '🔍 Siteyi Tara' butonuna tıklayın."
            )
            return

        self.progress_dialog = ProgressDialog("📊 GSC Verileri Çekiliyor", self)
        self.progress_dialog.show()

        worker = GSCWorker(self.gsc_client, mode="pages")
        thread = QThread()
        worker.moveToThread(thread)

        worker.progress.connect(self.progress_dialog.update_progress)
        worker.pages_fetched.connect(self._on_gsc_pages_fetched)
        worker.error.connect(self._on_gsc_error)
        thread.started.connect(worker.run)

        self._gsc_thread = thread
        self._gsc_worker = worker
        thread.start()

    def _on_gsc_pages_fetched(self, gsc_pages: dict):
        """Merge GSC page data with crawl data."""
        merged_count = 0
        for url, gsc_page in gsc_pages.items():
            if url in self.site_data.pages:
                page = self.site_data.pages[url]
                page.total_clicks = gsc_page.total_clicks
                page.total_impressions = gsc_page.total_impressions
                page.avg_ctr = gsc_page.avg_ctr
                page.avg_position = gsc_page.avg_position
                merged_count += 1
            else:
                # Page found in GSC but not crawled
                self.site_data.pages[url] = gsc_page

        self.site_data.gsc_timestamp = datetime.now().isoformat()
        self._rebuild_graph()
        self._save_cache()

        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.finish(
                f"✅ {merged_count} sayfa ile GSC verileri eşleştirildi."
            )
            QTimer.singleShot(1500, self.progress_dialog.close)

        self._cleanup_thread("gsc")
        self.statusBar().showMessage(
            f"✅ GSC verileri güncellendi: {merged_count} sayfa eşleştirildi."
        )

    def _on_gsc_error(self, error_msg: str):
        """Handle GSC error."""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
        ErrorDialog.show(self, "GSC Hatası", f"GSC verileri çekilirken hata oluştu:\n{error_msg}")
        self._cleanup_thread("gsc")

    def fetch_keywords_for_page(self, url: str):
        """Fetch keywords for a single page."""
        if not self.gsc_client:
            ErrorDialog.show(
                self, "GSC Hatası", "GSC bağlantısı kurulamadı."
            )
            return

        self.progress_dialog = ProgressDialog("🔑 Anahtar Kelimeler Çekiliyor", self)
        self.progress_dialog.show()

        worker = GSCWorker(self.gsc_client, mode="keywords", page_url=url)
        thread = QThread()
        worker.moveToThread(thread)

        worker.progress.connect(self.progress_dialog.update_progress)
        worker.keywords_fetched.connect(self._on_keywords_fetched)
        worker.error.connect(self._on_gsc_error)
        thread.started.connect(worker.run)

        self._gsc_thread = thread
        self._gsc_worker = worker
        thread.start()

    def _on_keywords_fetched(self, url: str, keywords: list):
        """Handle keywords fetched for a page."""
        if url in self.site_data.pages:
            self.site_data.pages[url].gsc_keywords = keywords
            self.sidebar.show_page(self.site_data.pages[url])
            self._save_cache()

        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.finish(
                f"✅ {len(keywords)} anahtar kelime bulundu."
            )
            QTimer.singleShot(1000, self.progress_dialog.close)

        self._cleanup_thread("gsc")

    # ── Graph Operations ──────────────────────────────────────────────────

    def _rebuild_graph(self):
        """Rebuild and display the graph."""
        if not self.site_data.pages:
            return

        # Filter out hidden categories and hidden urls
        filtered_pages = {
            url: page for url, page in self.site_data.pages.items()
            if self.get_url_category(url) not in self.hidden_categories
            and url not in self.hidden_urls
        }

        # Filter edges to only include nodes that are present in filtered_pages
        filtered_edges = [
            edge for edge in self.site_data.edges
            if edge.source_url in filtered_pages and edge.target_url in filtered_pages
        ]

        self.link_graph.build_from_data(
            filtered_pages,
            filtered_edges,
        )
        positions = self.link_graph.compute_layout(self.current_layout)
        self.graph_view.build_graph(
            filtered_pages,
            positions,
            filtered_edges,
        )

        self._update_stats()
        
        # Update missing pages button visibility based on missing amount
        missing_count = sum(1 for p in self.site_data.pages.values() if getattr(p, "crawled", False) is False)
        self.toolbar.show_crawl_missing_button(missing_count)

    def get_url_category(self, url: str) -> str:
        """Extract a category string from a URL based on its path."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return "[Ana Dizin]"
            
        segments = path.split("/")
        first = segments[0]
        
        # Determine if it's a file in the root
        if "." in first and first.endswith((".php", ".html", ".htm", ".aspx")):
            return f"[{first.split('.')[-1].upper()} Dosyaları]"
            
        return f"/{first}"

    def open_filter_dialog(self):
        """Open the filter dialog to hide/show categories."""
        if not self.site_data.pages:
            ErrorDialog.show(
                self, "Veri Yok",
                "Filtrelenecek veri yok. Önce siteyi taramanız gerekiyor."
            )
            return

        # Compute category counts
        category_counts = {}
        for url in self.site_data.pages.keys():
            cat = self.get_url_category(url)
            category_counts[cat] = category_counts.get(cat, 0) + 1

        dialog = FilterDialog(category_counts, self.hidden_categories, self)
        dialog.hidden_categories_changed.connect(self._on_hidden_categories_changed)
        dialog.exec()

    def _on_hidden_categories_changed(self, new_hidden: set):
        """Handle hidden categories change."""
        self.hidden_categories = new_hidden
        self._rebuild_graph()

    def hide_specific_page(self, url: str):
        """Hide a specific page from the graph."""
        self.hidden_urls.add(url)
        self.sidebar.hide()
        self._rebuild_graph()
        self.statusBar().showMessage(f"👁 Sayfa gizlendi: {url}")

    def change_layout(self, layout_type: str):
        """Change the graph layout algorithm."""
        self.current_layout = layout_type
        self._rebuild_graph()

    def on_node_clicked(self, url: str):
        """Handle node click — show page details in sidebar."""
        if url in self.site_data.pages:
            page = self.site_data.pages[url]
            self.sidebar.show_page(page)
            self.graph_view.highlight_node(url)
            self.statusBar().showMessage(
                f"📄 {page.title or page.short_url} — "
                f"Tıklama: {page.total_clicks} | Gösterim: {page.total_impressions}"
            )

    def search_node(self, query: str):
        """Search for a node in the graph."""
        found = self.graph_view.search_node(query)
        if found:
            self.on_node_clicked(found)
        else:
            self.statusBar().showMessage(f"❌ '{query}' ile eşleşen sayfa bulunamadı.")

    def _on_sidebar_link_clicked(self, path: str):
        """Handle link click from sidebar — navigate to that node."""
        # Find the URL that matches this path
        for url in self.site_data.pages:
            from urllib.parse import urlparse
            if urlparse(url).path.rstrip("/") == path.rstrip("/") or path.rstrip("/") == "":
                self.on_node_clicked(url)
                return

    # ── Export ─────────────────────────────────────────────────────────────

    def export_data(self):
        """Export site data to JSON."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Veriyi Dışa Aktar", str(DATA_DIR / "export.json"),
            "JSON dosyası (*.json)"
        )
        if filepath:
            try:
                self.site_data.save_to_file(filepath)
                ErrorDialog.show_info(
                    self, "Dışa Aktarma Başarılı",
                    f"Veriler başarıyla kaydedildi:\n{filepath}"
                )
            except Exception as e:
                ErrorDialog.show(
                    self, "Dışa Aktarma Hatası", str(e)
                )

    def open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, new_settings: dict):
        """Handle settings change."""
        self.app_settings = new_settings
        self._load_site_config()
        self.statusBar().showMessage("✅ Ayarlar ve Site listesi güncellendi.")

    def _on_site_changed(self, site_id: str):
        """Handle site change from toolbar."""
        if self.app_settings.get("active_site_id") == site_id:
            return
            
        # Save current cache before switching
        self._save_cache()
        
        self.app_settings["active_site_id"] = site_id
        from src.ui.components.dialogs import save_settings
        save_settings(self.app_settings)
        
        self._load_site_config()

    def clear_all_data(self):
        """Clear all cached data and reset the graph after user confirmation."""
        reply = QMessageBox.warning(
            self,
            "Verileri Temizle",
            "Tum tarama verileri, GSC verileri ve onbellek silinecek.\n\n"
            "Bu islem geri alinamaz. Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Clear data
        site = self._get_active_site()
        self.site_data = SiteData(site_url=site["url"] if site else "")
        self.link_graph = LinkGraph()

        # Clear graph view
        self.graph_view.scene_.clear()
        self.graph_view.nodes.clear()
        self.graph_view.edge_items.clear()

        # Hide sidebar
        self.sidebar.hide()

        # Delete cache file
        if site:
            cache_path = DATA_DIR / f"site_cache_{site['id']}.json"
            if cache_path.exists():
                try:
                    cache_path.unlink()
                except Exception as e:
                    logger.error(f"Cache delete failed: {e}")

        self.stats_label.setText("")
        self.statusBar().showMessage(
            "Tum veriler temizlendi. Yeniden taramak icin 'Siteyi Tara' butonuna tiklayin."
        )
        logger.info("All data cleared by user.")

    # ── Helpers ────────────────────────────────────────────────────────────

    def _update_stats(self):
        """Update the status bar statistics."""
        pages = len(self.site_data.pages)
        edges = len(self.site_data.edges)
        total_clicks = sum(p.total_clicks for p in self.site_data.pages.values())
        total_impressions = sum(p.total_impressions for p in self.site_data.pages.values())
        self.stats_label.setText(
            f"📄 {pages} Sayfa  |  🔗 {edges} Bağlantı  |  "
            f"👆 {total_clicks:,} Tıklama  |  👁 {total_impressions:,} Gösterim"
        )

    def _cleanup_thread(self, thread_type: str):
        """Clean up finished worker thread."""
        if thread_type == "crawl" and self._crawl_thread:
            self._crawl_thread.quit()
            self._crawl_thread.wait()
            self._crawl_thread = None
        elif thread_type == "gsc" and self._gsc_thread:
            self._gsc_thread.quit()
            self._gsc_thread.wait()
            self._gsc_thread = None

    def closeEvent(self, event):
        """Handle window close."""
        self._save_cache()
        # Clean up threads
        if self._crawl_thread:
            if hasattr(self, '_crawl_worker'):
                self._crawl_worker.stop()
            self._crawl_thread.quit()
            self._crawl_thread.wait(3000)
        if self._gsc_thread:
            self._gsc_thread.quit()
            self._gsc_thread.wait(3000)
        super().closeEvent(event)
