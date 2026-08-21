"""Hakem simülatörü (bölüm 1): plan bacaklarını ayrıştırır, araç zaman
çizelgesini ve maliyetini KURAL-BİREBİR yeniden hesaplar.

Kural kaynakları: şartname + Q&A + son-gelen-message. Optimizer'ın iç
durumunu görmez; yalnız çıktı-format DataFrame'leri okur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd

from src.timeutil import handling_minutes, parse_dt, travel_minutes


@dataclass(frozen=True)
class DeclaredRow:
    item_id: str | None
    desi: float
    travel_minutes: float
    arrival_handling_minutes: float
    departure_handling_minutes: float
    sla_penalty: float
    total_cost: float


@dataclass
class Leg:
    vehicle_id: str
    kind: str            # 'Spot' | 'Kiralık'
    vtype: str           # 'Tır' | 'Kamyon' | 'Hafif Kamyon' | 'Kamyonet'
    origin: str
    dest: str
    dep: datetime
    declared_arr: datetime
    items: list          # [(talep_id, desi), ...]; boş kiralık bacağında []
    violations: list[str] = field(default_factory=list)
    declared_rows: list[DeclaredRow] = field(default_factory=list)


@dataclass
class HandlingEvent:
    tm: str
    start: datetime
    end: datetime
    desi: float
    kind: str            # 'load' | 'unload'


@dataclass
class VehicleTrace:
    vehicle_id: str
    kind: str
    vtype: str
    legs: list
    usage_start: datetime = None
    usage_end: datetime = None
    usage_hours: float = 0.0
    total_km: int = 0
    cost: float = 0.0
    events: list = field(default_factory=list)
    leg_times: list = field(default_factory=list)
    violations: list = field(default_factory=list)


def _is_empty_id(v) -> bool:
    return pd.isna(v) or str(v).strip() == ""


def parse_legs(plan_df: pd.DataFrame) -> list[Leg]:
    legs = []
    group_cols = ["Araç ID", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                  "Çıkış Tarihi", "Çıkış Saati"]
    for (vid, origin, dest, dtarih, dsaat), g in plan_df.groupby(group_cols, sort=False):
        items = [(str(t), float(d))
                 for t, d in zip(g["Talep ID"], g["Taşınan Desi"])
                 if not _is_empty_id(t)]
        declared_rows = [
            DeclaredRow(
                item_id=None if _is_empty_id(row["Talep ID"])
                else str(row["Talep ID"]),
                desi=float(row["Taşınan Desi"]),
                travel_minutes=float(row["Yolculuk süresi"]),
                arrival_handling_minutes=float(
                    row["Varış elleçleme süresi"]),
                departure_handling_minutes=float(
                    row["Çıkış Elleçleme süresi"]),
                sla_penalty=float(row["SLA cezası"]),
                total_cost=float(row["Toplam maliyet"]),
            )
            for _, row in g.iterrows()
        ]
        kind = g["Araç Tipi"].iloc[0]
        vtype = g["Araç türü"].iloc[0]
        leg_violations = []
        declared_arrivals = [
            parse_dt(str(row["Varış Tarihi"]), str(row["Varış Saati"]))
            for _, row in g.iterrows()
        ]
        if len(set(declared_arrivals)) > 1:
            leg_violations.append(
                f"{vid}: aynı bacak grubunda beyan varış tutarsız"
            )
        for column in ("Araç Tipi", "Araç türü"):
            values = list(dict.fromkeys(str(v) for v in g[column]))
            if len(values) > 1:
                leg_violations.append(
                    f"{vid}: aynı bacak grubunda {column} tutarsız "
                    f"({', '.join(values)})")
        legs.append(Leg(
            vehicle_id=vid, kind=kind, vtype=vtype,
            origin=origin, dest=dest, dep=parse_dt(str(dtarih), str(dsaat)),
            declared_arr=declared_arrivals[0], items=items,
            violations=leg_violations,
            declared_rows=declared_rows,
        ))
    legs.sort(key=lambda l: (l.vehicle_id, l.dep))
    return legs


def trace_vehicle(legs: list, data) -> VehicleTrace:
    """Tek bir aracın bacak zincirini zaman çizelgesine çevirir."""
    assert legs and all(l.vehicle_id == legs[0].vehicle_id for l in legs)
    legs = sorted(legs, key=lambda l: l.dep)
    tr = VehicleTrace(vehicle_id=legs[0].vehicle_id, kind=legs[0].kind,
                      vtype=legs[0].vtype, legs=legs)
    for leg in legs:
        tr.violations.extend(leg.violations)
        if leg.kind != tr.kind or leg.vtype != tr.vtype:
            tr.violations.append(
                f"{tr.vehicle_id}: bacak araç tipi/türü tutarsız "
                f"({leg.kind}/{leg.vtype} != {tr.kind}/{tr.vtype})")
            break
    vt = data.vehicles[tr.vtype]
    hourly = vt.spot_hourly if tr.kind == "Spot" else vt.rental_hourly
    per_km = vt.spot_per_km if tr.kind == "Spot" else vt.rental_per_km

    prev_items = {}          # önceki bacaktan gemide kalanlar {talep_id: desi}
    seen_item_desi = {}      # aynı talep parçasının miktarı bacaklar arasında sabittir
    prev_unload_end = None
    prev_dest = None

    for i, leg in enumerate(legs):
        if prev_dest is not None and leg.origin != prev_dest:
            tr.violations.append(f"{leg.vehicle_id}: bacak zinciri kopuk "
                                 f"({prev_dest} -> {leg.origin})")
        cur_items = dict(leg.items)
        for talep_id, desi in cur_items.items():
            previous_desi = seen_item_desi.get(talep_id)
            if previous_desi is not None and abs(previous_desi - desi) > 1e-6:
                tr.violations.append(
                    f"{talep_id}: bacaklar arasında desi değişiyor "
                    f"({previous_desi:.1f} -> {desi:.1f}); hub'da desi "
                    "yaratılamaz/kaybolamaz")
            else:
                seen_item_desi[talep_id] = desi
        ids = [t for t, _ in leg.items]
        if len(ids) != len(set(ids)):
            tr.violations.append(
                f"{leg.vehicle_id}: aynı bacakta tekrarlı talep ID")
        if sum(cur_items.values()) > vt.capacity_desi + 1e-6:
            tr.violations.append(
                f"{leg.vehicle_id}: kapasite aşımı "
                f"({sum(cur_items.values()):.0f} > {vt.capacity_desi})")
        lane = data.lanes.get((leg.origin, leg.dest))
        if lane is None:
            tr.violations.append(f"{leg.vehicle_id}: matriste olmayan hat "
                                 f"{leg.origin}->{leg.dest}")
            tr.leg_times.append(None)
            prev_dest = leg.dest
            continue

        # Bu bacakta YENİ yüklenen desi (gemide kalanlar elleçlenmez)
        new_desi = sum(d for t, d in cur_items.items()
                       if t not in prev_items or abs(prev_items[t] - d) > 1e-6)
        load_min = handling_minutes(new_desi)
        load_start = leg.dep - timedelta(minutes=load_min)
        if load_min > 0:
            tr.events.append(HandlingEvent(leg.origin, load_start, leg.dep,
                                           new_desi, "load"))
        if prev_unload_end is not None and load_start < prev_unload_end:
            tr.violations.append(
                f"{leg.vehicle_id}: yükleme {load_start:%d.%m %H:%M} önceki "
                f"işlem bitmeden ({prev_unload_end:%d.%m %H:%M}) başlıyor")
        if tr.usage_start is None:
            tr.usage_start = load_start

        arr = leg.dep + timedelta(minutes=travel_minutes(lane.hours[tr.vtype]))
        if leg.declared_arr != arr:
            tr.violations.append(
                f"{leg.vehicle_id}: beyan varış {leg.declared_arr:%d.%m %H:%M} "
                f"!= matris varışı {arr:%d.%m %H:%M}"
            )
        # Bir sonraki bacakta da aynı (id, desi) ile devam edenler inmez
        next_leg = legs[i + 1] if i + 1 < len(legs) else None
        stay = {}
        if next_leg is not None and next_leg.origin == leg.dest:
            nxt = dict(next_leg.items)
            stay = {t: d for t, d in cur_items.items()
                    if t in nxt and abs(nxt[t] - d) < 1e-6}
        unload_desi = sum(d for t, d in cur_items.items() if t not in stay)
        unload_min = handling_minutes(unload_desi)
        unload_end = arr + timedelta(minutes=unload_min)
        if unload_min > 0:
            tr.events.append(HandlingEvent(leg.dest, arr, unload_end,
                                           unload_desi, "unload"))
        tr.leg_times.append({"load_start": load_start, "dep": leg.dep,
                             "arr": arr, "unload_end": unload_end,
                             "loaded": new_desi, "unloaded": unload_desi})
        tr.total_km += lane.km
        prev_items = stay
        prev_unload_end = unload_end
        prev_dest = leg.dest
        tr.usage_end = unload_end

    if tr.usage_start is not None and tr.usage_end is not None:
        tr.usage_hours = (tr.usage_end - tr.usage_start).total_seconds() / 3600
    tr.cost = hourly * tr.usage_hours + per_km * tr.total_km
    return tr


# --- Bölüm 2: tam simülasyon ---
from src.ledger import HandlingLedger, TirLedger
from src.schemas import _canonical_forecast_time, base_demand_id
from src.timeutil import SLA_TL_PER_DESI_HOUR, late_hours


@dataclass
class SimResult:
    vehicle_cost: float
    sla_penalty: float
    total_cost: float
    violations: list
    per_vehicle: pd.DataFrame
    per_demand: pd.DataFrame


def _forecast_datetime(row) -> datetime:
    value = row["Talep Tamamlama Saati"]
    canonical = _canonical_forecast_time(value)
    if canonical is None:
        raise ValueError(f"Geçersiz forecast saati: {value!r}")
    return parse_dt(str(row["Tarih"]), canonical)


def _forecast_records(forecast_df: pd.DataFrame, data, violations: list) -> dict:
    """talep_id -> dict(ready, origin, dest, desi, deadline)"""
    out = {}
    seen_ids = set()
    for _, r in forecast_df.iterrows():
        demand_id = str(r["Talep ID"])
        if demand_id in seen_ids:
            violations.append(
                f"{demand_id}: tahmin dosyasında tekrarlı talep ID")
            continue
        seen_ids.add(demand_id)
        key = (r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"])
        lane = data.lanes.get(key)
        if lane is None:
            violations.append(f"{r['Talep ID']}: matriste olmayan tahmin hattı {key}")
            continue
        ready = _forecast_datetime(r)
        out[demand_id] = {
            "ready": ready,
            "origin": key[0],
            "dest": key[1],
            "desi": float(r["Tahmin Edilen Desi"]),
            "deadline": ready + timedelta(hours=24 * lane.sla_days),
        }
    return out


_DESI_EPSILON = 1e-6
_SLA_TOLERANCE = Decimal("0.000001")
_COST_TOLERANCE = Decimal("0.01")


def _same_declared_cargo(left: DeclaredRow, right: DeclaredRow) -> bool:
    return (left.item_id == right.item_id
            and abs(left.desi - right.desi) < _DESI_EPSILON)


def _contains_declared_cargo(rows: list[DeclaredRow], row: DeclaredRow) -> bool:
    return any(_same_declared_cargo(candidate, row) for candidate in rows)


def _declared_operations(legs: list[Leg]) -> dict[tuple[int, int], tuple[bool, bool]]:
    """Derive load/unload ownership using only adjacent declared output rows."""
    cargo_by_leg = [
        [row for row in leg.declared_rows if row.item_id is not None]
        for leg in legs
    ]
    operations = {}
    previous_stay = []
    for leg_index, leg in enumerate(legs):
        connected_previous = (
            leg_index > 0 and legs[leg_index - 1].dest == leg.origin
        )
        connected_next = (
            leg_index + 1 < len(legs)
            and leg.dest == legs[leg_index + 1].origin
        )
        current_stay = []
        for row_index, row in enumerate(leg.declared_rows):
            if row.item_id is None:
                operations[(leg_index, row_index)] = (False, False)
                continue
            is_new = (not connected_previous
                      or not _contains_declared_cargo(previous_stay, row))
            stays = (connected_next
                     and _contains_declared_cargo(
                         cargo_by_leg[leg_index + 1], row))
            operations[(leg_index, row_index)] = (is_new, not stays)
            if stays:
                current_stay.append(row)
        previous_stay = current_stay
    return operations


def _as_decimal(value) -> Decimal:
    return Decimal(str(value))


def _row_declaration_context(
        trace: VehicleTrace, leg: Leg, row: DeclaredRow) -> str:
    item_id = row.item_id if row.item_id is not None else "<boş>"
    return (f"{trace.vehicle_id}: {leg.origin}->{leg.dest} "
            f"{leg.dep:%d.%m.%Y %H:%M} talep {item_id}")


def _check_exact_declaration(
        violations: list, context: str, field_name: str,
        declared: float, expected: float) -> None:
    if declared != expected:
        violations.append(
            f"{context} {field_name} beyan={declared}, beklenen={float(expected)}")


def _check_decimal_declaration(
        violations: list, context: str, field_name: str,
        declared: Decimal, expected: Decimal, tolerance: Decimal) -> None:
    if abs(declared - expected) > tolerance:
        violations.append(
            f"{context} {field_name} beyan={declared}, beklenen={expected}")


def _trace_context(trace: VehicleTrace) -> str:
    segments = "; ".join(
        f"{leg.origin}->{leg.dest} {leg.dep:%d.%m.%Y %H:%M}"
        for leg in trace.legs
    )
    return f"{trace.vehicle_id}: [{segments}] talep <iz toplamı>"


def _validate_empty_trace(
        trace: VehicleTrace, data, declared: list[tuple[int, int, Leg, DeclaredRow]],
        violations: list) -> None:
    context = _trace_context(trace)
    if trace.kind != "Kiralık":
        violations.append(
            f"{context} Boş fiziksel iz yalnız Kiralık olabilir "
            f"(beyan={trace.kind}, beklenen=Kiralık)")
    if (len(declared) != 1 or declared[0][3].item_id is not None
            or declared[0][3].desi != 0.0):
        violations.append(
            f"{context} Boş fiziksel iz tam bir boş beyan satırı gerektirir "
            f"(beyan={len(declared)}, beklenen=1)")
    matching_rental = (
        len(trace.legs) == 1
        and any(
            (trace.legs[0].origin, trace.legs[0].dest)
            == (route.origin, route.dest)
            and trace.vtype == route.vehicle
            for route in data.rentals
        )
    )
    if not matching_rental:
        violations.append(
            f"{context} Boş fiziksel iz eşleşen kiralık rota gerektirir "
            "(beyan=yok, beklenen=eşleşen rota)")


def _validate_trace_declarations(
        trace: VehicleTrace, demands: dict, data, violations: list) -> None:
    operations = _declared_operations(trace.legs)
    declared = [
        (leg_index, row_index, leg, row)
        for leg_index, leg in enumerate(trace.legs)
        for row_index, row in enumerate(leg.declared_rows)
    ]
    cargo = [entry for entry in declared if entry[3].item_id is not None]
    empty_trace = not cargo
    if empty_trace:
        _validate_empty_trace(trace, data, declared, violations)

    unique_new_positions = set()
    unique_new_rows = []
    for leg_index, row_index, _leg, row in cargo:
        is_new, _is_unloaded = operations[(leg_index, row_index)]
        if is_new and not _contains_declared_cargo(unique_new_rows, row):
            unique_new_positions.add((leg_index, row_index))
            unique_new_rows.append(row)
    new_total = sum(
        (_as_decimal(row.desi) for row in unique_new_rows), Decimal("0")
    )

    trace_cost = _as_decimal(trace.cost)
    cost_expected = all(
        (leg.origin, leg.dest) in data.lanes for leg in trace.legs
    )
    actual_vehicle_total = Decimal("0")
    for leg_index, row_index, leg, row in declared:
        context = _row_declaration_context(trace, leg, row)
        lane = data.lanes.get((leg.origin, leg.dest))
        if lane is not None:
            expected_travel = travel_minutes(lane.hours[trace.vtype])
            _check_exact_declaration(
                violations, context, "Yolculuk süresi",
                row.travel_minutes, expected_travel)

        is_new, is_unloaded = operations[(leg_index, row_index)]
        expected_departure = handling_minutes(row.desi) if is_new else 0
        expected_arrival = handling_minutes(row.desi) if is_unloaded else 0
        _check_exact_declaration(
            violations, context, "Çıkış Elleçleme süresi",
            row.departure_handling_minutes, expected_departure)
        _check_exact_declaration(
            violations, context, "Varış elleçleme süresi",
            row.arrival_handling_minutes, expected_arrival)

        expected_sla = None
        if row.item_id is None:
            expected_sla = Decimal("0")
        else:
            rec = demands.get(base_demand_id(row.item_id))
            if rec is None:
                missing = f"{row.item_id}: tahmin dosyasında olmayan talep"
                if not any(violation.startswith(missing)
                           for violation in violations):
                    violations.append(missing)
            elif is_unloaded and leg.dest == rec["dest"]:
                leg_time = (trace.leg_times[leg_index]
                            if leg_index < len(trace.leg_times) else None)
                if leg_time is not None:
                    expected_sla = (
                        _as_decimal(row.desi)
                        * Decimal(late_hours(
                            rec["deadline"], leg_time["unload_end"]))
                        * _as_decimal(SLA_TL_PER_DESI_HOUR)
                    )
            else:
                expected_sla = Decimal("0")
        declared_sla = _as_decimal(row.sla_penalty)
        if expected_sla is not None:
            _check_decimal_declaration(
                violations, context, "SLA cezası", declared_sla,
                expected_sla, _SLA_TOLERANCE)

        actual_vehicle = _as_decimal(row.total_cost) - declared_sla
        actual_vehicle_total += actual_vehicle
        if cost_expected:
            if empty_trace:
                expected_vehicle = (
                    trace_cost if row_index == 0 and leg_index == 0
                    else Decimal("0")
                )
            elif ((leg_index, row_index) in unique_new_positions
                  and new_total != 0):
                expected_vehicle = (
                    trace_cost * _as_decimal(row.desi) / new_total
                )
            else:
                expected_vehicle = Decimal("0")
            _check_decimal_declaration(
                violations, context, "Araç maliyeti payı", actual_vehicle,
                expected_vehicle, _COST_TOLERANCE)

    if cost_expected:
        _check_decimal_declaration(
            violations, _trace_context(trace),
            "Toplam maliyet uzlaşmıyor; Fiziksel iz araç maliyeti toplamı",
            actual_vehicle_total,
            trace_cost, _COST_TOLERANCE)


def simulate(plan_df: pd.DataFrame, forecast_df: pd.DataFrame, data,
             rental_days: list[date] | None = None) -> SimResult:
    """Planı simüle eder.

    ``rental_days=None``: kiralık zorunluluğu forecast günleri + son kargo
    tesliminin bittiği güne kadar denetlenir (Q&A: kiralık filo dağıtım
    bitene kadar her gün çıkar; 6-7 Temmuz sarkmaları dahil). Açık liste
    verilirse (ör. ``[]``) kontrol aralığını çağıran belirler.
    """
    violations = []
    demands = _forecast_records(forecast_df, data, violations)
    auto_rental_days = rental_days is None
    legs = parse_legs(plan_df)

    by_vehicle = {}
    for leg in legs:
        by_vehicle.setdefault(leg.vehicle_id, []).append(leg)
    traces = {vid: trace_vehicle(v_legs, data) for vid, v_legs in by_vehicle.items()}

    handling = HandlingLedger(data.handling_cap)
    tir = TirLedger(data.tir_cap)
    part_moves = {}   # talep_id -> [(dep, load_start, unload_end, origin, dest, vid, desi)]
    deliveries = {}   # base -> {part_id: (desi, unload_end, dest)}

    for tr in traces.values():
        violations.extend(tr.violations)
        for ev in tr.events:
            handling.add(ev.tm, ev.start, ev.desi)
        for i, leg in enumerate(tr.legs):
            lt = tr.leg_times[i] if i < len(tr.leg_times) else None
            if lt is None:
                continue    # matriste olmayan hat; ihlal zaten yazıldı
            if tr.vtype == "Tır":
                # ziyaret: bacak i kalkışı = visit i, varışı = visit i+1
                # (böylece i varışı ile i+1 kalkışı aynı TM'de tek ziyaret)
                tir.add_event(leg.origin, leg.dep.date(), tr.vehicle_id, visit_id=i)
                tir.add_event(leg.dest, lt["arr"].date(), tr.vehicle_id, visit_id=i + 1)
            for talep_id, desi in leg.items:
                base = base_demand_id(talep_id)
                rec = demands.get(base)
                if rec is None:
                    violations.append(f"{talep_id}: tahmin dosyasında olmayan talep")
                    continue
                part_moves.setdefault(talep_id, []).append(
                    (leg.dep, lt["load_start"], lt["unload_end"],
                     leg.origin, leg.dest, tr.vehicle_id, desi))
                cur = deliveries.setdefault(base, {}).get(talep_id)
                if cur is None or lt["unload_end"] > cur[1]:
                    deliveries[base][talep_id] = (desi, lt["unload_end"], leg.dest)
                if rec["origin"] == leg.origin and lt["load_start"] < rec["ready"]:
                    violations.append(
                        f"{talep_id}: yükleme talep hazır olmadan başlıyor "
                        f"({lt['load_start']:%d.%m %H:%M} < {rec['ready']:%d.%m %H:%M})")

    for trace in traces.values():
        _validate_trace_declarations(trace, demands, data, violations)

    # parça rota sürekliliği + araç-değişimli aktarma zamanlaması
    for tid, moves in part_moves.items():
        moves.sort(key=lambda m: m[0])
        first_origin = moves[0][3]
        rec0 = demands.get(base_demand_id(tid))
        if rec0 is not None and first_origin != rec0["origin"]:
            violations.append(
                f"{tid}: rota tahmin çıkışından başlamıyor "
                f"({first_origin} != {rec0['origin']})")
        for m1, m2 in zip(moves, moves[1:]):
            _, _, ue1, _, d1, v1, desi1 = m1
            _, ls2, _, o2, _, v2, desi2 = m2
            if v2 != v1 and abs(desi1 - desi2) > 1e-6:
                violations.append(
                    f"{tid}: bacaklar arasında desi değişiyor "
                    f"({d1}: {desi1:.1f} -> {desi2:.1f}); hub'da desi "
                    "yaratılamaz/kaybolamaz")
            if o2 != d1:
                violations.append(f"{tid}: rota kopuk ({d1} -> {o2})")
            elif v2 != v1 and ls2 < ue1:
                violations.append(
                    f"{tid}: aktarma zamanlaması ihlali ({o2}: yükleme "
                    f"{ls2:%H:%M} < indirme bitişi {ue1:%H:%M})")

    # teslim bütünlüğü + SLA
    demand_rows = []
    sla_penalty = 0.0
    for base, rec in demands.items():
        parts = deliveries.get(base, {})
        final_parts = {pid: (d, t) for pid, (d, t, dest) in parts.items()
                       if dest == rec["dest"]}
        delivered = sum(d for d, _ in final_parts.values())
        if abs(delivered - rec["desi"]) > 1e-6:
            violations.append(
                f"{base}: teslim edilen desi {delivered:.1f} != tahmin {rec['desi']:.1f}")
        penalty = 0.0
        for pid, (d, t) in final_parts.items():
            penalty += d * late_hours(rec["deadline"], t) * SLA_TL_PER_DESI_HOUR
        sla_penalty += penalty
        demand_rows.append({"talep_id": base, "desi": rec["desi"],
                            "teslim_desi": delivered, "ceza": penalty})

    # kiralık kuralları
    for tr in traces.values():
        if tr.kind != "Kiralık":
            continue
        for leg in tr.legs:
            ok = any((leg.origin, leg.dest) == (rr.origin, rr.dest)
                     and leg.vtype == rr.vehicle for rr in data.rentals)
            if not ok:
                violations.append(
                    f"{tr.vehicle_id}: kiralık rota dışı {leg.origin}->{leg.dest}")
        day_counts = {}
        for leg in tr.legs:
            day_counts[leg.dep.date()] = day_counts.get(leg.dep.date(), 0) + 1
        for day, n in day_counts.items():
            if n > 1:
                violations.append(f"{tr.vehicle_id}: kiralık araç aynı gün {n} bacak")
        days = {leg.dep.date() for leg in tr.legs}
        if len(days) > 1:
            violations.append(
                f"{tr.vehicle_id}: kiralık araç ID birden fazla günde "
                f"kullanılmış ({len(days)} gün); gün başına benzersiz ID verin")
    if auto_rental_days:
        fc_days = sorted({
            _forecast_datetime(r).date()
            for _, r in forecast_df.iterrows()
        })
        if fc_days:
            cargo_end = max(
                (lt["unload_end"].date() for tr in traces.values()
                 for lt in tr.leg_times
                 if lt is not None and lt["unloaded"] > 0),
                default=None)
            end = max(fc_days[-1],
                      cargo_end if cargo_end is not None else fc_days[-1])
            rental_days = [fc_days[0] + timedelta(days=i)
                           for i in range((end - fc_days[0]).days + 1)]
        else:
            rental_days = []

    kiralik_legs = [l for l in legs if l.kind == "Kiralık"]
    for day in rental_days:
        for rr in data.rentals:
            n = sum(1 for l in kiralik_legs
                    if l.dep.date() == day
                    and (l.origin, l.dest) == (rr.origin, rr.dest)
                    and l.vtype == rr.vehicle)
            if n != rr.count:
                violations.append(
                    f"Kiralık ihlali {day}: {rr.origin}->{rr.dest} {rr.vehicle} "
                    f"beklenen {rr.count}, plandaki {n}")

    violations.extend(handling.violations())
    violations.extend(tir.violations())

    vehicle_cost = sum(tr.cost for tr in traces.values())
    per_vehicle = pd.DataFrame([{
        "vehicle_id": tr.vehicle_id, "kind": tr.kind, "vtype": tr.vtype,
        "legs": len(tr.legs), "km": tr.total_km,
        "usage_hours": tr.usage_hours, "cost": tr.cost,
    } for tr in traces.values()], columns=["vehicle_id", "kind", "vtype", "legs", "km", "usage_hours", "cost"])
    return SimResult(
        vehicle_cost=vehicle_cost,
        sla_penalty=sla_penalty,
        total_cost=vehicle_cost + sla_penalty,
        violations=violations,
        per_vehicle=per_vehicle,
        per_demand=pd.DataFrame(demand_rows, columns=["talep_id", "desi", "teslim_desi", "ceza"]),
    )
