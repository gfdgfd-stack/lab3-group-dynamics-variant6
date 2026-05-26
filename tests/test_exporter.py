"""Юнит-тесты Exporter (Task 9.4).

Validates: Requirements 9.3–9.6, 9.11.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from projectile_calculator.domain.models import (
    CalculationInput,
    CalculationResult,
    HistoryRecord,
    Mode,
)
from projectile_calculator.infrastructure.exporter import ExportFormat, Exporter


def _make_records(n: int = 3) -> tuple[HistoryRecord, ...]:
    records = []
    for i in range(1, n + 1):
        inp = CalculationInput(v0=float(i * 10), alpha_deg=45.0, k=float(i), mode=Mode.WITH_DRAG)
        res = CalculationResult(L=float(i * 20), H=float(i * 5), mode=Mode.WITH_DRAG, timestamp=datetime.now())
        records.append(HistoryRecord(input=inp, result=res))
    return tuple(records)


class TestExporter:

    def test_csv_header_and_separator(self):
        """CSV содержит заголовок и разделитель ';'."""
        exporter = Exporter()
        records = _make_records(2)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.csv"
            exporter.export(records, path, ExportFormat.CSV)

            content = path.read_text(encoding="utf-8")
            lines = content.strip().split("\n")

            assert lines[0] == "v0_m_s;alpha_deg;k;mode;L_m;H_m"
            assert ";" in lines[1]
            assert len(lines) == 3  # header + 2 records

    def test_txt_format(self):
        """TXT содержит блоки «параметр: значение»."""
        exporter = Exporter()
        records = _make_records(2)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.txt"
            exporter.export(records, path, ExportFormat.TXT)

            content = path.read_text(encoding="utf-8")
            assert "v0:" in content
            assert "alpha:" in content
            assert "L:" in content
            assert "H:" in content

    def test_ensure_extension_adds_txt(self):
        path = Path("/some/file")
        result = Exporter.ensure_extension(path, ExportFormat.TXT)
        assert result.suffix == ".txt"

    def test_ensure_extension_adds_csv(self):
        path = Path("/some/file")
        result = Exporter.ensure_extension(path, ExportFormat.CSV)
        assert result.suffix == ".csv"

    def test_ensure_extension_idempotent(self):
        path = Path("/some/file.csv")
        result = Exporter.ensure_extension(path, ExportFormat.CSV)
        assert result == path

    def test_ensure_extension_replaces_wrong(self):
        path = Path("/some/file.txt")
        result = Exporter.ensure_extension(path, ExportFormat.CSV)
        assert result.suffix == ".csv"

    def test_atomicity_on_error(self):
        """При ошибке записи целевой файл не повреждается."""
        exporter = Exporter()
        records = _make_records(1)

        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "existing.csv"
            target.write_text("original content", encoding="utf-8")

            # Патчим os.replace чтобы он бросил ошибку
            with patch("projectile_calculator.infrastructure.exporter.os.replace", side_effect=OSError("disk full")):
                with pytest.raises(OSError):
                    exporter.export(records, target, ExportFormat.CSV)

            # Оригинал не повреждён
            assert target.read_text(encoding="utf-8") == "original content"
