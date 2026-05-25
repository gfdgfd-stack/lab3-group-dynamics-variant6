"""Validator for raw user input from the GUI form.

Слой Domain не зависит от Tkinter и не выполняет побочных эффектов:
``Validator`` принимает уже извлечённые из виджетов строковые значения и
работает только с ними. Полная валидация формы (метод
:meth:`Validator.validate`) собирает все ошибки за один проход и
возвращает агрегированный :class:`ValidationResult` (Req 2.9, 11.3).
"""

from __future__ import annotations

import re

from projectile_calculator.domain.models import (
    CalculationInput,
    Mode,
    ValidationError,
    ValidationResult,
)


# Строгий формат десятичного числа: опциональный знак, цифры до разделителя,
# опциональная дробная часть с точкой или запятой. Не допускает научной
# записи и пропуска цифр перед/после разделителя.
_DECIMAL_PATTERN = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


class Validator:
    """Валидация введённых пользователем строк (Req 2).

    Не зависит от GUI: принимает уже извлечённые строковые значения трёх
    полей Формы_Ввода и режима расчёта, возвращает
    :class:`ValidationResult` со всеми ошибками за один проход
    (Req 2.9, 11.3).

    В режиме :attr:`Mode.NO_DRAG` поле ``k`` игнорируется полностью
    (Req 1.8): его строковое значение не разбирается и не проверяется,
    а итоговый :class:`CalculationInput` получает ``k = 0.0``.
    """

    # ---------------------------------------------------------------------
    # Диапазоны и формат значений (Req 1.1, 1.2, 1.3, 2.1, 2.2, 2.3)
    # ---------------------------------------------------------------------
    V0_MIN: float = 0.01
    V0_MAX: float = 1000.0
    V0_DECIMALS: int = 2
    V0_MIN_INCLUSIVE: bool = True
    V0_MAX_INCLUSIVE: bool = True

    ALPHA_MIN: float = 0.0
    ALPHA_MAX: float = 90.0
    ALPHA_DECIMALS: int = 2
    ALPHA_MIN_INCLUSIVE: bool = False
    ALPHA_MAX_INCLUSIVE: bool = False

    K_MIN: float = 0.0
    K_MAX: float = 100.0
    K_DECIMALS: int = 3
    K_MIN_INCLUSIVE: bool = True
    K_MAX_INCLUSIVE: bool = True

    MAX_INPUT_LENGTH: int = 15

    # Подписи полей в точности так, как они отображаются в GUI
    # (Req 11.1: «название поля в точности так, как оно отображается
    # в виде подписи (label) рядом с этим полем»).
    FIELD_V0_NAME: str = "Начальная скорость v₀"
    FIELD_ALPHA_NAME: str = "Угол броска α"
    FIELD_K_NAME: str = "Коэффициент сопротивления k"

    # Текстовое описание диапазонов для сообщений об ошибках (Req 11.2).
    _V0_RANGE_TEXT: str = "0 < v₀ ≤ 1000 (м/с)"
    _ALPHA_RANGE_TEXT: str = "0 < α < 90 (градусов)"
    _K_RANGE_TEXT: str = "0 ≤ k ≤ 100 (кг/с)"

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def validate(
        self,
        raw_v0: str,
        raw_alpha: str,
        raw_k: str,
        mode: Mode,
    ) -> ValidationResult:
        """Полная валидация Формы_Ввода.

        Алгоритм за один проход для каждого применимого поля:

        1. Проверка непустоты после ``strip`` (Req 2.7).
        2. Проверка длины строки ≤ :attr:`MAX_INPUT_LENGTH` (Req 2.1–2.3).
        3. Проверка соответствия формату десятичного числа
           (Req 1.4, 2.8: точка или запятая как разделитель).
        4. Проверка количества знаков после разделителя для поля
           (2 для v₀ и α, 3 для k; Req 2.1, 2.2, 2.3).
        5. Парсинг строки во ``float`` через :meth:`parse_decimal`.
        6. Проверка диапазона значения (Req 2.4, 2.5, 2.6).

        Поле ``k`` валидируется только при ``mode == Mode.WITH_DRAG``.
        В режиме ``Mode.NO_DRAG`` строковое значение ``raw_k`` полностью
        игнорируется, а в итоговый :class:`CalculationInput` подставляется
        ``k = 0.0`` (Req 1.8).

        На каждое поле, не прошедшее проверку, формируется ровно один
        :class:`ValidationError` с первой обнаруженной причиной — таким
        образом ``len(errors)`` равно числу полей с ошибками
        (Req 2.9, 11.3).

        Args:
            raw_v0: содержимое поля «Начальная скорость v₀».
            raw_alpha: содержимое поля «Угол броска α».
            raw_k: содержимое поля «Коэффициент сопротивления k»
                (используется только при ``mode == Mode.WITH_DRAG``).
            mode: текущий режим расчёта.

        Returns:
            :class:`ValidationResult` с готовым :class:`CalculationInput`
            при успехе или с кортежем :class:`ValidationError` при наличии
            ошибок.
        """

        errors: list[ValidationError] = []

        v0_error, v0_value = self._validate_field(
            field_id="v0",
            field_name=self.FIELD_V0_NAME,
            raw=raw_v0,
            decimals_max=self.V0_DECIMALS,
            min_value=self.V0_MIN,
            max_value=self.V0_MAX,
            min_inclusive=self.V0_MIN_INCLUSIVE,
            max_inclusive=self.V0_MAX_INCLUSIVE,
            range_text=self._V0_RANGE_TEXT,
        )
        if v0_error is not None:
            errors.append(v0_error)

        alpha_error, alpha_value = self._validate_field(
            field_id="alpha",
            field_name=self.FIELD_ALPHA_NAME,
            raw=raw_alpha,
            decimals_max=self.ALPHA_DECIMALS,
            min_value=self.ALPHA_MIN,
            max_value=self.ALPHA_MAX,
            min_inclusive=self.ALPHA_MIN_INCLUSIVE,
            max_inclusive=self.ALPHA_MAX_INCLUSIVE,
            range_text=self._ALPHA_RANGE_TEXT,
        )
        if alpha_error is not None:
            errors.append(alpha_error)

        if mode == Mode.WITH_DRAG:
            k_error, k_value = self._validate_field(
                field_id="k",
                field_name=self.FIELD_K_NAME,
                raw=raw_k,
                decimals_max=self.K_DECIMALS,
                min_value=self.K_MIN,
                max_value=self.K_MAX,
                min_inclusive=self.K_MIN_INCLUSIVE,
                max_inclusive=self.K_MAX_INCLUSIVE,
                range_text=self._K_RANGE_TEXT,
            )
            if k_error is not None:
                errors.append(k_error)
        else:
            # NO_DRAG: поле k игнорируется полностью (Req 1.8).
            k_value = 0.0

        if errors:
            return ValidationResult(input=None, errors=tuple(errors))

        # Все поля прошли проверку — собираем валидированный вход.
        # ``v0_value`` и ``alpha_value`` гарантированно не None, так как
        # соответствующих ошибок не было.
        assert v0_value is not None
        assert alpha_value is not None
        return ValidationResult(
            input=CalculationInput(
                v0=v0_value,
                alpha_deg=alpha_value,
                k=k_value,
                mode=mode,
            ),
            errors=(),
        )

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _validate_field(
        self,
        *,
        field_id: str,
        field_name: str,
        raw: str,
        decimals_max: int,
        min_value: float,
        max_value: float,
        min_inclusive: bool,
        max_inclusive: bool,
        range_text: str,
    ) -> tuple[ValidationError | None, float | None]:
        """Проверить одно поле формы.

        Возвращает кортеж ``(error, value)``. При успехе ``error is None``
        и ``value`` содержит распарсенное число. При ошибке ``value is
        None`` и ``error`` содержит описание первой обнаруженной проблемы.
        """

        # Защита от случая, когда в качестве ввода переданы не-строковые
        # значения (например, ``None`` от незаполненного StringVar).
        if raw is None:
            raw = ""
        elif not isinstance(raw, str):
            raw = str(raw)

        format_hint = (
            "Целое или десятичное число; десятичный разделитель — точка или запятая; "
            f"не более {decimals_max} знаков после разделителя; "
            f"длина строки не более {self.MAX_INPUT_LENGTH} символов."
        )

        def make_error(message: str) -> ValidationError:
            return ValidationError(
                field_name=field_name,
                field_id=field_id,
                raw_value=raw,
                message=message,
                allowed_min=min_value,
                allowed_max=max_value,
                format_hint=format_hint,
            )

        stripped = raw.strip()

        # 1. Непустота (Req 2.7): пустая строка или только пробельные символы.
        if not stripped:
            message = (
                f"Поле «{field_name}» не должно быть пустым. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        # 2. Длина строки (Req 2.1, 2.2, 2.3): проверяем исходное значение,
        # как оно есть в поле ввода.
        if len(raw) > self.MAX_INPUT_LENGTH:
            message = (
                f"Длина значения поля «{field_name}» превышает "
                f"{self.MAX_INPUT_LENGTH} символов. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        # 3. Формат десятичного числа (Req 1.4, 2.4–2.6, 2.8).
        if not _DECIMAL_PATTERN.match(stripped):
            message = (
                f"Значение поля «{field_name}» не является числом. "
                "Допустимый формат: целое или десятичное число; десятичный разделитель — "
                "точка или запятая. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        # 4. Количество знаков после разделителя (Req 2.1, 2.2, 2.3).
        normalized = stripped.replace(",", ".")
        if "." in normalized:
            fractional = normalized.split(".", 1)[1]
            decimals_used = len(fractional)
        else:
            decimals_used = 0
        if decimals_used > decimals_max:
            message = (
                f"Значение поля «{field_name}» содержит более {decimals_max} "
                "знаков после десятичного разделителя. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        # 5. Парсинг во ``float`` через тот же помощник, что используется
        # снаружи валидатора. После прохождения регулярного выражения
        # выше эта операция должна успевать, но защищаемся на случай
        # экзотических форматов чисел.
        try:
            value = Validator.parse_decimal(raw)
        except ValueError:
            message = (
                f"Значение поля «{field_name}» не является числом. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        # 6. Диапазон (Req 2.4, 2.5, 2.6).
        too_low = value < min_value if min_inclusive else value <= min_value
        too_high = value > max_value if max_inclusive else value >= max_value
        if too_low or too_high:
            message = (
                f"Значение поля «{field_name}» вне допустимого диапазона. "
                f"Допустимый диапазон: {range_text}."
            )
            return make_error(message), None

        return None, value

    # ---------------------------------------------------------------------
    # Низкоуровневый парсер строк в число (используется и в validate,
    # и снаружи — например, в тестах). Поведение не изменено по сравнению
    # с задачей 3.1.
    # ---------------------------------------------------------------------
    @staticmethod
    def parse_decimal(raw: str) -> float:
        """Преобразовать строку с десятичной запятой или точкой во ``float``.

        Окружающие пробелы отбрасываются. В качестве десятичного
        разделителя принимаются как ``.``, так и ``,`` — оба варианта
        интерпретируются как одно и то же числовое значение (Req 1.4, 2.8).
        Проверка диапазона значений и числа знаков после разделителя в
        этом методе не выполняется — это задача :meth:`Validator.validate`.

        Args:
            raw: строка из поля ввода Формы_Ввода.

        Returns:
            Числовое значение, полученное парсингом ``raw``.

        Raises:
            ValueError: если ``raw`` пустая, состоит только из пробельных
                символов, содержит одновременно ``.`` и ``,``, либо не
                является корректной записью числа.
        """
        if not isinstance(raw, str):
            raise ValueError("parse_decimal expects a string")

        stripped = raw.strip()
        if not stripped:
            raise ValueError("Пустая строка не является корректным числом")

        if "." in stripped and "," in stripped:
            raise ValueError(
                "Строка содержит и точку, и запятую как десятичный разделитель"
            )

        normalized = stripped.replace(",", ".")

        # ``float`` принимает строки с пробелами внутри и спецзначения вроде
        # "nan"/"inf"; требуем строгий формат конечного числа.
        try:
            value = float(normalized)
        except ValueError as exc:
            raise ValueError(f"Некорректное числовое значение: {raw!r}") from exc

        # math.isfinite избегает зависимости — используем побитовую проверку
        # через сравнение с самим собой и неравенство с бесконечностями.
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"Значение не является конечным числом: {raw!r}")

        return value
