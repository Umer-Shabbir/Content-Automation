DARK_THEME = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 14px;
}

/* Sidebar / Left Navigation */
QDockWidget {
    background-color: #181825;
    color: #cdd6f4;
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
}

QDockWidget::title {
    background-color: #11111b;
    padding: 8px;
    font-weight: bold;
}

/* Sidebar Buttons */
QPushButton#nav_button {
    background-color: #181825;
    color: #cdd6f4;
    border: none;
    padding: 12px 16px;
    text-align: left;
    font-size: 15px;
    margin: 2px 0px;
    border-left: 4px solid transparent;
}

QPushButton#nav_button:hover {
    background-color: #313244;
}

QPushButton#nav_button:checked {
    background-color: #313244;
    border-left: 4px solid #89b4fa;
    color: #89b4fa;
    font-weight: bold;
}

/* Specific elements */
QLabel#header {
    font-size: 24px;
    font-weight: bold;
    color: #89b4fa;
    padding: 10px 0;
}

QLabel#subheader {
    font-size: 18px;
    font-weight: bold;
    color: #b4befe;
    padding: 5px 0;
}

/* Input Fields */
QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}

/* Action Buttons */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #74c7ec;
}

QPushButton:pressed {
    background-color: #89dceb;
}

QPushButton:disabled {
    background-color: #45475a;
    color: #a6adc8;
}

QPushButton#btn_secondary {
    background-color: #45475a;
    color: #cdd6f4;
}

QPushButton#btn_secondary:hover {
    background-color: #585b70;
}

QPushButton#btn_danger {
    background-color: #f38ba8;
    color: #1e1e2e;
}

QPushButton#btn_danger:hover {
    background-color: #eba0ac;
}

/* Metric Cards */
QFrame#metric_card {
    background-color: #181825;
    border-radius: 8px;
    border: 1px solid #313244;
    padding: 16px;
}

QLabel#metric_title {
    font-size: 14px;
    color: #bac2de;
}

QLabel#metric_value {
    font-size: 32px;
    font-weight: bold;
    color: #89b4fa;
}

/* Tables */
QTableWidget {
    background-color: #1e1e2e;
    alternate-background-color: #181825;
    border: 1px solid #313244;
    border-radius: 4px;
    color: #cdd6f4;
    gridline-color: #313244;
    selection-background-color: #313244;
    selection-color: #cdd6f4;
}

QHeaderView::section {
    background-color: #11111b;
    color: #bac2de;
    padding: 8px;
    border: 1px solid #313244;
    border-top: none;
    border-left: none;
    font-weight: bold;
}

QTableWidget::item {
    padding: 4px 8px;
}

QTableWidget::item:selected {
    background-color: #313244;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #1e1e2e;
    width: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background-color: #45475a;
    min-height: 20px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #1e1e2e;
    height: 12px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background-color: #45475a;
    min-width: 20px;
    border-radius: 6px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #585b70;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}

QCheckBox::indicator:hover {
    border: 1px solid #89b4fa;
}

QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
}
"""