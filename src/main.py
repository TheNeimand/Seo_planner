"""
SEO Planner — Application entry point.
Site map visualization and keyword analysis tool powered by GSC.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


def setup_logging():
    """Configure application-wide logging."""
    log_dir = Path(__file__).parent.parent / "data"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "seo_planner.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("SEO Planner starting...")
    logger.info("=" * 60)

    # Create application
    app = QApplication(sys.argv)

    # High DPI support
    app.setStyle("Fusion")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Import and create main window
    from src.ui.app import MainWindow

    window = MainWindow()
    window.show()

    logger.info("Application window displayed.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
