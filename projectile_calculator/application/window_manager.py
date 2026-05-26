"""Управление жизненным циклом приложения (Requirement 10).

WindowManager отвечает за корректное завершение: остановку рабочего потока,
очистку истории, уничтожение Tk-корня и fallback force-exit (Req 10.1–10.4).
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from projectile_calculator.application.controller import CalculationController
    from projectile_calculator.infrastructure.history import HistoryRepository


class WindowManager:
    """Менеджер завершения работы Калькулятора (Req 8.4, 10.1–10.4)."""

    _JOIN_TIMEOUT: float = 2.5
    _FALLBACK_DELAY_MS: int = 3000
    _FORCE_EXIT_DELAY_MS: int = 5000

    def __init__(
        self,
        root: tk.Tk,
        controller: "CalculationController",
        history: "HistoryRepository",
    ) -> None:
        self._root = root
        self._controller = controller
        self._history = history

    def on_close(self) -> None:
        """Обработчик WM_DELETE_WINDOW и кнопки «Выход».

        Порядок:
        1. Сигнализирует рабочему потоку об остановке.
        2. Ожидает завершения потока (timeout 2.5 с).
        3. Очищает историю (Req 8.4).
        4. Уничтожает root.
        5. Планирует fallback force-exit через 3 с (Req 10.4).
        """
        # Планируем fallback на случай зависания.
        self._root.after(self._FALLBACK_DELAY_MS, self._fallback_force_exit)

        # Сигнал рабочему потоку.
        self._controller.stop_event.set()

        # Ожидание потока в отдельном потоке, чтобы не блокировать mainloop.
        threading.Thread(
            target=self._shutdown_sequence, daemon=True
        ).start()

    def _shutdown_sequence(self) -> None:
        """Фоновая последовательность завершения."""
        worker = self._controller.worker_thread
        if worker is not None and worker.is_alive():
            worker.join(timeout=self._JOIN_TIMEOUT)

        # Очистка и уничтожение — в главном потоке.
        try:
            self._root.after(0, self._finalize)
        except Exception:
            # Если root уже уничтожен — просто выходим.
            os._exit(0)

    def _finalize(self) -> None:
        """Финальные действия в главном потоке."""
        self._history.clear()
        try:
            self._root.destroy()
        except Exception:
            os._exit(0)

    def _fallback_force_exit(self) -> None:
        """Принудительное завершение при зависании (Req 10.4)."""
        try:
            messagebox.showerror(
                "Ошибка завершения",
                "Приложение не удалось завершить корректно. "
                "Принудительное завершение через 5 секунд.",
            )
        except Exception:
            pass
        # Даём 5 секунд и принудительно выходим.
        try:
            self._root.after(self._FORCE_EXIT_DELAY_MS, lambda: os._exit(1))
        except Exception:
            os._exit(1)
