"""
OCR Worker Thread
Runs EasyOCR + pixel diff + regex matching in background.
"""

import re
import time
import threading
import winsound
import numpy as np
import easyocr
from PyQt6.QtCore import QThread, pyqtSignal


class OCRWorker(QThread):
    # Signals to send results back to main UI thread
    result_found     = pyqtSignal(str)   # emits matched + excluded text
    status_update    = pyqtSignal(str)   # emits status messages
    request_screenshot = pyqtSignal()    # asks main thread to grab a screenshot

    def __init__(self, browser_widget, regex, exclude, interval,
                 alarm=False, alarm_interval="0", gpu=False, muted=False):
        super().__init__()
        self.browser_widget  = browser_widget
        self.regex           = regex
        self.exclude         = exclude
        self.interval        = float(interval)
        self.alarm           = alarm
        self.alarm_interval  = float(alarm_interval) if alarm else 0.0
        self.gpu             = gpu
        self.muted           = muted
        self.running         = False
        self.last_screenshot = None   # numpy array of last frame
        self.seen_results    = set()  # dedup memory
        self.reader          = None   # EasyOCR reader

        # Used to pass screenshot back from main thread to worker thread
        self._screenshot_data  = None
        self._screenshot_event = threading.Event()

    def receive_screenshot(self, arr):
        """Called from main thread to deliver a screenshot numpy array to the worker."""
        self._screenshot_data = arr
        self._screenshot_event.set()

    def _beep(self):
        """Fire a single beep of alarm_interval duration. Skipped if muted."""
        if not self.muted:
            winsound.Beep(1000, int(self.alarm_interval * 1000))

    def _trigger_alarm(self):
        """Start a one-shot beep in a background daemon thread."""
        t = threading.Thread(target=self._beep, daemon=True)
        t.start()

    def run(self):
        self.running = True

        # Initialise EasyOCR once (slow first load)
        self.status_update.emit("Loading EasyOCR model...")
        self.reader = easyocr.Reader(['en'], gpu=self.gpu)
        self.status_update.emit("EasyOCR ready. Monitoring started.")

        while self.running:
            try:
                # ── Step 1: Grab screenshot of browser widget ──
                screenshot_np = self.grab_screenshot()
                if screenshot_np is None:
                    time.sleep(self.interval)
                    continue

                # ── Step 2: Run EasyOCR every tick ────────────
                # No pixel diff — needed to track typing in real time
                self.last_screenshot = screenshot_np

                # ── Step 3: Run EasyOCR ────────────────────────
                ocr_results = self.reader.readtext(screenshot_np)

                # Flatten all detected text into one string per item
                all_texts = [text for (_, text, _) in ocr_results]

                # ── Step 4: Regex match ────────────────────────
                full_text = " ".join(all_texts)
                try:
                    matches = re.findall(self.regex, full_text)
                except re.error as e:
                    self.status_update.emit(f"Invalid regex: {e}")
                    time.sleep(self.interval)
                    continue

                # ── Step 5: Apply exclude ──────────────────────
                exclude_str = self.exclude.strip()
                results = []
                for match in matches:
                    cleaned = match.replace(exclude_str, "") if exclude_str else match
                    cleaned = cleaned.strip()
                    if cleaned:
                        results.append(cleaned)

                # ── Step 6: Dedup + emit + alarm ──────────────
                new_results = set(results)
                # Only output if results changed since last tick
                if new_results != self.seen_results:
                    for result in results:
                        self.result_found.emit(result)
                    self.seen_results = new_results

                    # Trigger a single beep if alarm enabled and new matches found
                    if new_results and self.alarm and self.running:
                        self._trigger_alarm()

            except Exception as e:
                self.status_update.emit(f"Error: {e}")

            time.sleep(self.interval)

    def stop(self):
        self.running = False
        self.seen_results.clear()
        self.last_screenshot = None
        self.quit()
        self.wait(3000)  # Wait up to 3 seconds for thread to finish

    def grab_screenshot(self):
        """Request a screenshot from the main thread and wait for it."""
        try:
            self._screenshot_data = None
            self._screenshot_event.clear()
            self.request_screenshot.emit()
            # Wait up to 5 seconds for main thread to deliver the screenshot
            self._screenshot_event.wait(timeout=5)
            return self._screenshot_data
        except Exception as e:
            self.status_update.emit(f"Screenshot error: {e}")
            return None

    def _do_grab(self):
        """Called on the main thread to grab the widget and deliver it to the worker."""
        try:
            pixmap = self.browser_widget.grab()
            qimage = pixmap.toImage()
            width  = qimage.width()
            height = qimage.height()
            ptr    = qimage.bits()
            ptr.setsize(height * width * 4)
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
            self.receive_screenshot(arr[:, :, :3].copy())
        except Exception as e:
            self.status_update.emit(f"Screenshot error: {e}")
            self.receive_screenshot(None)
