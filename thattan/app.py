"""Application entry point and setup for the Thattan typing tutor."""

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont, QIcon
from PySide6.QtWidgets import QApplication

from thattan.core.progress import ProgressStore
from thattan.core.levels import LevelRepository
from thattan.ui.main_window import MainWindow


def configure_logging() -> None:
    """Configure application-wide logging with a standard format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def load_application_font(app: QApplication) -> None:
    """Load and set TAU-Marutham as the default font for the application."""
    font_path = Path(__file__).parent / "assets" / "TAU-Marutham.ttf"
    
    if not font_path.exists():
        logging.warning(f"Font file not found: {font_path}")
        return

    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        logging.warning(f"Failed to load font: {font_path}")
        return

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if not font_families:
        logging.warning(f"Font loaded but no family name found: {font_path}")
        return

    font_family = font_families[0]

    # Keep TAU-Marutham for Tamil text, but allow emoji fonts as fallbacks so
    # symbols like 🔥 ⭐ 🎯 render properly on Linux/Windows/macOS.
    app_font = QFont(font_family)
    try:
        app_font.setFamilies(
            [
                font_family,
                "Noto Color Emoji",  # Linux (common)
                "Noto Emoji",
                "Segoe UI Emoji",  # Windows
                "Apple Color Emoji",  # macOS
            ]
        )
    except Exception:
        # Older bindings may not support setFamilies; Qt will still try fallback fonts.
        pass

    app_font.setPointSize(11)
    app.setFont(app_font)
    QGuiApplication.setFont(app_font)
    QApplication.setFont(app_font)

    logging.info(f"Loaded and set default font: {font_family}")


def run() -> None:
    """Initialize the application, load resources, and start the main window."""
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Thattan")
    app.setApplicationDisplayName("Thattan")

    load_application_font(app)

    levels = LevelRepository()
    progress_store = ProgressStore()

    logo_dir = Path(__file__).parent / "assets" / "logo"
    for name in ("logo_256.png", "logo.svg"):
        icon_path = logo_dir / name
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break

    window = MainWindow(levels=levels, progress_store=progress_store)
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        window.setGeometry(geometry)
    window.show()

    sys.exit(app.exec())
