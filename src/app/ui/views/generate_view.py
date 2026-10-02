from typing import List, Dict, Any
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QPushButton,
    QFormLayout,
    QFrame,
    QFileDialog,
    QScrollArea,
    QGridLayout,
    QMessageBox,
    QGroupBox
)
from PySide6.QtCore import Signal, QTimer

from app.models.preset import BUILTIN_PRESETS


class GenerateView(QWidget):
    """
    Generate view for configuring and launching content generation batches & 2nd round prompt generation.
    """

    start_generation_requested = Signal(str, list, int, str, bool)  # topic, list of presets, count, custom_output_dir, generate_prompts
    generate_prompts_for_folders_requested = Signal(list)  # list of folder path strings to generate prompts for
    start_generation = start_generation_requested  # Alias for compatibility

    def __init__(self, parent=None):
        super().__init__(parent)
        self.preset_checkboxes: Dict[str, QCheckBox] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("Generate Content")
        header.setObjectName("header")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

        # ── SECTION 1: Round 1 Initial Generation (Topic -> Title & Script) ──
        form_card = QGroupBox("Round 1: Topic to Script Generation")
        form_card.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(16)

        # Topic
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("Enter topic concept (e.g. Ancient Rome, AI Ethics, Cyberpunk City)")
        form_layout.addRow("Topic:", self.topic_input)

        # Dynamic Preset Checkboxes inside a Scrollable Grid
        presets_scroll = QScrollArea()
        presets_scroll.setWidgetResizable(True)
        presets_scroll.setMaximumHeight(140)
        presets_scroll.setFrameShape(QFrame.NoFrame)

        presets_widget = QWidget()
        presets_grid = QGridLayout(presets_widget)
        presets_grid.setContentsMargins(4, 4, 4, 4)
        presets_grid.setSpacing(10)

        # Populate with all BUILTIN_PRESETS
        row, col = 0, 0
        for slug, preset_obj in BUILTIN_PRESETS.items():
            display_title = slug.replace("_", " ").title()
            cb = QCheckBox(display_title)
            if slug == "money_chuck":
                self.cb_money_chuck = cb
            if slug == "money_chuck":
                cb.setChecked(True)
            self.preset_checkboxes[slug] = cb
            presets_grid.addWidget(cb, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        presets_scroll.setWidget(presets_widget)
        form_layout.addRow("Select Presets:", presets_scroll)

        # Items per preset SpinBox
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(1)
        form_layout.addRow("Items per Preset:", self.count_spin)

        # Stage Options
        self.cb_generate_prompts = QCheckBox("Include Image Prompts Now (Uncheck if doing TTS first)")
        self.cb_generate_prompts.setChecked(False)  # Default unchecked per 2-phase contract
        form_layout.addRow("Prompt Stage:", self.cb_generate_prompts)

        # Output Directory
        out_dir_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(r"H:\Automation\output")
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._on_browse_output_dir)
        out_dir_layout.addWidget(self.output_dir_input)
        out_dir_layout.addWidget(self.btn_browse)
        form_layout.addRow("Output Directory:", out_dir_layout)

        # Start Round 1 Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.start_btn = QPushButton("Start Initial Generation")
        self.start_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 18px;")
        self.start_btn.clicked.connect(self._on_start_clicked)
        btn_row.addWidget(self.start_btn)
        form_layout.addRow("", btn_row)

        layout.addWidget(form_card)

        # ── SECTION 2: Round 2 Prompt Generation (Selected Project Folders -> Prompts) ──
        round2_card = QGroupBox("Round 2: Generate Audio-Aligned Image Prompts for Project Folders")
        round2_card.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; margin-top: 10px; }")
        round2_layout = QVBoxLayout(round2_card)
        round2_layout.setContentsMargins(20, 20, 20, 20)
        round2_layout.setSpacing(12)

        desc_lbl = QLabel("Select or paste project folders (containing script.txt and metadata.json) after TTS transcription to generate audio-synced scene image prompts:")
        desc_lbl.setStyleSheet("font-weight: normal; color: #a6adc8; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        round2_layout.addWidget(desc_lbl)

        round2_btn_row = QHBoxLayout()

        self.btn_select_folders = QPushButton("📁  Select Project Folder(s)...")
        self.btn_select_folders.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px 20px; background-color: #89b4fa; color: #11111b;")
        self.btn_select_folders.clicked.connect(self._on_select_project_folders)

        round2_btn_row.addWidget(self.btn_select_folders)
        round2_btn_row.addStretch()
        round2_layout.addLayout(round2_btn_row)

        layout.addWidget(round2_card)
        layout.addStretch()

    def _on_browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_dir_input.text() or r"H:\Automation\output"
        )
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def _on_start_clicked(self):
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "Missing Topic", "Please enter a topic before starting generation.")
            return

        presets = [slug for slug, cb in self.preset_checkboxes.items() if cb.isChecked()]
        if not presets:
            QMessageBox.warning(self, "No Preset Selected", "Please select at least one preset checkbox.")
            return

        count = self.count_spin.value()
        custom_output_dir = self.output_dir_input.text().strip()
        generate_prompts = self.cb_generate_prompts.isChecked()

        self.start_generation_requested.emit(topic, presets, count, custom_output_dir, generate_prompts)
        self.topic_input.clear()

        # Provide visual feedback
        self.start_btn.setText("Queuing...")
        self.start_btn.setEnabled(False)
        QTimer.singleShot(1000, self._reset_btn)

    def _reset_btn(self):
        self.start_btn.setText("Start Initial Generation")
        self.start_btn.setEnabled(True)

    def _on_select_project_folders(self):
        """Open dialog allowing user to select one or multiple project folders for 2nd round prompt generation."""
        output_base = self.output_dir_input.text().strip() or r"H:\Automation\output"

        # Open directory browser dialog
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setDirectory(output_base)
        dialog.setWindowTitle("Select Project Folder for Image Prompt Generation")

        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                valid_folders = []
                for folder_str in selected_dirs:
                    f = Path(folder_str)
                    if (f / "script.txt").exists():
                        valid_folders.append(str(f))
                    else:
                        QMessageBox.warning(self, "Invalid Folder", f"The folder '{f.name}' does not contain script.txt.")

                if valid_folders:
                    self.generate_prompts_for_folders_requested.emit(valid_folders)
                    QMessageBox.information(self, "Queued for Prompts", f"Queued {len(valid_folders)} project folder(s) for audio-synchronized image prompt generation!")
