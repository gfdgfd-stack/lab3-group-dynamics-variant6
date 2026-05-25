"""Domain models for the projectile calculator.

Все value-объекты слоя Domain: перечисления режимов и категорий ошибок,
а также иммутабельные dataclass-ы для входа, результата, ошибок валидации
и записей Журнала_Истории.

Этот модуль не имеет побочных эффектов и не зависит от Tkinter, файловой
системы или иных внешних ресурсов — он используется как контракт между
слоями Domain, Application и Infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Mode(Enum):
    """Режим расчёта траектории."""

    NO_DRAG = "no_drag"          # Режим_Без_Сопротивления (Req 1.7)
    WITH_DRAG = "with_drag"      # Режим_С_Сопротивлением (Req 1.6)


class IntegrationStatus(Enum):
    """Статус завершения численного интегрирования."""

    LANDED = "landed"            # пересечение y = 0 при vy < 0 (Req 4.4)
    TIMEOUT = "timeout"          # достигнут T_max = 600 с (Req 4.3, 4.8)


class CalculationErrorCategory(Enum):
    """Категория внутренней ошибки расчёта (Req 11.7)."""

    OVERFLOW = "overflow"
    DIVISION_BY_ZERO = "division_by_zero"
    DOMAIN_ERROR = "domain_error"        # sqrt отрицательного, log неположительного
    TIMEOUT = "timeout"                  # T_max превышен (Req 4.8)
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CalculationInput:
    """Уже валидированные входные данные расчёта.

    Создаётся только Validator-ом. Все значения — в SI-единицах.

    Инварианты (обеспечиваются Validator-ом, Req 1.1, 1.2, 1.3):
        0.01 ≤ v0 ≤ 1000 (м/с)
        0 < alpha_deg < 90 (градусы)
        0 ≤ k ≤ 100 (кг/с)
    """

    v0: float
    alpha_deg: float
    k: float
    mode: Mode


@dataclass(frozen=True)
class CalculationResult:
    """Результат успешного расчёта (Req 3.1, 3.2, 4.1).

    Инварианты:
        L ≥ 0
        H ≥ 0
    """

    L: float
    H: float
    mode: Mode
    timestamp: datetime


@dataclass(frozen=True)
class ValidationError:
    """Описание одной ошибки валидации одного поля (Req 2, Req 11.1, 11.2).

    Поля:
        field_name: подпись поля как в GUI
            (например, "Начальная скорость v₀").
        field_id: технический идентификатор поля
            ("v0" | "alpha" | "k").
        raw_value: исходная строка, введённая пользователем.
        message: текст для модального диалога ошибки.
        allowed_min: минимально допустимое значение (None, если неприменимо).
        allowed_max: максимально допустимое значение (None, если неприменимо).
        format_hint: описание допустимого формата (разделитель, число знаков
            после разделителя, максимальная длина строки).
    """

    field_name: str
    field_id: str
    raw_value: str
    message: str
    allowed_min: float | None
    allowed_max: float | None
    format_hint: str


@dataclass(frozen=True)
class ValidationResult:
    """Агрегированный результат валидации Формы_Ввода (Req 2.9, 11.3).

    Если форма валидна, поле ``input`` содержит готовый ``CalculationInput``,
    а ``errors`` — пустой кортеж. При наличии ошибок ``input is None``,
    а ``errors`` содержит по одному ``ValidationError`` на каждое поле,
    не прошедшее проверку.
    """

    input: CalculationInput | None
    errors: tuple[ValidationError, ...] = ()

    @property
    def is_valid(self) -> bool:
        """True ⇔ есть валидный input и нет накопленных ошибок."""
        return self.input is not None and not self.errors


@dataclass(frozen=True)
class HistoryRecord:
    """Запись в Журнале_Истории (Req 8.1).

    Инвариант:
        input.mode == result.mode
    """

    input: CalculationInput
    result: CalculationResult
