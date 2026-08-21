"""Hat-gün bazında araç-karması adayları ve kesin maliyet modeli.

Her (hat, gün) için talep parçalarını (Part) araç sayısı karmalarına atar;
maliyeti hakem simülatörüyle BİREBİR aynı formülle hesaplar:

    araç maliyeti = saatlik × (yükleme + yol + indirme) + km × km_başı
    SLA cezası    = geciken desi × ⌈gecikme saati⌉ × 0,40 TL

Taşıma-erteleme (carry-over) kararı: kalan desinin yarınki dalgayla
taşınmasının tahmini ceza + marjinal elleçleme maliyeti, ek araç sabit
maliyetiyle karşılaştırılır. Erteleme, yarınki araçların yutabileceği
ölçüyle (Kamyonet kapasitesi) sınırlıdır.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from src.timeutil import (SLA_TL_PER_DESI_HOUR, handling_minutes, late_hours,
                          travel_minutes)

# Ertelemeye eklenen gelecek-gün marjinal elleçleme maliyeti (TL/desi).
CARRY_VAR_TL = 0.12
# Bir günden ertelenebilecek azami desi (yarın tek küçük araca sığmalı).
MAX_CARRY_DESI = 5600
# Sayım üst sınırına eklenen güvenlik payı.
COUNT_SLACK = 1


@dataclass
class Part:
    """Bir tahmin talebinin (muhtemelen bölünmüş) fiziksel parçası.

    Kimlik kuralı: her (bacak, kalem) benzersiz bir Part nesnesi tutar;
    bölünme YENİ nesneler yaratır, süt/aktarma sürüşü aynı nesneyi
    paylaşır. Böylece nesne kimliği = parça kimliği olur.
    """
    part_id: str
    base_id: str
    desi: int
    ready: datetime
    deadline: datetime
    carried_before: bool = False
    dest: str | None = None

    @property
    def urgent_key(self):
        return (self.deadline, self.ready, self.part_id)

    def piece(self, take: int) -> "Part":
        """Bu parçadan ``take`` desilik yeni bir fiziksel parça üretir."""
        return Part(self.part_id, self.base_id, take, self.ready,
                    self.deadline, self.carried_before, self.dest)


@dataclass
class VehicleLoadPlan:
    """Tek aracın yükü ve kesin zaman/maliyet çizelgesi."""
    vtype: str
    items: list  # [(Part, desi)]
    load_start: datetime
    dep: datetime
    arr: datetime
    unload_end: datetime
    cost: float
    penalty: float

    @property
    def desi(self) -> float:
        return sum(d for _, d in self.items)


@dataclass
class LaneDayPlan:
    loads: list            # [VehicleLoadPlan]
    carried: list          # [(Part, desi)] yarınki dalgaya kalanlar
    objective: float       # araç + ceza + erteleme maliyeti
    vehicle_cost: float
    penalty: float
    carry_cost: float


def _travel_min(lane, vtype: str) -> int:
    return travel_minutes(lane.hours[vtype])


def plan_vehicle(vtype: str, items: list, lane, vehicles: dict, *,
                 earliest_start: datetime | None = None) -> VehicleLoadPlan:
    """Tek aracın zaman çizelgesini ve maliyetini kural-birebir hesaplar.

    Yükleme, yükteki en geç hazır olma anında başlar (bekleme yok);
    ``earliest_start`` verilirse yükleme ondan önce başlayamaz (boşaltma
    günleri). Tüm süreler yukarı tam dakikaya yuvarlanır (timeutil tek
    kaynak).
    """
    vt = vehicles[vtype]
    desi = sum(d for _, d in items)
    load_min = handling_minutes(desi)
    load_start = max(p.ready for p, _ in items)
    if earliest_start is not None and load_start < earliest_start:
        load_start = earliest_start
    dep = load_start + timedelta(minutes=load_min)
    arr = dep + timedelta(minutes=_travel_min(lane, vtype))
    unload_end = arr + timedelta(minutes=handling_minutes(desi))
    usage_hours = (unload_end - load_start).total_seconds() / 3600.0
    cost = vt.spot_hourly * usage_hours + vt.spot_per_km * lane.km
    penalty = sum(
        d * late_hours(p.deadline, unload_end) * SLA_TL_PER_DESI_HOUR
        for p, d in items)
    return VehicleLoadPlan(vtype=vtype, items=list(items),
                           load_start=load_start, dep=dep, arr=arr,
                           unload_end=unload_end, cost=cost, penalty=penalty)


def assign_parts(parts: list, counts: dict, lane, vehicles: dict, *,
                 earliest_start: datetime | None = None):
    """Parçaları araçlara doldurur; (yükler, kalanlar) döner.

    Araçlar saatlik ücreti UCUZ olandan pahalıya sıralanır (elleçleme
    süresi maliyeti ucuz araçta daha düşük); parçalar teslim tarihi en
    yakın olandan başlayarak doldurulur — acil yük, erken kalkan küçük
    ve hızlı araca biner.
    """
    order = sorted((v for v in counts if counts[v] > 0),
                   key=lambda v: vehicles[v].spot_hourly)
    fleet = []
    for v in order:
        fleet.extend([v] * counts[v])

    loads: list[list] = [[] for _ in fleet]
    queue = sorted(parts, key=lambda p: p.urgent_key)
    qi = 0
    for fi, v in enumerate(fleet):
        room = vehicles[v].capacity_desi
        while room > 0 and qi < len(queue):
            part = queue[qi]
            take = min(room, part.desi)
            loads[fi].append((part.piece(take), take))
            room -= take
            if take == part.desi:
                qi += 1
            else:
                queue[qi] = part.piece(part.desi - take)
        if qi >= len(queue):
            break
    remaining = [(part, part.desi) for part in queue[qi:]]

    plans = [plan_vehicle(v, items, lane, vehicles,
                          earliest_start=earliest_start)
             for v, items in zip(fleet, loads) if items]
    return plans, remaining


def _standalone_cost(desi: float, lane, vehicles: dict) -> float:
    """Kalan desinin yarın TEK BAŞINA taşınmasının en ucuz araç maliyeti.

    Yarın o hatta yutucu araç yoksa ertelemenin gerçek bedeli budur
    (boş güne ertelemek aracı yalnız ileri atar, paylaşım olmaz).
    """
    best = float("inf")
    for name, vt in vehicles.items():
        if vt.capacity_desi < desi:
            continue
        usage = (2 * handling_minutes(desi)
                 + _travel_min(lane, name)) / 60.0
        best = min(best, vt.spot_hourly * usage + vt.spot_per_km * lane.km)
    return best


def _carry_cost(carried: list, lane, next_wave_ready: datetime, *,
                absorb: bool, vehicles: dict) -> float:
    """Kalan desinin yarınki dalgayla taşınmasının tahmini maliyeti.

    Yarınki dalga 17:00'da yüklenir; varış + parça indirmesi sonrası SLA
    gecikmesi birebir hesaplanır. ``absorb`` doğruysa (yarın o hatta
    kendi talebi var = paylaşılacak araç var) marjinal elleçleme payı,
    değilse tek-başına taşıma maliyeti eklenir.
    """
    travel = timedelta(minutes=_travel_min(lane, "Kamyon"))
    total = 0.0
    for part, desi in carried:
        arr_end = (next_wave_ready + travel
                   + timedelta(minutes=handling_minutes(desi)))
        total += desi * late_hours(part.deadline, arr_end) * \
            SLA_TL_PER_DESI_HOUR
        total += (desi * CARRY_VAR_TL if absorb
                  else _standalone_cost(desi, lane, vehicles))
    return total


def _count_bounds(desi: int, vehicles: dict, max_tir: int) -> dict:
    return {
        "Tır": min(math.ceil(desi / vehicles["Tır"].capacity_desi)
                   + COUNT_SLACK, max_tir),
        "Kamyon": math.ceil(desi / vehicles["Kamyon"].capacity_desi)
        + COUNT_SLACK,
        # Ek Hafif Kamyon/Kamyonet karmaları Kamyon tarafından domine
        # edilir; küçük kalanlar için 1-2 adet yeterlidir.
        "Hafif Kamyon": 2,
        "Kamyonet": 1,
    }


def plan_lane_day(parts: list, lane, vehicles: dict, *,
                  max_tir: int, next_wave_ready: datetime | None,
                  earliest_start: datetime | None = None,
                  absorb: bool = True) -> LaneDayPlan:
    """Bir (hat, gün) için en iyi araç karmasını numaralandırarak seçer.

    ``parts`` o gün taşınmayı bekleyen tüm parçalar (devreden + yeni).
    ``next_wave_ready`` None ise erteleme yasaktır (ufuk sonrası boşaltma).
    ``earliest_start`` yükleme başlangıcına alt sınır koyar (boşaltma
    günleri). ``absorb``: yarın o hatta paylaşılacak araç var mı (erteleme
    fiyatlandırması). Daha önce ertelenmiş parça tekrar ertelenemez.
    Dönen plan simülatör-birebir araç maliyeti + SLA cezası + erteleme
    maliyeti toplamını (objective) minimize eder.
    """
    total_desi = sum(p.desi for p in parts)
    if total_desi <= 0:
        return LaneDayPlan([], [], 0.0, 0.0, 0.0, 0.0)

    bounds = _count_bounds(total_desi, vehicles, max_tir)
    min_cap = min(vt.capacity_desi for vt in vehicles.values())
    best: LaneDayPlan | None = None

    def _consider(counts: dict) -> None:
        nonlocal best
        cap = sum(counts[v] * vehicles[v].capacity_desi for v in counts)
        if cap <= 0:
            loads, carried = [], [(p, p.desi) for p in parts]
        else:
            if cap < total_desi - MAX_CARRY_DESI:
                return  # erteleme sınırı aşılır
            smallest = min(vehicles[v].capacity_desi
                           for v in counts if counts[v] > 0)
            if cap - smallest >= total_desi:
                return  # en küçük aracı çıkarmak yetiyor: domine
            loads, carried = assign_parts(parts, counts, lane, vehicles,
                                          earliest_start=earliest_start)
        if sum(d for _, d in carried) > MAX_CARRY_DESI:
            return
        if carried and next_wave_ready is None:
            return  # boşaltma günü: erteleme yok
        if any(p.carried_before for p, _ in carried):
            return  # bir parça en fazla bir kez ertelenebilir
        vehicle_cost = sum(l.cost for l in loads)
        penalty = sum(l.penalty for l in loads)
        carry_cost = (_carry_cost(carried, lane, next_wave_ready,
                                  absorb=absorb, vehicles=vehicles)
                      if carried else 0.0)
        objective = vehicle_cost + penalty + carry_cost
        if best is None or objective < best.objective - 1e-9:
            best = LaneDayPlan(loads, carried, objective,
                               vehicle_cost, penalty, carry_cost)

    for n_tir in range(bounds["Tır"] + 1):
        for n_kam in range(bounds["Kamyon"] + 1):
            for n_haf in range(bounds["Hafif Kamyon"] + 1):
                for n_et in range(bounds["Kamyonet"] + 1):
                    if not (n_tir or n_kam or n_haf or n_et):
                        continue
                    _consider({"Tır": n_tir, "Kamyon": n_kam,
                               "Hafif Kamyon": n_haf, "Kamyonet": n_et})
    # Hiç araç çıkarmama (tam erteleme) adayı — yalnız küçük günlerde ve
    # havuzda daha önce ertelenmiş parça yoksa.
    if (next_wave_ready is not None and total_desi <= MAX_CARRY_DESI
            and not any(p.carried_before for p in parts)):
        _consider({"Tır": 0, "Kamyon": 0, "Hafif Kamyon": 0, "Kamyonet": 0})

    assert best is not None
    return best


def wave_ready(day, slot: str = "17:00") -> datetime:
    """Günün birleşik yükleme dalgasının hazır olma anı."""
    hh, mm = (int(x) for x in slot.split(":"))
    return datetime.combine(day, time(hh, mm))
