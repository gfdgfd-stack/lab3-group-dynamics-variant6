"""Smoke-тесты (Task 14.2).

Validates: Requirements 12.2.
"""

import os
import sys

import pytest


@pytest.fixture
def has_display():
    """Проверяем доступность дисплея."""
    if sys.platform == "win32":
        return True
    if os.environ.get("DISPLAY"):
        return True
    pytest.skip("No display available")


def test_import_main_window(has_display):
    """Импорт main_window без исключений."""
    import tkinter as tk
    from projectile_calculator.presentation.main_window import MainWindow

    # Только проверяем что импорт проходит
    assert MainWindow is not None


def test_create_tk_root(has_display):
    """Создание Tk root без исключений."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()  # Скрываем окно
    root.destroy()
