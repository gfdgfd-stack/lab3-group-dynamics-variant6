"""Журнал истории вычислений (Requirement 8).

In-memory хранилище записей о выполненных расчётах за текущий сеанс.
Реализовано через ``collections.deque(maxlen=100)`` для автоматического
соблюдения лимита FIFO (Req 8.6).
"""

from __future__ import annotations

from collections import deque

from projectile_calculator.domain.models import HistoryRecord


class HistoryRepository:
    """Репозиторий записей Журнала_Истории (Req 8.1, 8.3, 8.4, 8.6).

    Хранит до 100 последних записей. При переполнении самая ранняя
    запись вытесняется автоматически (FIFO, Req 8.6).
    """

    _MAX_SIZE: int = 100

    def __init__(self) -> None:
        self._storage: deque[HistoryRecord] = deque(maxlen=self._MAX_SIZE)

    def add(self, record: HistoryRecord) -> None:
        """Добавить запись в конец хранилища (самая свежая — последняя)."""
        self._storage.append(record)

    def list_newest_first(self) -> tuple[HistoryRecord, ...]:
        """Вернуть все записи в порядке убывания времени добавления.

        Самая последняя добавленная запись — первая в результате (Req 8.3).
        """
        return tuple(reversed(self._storage))

    def list_oldest_first(self) -> tuple[HistoryRecord, ...]:
        """Вернуть все записи в порядке добавления (от ранней к поздней)."""
        return tuple(self._storage)

    def clear(self) -> None:
        """Очистить хранилище (Req 8.4)."""
        self._storage.clear()

    def __len__(self) -> int:
        """Текущее количество записей."""
        return len(self._storage)
