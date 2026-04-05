"""
Sidebar panel for displaying page details and keyword data.
Shows when a node is clicked on the graph.
"""
import logging

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QPushButton, QSizePolicy, QAbstractItemView, QSpacerItem,
)

from src.config import COLORS, NODE_COLORS
from src.gsc.models import Page, KeywordData

logger = logging.getLogger(__name__)


class MetricCard(QFrame):
    """A small card showing a single metric value."""

    def __init__(self, label: str, value: str, color: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setFixedHeight(70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        if color:
            value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        text_label = QLabel(label)
        text_label.setObjectName("metricLabel")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text_label)

        self.value_label = value_label

    def update_value(self, value: str):
        self.value_label.setText(value)


class Sidebar(QWidget):
    """
    Right sidebar panel that displays page details and keyword table.
    """

    keyword_fetch_requested = Signal(str)  # Emits URL to fetch keywords for
    page_link_clicked = Signal(str)  # Emits URL of a clicked link
    hide_page_requested = Signal(str)  # Emits URL to be hidden

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarFrame")
        self.setMinimumWidth(450)
        self.setMaximumWidth(600)
        self.current_url = ""

        self._setup_ui()

    def _setup_ui(self):
        """Build the sidebar UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)

        # ── Header ──
        self.header_frame = QFrame()
        self.header_frame.setObjectName("cardFrame")
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setSpacing(4)

        # Page type badge + close button
        top_row = QHBoxLayout()
        self.type_badge = QLabel("SAYFA")
        self.type_badge.setStyleSheet(
            "background-color: #21262D; color: #8B949E; "
            "padding: 2px 8px; border-radius: 4px; font-size: 10px; "
            "font-weight: 700; letter-spacing: 1px;"
        )
        top_row.addWidget(self.type_badge)
        top_row.addStretch()

        self.hide_btn = QPushButton("👁 Gizle")
        self.hide_btn.setFixedHeight(30)
        self.hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hide_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; padding: 2px 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; }}"
        )
        self.hide_btn.clicked.connect(self._on_hide_clicked)
        top_row.addWidget(self.hide_btn)

        close_btn = QPushButton("X  Kapat")
        close_btn.setFixedHeight(30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: {COLORS['bg_tertiary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 6px; "
            f"color: {COLORS['text_secondary']}; font-size: 12px; "
            f"font-weight: 600; padding: 2px 12px; }}"
            f"QPushButton:hover {{ background: {COLORS['accent_red']}; "
            f"color: white; border-color: {COLORS['accent_red']}; }}"
        )
        close_btn.clicked.connect(self.hide)
        top_row.addWidget(close_btn)
        header_layout.addLayout(top_row)

        self.title_label = QLabel("Sayfa Seçin")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label)

        self.url_label = QLabel("")
        self.url_label.setObjectName("metricLabel")
        self.url_label.setWordWrap(True)
        self.url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        header_layout.addWidget(self.url_label)

        self.content_layout.addWidget(self.header_frame)

        # ── Metrics Row ──
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)

        self.clicks_card = MetricCard("Tıklama", "0", COLORS["accent_blue"])
        self.impressions_card = MetricCard("Gösterim", "0", COLORS["accent_green"])
        self.position_card = MetricCard("Pozisyon", "0", COLORS["accent_orange"])
        self.ctr_card = MetricCard("CTR", "0%", COLORS["accent_purple"])

        metrics_row.addWidget(self.clicks_card)
        metrics_row.addWidget(self.impressions_card)
        metrics_row.addWidget(self.position_card)
        metrics_row.addWidget(self.ctr_card)

        self.content_layout.addLayout(metrics_row)

        # ── Link Metrics ──
        link_frame = QFrame()
        link_frame.setObjectName("cardFrame")
        link_layout = QHBoxLayout(link_frame)
        link_layout.setSpacing(16)

        self.in_links_label = QLabel("← Gelen: 0")
        self.in_links_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-weight: 600;")
        link_layout.addWidget(self.in_links_label)

        self.out_links_label = QLabel("→ Giden: 0")
        self.out_links_label.setStyleSheet(f"color: {COLORS['accent_blue']}; font-weight: 600;")
        link_layout.addWidget(self.out_links_label)

        self.ext_links_label = QLabel("↗ Dış: 0")
        self.ext_links_label.setStyleSheet(f"color: {COLORS['accent_orange']}; font-weight: 600;")
        link_layout.addWidget(self.ext_links_label)

        self.content_layout.addWidget(link_frame)

        # ── Keywords Section ──
        kw_header = QHBoxLayout()
        kw_title = QLabel("🔑 ANAHTAR KELİMELER")
        kw_title.setObjectName("sectionLabel")
        kw_header.addWidget(kw_title)
        kw_header.addStretch()

        self.fetch_kw_btn = QPushButton("Verileri Çek")
        self.fetch_kw_btn.setObjectName("accentButton")
        self.fetch_kw_btn.setFixedHeight(28)
        self.fetch_kw_btn.clicked.connect(self._on_fetch_keywords)
        kw_header.addWidget(self.fetch_kw_btn)

        self.content_layout.addLayout(kw_header)

        self.kw_count_label = QLabel("Henüz veri yok")
        self.kw_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.content_layout.addWidget(self.kw_count_label)

        # Keyword table
        self.keyword_table = QTableWidget()
        self.keyword_table.setColumnCount(5)
        self.keyword_table.setHorizontalHeaderLabels(
            ["Anahtar Kelime", "Tıklama", "Gösterim", "CTR", "Pozisyon"]
        )
        self.keyword_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, 5):
            self.keyword_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )
        self.keyword_table.verticalHeader().setVisible(False)
        self.keyword_table.setAlternatingRowColors(True)
        self.keyword_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.keyword_table.setSortingEnabled(True)
        self.keyword_table.setMinimumHeight(250)
        self.content_layout.addWidget(self.keyword_table)

        # ── Internal Links Section ──
        links_title = QLabel("🔗 İÇ LİNKLER (GİDEN)")
        links_title.setObjectName("sectionLabel")
        self.content_layout.addWidget(links_title)

        self.links_table = QTableWidget()
        self.links_table.setColumnCount(2)
        self.links_table.setHorizontalHeaderLabels(["Sayfa", "Anchor Text"])
        self.links_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.links_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.links_table.verticalHeader().setVisible(False)
        self.links_table.setAlternatingRowColors(True)
        self.links_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.links_table.setMinimumHeight(150)
        self.links_table.cellDoubleClicked.connect(self._on_link_clicked)
        self.content_layout.addWidget(self.links_table)

        # ── Incoming Links Section ──
        incoming_title = QLabel("📥 İÇ LİNKLER (GELEN)")
        incoming_title.setObjectName("sectionLabel")
        self.content_layout.addWidget(incoming_title)

        self.incoming_table = QTableWidget()
        self.incoming_table.setColumnCount(1)
        self.incoming_table.setHorizontalHeaderLabels(["Kaynak Sayfa"])
        self.incoming_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.incoming_table.verticalHeader().setVisible(False)
        self.incoming_table.setAlternatingRowColors(True)
        self.incoming_table.setMinimumHeight(120)
        self.incoming_table.cellDoubleClicked.connect(
            self._on_incoming_link_clicked
        )
        self.content_layout.addWidget(self.incoming_table)

        # Spacer
        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def show_page(self, page: Page):
        """Display data for the given page."""
        self.current_url = page.url

        # Header
        self.title_label.setText(page.title or page.short_url)
        self.url_label.setText(page.url)

        # Type badge
        type_names = {
            "homepage": "ANA SAYFA",
            "category": "KATEGORİ",
            "product": "ÜRÜN",
            "blog": "BLOG",
            "other": "DİĞER",
        }
        type_colors = NODE_COLORS.get(page.page_type, "#8B949E")
        self.type_badge.setText(type_names.get(page.page_type, "DİĞER"))
        self.type_badge.setStyleSheet(
            f"background-color: {type_colors}20; color: {type_colors}; "
            f"padding: 2px 8px; border-radius: 4px; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 1px;"
        )

        # Metrics
        self.clicks_card.update_value(f"{page.total_clicks:,}")
        self.impressions_card.update_value(f"{page.total_impressions:,}")
        self.position_card.update_value(f"{page.avg_position:.1f}")
        self.ctr_card.update_value(f"{page.avg_ctr:.1%}")

        # Link metrics
        self.in_links_label.setText(f"← Gelen: {page.in_degree}")
        self.out_links_label.setText(f"→ Giden: {page.out_degree}")
        self.ext_links_label.setText(f"↗ Dış: {len(page.external_links)}")

        # Keywords
        self._populate_keywords(page.gsc_keywords)

        # Outgoing links
        self.links_table.setRowCount(len(page.internal_links_out))
        for i, link_url in enumerate(page.internal_links_out):
            from urllib.parse import urlparse
            path = urlparse(link_url).path or "/"
            self.links_table.setItem(i, 0, QTableWidgetItem(path))
            anchor = page.anchor_texts_out.get(link_url, "")
            self.links_table.setItem(i, 1, QTableWidgetItem(anchor))

        # Incoming links
        self.incoming_table.setRowCount(len(page.internal_links_in))
        for i, link_url in enumerate(page.internal_links_in):
            from urllib.parse import urlparse
            path = urlparse(link_url).path or "/"
            self.incoming_table.setItem(i, 0, QTableWidgetItem(path))

        self.show()

    def _populate_keywords(self, keywords: list[KeywordData]):
        """Fill the keyword table with data."""
        self.keyword_table.setSortingEnabled(False)
        self.keyword_table.setRowCount(len(keywords))

        for i, kw in enumerate(keywords):
            query_item = QTableWidgetItem(kw.query)
            clicks_item = QTableWidgetItem()
            clicks_item.setData(Qt.ItemDataRole.DisplayRole, kw.clicks)
            imp_item = QTableWidgetItem()
            imp_item.setData(Qt.ItemDataRole.DisplayRole, kw.impressions)
            ctr_item = QTableWidgetItem(f"{kw.ctr:.1%}")
            pos_item = QTableWidgetItem(f"{kw.position:.1f}")

            # Color coding for position
            if kw.position <= 3:
                pos_item.setForeground(QColor(COLORS["accent_green"]))
            elif kw.position <= 10:
                pos_item.setForeground(QColor(COLORS["accent_blue"]))
            elif kw.position <= 20:
                pos_item.setForeground(QColor(COLORS["accent_orange"]))
            else:
                pos_item.setForeground(QColor(COLORS["accent_red"]))

            self.keyword_table.setItem(i, 0, query_item)
            self.keyword_table.setItem(i, 1, clicks_item)
            self.keyword_table.setItem(i, 2, imp_item)
            self.keyword_table.setItem(i, 3, ctr_item)
            self.keyword_table.setItem(i, 4, pos_item)

        self.keyword_table.setSortingEnabled(True)

        if keywords:
            self.kw_count_label.setText(f"✅ {len(keywords)} anahtar kelime bulundu")
            self.kw_count_label.setStyleSheet(f"color: {COLORS['accent_green']}; font-size: 11px;")
            self.fetch_kw_btn.setVisible(False)
        else:
            self.kw_count_label.setText("Henüz veri yok — \"Verileri Çek\" butonuna tıklayın")
            self.kw_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            self.fetch_kw_btn.setVisible(True)

    def _on_fetch_keywords(self):
        """Request keyword fetch for current page."""
        if self.current_url:
            self.keyword_fetch_requested.emit(self.current_url)

    def _on_link_clicked(self, row: int, col: int):
        """Handle click on outgoing link."""
        item = self.links_table.item(row, 0)
        if item:
            # Reconstruct full URL from path
            from urllib.parse import urlparse
            path = item.text()
            # Emit the URL path to focus on that node
            self.page_link_clicked.emit(path)

    def _on_incoming_link_clicked(self, row: int, col: int):
        """Handle click on incoming link."""
        item = self.incoming_table.item(row, 0)
        if item:
            self.page_link_clicked.emit(item.text())

    def _on_hide_clicked(self):
        """Request the current page to be hidden from the graph."""
        if self.current_url:
            self.hide_page_requested.emit(self.current_url)
