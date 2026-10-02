from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton
)


class LogsView(QWidget):
    """
    View for displaying application logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Title
        title = QLabel("System Logs")
        title.setObjectName("h1")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Text Edit for logs
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        # Use a monospace font
        self.logs_text.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; line-height: 1.2;")
        layout.addWidget(self.logs_text)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_clear = QPushButton("Clear Logs")
        self.btn_clear.clicked.connect(self.logs_text.clear)
        btn_layout.addWidget(self.btn_clear)

        layout.addLayout(btn_layout)

    def append_log(self, message: str):
        """Append a new log message to the log viewer."""
        self.logs_text.append(message)
        # Scroll to bottom
        scrollbar = self.logs_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
