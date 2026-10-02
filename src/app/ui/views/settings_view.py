from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFileDialog,
    QGroupBox
)
from PySide6.QtCore import Qt, QTimer
import os
import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".content_automation" / "settings.json"


class SettingsView(QWidget):
    """
    A view to configure application settings and persist them to disk.
    """
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Settings")
        title.setObjectName("h1")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form
        group_box = QGroupBox("Configuration")
        form_layout = QFormLayout(group_box)
        form_layout.setSpacing(15)

        # API Base URL
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setText("https://api.anthropic.com")
        form_layout.addRow("API Base URL:", self.api_url_edit)

        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter API Key")
        form_layout.addRow("API Key:", self.api_key_edit)

        # Model Name
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setText("claude-3-haiku-20240307")
        form_layout.addRow("Model Name:", self.model_name_edit)

        # Max Concurrent API Requests
        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 20)
        self.max_concurrent_spin.setValue(3)
        self.max_concurrent_spin.setToolTip("Maximum simultaneous requests allowed to prevent API rate limiting.")
        form_layout.addRow("Max Concurrent Requests:", self.max_concurrent_spin)

        # Output Directory
        out_dir_layout = QHBoxLayout()
        self.out_dir_edit = QLineEdit()
        self.out_dir_edit.setText(r"H:\Automation\output")

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_directory)

        out_dir_layout.addWidget(self.out_dir_edit)
        out_dir_layout.addWidget(self.btn_browse)

        form_layout.addRow("Global Output Directory:", out_dir_layout)

        layout.addWidget(group_box)

        # Save Button & Status Label
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6e3a1; font-weight: bold; margin-right: 10px;")
        btn_layout.addWidget(self.status_label)

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setObjectName("primary_button")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        layout.addLayout(btn_layout)
        layout.addStretch()

    def _browse_directory(self):
        """Open a folder dialog to select the output directory"""
        start_dir = self.out_dir_edit.text() if os.path.exists(self.out_dir_edit.text()) else r"H:\Automation\output"
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", start_dir)
        if directory:
            self.out_dir_edit.setText(directory)

    def load_settings(self):
        """Load settings from JSON file on disk."""
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if "base_url" in data:
                    self.api_url_edit.setText(data["base_url"])
                if "api_key" in data:
                    self.api_key_edit.setText(data["api_key"])
                if "model" in data:
                    self.model_name_edit.setText(data["model"])
                if "output_dir" in data:
                    self.out_dir_edit.setText(data["output_dir"])
                if "max_concurrent_requests" in data:
                    self.max_concurrent_spin.setValue(int(data["max_concurrent_requests"]))
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save settings to JSON file on disk."""
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "base_url": self.api_url_edit.text().strip(),
                "api_key": self.api_key_edit.text().strip(),
                "model": self.model_name_edit.text().strip(),
                "output_dir": self.out_dir_edit.text().strip() or r"H:\Automation\output",
                "max_concurrent_requests": self.max_concurrent_spin.value()
            }
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def _on_save_clicked(self):
        success = self.save_settings()
        if success:
            self.status_label.setText("Settings Saved & Persisted!")
        else:
            self.status_label.setText("Error saving settings")
        QTimer.singleShot(3000, self.status_label.clear)
