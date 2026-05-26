"""Юнит-тесты Validator (Task 3.5).

Граничные значения, форматы, агрегация ошибок.
Validates: Requirements 2.1–2.10, 11.1–11.3.
"""

import pytest

from projectile_calculator.domain.models import Mode
from projectile_calculator.domain.validator import Validator


@pytest.fixture
def validator():
    return Validator()


class TestParseDecimal:
    """Тесты parse_decimal."""

    def test_integer(self, validator):
        assert validator.parse_decimal("42") == 42.0

    def test_dot_separator(self, validator):
        assert validator.parse_decimal("3.14") == 3.14

    def test_comma_separator(self, validator):
        assert validator.parse_decimal("3,14") == 3.14

    def test_leading_trailing_spaces(self, validator):
        assert validator.parse_decimal("  5.5  ") == 5.5

    def test_negative(self, validator):
        assert validator.parse_decimal("-2.5") == -2.5

    def test_empty_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("")

    def test_whitespace_only_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("   ")

    def test_both_separators_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("1.2,3")

    def test_non_numeric_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("abc")

    def test_inf_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("inf")

    def test_nan_raises(self, validator):
        with pytest.raises(ValueError):
            validator.parse_decimal("nan")


class TestValidate:
    """Тесты Validator.validate."""

    # --- Граничные значения v0 ---
    def test_v0_min_valid(self, validator):
        result = validator.validate("0.01", "45", "0", Mode.NO_DRAG)
        assert result.is_valid
        assert result.input.v0 == 0.01

    def test_v0_max_valid(self, validator):
        result = validator.validate("1000", "45", "0", Mode.NO_DRAG)
        assert result.is_valid
        assert result.input.v0 == 1000.0

    def test_v0_zero_invalid(self, validator):
        result = validator.validate("0", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_v0_negative_invalid(self, validator):
        result = validator.validate("-1", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_v0_above_max_invalid(self, validator):
        result = validator.validate("1001", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid

    # --- Граничные значения alpha ---
    def test_alpha_near_zero_valid(self, validator):
        result = validator.validate("10", "0.01", "0", Mode.NO_DRAG)
        assert result.is_valid

    def test_alpha_zero_invalid(self, validator):
        result = validator.validate("10", "0", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_alpha_90_invalid(self, validator):
        result = validator.validate("10", "90", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_alpha_near_90_valid(self, validator):
        result = validator.validate("10", "89.99", "0", Mode.NO_DRAG)
        assert result.is_valid

    # --- Граничные значения k ---
    def test_k_zero_valid(self, validator):
        result = validator.validate("10", "45", "0", Mode.WITH_DRAG)
        assert result.is_valid
        assert result.input.k == 0.0

    def test_k_max_valid(self, validator):
        result = validator.validate("10", "45", "100", Mode.WITH_DRAG)
        assert result.is_valid
        assert result.input.k == 100.0

    def test_k_above_max_invalid(self, validator):
        result = validator.validate("10", "45", "101", Mode.WITH_DRAG)
        assert not result.is_valid

    def test_k_negative_invalid(self, validator):
        result = validator.validate("10", "45", "-1", Mode.WITH_DRAG)
        assert not result.is_valid

    # --- Формат: запятая и точка ---
    def test_comma_as_separator(self, validator):
        result = validator.validate("10,5", "45", "0", Mode.NO_DRAG)
        assert result.is_valid
        assert result.input.v0 == 10.5

    # --- Длина строки ---
    def test_too_long_string(self, validator):
        result = validator.validate("1234567890123456", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid
        assert result.errors[0].field_id == "v0"

    # --- Число знаков после разделителя ---
    def test_v0_too_many_decimals(self, validator):
        result = validator.validate("1.234", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_alpha_too_many_decimals(self, validator):
        result = validator.validate("10", "45.123", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_k_3_decimals_valid(self, validator):
        result = validator.validate("10", "45", "0.123", Mode.WITH_DRAG)
        assert result.is_valid

    def test_k_4_decimals_invalid(self, validator):
        result = validator.validate("10", "45", "0.1234", Mode.WITH_DRAG)
        assert not result.is_valid

    # --- Пустые и пробельные строки ---
    def test_empty_v0(self, validator):
        result = validator.validate("", "45", "0", Mode.NO_DRAG)
        assert not result.is_valid

    def test_whitespace_alpha(self, validator):
        result = validator.validate("10", "   ", "0", Mode.NO_DRAG)
        assert not result.is_valid

    # --- Режим NO_DRAG игнорирует k ---
    def test_no_drag_ignores_k(self, validator):
        result = validator.validate("10", "45", "invalid", Mode.NO_DRAG)
        assert result.is_valid
        assert result.input.k == 0.0

    # --- Агрегация ошибок ---
    def test_multiple_errors_aggregated(self, validator):
        result = validator.validate("", "", "", Mode.WITH_DRAG)
        assert not result.is_valid
        assert len(result.errors) == 3
        field_ids = {e.field_id for e in result.errors}
        assert field_ids == {"v0", "alpha", "k"}

    def test_two_errors_no_drag(self, validator):
        result = validator.validate("", "", "anything", Mode.NO_DRAG)
        assert not result.is_valid
        assert len(result.errors) == 2
