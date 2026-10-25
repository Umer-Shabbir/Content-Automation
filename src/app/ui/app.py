import sys
import os

# Add src directory to path if running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.orchestrator.event_bus import default_bus
from app.db.idea_manager import get_idea_manager

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Initialize SQLite persistent database and IdeaManager with historical disk sync
    idea_manager = get_idea_manager()
    idea_manager.initialize()

    window = MainWindow(event_bus=default_bus)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
