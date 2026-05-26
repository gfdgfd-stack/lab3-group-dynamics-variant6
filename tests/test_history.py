"""Юнит-тесты HistoryRepository (Task 8.3).

Validates: Requirements 8.1, 8.3, 8.5, 8.6.
"""

from datetime import datetime

import pytest

from projectile_calculator.domain.models import (
    CalculationInput,
    CalculationResult,
    HistoryRecord,
    Mode,
)
from projectile_calculator.infrastructure.history import HistoryRepository


def _record(i: int) -> HistoryRecord:
    inp = CalculationInput(v0=float(i), alpha_deg=45.0, k=0.0, mode=Mode.NO_DRAG)
    res = CalculationResult(L=float(i * 2), H=float(i), mode=Mode.NO_DRAG, timestamp=datetime.now())
    return HistoryRecord(input=inp, result=res)


class TestHistoryRepository:

    def test_empty_initially(self):
        repo = HistoryRepository()
        assert len(repo) == 0
        assert repo.list_newest_first() == ()
        assert repo.list_oldest_first() == ()

    def test_add_single(self):
        repo = HistoryRepository()
        rec = _record(1)
        repo.add(rec)
        assert len(repo) == 1
        assert repo.list_newest_first() == (rec,)

    def test_order_newest_first(self):
        repo = HistoryRepository()
        r1, r2, r3 = _record(1), _record(2), _record(3)
        repo.add(r1)
        repo.add(r2)
        repo.add(r3)
        assert repo.list_newest_first() == (r3, r2, r1)

    def test_order_oldest_first(self):
        repo = HistoryRepository()
        r1, r2, r3 = _record(1), _record(2), _record(3)
        repo.add(r1)
        repo.add(r2)
        repo.add(r3)
        assert repo.list_oldest_first() == (r1, r2, r3)

    def test_overflow_removes_oldest(self):
        repo = HistoryRepository()
        for i in range(105):
            repo.add(_record(i))
        assert len(repo) == 100
        # Первые 5 (0-4) вытеснены
        oldest = repo.list_oldest_first()
        assert oldest[0].input.v0 == 5.0

    def test_clear(self):
        repo = HistoryRepository()
        for i in range(10):
            repo.add(_record(i))
        repo.clear()
        assert len(repo) == 0
        assert repo.list_newest_first() == ()
