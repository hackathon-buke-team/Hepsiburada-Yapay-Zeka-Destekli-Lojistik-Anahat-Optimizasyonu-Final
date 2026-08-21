"""Günlük taşıma planı orkestrasyonu.

Sıra: kiralık doldur (batık maliyet, marjinal ~0,07-0,10 TL/desi) →
kıt tır ziyaret bütçesini değer sırasıyla hatlara tahsis et → her
(hat, gün) için en iyi spot karmasını seç (ertelemeli) → ufuk sonrası
kalanları boşaltma günlerinde taşı. Q&A gereği kiralık filo dağıtım
bitene kadar her gün (boşaltma günleri dahil, boş olsa bile) çıkar.

Çıktı: schedule.py'nin dakika-çizelgesine ve şablon DataFrame'e
dönüştüreceği PlannedLeg listesi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from src.candidates import Part, plan_lane_day, wave_ready
from src.timeutil import handling_minutes, travel_minutes

# Tır yalnızca bu eşiğin üzerindeki hat-günlerde değerlendirilir
# (altında Kamyon her zaman daha ucuz — sabit maliyet analizi).
TIR_MIN_DESI = 12000
# Tek hatta bir günde tahsis edilebilecek azami spot tır.
MAX_TIR_PER_LANE = 3


@dataclass
class PlannedLeg:
    """Tek araçlık (tek bacaklık) planlanmış sefer."""
    kind: str                  # 'Spot' | 'Kiralık'
    vtype: str
    origin: str
    dest: str
    load_start: datetime
    dep: datetime
    arr: datetime
    unload_end: datetime
    items: list                # [(Part, desi)] — o bacakta GEMİDE olan yük
    cost: float = 0.0
    penalty: float = 0.0
    vehicle_id: str | None = None
    item_ids: list = field(default_factory=list)  # item başına final ID
    chain_id: int | None = None   # çok bacaklı (milk-run) araç grubu
    chain_seq: int = 0            # zincir içi bacak sırası

    @property
    def desi(self) -> float:
        return sum(d for _, d in self.items)


@dataclass
class PlanContext:
    """Optimizasyonun günler arası paylaşılan durumu."""
    data: object
    pool: dict = field(default_factory=dict)          # (o,d) -> [Part]
    tir_left: dict = field(default_factory=dict)      # (tm, day) -> int
    legs: list = field(default_factory=list)          # [PlannedLeg]
    lane_day_desi: dict = field(default_factory=dict)  # (lane, day) -> desi
    horizon_days: set = field(default_factory=set)    # tahmin günleri (boşaltma hariç)


def prepare_frame(forecast_frame):
    """Şablon tahmin DataFrame'ine ``_day``/``_ready`` kolonları ekler."""
    import pandas as pd

    frame = forecast_frame.copy()
    ready = pd.to_datetime(frame["Tarih"], format="%d.%m.%Y") \
        + pd.to_timedelta(frame["Talep Tamamlama Saati"].astype(str) + ":00")
    frame["_ready"] = ready
    frame["_day"] = ready.dt.date
    return frame


def _seed_context(data, horizon_days: list, all_days: list) -> PlanContext:
    """Havuzu ve kiralık-sonrası tır bütçelerini hazırlar.

    Kiralık tır ziyaretleri TAM yük varsayımıyla (en geç varış) önceden
    rezerve edilir; kıt merkezlerde kiralık varışları zaten aynı gündedir.
    Q&A gereği kiralık filo boşaltma günlerinde de çıkar (boş olsa bile),
    dolayısıyla rezervasyon ufuk + boşaltma günlerinin tamamını kapsar.
    """
    ctx = PlanContext(data=data)
    # Boşaltma günü kalkan (kiralık ya da spot) tırlar son plan gününden
    # sonra varabilir; bütçe takvimine tampon günler eklenir.
    budget_days = list(all_days)
    for _ in range(2):
        budget_days.append(budget_days[-1] + timedelta(days=1))
    for day in budget_days:
        for tm in data.tms:
            ctx.tir_left[(tm, day)] = int(data.tir_cap[tm])
    horizon_set = set(horizon_days)
    ctx.horizon_days = horizon_set
    for day in all_days:
        for rr in data.rentals:
            lane = data.lanes[(rr.origin, rr.dest)]
            for _ in range(rr.count):
                dep = rented_departure(rr, data.vehicles, day,
                                       early=_rented_early(
                                           rr, day, horizon_set))
                arr = dep + timedelta(minutes=travel_minutes(
                    lane.hours[rr.vehicle]))
                if rr.vehicle == "Tır":
                    ctx.tir_left[(rr.origin, day)] -= 1
                    ctx.tir_left[(rr.dest, arr.date())] -= 1
    return ctx


def _add_demand(ctx: PlanContext, frame, day) -> None:
    """Günün tahmin satırlarını (desi > 0) havuza Part olarak ekler."""
    rows = frame[(frame["_day"] == day)
                 & (frame["Tahmin Edilen Desi"] > 0)]
    for r in rows.to_dict("records"):
        key = (r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"])
        lane = ctx.data.lanes[key]
        ready = r["_ready"].to_pydatetime()
        part = Part(part_id=r["Talep ID"], base_id=r["Talep ID"],
                    desi=int(r["Tahmin Edilen Desi"]), ready=ready,
                    deadline=ready + timedelta(hours=24 * lane.sla_days),
                    dest=key[1])
        ctx.pool.setdefault(key, []).append(part)


def rented_departure(rr, vehicles, day, *, early: bool = False) -> datetime:
    """Kiralık kalkış anı: dalga + TAM yük yükleme süresi (sabit politika).

    Kalkışı sabitlemek varış GÜNÜNÜ yüke bağlı olmaktan çıkarır — böylece
    tır ziyaret bütçesi rezervasyonu her zaman birebir doğrudur. Yükleme
    başlangıcı = kalkış − gerçek yükleme süresi olduğundan bekleme
    maliyeti doğmaz. ``early=True`` boşaltma günlerinde kullanılır: yeni
    talep dalgası yoktur, devreden yük zaten hazırdır; kalkış gece
    yarısına çekilerek gereksiz SLA gecikmesi önlenir.
    """
    vt = vehicles[rr.vehicle]
    base = datetime.combine(day, time(0, 0)) if early else wave_ready(day)
    return base + timedelta(minutes=handling_minutes(vt.capacity_desi))


def _rented_early(rr, day, horizon_days) -> bool:
    """Boşaltma gününde erken kalkış yalnız Tır-olmayan kiralıklar için.

    Tır kiralıkların erken kalkması varışı aynı güne çeker; bir önceki
    akşam kalkışın gece yarısını geçen varışıyla aynı günde çift ziyaret
    oluşur ve kıt bütçeler (Balıkesir 1, Tekirdağ 2) aşılır. Tır
    kiralıklarda 17:00 politikası korunur (varış düzeni ufuk günleriyle
    birebir aynı kalır). Tır-olmayan kiralıklar ziyaret bütçesi tüketmez;
    erken kalkış sarkan yükün SLA'sını rahatlatır.
    """
    return day not in horizon_days and rr.vehicle != "Tır"


def _rented_leg(rr, lane, vehicles, items, day, *, early: bool = False) -> PlannedLeg:
    """Kiralık araç bacağını (boş dahil) kural-birebir kurar."""
    vt = vehicles[rr.vehicle]
    desi = sum(d for _, d in items)
    dep = rented_departure(rr, vehicles, day, early=early)
    load_start = dep - timedelta(minutes=handling_minutes(desi))
    if items:
        earliest = max(p.ready for p, _ in items)
        if load_start < earliest:
            load_start = earliest
            dep = load_start + timedelta(minutes=handling_minutes(desi))
    arr = dep + timedelta(minutes=travel_minutes(lane.hours[rr.vehicle]))
    unload_end = arr + timedelta(minutes=handling_minutes(desi))
    usage = (unload_end - load_start).total_seconds() / 3600.0
    cost = vt.rental_hourly * usage + vt.rental_per_km * lane.km
    return PlannedLeg(kind="Kiralık", vtype=rr.vehicle, origin=rr.origin,
                      dest=rr.dest, load_start=load_start, dep=dep, arr=arr,
                      unload_end=unload_end, items=list(items), cost=cost)


def _fill_rented(ctx: PlanContext, day) -> None:
    """Kiralık araçları kendi hattının talebiyle (önce acil) doldurur.

    Havuz boş olsa bile ``rr.count`` adet bacak (gerektiğinde boş)
    üretilir — kiralık filonun her gün çıkması zorunludur. Kalkış
    politikası ``_rented_early``'ye göre belirlenir (boşaltma gününde
    yalnız Tır-olmayan kiralıklar erken kalkar).
    """
    data = ctx.data
    for rr in data.rentals:
        key = (rr.origin, rr.dest)
        lane = data.lanes[key]
        cap = data.vehicles[rr.vehicle].capacity_desi
        queue = sorted(ctx.pool.get(key, []), key=lambda p: p.urgent_key)
        qi = 0
        for _ in range(rr.count):
            items = []
            room = cap
            while room > 0 and qi < len(queue):
                part = queue[qi]
                take = min(room, part.desi)
                items.append((part.piece(take), take))
                room -= take
                if take == part.desi:
                    qi += 1
                else:
                    queue[qi] = part.piece(part.desi - take)
            ctx.legs.append(_rented_leg(rr, lane, data.vehicles, items, day,
                                        early=_rented_early(
                                            rr, day, ctx.horizon_days)))
        ctx.pool[key] = queue[qi:]


def _spot_options(ctx: PlanContext, day, next_wave) -> dict:
    """Her dolu hat için max_tir = 0..K planlarını üretir."""
    data = ctx.data
    options = {}
    for key, parts in ctx.pool.items():
        if not parts:
            continue
        lane = data.lanes[key]
        total = sum(p.desi for p in parts)
        max_tir = 0
        if total > TIR_MIN_DESI and ctx.tir_left.get((key[0], day), 0) > 0:
            max_tir = MAX_TIR_PER_LANE
        # Yarın bu hatta kendi talebi varsa ertelenen yük paylaşımlı
        # araca biner (ucuz); yoksa tek başına taşınır (pahalı).
        absorb = ctx.lane_day_desi.get(
            (key, day + timedelta(days=1)), 0) > 0
        options[key] = [
            plan_lane_day(parts, lane, data.vehicles, max_tir=k,
                          next_wave_ready=next_wave, absorb=absorb)
            for k in range(max_tir + 1)]
    return options


def _allocate_tir(ctx: PlanContext, day, options: dict) -> dict:
    """Kıt tır ziyaretlerini değer sırasıyla hatlara tahsis eder.

    value_k = objective(k-1 tır) - objective(k tır); azalan getiriyle
    açgözlü atama. Bütçe hem çıkış (kalkış günü) hem varış (varış günü)
    için planın kesin tarihleriyle kontrol edilir.
    """
    chosen = {key: plans[0] for key, plans in options.items()}
    lane_k = {key: 0 for key in options}
    while True:
        best = None  # (gain, key, k, needed)
        for key, plans in options.items():
            k = lane_k[key] + 1
            if k >= len(plans):
                continue
            gain = plans[k - 1].objective - plans[k].objective
            if gain <= 1e-9:
                continue
            needed = []
            for load in plans[k].loads:
                if load.vtype != "Tır":
                    continue
                needed.append((key[0], load.dep.date()))
                needed.append((key[1], load.arr.date()))
            if all(ctx.tir_left.get((tm, d), 0) > 0 for tm, d in needed):
                if best is None or gain > best[0]:
                    best = (gain, key, k, needed)
        if best is None:
            break
        _, key, k, needed = best
        for tm, d in needed:
            ctx.tir_left[(tm, d)] -= 1
        lane_k[key] = k
        chosen[key] = options[key][k]
    return chosen


def _emit_spot(ctx: PlanContext, chosen: dict) -> None:
    """Seçilen planları PlannedLeg'e çevirir; kalanları havuza iade eder."""
    for key, plan in chosen.items():
        for load in plan.loads:
            ctx.legs.append(PlannedLeg(
                kind="Spot", vtype=load.vtype, origin=key[0], dest=key[1],
                load_start=load.load_start, dep=load.dep, arr=load.arr,
                unload_end=load.unload_end, items=load.items,
                cost=load.cost, penalty=load.penalty))
        carried = []
        for p, d in plan.carried:
            piece = p.piece(d)
            piece.carried_before = True
            carried.append(piece)
        ctx.pool[key] = carried


def _flush_day(ctx: PlanContext, day) -> None:
    """Boşaltma günü: kalan tüm parçaları gün başında taşır (erteleme yok).

    Spot tır kullanımı kalan ziyaret bütçesiyle sınırlanır ve kesin
    kalkış/varış günleriyle bütçeden düşülür (kiralık rezervasyonu
    sonrası kalan bütçe).
    """
    earliest = datetime.combine(day, time(0, 0))
    for key in list(ctx.pool):
        parts = ctx.pool[key]
        if not parts:
            continue
        lane = ctx.data.lanes[key]
        max_tir = min(MAX_TIR_PER_LANE,
                      max(0, ctx.tir_left.get((key[0], day), 0)))
        plan = plan_lane_day(parts, lane, ctx.data.vehicles,
                             max_tir=max_tir, next_wave_ready=None,
                             earliest_start=earliest)
        for load in plan.loads:
            if load.vtype == "Tır":
                ctx.tir_left[(key[0], load.dep.date())] -= 1
                ctx.tir_left[(key[1], load.arr.date())] -= 1
            ctx.legs.append(PlannedLeg(
                kind="Spot", vtype=load.vtype, origin=key[0], dest=key[1],
                load_start=load.load_start, dep=load.dep, arr=load.arr,
                unload_end=load.unload_end, items=load.items,
                cost=load.cost, penalty=load.penalty))
        ctx.pool[key] = []


def build_plan(data, frame, days: list, flush_days: int = 2) -> list:
    """Tam ufuk için PlannedLeg listesi üretir.

    ``frame`` ``prepare_frame`` çıktısı tahmin DataFrame'i; ``days``
    sıralı tahmin günleri. Ardından ``flush_days`` boşaltma günü eklenir
    ve havuzun tamamen boşaldığı doğrulanır.
    """
    all_days = list(days)
    for i in range(1, flush_days + 1):
        all_days.append(all_days[-1] + timedelta(days=1))
    ctx = _seed_context(data, days, all_days)
    for r in frame[frame["Tahmin Edilen Desi"] > 0].to_dict("records"):
        key = (r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"])
        ctx.lane_day_desi[(key, r["_day"])] = \
            ctx.lane_day_desi.get((key, r["_day"]), 0) \
            + int(r["Tahmin Edilen Desi"])

    horizon_days = set(days)
    for i, day in enumerate(all_days):
        if day in horizon_days:
            _add_demand(ctx, frame, day)
            _fill_rented(ctx, day)
            next_wave = wave_ready(all_days[i + 1])
            options = _spot_options(ctx, day, next_wave)
            chosen = _allocate_tir(ctx, day, options)
            _emit_spot(ctx, chosen)
        else:
            # Q&A: dağıtım bitene kadar kiralık filo her gün çıkar (boş
            # olsa bile maliyeti plana eklenir); sarkan yük önce kiralığa
            # biner, kalan spot ile taşınır.
            _fill_rented(ctx, day)
            _flush_day(ctx, day)
    leftover = sum(p.desi for parts in ctx.pool.values() for p in parts)
    assert leftover == 0, f"boşaltma sonrası kalan desi: {leftover}"
    return ctx.legs
