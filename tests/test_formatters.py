"""Юнит-тесты форматтеров (Task 6.3).

Validates: Requirements 5.4.
"""

import pytest

from projectile_calculator.presentation.formatters import format_meters, round_to_centimeter


class TestRoundToCentimeter:

    def test_zero(self):
        assert round_to_centimeter(0) == 0.0

    def test_half_up_005(self):
        """0.005 → 0.01 (round-half-away-from-zero)."""
        assert round_to_centimeter(0.005) == 0.01

    def test_half_up_015(self):
        """0.015 → 0.02."""
        assert round_to_centimeter(0.015) == 0.02

    def test_negative_half(self):
        """-0.005 → -0.01."""
        assert round_to_centimeter(-0.005) == -0.01

    def test_exact_value(self):
        assert round_to_centimeter(1.23) == 1.23

    def test_large_value(self):
        assert round_to_centimeter(12345.678) == 12345.68

    def test_idempotent(self):
        val = round_to_centimeter(3.14159)
        assert round_to_centimeter(val) == val


class TestFormatMeters:

    def test_zero(self):
        assert format_meters(0) == "0,00"

    def test_integer(self):
        assert format_meters(5) == "5,00"

    def test_one_decimal(self):
        assert format_meters(1234.5) == "1234,50"

    def test_two_decimals(self):
        assert format_meters(7.89) == "7,89"

    def test_no_dot_in_output(self):
        result = format_meters(10.123)
        assert "." not in result

    def test_no_spaces_in_output(self):
        result = format_meters(100000.5)
        assert " " not in result

    def test_comma_as_separator(self):
        result = format_meters(3.14)
        assert "," in result
