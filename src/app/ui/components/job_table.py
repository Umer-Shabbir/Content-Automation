from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt


class JobTable(QTableWidget):
    """
    A QTableWidget displaying jobs with standard columns:
    ID, Topic, Preset, Status, Created At.
    """

    COLUMNS = ["Job ID", "Topic", "Preset", "Status", "Created At"]

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)

    def set_jobs(self, jobs: List[Dict[str, Any]]):
        """Populate the table with a list of job dicts/records."""
        self.setRowCount(0)
        for job in jobs:
            row = self.rowCount()
            self.insertRow(row)

            job_id = str(job.get("id", ""))
            topic = str(job.get("topic", ""))
            preset = str(job.get("preset_name", job.get("preset", "")))
            status = str(job.get("status", ""))
            created_at = str(job.get("created_at", ""))

            self.setItem(row, 0, QTableWidgetItem(job_id))
            self.setItem(row, 1, QTableWidgetItem(topic))
            self.setItem(row, 2, QTableWidgetItem(preset))
            self.setItem(row, 3, QTableWidgetItem(status))
            self.setItem(row, 4, QTableWidgetItem(created_at))

    def refresh_data(self, jobs: List[Dict[str, Any]]):
        """Alias for set_jobs."""
        self.set_jobs(jobs)

    def update_jobs(self, jobs: List[Dict[str, Any]]):
        """Alias for set_jobs."""
        self.set_jobs(jobs)

    def update_or_add_job(self, job_data: Dict[str, Any]):
        """Update an existing job row or add a new one."""
        target_id = str(job_data.get("id", ""))
        row_to_update = -1

        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.text() == target_id:
                row_to_update = r
                break

        if row_to_update == -1:
            row_to_update = self.rowCount()
            self.insertRow(row_to_update)

        preset = str(job_data.get("preset_name", job_data.get("preset", "")))

        self.setItem(row_to_update, 0, QTableWidgetItem(target_id))
        self.setItem(row_to_update, 1, QTableWidgetItem(str(job_data.get("topic", ""))))
        self.setItem(row_to_update, 2, QTableWidgetItem(preset))
        self.setItem(row_to_update, 3, QTableWidgetItem(str(job_data.get("status", ""))))
        self.setItem(row_to_update, 4, QTableWidgetItem(str(job_data.get("created_at", ""))))

    def get_selected_job_id(self) -> Optional[str]:
        """Returns the ID of the currently selected job row, if any."""
        selected_rows = self.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        item = self.item(row, 0)
        return item.text() if item else None
