"""Главное окно Калькулятора траектории полёта (Requirements 12, 13.4).

Содержит Форму_Ввода, Область_Результатов, Журнал_Истории и панель кнопок.
Делегирует все вычисления контроллеру.
"""

from __future__ import annotations

import tkinter as tk
from enum import Enum
from tkinter import ttk
from typing import TYPE_CHECKING

from projectile_calculator.domain.models import (
    CalculationErrorCategory,
    CalculationInput,
    CalculationResult,
    Mode,
    ValidationError,
)
from projectile_calculator.presentation.dialogs import (
    ask_save_path,
    show_calculation_error,
    show_info,
    show_io_error,
    show_validation_errors,
)
from projectile_calculator.presentation.formatters import format_meters
from projectile_calculator.presentation.help_window import HelpWindow

if TYPE_CHECKING:
    from projectile_calculator.application.controller import CalculationController
    from projectile_calculator.application.window_manager import WindowManager


# ------------------------------------------------------------------
# Перечисления состояний (Req 12.1)
# ------------------------------------------------------------------

class ButtonState(Enum):
    """Состояние кнопки «Рассчитать»."""
    ENABLED = "enabled"
    DISABLED = "disabled"


class FieldState(Enum):
    """Состояние поля k."""
    EDITABLE = "editable"
    READ_ONLY = "readonly"


# ------------------------------------------------------------------
# Чистые функции состояния (Req 12.1, 13.4, 13.5, 1.8)
# ------------------------------------------------------------------

def compute_calculate_button_state(
    raw_v0: str, raw_alpha: str, raw_k: str, mode: Mode,
) -> ButtonState:
    """Определить состояние кнопки «Рассчитать» по текущему содержимому формы.

    Кнопка активна ⇔ все обязательные поля непусты (Req 13.4, 13.5).
    Полная валидация выполняется при нажатии — здесь только быстрая проверка.
    """
    if not raw_v0.strip():
        return ButtonState.DISABLED
    if not raw_alpha.strip():
        return ButtonState.DISABLED
    if mode == Mode.WITH_DRAG and not raw_k.strip():
        return ButtonState.DISABLED
    return ButtonState.ENABLED


def compute_k_field_state(mode: Mode) -> FieldState:
    """Определить состояние поля k по текущему режиму (Req 1.8)."""
    if mode == Mode.NO_DRAG:
        return FieldState.READ_ONLY
    return FieldState.EDITABLE


# ------------------------------------------------------------------
# MainWindow
# ------------------------------------------------------------------

class MainWindow:
    """Главное окно приложения (Req 13.1–13.7)."""

    def __init__(
        self,
        root: tk.Tk,
        controller: "CalculationController",
        window_manager: "WindowManager",
    ) -> None:
        self._root = root
        self._controller = controller
        self._window_manager = window_manager
        self._help_window = HelpWindow(root)

        self._progress_after_id: str | None = None

        self._setup_window()
        self._create_widgets()
        self._bind_events()
        self._update_button_states()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------
    def _setup_window(self) -> None:
        self._root.title("Калькулятор траектории полёта")
        self._root.geometry("800x600")
        self._root.minsize(800, 600)

    # ------------------------------------------------------------------
    # Widget creation
    # ------------------------------------------------------------------
    def _create_widgets(self) -> None:
        # --- Форма Ввода (верхняя часть) ---
        form_frame = ttk.LabelFrame(self._root, text="Исходные данные", padding=10)
        form_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # v0
        row = 0
        ttk.Label(form_frame, text="Начальная скорость v₀ (м/с):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self._var_v0 = tk.StringVar()
        self._entry_v0 = ttk.Entry(form_frame, textvariable=self._var_v0, width=20)
        self._entry_v0.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # alpha
        row = 1
        ttk.Label(form_frame, text="Угол броска α (градусы):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self._var_alpha = tk.StringVar()
        self._entry_alpha = ttk.Entry(form_frame, textvariable=self._var_alpha, width=20)
        self._entry_alpha.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # k
        row = 2
        ttk.Label(form_frame, text="Коэффициент сопротивления k (кг/с):").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self._var_k = tk.StringVar()
        self._entry_k = ttk.Entry(form_frame, textvariable=self._var_k, width=20)
        self._entry_k.grid(row=row, column=1, sticky=tk.W, padx=(10, 0), pady=2)

        # Mode checkbox
        row = 3
        self._var_drag = tk.BooleanVar(value=False)
        self._check_drag = ttk.Checkbutton(
            form_frame,
            text="Учитывать сопротивление воздуха",
            variable=self._var_drag,
            command=self._on_mode_changed,
        )
        self._check_drag.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        # --- Область результатов (центральная часть) ---
        result_frame = ttk.LabelFrame(self._root, text="Результаты", padding=10)
        result_frame.pack(fill=tk.X, padx=10, pady=5)

        self._lbl_L = ttk.Label(result_frame, text="Дальность: —", font=("Arial", 11))
        self._lbl_L.pack(anchor=tk.W)

        self._lbl_H = ttk.Label(result_frame, text="Максимальная высота: —", font=("Arial", 11))
        self._lbl_H.pack(anchor=tk.W)

        self._lbl_mode = ttk.Label(result_frame, text="", font=("Arial", 10, "italic"))
        self._lbl_mode.pack(anchor=tk.W, pady=(5, 0))

        # Progress label (скрыта по умолчанию)
        self._lbl_progress = ttk.Label(result_frame, text="Идёт расчёт…", foreground="blue")

        # --- Журнал Истории ---
        history_frame = ttk.LabelFrame(self._root, text="История вычислений", padding=5)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self._history_text = tk.Text(
            history_frame, height=8, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9)
        )
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self._history_text.yview)
        self._history_text.configure(yscrollcommand=scrollbar.set)
        self._history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- Панель кнопок (нижняя часть) ---
        btn_frame = ttk.Frame(self._root, padding=10)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self._btn_calculate = ttk.Button(btn_frame, text="Рассчитать", command=self._on_calculate)
        self._btn_calculate.pack(side=tk.LEFT, padx=(0, 5))

        self._btn_clear = ttk.Button(btn_frame, text="Очистить", command=self._on_clear)
        self._btn_clear.pack(side=tk.LEFT, padx=5)

        self._btn_help = ttk.Button(btn_frame, text="Справка", command=self._on_help)
        self._btn_help.pack(side=tk.LEFT, padx=5)

        self._btn_export = ttk.Button(btn_frame, text="Экспорт", command=self._on_export)
        self._btn_export.pack(side=tk.LEFT, padx=5)

        self._btn_exit = ttk.Button(btn_frame, text="Выход", command=self._on_exit)
        self._btn_exit.pack(side=tk.LEFT, padx=5)

        # Initial state
        self._on_mode_changed()

    # ------------------------------------------------------------------
    # Event bindings
    # ------------------------------------------------------------------
    def _bind_events(self) -> None:
        # Обновление состояния кнопки при изменении полей (Req 13.4, 13.5, 2.10).
        self._var_v0.trace_add("write", lambda *_: self._update_button_states())
        self._var_alpha.trace_add("write", lambda *_: self._update_button_states())
        self._var_k.trace_add("write", lambda *_: self._update_button_states())

        # Tab order: v0 → alpha → k → checkbox → buttons
        self._entry_v0.focus_set()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _on_calculate(self) -> None:
        mode = Mode.WITH_DRAG if self._var_drag.get() else Mode.NO_DRAG
        self._controller.on_calculate(
            self._var_v0.get(),
            self._var_alpha.get(),
            self._var_k.get(),
            mode,
        )

    def _on_clear(self) -> None:
        self._controller.on_clear()
        self._var_v0.set("")
        self._var_alpha.set("")
        self._var_k.set("")
        self._var_drag.set(False)
        self._on_mode_changed()
        self._lbl_L.configure(text="Дальность: —")
        self._lbl_H.configure(text="Максимальная высота: —")
        self._lbl_mode.configure(text="")
        self._entry_v0.focus_set()

    def _on_help(self) -> None:
        self._help_window.show()

    def _on_export(self) -> None:
        from projectile_calculator.infrastructure.history import HistoryRepository

        if len(self._controller._history) == 0:
            show_info(self._root, "История вычислений пуста.")
            return

        result = ask_save_path(self._root)
        if result is None:
            return

        path, fmt = result
        error = self._controller.on_export(path, fmt)
        if error is None:
            resolved = self._controller._exporter.ensure_extension(path, fmt)
            show_info(self._root, f"Сохранено в {resolved}")
        else:
            show_io_error(self._root, error)

    def _on_exit(self) -> None:
        self._window_manager.on_close()

    def _on_mode_changed(self) -> None:
        mode = Mode.WITH_DRAG if self._var_drag.get() else Mode.NO_DRAG
        state = compute_k_field_state(mode)
        if state == FieldState.READ_ONLY:
            self._entry_k.configure(state="disabled")
        else:
            self._entry_k.configure(state="normal")
        self._update_button_states()

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _update_button_states(self) -> None:
        mode = Mode.WITH_DRAG if self._var_drag.get() else Mode.NO_DRAG
        state = compute_calculate_button_state(
            self._var_v0.get(), self._var_alpha.get(), self._var_k.get(), mode
        )
        if state == ButtonState.ENABLED:
            self._btn_calculate.configure(state="normal")
        else:
            self._btn_calculate.configure(state="disabled")

    # ------------------------------------------------------------------
    # Controller callbacks
    # ------------------------------------------------------------------
    def on_validation_errors(self, errors: tuple[ValidationError, ...]) -> None:
        """Колбэк: ошибки валидации."""
        self._lbl_L.configure(text="Дальность: —")
        self._lbl_H.configure(text="Максимальная высота: —")
        show_validation_errors(self._root, errors)
        # Фокус на первое ошибочное поле (Req 11.6).
        if errors:
            field_id = errors[0].field_id
            if field_id == "v0":
                self._entry_v0.focus_set()
            elif field_id == "alpha":
                self._entry_alpha.focus_set()
            elif field_id == "k":
                self._entry_k.focus_set()

    def on_calculation_error(self, category: CalculationErrorCategory) -> None:
        """Колбэк: ошибка расчёта."""
        self._lbl_L.configure(text="Дальность: —")
        self._lbl_H.configure(text="Максимальная высота: —")
        show_calculation_error(self._root, category)

    def on_result(self, result: CalculationResult, calc_input: CalculationInput) -> None:
        """Колбэк: успешный результат."""
        L_str = format_meters(result.L)
        H_str = format_meters(result.H)
        self._lbl_L.configure(text=f"Дальность: {L_str} м")
        self._lbl_H.configure(text=f"Максимальная высота: {H_str} м")

        mode_label = (
            "Без сопротивления воздуха"
            if result.mode == Mode.NO_DRAG
            else "С сопротивлением воздуха"
        )
        self._lbl_mode.configure(text=f"Режим: {mode_label}")

        # Обновить журнал истории (Req 8.2, 8.3).
        self._refresh_history()

    def on_progress_visible(self, visible: bool) -> None:
        """Показать/скрыть «Идёт расчёт…» (Req 12.7)."""
        if visible:
            # Показываем через 1 секунду задержки.
            self._btn_calculate.configure(state="disabled")
            self._btn_clear.configure(state="disabled")
            self._progress_after_id = self._root.after(
                1000, lambda: self._lbl_progress.pack(anchor=tk.W, pady=(5, 0))
            )
        else:
            if self._progress_after_id is not None:
                self._root.after_cancel(self._progress_after_id)
                self._progress_after_id = None
            self._lbl_progress.pack_forget()
            self._btn_clear.configure(state="normal")
            self._update_button_states()

    # ------------------------------------------------------------------
    # History display
    # ------------------------------------------------------------------
    def _refresh_history(self) -> None:
        """Перерисовать журнал истории (Req 8.2, 8.3)."""
        records = self._controller._history.list_newest_first()
        self._history_text.configure(state=tk.NORMAL)
        self._history_text.delete("1.0", tk.END)
        for i, rec in enumerate(records):
            mode_str = (
                "без сопр."
                if rec.input.mode == Mode.NO_DRAG
                else "с сопр."
            )
            line = (
                f"{i+1}. v₀={rec.input.v0} м/с, α={rec.input.alpha_deg}°, "
                f"k={rec.input.k} кг/с [{mode_str}] → "
                f"L={format_meters(rec.result.L)} м, "
                f"H={format_meters(rec.result.H)} м\n"
            )
            self._history_text.insert(tk.END, line)
        self._history_text.configure(state=tk.DISABLED)
