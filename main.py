"""Точка входа Калькулятора траектории полёта (Requirement 14.1).

Собирает все зависимости и запускает Tkinter mainloop.
"""

from __future__ import annotations

import tkinter as tk

from projectile_calculator.application.controller import CalculationController
from projectile_calculator.application.window_manager import WindowManager
from projectile_calculator.domain.analytic import AnalyticCalculator
from projectile_calculator.domain.numerical import NumericalIntegrator
from projectile_calculator.domain.validator import Validator
from projectile_calculator.infrastructure.exporter import Exporter
from projectile_calculator.infrastructure.history import HistoryRepository
from projectile_calculator.presentation.main_window import MainWindow


def main() -> None:
    """Инициализация и запуск приложения."""
    root = tk.Tk()

    # Domain services
    validator = Validator()
    analytic = AnalyticCalculator()
    numerical = NumericalIntegrator()

    # Infrastructure
    history = HistoryRepository()
    exporter = Exporter()

    # schedule_main_thread: безопасная доставка колбэков в главный поток Tk.
    def schedule_main_thread(fn):
        root.after(0, fn)

    # Placeholder callbacks — будут подключены после создания MainWindow.
    controller = CalculationController(
        validator=validator,
        analytic=analytic,
        numerical=numerical,
        history=history,
        exporter=exporter,
        on_validation_errors=lambda errors: None,
        on_calculation_error=lambda cat: None,
        on_result=lambda res, inp: None,
        on_progress_visible=lambda v: None,
        schedule_main_thread=schedule_main_thread,
    )

    # Window manager
    window_manager = WindowManager(root, controller, history)

    # Presentation
    main_window = MainWindow(root, controller, window_manager)

    # Подключаем реальные колбэки UI к контроллеру.
    controller._on_validation_errors = main_window.on_validation_errors
    controller._on_calculation_error = main_window.on_calculation_error
    controller._on_result = main_window.on_result
    controller._on_progress_visible = main_window.on_progress_visible

    # WM_DELETE_WINDOW → WindowManager
    root.protocol("WM_DELETE_WINDOW", window_manager.on_close)

    root.mainloop()


if __name__ == "__main__":
    main()
