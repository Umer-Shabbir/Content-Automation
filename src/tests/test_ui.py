import pytest
import os
import sys

# Ensure offscreen platform for headless Qt tests
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.styles.theme import DARK_THEME
from app.ui.components.metric_card import MetricCard
from app.ui.components.job_table import JobTable
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.generate_view import GenerateView
from app.ui.views.history_view import HistoryView
from app.ui.views.presets_view import PresetsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.logs_view import LogsView
from app.ui.components.log_handler import SignaledLogHandler
from app.ui.main_window import MainWindow
from app.orchestrator.event_bus import EventBus
import logging


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()


def test_theme_content():
    assert "QMainWindow" in DARK_THEME
    assert "background-color" in DARK_THEME


def test_metric_card(qapp):
    card = MetricCard("Active Tasks", "12")
    assert card.title_label.text() == "Active Tasks"
    assert card.value_label.text() == "12"

    card.set_value(25)
    assert card.value_label.text() == "25"

    card.set_title("Completed")
    assert card.title_label.text() == "Completed"


def test_job_table(qapp):
    table = JobTable()
    assert table.columnCount() == 5

    jobs = [
        {"id": "j1", "topic": "Tech History", "preset": "history", "status": "COMPLETED", "created_at": "2026-09-20"},
        {"id": "j2", "topic": "Mystery Box", "preset": "mystery", "status": "RUNNING", "created_at": "2026-09-20"}
    ]
    table.set_jobs(jobs)
    assert table.rowCount() == 2

    # Update or add job
    table.update_or_add_job({"id": "j1", "topic": "Tech History", "preset": "history", "status": "FAILED", "created_at": "2026-09-20"})
    assert table.rowCount() == 2
    assert table.item(0, 3).text() == "FAILED"

    # Add new job
    table.update_or_add_job({"id": "j3", "topic": "Drama Scene", "preset": "drama", "status": "PENDING", "created_at": "2026-09-20"})
    assert table.rowCount() == 3


def test_dashboard_view(qapp):
    view = DashboardView()
    view.update_metrics(10, 8, 2)
    assert view.total_card.value_label.text() == "10"
    assert view.success_card.value_label.text() == "8"
    assert view.failed_card.value_label.text() == "2"

    jobs = [{"id": "j1", "topic": "Ancient Rome", "preset": "history", "status": "COMPLETED", "created_at": "2026-09-20"}]
    view.update_jobs(jobs)
    assert view.job_table.rowCount() == 1


def test_generate_view(qapp):
    view = GenerateView()
    emitted = []

    def on_generate(topic, presets, count, custom_output_dir):
        emitted.append((topic, presets, count, custom_output_dir))

    view.start_generation_requested.connect(on_generate)

    # Check default output directory
    assert view.output_dir_input.text() == r"H:\Automation\output"

    view.topic_input.setText("Space Odyssey")
    if "money_chuck" in view.preset_checkboxes:
        view.preset_checkboxes["money_chuck"].setChecked(True)
    view.count_spin.setValue(2)
    view.output_dir_input.setText(r"H:\Custom\Path")

    view.start_btn.click()
    assert len(emitted) == 1
    topic, presets, count, custom_output_dir = emitted[0]
    assert topic == "Space Odyssey"
    assert "money_chuck" in presets
    assert count == 2
    assert custom_output_dir == r"H:\Custom\Path"


def test_history_view(qapp):
    view = HistoryView()
    jobs = [{"id": "j1", "topic": "History 1", "preset": "history", "status": "COMPLETED", "created_at": "2026-09-20"}]
    view.update_history(jobs)
    assert view.table.rowCount() == 1

    view.set_preview_text("Generated script content...")
    assert view.preview_box.toPlainText() == "Generated script content..."


def test_presets_view(qapp):
    view = PresetsView()
    assert view.preset_list.count() >= 1

    # Just check that it has loaded at least one valid preset name
    first_item = view.preset_list.item(0).text()
    assert len(first_item) > 0

def test_settings_view(qapp, monkeypatch, tmp_path):
    monkeypatch.setattr("app.ui.views.settings_view.SETTINGS_FILE", tmp_path / "settings.json")
    view = SettingsView()
    # Check if a form element exists
    assert view.api_url_edit.text() is not None
    assert view.max_concurrent_spin.value() == 3

def test_main_window_wiring(qapp):
    event_bus = EventBus()
    window = MainWindow(event_bus=event_bus)

    # Check views exist
    assert window.dashboard_view is not None
    assert window.generate_view is not None
    assert window.history_view is not None
    assert window.presets_view is not None
    assert window.settings_view is not None

    # Verify the stack widget has 7 tabs
    assert window.stack.count() == 7
    assert window.presets_view is not None
    assert window.settings_view is not None

    # Check that StackedWidget has 7 tabs
    assert window.stack.count() == 7
    assert window.stack.widget(4) == window.presets_view
    assert window.stack.widget(5) == window.settings_view
    assert window.stack.widget(6) == window.logs_view

    # Simulate generation
    window.idea_manager.is_idea_generated = lambda t: False
    window.generate_view.topic_input.setText("Quantum Computing")
    if "money_chuck" in window.generate_view.preset_checkboxes:
        window.generate_view.preset_checkboxes["money_chuck"].setChecked(True)
    window.generate_view.start_btn.click()

    assert len(window.jobs_cache) >= 1
    assert window.dashboard_view.job_table.rowCount() >= 1
    window.close()
    if hasattr(window, "log_handler") and window.log_handler:
        logging.getLogger().removeHandler(window.log_handler)


def test_signaled_log_handler(qapp):
    handler = SignaledLogHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    received_logs = []
    handler.new_log.connect(received_logs.append)

    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Test log message")
    assert len(received_logs) == 1
    assert "INFO - Test log message" in received_logs[0]

    logger.removeHandler(handler)


def test_logs_view(qapp):
    view = LogsView()
    view.append_log("Log line 1")
    view.append_log("Log line 2")
    assert "Log line 1" in view.logs_text.toPlainText()
    assert "Log line 2" in view.logs_text.toPlainText()

    view.btn_clear.click()
    assert view.logs_text.toPlainText() == ""


def test_ui_feedback_generate_view(qapp):
    view = GenerateView()
    view.topic_input.setText("Topic")
    if "money_chuck" in view.preset_checkboxes:
        view.preset_checkboxes["money_chuck"].setChecked(True)
    view.start_btn.click()

    assert view.start_btn.text() == "Queuing..."
    assert not view.start_btn.isEnabled()

    view._reset_btn()
    assert view.start_btn.text() == "Start Initial Generation"
    assert view.start_btn.isEnabled()


def test_ui_feedback_settings_view(qapp):
    view = SettingsView()
    assert view.status_label.text() == ""

    view.btn_save.click()
    assert "Settings Saved" in view.status_label.text()


def test_ui_feedback_presets_view(qapp):
    view = PresetsView()
    assert view.status_label.text() == ""

    view.btn_save.click()
    assert "Preset Saved" in view.status_label.text()


def test_signaled_log_handler_and_logs_view(qapp):
    logs_view = LogsView()
    handler = SignaledLogHandler()
    handler.new_log.connect(logs_view.append_log)

    logger = logging.getLogger("test_logger")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Test log message 12345")
    assert "Test log message 12345" in logs_view.logs_text.toPlainText()

    logs_view.btn_clear.click()
    assert logs_view.logs_text.toPlainText() == ""
    logger.removeHandler(handler)


def test_ui_feedback_on_generate_button(qapp):
    view = GenerateView()
    view.topic_input.setText("Testing Feedback")
    if "money_chuck" in view.preset_checkboxes:
        view.preset_checkboxes["money_chuck"].setChecked(True)

    view.start_btn.click()
    assert view.start_btn.text() == "Queuing..."
    assert not view.start_btn.isEnabled()

    # Call reset directly
    view._reset_btn()
    assert view.start_btn.text() == "Start Initial Generation"
    assert view.start_btn.isEnabled()


def test_ui_feedback_on_settings_button(qapp):
    view = SettingsView()
    assert view.status_label.text() == ""

    view.btn_save.click()
    assert view.status_label.text() == "Settings Saved & Persisted!"


def test_ui_feedback_on_presets_button(qapp):
    view = PresetsView()
    assert view.status_label.text() == ""

    view.btn_save.click()
    assert view.status_label.text() == "Preset Saved."


def test_main_window_worker_concurrency_queue(qapp):
    from PySide6.QtCore import QThread
    from unittest.mock import MagicMock

    event_bus = EventBus()
    window = MainWindow(event_bus=event_bus)
    window.settings_view.max_concurrent_spin.setValue(2)

    class DummyWorker(QThread):
        def run(self):
            pass

    workers = [DummyWorker() for _ in range(5)]
    for w in workers:
        w.start = MagicMock()

    for idx, w in enumerate(workers):
        job_id = f"test-job-{idx}"
        job_data = {"id": job_id, "topic": f"Topic {idx}", "preset": "test", "status": "PENDING"}
        window._enqueue_worker(job_id, w, job_data)

    # Max concurrent is 2, so exactly 2 should be running and 3 queued
    assert len(window._running_workers) == 2
    assert len(window._worker_queue) == 3

    # Check statuses in jobs_cache
    running_jobs = [j for j in window.jobs_cache if j.get("status") == "RUNNING"]
    queued_jobs = [j for j in window.jobs_cache if j.get("status") == "QUEUED"]
    assert len(running_jobs) == 2
    assert len(queued_jobs) == 3

    # Finish one running job
    first_running_id = list(window._running_workers.keys())[0]
    window._on_worker_finished(first_running_id, {"title": "T", "script": "S", "output_path": "P"})

    # Next job in queue should have started automatically: running count stays 2, queue count drops to 2
    assert len(window._running_workers) == 2
    assert len(window._worker_queue) == 2
    window.close()
    if hasattr(window, "log_handler") and window.log_handler:
        logging.getLogger().removeHandler(window.log_handler)


