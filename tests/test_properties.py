"""Property-based тесты (14 Correctness Properties из design.md).

Каждый тест помечен комментарием с номером Property и ссылками
на Requirements.
"""

from __future__ import annotations

import math
import re
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from projectile_calculator.domain.analytic import AnalyticCalculator, G
from projectile_calculator.domain.models import (
    CalculationInput,
    CalculationResult,
    HistoryRecord,
    IntegrationStatus,
    Mode,
)
from projectile_calculator.domain.numerical import NumericalIntegrator
from projectile_calculator.domain.validator import Validator
from projectile_calculator.infrastructure.exporter import ExportFormat, Exporter
from projectile_calculator.infrastructure.history import HistoryRepository
from projectile_calculator.presentation.formatters import format_meters, round_to_centimeter
from projectile_calculator.presentation.main_window import (
    ButtonState,
    FieldState,
    compute_calculate_button_state,
    compute_k_field_state,
)


# =====================================================================
# Стратегии
# =====================================================================

decimal_string_strategy = st.from_regex(r"-?\d{1,4}([.,]\d{1,3})?", fullmatch=True)

v0_strategy = st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
alpha_strategy = st.floats(min_value=0.01, max_value=89.99, allow_nan=False, allow_infinity=False)
k_strategy = st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)


# =====================================================================
# Property 1: Эквивалентность парсинга запятой и точки
# Feature: projectile-calculator, Property 1: parse_decimal comma/dot equivalence
# Validates: Requirements 1.4, 2.8
# =====================================================================

@settings(max_examples=200)
@given(s=decimal_string_strategy)
def test_property_1_parse_decimal_comma_dot_equivalence(s: str):
    """Замена запятой на точку (и наоборот) не меняет результат парсинга."""
    validator = Validator()

    # Строка может содержать только точку или только запятую (не обе)
    if "." in s and "," in s:
        return

    try:
        val_original = validator.parse_decimal(s)
    except ValueError:
        return

    # Заменяем разделитель
    if "." in s:
        s_alt = s.replace(".", ",")
    elif "," in s:
        s_alt = s.replace(",", ".")
    else:
        s_alt = s  # целое число — без разделителя

    val_alt = validator.parse_decimal(s_alt)
    assert val_original == val_alt


# =====================================================================
# Property 2: Корректность валидации формы
# Feature: projectile-calculator, Property 2: validation correctness
# Validates: Requirements 2.1–2.9, 11.1–11.3
# =====================================================================

@settings(max_examples=200)
@given(
    raw_v0=st.text(min_size=0, max_size=20),
    raw_alpha=st.text(min_size=0, max_size=20),
    raw_k=st.text(min_size=0, max_size=20),
    with_drag=st.booleans(),
)
def test_property_2_validation_correctness(raw_v0, raw_alpha, raw_k, with_drag):
    """len(errors) == числу полей с ошибками; is_valid ↔ нет ошибок."""
    validator = Validator()
    mode = Mode.WITH_DRAG if with_drag else Mode.NO_DRAG

    result = validator.validate(raw_v0, raw_alpha, raw_k, mode)

    if result.is_valid:
        assert result.input is not None
        assert len(result.errors) == 0
    else:
        assert result.input is None
        assert len(result.errors) > 0
        # Каждая ошибка ссылается на уникальное поле
        field_ids = [e.field_id for e in result.errors]
        assert len(field_ids) == len(set(field_ids))


# =====================================================================
# Property 3: Аналитическая дальность
# Feature: projectile-calculator, Property 3: analytic range L
# Validates: Requirements 3.1, 3.3, 3.4, 3.5
# =====================================================================

@settings(max_examples=200)
@given(v0=v0_strategy, alpha=alpha_strategy)
def test_property_3_analytic_range(v0, alpha):
    """L совпадает с формулой v0²·sin(2α)/g с точностью 1e-6."""
    calc = AnalyticCalculator()
    L, _H = calc.compute(v0, alpha)
    expected = v0**2 * math.sin(2 * math.radians(alpha)) / G
    assert abs(L - expected) <= 1e-6


# =====================================================================
# Property 4: Аналитическая высота
# Feature: projectile-calculator, Property 4: analytic height H
# Validates: Requirements 3.2, 3.3, 3.4, 3.5
# =====================================================================

@settings(max_examples=200)
@given(v0=v0_strategy, alpha=alpha_strategy)
def test_property_4_analytic_height(v0, alpha):
    """H совпадает с формулой (v0·sin(α))²/(2g) с точностью 1e-6."""
    calc = AnalyticCalculator()
    _L, H = calc.compute(v0, alpha)
    expected = (v0 * math.sin(math.radians(alpha)))**2 / (2 * G)
    assert abs(H - expected) <= 1e-6


# =====================================================================
# Property 5: Согласованность режимов при k = 0
# Feature: projectile-calculator, Property 5: mode consistency at k=0
# Validates: Requirements 4.1, 4.2, 4.4, 4.5, 4.7
# =====================================================================

@settings(max_examples=200)
@given(v0=v0_strategy, alpha=alpha_strategy)
def test_property_5_mode_consistency_k0(v0, alpha):
    """При k=0 численный результат совпадает с аналитическим ± 0.01 м."""
    analytic = AnalyticCalculator()
    numerical = NumericalIntegrator()

    L_a, H_a = analytic.compute(v0, alpha)
    L_n, H_n, status = numerical.integrate(v0, alpha, k=0.0)

    assert status == IntegrationStatus.LANDED
    assert abs(L_a - L_n) <= 0.01, f"L diff: {abs(L_a - L_n)}"
    assert abs(H_a - H_n) <= 0.01, f"H diff: {abs(H_a - H_n)}"


# =====================================================================
# Property 6: Завершение численного интегрирования
# Feature: projectile-calculator, Property 6: numerical integration terminates
# Validates: Requirements 4.3
# =====================================================================

@settings(max_examples=200)
@given(v0=v0_strategy, alpha=alpha_strategy, k=k_strategy)
def test_property_6_integration_terminates(v0, alpha, k):
    """Интегрирование всегда завершается со статусом LANDED."""
    numerical = NumericalIntegrator()
    L, H, status = numerical.integrate(v0, alpha, k)
    assert status == IntegrationStatus.LANDED


# =====================================================================
# Property 7: Точность численного интегрирования
# Feature: projectile-calculator, Property 7: numerical accuracy
# Validates: Requirements 4.6
# =====================================================================

@pytest.mark.slow
@settings(max_examples=50)
@given(
    v0=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    alpha=st.floats(min_value=5.0, max_value=85.0, allow_nan=False, allow_infinity=False),
    k=st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False),
)
def test_property_7_numerical_accuracy(v0, alpha, k):
    """dt=0.001 vs dt=1e-5 reference: разница ≤ 0.01 м."""
    numerical = NumericalIntegrator()

    L_n, H_n, status_n = numerical.integrate(v0, alpha, k, dt=0.001)
    L_ref, H_ref, status_ref = numerical.integrate(v0, alpha, k, dt=1e-5)

    assume(status_n == IntegrationStatus.LANDED)
    assume(status_ref == IntegrationStatus.LANDED)

    assert abs(L_n - L_ref) <= 0.01, f"L diff: {abs(L_n - L_ref)}"
    assert abs(H_n - H_ref) <= 0.01, f"H diff: {abs(H_n - H_ref)}"


# =====================================================================
# Property 8: Метаморфическая монотонность по k
# Feature: projectile-calculator, Property 8: monotonicity in k
# Validates: Requirements 4.1
# =====================================================================

@settings(max_examples=200)
@given(
    v0=v0_strategy,
    alpha=alpha_strategy,
    k1=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
    k2=st.floats(min_value=0.0, max_value=50.0, allow_nan=False, allow_infinity=False),
)
def test_property_8_monotonicity_in_k(v0, alpha, k1, k2):
    """При k1 < k2: L(k1) >= L(k2) - 0.01 и H(k1) >= H(k2) - 0.01."""
    assume(k1 < k2)
    assume(k2 - k1 > 0.001)

    numerical = NumericalIntegrator()
    L1, H1, s1 = numerical.integrate(v0, alpha, k1)
    L2, H2, s2 = numerical.integrate(v0, alpha, k2)

    assume(s1 == IntegrationStatus.LANDED)
    assume(s2 == IntegrationStatus.LANDED)

    assert L1 >= L2 - 0.01, f"L1={L1}, L2={L2}"
    assert H1 >= H2 - 0.01, f"H1={H1}, H2={H2}"


# =====================================================================
# Property 9: Идемпотентность округления и формат вывода
# Feature: projectile-calculator, Property 9: rounding idempotency and format
# Validates: Requirements 3.7, 4.9, 5.4
# =====================================================================

@settings(max_examples=200)
@given(x=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_property_9_rounding_idempotency_and_format(x):
    r"""Идемпотентность округления; кратность 0.01; формат ^\d+,\d{2}$."""
    r1 = round_to_centimeter(x)
    r2 = round_to_centimeter(r1)
    assert r1 == r2, "Идемпотентность нарушена"

    # Кратность 0.01 (с допуском для FP-арифметики)
    assert abs(r1 * 100 - round(r1 * 100)) < 1e-6

    # Формат вывода
    formatted = format_meters(x)
    assert re.match(r"^\d+,\d{2}$", formatted), f"Bad format: {formatted}"


# =====================================================================
# Property 10: FIFO-инварианты Журнала_Истории
# Feature: projectile-calculator, Property 10: history FIFO invariants
# Validates: Requirements 8.1, 8.3, 8.6
# =====================================================================

def _make_record(v0: float, alpha: float) -> HistoryRecord:
    """Вспомогательная фабрика записей истории."""
    from datetime import datetime
    inp = CalculationInput(v0=v0, alpha_deg=alpha, k=0.0, mode=Mode.NO_DRAG)
    res = CalculationResult(L=v0, H=alpha, mode=Mode.NO_DRAG, timestamp=datetime.now())
    return HistoryRecord(input=inp, result=res)


@settings(max_examples=200)
@given(n=st.integers(min_value=0, max_value=200))
def test_property_10_history_fifo(n):
    """FIFO-инварианты: len, порядок, ёмкость 100."""
    repo = HistoryRepository()

    records = [_make_record(float(i), 45.0) for i in range(1, n + 1)]
    for rec in records:
        repo.add(rec)

    # Длина
    assert len(repo) == min(n, 100)

    if n > 0:
        newest = repo.list_newest_first()
        oldest = repo.list_oldest_first()

        # Первая в newest — последняя добавленная
        assert newest[0] == records[-1]

        # newest == reversed(oldest)
        assert newest == tuple(reversed(oldest))

        # При N > 100 последние 100 не потеряны
        if n > 100:
            for rec in records[-100:]:
                assert rec in newest


# =====================================================================
# Property 11: Round-trip экспорта истории
# Feature: projectile-calculator, Property 11: export round-trip
# Validates: Requirements 9.3, 9.4, 9.5
# =====================================================================

@settings(max_examples=50)
@given(
    n=st.integers(min_value=1, max_value=10),
    v0_list=st.lists(v0_strategy, min_size=1, max_size=10),
)
def test_property_11_export_round_trip(n, v0_list):
    """Экспорт CSV и чтение обратно совпадают по полям."""
    from datetime import datetime

    records = []
    for i, v0 in enumerate(v0_list[:n]):
        inp = CalculationInput(v0=v0, alpha_deg=45.0, k=0.0, mode=Mode.NO_DRAG)
        res = CalculationResult(L=v0 * 2, H=v0, mode=Mode.NO_DRAG, timestamp=datetime.now())
        records.append(HistoryRecord(input=inp, result=res))

    exporter = Exporter()

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "test.csv"
        exporter.export(tuple(records), csv_path, ExportFormat.CSV)

        # Парсим обратно
        lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
        assert lines[0] == "v0_m_s;alpha_deg;k;mode;L_m;H_m"

        for i, rec in enumerate(records):
            parts = lines[i + 1].split(";")
            assert float(parts[0]) == pytest.approx(rec.input.v0, abs=0.01)
            assert float(parts[4]) == pytest.approx(rec.result.L, abs=0.01)
            assert float(parts[5]) == pytest.approx(rec.result.H, abs=0.01)


# =====================================================================
# Property 12: Авто-расширение пути экспорта
# Feature: projectile-calculator, Property 12: export path auto-extension
# Validates: Requirements 9.11
# =====================================================================

@settings(max_examples=200)
@given(
    name=st.from_regex(r"[a-z]{1,10}", fullmatch=True),
    fmt=st.sampled_from([ExportFormat.TXT, ExportFormat.CSV]),
)
def test_property_12_export_auto_extension(name, fmt):
    """Идемпотентность ensure_extension; правильное расширение."""
    path = Path(f"/tmp/{name}")
    result = Exporter.ensure_extension(path, fmt)

    expected_suffix = f".{fmt.value}"
    assert result.suffix == expected_suffix

    # Идемпотентность
    result2 = Exporter.ensure_extension(result, fmt)
    assert result == result2


# =====================================================================
# Property 13: Активность кнопки «Рассчитать» эквивалентна валидности формы
# Feature: projectile-calculator, Property 13: calculate button state
# Validates: Requirements 13.4, 13.5
# =====================================================================

@settings(max_examples=200)
@given(
    raw_v0=st.text(min_size=0, max_size=5),
    raw_alpha=st.text(min_size=0, max_size=5),
    raw_k=st.text(min_size=0, max_size=5),
    with_drag=st.booleans(),
)
def test_property_13_calculate_button_state(raw_v0, raw_alpha, raw_k, with_drag):
    """Кнопка ENABLED ⇔ все обязательные поля непусты."""
    mode = Mode.WITH_DRAG if with_drag else Mode.NO_DRAG
    state = compute_calculate_button_state(raw_v0, raw_alpha, raw_k, mode)

    v0_filled = bool(raw_v0.strip())
    alpha_filled = bool(raw_alpha.strip())
    k_filled = bool(raw_k.strip()) if mode == Mode.WITH_DRAG else True

    if v0_filled and alpha_filled and k_filled:
        assert state == ButtonState.ENABLED
    else:
        assert state == ButtonState.DISABLED


# =====================================================================
# Property 14: Инвариант readonly для поля k
# Feature: projectile-calculator, Property 14: k field readonly invariant
# Validates: Requirements 1.8
# =====================================================================

@settings(max_examples=200)
@given(with_drag=st.booleans())
def test_property_14_k_field_readonly(with_drag):
    """READ_ONLY ⇔ mode == NO_DRAG."""
    mode = Mode.WITH_DRAG if with_drag else Mode.NO_DRAG
    state = compute_k_field_state(mode)

    if mode == Mode.NO_DRAG:
        assert state == FieldState.READ_ONLY
    else:
        assert state == FieldState.EDITABLE
