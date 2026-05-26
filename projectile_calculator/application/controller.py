"""Прикладной контроллер расчёта (Requirement 11.1).

Связывает Domain-сервисы с GUI через колбэки. Расчёт выполняется
в рабочем потоке, доставка результатов — через ``schedule_main_thread``.
"""

from __future__ import annotations

import errno
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from projectile_calculator.domain.analytic import AnalyticCalculator
from projectile_calculator.domain.models import (
    CalculationErrorCategory,
    CalculationInput,
    CalculationResult,
    HistoryRecord,
    IntegrationStatus,
    Mode,
    ValidationError,
    ValidationResult,
)
from projectile_calculator.domain.numerical import NumericalIntegrator
from projectile_calculator.domain.validator import Validator
from projectile_calculator.infrastructure.exporter import ExportFormat, Exporter
from projectile_calculator.infrastructure.history import HistoryRepository


class CalculationController:
    """Контроллер расчёта траектории (Req 5.1, 5.2, 5.3, 11.7, 12.7, 12.8).

    Координирует валидацию, запуск расчёта в фоновом потоке,
    доставку результата/ошибки в главный поток и обновление истории.
    """

    def __init__(
        self,
        validator: Validator,
        analytic: AnalyticCalculator,
        numerical: NumericalIntegrator,
        history: HistoryRepository,
        exporter: Exporter,
        on_validation_errors: Callable[[tuple[ValidationError, ...]], None],
        on_calculation_error: Callable[[CalculationErrorCategory], None],
        on_result: Callable[[CalculationResult, CalculationInput], None],
        on_progress_visible: Callable[[bool], None],
        schedule_main_thread: Callable[[Callable[[], None]], None],
    ) -> None:
        self._validator = validator
        self._analytic = analytic
        self._numerical = numerical
        self._history = history
        self._exporter = exporter

        self._on_validation_errors = on_validation_errors
        self._on_calculation_error = on_calculation_error
        self._on_result = on_result
        self._on_progress_visible = on_progress_visible
        self._schedule = schedule_main_thread

        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def stop_event(self) -> threading.Event:
        """Event для кооперативной остановки рабочего потока."""
        return self._stop_event

    @property
    def worker_thread(self) -> threading.Thread | None:
        """Текущий рабочий поток расчёта (или None)."""
        return self._worker_thread

    def on_calculate(
        self,
        raw_v0: str,
        raw_alpha: str,
        raw_k: str,
        mode: Mode,
    ) -> None:
        """Обработчик нажатия «Рассчитать» (Req 3.6, 5.1).

        Синхронная валидация → запуск фонового потока с расчётом.
        """
        result: ValidationResult = self._validator.validate(
            raw_v0, raw_alpha, raw_k, mode
        )

        if not result.is_valid:
            self._on_validation_errors(result.errors)
            return

        assert result.input is not None
        calc_input = result.input

        self._on_progress_visible(True)

        self._worker_thread = threading.Thread(
            target=self._run_calculation,
            args=(calc_input,),
            daemon=True,
        )
        self._worker_thread.start()

    def on_clear(self) -> None:
        """Обработчик «Очистить» (Req 6.2–6.7).

        Дожидается рабочего потока и вызывает UI-колбэк очистки.
        Не очищает историю (Req 6.5).
        """
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.5)
        # UI-очистка делается MainWindow напрямую — контроллер
        # только завершает поток.

    def on_export(
        self,
        target_path: Path,
        fmt: ExportFormat,
    ) -> str | None:
        """Экспорт истории в файл (Req 9.3–9.7).

        Returns:
            None при успехе, строка с категорией ошибки при неудаче.
        """
        if len(self._history) == 0:
            return "empty"

        resolved = self._exporter.ensure_extension(target_path, fmt)
        records = self._history.list_oldest_first()

        try:
            self._exporter.export(records, resolved, fmt)
        except PermissionError:
            return "permission"
        except OSError as exc:
            if exc.errno == errno.ENOSPC:
                return "no_space"
            return "io_error"
        except UnicodeEncodeError:
            return "encoding"

        return None

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------
    def _run_calculation(self, calc_input: CalculationInput) -> None:
        """Выполнить расчёт в рабочем потоке и доставить результат."""
        try:
            if calc_input.mode == Mode.NO_DRAG:
                L, H = self._analytic.compute(calc_input.v0, calc_input.alpha_deg)
            else:
                L, H, status = self._numerical.integrate(
                    calc_input.v0, calc_input.alpha_deg, calc_input.k
                )
                if status == IntegrationStatus.TIMEOUT:
                    self._schedule(
                        lambda: self._deliver_error(CalculationErrorCategory.TIMEOUT)
                    )
                    return

            result = CalculationResult(
                L=L,
                H=H,
                mode=calc_input.mode,
                timestamp=datetime.now(),
            )
            record = HistoryRecord(input=calc_input, result=result)

            self._schedule(lambda: self._deliver_result(result, calc_input, record))

        except OverflowError:
            self._schedule(
                lambda: self._deliver_error(CalculationErrorCategory.OVERFLOW)
            )
        except ZeroDivisionError:
            self._schedule(
                lambda: self._deliver_error(CalculationErrorCategory.DIVISION_BY_ZERO)
            )
        except ValueError:
            self._schedule(
                lambda: self._deliver_error(CalculationErrorCategory.DOMAIN_ERROR)
            )
        except Exception:
            self._schedule(
                lambda: self._deliver_error(CalculationErrorCategory.UNKNOWN)
            )

    def _deliver_result(
        self,
        result: CalculationResult,
        calc_input: CalculationInput,
        record: HistoryRecord,
    ) -> None:
        """Доставить результат в главном потоке."""
        self._on_progress_visible(False)
        self._history.add(record)
        self._on_result(result, calc_input)

    def _deliver_error(self, category: CalculationErrorCategory) -> None:
        """Доставить ошибку расчёта в главном потоке."""
        self._on_progress_visible(False)
        self._on_calculation_error(category)
