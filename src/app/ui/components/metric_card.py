from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class MetricCard(QFrame):
    """
    A resizable card widget displaying a title and large value.
    """

    def __init__(self, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("metric_card")
        self.setProperty("class", "card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metric_title")

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("metric_value")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        """Update metric value displayed."""
        self.value_label.setText(str(value))

    def set_title(self, title: str):
        """Update metric title displayed."""
        self.title_label.setText(str(title))
