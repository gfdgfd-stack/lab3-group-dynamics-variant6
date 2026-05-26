"""Диалоговые окна Калькулятора (Requirement 13.2).

Модальные диалоги для ошибок валидации, ошибок расчёта, ошибок ввода-вывода,
информационных сообщений и выбора пути экспорта.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from projectile_calculator.domain.models import (
    CalculationErrorCategory,
    ValidationError,
)
from projectile_calculator.infrastructure.exporter import ExportFormat

if TYPE_CHECKING:
    pass


def show_validation_errors(
    parent: tk.Tk | tk.Toplevel,
    errors: tuple[ValidationError, ...],
) -> None:
    """Модальный диалог со списком ошибок валидации (Req 11.3, 11.4, 11.5).

    По одной строке на каждое поле с ошибкой. Закрытие — OK / Enter / Esc.
    """
    lines: list[str] = []
    for err in errors:
        lines.append(f"• {err.field_name}: {err.message}")

    message = "\n".join(lines)
    messagebox.showerror("Ошибка валидации", message, parent=parent)


def show_calculation_error(
    parent: tk.Tk | tk.Toplevel,
    category: CalculationErrorCategory,
) -> None:
    """Модальный диалог ошибки расчёта (Req 11.7)."""
    texts = {
        CalculationErrorCategory.OVERFLOW: "Переполнение: результат превышает допустимый диапазон значений.",
        CalculationErrorCategory.DIVISION_BY_ZERO: "Деление на ноль при вычислении.",
        CalculationErrorCategory.DOMAIN_ERROR: "Математическая ошибка: недопустимая операция (например, корень из отрицательного числа).",
        CalculationErrorCategory.TIMEOUT: "Таймаут: расчёт не завершился за допустимое время (T_max = 600 с).",
        CalculationErrorCategory.UNKNOWN: "Неизвестная внутренняя ошибка расчёта.",
    }
    text = texts.get(category, "Неизвестная ошибка расчёта.")
    messagebox.showerror("Ошибка расчёта", text, parent=parent)


def show_io_error(parent: tk.Tk | tk.Toplevel, error_category: str) -> None:
    """Модальный диалог ошибки ввода-вывода при экспорте (Req 9.6, 9.7)."""
    texts = {
        "permission": "Нет прав на запись в указанное расположение.",
        "no_space": "Недостаточно места на диске.",
        "io_error": "Ошибка ввода-вывода: недопустимый путь или общая ошибка файловой системы.",
        "encoding": "Ошибка кодирования данных (UTF-8).",
    }
    text = texts.get(error_category, "Неизвестная ошибка экспорта.")
    messagebox.showerror("Ошибка экспорта", text, parent=parent)


def show_info(parent: tk.Tk | tk.Toplevel, message: str) -> None:
    """Информационный диалог (Req 9.7, 9.9)."""
    messagebox.showinfo("Информация", message, parent=parent)


def ask_save_path(
    parent: tk.Tk | tk.Toplevel,
) -> tuple[Path, ExportFormat] | None:
    """Системный диалог сохранения файла (Req 9.1, 9.2).

    Returns:
        Кортеж (path, format) или None при отмене.
    """
    filepath = filedialog.asksaveasfilename(
        parent=parent,
        title="Экспорт истории вычислений",
        initialfile="projectile_history",
        defaultextension=".txt",
        filetypes=[
            ("Текстовый файл", "*.txt"),
            ("CSV файл", "*.csv"),
        ],
        confirmoverwrite=True,
    )

    if not filepath:
        return None

    path = Path(filepath)
    if path.suffix.lower() == ".csv":
        fmt = ExportFormat.CSV
    else:
        fmt = ExportFormat.TXT

    return path, fmt
