import sys
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QProgressBar, QScrollArea, QCheckBox, QMessageBox, QFrame,
    QTextEdit, QLineEdit, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QPixmap, QFont, QColor, QPainter, QPen, QLinearGradient, QBrush, QPalette
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QPoint

from chatbot import ChatBot


# ================= HASH FUNCTION =================
def get_hash(file):
    sha = hashlib.sha256()
    try:
        with open(file, 'rb') as f:
            while chunk := f.read(65536):
                sha.update(chunk)
    except Exception:
        return None
    return sha.hexdigest()


# ================= THREAD =================
class ScanThread(QThread):
    progress_update = pyqtSignal(int)
    scan_complete = pyqtSignal(list)

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        seen = {}
        duplicates = []
        total = len(self.files)
        count = 0
        lock = Lock()

        def process(f):
            return f, get_hash(f)

        with ThreadPoolExecutor(max_workers=8) as executor:
            for file, h in executor.map(process, self.files):
                with lock:
                    count += 1
                    self.progress_update.emit(int((count / total) * 100))
                if h:
                    if h in seen:
                        duplicates.append((file, seen[h]))
                    else:
                        seen[h] = file

        self.scan_complete.emit(duplicates)


# ================= GLOW BUTTON =================
class GlowButton(QPushButton):
    def __init__(self, text, accent_color="#00d4ff", parent=None):
        super().__init__(text, parent)
        self.accent = accent_color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)
        self._apply_style(False)
        self.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

    def _apply_style(self, hovered):
        bg = self.accent if hovered else "transparent"
        text_color = "#0a0a14" if hovered else self.accent
        border = self.accent
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 10px 20px;
                font-family: 'Segoe UI';
                font-size: 10pt;
                font-weight: bold;
                letter-spacing: 0px;
            }}
        """)

    def enterEvent(self, e):
        self._apply_style(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._apply_style(False)
        super().leaveEvent(e)


# ================= STAT CARD =================
class StatCard(QFrame):
    def __init__(self, label, value="0", accent="#00d4ff"):
        super().__init__()
        self.accent = accent
        self.setMinimumHeight(90)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #12122a;
                border: 1px solid {accent}55;
                border-left: 4px solid {accent};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Label on top — large, bright, always visible
        self.lbl = QLabel(label)
        self.lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl.setStyleSheet(
            "color: #dde6ff;"
            "border: none;"
            "background: transparent;"
        )

        # Big value number below
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.value_label.setStyleSheet(
            f"color: {accent};"
            "border: none;"
            "background: transparent;"
        )

        layout.addWidget(self.lbl)
        layout.addWidget(self.value_label)

    def set_value(self, val):
        self.value_label.setText(str(val))


# ================= DUPLICATE CARD =================
class DuplicateCard(QFrame):
    def __init__(self, dup_path, orig_path, dup_size, orig_size, format_size_fn):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #1e1e3a;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QFrame:hover {
                border-color: #00d4ff33;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Checkbox column
        cb_col = QVBoxLayout()
        cb_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border: 1px solid #00d4ff;
                border-radius: 2px;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #00d4ff;
                image: none;
            }
        """)
        cb_col.addWidget(self.checkbox)
        layout.addLayout(cb_col)

        # File info column
        info_col = QVBoxLayout()
        info_col.setSpacing(6)

        dup_row = QHBoxLayout()
        dup_icon = QLabel("◈")
        dup_icon.setStyleSheet("color: #ff4d6d; font-size: 10pt; background: transparent; border: none;")
        dup_label_tag = QLabel("  Duplicate  ")
        dup_label_tag.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        dup_label_tag.setStyleSheet("""
            color: #ff4d6d;
            background-color: #ff4d6d18;
            border: 1px solid #ff4d6d44;
            border-radius: 2px;
            padding: 1px 6px;
            letter-spacing: 2px;
        """)
        dup_row.addWidget(dup_icon)
        dup_row.addWidget(dup_label_tag)
        dup_row.addStretch()
        info_col.addLayout(dup_row)

        dup_path_label = QLabel(dup_path)
        dup_path_label.setFont(QFont("Segoe UI", 9))
        dup_path_label.setStyleSheet("color: #ccd6f6; border: none; background: transparent;")
        dup_path_label.setWordWrap(True)
        info_col.addWidget(dup_path_label)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1e1e3a; border: none;")
        info_col.addWidget(sep)

        orig_row = QHBoxLayout()
        orig_icon = QLabel("◉")
        orig_icon.setStyleSheet("color: #00ffaa; font-size: 10pt; background: transparent; border: none;")
        orig_label_tag = QLabel("  Original  ")
        orig_label_tag.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        orig_label_tag.setStyleSheet("""
            color: #00ffaa;
            background-color: #00ffaa18;
            border: 1px solid #00ffaa44;
            border-radius: 2px;
            padding: 1px 6px;
            letter-spacing: 2px;
        """)
        orig_row.addWidget(orig_icon)
        orig_row.addWidget(orig_label_tag)
        orig_row.addStretch()
        info_col.addLayout(orig_row)

        orig_path_label = QLabel(orig_path)
        orig_path_label.setFont(QFont("Segoe UI", 9))
        orig_path_label.setStyleSheet("color: #8892b0; border: none; background: transparent;")
        orig_path_label.setWordWrap(True)
        info_col.addWidget(orig_path_label)

        layout.addLayout(info_col, 1)

        # Size column
        size_col = QVBoxLayout()
        size_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        size_col.setSpacing(8)

        dup_size_lbl = QLabel(format_size_fn(dup_size))
        dup_size_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        dup_size_lbl.setStyleSheet("color: #ff4d6d; border: none; background: transparent;")
        dup_size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        orig_size_lbl = QLabel(format_size_fn(orig_size))
        orig_size_lbl.setFont(QFont("Segoe UI", 11))
        orig_size_lbl.setStyleSheet("color: #556677; border: none; background: transparent;")
        orig_size_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        size_col.addWidget(dup_size_lbl)
        size_col.addWidget(orig_size_lbl)
        layout.addLayout(size_col)

        # Thumbnail (if image)
        if dup_path.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                pix = QPixmap(dup_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(pix)
                img_lbl.setStyleSheet("""
                    border: 1px solid #1e1e3a;
                    border-radius: 3px;
                    background: transparent;
                """)
                img_lbl.setFixedSize(68, 68)
                layout.addWidget(img_lbl)
            except:
                pass


# ================= MAIN APP =================
class DuplicateFinderApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Automated Duplicate File Finder")
        self.setGeometry(80, 40, 1520, 860)
        self.setMinimumSize(1200, 700)

        self.files = []
        self.duplicates = []
        self.checkboxes = []
        self.folder = None
        self.scan_thread = None
        self.chatbot = ChatBot(self.checkboxes)

        self._build_ui()

    def _build_ui(self):
        # ── Root stylesheet ──────────────────────────────────────────────────
        self.setStyleSheet("""
            QWidget {
                background-color: #080811;
                color: #ccd6f6;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #0d0d1a;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #00d4ff44;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00d4ff88;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar:horizontal { height: 0; }
            QMessageBox {
                background-color: #0d0d1a;
            }
        """)

        # ── Root layout: vertical (title bar on top, 3-column body below) ─────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── TOP TITLE BAR (full width) ────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(72)
        title_bar.setStyleSheet("""
            background-color: #0a0a1e;
            border-bottom: 2px solid #1a1a40;
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(28, 0, 28, 0)
        title_bar_layout.setSpacing(0)

        # Icon accent
        icon_bar = QLabel("⬡")
        icon_bar.setFont(QFont("Segoe UI", 20))
        icon_bar.setStyleSheet("color: #00d4ff; background: transparent; border: none; padding-right: 14px;")
        title_bar_layout.addWidget(icon_bar)

        # Main title
        main_title = QLabel("Automated Duplicate File Finder")
        main_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        main_title.setStyleSheet("""
            color: #ffffff;
            background: transparent;
            border: none;
            letter-spacing: 0.5px;
        """)
        title_bar_layout.addWidget(main_title)

        title_bar_layout.addSpacing(18)

        # Subtitle pill
        subtitle = QLabel("Smart Detection")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("""
            color: #00d4ff;
            background-color: #00d4ff12;
            border: 1px solid #00d4ff33;
            border-radius: 12px;
            padding: 4px 10px;
        """)
        title_bar_layout.addWidget(subtitle)
        title_bar_layout.addStretch()

        outer.addWidget(title_bar)

        # ── 3-column body widget ──────────────────────────────────────────────
        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer.addWidget(body, 1)

        # ── LEFT SIDEBAR ─────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(270)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #0a0a16;
                border-right: 1px solid #1a1a38;
            }
        """)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(18, 22, 18, 18)
        sb_layout.setSpacing(0)

        # Folder path display
        path_header = QLabel("Target Directory")
        path_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        path_header.setStyleSheet("color: #8899cc; letter-spacing: 0px; border: none; background: transparent;")
        sb_layout.addWidget(path_header)

        sb_layout.addSpacing(6)

        self.folder_label = QLabel("No directory selected")
        self.folder_label.setWordWrap(True)
        self.folder_label.setFont(QFont("Segoe UI", 9))
        self.folder_label.setStyleSheet("""
            color: #7788aa;
            background-color: #0d0d1a;
            border: 1px solid #1e1e3a;
            border-radius: 3px;
            padding: 8px 10px;
        """)
        self.folder_label.setMinimumHeight(52)
        sb_layout.addWidget(self.folder_label)

        sb_layout.addSpacing(10)

        self.folder_btn = GlowButton("⊕   Select Directory", "#00d4ff")
        self.folder_btn.clicked.connect(self.select_folder)
        sb_layout.addWidget(self.folder_btn)

        sb_layout.addSpacing(8)

        self.scan_btn = GlowButton("▶   Initiate Scan", "#7c3aed")
        self.scan_btn.clicked.connect(self.scan)
        sb_layout.addWidget(self.scan_btn)

        sb_layout.addSpacing(20)

        # Progress section
        prog_header = QLabel("Scan Progress")
        prog_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        prog_header.setStyleSheet("color: #8899cc; border: none; background: transparent;")
        sb_layout.addWidget(prog_header)

        sb_layout.addSpacing(6)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat(" %p% ")
        self.progress.setFixedHeight(28)
        self.progress.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #12122a;
                border: 1px solid #2a2a55;
                border-radius: 5px;
                text-align: center;
                color: #ffffff;
                font-size: 10pt;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #00d4ff);
                border-radius: 4px;
            }
        """)
        sb_layout.addWidget(self.progress)

        self.prog_label = QLabel("Ready to scan")
        self.prog_label.setFont(QFont("Segoe UI", 9))
        self.prog_label.setStyleSheet("color: #8899cc; border: none; background: transparent;")
        sb_layout.addWidget(self.prog_label)

        sb_layout.addSpacing(24)

        # Stats
        stats_header = QLabel("Analysis Summary")
        stats_header.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        stats_header.setStyleSheet("color: #8899cc; border: none; background: transparent;")
        sb_layout.addWidget(stats_header)

        sb_layout.addSpacing(8)

        self.stat_total = StatCard("Files Scanned", "0", accent="#00d4ff")
        self.stat_dups = StatCard("Duplicates", "0", accent="#ff4d6d")
        self.stat_space = StatCard("Reclaimable", "0 B", accent="#00ffaa")

        sb_layout.addWidget(self.stat_total)
        sb_layout.addSpacing(6)
        sb_layout.addWidget(self.stat_dups)
        sb_layout.addSpacing(6)
        sb_layout.addWidget(self.stat_space)

        sb_layout.addStretch()

        self.delete_btn = GlowButton("⊗   Delete Selected", "#ff4d6d")
        self.delete_btn.clicked.connect(self.delete_selected)
        sb_layout.addWidget(self.delete_btn)

        root.addWidget(sidebar)

        # ── CENTER PANEL ─────────────────────────────────────────────────────
        center = QWidget()
        center.setStyleSheet("background-color: #080811; border: none;")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setFixedHeight(56)
        topbar.setStyleSheet("""
            background-color: #0a0a14;
            border-bottom: 1px solid #1e1e3a;
        """)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(28, 0, 28, 0)

        results_title = QLabel("Scan Results")
        results_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        results_title.setStyleSheet("color: #ccd6f6; letter-spacing: 0px; border: none; background: transparent;")
        tb_layout.addWidget(results_title)

        tb_layout.addStretch()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                color: #7788aa;
                background: transparent;
                border: none;
                letter-spacing: 0px;
            }
            QPushButton:hover { color: #00d4ff; }
        """)
        self.select_all_btn.clicked.connect(self.select_all)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.deselect_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deselect_all_btn.setStyleSheet("""
            QPushButton {
                color: #7788aa;
                background: transparent;
                border: none;
                letter-spacing: 0px;
            }
            QPushButton:hover { color: #00d4ff; }
        """)
        self.deselect_all_btn.clicked.connect(self.deselect_all)

        tb_layout.addWidget(self.select_all_btn)
        tb_layout.addSpacing(16)
        tb_layout.addWidget(self.deselect_all_btn)

        center_layout.addWidget(topbar)

        # Scroll area for results
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background-color: #080811;")
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(20, 16, 20, 16)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_widget)
        center_layout.addWidget(self.scroll)

        # Empty state
        self.empty_label = QLabel("No scan performed yet.\nSelect a directory and click  Initiate Scan  to begin.")
        self.empty_label.setFont(QFont("Segoe UI", 11))
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #2a3060; border: none; background: transparent;")
        self.scroll_layout.addWidget(self.empty_label)

        root.addWidget(center, 1)

        # ── RIGHT PANEL — CHATBOT ────────────────────────────────────────────
        chat_panel = QWidget()
        chat_panel.setFixedWidth(340)
        chat_panel.setStyleSheet("""
            QWidget {
                background-color: #0a0a18;
                border-left: 2px solid #1e1e40;
            }
        """)
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # ── Chat Header ──
        chat_header = QWidget()
        chat_header.setFixedHeight(62)
        chat_header.setStyleSheet("""
            background-color: #0d0d24;
            border-bottom: 2px solid #1e1e40;
        """)
        ch_layout = QHBoxLayout(chat_header)
        ch_layout.setContentsMargins(16, 0, 16, 0)
        ch_layout.setSpacing(10)

        dot = QLabel("●")
        dot.setFont(QFont("Segoe UI", 12))
        dot.setStyleSheet("color: #00ffaa; border: none; background: transparent;")
        ch_layout.addWidget(dot)

        chat_title_lbl = QLabel("Chatbot")
        chat_title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        chat_title_lbl.setStyleSheet(
            "color: #e8eeff; border: none; background: transparent;"
        )
        ch_layout.addWidget(chat_title_lbl)
        ch_layout.addStretch()

        badge = QLabel("Online")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet("""
            color: #00ffaa;
            background-color: #00ffaa18;
            border: 1px solid #00ffaa44;
            border-radius: 8px;
            padding: 2px 8px;
        """)
        ch_layout.addWidget(badge)

        chat_layout.addWidget(chat_header)

        # ── Chat Messages Display ──
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Segoe UI", 10))
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #080814;
                border: none;
                padding: 16px;
                color: #c0ccee;
                font-size: 10pt;
                font-family: 'Segoe UI';
                selection-background-color: #00d4ff33;
            }
            QScrollBar:vertical {
                background: #0d0d1a;
                width: 5px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2a2a5a;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00d4ff55;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0; }
        """)
        self.chat_display.setHtml("""
            <div style='font-family:"Segoe UI"; font-size:10pt; padding:4px;'>
                <p style='color:#5566aa; font-size:11pt; font-weight:bold;'>
                    Welcome to Chatbot
                </p>
                <p style='color:#3a4a80; margin-top:10px; line-height:1.6;'>
                    Scan a folder first, then ask me things like:<br>
                    &nbsp;&nbsp;&#8226; How many duplicates were found?<br>
                    &nbsp;&nbsp;&#8226; How much space can I reclaim?<br>
                    &nbsp;&nbsp;&#8226; Which files are duplicated?<br>
                    &nbsp;&nbsp;&#8226; Select all duplicates
                </p>
            </div>
        """)
        chat_layout.addWidget(self.chat_display, 1)

        # ── Separator ──
        sep_line = QFrame()
        sep_line.setFixedHeight(2)
        sep_line.setStyleSheet("background-color: #1e1e40; border: none;")
        chat_layout.addWidget(sep_line)

        # ── Chat Input Bar ──
        input_bar = QWidget()
        input_bar.setFixedHeight(70)
        input_bar.setStyleSheet("background-color: #0d0d24;")
        ib_layout = QHBoxLayout(input_bar)
        ib_layout.setContentsMargins(12, 14, 12, 14)
        ib_layout.setSpacing(10)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here and press Enter…")
        self.chat_input.setFont(QFont("Segoe UI", 10))
        self.chat_input.setMinimumHeight(42)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a38;
                border: 2px solid #2e2e60;
                border-radius: 7px;
                padding: 6px 14px;
                color: #eef2ff;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 2px solid #00d4ffaa;
                background-color: #1e1e42;
            }
        """)
        self.chat_input.returnPressed.connect(self.handle_ai_query)

        # Force placeholder text to be clearly visible
        palette = self.chat_input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#6a7aaa"))
        self.chat_input.setPalette(palette)
        ib_layout.addWidget(self.chat_input)

        send_btn = QPushButton("Send")
        send_btn.setMinimumHeight(42)
        send_btn.setFixedWidth(64)
        send_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #00d4ff28;
                color: #00d4ff;
                border: 1.5px solid #00d4ff77;
                border-radius: 7px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #08081a;
            }
            QPushButton:pressed {
                background-color: #009fcc;
                color: #08081a;
            }
        """)
        send_btn.clicked.connect(self.handle_ai_query)
        ib_layout.addWidget(send_btn)

        chat_layout.addWidget(input_bar)
        root.addWidget(chat_panel)

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def select_all(self):
        for cb, _ in self.checkboxes:
            cb.setChecked(True)

    def deselect_all(self):
        for cb, _ in self.checkboxes:
            cb.setChecked(False)

    # ── ACTIONS ──────────────────────────────────────────────────────────────

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.folder = folder
            short = folder if len(folder) < 40 else "…" + folder[-37:]
            self.folder_label.setText(short)
            self.folder_label.setStyleSheet("""
                color: #ccd6f6;
                background-color: #0d0d1a;
                border: 1px solid #00d4ff33;
                border-radius: 3px;
                padding: 8px 10px;
                font-family: Segoe UI;
                font-size: 9pt;
            """)

    def scan(self):
        if not self.folder:
            QMessageBox.warning(self, "Error", "Select a directory first.")
            return

        self.files = []
        self.duplicates = []
        self.checkboxes.clear()
        self.progress.setValue(0)
        self.prog_label.setText("Scanning…")
        self.stat_total.set_value("…")
        self.stat_dups.set_value("…")
        self.stat_space.set_value("…")

        # Clear results
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for root, _, files in os.walk(self.folder):
            for f in files:
                self.files.append(os.path.join(root, f))

        if not self.files:
            QMessageBox.information(self, "Info", "No files found in selected directory.")
            return

        self.stat_total.set_value(str(len(self.files)))

        self.scan_thread = ScanThread(self.files)
        self.scan_thread.progress_update.connect(self._on_progress)
        self.scan_thread.scan_complete.connect(self.show_duplicates)
        self.scan_thread.start()

    def _on_progress(self, val):
        self.progress.setValue(val)
        self.prog_label.setText(f"{val}% complete")

    def show_duplicates(self, duplicates):
        self.duplicates = duplicates
        self.prog_label.setText("Scan complete")
        self.stat_dups.set_value(str(len(duplicates)))

        if not duplicates:
            no_dup = QLabel("✓   No duplicates found in this directory.")
            no_dup.setFont(QFont("Segoe UI", 12))
            no_dup.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_dup.setStyleSheet("color: #00ffaa88; border: none; background: transparent; padding: 60px;")
            self.scroll_layout.addWidget(no_dup)
            self.stat_space.set_value("0 B")
            return

        total_space = 0

        for dup, orig in duplicates:
            try:
                dup_size = os.path.getsize(dup)
                orig_size = os.path.getsize(orig)
            except:
                dup_size = 0
                orig_size = 0

            total_space += dup_size

            card = DuplicateCard(dup, orig, dup_size, orig_size, self.format_size)
            self.scroll_layout.addWidget(card)
            self.checkboxes.append((card.checkbox, dup))

        self.stat_space.set_value(self.format_size(total_space))
        self.chatbot.update_checkboxes(self.checkboxes)

    def delete_selected(self):
        selected = [f for cb, f in self.checkboxes if cb.isChecked()]

        if not selected:
            QMessageBox.warning(self, "Warning", "No files selected for deletion.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Permanently delete {len(selected)} file(s)?\nThis action cannot be undone."
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        errors = []
        for f in selected:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                errors.append(str(e))

        msg = f"{len(selected)} file(s) deleted."
        if errors:
            msg += f"\n{len(errors)} error(s) occurred."
        QMessageBox.information(self, "Done", msg)

    def handle_ai_query(self):
        query = self.chat_input.text().strip()
        if not query:
            return

        self.chat_display.append(
            f"<div style='font-family:Segoe UI; font-size:10pt; margin:8px 0 4px 0;'>"
            f"<span style='color:#00d4ff; font-weight:bold;'>You</span>"
            f"<span style='color:#2a3a60;'> &nbsp;›&nbsp; </span>"
            f"<span style='color:#dde6ff;'>{query}</span></div>"
        )

        response = self.chatbot.respond(query)

        self.chat_display.append(
            f"<div style='font-family:Segoe UI; font-size:10pt; margin:4px 0 10px 0;"
            f"padding:8px 10px; background-color:#12122a; border-radius:6px;'>"
            f"<span style='color:#ffaa00; font-weight:bold;'>AI</span>"
            f"<span style='color:#2a3a60;'> &nbsp;›&nbsp; </span>"
            f"<span style='color:#c0ccee;'>{response}</span></div>"
        )

        self.chat_input.clear()
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )


# ── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DuplicateFinderApp()
    window.show()
    sys.exit(app.exec())
