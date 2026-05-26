"""Окно справки — Singleton (Requirement 13.3).

Повторный вызов ``show()`` возвращает фокус существующему окну.
Закрытие: системная кнопка или Escape.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext

from projectile_calculator.resources.help_text import HELP_CONTENT, HELP_TITLE


class HelpWindow:
    """Singleton-окно справки (Req 7.1–7.3, 7.8)."""

    _instance: HelpWindow | None = None
    _toplevel: tk.Toplevel | None = None

    def __init__(self, parent: tk.Tk) -> None:
        self._parent = parent

    def show(self) -> None:
        """Показать или перефокусировать окно справки."""
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.focus_force()
            self._toplevel.lift()
            return

        self._toplevel = tk.Toplevel(self._parent)
        self._toplevel.title(HELP_TITLE)
        self._toplevel.geometry("600x500")
        self._toplevel.minsize(400, 300)
        self._toplevel.transient(self._parent)

        text_widget = scrolledtext.ScrolledText(
            self._toplevel,
            wrap=tk.WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, HELP_CONTENT)
        text_widget.configure(state=tk.DISABLED)

        self._toplevel.bind("<Escape>", lambda e: self._close())
        self._toplevel.protocol("WM_DELETE_WINDOW", self._close)

    def _close(self) -> None:
        """Закрыть окно и вернуть фокус родителю (Req 7.8)."""
        if self._toplevel is not None and self._toplevel.winfo_exists():
            self._toplevel.destroy()
        self._toplevel = None
        try:
            self._parent.focus_force()
        except tk.TclError:
            pass
