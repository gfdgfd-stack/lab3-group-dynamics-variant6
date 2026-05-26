"""Модуль экспорта Журнала_Истории в файл (Requirement 9).

Поддерживает два формата: текстовый (.txt) и CSV (.csv).
Запись атомарна: используется временный файл с последующим
``os.replace`` (Req 9.6).
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from projectile_calculator.domain.models import HistoryRecord, Mode


class ExportFormat(Enum):
    """Поддерживаемые форматы экспорта."""

    TXT = "txt"
    CSV = "csv"


class Exporter:
    """Экспорт записей Журнала_Истории в файл (Req 9.3–9.6, 9.11)."""

    # CSV-заголовок (Req 9.4).
    _CSV_HEADER = "v0_m_s;alpha_deg;k;mode;L_m;H_m"

    @staticmethod
    def ensure_extension(path: Path, fmt: ExportFormat) -> Path:
        """Добавить расширение, если оно не соответствует формату (Req 9.11).

        Идемпотентна: если расширение уже корректное, путь не изменяется.
        """
        expected_suffix = f".{fmt.value}"
        if path.suffix.lower() == expected_suffix:
            return path
        return path.with_suffix(expected_suffix)

    def export(
        self,
        records: tuple[HistoryRecord, ...],
        path: Path,
        fmt: ExportFormat,
    ) -> None:
        """Записать ``records`` в файл ``path`` в указанном формате.

        Записи пишутся в порядке от ранней к поздней (Req 9.3).
        Используется атомарная запись через временный файл (Req 9.6).

        Args:
            records: записи истории, упорядоченные от ранней к поздней.
            path: целевой путь (расширение должно быть корректным —
                вызывающий код обязан пропустить через ``ensure_extension``).
            fmt: формат экспорта.

        Raises:
            OSError: при ошибке записи на диск.
            UnicodeEncodeError: если данные не кодируются в UTF-8.
        """
        target = path
        tmp_path = target.with_name(target.name + ".tmp")

        try:
            with open(tmp_path, "w", encoding="utf-8", newline="") as f:
                if fmt == ExportFormat.CSV:
                    self._write_csv(f, records)
                else:
                    self._write_txt(f, records)
            os.replace(str(tmp_path), str(target))
        except BaseException:
            # Удаляем временный файл, если он остался, чтобы не засорять
            # файловую систему; целевой файл не повреждён (Req 9.6).
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Internal formatters
    # ------------------------------------------------------------------
    def _write_csv(self, f, records: tuple[HistoryRecord, ...]) -> None:
        """Формат CSV: разделитель ';', заголовок, UTF-8 (Req 9.4)."""
        f.write(self._CSV_HEADER + "\n")
        for rec in records:
            mode_str = "no_drag" if rec.input.mode == Mode.NO_DRAG else "with_drag"
            line = (
                f"{rec.input.v0};"
                f"{rec.input.alpha_deg};"
                f"{rec.input.k};"
                f"{mode_str};"
                f"{rec.result.L};"
                f"{rec.result.H}"
            )
            f.write(line + "\n")

    def _write_txt(self, f, records: tuple[HistoryRecord, ...]) -> None:
        """Текстовый формат: блоки «параметр: значение» (Req 9.5)."""
        for i, rec in enumerate(records):
            if i > 0:
                f.write("\n")
            mode_label = (
                "Без сопротивления воздуха"
                if rec.input.mode == Mode.NO_DRAG
                else "С сопротивлением воздуха"
            )
            f.write(f"v0: {rec.input.v0}\n")
            f.write(f"alpha: {rec.input.alpha_deg}\n")
            f.write(f"k: {rec.input.k}\n")
            f.write(f"mode: {mode_label}\n")
            f.write(f"L: {rec.result.L}\n")
            f.write(f"H: {rec.result.H}\n")
