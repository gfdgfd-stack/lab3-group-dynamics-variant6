"""Аналитический расчёт траектории без учёта сопротивления воздуха.

Реализует Requirement 3: Режим_Без_Сопротивления.
"""

from __future__ import annotations

import math


# Ускорение свободного падения, м/с² (Req 3.3).
G: float = 9.81


class AnalyticCalculator:
    """Расчёт без учёта сопротивления воздуха (Req 3).

    Использует классические аналитические формулы для тела, брошенного под
    углом к горизонту в однородном поле тяжести без сопротивления среды.
    """

    def compute(self, v0: float, alpha_deg: float) -> tuple[float, float]:
        """Вычислить (L, H) по аналитическим формулам.

        L = v0² · sin(2α) / g            (Req 3.1)
        H = (v0 · sin(α))² / (2g)        (Req 3.2)

        α конвертируется в радианы перед math.sin (Req 3.4).
        Округление не производится — это ответственность
        Presentation-слоя (Req 3.7).

        Args:
            v0: начальная скорость, м/с, 0 < v0 ≤ 1000.
            alpha_deg: угол броска, градусы, 0 < alpha_deg < 90.

        Returns:
            Кортеж (L, H) в метрах без округления.
        """
        alpha_rad = math.radians(alpha_deg)
        L = v0 ** 2 * math.sin(2 * alpha_rad) / G
        H = (v0 * math.sin(alpha_rad)) ** 2 / (2 * G)
        return L, H
