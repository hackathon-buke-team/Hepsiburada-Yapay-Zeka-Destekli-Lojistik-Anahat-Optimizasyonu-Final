"""Yarışma yuvarlama/zaman kuralları — TEK doğruluk kaynağı.

Kurallar:
- Tüm süreler en yakın BÜYÜK tam dakikaya yuvarlanır (55,2 dk -> 56).
- Elleçleme 0,01 dk/desi (yükleme ve indirme ayrı ayrı).
- SLA gecikmesi bir üst tam saate yuvarlanır; ceza 0,4 TL/desi/saat.
"""
from __future__ import annotations

import math
from datetime import datetime

HANDLING_MIN_PER_DESI = 0.01
SLA_TL_PER_DESI_HOUR = 0.4


def _ceil_guarded(x: float) -> int:
    # float artefaktı (275.99999) yukarı taşmasın diye önce 6 haneye yuvarla
    return math.ceil(round(x, 6))


def travel_minutes(hours: float) -> int:
    return _ceil_guarded(hours * 60)


def handling_minutes(desi: float) -> int:
    if desi <= 0:
        return 0
    return _ceil_guarded(desi * HANDLING_MIN_PER_DESI)


def late_hours(deadline: datetime, completion: datetime) -> int:
    late_min = (completion - deadline).total_seconds() / 60
    if late_min <= 0:
        return 0
    return _ceil_guarded(late_min / 60)


def parse_dt(tarih: str, saat: str) -> datetime:
    return datetime.strptime(f"{tarih} {saat}", "%d.%m.%Y %H:%M")


def fmt_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y")


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")
