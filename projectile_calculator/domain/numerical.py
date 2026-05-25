"""Численное интегрирование уравнений движения с сопротивлением воздуха.

Реализует Requirement 4: Режим_С_Сопротивлением.

Слой Domain не имеет побочных эффектов и не зависит от Tkinter, файловой
системы или иных внешних ресурсов. Расчёт выполняется в чистом Python
без сторонних библиотек (Req 12.3, 12.4).
"""

from __future__ import annotations

import math

from projectile_calculator.domain.analytic import G
from projectile_calculator.domain.models import IntegrationStatus


# Тип состояния (x, y, vx, vy).
_State = tuple[float, float, float, float]


class NumericalIntegrator:
    """Численное решение уравнений движения методом Рунге-Кутты 4-го порядка.

    Уравнения движения для модели вязкого сопротивления F = -k·v
    при единичной массе тела (m = 1 кг)::

        dx/dt  =  vx
        dy/dt  =  vy
        dvx/dt = -k · vx
        dvy/dt = -k · vy − g

    где g = 9.81 м/с² импортируется из ``analytic`` для единства источника
    истины (Req 3.3, 4.1).

    Условия завершения интегрирования (Req 4.3):

    * **LANDED** — y пересекло уровень 0 сверху вниз (vy < 0). Точка
      падения и дальность L определяются линейной интерполяцией между
      двумя последними шагами RK4 (Req 4.4).
    * **TIMEOUT** — достигнут предел ``t_max`` до пересечения y = 0
      (Req 4.3, 4.8). Вызывающий код обязан трактовать это как ошибку
      и не отображать L и H пользователю.

    H — максимум y по всей траектории, отслеживается на каждом шаге
    (Req 4.5).

    Метод :meth:`integrate` не бросает исключений на корректных входах:
    проверка диапазона аргументов — ответственность
    :class:`projectile_calculator.domain.validator.Validator`.
    """

    DEFAULT_DT: float = 0.001        # Шаг интегрирования, с (Req 4.2).
    DEFAULT_T_MAX: float = 600.0     # Предельное время, с (Req 4.3, 4.8).
    MASS: float = 1.0                # Масса тела, кг (m = 1 по ТЗ).

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def integrate(
        self,
        v0: float,
        alpha_deg: float,
        k: float,
        dt: float = DEFAULT_DT,
        t_max: float = DEFAULT_T_MAX,
    ) -> tuple[float, float, IntegrationStatus]:
        """Запустить численное интегрирование траектории.

        Args:
            v0: начальная скорость, м/с (v₀ > 0).
            alpha_deg: угол броска, градусы (0 < α < 90).
            k: коэффициент сопротивления, кг/с (k ≥ 0).
            dt: шаг интегрирования, с. По умолчанию
                :attr:`DEFAULT_DT` = 0.001 с.
            t_max: предельное время интегрирования, с. По умолчанию
                :attr:`DEFAULT_T_MAX` = 600 с.

        Returns:
            Кортеж ``(L, H, status)``:

            * ``status == IntegrationStatus.LANDED`` — ``L`` есть x в
              момент пересечения уровня y = 0, найденный линейной
              интерполяцией между двумя последними шагами RK4
              (Req 4.4); ``H`` — максимум y за весь полёт (Req 4.5).
            * ``status == IntegrationStatus.TIMEOUT`` — ``L`` равен
              последней горизонтальной координате тела, ``H`` — максимуму
              y за пройденный участок интегрирования. Это
              сигнал об ошибке для Application-слоя (Req 4.8).

        Notes:
            Для корректных входных данных функция не возбуждает
            исключений. Поведение на некорректных входах (v₀ ≤ 0,
            α вне (0, 90), k < 0, dt ≤ 0, t_max ≤ 0) не определено —
            проверки выполняет ``Validator``.
        """
        alpha_rad = math.radians(alpha_deg)
        vx0 = v0 * math.cos(alpha_rad)
        vy0 = v0 * math.sin(alpha_rad)

        # Текущее и предыдущее состояния. Стартуем из точки броска
        # (x = 0, y = 0).
        x_prev = 0.0
        y_prev = 0.0
        state: _State = (0.0, 0.0, vx0, vy0)

        # Максимум y за всю траекторию (Req 4.5). Начинается с y(0) = 0,
        # так как стартовая высота — 0.
        H = 0.0

        t = 0.0
        while t < t_max:
            x_curr, y_curr, _vx_curr, vy_curr = self._rk4_step(state, dt, k)
            t += dt

            if y_curr > H:
                H = y_curr

            # Условие приземления (Req 4.3, 4.4): y пересекло уровень 0
            # сверху вниз при vy < 0. На штатной траектории это происходит
            # после восхождения; для вырожденных входов (очень малое vy₀,
            # уже за один шаг переходящее в отрицательную область) условие
            # сработает на первом же шаге, а линейная интерполяция от
            # стартовой точки (0, 0) корректно даст L ≈ 0.
            if y_curr <= 0.0 and vy_curr < 0.0:
                denom = y_prev - y_curr
                if denom > 0.0:
                    fraction = y_prev / denom
                else:
                    # Защита от деления на ноль в граничном случае
                    # y_prev == y_curr == 0: считаем точку падения
                    # совпадающей с предыдущим шагом.
                    fraction = 0.0
                L = x_prev + fraction * (x_curr - x_prev)
                return L, H, IntegrationStatus.LANDED

            x_prev = x_curr
            y_prev = y_curr
            state = (x_curr, y_curr, _vx_curr, vy_curr)

        # Достигнут t_max до пересечения y = 0 (Req 4.3, 4.8).
        return state[0], H, IntegrationStatus.TIMEOUT

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    @staticmethod
    def _derivatives(state: _State, k: float) -> _State:
        """Правая часть системы ОДУ.

        Принимает состояние ``(x, y, vx, vy)`` и возвращает кортеж
        производных ``(dx/dt, dy/dt, dvx/dt, dvy/dt)``. Время в правой
        части явно не входит — система автономна.
        """
        _x, _y, vx, vy = state
        return (vx, vy, -k * vx, -k * vy - G)

    @classmethod
    def _rk4_step(
        cls,
        state: _State,
        dt: float,
        k: float,
    ) -> _State:
        """Один шаг классического метода Рунге-Кутты 4-го порядка.

        Стандартная схема для автономной системы dy/dt = f(y)::

            k1 = f(y)
            k2 = f(y + dt/2 · k1)
            k3 = f(y + dt/2 · k2)
            k4 = f(y + dt   · k3)
            y' = y + dt/6 · (k1 + 2·k2 + 2·k3 + k4)
        """
        x, y, vx, vy = state
        half = 0.5 * dt
        sixth = dt / 6.0

        k1 = cls._derivatives(state, k)

        s2: _State = (
            x + half * k1[0],
            y + half * k1[1],
            vx + half * k1[2],
            vy + half * k1[3],
        )
        k2 = cls._derivatives(s2, k)

        s3: _State = (
            x + half * k2[0],
            y + half * k2[1],
            vx + half * k2[2],
            vy + half * k2[3],
        )
        k3 = cls._derivatives(s3, k)

        s4: _State = (
            x + dt * k3[0],
            y + dt * k3[1],
            vx + dt * k3[2],
            vy + dt * k3[3],
        )
        k4 = cls._derivatives(s4, k)

        return (
            x + sixth * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]),
            y + sixth * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]),
            vx + sixth * (k1[2] + 2.0 * k2[2] + 2.0 * k3[2] + k4[2]),
            vy + sixth * (k1[3] + 2.0 * k2[3] + 2.0 * k3[3] + k4[3]),
        )
