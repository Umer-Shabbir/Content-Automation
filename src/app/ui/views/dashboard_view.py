from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtCore import Signal
from app.ui.components.metric_card import MetricCard
from app.ui.components.job_table import JobTable


class DashboardView(QWidget):
    refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Row
        header_row = QHBoxLayout()
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        header_row.addWidget(title_label)

        header_row.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        header_row.addWidget(self.refresh_btn)

        layout.addLayout(header_row)

        # Metrics Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(16)

        self.total_card = MetricCard("Total Jobs", "0")
        self.success_card = MetricCard("Successful", "0")
        self.failed_card = MetricCard("Failed", "0")

        metrics_row.addWidget(self.total_card)
        metrics_row.addWidget(self.success_card)
        metrics_row.addWidget(self.failed_card)

        layout.addLayout(metrics_row)

        # Table Subheader
        table_label = QLabel("Active & Recent Jobs")
        table_label.setStyleSheet("font-size: 15px; font-weight: 600; color: #94A3B8; margin-top: 12px;")
        layout.addWidget(table_label)

        # Table
        self.job_table = JobTable()
        layout.addWidget(self.job_table)

    def update_metrics(self, total: int, success: int, failed: int):
        self.total_card.set_value(str(total))
        self.success_card.set_value(str(success))
        self.failed_card.set_value(str(failed))

    def update_jobs(self, jobs: List[Dict[str, Any]]):
        self.job_table.refresh_data(jobs)
