"""
Dialog windows for progress, errors, and settings.
"""
import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QMessageBox, QTextEdit,
    QSpinBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGroupBox, QComboBox, QScrollArea, QCheckBox, QWidget,
    QTabWidget, QListWidget, QListWidgetItem, QLineEdit, QFileDialog,
)

from src.config import (
    COLORS, SETTINGS_FILE,
    CRAWL_WORKERS, CRAWL_DELAY, CRAWL_MAX_DEPTH, CRAWL_MAX_PAGES,
)

logger = logging.getLogger(__name__)


# ─── User Settings Manager ───────────────────────────────────────────────────

_DEFAULT_SETTINGS = {
    "crawl_workers": CRAWL_WORKERS,
    "crawl_delay": CRAWL_DELAY,
    "crawl_max_depth": CRAWL_MAX_DEPTH,
    "crawl_max_pages": CRAWL_MAX_PAGES,
    "sites": [],  # List of dicts: {"id": str, "name": str, "url": str, "gsc_property": str, "creds_path": str}
    "active_site_id": None,
}


def load_settings() -> dict:
    """Load user settings from JSON file, falling back to defaults."""
    settings = dict(_DEFAULT_SETTINGS)
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
    return settings


def save_settings(settings: dict) -> None:
    """Persist user settings to JSON file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        logger.info("Settings saved.")
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")


# ─── Progress Dialog ─────────────────────────────────────────────────────────

class ProgressDialog(QDialog):
    """
    Modal progress dialog shown during crawling and API operations.
    """

    cancel_requested = Signal()

    def __init__(self, title: str = "İşlem Devam Ediyor", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(480, 200)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_secondary']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 12px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #FFFFFF;"
        )
        layout.addWidget(self.title_label)

        # Status message
        self.status_label = QLabel("Başlatılıyor...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)

        # Counter
        self.counter_label = QLabel("")
        self.counter_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
        )
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.counter_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedSize(90, 32)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']}; }}"
        )
        cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def update_progress(self, current: int, total: int, message: str):
        """Update the progress display."""
        self.status_label.setText(message)

        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)
            self.counter_label.setText(f"{current} / {total}")
        else:
            self.progress_bar.setRange(0, 0)  # Indeterminate
            self.counter_label.setText(f"{current} işlendi")

    def _on_cancel(self):
        self.cancel_requested.emit()
        self.close()

    def finish(self, message: str = "Tamamlandı!"):
        """Mark the operation as complete."""
        self.status_label.setText(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.counter_label.setText("")


# ─── Error Dialog ─────────────────────────────────────────────────────────────

class ErrorDialog:
    """Utility for showing error dialogs."""

    @staticmethod
    def show(parent, title: str, message: str, details: str = ""):
        """Show an error dialog."""
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if details:
            msg_box.setDetailedText(details)
        msg_box.setStyleSheet(
            f"QMessageBox {{ background-color: {COLORS['bg_secondary']}; "
            f"color: {COLORS['text_primary']}; }}"
        )
        msg_box.exec()

    @staticmethod
    def show_info(parent, title: str, message: str):
        """Show an info dialog."""
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStyleSheet(
            f"QMessageBox {{ background-color: {COLORS['bg_secondary']}; "
            f"color: {COLORS['text_primary']}; }}"
        )
        msg_box.exec()


# ─── Settings Dialog ─────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """
    Settings dialog for configuring crawl and application behaviour.
    Opened via the ⚙ icon on the toolbar.
    """

    settings_changed = Signal(dict)  # emits the full settings dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setFixedSize(400, 390)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_secondary']}; "
            f"border: 1px solid {COLORS['border']}; }}"
        )

        self._settings = load_settings()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"QTabWidget::pane {{ border-top: 1px solid {COLORS['border']}; background-color: {COLORS['bg_secondary']}; }}"
            f"QTabBar::tab {{ background: {COLORS['bg_tertiary']}; color: {COLORS['text_secondary']}; padding: 10px 20px; border: 1px solid {COLORS['border']}; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }}"
            f"QTabBar::tab:selected {{ background: {COLORS['bg_secondary']}; color: {COLORS['text_primary']}; border-bottom: 2px solid {COLORS['accent_blue']}; }}"
            f"QTabBar::tab:hover {{ background: {COLORS['bg_secondary']}; }}"
        )

        # ── Tab 1: Crawler Settings ──
        crawler_tab = QWidget()
        crawler_layout = QVBoxLayout(crawler_tab)
        crawler_layout.setContentsMargins(24, 24, 24, 24)
        crawler_layout.setSpacing(16)

        # Title
        title = QLabel("Uygulama Ayarları")
        title.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 4px;"
        )
        crawler_layout.addWidget(title)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {COLORS['border']};")
        crawler_layout.addWidget(separator)

        # Crawler group
        crawl_group = QGroupBox("Tarayıcı Yapılandırması")
        crawl_group.setStyleSheet(
            f"QGroupBox {{ color: {COLORS['text_secondary']}; font-weight: 600; font-size: 13px; border: 1px solid {COLORS['border']}; border-radius: 6px; margin-top: 14px; padding-top: 18px; background-color: {COLORS['bg_primary']}; }} "
            f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 4px; left: 8px; }}"
        )
        form = QFormLayout(crawl_group)
        form.setSpacing(12)
        form.setContentsMargins(16, 20, 16, 16)

        label_style = f"color: {COLORS['text_secondary']}; font-weight: 500;"
        combo_style = (
            f"QComboBox {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 8px; color: {COLORS['text_primary']}; font-size: 13px; min-width: 120px; }} "
            f"QComboBox:focus {{ border: 1px solid {COLORS['text_muted']}; }}"
        )

        def make_combo(items_dict, current_val):
            cb = QComboBox()
            cb.setStyleSheet(combo_style)
            for text, val in items_dict.items(): cb.addItem(text, val)
            idx = cb.findData(current_val)
            if idx >= 0: cb.setCurrentIndex(idx)
            else:
                cb.addItem(f"Ozel ({current_val})", current_val)
                cb.setCurrentIndex(cb.count() - 1)
            return cb

        self.spider_combo = make_combo({"1 Spider": 1, "2 Spider": 2, "3 Spider": 3, "5 Spider": 5, "10 Spider": 10}, self._settings["crawl_workers"])
        form.addRow(QLabel("Spider Sayısı:", styleSheet=label_style), self.spider_combo)

        self.delay_combo = make_combo({"Yok (0.0s)": 0.0, "0.1s": 0.1, "0.3s": 0.3, "0.5s": 0.5, "1.0s": 1.0}, self._settings["crawl_delay"])
        form.addRow(QLabel("İstek Gecikmesi:", styleSheet=label_style), self.delay_combo)

        self.depth_combo = make_combo({"1 Seviye": 1, "3 Seviye": 3, "5 Seviye": 5, "10 Seviye": 10, "Limit yok": 100}, self._settings["crawl_max_depth"])
        form.addRow(QLabel("Maks. Derinlik:", styleSheet=label_style), self.depth_combo)

        self.pages_combo = make_combo({"50": 50, "100": 100, "500": 500, "1000": 1000, "5000": 5000}, self._settings["crawl_max_pages"])
        form.addRow(QLabel("Maks. Sayfa:", styleSheet=label_style), self.pages_combo)

        crawler_layout.addWidget(crawl_group)
        crawler_layout.addStretch()
        self.tabs.addTab(crawler_tab, "Tarayıcı")

        # ── Tab 2: Site Management ──
        sites_tab = QWidget()
        sites_layout = QVBoxLayout(sites_tab)
        sites_layout.setContentsMargins(16, 16, 16, 16)
        sites_layout.setSpacing(12)

        # Site list
        self.sites_list = QListWidget()
        self.sites_list.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_primary']}; border: 1px solid {COLORS['border']}; border-radius: 6px; padding: 4px; color: {COLORS['text_primary']}; }}"
            f"QListWidget::item {{ border-bottom: 1px solid {COLORS['border']}; padding: 8px; }}"
            f"QListWidget::item:selected {{ background-color: {COLORS['selected']}; color: white; border-radius: 4px; }}"
        )
        self._refresh_sites_list()
        sites_layout.addWidget(QLabel("Ekli Siteler (Proje Dosyaları)", styleSheet=f"color: {COLORS['text_primary']}; font-weight: bold;"))
        sites_layout.addWidget(self.sites_list)

        # Buttons for site management
        site_btn_layout = QHBoxLayout()
        add_site_btn = QPushButton("+ Site Ekle")
        add_site_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent_green']}; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: bold; }} QPushButton:hover {{ background-color: #4ed360; }}")
        add_site_btn.clicked.connect(self._add_site_dialog)
        
        del_site_btn = QPushButton("Sil")
        del_site_btn.setStyleSheet(f"QPushButton {{ background-color: transparent; color: {COLORS['accent_red']}; border: 1px solid {COLORS['accent_red']}; border-radius: 4px; padding: 6px 12px; }} QPushButton:hover {{ background-color: {COLORS['accent_red']}; color: white; }}")
        del_site_btn.clicked.connect(self._delete_site)

        active_site_btn = QPushButton("Aktif Yap")
        active_site_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent_blue']}; color: white; border: none; border-radius: 4px; padding: 6px 12px; }} QPushButton:hover {{ background-color: #6fbaff; }}")
        active_site_btn.clicked.connect(self._set_active_site)

        site_btn_layout.addWidget(add_site_btn)
        site_btn_layout.addWidget(active_site_btn)
        site_btn_layout.addStretch()
        site_btn_layout.addWidget(del_site_btn)
        sites_layout.addLayout(site_btn_layout)

        self.tabs.addTab(sites_tab, "Siteler")
        layout.addWidget(self.tabs)

        # Lower UI buttons (Save/Cancel)
        bottom_btns = QWidget()
        bottom_btns.setFixedHeight(60)
        bottom_btn_layout = QHBoxLayout(bottom_btns)
        bottom_btn_layout.setContentsMargins(16, 0, 16, 0)
        bottom_btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedSize(80, 30)
        cancel_btn.setStyleSheet(f"QPushButton {{ color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; }} QPushButton:hover {{ background: {COLORS['bg_primary']}; }}")
        cancel_btn.clicked.connect(self.reject)
        bottom_btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Kaydet")
        save_btn.setFixedSize(80, 30)
        save_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['accent_blue']}; color: white; border: none; border-radius: 4px; font-weight: bold; }} QPushButton:hover {{ background-color: #6fbaff; }}")
        save_btn.clicked.connect(self._save_and_close)
        bottom_btn_layout.addWidget(save_btn)
        layout.addWidget(bottom_btns)

    def _refresh_sites_list(self):
        self.sites_list.clear()
        for site in self._settings["sites"]:
            display = f"{site['name']} ({site['url']})"
            if site["id"] == self._settings["active_site_id"]:
                display = "⭐ " + display
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, site["id"])
            self.sites_list.addItem(item)

    def _add_site_dialog(self):
        # Nested dialog for adding site
        dialog = QDialog(self)
        dialog.setWindowTitle("Yeni Site Ekle")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet(f"QDialog {{ background-color: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']}; }}")
        
        d_layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        name_edit = QLineEdit(); name_edit.setPlaceholderText("Örn: Altınoran Web")
        url_edit = QLineEdit(); url_edit.setPlaceholderText("https://www.orneksite.com")
        property_edit = QLineEdit(); property_edit.setPlaceholderText("orneksite.com (veya sc-domain:...)")
        creds_edit = QLineEdit(); creds_edit.setReadOnly(True)
        
        def pick_creds():
            path, _ = QFileDialog.getOpenFileName(dialog, "JSON Credentials Seç", "", "JSON Dosyaları (*.json)")
            if path: creds_edit.setText(path)

        creds_row = QHBoxLayout()
        creds_row.addWidget(creds_edit)
        pick_btn = QPushButton("Dosya Seç")
        pick_btn.clicked.connect(pick_creds)
        creds_row.addWidget(pick_btn)

        form.addRow(QLabel("Site Adı:", styleSheet=f"color: {COLORS['text_primary']}"), name_edit)
        form.addRow(QLabel("Site URL:", styleSheet=f"color: {COLORS['text_primary']}"), url_edit)
        form.addRow(QLabel("GSC Mülkü:", styleSheet=f"color: {COLORS['text_primary']}"), property_edit)
        form.addRow(QLabel("GSC JSON:", styleSheet=f"color: {COLORS['text_primary']}"), creds_row)
        d_layout.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()
        add_btn = QPushButton("Ekle")
        add_btn.setStyleSheet(f"background-color: {COLORS['accent_blue']}; color: white; padding: 6px 16px; font-weight: bold; border-radius: 4px;")
        add_btn.clicked.connect(dialog.accept)
        btns.addWidget(add_btn)
        d_layout.addLayout(btns)

        if dialog.exec() == QDialog.Accepted:
            if not name_edit.text() or not url_edit.text() or not property_edit.text() or not creds_edit.text():
                return
            
            prop = property_edit.text().strip()
            if not prop.startswith(("http://", "https://", "sc-domain:")):
                prop = f"sc-domain:{prop}"

            import uuid
            site_id = str(uuid.uuid4())[:8]
            new_site = {
                "id": site_id,
                "name": name_edit.text().strip(),
                "url": url_edit.text().strip(),
                "gsc_property": prop,
                "creds_path": creds_edit.text().strip()
            }
            self._settings["sites"].append(new_site)
            if not self._settings["active_site_id"]:
                self._settings["active_site_id"] = site_id
            
            self._refresh_sites_list()

    def _delete_site(self):
        curr = self.sites_list.currentItem()
        if not curr: return
        site_id = curr.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "Siteyi Sil", "Bu siteyi ve tüm ayarlarını silmek istiyor musunuz?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._settings["sites"] = [s for s in self._settings["sites"] if s["id"] != site_id]
            if self._settings["active_site_id"] == site_id:
                self._settings["active_site_id"] = self._settings["sites"][0]["id"] if self._settings["sites"] else None
            self._refresh_sites_list()

    def _set_active_site(self):
        curr = self.sites_list.currentItem()
        if not curr: return
        site_id = curr.data(Qt.UserRole)
        self._settings["active_site_id"] = site_id
        self._refresh_sites_list()

    def _save_and_close(self):
        """Save settings and close the dialog."""
        self._settings["crawl_workers"] = self.spider_combo.currentData()
        self._settings["crawl_delay"] = self.delay_combo.currentData()
        self._settings["crawl_max_depth"] = self.depth_combo.currentData()
        self._settings["crawl_max_pages"] = self.pages_combo.currentData()

        save_settings(self._settings)
        self.settings_changed.emit(dict(self._settings))
        self.accept()

    def get_settings(self) -> dict:
        return dict(self._settings)

# ─── Filter Dialog ──────────────────────────────────────────────────────────

class FilterDialog(QDialog):
    """
    Dialog for selecting which URL categories to hide.
    """
    hidden_categories_changed = Signal(set)

    def __init__(self, category_counts: dict[str, int], hidden_categories: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kategorileri Filtrele")
        self.setFixedSize(450, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(
            f"QDialog {{ background-color: {COLORS['bg_secondary']}; "
            f"border: 1px solid {COLORS['border']}; }}"
        )

        self.category_counts = category_counts
        self.hidden_categories = set(hidden_categories)
        self.checkboxes = {}

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Kategorileri Gör / Gizle")
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};"
        )
        layout.addWidget(title)
        
        desc = QLabel("Seçili olmayan kategoriler ağ haritasında gösterilmez. İstemediğiniz gereksiz linklerin yanındaki tiki kaldırarek gizleyebilirsiniz.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(desc)

        # Actions
        actions_layout = QHBoxLayout()
        select_all_btn = QPushButton("Tümünü Seç")
        select_all_btn.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 4px; font-weight: bold; background: transparent; border: 1px solid {COLORS['border']}; border-radius: 4px;")
        select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_all_btn.clicked.connect(self._select_all)
        actions_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Tümünü Kaldır")
        deselect_all_btn.setStyleSheet(f"color: {COLORS['text_primary']}; padding: 4px; font-weight: bold; background: transparent; border: 1px solid {COLORS['border']}; border-radius: 4px;")
        deselect_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deselect_all_btn.clicked.connect(self._deselect_all)
        actions_layout.addWidget(deselect_all_btn)
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Scroll area for categories
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {COLORS['border']}; border-radius: 6px; background-color: {COLORS['bg_primary']}; }}"
            f"QWidget {{ background-color: transparent; }}"
        )
        
        container = QWidget()
        form = QVBoxLayout(container)
        form.setSpacing(8)

        # Sort categories by count (descending)
        sorted_cats = sorted(self.category_counts.items(), key=lambda x: x[1], reverse=True)

        for cat, count in sorted_cats:
            cb = QCheckBox(f"{cat} ({count} sayfa)")
            cb.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
            cb.setChecked(cat not in self.hidden_categories)
            self.checkboxes[cat] = cb
            form.addWidget(cb)
            
        form.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setFixedSize(80, 30)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background-color: transparent; "
            f"color: {COLORS['text_secondary']}; border: 1px solid {COLORS['border']}; border-radius: 4px; font-weight: 500; }}"
            f"QPushButton:hover {{ background-color: {COLORS['bg_primary']}; color: {COLORS['text_primary']}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Uygula")
        save_btn.setFixedSize(80, 30)
        save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {COLORS['text_primary']}; "
            f"color: {COLORS['bg_primary']}; border: none; border-radius: 4px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: #FFFFFF; }}"
        )
        save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def _save_and_close(self):
        self.hidden_categories.clear()
        for cat, cb in self.checkboxes.items():
            if not cb.isChecked():
                self.hidden_categories.add(cat)
        
        self.hidden_categories_changed.emit(self.hidden_categories)
        self.accept()

