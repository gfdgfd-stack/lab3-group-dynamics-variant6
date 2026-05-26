"""Юнит-тесты CalculationController (Task 11.2).

Validates: Requirements 11.7, 12.7, 12.8.
"""

import threading
import time

import pytest

from projectile_calculator.application.controller import CalculationController
from projectile_calculator.domain.analytic import AnalyticCalculator
from projectile_calculator.domain.models import (
    CalculationErrorCategory,
    CalculationInput,
    CalculationResult,
    Mode,
    ValidationError,
)
from projectile_calculator.domain.numerical import NumericalIntegrator
from projectile_calculator.domain.validator import Validator
from projectile_calculator.infrastructure.exporter import Exporter
from projectile_calculator.infrastructure.history import HistoryRepository


class TestCalculationController:

    def _make_controller(self):
        """Собрать контроллер с мок-колбэками."""
        self.validation_errors = []
        self.calc_errors = []
        self.results = []
        self.progress_states = []
        self.main_thread_calls = []

        def on_validation_errors(errors):
            self.validation_errors.append(errors)

        def on_calculation_error(cat):
            self.calc_errors.append(cat)

        def on_result(res, inp):
            self.results.append((res, inp))

        def on_progress(visible):
            self.progress_states.append(visible)

        def schedule(fn):
            # В тестах просто вызываем сразу
            self.main_thread_calls.append(fn)
            fn()

        controller = CalculationController(
            validator=Validator(),
            analytic=AnalyticCalculator(),
            numerical=NumericalIntegrator(),
            history=HistoryRepository(),
            exporter=Exporter(),
            on_validation_errors=on_validation_errors,
            on_calculation_error=on_calculation_error,
            on_result=on_result,
            on_progress_visible=on_progress,
            schedule_main_thread=schedule,
        )
        return controller

    def test_validation_error_no_history(self):
        """Ошибки валидации → on_validation_errors, нет записи в истории."""
        ctrl = self._make_controller()
        ctrl.on_calculate("", "45", "0", Mode.NO_DRAG)

        assert len(self.validation_errors) == 1
        assert len(self.results) == 0
        assert len(ctrl._history) == 0

    def test_successful_calculation(self):
        """Успешный расчёт → on_result и пополнение истории."""
        ctrl = self._make_controller()
        ctrl.on_calculate("10", "45", "0", Mode.NO_DRAG)

        # Ждём завершения потока
        if ctrl.worker_thread:
            ctrl.worker_thread.join(timeout=5)

        assert len(self.results) == 1
        assert len(ctrl._history) == 1
        res, inp = self.results[0]
        assert res.L > 0
        assert res.H > 0

    def test_progress_shown_on_calculate(self):
        """При запуске расчёта on_progress_visible(True) вызывается."""
        ctrl = self._make_controller()
        ctrl.on_calculate("10", "45", "0", Mode.NO_DRAG)

        if ctrl.worker_thread:
            ctrl.worker_thread.join(timeout=5)

        assert True in self.progress_states

    def test_timeout_error(self):
        """IntegrationStatus.TIMEOUT → on_calculation_error(TIMEOUT)."""
        ctrl = self._make_controller()

        # Подменяем интегратор чтобы он всегда давал TIMEOUT
        from projectile_calculator.domain.models import IntegrationStatus

        original_integrate = ctrl._numerical.integrate

        def fake_integrate(v0, alpha, k, **kwargs):
            return 0.0, 0.0, IntegrationStatus.TIMEOUT

        ctrl._numerical.integrate = fake_integrate
        ctrl.on_calculate("10", "45", "1", Mode.WITH_DRAG)

        if ctrl.worker_thread:
            ctrl.worker_thread.join(timeout=5)

        assert CalculationErrorCategory.TIMEOUT in self.calc_errors

    def test_overflow_error(self):
        """OverflowError от расчётчика → on_calculation_error(OVERFLOW)."""
        ctrl = self._make_controller()

        def fake_compute(v0, alpha):
            raise OverflowError("too big")

        ctrl._analytic.compute = fake_compute
        ctrl.on_calculate("10", "45", "0", Mode.NO_DRAG)

        if ctrl.worker_thread:
            ctrl.worker_thread.join(timeout=5)

        assert CalculationErrorCategory.OVERFLOW in self.calc_errors
