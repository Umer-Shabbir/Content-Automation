import sys
import os

# Add src directory to path if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.orchestrator.event_bus import default_bus
from app.db.database import DatabaseCoordinator

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Initialize SQLite database if needed
    db_coordinator = DatabaseCoordinator()

    window = MainWindow(event_bus=default_bus)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
