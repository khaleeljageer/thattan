import logging
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
from PySide6.QtWidgets import QApplication

from ezhuthaali.core.progress import ProgressStore
from ezhuthaali.core.levels import LevelRepository
from ezhuthaali.ui.main_window import MainWindow


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def load_application_font(app: QApplication) -> None:
    """Load and set TAU-Marutham as the default font for the application"""
    # Get the font file path
    font_path = Path(__file__).parent / "assets" / "TAU-Marutham.ttf"
    
    if not font_path.exists():
        logging.warning(f"Font file not found: {font_path}")
        return
    
    # Load the font
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        logging.warning(f"Failed to load font: {font_path}")
        return

    font_families = QFontDatabase.applicationFontFamilies(font_id)
    if not font_families:
        logging.warning(f"Font loaded but no family name found: {font_path}")
        return

    font_family = font_families[0]

    # Set as default application font (Qt + widgets)
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

    app_font.setPointSize(11)  # default size; UI can override per-widget
    app.setFont(app_font)
    QGuiApplication.setFont(app_font)
    QApplication.setFont(app_font)

    logging.info(f"Loaded and set default font: {font_family}")


def run() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    
    # Load and set the Tamil font as default
    load_application_font(app)

    levels = LevelRepository()
    progress_store = ProgressStore()

    window = MainWindow(levels=levels, progress_store=progress_store)
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        geometry = screen.availableGeometry()
        window.setGeometry(geometry)
    window.show()

    sys.exit(app.exec())
