from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QButtonGroup,
    QLabel
)
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.generate_view import GenerateView
from app.ui.views.history_view import HistoryView
from app.ui.views.presets_view import PresetsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.logs_view import LogsView
from app.ui.components.log_handler import SignaledLogHandler
from app.ui.styles.theme import DARK_THEME
from app.orchestrator.event_bus import EventBus
from app.pipeline.pipeline import GenerationPipeline
from app.models.preset import ContentPreset
from app.models.api_profile import APIProfile, RequestConfig
from app.ai.client import AnthropicClient
from app.storage.exporter import ContentExporter
from app.orchestrator.folder_prompt_worker import FolderPromptWorker

import uuid
import datetime
import logging
import asyncio
import os

logger = logging.getLogger(__name__)

class EventBusBridge(QObject):
    """
    Bridge that listens to EventBus events and forwards them as Qt Signals
    to be safely handled on the Qt GUI thread.
    """
    job_updated = Signal(dict)
    job_completed = Signal(dict)
    job_failed = Signal(dict)

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self._register_listeners()

    def _register_listeners(self):
        self.event_bus.subscribe("job_started", self._on_job_event)
        self.event_bus.subscribe("job_progress", self._on_job_event)
        self.event_bus.subscribe("job_completed", self._on_job_completed)
        self.event_bus.subscribe("job_failed", self._on_job_failed)

    def _on_job_event(self, data):
        self.job_updated.emit(data if isinstance(data, dict) else {"id": str(data)})

    def _on_job_completed(self, data):
        self.job_completed.emit(data if isinstance(data, dict) else {"id": str(data)})

    def _on_job_failed(self, data):
        self.job_failed.emit(data if isinstance(data, dict) else {"id": str(data)})


class PipelineWorker(QThread):
    """
    Asynchronously executes generation pipeline runs without freezing the PySide6 UI thread.
    """
    finished_signal = Signal(dict)
    failed_signal = Signal(str, str)

    def __init__(self, topic: str, preset_name: str, settings_data: dict, custom_output_dir: str = "", generate_prompts: bool = False, parent=None):
        super().__init__(parent)
        self.topic = topic
        self.preset_name = preset_name
        self.settings_data = settings_data
        self.custom_output_dir = custom_output_dir
        self.generate_prompts = generate_prompts

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()

    async def _async_run(self):
        try:
            # 1. Setup API Client from user Settings
            max_concurrent = self.settings_data.get("max_concurrent_requests", 3)
            request_config = RequestConfig(max_concurrent_requests=max_concurrent)

            api_key_str = self.settings_data.get("api_key", "").strip() or "sk-dummy-key-for-local-testing"
            profile = APIProfile(
                name="runtime_profile",
                base_url=self.settings_data.get("base_url", "https://api.anthropic.com"),
                api_key=api_key_str,
                model=self.settings_data.get("model", "claude-3-haiku-20240307"),
                config=request_config
            )
            ai_client = AnthropicClient(profile)

            # 2. Setup preset
            fallback_dir = self.settings_data.get("output_dir", "output")
            effective_output_dir = self.custom_output_dir.strip() if self.custom_output_dir else fallback_dir

            preset = ContentPreset(
                name=self.preset_name,
                output_dir=effective_output_dir
            )

            # 3. Instantiate and run pipeline
            pipeline = GenerationPipeline()
            pipeline.title_stage.ai = ai_client
            pipeline.script_stage.ai = ai_client
            pipeline.scene_stage.ai = ai_client
            pipeline.image_prompt_stage.ai = ai_client
            pipeline.final_review_stage.ai = ai_client

            logger.info(f"Starting real generation pipeline for topic: '{self.topic}' with preset '{self.preset_name}' (generate_prompts={self.generate_prompts})...")
            package = await pipeline.run(topic=self.topic, preset=preset, generate_prompts=self.generate_prompts)

            # 4. Export the clean files (title.txt, script.txt, metadata.json, and conditionally prompts.txt)
            exported_path = ContentExporter.export_package(
                package=package,
                base_output_dir=effective_output_dir,
                preset=preset
            )
            logger.info(f"Successfully generated and exported content to disk at: {exported_path}")

            result_payload = {
                "topic": self.topic,
                "preset": self.preset_name,
                "title": package.title,
                "script": package.script,
                "output_path": exported_path,
                "status": "COMPLETED"
            }
            self.finished_signal.emit(result_payload)

        except Exception as e:
            logger.exception(f"Pipeline generation failed for topic '{self.topic}': {e}")
            self.failed_signal.emit(self.topic, str(e))


class MainWindow(QMainWindow):
    """
    Main Application Window with Sidebar navigation, Stacked View,
    and EventBus integration for live UI updates.
    """

    def __init__(self, event_bus: EventBus = None):
        super().__init__()
        self.setWindowTitle("Content Automation Pipeline")
        self.resize(1100, 750)
        self.setStyleSheet(DARK_THEME)

        self.event_bus = event_bus or EventBus()
        self.bridge = EventBusBridge(self.event_bus)

        self.jobs_cache = []
        self._active_workers = []

        self._setup_ui()
        self._wire_signals()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Sidebar Navigation
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #181825;")

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 24, 12, 24)
        sidebar_layout.setSpacing(8)

        # App Title
        app_title = QLabel("AI Studio")
        app_title.setObjectName("header")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addSpacing(20)

        # Nav Buttons
        self.btn_nav_dashboard = QPushButton("Dashboard")
        self.btn_nav_dashboard.setObjectName("nav_button")
        self.btn_nav_dashboard.setCheckable(True)
        self.btn_nav_dashboard.setChecked(True)

        self.btn_nav_generate = QPushButton("Generate")
        self.btn_nav_generate.setObjectName("nav_button")
        self.btn_nav_generate.setCheckable(True)

        self.btn_nav_history = QPushButton("History")
        self.btn_nav_history.setObjectName("nav_button")
        self.btn_nav_history.setCheckable(True)

        self.btn_nav_presets = QPushButton("Presets")
        self.btn_nav_presets.setObjectName("nav_button")
        self.btn_nav_presets.setCheckable(True)

        self.btn_nav_settings = QPushButton("Settings")
        self.btn_nav_settings.setObjectName("nav_button")
        self.btn_nav_settings.setCheckable(True)

        self.btn_nav_logs = QPushButton("Logs")
        self.btn_nav_logs.setObjectName("nav_button")
        self.btn_nav_logs.setCheckable(True)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.addButton(self.btn_nav_dashboard, 0)
        self.nav_group.addButton(self.btn_nav_generate, 1)
        self.nav_group.addButton(self.btn_nav_history, 2)
        self.nav_group.addButton(self.btn_nav_presets, 3)
        self.nav_group.addButton(self.btn_nav_settings, 4)
        self.nav_group.addButton(self.btn_nav_logs, 5)

        sidebar_layout.addWidget(self.btn_nav_dashboard)
        sidebar_layout.addWidget(self.btn_nav_generate)
        sidebar_layout.addWidget(self.btn_nav_history)
        sidebar_layout.addWidget(self.btn_nav_presets)
        sidebar_layout.addWidget(self.btn_nav_settings)
        sidebar_layout.addWidget(self.btn_nav_logs)
        sidebar_layout.addStretch()

        main_layout.addWidget(sidebar)

        # Right Content Area (QStackedWidget)
        self.stack = QStackedWidget()

        self.dashboard_view = DashboardView()
        self.generate_view = GenerateView()
        self.history_view = HistoryView()
        self.presets_view = PresetsView()
        self.settings_view = SettingsView()
        self.logs_view = LogsView()

        self.stack.addWidget(self.dashboard_view)  # 0
        self.stack.addWidget(self.generate_view)   # 1
        self.stack.addWidget(self.history_view)    # 2
        self.stack.addWidget(self.presets_view)    # 3
        self.stack.addWidget(self.settings_view)   # 4
        self.stack.addWidget(self.logs_view)       # 5

        main_layout.addWidget(self.stack)

        # Set up logging handler
        self.log_handler = SignaledLogHandler()
        self.log_handler.new_log.connect(self.logs_view.append_log)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def _wire_signals(self):
        # Navigation
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        # Dashboard refresh
        self.dashboard_view.refresh_clicked.connect(self._refresh_dashboard)

        # Generate action -> start worker thread
        self.generate_view.start_generation_requested.connect(self._handle_start_generation)
        self.generate_view.generate_prompts_for_folders_requested.connect(self._handle_generate_prompts_for_folders)

        # History item selected
        self.history_view.job_selected.connect(self._handle_history_job_selected)

        # Bridge event bus signals to UI slots
        self.bridge.job_updated.connect(self._on_job_updated)
        self.bridge.job_completed.connect(self._on_job_completed)
        self.bridge.job_failed.connect(self._on_job_failed)

    def _get_current_settings(self) -> dict:
        """Extracts settings configured in SettingsView."""
        return {
            "base_url": self.settings_view.api_url_edit.text().strip(),
            "api_key": self.settings_view.api_key_edit.text().strip(),
            "model": self.settings_view.model_name_edit.text().strip(),
            "output_dir": self.settings_view.out_dir_edit.text().strip() or "output",
            "max_concurrent_requests": self.settings_view.max_concurrent_spin.value()
        }

    def _handle_generate_prompts_for_folders(self, folder_paths: list):
        """Handle execution of Round 2: Generating Image Prompts for existing Project Folders"""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        settings_data = self._get_current_settings()

        for folder_path in folder_paths:
            job_id = f"job-prmpt-{uuid.uuid4().hex[:6]}"
            folder_name = os.path.basename(folder_path)
            job_data = {
                "id": job_id,
                "topic": f"Round 2 Prompts: {folder_name}",
                "preset": "auto-match",
                "status": "RUNNING",
                "created_at": now_str,
                "output": f"Executing Round 2 Image Prompts Generation for folder '{folder_name}'..."
            }
            self.jobs_cache.insert(0, job_data)
            self.event_bus.publish_sync("job_started", job_data)

            # Launch async folder prompt worker
            worker = FolderPromptWorker(
                folder_path=folder_path,
                settings_data=settings_data,
                parent=self
            )
            worker.finished_signal.connect(lambda folder, res, j_id=job_id: self._on_worker_finished(j_id, res))
            worker.failed_signal.connect(lambda folder, err, j_id=job_id: self._on_worker_failed(j_id, folder, err))
            self._active_workers.append(worker)
            worker.start()

        self._refresh_dashboard()

    def _handle_start_generation(self, topic: str, presets: list, count: int, custom_output_dir: str = "", generate_prompts: bool = False):
        """Handle real generation request and launch non-blocking worker threads."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        settings_data = self._get_current_settings()

        for preset in presets:
            for _ in range(count):
                job_id = f"job-{uuid.uuid4().hex[:6]}"
                job_data = {
                    "id": job_id,
                    "topic": topic,
                    "preset": preset,
                    "status": "RUNNING",
                    "created_at": now_str,
                    "output": f"Executing generation pipeline for '{topic}' under '{preset}'..."
                }
                self.jobs_cache.insert(0, job_data)
                self.event_bus.publish_sync("job_started", job_data)

                # Launch async pipeline worker
                worker = PipelineWorker(
                    topic=topic,
                    preset_name=preset,
                    settings_data=settings_data,
                    custom_output_dir=custom_output_dir,
                    generate_prompts=generate_prompts,
                    parent=self
                )
                worker.finished_signal.connect(lambda res, j_id=job_id: self._on_worker_finished(j_id, res))
                worker.failed_signal.connect(lambda t, err, j_id=job_id: self._on_worker_failed(j_id, t, err))
                self._active_workers.append(worker)
                worker.start()

        self._refresh_dashboard()

    def _handle_generate_prompts_for_folders(self, folder_paths: list):
        """Handle execution of Round 2: Generating Image Prompts for existing Project Folders"""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        settings_data = self._get_current_settings()

        for folder_path in folder_paths:
            job_id = f"job-prmpt-{uuid.uuid4().hex[:6]}"
            folder_name = os.path.basename(folder_path)
            job_data = {
                "id": job_id,
                "topic": f"Round 2 Prompts: {folder_name}",
                "preset": "auto-match",
                "status": "RUNNING",
                "created_at": now_str,
                "output": f"Executing Round 2 Image Prompts Generation for folder '{folder_name}'..."
            }
            self.jobs_cache.insert(0, job_data)
            self.event_bus.publish_sync("job_started", job_data)

            # Launch async folder prompt worker
            worker = FolderPromptWorker(
                folder_path=folder_path,
                settings_data=settings_data,
                parent=self
            )
            worker.finished_signal.connect(lambda folder, res, j_id=job_id: self._on_worker_finished(j_id, res))
            worker.failed_signal.connect(lambda folder, err, j_id=job_id: self._on_worker_failed(j_id, folder, err))
            self._active_workers.append(worker)
            worker.start()

        self._refresh_dashboard()

    def _on_worker_finished(self, job_id: str, result_payload: dict):
        output_text = f"Title: {result_payload.get('title')}\n\nScript:\n{result_payload.get('script')}\n\nExported to folder:\n{result_payload.get('output_path')}"
        job_data = {
            "id": job_id,
            "status": "COMPLETED",
            "output": output_text
        }
        self.event_bus.publish_sync("job_completed", job_data)

    def _on_worker_failed(self, job_id: str, topic: str, error_msg: str):
        job_data = {
            "id": job_id,
            "status": "FAILED",
            "output": f"Error during generation: {error_msg}"
        }
        self.event_bus.publish_sync("job_failed", job_data)

    def _refresh_dashboard(self):
        """Update metrics and jobs table on the dashboard."""
        total = len(self.jobs_cache)
        success = len([j for j in self.jobs_cache if j.get("status") == "COMPLETED"])
        failed = len([j for j in self.jobs_cache if j.get("status") == "FAILED"])

        self.dashboard_view.update_metrics(total, success, failed)
        self.dashboard_view.update_jobs(self.jobs_cache)

        completed_jobs = [j for j in self.jobs_cache if j.get("status") == "COMPLETED"]
        self.history_view.update_history(completed_jobs)

    def _handle_history_job_selected(self, job_id: str):
        """Show preview text when history item is selected."""
        for j in self.jobs_cache:
            if j.get("id") == job_id:
                self.history_view.set_preview_text(j.get("output", "No output available."))
                return

    @Slot(dict)
    def _on_job_updated(self, job_data: dict):
        self._update_cached_job(job_data)
        self.dashboard_view.job_table.update_or_add_job(job_data)

    @Slot(dict)
    def _on_job_completed(self, job_data: dict):
        self._update_cached_job(job_data)
        self.dashboard_view.job_table.update_or_add_job(job_data)
        self._refresh_dashboard()

    @Slot(dict)
    def _on_job_failed(self, job_data: dict):
        self._update_cached_job(job_data)
        self.dashboard_view.job_table.update_or_add_job(job_data)
        self._refresh_dashboard()

    def _update_cached_job(self, job_data: dict):
        job_id = job_data.get("id")
        for idx, j in enumerate(self.jobs_cache):
            if j.get("id") == job_id:
                self.jobs_cache[idx].update(job_data)
                return
        self.jobs_cache.insert(0, job_data)
