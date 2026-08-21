"""Günlük kapasite defterleri (00:00 reset).

HandlingLedger: TM x gün elleçleme desisi; gece yarısını aşan işlem desisi
süreye ORANSAL bölünür (örn. 23:30'da 10.000 desi, 100 dk -> 3.000/7.000).
TirLedger: TM x gün tır ziyaret sayısı; aynı (araç, ziyaret) çifti aynı
TM-günde bir kez sayılır (hareketsiz boşalt+yükle = 1 ziyaret).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from src.timeutil import handling_minutes


class HandlingLedger:
    def __init__(self, capacity: dict):
        self.capacity = capacity
        self.used = {}

    def add(self, tm: str, start: datetime, desi: float) -> datetime:
        dur = handling_minutes(desi)
        end = start + timedelta(minutes=dur)
        if dur == 0:
            return end
        cur = start
        while cur < end:
            next_midnight = datetime.combine(cur.date() + timedelta(days=1), time(0, 0))
            seg_end = min(end, next_midnight)
            seg_min = (seg_end - cur).total_seconds() / 60
            key = (tm, cur.date())
            self.used[key] = self.used.get(key, 0.0) + desi * seg_min / dur
            cur = seg_end
        return end

    def over_caps(self) -> list:
        """Aşımları yapısal döner: [(tm, day, used, cap), ...]."""
        out = []
        for (tm, d), used in sorted(self.used.items()):
            cap = self.capacity.get(tm)
            if cap is not None and used > cap + 1e-6:
                out.append((tm, d, used, cap))
        return out

    def violations(self) -> list:
        out = []
        for (tm, d), used in sorted(self.used.items()):
            cap = self.capacity.get(tm)
            if cap is None:
                out.append(f"Bilinmeyen TM elleçleme defterinde: {tm} {d}")
        for tm, d, used, cap in self.over_caps():
            out.append(f"Elleçleme kapasitesi aşıldı: {tm} {d}: "
                       f"{used:.1f} > {cap:.1f}")
        return out


class TirLedger:
    def __init__(self, capacity: dict):
        self.capacity = capacity
        self._visits = defaultdict(set)

    def add_event(self, tm: str, day: date, vehicle_id: str, visit_id: int) -> None:
        self._visits[(tm, day)].add((vehicle_id, visit_id))

    def count(self, tm: str, day: date) -> int:
        return len(self._visits.get((tm, day), ()))

    def violations(self) -> list:
        out = []
        for (tm, d), v in sorted(self._visits.items()):
            cap = self.capacity.get(tm)
            if cap is None:
                out.append(f"Bilinmeyen TM tır defterinde: {tm} {d}")
            elif len(v) > cap:
                out.append(f"Tır kapasitesi aşıldı: {tm} {d}: {len(v)} > {cap}")
        return out
