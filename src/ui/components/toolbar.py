"""
Toolbar widget with action buttons, search, and layout controls.
"""
import logging
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLineEdit,
    QComboBox, QLabel, QFrame, QSpacerItem,
    QSizePolicy,
)

from src.config import COLORS

logger = logging.getLogger(__name__)

# Emoji-safe font family (Windows has Segoe UI Emoji, others use platform default)
_EMOJI_FONT = "Segoe UI Emoji" if sys.platform == "win32" else ""


class Toolbar(QWidget):
    """Top toolbar with action buttons and controls."""

    crawl_requested = Signal()
    gsc_fetch_requested = Signal()
    layout_changed = Signal(str)
    search_submitted = Signal(str)
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    zoom_fit_requested = Signal()
    export_requested = Signal()
    settings_requested = Signal()
    clear_requested = Signal()
    crawl_missing_requested = Signal()
    filter_requested = Signal()
    site_changed = Signal(str) # site_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border-bottom: 1px solid {COLORS['border']};"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        # ── Logo / Title ──
        logo_label = QLabel("SEO Planner")
        logo_label.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #FFFFFF; "
            "background: transparent;"
        )
        layout.addWidget(logo_label)

        self._add_separator(layout)

        # ── Site Selector ──
        self.site_combo = QComboBox()
        self.site_combo.setFixedWidth(180)
        self.site_combo.setStyleSheet(
            f"QComboBox {{ background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px; color: {COLORS['text_primary']}; font-weight: bold; }}"
        )
        self.site_combo.currentIndexChanged.connect(self._on_site_combo_changed)
        layout.addWidget(self.site_combo)

        self._add_separator(layout)
        self.crawl_btn = self._make_button(
            "Siteyi Tara", "primaryButton"
        )
        self.crawl_btn.clicked.connect(self.crawl_requested.emit)
        layout.addWidget(self.crawl_btn)

        self.gsc_btn = self._make_button(
            "GSC Verisi Cek", "accentButton"
        )
        self.gsc_btn.clicked.connect(self.gsc_fetch_requested.emit)
        layout.addWidget(self.gsc_btn)

        # ── Clear ──
        self.clear_btn = self._make_button("Temizle", "")
        self.clear_btn.setToolTip("Tum verileri sil ve sifirla")
        self.clear_btn.setStyleSheet(
            f"QPushButton {{ color: {COLORS['accent_red']}; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_red']}; color: white; }}"
        )
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        layout.addWidget(self.clear_btn)

        # ── Crawl Missing ──
        self.crawl_missing_btn = self._make_button("Eksik Sayfalari Tara", "")
        self.crawl_missing_btn.setToolTip(
            "GSC'de bulunan ama spider'in taramadigi sayfalari tara"
        )
        self.crawl_missing_btn.setStyleSheet(
            f"QPushButton {{ color: {COLORS['accent_orange']}; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_orange']}; color: white; }}"
        )
        self.crawl_missing_btn.clicked.connect(self.crawl_missing_requested.emit)
        self.crawl_missing_btn.hide()  # By default hidden, shown after GSC data is loaded
        layout.addWidget(self.crawl_missing_btn)

        # ── Filter / Hide ──
        self.filter_btn = self._make_button("Gizle / Filtrele", "")
        self.filter_btn.setToolTip("Görmek istemediğiniz sayfa kategorilerini haritadan gizleyin")
        self.filter_btn.setStyleSheet(
            f"QPushButton {{ color: {COLORS['text_primary']}; font-weight: 600; }}"
            f"QPushButton:hover {{ background: {COLORS['text_secondary']}; color: {COLORS['bg_primary']}; }}"
        )
        self.filter_btn.clicked.connect(self.filter_requested.emit)
        layout.addWidget(self.filter_btn)

        self._add_separator(layout)

        # ── Layout Selector ──
        layout_label = QLabel("Yerlesim:")
        layout_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; background: transparent; font-size: 12px;"
        )
        layout.addWidget(layout_label)

        self.layout_combo = QComboBox()
        self.layout_combo.addItems([
            "Akıllı Ağaç (Önerilen)",
            "Force-Directed (Yumak)",
            "Dairesel",
            "Ağaç",
            "Kabuk (Radial)",
        ])
        self.layout_combo.currentIndexChanged.connect(self._on_layout_change)
        layout.addWidget(self.layout_combo)

        self._add_separator(layout)

        # ── Zoom Controls ──
        zoom_out_btn = self._make_icon_button("−")
        zoom_out_btn.setToolTip("Uzaklastir")
        zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        layout.addWidget(zoom_out_btn)

        zoom_fit_btn = self._make_icon_button("⛶")
        zoom_fit_btn.setToolTip("Sigdir")
        zoom_fit_btn.clicked.connect(self.zoom_fit_requested.emit)
        layout.addWidget(zoom_fit_btn)

        zoom_in_btn = self._make_icon_button("＋")
        zoom_in_btn.setToolTip("Yakinlastir")
        zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        layout.addWidget(zoom_in_btn)

        layout.addStretch()

        # ── Search ──
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Sayfa ara...")
        self.search_input.setToolTip(
            "Normal arama başlıkta ve linkte arar.\n"
            "Sadece linkte arama yapmak için '/' ile başlayın.\n"
            "Tam link yapıştırdığınızda otomatik olarak yola (path) çevrilir."
        )
        self.search_input.setFixedWidth(220)
        self.search_input.returnPressed.connect(
            lambda: self.search_submitted.emit(self.search_input.text())
        )
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)

        # ── Export ──
        export_btn = self._make_icon_button("⊛") # Or maybe ⭳
        export_btn.setText("⭳")
        export_btn.setToolTip("Dışa Aktar")
        export_btn.clicked.connect(self.export_requested.emit)
        layout.addWidget(export_btn)

        # ── Settings ──
        settings_btn = self._make_icon_button("⚙")
        settings_btn.setToolTip("Gelistirmis ayarlar ve yapilandirma")
        settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(settings_btn)

    def _make_button(self, text: str, object_name: str) -> QPushButton:
        """Create a styled button."""
        btn = QPushButton(text)
        if object_name:
            btn.setObjectName(object_name)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        return btn

    def _make_icon_button(self, icon_text: str) -> QPushButton:
        """Create a small icon button."""
        btn = QPushButton(icon_text)
        btn.setFixedSize(34, 34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        # Zero padding so text isn't hidden inside a small fixed box
        btn.setStyleSheet("padding: 0px;")
        return btn

    def _add_separator(self, layout: QHBoxLayout):
        """Add a vertical separator line."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(
            f"color: {COLORS['border']}; background: transparent;"
        )
        sep.setFixedWidth(1)
        layout.addWidget(sep)

    def _on_layout_change(self, index: int):
        """Handle layout type change."""
        layout_map = {
            0: "smart_tree",
            1: "force",
            2: "circular",
            3: "tree",
            4: "radial",
        }
        self.layout_changed.emit(layout_map.get(index, "force"))

    def set_loading(self, loading: bool, message: str = ""):
        """Update UI during loading state."""
        self.crawl_btn.setEnabled(not loading)
        self.gsc_btn.setEnabled(not loading)
        if loading and message:
            self.crawl_btn.setText(f"{message}")
        else:
            self.crawl_btn.setText("Siteyi Tara")

    def show_crawl_missing_button(self, count: int):
        """Show the crawl missing pages button if there are pages to crawl."""
        if count > 0:
            self.crawl_missing_btn.setText(f"Eksik Sayfalari Tara ({count})")
            self.crawl_missing_btn.show()
        else:
            self.crawl_missing_btn.hide()

    def _on_search_text_changed(self, text: str):
        """Format pasted URLs to only keep the path if a domain is pasted."""
        # Check if the text starts with a protocol
        if text.startswith("http://") or text.startswith("https://"):
            from urllib.parse import urlparse
            try:
                parsed = urlparse(text)
                if parsed.path:
                    new_text = parsed.path
                    if parsed.query:
                        new_text += "?" + parsed.query
                    if parsed.fragment:
                        new_text += "#" + parsed.fragment
                    
                    self.search_input.setText(new_text)
            except Exception as e:
                logger.debug(f"URL parse basarisiz: {e}")

    def refresh_sites(self, sites: list, active_site_id: str):
        """Update the site selection dropdown."""
        self.site_combo.blockSignals(True)
        self.site_combo.clear()
        
        if not sites:
            self.site_combo.addItem("Site Seçilmemiş", None)
            self.site_combo.setEnabled(False)
        else:
            self.site_combo.setEnabled(True)
            active_index = 0
            for i, site in enumerate(sites):
                self.site_combo.addItem(site["name"], site["id"])
                if site["id"] == active_site_id:
                    active_index = i
            self.site_combo.setCurrentIndex(active_index)
        self.site_combo.blockSignals(False)

    def _on_site_combo_changed(self, index: int):
        site_id = self.site_combo.itemData(index)
        if site_id:
            self.site_changed.emit(site_id)

