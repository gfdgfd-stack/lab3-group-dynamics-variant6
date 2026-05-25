# Implementation Plan: Калькулятор траектории полёта

## Overview

Реализация настольного приложения «Калькулятор траектории полёта тела, брошенного под углом к горизонту» на Python 3.10+ / Tkinter / Hypothesis в соответствии с дизайн-документом. План построен снизу вверх: сначала чистый Domain (модели, валидатор, аналитический и численный расчёт), затем Infrastructure (история и экспорт), затем Application (контроллер, lifecycle), затем Presentation (диалоги, окно справки, главное окно) и, наконец, точка входа `main.py`. Каждое из 14 формальных Correctness Properties оформлено отдельным property-based тестом в `tests/test_properties.py`. Тестовые подзадачи помечены `*` и являются опциональными для MVP, но настоятельно рекомендуются.

Convert the feature design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Make sure that each prompt builds on the previous prompts, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.

## Tasks

- [ ] 1. Подготовка структуры проекта
  - [ ] 1.1 Создать каркас пакета и тестов
    - Создать пакеты `projectile_calculator/`, `projectile_calculator/domain/`, `projectile_calculator/application/`, `projectile_calculator/infrastructure/`, `projectile_calculator/presentation/`, `projectile_calculator/resources/` с пустыми `__init__.py`
    - Создать пакет `tests/` с пустым `__init__.py`
    - Создать `requirements.txt` со строками `pytest>=8.0` и `hypothesis>=6.100`
    - Создать минимальный `pyproject.toml` с конфигом pytest (`testpaths = ["tests"]`, маркер `slow`)
    - _Requirements: 12.3, 12.4_

  - [ ]* 1.2 Настроить профили Hypothesis в `tests/conftest.py`
    - Зарегистрировать профиль `default` (`max_examples=200`, `deadline=None`, `suppress_health_check=[HealthCheck.too_slow]`)
    - Зарегистрировать профиль `ci` (`max_examples=500`, `deadline=None`)
    - Загрузить профиль `default` по умолчанию
    - _Requirements: 12.1_

- [ ] 2. Реализовать модели предметной области
  - [ ] 2.1 Создать `projectile_calculator/domain/models.py`
    - Объявить enum-ы `Mode` (`NO_DRAG`, `WITH_DRAG`), `IntegrationStatus` (`LANDED`, `TIMEOUT`), `CalculationErrorCategory` (`OVERFLOW`, `DIVISION_BY_ZERO`, `DOMAIN_ERROR`, `TIMEOUT`, `UNKNOWN`)
    - Объявить `@dataclass(frozen=True)` `CalculationInput`, `CalculationResult`, `ValidationError`, `ValidationResult` (с `is_valid` property), `HistoryRecord`
    - Включить `from __future__ import annotations`, типовые аннотации, `tuple[ValidationError, ...]` для агрегата ошибок
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 2.9, 3.1, 3.2, 4.1, 8.1, 11.7_

- [ ] 3. Реализовать валидатор
  - [ ] 3.1 Реализовать `Validator.parse_decimal` в `projectile_calculator/domain/validator.py`
    - Принимать строку с десятичной точкой или запятой и возвращать `float`
    - Бросать `ValueError` на некорректных строках, не выполнять проверку диапазона
    - Предусмотреть отбрасывание окружающих пробелов; запретить пустую строку
    - _Requirements: 1.4, 2.8_

  - [ ]* 3.2 Property test для `parse_decimal` в `tests/test_properties.py`
    - **Property 1: Эквивалентность парсинга запятой и точки**
    - **Validates: Requirements 1.4, 2.8**
    - Использовать стратегию `st.from_regex(r'-?\d{1,4}([.,]\d{1,3})?', fullmatch=True)`
    - Помечать тест комментарием `# Feature: projectile-calculator, Property 1: …`

  - [ ] 3.3 Реализовать `Validator.validate` в том же файле
    - Хранить константы диапазонов и допустимых знаков после разделителя как атрибуты класса
    - За один проход проверять непустоту, длину строки ≤ 15, число знаков, диапазон для каждого из v0/alpha/k
    - Поле `k` валидировать только при `mode == WITH_DRAG`
    - Возвращать `ValidationResult(input=…)` или `ValidationResult(input=None, errors=tuple(...))` со всеми обнаруженными ошибками
    - В каждый `ValidationError` записывать `field_name` (точная подпись из GUI: «Начальная скорость v₀», «Угол броска α», «Коэффициент сопротивления k»), `field_id` (`v0`/`alpha`/`k`), `raw_value`, `message`, `allowed_min`, `allowed_max`, `format_hint`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9, 11.1, 11.2, 11.3_

  - [ ]* 3.4 Property test для `validate` в `tests/test_properties.py`
    - **Property 2: Корректность валидации формы**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.9, 11.1, 11.2, 11.3**
    - Генерировать стратегиями любые строки и режимы; проверять эквивалентность `is_valid` ↔ конъюнкции пунктов (a)…(e); проверять, что `len(errors)` равно числу полей с ошибками

  - [ ]* 3.5 Юнит-тесты `Validator` в `tests/test_validator.py`
    - Граничные значения (v0 = 0.01 / 1000; α ≈ 0 / 90; k = 0 / 100)
    - Запятая и точка как разделитель; превышение длины строки и числа знаков
    - Пустые и пробельные строки; режим без сопротивления игнорирует валидацию k по диапазону при некорректных значениях, но всё равно требует число при `WITH_DRAG`
    - Агрегирование нескольких ошибок в одном вызове
    - _Requirements: 2.1–2.10, 11.1–11.3_

- [ ] 4. Реализовать аналитический расчёт
  - [ ] 4.1 Реализовать `AnalyticCalculator` в `projectile_calculator/domain/analytic.py`
    - Объявить константу `G: float = 9.81`
    - Метод `compute(v0, alpha_deg) -> tuple[float, float]` возвращает `(L, H)`
    - Конвертировать угол в радианы перед `math.sin`
    - Использовать формулы `L = v0**2 * sin(2α) / G`, `H = (v0 * sin(α))**2 / (2*G)`; не округлять
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 4.2 Property test аналитической дальности в `tests/test_properties.py`
    - **Property 3: Аналитическая дальность**
    - **Validates: Requirements 3.1, 3.3, 3.4, 3.5**
    - `abs(L − v0**2 * sin(2*radians(α)) / 9.81) ≤ 1e-6` для любых v0 ∈ [0.01, 1000], α ∈ (0, 90)

  - [ ]* 4.3 Property test аналитической высоты в `tests/test_properties.py`
    - **Property 4: Аналитическая высота**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    - `abs(H − (v0 * sin(radians(α)))**2 / (2*9.81)) ≤ 1e-6`

  - [ ]* 4.4 Юнит-тесты `AnalyticCalculator` в `tests/test_analytic.py`
    - Эталонный пример (v0 = 10, α = 45°): L ≈ 10.193 м, H ≈ 2.548 м
    - Симметрия α и 90°−α по дальности
    - α = 45° даёт максимум L при фиксированном v0
    - _Requirements: 3.1–3.7_

- [ ] 5. Реализовать численный интегратор
  - [ ] 5.1 Реализовать `NumericalIntegrator` в `projectile_calculator/domain/numerical.py`
    - RK4 с `DEFAULT_DT = 0.001`, `DEFAULT_T_MAX = 600.0`, масса m = 1 кг
    - Уравнения движения для F = -k·v: `dvx/dt = -k*vx`, `dvy/dt = -k*vy - g`, `dx/dt = vx`, `dy/dt = vy`
    - Завершение по пересечению `y = 0` при `vy < 0` через линейную интерполяцию между двумя последними шагами; либо `IntegrationStatus.TIMEOUT` при `t ≥ t_max`
    - Возвращать `(L, H, status)`; `H` — максимум `y` за весь полёт
    - На корректных входах не бросать исключений (валидация — снаружи)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 4.8_

  - [ ]* 5.2 Property test согласованности режимов при k = 0 в `tests/test_properties.py`
    - **Property 5: Согласованность режимов при k = 0**
    - **Validates: Requirements 4.1, 4.2, 4.4, 4.5, 4.7**
    - Для любых v0, α: `(L_a, H_a)` совпадает с `(L_n, H_n)` при `k = 0` с допуском 0.01 м, `status == LANDED`

  - [ ]* 5.3 Property test завершения интегрирования в `tests/test_properties.py`
    - **Property 6: Завершение численного интегрирования**
    - **Validates: Requirements 4.3**
    - Для любых v0 ∈ [0.01, 1000], α ∈ (0, 90), k ∈ [0, 100]: `status == LANDED` при штатных `dt = 0.001`, `t_max = 600`; `y(L) ≤ 1e-6` после интерполяции

  - [ ]* 5.4 Property test точности численного интегрирования в `tests/test_properties.py`
    - **Property 7: Точность численного интегрирования**
    - **Validates: Requirements 4.6**
    - Сравнение `dt = 0.001` с reference `dt = 1e-5`: `abs(L_n − L_ref) ≤ 0.01` и `abs(H_n − H_ref) ≤ 0.01`
    - Помечать `@pytest.mark.slow` (запускается отдельно, по требованию)

  - [ ]* 5.5 Property test метаморфической монотонности по k в `tests/test_properties.py`
    - **Property 8: Метаморфическая монотонность по k**
    - **Validates: Requirements 4.1**
    - Для пары `0 ≤ k1 < k2 ≤ 100`: `L(v0, α, k1) ≥ L(v0, α, k2) − 0.01` и `H(v0, α, k1) ≥ H(v0, α, k2) − 0.01`

  - [ ]* 5.6 Юнит-тесты `NumericalIntegrator` в `tests/test_numerical.py`
    - При k = 0 — совпадение с аналитикой ≤ 0.01 м (Req 4.7)
    - Убывание L и H при росте k
    - Статус `TIMEOUT` при искусственно малом `t_max`
    - _Requirements: 4.1–4.9_

- [ ] 6. Реализовать форматирование вывода
  - [ ] 6.1 Реализовать `round_to_centimeter` и `format_meters` в `projectile_calculator/presentation/formatters.py`
    - `round_to_centimeter(x)` — round-half-away-from-zero до 2 знаков (через `math.floor(abs(x)*100 + 0.5) / 100` с восстановлением знака)
    - `format_meters(x)` — строка вида `"12,34"` (запятая как разделитель, без разделителей разрядов)
    - Корректная обработка `x == 0` (вернуть `0.0` / `"0,00"`)
    - _Requirements: 3.7, 4.9, 5.4_

  - [ ]* 6.2 Property test округления и формата в `tests/test_properties.py`
    - **Property 9: Идемпотентность округления и формат вывода**
    - **Validates: Requirements 3.7, 4.9, 5.4**
    - Для любого x ∈ [0, 1e9]: идемпотентность; кратность 0.01; `format_meters(x)` соответствует `^\d+,\d{2}$`

  - [ ]* 6.3 Юнит-тесты форматтеров в `tests/test_formatters.py`
    - Граничные случаи округления (0.005, 0.015), `0`, отрицательные значения
    - Проверка отсутствия точки и пробелов в `format_meters`
    - _Requirements: 5.4_

- [ ] 7. Чекпойнт: Domain-слой готов
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Реализовать журнал истории
  - [ ] 8.1 Реализовать `HistoryRepository` в `projectile_calculator/infrastructure/history.py`
    - `deque(maxlen=100)` как хранилище; методы `add`, `list_newest_first`, `list_oldest_first`, `clear`, `__len__`
    - `list_newest_first` возвращает кортеж в порядке убывания времени добавления; `list_oldest_first` — в порядке добавления
    - _Requirements: 8.1, 8.3, 8.4, 8.6_

  - [ ]* 8.2 Property test FIFO-инвариантов в `tests/test_properties.py`
    - **Property 10: FIFO-инварианты Журнала_Истории**
    - **Validates: Requirements 8.1, 8.3, 8.6**
    - `len(repo) == min(N, 100)`; первая в `list_newest_first()` — последняя добавленная; `list_newest_first() == tuple(reversed(list_oldest_first()))`; при N > 100 ни одна из последних 100 не теряется

  - [ ]* 8.3 Юнит-тесты `HistoryRepository` в `tests/test_history.py`
    - Добавление до и после переполнения, порядок выдачи, очистка
    - _Requirements: 8.1, 8.3, 8.5, 8.6_

- [ ] 9. Реализовать модуль экспорта
  - [ ] 9.1 Реализовать `Exporter` в `projectile_calculator/infrastructure/exporter.py`
    - Enum `ExportFormat` (`TXT`, `CSV`)
    - Метод `export(records, path, fmt)` пишет во временный файл `<target>.tmp` и затем `os.replace(tmp, target)` для атомарности
    - CSV: разделитель `;`, заголовок `("v0_m_s", "alpha_deg", "k", "mode", "L_m", "H_m")`, кодировка UTF-8
    - TXT: блоки строк формата `параметр: значение`, по одному параметру в строке, ровно одна пустая строка между записями
    - Записи в порядке от ранней к поздней
    - `ensure_extension(path, fmt)` добавляет `.txt` / `.csv`, если расширение не соответствует формату; идемпотентность сохраняется
    - _Requirements: 9.3, 9.4, 9.5, 9.6, 9.11_

  - [ ]* 9.2 Property test round-trip экспорта в `tests/test_properties.py`
    - **Property 11: Round-trip экспорта истории**
    - **Validates: Requirements 9.3, 9.4, 9.5**
    - Реализовать симметричный парсер в самом тесте; сравнивать поля до 2 знаков после разделителя; проверять заголовок CSV и формат TXT-блоков

  - [ ]* 9.3 Property test авто-расширения пути в `tests/test_properties.py`
    - **Property 12: Авто-расширение пути экспорта**
    - **Validates: Requirements 9.11**
    - Идемпотентность; правильное расширение для формата; неизменность имени, если расширение уже корректно

  - [ ]* 9.4 Юнит-тесты `Exporter` в `tests/test_exporter.py`
    - Заголовки CSV и разделитель `;`; формат TXT; авто-расширение
    - Атомарность: `monkeypatch` для имитации `OSError` при записи временного файла — целевой файл не должен изменяться
    - _Requirements: 9.3–9.6, 9.11_

- [ ] 10. Чекпойнт: Infrastructure-слой готов
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Реализовать прикладной слой
  - [ ] 11.1 Реализовать `CalculationController` в `projectile_calculator/application/controller.py`
    - Конструктор принимает `validator`, `analytic`, `numerical`, `history`, `exporter` и колбэки `on_validation_errors`, `on_calculation_error`, `on_result`, `on_progress_visible`, `schedule_main_thread`
    - `on_calculate(raw_v0, raw_alpha, raw_k, mode)`: синхронная валидация → запуск рабочего потока (`threading.Thread(daemon=True)`) с расчётом → доставка результата/ошибки в главный поток через `queue.Queue` и `schedule_main_thread`
    - При ошибках расчёта (`OverflowError`, `ZeroDivisionError`, `ValueError`, `IntegrationStatus.TIMEOUT`) формировать соответствующий `CalculationErrorCategory`
    - При успехе складывать `HistoryRecord` в `HistoryRepository` (всегда из главного потока через `schedule_main_thread`)
    - `on_clear()` дожидается активного расчёта и затем триггерит UI-колбэк очистки формы; не очищает историю
    - `on_export(target_path, fmt)` ловит `PermissionError` / `OSError(ENOSPC)` / прочие `OSError` / `UnicodeEncodeError` и преобразует в категории; не открывает диалог при пустой истории (защита поверх UI-проверки)
    - _Requirements: 3.6, 4.1, 4.8, 5.1, 5.2, 5.3, 5.7, 6.7, 8.1, 8.5, 9.6, 9.7, 11.7, 12.7, 12.8_

  - [ ]* 11.2 Юнит-тесты `CalculationController` в `tests/test_controller.py`
    - Ошибки валидации → вызов `on_validation_errors`, отсутствие записи в истории
    - Успешный расчёт → `on_result` и пополнение истории
    - Имитация `OverflowError` от расчётчика → `on_calculation_error(OVERFLOW)`
    - `IntegrationStatus.TIMEOUT` → `on_calculation_error(TIMEOUT)`
    - Колбэки UI вызываются только из главного потока (через переданный `schedule_main_thread`)
    - _Requirements: 11.7, 12.7, 12.8_

  - [ ] 11.3 Реализовать `WindowManager` в `projectile_calculator/application/window_manager.py`
    - Управляет `stop_event`, ожиданием рабочего потока (`thread.join(timeout=2.5)`), очисткой `HistoryRepository.clear()` и `root.destroy()` в правильном порядке
    - Запускает `root.after(3000, fallback_force_exit)` и при превышении 3 с показывает диалог «Ошибка завершения» и вызывает `os._exit(1)` через ещё 5 с
    - _Requirements: 8.4, 10.1, 10.2, 10.3, 10.4_

- [ ] 12. Подготовить чистые помощники для презентации
  - [ ] 12.1 Реализовать `compute_calculate_button_state` и `compute_k_field_state` в `projectile_calculator/presentation/main_window.py`
    - `compute_calculate_button_state(form_state) -> Enabled | Disabled` — обёртка поверх `Validator`
    - `compute_k_field_state(mode) -> ReadOnly | Editable` — `ReadOnly ⇔ mode == NO_DRAG`
    - Перечисления состояний (`Enum`) экспортируются из того же модуля; класс `MainWindow` пока не реализуется (заглушка)
    - _Requirements: 1.8, 13.4, 13.5_

  - [ ]* 12.2 Property test состояния кнопки «Рассчитать» в `tests/test_properties.py`
    - **Property 13: Активность кнопки «Рассчитать» эквивалентна валидности формы**
    - **Validates: Requirements 13.4, 13.5**

  - [ ]* 12.3 Property test readonly-инварианта поля k в `tests/test_properties.py`
    - **Property 14: Инвариант readonly для поля k**
    - **Validates: Requirements 1.8**

- [ ] 13. Реализовать виджеты Tkinter
  - [ ] 13.1 Реализовать ресурс справки в `projectile_calculator/resources/help_text.py`
    - Константные строки (RU): формулы L, H, легенда переменных, описание RK4 и силы сопротивления, диапазоны и формат ввода, значение g = 9.81 м/с²
    - _Requirements: 7.4, 7.5, 7.6, 7.7_

  - [ ] 13.2 Реализовать диалоги в `projectile_calculator/presentation/dialogs.py`
    - `show_validation_errors(parent, errors)` — модальный диалог со списком ошибок (по строке на поле); кнопка OK / Enter / Esc
    - `show_calculation_error(parent, category)` — заголовок «Ошибка расчёта», текст по `CalculationErrorCategory`
    - `show_io_error(parent, error)` — категории «нет прав на запись», «нехватка места», «недопустимый путь / общая ошибка ввода-вывода», «ошибка кодирования»
    - `show_info(parent, message)` — общий info-диалог (для «История пуста» и «Сохранено в …»)
    - `ask_save_path(parent) -> tuple[Path, ExportFormat] | None` — `tkinter.filedialog.asksaveasfilename` с фильтрами `.txt` и `.csv`, `confirmoverwrite=True`, дефолтное имя `projectile_history`; возвращает `None` при отмене
    - _Requirements: 9.1, 9.2, 9.7, 9.8, 9.9, 9.10, 11.4, 11.5, 11.7_

  - [ ] 13.3 Реализовать `HelpWindow` в `projectile_calculator/presentation/help_window.py`
    - Singleton: повторный `show()` возвращает фокус существующему окну
    - Закрытие по системной кнопке и по Escape; возврат фокуса главному окну
    - Содержимое формируется из `resources/help_text.py`
    - _Requirements: 7.1, 7.2, 7.3, 7.8_

  - [ ] 13.4 Реализовать `MainWindow` в `projectile_calculator/presentation/main_window.py`
    - Заголовок «Калькулятор траектории полёта», `geometry("800x600")`, `minsize(800, 600)`
    - Layout: Форма_Ввода (поля v₀, α, k с подписями и единицами; чекбокс «учитывать сопротивление воздуха»; k = read-only при `NO_DRAG`), Область_Результатов («Дальность:», «Максимальная высота:», метка режима), Журнал_Истории (видимая область), панель кнопок («Рассчитать», «Очистить», «Справка», «Экспорт», «Выход»)
    - Tab-порядок: v0 → α → k → mode → Рассчитать → Очистить → Справка → Экспорт → Выход; Enter / Space активирует выделенную кнопку
    - Делегирует все события контроллеру (без вычислений и парсинга в самом окне)
    - При получении результата обновляет Область_Результатов через `format_meters`, метку режима и Журнал_Истории
    - При запуске расчёта: блокирует «Рассчитать» / «Очистить»; через `root.after(1000, …)` показывает «Идёт расчёт…»; «Выход» остаётся активным
    - Скрывает диалог ошибки при следующем редактировании (Req 2.10); состояние «Рассчитать» обновляется через `compute_calculate_button_state`; readonly k через `compute_k_field_state`
    - При ошибке расчёта/валидации: численные значения L и H заменяются на «—», подписи и метка режима не трогаются; фокус переходит в первое ошибочное поле по Tab-порядку
    - _Requirements: 1.1–1.8, 2.4–2.7, 2.10, 5.1, 5.2, 5.3, 5.5, 5.6, 5.7, 6.1–6.6, 7.1, 8.2, 8.3, 9.1, 11.6, 11.8, 12.7, 12.8, 13.1–13.7_

- [ ] 14. Связать всё в точке входа
  - [ ] 14.1 Реализовать `main.py`
    - Создать `tk.Tk()` (root), все домейные сервисы, `HistoryRepository`, `Exporter`, контроллер с колбэками к `MainWindow` (через `schedule_main_thread = lambda fn: root.after(0, fn)`), `WindowManager`
    - Зарегистрировать обработчик `WM_DELETE_WINDOW` через `WindowManager`
    - Запустить `MainWindow` и `root.mainloop()`
    - _Requirements: 8.4, 10.1, 10.2, 10.3, 10.4, 12.2, 12.7, 12.8, 13.1, 13.3_

  - [ ]* 14.2 Smoke-тесты в `tests/test_smoke.py`
    - Импорт `projectile_calculator.presentation.main_window`; создание `tk.Tk()` и `MainWindow` без исключений (только при наличии переменной окружения `DISPLAY` или на Windows-агенте; иначе тест помечается `pytest.skip`)
    - _Requirements: 12.2_

- [ ] 15. Финальный чекпойнт: все тесты проходят
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Подзадачи, помеченные `*`, опциональны для MVP и могут быть пропущены, чтобы быстрее получить рабочий прототип; для production-качества рекомендуется выполнить их все.
- Каждая задача ссылается на конкретные пункты Acceptance Criteria из `requirements.md` для трассируемости.
- Все 14 Correctness Properties из `design.md` представлены отдельными property-based тестами в `tests/test_properties.py`; каждый тест помечается комментарием `# Feature: projectile-calculator, Property N: …` и аннотируется тегами `@settings(max_examples=200)` (CP7 — `@pytest.mark.slow`).
- Чекпойнты после Domain (задача 7), Infrastructure (10) и финальный (15) обеспечивают инкрементальную валидацию.
- Production-зависимостей нет: только `python` stdlib и `tkinter`. Тестовые зависимости — `pytest` и `hypothesis`.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["3.1", "4.1", "6.1", "8.1", "13.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "5.1", "9.1", "4.4", "6.3", "8.3"] },
    { "id": 4, "tasks": ["3.4", "3.5", "5.6", "9.4", "11.1", "11.3", "13.2", "12.1"] },
    { "id": 5, "tasks": ["4.2", "11.2", "13.3"] },
    { "id": 6, "tasks": ["4.3"] },
    { "id": 7, "tasks": ["5.2"] },
    { "id": 8, "tasks": ["5.3"] },
    { "id": 9, "tasks": ["5.4"] },
    { "id": 10, "tasks": ["5.5"] },
    { "id": 11, "tasks": ["6.2"] },
    { "id": 12, "tasks": ["8.2"] },
    { "id": 13, "tasks": ["9.2"] },
    { "id": 14, "tasks": ["9.3"] },
    { "id": 15, "tasks": ["12.2"] },
    { "id": 16, "tasks": ["12.3"] },
    { "id": 17, "tasks": ["13.4"] },
    { "id": 18, "tasks": ["14.1", "14.2"] }
  ]
}
```
