from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QSplitter,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer

from app.models.preset import BUILTIN_PRESETS, ContentPreset


class PresetsView(QWidget):
    """
    A view to see and inspect presets dynamically loaded from BUILTIN_PRESETS.
    Left side: List of presets
    Right side: Form showing preset settings
    """
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Presets Management")
        title.setObjectName("h1")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Splitter to separate list and form
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: List of presets
        self.preset_list = QListWidget()
        for p_name in sorted(BUILTIN_PRESETS.keys()):
            self.preset_list.addItem(p_name)
        splitter.addWidget(self.preset_list)

        # Right side: Edit form
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)

        self.form = QFormLayout()

        self.name_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)

        self.voice_edit = QLineEdit()
        self.language_edit = QLineEdit()

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 3600)
        self.duration_spin.setSuffix(" seconds")
        self.duration_spin.setValue(60)

        self.quality_score_spin = QDoubleSpinBox()
        self.quality_score_spin.setRange(0.0, 10.0)
        self.quality_score_spin.setSingleStep(0.1)
        self.quality_score_spin.setValue(8.5)

        self.hook_style_combo = QComboBox()
        self.hook_style_combo.addItems(["Curiosity", "Question", "Statement", "Story", "Statistic"])

        self.visual_style_edit = QTextEdit()
        self.visual_style_edit.setMaximumHeight(80)

        self.form.addRow("Preset Name:", self.name_edit)
        self.form.addRow("Description:", self.desc_edit)
        self.form.addRow("TTS Voice Name:", self.voice_edit)
        self.form.addRow("Language:", self.language_edit)
        self.form.addRow("Target Duration:", self.duration_spin)
        self.form.addRow("Min Quality Score:", self.quality_score_spin)
        self.form.addRow("Hook Style:", self.hook_style_combo)
        self.form.addRow("Visual Style (Image Auto):", self.visual_style_edit)

        form_layout.addLayout(self.form)

        # Form buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Preset")
        self.btn_save.setObjectName("primary_button")
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_new = QPushButton("New Preset")

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6e3a1; font-weight: bold; margin-right: 10px;")

        btn_layout.addWidget(self.btn_new)
        btn_layout.addStretch()
        btn_layout.addWidget(self.status_label)
        btn_layout.addWidget(self.btn_save)

        form_layout.addLayout(btn_layout)
        form_layout.addStretch()

        splitter.addWidget(form_widget)

        # Set splitter sizes
        splitter.setSizes([260, 540])

        layout.addWidget(splitter)

        # Connections
        self.preset_list.itemClicked.connect(self._on_preset_selected)

        # Initialize with first item if any
        if self.preset_list.count() > 0:
            self.preset_list.setCurrentRow(0)
            self._on_preset_selected(self.preset_list.item(0))

    def _on_save_clicked(self):
        self.status_label.setText("Preset Saved.")
        QTimer.singleShot(3000, self.status_label.clear)

    def _on_preset_selected(self, item):
        """Populate the form based on selected list item"""
        if not item:
            return
        slug = item.text()
        self.name_edit.setText(slug)

        if slug in BUILTIN_PRESETS:
            p: ContentPreset = BUILTIN_PRESETS[slug]
            self.desc_edit.setText(p.description)
            self.voice_edit.setText(p.voice_name)
            self.language_edit.setText(p.video_language)
            self.duration_spin.setValue(p.script_rules.target_duration_minutes * 60)
            self.quality_score_spin.setValue(p.reviewer_rules.min_quality_score)
            self.visual_style_edit.setText(p.image_rules.visual_style)
        else:
            self.desc_edit.setText("Custom user preset")
            self.voice_edit.setText("Adam   ·  American Male")
            self.language_edit.setText("English")
            self.duration_spin.setValue(600)
            self.quality_score_spin.setValue(8.5)
            self.visual_style_edit.setText("")
