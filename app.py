#!/usr/bin/env python3
"""
LocalMind - Smart file cleanup. 100% offline. AI that tidies your computer without touching the cloud.
Python desktop GUI entry point (PySimpleGUI).
"""

import os
os.environ["TK_SILENCE_DEPRECATION"] = "1"

# Patch tkinter.PhotoImage BEFORE importing PySimpleGUI to avoid icon crash on macOS
try:
    import tkinter  # type: ignore
    _orig_PhotoImage = tkinter.PhotoImage
    def _safe_PhotoImage(*args, **kwargs):
        try:
            return _orig_PhotoImage(*args, **kwargs)
        except Exception:
            return _orig_PhotoImage(width=1, height=1)
    tkinter.PhotoImage = _safe_PhotoImage  # type: ignore
except Exception:
    pass

import PySimpleGUI as sg


def main():
    try:
        from cleanslate_gui import main as gui_main
        gui_main()
    except Exception as e:
        sg.popup_error(f"Application error: {str(e)}")


if __name__ == "__main__":
    main()



