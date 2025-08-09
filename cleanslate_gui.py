#!/usr/bin/env python3
"""
LocalMind GUI (PySimpleGUI) - Simple 3-tab interface per MVP spec.
"""

import os
os.environ["TK_SILENCE_DEPRECATION"] = "1"
import json
import threading
from pathlib import Path
from typing import List, Dict, Any
import webbrowser
import PySimpleGUI as sg

# Disable all icon handling (macOS-safe)
try:
    sg.set_global_icon(None)
except Exception:
    pass
try:
    sg.set_options(icon=None, window_icon=None)
except Exception:
    pass

def _no_icon(self, *args, **kwargs):
    return
try:
    sg.Window._set_icon = _no_icon
    sg.Window.set_icon = _no_icon
except Exception:
    pass
try:
    sg.DEFAULT_BASE64_ICON = None
except Exception:
    pass
try:
    import tkinter
    _orig_PhotoImage = tkinter.PhotoImage
    def _safe_PhotoImage(*args, **kwargs):
        try:
            return _orig_PhotoImage(*args, **kwargs)
        except Exception:
            return _orig_PhotoImage(width=1, height=1)
    tkinter.PhotoImage = _safe_PhotoImage
    try:
        sg.Window.WindowIcon = None
    except Exception:
        pass
except Exception:
    pass

# Keys
INPUT_SCAN_PATH = "-INPUT_SCAN_PATH-"
BTN_BROWSE = "-BTN_BROWSE-"
CHK_DEMO = "-CHK_DEMO-"
BTN_RUN = "-BTN_RUN-"
BTN_STOP = "-BTN_STOP-"
BTN_OPEN_REPORT = "-BTN_OPEN_REPORT-"
TXT_STATUS = "-TXT_STATUS-"
ML_RESULTS = "-ML_RESULTS-"
TXT_SUMMARY = "-TXT_SUMMARY-"
IN_SIZE_MB = "-IN_SIZE_MB-"
IN_AGE_DAYS = "-IN_AGE_DAYS-"
ML_EXCLUSIONS = "-ML_EXCLUSIONS-"
CHK_WRITE_TXT = "-CHK_WRITE_TXT-"
CHK_WRITE_HTML = "-CHK_WRITE_HTML-"
BTN_SAVE_SETTINGS = "-BTN_SAVE_SETTINGS-"
BTN_RELOAD_SETTINGS = "-BTN_RELOAD_SETTINGS-"
BTN_DEFAULTS = "-BTN_DEFAULTS-"
BTN_OPEN_LOGS = "-BTN_OPEN_LOGS-"
BTN_VIEW_LICENSE = "-BTN_VIEW_LICENSE-"
EV_SCAN_PROGRESS = "-EV_SCAN_PROGRESS-"
EV_SCAN_DONE = "-EV_SCAN_DONE-"
EV_SCAN_ERROR = "-EV_SCAN_ERROR-"

APP_VERSION = "1.0.0"
CONFIG_PATH = Path("config.json")
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "localmind.log"

DEFAULTS = {
    "size_threshold_mb": 50,
    "age_threshold_days": 180,
    "exclusions": [],
    "write_text_report": True,
    "write_html_report": True,
}


def _log(msg: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def load_settings() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Translate possible Phase 2 keys
            mapped = {
                "size_threshold_mb": data.get("size_threshold_mb") or data.get("large_file_threshold_mb", 50),
                "age_threshold_days": data.get("age_threshold_days") or data.get("old_file_threshold_days", 180),
                "exclusions": data.get("exclusions") or data.get("exclude_paths") or data.get("excluded_file_types", []),
                "write_text_report": data.get("write_text_report", True),
                "write_html_report": data.get("write_html_report", True),
            }
            # Normalize list
            if isinstance(mapped["exclusions"], str):
                mapped["exclusions"] = [mapped["exclusions"]]
            return {**DEFAULTS, **{k: v for k, v in mapped.items() if v is not None}}
        except Exception:
            _log("load_settings error; using defaults")
    save_settings(DEFAULTS)
    return dict(DEFAULTS)


def save_settings(settings: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        _log(f"save_settings error: {e}")


def build_layout(settings: Dict[str, Any]):
    # Scan tab
    left_col = [
        [sg.Text("Select folder to scan.")],
        [sg.Input(key=INPUT_SCAN_PATH, enable_events=False, readonly=True, size=(36, 1)),
         sg.FolderBrowse("Browse", key=BTN_BROWSE)],
        [sg.Checkbox("Demo mode", key=CHK_DEMO, enable_events=True)],
        [sg.HorizontalSeparator()],
        [sg.Text("Actions.")],
        [sg.Button("Run Scan", key=BTN_RUN, size=(12, 1)),
         sg.Button("Stop", key=BTN_STOP, size=(8, 1), disabled=True),
         sg.Button("Open Report", key=BTN_OPEN_REPORT, size=(12, 1), disabled=True)],
        [sg.Text("Status:"), sg.Text("Ready", key=TXT_STATUS, size=(40, 1))],
    ]
    right_col = [
        [sg.Text("Results.")],
        [sg.Multiline(key=ML_RESULTS, size=(70, 25), font=("Courier New", 10), autoscroll=True,
                      write_only=True, disabled=True)],
        [sg.Text("", key=TXT_SUMMARY, size=(60, 1))],
    ]
    tab_scan = [
        [sg.Column(left_col, pad=((0, 16), (0, 0))), sg.Column(right_col, expand_y=True)],
    ]

    # Settings tab
    left_set = [
        [sg.Text("Scan thresholds.")],
        [sg.Text("Size threshold (MB):"), sg.Input(str(settings["size_threshold_mb"]), key=IN_SIZE_MB, size=(8, 1))],
        [sg.Text("Age threshold (days):"), sg.Input(str(settings["age_threshold_days"]), key=IN_AGE_DAYS, size=(8, 1))],
        [sg.Text("Exclusions (one per line)\nExample: .DS_Store or node_modules")],
        [sg.Multiline("\n".join(settings["exclusions"]), key=ML_EXCLUSIONS, size=(40, 6))],
    ]
    right_set = [
        [sg.Text("Behavior.")],
        [sg.Checkbox("Write text report after scan", key=CHK_WRITE_TXT, default=settings["write_text_report"])],
        [sg.Checkbox("Write HTML report after scan", key=CHK_WRITE_HTML, default=settings["write_html_report"])],
        [sg.Text("Reports: LocalMind_Report.txt / LocalMind_Report.html in project root")],
        [sg.Push(), sg.Button("Save Settings", key=BTN_SAVE_SETTINGS), sg.Button("Reload Settings", key=BTN_RELOAD_SETTINGS),
         sg.Button("Restore Defaults", key=BTN_DEFAULTS)],
    ]
    tab_settings = [[sg.Column(left_set, pad=((0, 16), (0, 0))), sg.Column(right_set, expand_y=True)]]

    # About tab
    about_layout = [
        [sg.Text("What LocalMind does", font=("Helvetica", 12, "bold"))],
        [sg.Text("Smart file cleanup. 100% offline. Runs locally.")],
        [sg.Text("Privacy", font=("Helvetica", 12, "bold"))],
        [sg.Text("All scans run locally and do not leave your machine.")],
        [sg.Text("Version", font=("Helvetica", 12, "bold"))],
        [sg.Text(f"{APP_VERSION}")],
        [sg.Text("Contact", font=("Helvetica", 12, "bold"))],
        [sg.Text("support@localmindit.com (placeholder)")],
        [sg.Button("Open Logs", key=BTN_OPEN_LOGS), sg.Button("View License", key=BTN_VIEW_LICENSE)],
    ]

    layout = [
        [sg.Text("LocalMind", font=("Helvetica", 16, "bold")), sg.Push(), sg.Button("Help", key="-HELP-")],
        [sg.TabGroup([[sg.Tab("Scan", tab_scan), sg.Tab("Settings", tab_settings), sg.Tab("About", about_layout)]], expand_x=True, expand_y=True)],
    ]
    return layout


class LocalMindWindow:
    def __init__(self):
        sg.theme("SystemDefault")
        self.settings = load_settings()
        self.window = sg.Window(
            "LocalMind",
            build_layout(self.settings),
            size=(800, 600),
            resizable=True,
            margins=(16, 16),
            finalize=True,
        )
        self.window[ML_RESULTS].Widget.configure(state="normal")
        self.cancel_event: threading.Event = threading.Event()
        self.worker: threading.Thread | None = None
        self.latest_reports = {"txt": None, "html": None}
        self._enforce_demo_state()

    def _enforce_demo_state(self):
        demo = self.window[CHK_DEMO].get()
        self.window[INPUT_SCAN_PATH].update(disabled=demo)
        if demo:
            self.window[INPUT_SCAN_PATH].update("./demo_data")

    def _append_line(self, line: str):
        self.window[ML_RESULTS].print(line)

    def _scan_worker(self, scan_path: str, thresholds: Dict[str, int], exclusions: List[str], write_txt: bool, write_html: bool):
        try:
            from cleanslate_core import scan_folder

            def progress_cb(line: str):
                self.window.write_event_value(EV_SCAN_PROGRESS, line)

            results = scan_folder(
                scan_path,
                thresholds["size_threshold_mb"],
                thresholds["age_threshold_days"],
                exclusions,
                write_txt,
                write_html,
                self.cancel_event,
                progress_cb,
            )
            self.window.write_event_value(EV_SCAN_DONE, results)
        except Exception as e:
            self.window.write_event_value(EV_SCAN_ERROR, str(e))

    def run(self):
        while True:
            event, values = self.window.read(timeout=200)
            if event in (sg.WIN_CLOSED, "Exit"):
                # cancel worker if running
                if self.worker and self.worker.is_alive():
                    self.cancel_event.set()
                    self.worker.join(timeout=2)
                break

            if event == "-HELP-":
                sg.popup("LocalMind\nSmart file cleanup. 100% offline.")

            if event == CHK_DEMO:
                self._enforce_demo_state()

            if event == BTN_BROWSE:
                # FolderBrowse element populates the input automatically
                pass

            if event == BTN_RUN:
                scan_path = values.get(INPUT_SCAN_PATH, "").strip()
                demo_mode = values.get(CHK_DEMO, False)
                if demo_mode:
                    scan_path = "./demo_data"
                if not scan_path or not Path(scan_path).exists():
                    sg.popup_error("Please select a folder or enable Demo mode.")
                    continue
                # Parse settings
                try:
                    size_mb = int(values.get(IN_SIZE_MB, self.settings["size_threshold_mb"]))
                    age_days = int(values.get(IN_AGE_DAYS, self.settings["age_threshold_days"]))
                except ValueError:
                    sg.popup_error("Please enter valid numbers for thresholds.")
                    continue
                exclusions_text = values.get(ML_EXCLUSIONS, "") or ""
                exclusions = [ln.strip() for ln in exclusions_text.splitlines() if ln.strip()]
                write_txt = bool(values.get(CHK_WRITE_TXT, True))
                write_html = bool(values.get(CHK_WRITE_HTML, True))

                # Start worker
                self.window[BTN_RUN].update(disabled=True)
                self.window[BTN_STOP].update(disabled=False)
                self.window[TXT_STATUS].update("Scanning")
                self.window[ML_RESULTS].update("")
                self.cancel_event.clear()
                self.worker = threading.Thread(
                    target=self._scan_worker,
                    args=(scan_path, {"size_threshold_mb": size_mb, "age_threshold_days": age_days}, exclusions, write_txt, write_html),
                    daemon=True,
                )
                self.worker.start()

            if event == BTN_STOP:
                self.cancel_event.set()
                self.window[TXT_STATUS].update("Canceled")
                self.window[BTN_RUN].update(disabled=False)
                self.window[BTN_STOP].update(disabled=True)

            if event == BTN_OPEN_REPORT:
                # open text report first
                if self.latest_reports.get("txt") and Path(self.latest_reports["txt"]).exists():
                    webbrowser.open(self.latest_reports["txt"])  # default editor
                elif self.latest_reports.get("html") and Path(self.latest_reports["html"]).exists():
                    webbrowser.open(self.latest_reports["html"])  # browser
                else:
                    sg.popup("No report available yet.")

            if event == BTN_SAVE_SETTINGS:
                try:
                    new_settings = {
                        "size_threshold_mb": int(values.get(IN_SIZE_MB, self.settings["size_threshold_mb"])),
                        "age_threshold_days": int(values.get(IN_AGE_DAYS, self.settings["age_threshold_days"])),
                        "exclusions": [ln.strip() for ln in (values.get(ML_EXCLUSIONS, "") or "").splitlines() if ln.strip()],
                        "write_text_report": bool(values.get(CHK_WRITE_TXT, True)),
                        "write_html_report": bool(values.get(CHK_WRITE_HTML, True)),
                    }
                    save_settings(new_settings)
                    self.settings = new_settings
                    sg.popup("Settings saved.")
                except ValueError:
                    sg.popup_error("Please enter valid numbers for thresholds.")

            if event == BTN_RELOAD_SETTINGS:
                self.settings = load_settings()
                # refresh fields
                self.window[IN_SIZE_MB].update(str(self.settings["size_threshold_mb"]))
                self.window[IN_AGE_DAYS].update(str(self.settings["age_threshold_days"]))
                self.window[ML_EXCLUSIONS].update("\n".join(self.settings["exclusions"]))
                self.window[CHK_WRITE_TXT].update(self.settings["write_text_report"]) 
                self.window[CHK_WRITE_HTML].update(self.settings["write_html_report"]) 
                sg.popup("Settings reloaded.")

            if event == BTN_DEFAULTS:
                if sg.popup_yes_no("Restore default settings?") == "Yes":
                    save_settings(DEFAULTS)
                    self.settings = dict(DEFAULTS)
                    self.window[IN_SIZE_MB].update(str(self.settings["size_threshold_mb"]))
                    self.window[IN_AGE_DAYS].update(str(self.settings["age_threshold_days"]))
                    self.window[ML_EXCLUSIONS].update("\n".join(self.settings["exclusions"]))
                    self.window[CHK_WRITE_TXT].update(self.settings["write_text_report"]) 
                    self.window[CHK_WRITE_HTML].update(self.settings["write_html_report"]) 

            if event == BTN_OPEN_LOGS:
                if LOG_FILE.exists():
                    webbrowser.open(str(LOG_FILE.resolve()))
                else:
                    sg.popup("No logs yet.")

            if event == BTN_VIEW_LICENSE:
                sg.popup("License: Unlicensed (OK for testing)")

            # Worker events
            if event == EV_SCAN_PROGRESS:
                self._append_line(values.get(EV_SCAN_PROGRESS, ""))

            if event == EV_SCAN_DONE:
                res = values.get(EV_SCAN_DONE, {})
                self.window[BTN_RUN].update(disabled=False)
                self.window[BTN_STOP].update(disabled=True)
                self.window[TXT_STATUS].update("Scan complete")
                total = res.get("total_files", 0)
                large = res.get("large_count", 0)
                old = res.get("old_count", 0)
                dups = res.get("dup_groups", 0)
                self.window[TXT_SUMMARY].update(f"Files scanned {total}. Large {large}. Old {old}. Duplicate groups {dups}.")
                self.latest_reports["txt"] = res.get("report_txt_path")
                self.latest_reports["html"] = res.get("report_html_path")
                if self.latest_reports["txt"] or self.latest_reports["html"]:
                    self.window[BTN_OPEN_REPORT].update(disabled=False)

            if event == EV_SCAN_ERROR:
                self.window[BTN_RUN].update(disabled=False)
                self.window[BTN_STOP].update(disabled=True)
                self.window[TXT_STATUS].update("Error")
                sg.popup_error(f"Scan error: {values.get(EV_SCAN_ERROR)}")

        self.window.close()


def main():
    LocalMindWindow().run()

if __name__ == "__main__":
    main() 