from PyQt6.QtWidgets import (
    QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel,
    QFrame, QTabWidget, QPushButton, QLineEdit,
    QSizePolicy, QTextEdit, QCheckBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QFont
from model import OCRWorker

INPUT_ENABLED_STYLE = """
    background: #242424; color: #ddd;
    border: 1px solid #333; border-radius: 6px;
    padding: 4px 8px; font-size: 11px;
"""
INPUT_DISABLED_STYLE = """
    background: #1a1a1a; color: #555;
    border: 1px solid #222; border-radius: 6px;
    padding: 4px 8px; font-size: 11px;
"""
CHECKBOX_ENABLED_STYLE = """
    color: #00ff88;
"""
CHECKBOX_DISABLED_STYLE = """
    color: #555;
"""
CHECKBOX_INDICATOR = """
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {border}; border-radius: 3px;
        background: {bg};
    }}
    QCheckBox::indicator:checked {{
        background: {checked_bg};
        border: 1px solid {checked_border};
    }}
"""


class BrowserTab(QWebEngineView):
    def __init__(self, url="https://www.google.com"):
        super().__init__()
        self.setUrl(QUrl(url))

    def createWindow(self, window_type):
        app = self.window()
        return app.add_new_tab()


class BrowserApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("Browser Text Pattern Extractor")
        self.setMinimumSize(1200, 750)
        self.setStyleSheet(f""" QMainWindow#{self.objectName()} {{background-color: #0f0f0f;}}""")
        self.worker = None

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── LEFT: Browser ──────────────────────────────────────
        browser_container = QWidget()
        browser_container.setObjectName("browserContainerWidget")
        browser_container.setStyleSheet(f"""
            QWidget#{browser_container.objectName()} {{
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
                }}
            """)
        browser_layout = QVBoxLayout(browser_container)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        browser_layout.setSpacing(0)

        # ── Title bar ──────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("titleBarWidget")
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet(f"""
            QWidget#{title_bar.objectName()} {{
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #2a2a2a;
            }}""")
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 0, 12, 0)
        title_bar_layout.setSpacing(6)

        title_bar_layout.addStretch()
        app_label = QLabel("Browser Text Pattern Extractor")
        app_label.setObjectName("appLabel")
        app_label.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        app_label.setStyleSheet(f"""
            QWidget#{app_label.objectName()} {{
                color: #00ff88;
                letter-spacing: 2px;
            }}""")
        title_bar_layout.addWidget(app_label)
        title_bar_layout.addStretch()
        browser_layout.addWidget(title_bar)

        # ── URL Bar ────────────────────────────────────────────
        url_bar_widget = QWidget()
        url_bar_widget.setObjectName("urlBarWidget")
        url_bar_widget.setFixedHeight(44)
        url_bar_widget.setStyleSheet(f"""
            QWidget#{url_bar_widget.objectName()}
            {{
                background-color: #181818;
                border-bottom: 1px solid #2a2a2a;
            }}""")
        url_bar_layout = QHBoxLayout(url_bar_widget)
        url_bar_layout.setContentsMargins(10, 6, 10, 6)
        url_bar_layout.setSpacing(6)

        for symbol, slot in [("←", self.go_back), ("→", self.go_forward), ("⟳", self.reload_page)]:
            btn = QPushButton(symbol)
            btn.setObjectName(symbol)
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(f"""
                QPushButton#{symbol} {{
                    background: #2a2a2a; color: #aaa;
                    border: none; border-radius: 6px; font-size: 14px;
                    }}
                QPushButton#{symbol}:hover {{ background: #333; color: white; }}
            """)
            btn.clicked.connect(slot)
            url_bar_layout.addWidget(btn)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlInputLineEdit")
        self.url_input.setPlaceholderText("Enter URL or search...")
        self.url_input.setFont(QFont("Courier New", 11))
        self.url_input.setStyleSheet(f"""
            QLineEdit#{self.url_input.objectName()} {{
                background: #242424; color: #ddd;
                border: 1px solid #333; border-radius: 6px;
                padding: 4px 10px; font-size: 12px;
            }}
            QLineEdit#{self.url_input.objectName()}:focus {{ border: 1px solid #00ff88; color: white; }}
        """)
        self.url_input.returnPressed.connect(self.navigate_to_url)
        url_bar_layout.addWidget(self.url_input)

        go_btn = QPushButton("Go")
        go_btn.setObjectName("goBtnPushButton")
        go_btn.setFixedSize(36, 28)
        go_btn.setStyleSheet(f"""
            QPushButton#{go_btn.objectName()} {{
                background: #00ff88; color: #0f0f0f;
                border: none; border-radius: 6px;
                font-family: 'Courier New'; font-size: 11px; font-weight: bold;
                }}
            QPushButton#{go_btn.objectName()}:hover {{ background: #00cc6a; }}
        """)
        go_btn.clicked.connect(self.navigate_to_url)
        url_bar_layout.addWidget(go_btn)
        browser_layout.addWidget(url_bar_widget)

        # ── Tabs ───────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabWidget")
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        #Only this one dont have objectName()
        self.tabs.setStyleSheet(f"""
            QTabWidget#{self.tabs.objectName()}::pane {{ border: none; background: #1a1a1a; }}
            QTabBar::tab {{
                background: #1e1e1e; color: white;
                padding: 6px 14px; margin-right: 2px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-family: 'Courier New'; font-size: 11px;
                min-width: 80px; max-width: 160px;
            }}
            QTabBar::tab:selected {{ background: #2a2a2a; color: #00ff88; }}
            QTabBar::tab:hover {{ background: #252525; }}
        """)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Add fake "+" tab at the end
        self.tabs.addTab(QWidget(), "+")
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        self.tabs.currentChanged.connect(self.check_plus_tab)

        # Open first real tab
        self.add_new_tab("https://www.google.com")

        browser_layout.addWidget(self.tabs)
        main_layout.addWidget(browser_container, stretch=4)

        # ── RIGHT: UI Panel ────────────────────────────────────
        ui_panel = QWidget()
        ui_panel.setObjectName("uiPanelWidget")
        ui_panel.setFixedWidth(220)
        ui_panel.setStyleSheet(f"""
            QWidget#{ui_panel.objectName()} {{
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 10px;
            }}
                
        """)
        panel_layout = QVBoxLayout(ui_panel)
        panel_layout.setContentsMargins(16, 20, 16, 20)
        panel_layout.setSpacing(16)

        header = QLabel("B MONITOR")
        header.setObjectName("headerLabel")
        header.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
        header.setStyleSheet(f"""
            QLabel#{header.objectName()} {{
                color: #00ff88; letter-spacing: 2px;
            }}
            """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(header)

        divider = QFrame()
        divider.setObjectName("dividerFrame")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"""
            QFrame#{divider.objectName()} {{
                color: #2a2a2a;
            }}""")
        panel_layout.addWidget(divider)

        # Regex input
        regex_label = QLabel("Regex")
        regex_label.setObjectName("regexLabel")
        regex_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        regex_label.setStyleSheet(f"""
            QLabel#{regex_label.objectName()} {{
                color: #00ff88;
            }}""")
        panel_layout.addWidget(regex_label)

        self.regex_input = QLineEdit()
        self.regex_input.setObjectName("regexInputLineEdit")
        self.regex_input.setPlaceholderText("e.g. \\w+")
        self.regex_input.setFont(QFont("Courier New", 10))
        self.regex_input.setStyleSheet(f"QLineEdit#{self.regex_input.objectName()} {{{INPUT_ENABLED_STYLE}}}")
        panel_layout.addWidget(self.regex_input)

        # Exclude input
        exclude_label = QLabel("Exclude")
        exclude_label.setObjectName("excludeLabel")
        exclude_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        exclude_label.setStyleSheet(f"""
            QLabel#{exclude_label.objectName()} {{
                color: #00ff88;
            }}
        """)
        panel_layout.addWidget(exclude_label)

        self.exclude_input = QLineEdit()
        self.exclude_input.setObjectName("excludeInputLineEdit")
        self.exclude_input.setPlaceholderText("e.g. Code: ")
        self.exclude_input.setFont(QFont("Courier New", 10))
        self.exclude_input.setStyleSheet(f"QLineEdit#{self.exclude_input.objectName()} {{{INPUT_ENABLED_STYLE}}}")
        panel_layout.addWidget(self.exclude_input)

        # Scan Interval input
        interval_label = QLabel("Scan Interval (seconds)")
        interval_label.setObjectName("intervalLabel")
        interval_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        interval_label.setStyleSheet(f"""
            QLabel#{interval_label.objectName()} {{
                color: #00ff88;
            }}""")
        panel_layout.addWidget(interval_label)

        self.interval_input = QLineEdit()
        self.interval_input.setObjectName("intervalInputLineEdit")
        self.interval_input.setPlaceholderText("e.g. 1")
        self.interval_input.setText("1")
        self.interval_input.setFont(QFont("Courier New", 10))
        self.interval_input.setStyleSheet(f"QLineEdit#{self.interval_input.objectName()} {{{INPUT_ENABLED_STYLE}}}")
        self.interval_input.textChanged.connect(
            lambda text: self.validate_seconds_input(self.interval_input, text)
        )
        panel_layout.addWidget(self.interval_input)

        # Alarm checkbox
        self.alarm_checkbox = QCheckBox("Alarm")
        self.alarm_checkbox.setObjectName("alarmCheckBox")
        self.alarm_checkbox.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.alarm_checkbox.setStyleSheet(
            f"QCheckBox#{self.alarm_checkbox.objectName()} {{ {CHECKBOX_ENABLED_STYLE} }}" +
            CHECKBOX_INDICATOR.format(border="#555", bg="#242424", checked_bg="#00ff88", checked_border="#00ff88")
        )
        self.alarm_checkbox.toggled.connect(self.on_alarm_toggled)
        panel_layout.addWidget(self.alarm_checkbox)

        # Alarm Interval input
        alarm_interval_label = QLabel("Alarm Interval (seconds)")
        alarm_interval_label.setObjectName("alarmIntervalLabel")
        alarm_interval_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        alarm_interval_label.setStyleSheet(f"""
            QLabel#{alarm_interval_label.objectName()} {{
                color: #00ff88;
            }}""")
        panel_layout.addWidget(alarm_interval_label)

        self.alarm_interval_input = QLineEdit()
        self.alarm_interval_input.setObjectName("alarmIntervalInputLineEdit")
        self.alarm_interval_input.setPlaceholderText("e.g. 1")
        self.alarm_interval_input.setText("1")
        self.alarm_interval_input.setFont(QFont("Courier New", 10))
        self.alarm_interval_input.setStyleSheet(f"QLineEdit#{self.alarm_interval_input.objectName()} {{{INPUT_DISABLED_STYLE}}}")
        self.alarm_interval_input.setEnabled(False)
        self.alarm_interval_input.textChanged.connect(
            lambda text: self.validate_seconds_input(self.alarm_interval_input, text)
        )
        panel_layout.addWidget(self.alarm_interval_input)

        # GPU checkbox
        self.gpu_checkbox = QCheckBox("GPU")
        self.gpu_checkbox.setObjectName("gpuCheckBox")
        self.gpu_checkbox.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.gpu_checkbox.setStyleSheet(
            f"QCheckBox#{self.gpu_checkbox.objectName()} {{ {CHECKBOX_ENABLED_STYLE} }}" +
            CHECKBOX_INDICATOR.format(border="#555", bg="#242424", checked_bg="#00ff88", checked_border="#00ff88")
        )
        panel_layout.addWidget(self.gpu_checkbox)

        # Start/Stop button
        self.toggle_btn = QPushButton("Start")
        self.toggle_btn.setObjectName("toggleBtnPushButton")
        self.toggle_btn.setFixedHeight(32)
        self.toggle_btn.setFont(QFont("Courier New", 10, QFont.Weight.Bold))
        self.toggle_btn.setStyleSheet(f"""
            QPushButton#{self.toggle_btn.objectName()} {{
                background: #00ff88; color: #0f0f0f;
                border: none; border-radius: 6px;
            }}
                
            QPushButton#{self.toggle_btn.objectName()}:hover {{ background: #00cc6a; }}
        """)
        self.toggle_btn.clicked.connect(self.toggle_monitoring)
        panel_layout.addWidget(self.toggle_btn)

        # Output box
        output_label = QLabel("Output:")
        output_label.setObjectName("outputLabel")
        output_label.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        output_label.setStyleSheet(f"""
            QLabel#{output_label.objectName()} {{
                color: #00ff88;
            }}""")
        panel_layout.addWidget(output_label)


        self.output_box = QTextEdit()
        self.output_box.setObjectName("outputBoxTextEdit")
        self.output_box.setFont(QFont("Courier New", 9))
        self.output_box.setStyleSheet(f"""
            QTextEdit#{self.output_box.objectName()} {{
                color: #ddd;
                background: #242424;
                padding: 6px;
                border-radius: 6px;
                border: 1px solid #333;
            }}
            QTextEdit#{self.output_box.objectName()}::selection {{
                background: #00ff88;
                color: #0f0f0f;
            }}
        """)
        self.output_box.setReadOnly(True)
        self.output_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel_layout.addWidget(self.output_box)

        # Status label
        self.status = QLabel("● UNREADY")
        self.status.setObjectName("statusLabel")
        self.status.setFont(QFont("Courier New", 9))
        self.status.setStyleSheet(f"""
            QLabel#{self.status.objectName()} {{
                color: #ff4444;
            }}""")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.status)

        # Mute/Unmute button (below the status label)
        self._is_muted = False
        self.mute_btn = QPushButton("🔊  Mute")
        self.mute_btn.setObjectName("muteBtnPushButton")
        self.mute_btn.setFixedHeight(28)
        self.mute_btn.setFont(QFont("Courier New", 9, QFont.Weight.Bold))
        self.mute_btn.setStyleSheet(f"""
            QPushButton#{self.mute_btn.objectName()} {{
                background: #2a2a2a; color: #aaa;
                border: 1px solid #333; border-radius: 6px;
            }}
            QPushButton#{self.mute_btn.objectName()}:hover {{ background: #333; color: white; }}
        """)
        self.mute_btn.clicked.connect(self.toggle_mute)
        panel_layout.addWidget(self.mute_btn)

        main_layout.addWidget(ui_panel, stretch=1)

    def toggle_mute(self):
        """Toggle mute/unmute — flips the flag on the worker if running."""
        self._is_muted = not self._is_muted
        if self.worker:
            self.worker.muted = self._is_muted
        if self._is_muted:
            self.mute_btn.setText("🔇  Unmute")
            self.mute_btn.setStyleSheet(f"""
                QPushButton#{self.mute_btn.objectName()} {{
                    background: #2a2a2a; color: #ff4444;
                    border: 1px solid #ff4444; border-radius: 6px;
                }}
                QPushButton#{self.mute_btn.objectName()}:hover {{ background: #333; color: #ff6666; }}
            """)
        else:
            self.mute_btn.setText("🔊  Mute")
            self.mute_btn.setStyleSheet(f"""
                QPushButton#{self.mute_btn.objectName()} {{
                    background: #2a2a2a; color: #aaa;
                    border: 1px solid #333; border-radius: 6px;
                }}
                QPushButton#{self.mute_btn.objectName()}:hover {{ background: #333; color: white; }}
            """)

    def on_alarm_toggled(self, checked: bool):
        self.alarm_interval_input.setEnabled(checked)
        style = INPUT_ENABLED_STYLE if checked else INPUT_DISABLED_STYLE
        self.alarm_interval_input.setStyleSheet(
            f"QLineEdit#{self.alarm_interval_input.objectName()} {{{style}}}"
        )

    def validate_seconds_input(self, field: QLineEdit, text: str):
        """Strip non-numeric/non-dot characters from a seconds input field."""
        cleaned = ''.join(c for c in text if c.isdigit() or c == '.')
        if cleaned != text:
            field.setText(cleaned)

    def set_inputs_enabled(self, enabled: bool):
        inputs = [self.regex_input, self.exclude_input, self.interval_input]
        checkboxes = [self.alarm_checkbox, self.gpu_checkbox]

        for field in inputs:
            field.setEnabled(enabled)
            style = INPUT_ENABLED_STYLE if enabled else INPUT_DISABLED_STYLE
            field.setStyleSheet(f"QLineEdit#{field.objectName()} {{{style}}}")

        # alarm_interval_input follows alarm checkbox state, not just enabled flag
        alarm_interval_enabled = enabled and self.alarm_checkbox.isChecked()
        style = INPUT_ENABLED_STYLE if alarm_interval_enabled else INPUT_DISABLED_STYLE
        self.alarm_interval_input.setEnabled(alarm_interval_enabled)
        self.alarm_interval_input.setStyleSheet(
            f"QLineEdit#{self.alarm_interval_input.objectName()} {{{style}}}"
        )

        for cb in checkboxes:
            cb.setEnabled(enabled)
            color = CHECKBOX_ENABLED_STYLE if enabled else CHECKBOX_DISABLED_STYLE
            border = "#555" if enabled else "#333"
            bg = "#242424" if enabled else "#1a1a1a"
            checked_bg = "#00ff88" if enabled else "#444"
            checked_border = "#00ff88" if enabled else "#444"
            cb.setStyleSheet(
                f"QCheckBox#{cb.objectName()} {{ {color} }}" +
                CHECKBOX_INDICATOR.format(border=border, bg=bg, checked_bg=checked_bg, checked_border=checked_border)
            )

    def add_new_tab(self, url="https://www.google.com"):
        tab = BrowserTab(url)
        tab.titleChanged.connect(lambda title, t=tab: self.update_tab_title(t, title))
        tab.urlChanged.connect(lambda qurl, t=tab: self.on_url_changed(qurl, t))
        # Insert before the "+" tab (always last)
        plus_index = self.tabs.count() - 1
        index = self.tabs.insertTab(plus_index, tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        return tab

    def check_plus_tab(self, index):
        # If user clicks the "+" tab, open a new tab instead
        if index == self.tabs.count() - 1:
            self.add_new_tab()

    def close_tab(self, index):
        # Don't close the "+" tab
        if index == self.tabs.count() - 1:
            return
        if self.tabs.count() > 2:
            if self.tabs.currentIndex() == index:
                self.tabs.setCurrentIndex(index - 1)
            self.tabs.removeTab(index)

    def update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index != -1:
            short = title[:20] + "..." if len(title) > 20 else title
            self.tabs.setTabText(index, short)

    def on_tab_changed(self, index):
        tab = self.tabs.widget(index)
        if tab and isinstance(tab, BrowserTab):
            self.url_input.setText(tab.url().toString())

    def on_url_changed(self, qurl, tab):
        if self.tabs.currentWidget() == tab:
            self.url_input.setText(qurl.toString())

    def navigate_to_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            if " " in url or "." not in url:
                url = f"https://www.google.com/search?q={url.replace(' ', '+')}"
            else:
                url = "https://" + url
        tab = self.tabs.currentWidget()
        if tab and isinstance(tab, BrowserTab):
            tab.setUrl(QUrl(url))

    def toggle_monitoring(self):
        if self.toggle_btn.text() == "Start":
            regex    = self.regex_input.text().strip()
            exclude  = self.exclude_input.text().strip()
            interval = self.interval_input.text().strip()

            # Validate scan interval is provided
            if not interval:
                self.status.setText("● Set scan interval!")
                self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #ff4444; }}")
                return

            # Validate scan interval is a valid number
            try:
                float(interval)
            except ValueError:
                self.status.setText("● Invalid scan interval!")
                self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #ff4444; }}")
                return

            # Validate alarm interval if alarm is checked
            if self.alarm_checkbox.isChecked():
                alarm_interval = self.alarm_interval_input.text().strip()
                if not alarm_interval:
                    self.status.setText("● Set alarm interval!")
                    self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #ff4444; }}")
                    return
                try:
                    float(alarm_interval)
                except ValueError:
                    self.status.setText("● Invalid alarm interval!")
                    self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #ff4444; }}")
                    return

            # Disable all inputs
            self.set_inputs_enabled(False)

            # Create and connect worker
            self.worker = OCRWorker(
                browser_widget=self.tabs.currentWidget(),
                regex=regex,
                exclude=exclude,
                interval=interval,
                alarm=self.alarm_checkbox.isChecked(),
                alarm_interval=self.alarm_interval_input.text().strip() if self.alarm_checkbox.isChecked() else "0",
                gpu=self.gpu_checkbox.isChecked(),
                muted=self._is_muted
            )
            self.worker.result_found.connect(self.append_output)
            self.worker.status_update.connect(self.update_status)
            self.worker.request_screenshot.connect(self.worker._do_grab)
            self.worker.start()


            self.toggle_btn.setText("Stop")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton#{self.toggle_btn.objectName()} {{
                    background: #ff4444; color: white;
                    border: none; border-radius: 6px;
                }}
                QPushButton#{self.toggle_btn.objectName()}:hover {{ background: #cc3333; }}
            """)
            self.status.setText("● READY")
            self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #00ff88; }}")
        else:
            if self.worker:
                self.worker.result_found.disconnect(self.append_output)
                self.worker.stop()
                self.worker = None
            self.output_box.clear()

            # Re-enable all inputs
            self.set_inputs_enabled(True)

            self.toggle_btn.setText("Start")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton#{self.toggle_btn.objectName()} {{
                    background: #00ff88; color: #0f0f0f;
                    border: none; border-radius: 6px;
                }}
                    
                QPushButton#{self.toggle_btn.objectName()}:hover {{ background: #00cc6a; }}
            """)
            self.status.setText("● UNREADY")
            self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #ff4444; }}")

    def append_output(self, text):
        self.output_box.append(text)

    def update_status(self, message):
        self.status.setText(f"● {message}")
        self.status.setStyleSheet(f"QLabel#{self.status.objectName()} {{ color: #00ff88; }}")

    def closeEvent(self, event):
        if self.worker:
            self.worker.stop()
        event.accept()

    def go_back(self):
        tab = self.tabs.currentWidget()
        if tab and isinstance(tab, BrowserTab):
            tab.back()

    def go_forward(self):
        tab = self.tabs.currentWidget()
        if tab and isinstance(tab, BrowserTab):
            tab.forward()

    def reload_page(self):
        tab = self.tabs.currentWidget()
        if tab and isinstance(tab, BrowserTab):
            tab.reload()