"""Юнит-тесты AnalyticCalculator (Task 4.4).

Validates: Requirements 3.1–3.7.
"""

import math

import pytest

from projectile_calculator.domain.analytic import AnalyticCalculator, G


@pytest.fixture
def calc():
    return AnalyticCalculator()


class TestAnalyticCalculator:

    def test_reference_example(self, calc):
        """v0=10, α=45°: L≈10.194 м, H≈2.548 м."""
        L, H = calc.compute(10.0, 45.0)
        assert L == pytest.approx(10.194, abs=0.001)
        assert H == pytest.approx(2.548, abs=0.001)

    def test_symmetry(self, calc):
        """α и 90°−α дают одинаковую дальность."""
        L1, _ = calc.compute(50.0, 30.0)
        L2, _ = calc.compute(50.0, 60.0)
        assert L1 == pytest.approx(L2, abs=1e-9)

    def test_45_gives_max_range(self, calc):
        """α=45° даёт максимальную дальность при фиксированном v0."""
        v0 = 100.0
        L_45, _ = calc.compute(v0, 45.0)
        for angle in [10, 20, 30, 40, 50, 60, 70, 80]:
            L_other, _ = calc.compute(v0, float(angle))
            assert L_45 >= L_other - 1e-9

    def test_small_angle(self, calc):
        """Малый угол — L и H положительны."""
        L, H = calc.compute(100.0, 1.0)
        assert L > 0
        assert H > 0

    def test_large_angle(self, calc):
        """Угол близкий к 90° — малая L, большая H."""
        L, H = calc.compute(100.0, 89.0)
        assert L < 50
        assert H > 400
