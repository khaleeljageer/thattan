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
    
    if font_path.exists():
        # Load the font
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id != -1:
            # Get the font family name
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                font_family = font_families[0]
                # Set as default application font
                app_font = QFont(font_family)
                app_font.setPointSize(10)  # Default size, can be overridden
                app.setFont(app_font)
                logging.info(f"Loaded and set default font: {font_family}")
            else:
                logging.warning(f"Font loaded but no family name found: {font_path}")
        else:
            logging.warning(f"Failed to load font: {font_path}")
    else:
        logging.warning(f"Font file not found: {font_path}")


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
