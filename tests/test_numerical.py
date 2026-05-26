"""Юнит-тесты NumericalIntegrator (Task 5.6).

Validates: Requirements 4.1–4.9.
"""

import pytest

from projectile_calculator.domain.analytic import AnalyticCalculator
from projectile_calculator.domain.models import IntegrationStatus
from projectile_calculator.domain.numerical import NumericalIntegrator


@pytest.fixture
def integrator():
    return NumericalIntegrator()


@pytest.fixture
def analytic():
    return AnalyticCalculator()


class TestNumericalIntegrator:

    def test_k0_matches_analytic(self, integrator, analytic):
        """k=0 совпадает с аналитикой ≤ 0.01 м (Req 4.7)."""
        v0, alpha = 50.0, 30.0
        L_a, H_a = analytic.compute(v0, alpha)
        L_n, H_n, status = integrator.integrate(v0, alpha, k=0.0)

        assert status == IntegrationStatus.LANDED
        assert abs(L_a - L_n) <= 0.01
        assert abs(H_a - H_n) <= 0.01

    def test_k0_matches_analytic_steep(self, integrator, analytic):
        """k=0, крутой угол."""
        v0, alpha = 100.0, 80.0
        L_a, H_a = analytic.compute(v0, alpha)
        L_n, H_n, status = integrator.integrate(v0, alpha, k=0.0)

        assert status == IntegrationStatus.LANDED
        assert abs(L_a - L_n) <= 0.01
        assert abs(H_a - H_n) <= 0.01

    def test_drag_reduces_range(self, integrator):
        """Рост k уменьшает L."""
        v0, alpha = 100.0, 45.0
        L1, _, s1 = integrator.integrate(v0, alpha, k=0.0)
        L2, _, s2 = integrator.integrate(v0, alpha, k=1.0)
        L3, _, s3 = integrator.integrate(v0, alpha, k=5.0)

        assert s1 == s2 == s3 == IntegrationStatus.LANDED
        assert L1 > L2 > L3

    def test_drag_reduces_height(self, integrator):
        """Рост k уменьшает H."""
        v0, alpha = 100.0, 45.0
        _, H1, s1 = integrator.integrate(v0, alpha, k=0.0)
        _, H2, s2 = integrator.integrate(v0, alpha, k=1.0)
        _, H3, s3 = integrator.integrate(v0, alpha, k=5.0)

        assert s1 == s2 == s3 == IntegrationStatus.LANDED
        assert H1 > H2 > H3

    def test_timeout_with_small_tmax(self, integrator):
        """Искусственно малый t_max → TIMEOUT."""
        L, H, status = integrator.integrate(100.0, 45.0, k=0.0, t_max=0.001)
        assert status == IntegrationStatus.TIMEOUT

    def test_positive_results(self, integrator):
        """L и H положительны для нормальных входов."""
        L, H, status = integrator.integrate(50.0, 60.0, k=2.0)
        assert status == IntegrationStatus.LANDED
        assert L > 0
        assert H > 0
