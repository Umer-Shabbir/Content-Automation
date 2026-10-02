from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QSplitter,
    QPushButton
)
from PySide6.QtCore import Qt, Signal
from app.ui.components.job_table import JobTable


class HistoryView(QWidget):
    """
    History View displaying previously completed generations and an output preview pane.
    """

    job_selected = Signal(str)  # Emits job_id when selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        header_label = QLabel("Generation History")
        header_label.setObjectName("header")
        header_row.addWidget(header_label)
        layout.addLayout(header_row)

        # Splitter for list + preview
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left pane: Job Table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        table_title = QLabel("Completed Generations")
        table_title.setObjectName("subheader")
        left_layout.addWidget(table_title)

        self.table = JobTable()
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.table)
        splitter.addWidget(left_widget)

        # Right pane: Output Preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_title = QLabel("Output Content")
        preview_title.setObjectName("subheader")
        right_layout.addWidget(preview_title)

        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setPlaceholderText("Select a completed job to view generated output...")
        right_layout.addWidget(self.preview_box)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _on_selection_changed(self):
        job_id = self.table.get_selected_job_id()
        if job_id:
            self.job_selected.emit(job_id)

    def update_history(self, jobs: List[Dict[str, Any]]):
        """Populate the table with history records."""
        self.table.set_jobs(jobs)

    def set_preview_text(self, text: str):
        """Set preview pane text content."""
        self.preview_box.setPlainText(text)
