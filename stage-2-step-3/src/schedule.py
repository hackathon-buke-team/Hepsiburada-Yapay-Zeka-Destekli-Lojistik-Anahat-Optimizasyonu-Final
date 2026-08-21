"""Dakika çizelgeleyici: planlanmış bacakları şablon plan DataFrame'ine
dönüştürür.

Görevler: araç/talep kimliği üretimi, elleçleme kapasitesi düzeltmeleri
(gece yarısı kaydırma), tır defteri doğrulaması ve şablon kolonlarının
(beyan süreleri + maliyet paylaşımı) doldurulması. Kesin hakem her zaman
simülatördür; buradaki maliyet paylaşımı beyan kolonları içindir.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

import pandas as pd

from src.chain import analyze_leg_flows, physical_routes
from src.ledger import HandlingLedger, TirLedger
from src.optimize import PlannedLeg
from src.schemas import PLAN_COLS
from src.timeutil import (SLA_TL_PER_DESI_HOUR, fmt_date, fmt_time,
                          handling_minutes, late_hours, travel_minutes)

# Elleçleme düzeltmesinde kaydırma denemesi üst sınırı.
MAX_SHIFT_TRIES = 500


def _retime(leg: PlannedLeg, new_load_start: datetime, lane) -> None:
    """Bacağı yeni yükleme başlangıcına kaydırır (kullanım süresi sabit)."""
    load_min = handling_minutes(leg.desi)
    leg.load_start = new_load_start
    leg.dep = new_load_start + timedelta(minutes=load_min)
    leg.arr = leg.dep + timedelta(minutes=travel_minutes(lane.hours[leg.vtype]))
    leg.unload_end = leg.arr + timedelta(minutes=handling_minutes(leg.desi))


def _shiftable(leg: PlannedLeg) -> bool:
    """Yalnız bağımsız Spot, Tır olmayan dolu bacaklar kaydırılabilir."""
    return (leg.chain_id is None and leg.desi > 0
            and leg.kind == "Spot" and leg.vtype != "Tır")


def _fix_handling(legs: list, data, notes: list) -> None:
    """Aşılan (TM, gün) elleçleme kapasitelerini gece yarısına kaydırır.

    Aşımı yaratan olaylar arasından en küçük spot (Tır olmayan) yükler
    seçilir; bacak bütün olarak ertesi güne kaydırılır. SLA etkisi ceza
    olarak kabul edilir; kapasite ihlali kabul edilemez.
    """
    def contributes(start, desi, day):
        if desi <= 0:
            return False
        end = start + timedelta(minutes=handling_minutes(desi))
        day_start = datetime.combine(day, time(0, 0))
        day_end = day_start + timedelta(days=1)
        return start < day_end and end > day_start

    for _ in range(MAX_SHIFT_TRIES):
        flows = analyze_leg_flows(legs)
        ledger = HandlingLedger(data.handling_cap)
        operations = []
        for leg, flow in zip(legs, flows):
            loaded_desi = sum(desi for _part, desi in flow.loaded)
            unloaded_desi = sum(desi for _part, desi in flow.unloaded)
            operations.append((leg, loaded_desi, unloaded_desi))
            if loaded_desi > 0:
                ledger.add(leg.origin, leg.load_start, loaded_desi)
            if unloaded_desi > 0:
                ledger.add(leg.dest, leg.arr, unloaded_desi)
        over = ledger.over_caps()
        if not over:
            return
        moved = False
        for tm, day, used, cap in over:
            midnight = datetime.combine(day + timedelta(days=1), time(0, 0))
            candidates = [
                leg for leg, loaded_desi, unloaded_desi in operations
                if _shiftable(leg)
                and ((leg.origin == tm
                      and contributes(leg.load_start, loaded_desi, day))
                     or (leg.dest == tm
                         and contributes(leg.arr, unloaded_desi, day)))]
            candidates.sort(key=lambda l: (l.desi, l.dep))
            for leg in candidates:
                if leg.load_start < midnight:
                    _retime(leg, midnight,
                            data.lanes[(leg.origin, leg.dest)])
                    moved = True
                    notes.append(f"Elleçleme düzeltmesi: {leg.vehicle_id} "
                                 f"{leg.origin}->{leg.dest} {day} sonrasına "
                                 f"kaydırıldı (aşım {used:.0f}>{cap:.0f})")
                    break
            if moved:
                break
        if not moved:
            notes.append(f"Elleçleme düzeltmesi bacak bulamadı: {over[0]}")
            return
    notes.append("Elleçleme düzeltmesi deneme sınırına ulaştı")


def _assign_ids(legs: list) -> None:
    """Araç (V0001...) ve talep parçası (D00001-1...) kimliklerini atar.

    Araç kimlikleri fiziksel rotalara kararlı sırayla atanır: önce kiralık
    (kalkış, hat), sonra spot. Bir talep tek fiziksel Part nesnesiyse temel
    kimliğini korur; bölündüyse ilk fiziksel geçiş sırasıyla -1, -2, ...
    alır.
    """
    routes = physical_routes(legs)
    ordered_routes = sorted(
        routes,
        key=lambda route: (
            route[0].kind != "Kiralık",
            route[0].dep,
            route[0].origin,
            route[0].dest,
        ),
    )
    for i, route in enumerate(ordered_routes, start=1):
        for leg in route:
            leg.vehicle_id = f"V{i:04d}"

    occurrences = []
    for leg in legs:
        leg.item_ids = [None] * len(leg.items)
        for pos, (part, _desi) in enumerate(leg.items):
            occurrences.append((leg, pos, part))
    occurrences.sort(
        key=lambda occurrence: (
            occurrence[0].dep,
            occurrence[0].vehicle_id,
            occurrence[1],
        )
    )

    pieces: dict[str, list] = {}
    for leg, pos, part in occurrences:
        pieces.setdefault(part.base_id, []).append((leg, pos, part))

    for base, plist in pieces.items():
        unique_identities = []
        seen_identities = set()
        for _leg, _pos, part in plist:
            identity = id(part)
            if identity not in seen_identities:
                seen_identities.add(identity)
                unique_identities.append(identity)

        if len(unique_identities) == 1:
            final_ids = {unique_identities[0]: base}
        else:
            final_ids = {
                identity: f"{base}-{i}"
                for i, identity in enumerate(unique_identities, start=1)
            }
        for leg, pos, part in plist:
            leg.item_ids[pos] = final_ids[id(part)]


def _check_tir(legs: list, data) -> list:
    """Tır ziyaret defterini kurar; ihlalleri (varsa) döner."""
    ledger = TirLedger(data.tir_cap)
    for leg in legs:
        if leg.vtype != "Tır":
            continue
        ledger.add_event(leg.origin, leg.dep.date(), leg.vehicle_id, 0)
        ledger.add_event(leg.dest, leg.arr.date(), leg.vehicle_id, 1)
    return ledger.violations()


def to_plan_frame(legs: list, data, fix: bool = True) -> tuple:
    """PlannedLeg listesini şablon PLAN_COLS DataFrame'ine çevirir.

    Döner: (plan_df, düzeltme_notları). Beyan kolonları:
    - Yolculuk süresi: bacak yol süresi (dk, yukarı yuvarlı; Q&A gereği
      oransal dağıtılmaz, her satırda tam yazılır)
    - Çıkış/Varış elleçleme süresi: yalnız gerçek yükleme/indirme işlemi
    - SLA cezası: yalnız nihai varış merkezindeki gerçek indirme
    - Toplam maliyet: fiziksel rota maliyetinin yeni yüklere payı + SLA
    """
    notes = []
    _assign_ids(legs)
    if fix:
        _fix_handling(legs, data, notes)
    flows = analyze_leg_flows(legs)
    tir_notes = _check_tir(legs, data)
    notes.extend(tir_notes)

    flow_by_leg = {
        id(leg): flow for leg, flow in zip(legs, flows)
    }
    route_meta = {}
    for route in physical_routes(legs):
        if len(route) > 1:
            for later_leg in route[1:]:
                if Decimal(str(later_leg.cost)) != Decimal("0"):
                    raise ValueError(
                        f"chain {route[0].chain_id}: later segment cost "
                        "must be zero")

        newly_loaded = [
            item
            for leg in route
            for item in flow_by_leg[id(leg)].loaded
        ]
        load_counts = {}
        for part, _desi in newly_loaded:
            identity = id(part)
            load_counts[identity] = load_counts.get(identity, 0) + 1
        if any(count != 1 for count in load_counts.values()):
            raise ValueError("physical Part must be newly loaded exactly once")

        new_total = sum(
            (Decimal(str(desi)) for _part, desi in newly_loaded),
            Decimal("0"),
        )
        if len(route) > 1 and new_total == Decimal("0"):
            raise ValueError(
                f"chain {route[0].chain_id}: empty multi-segment route")
        metadata = (len(route), route[0].cost, new_total)
        for leg in route:
            route_meta[id(leg)] = metadata

    rows = []
    for leg, flow in zip(legs, flows):
        lane = data.lanes[(leg.origin, leg.dest)]
        travel = travel_minutes(lane.hours[leg.vtype])
        route_length, route_cost, new_total = route_meta[id(leg)]
        if not leg.items:
            rows.append({
                "Araç ID": leg.vehicle_id, "Araç Tipi": leg.kind,
                "Araç türü": leg.vtype,
                "Çıkış Transfer Merkezi": leg.origin,
                "Varış Transfer Merkezi": leg.dest,
                "Çıkış Tarihi": fmt_date(leg.dep),
                "Çıkış Saati": fmt_time(leg.dep),
                "Varış Tarihi": fmt_date(leg.arr),
                "Varış Saati": fmt_time(leg.arr),
                "Talep ID": "", "Taşınan Desi": 0,
                "Yolculuk süresi": travel,
                "Varış elleçleme süresi": 0,
                "Çıkış Elleçleme süresi": 0,
                "SLA cezası": 0.0,
                "Toplam maliyet": leg.cost if route_length == 1 else 0.0,
            })
            continue
        loaded_ids = {id(part) for part, _desi in flow.loaded}
        unloaded_ids = {id(part) for part, _desi in flow.unloaded}
        for pos, (part, desi) in enumerate(leg.items):
            identity = id(part)
            loaded = identity in loaded_ids
            unloaded = identity in unloaded_ids
            penalty = (
                desi * late_hours(part.deadline, leg.unload_end)
                * SLA_TL_PER_DESI_HOUR
                if unloaded and leg.dest == part.dest else 0.0
            )
            if route_length == 1:
                share = leg.cost * (desi / leg.desi) if leg.desi else 0.0
            elif loaded:
                share = route_cost * (desi / float(new_total))
            else:
                share = 0.0
            total_cost = (share + penalty if route_length == 1
                          else float(share) + penalty)
            item_min = handling_minutes(desi)
            rows.append({
                "Araç ID": leg.vehicle_id, "Araç Tipi": leg.kind,
                "Araç türü": leg.vtype,
                "Çıkış Transfer Merkezi": leg.origin,
                "Varış Transfer Merkezi": leg.dest,
                "Çıkış Tarihi": fmt_date(leg.dep),
                "Çıkış Saati": fmt_time(leg.dep),
                "Varış Tarihi": fmt_date(leg.arr),
                "Varış Saati": fmt_time(leg.arr),
                "Talep ID": leg.item_ids[pos], "Taşınan Desi": desi,
                "Yolculuk süresi": travel,
                "Varış elleçleme süresi": item_min if unloaded else 0,
                "Çıkış Elleçleme süresi": item_min if loaded else 0,
                "SLA cezası": penalty,
                "Toplam maliyet": total_cost,
            })
    df = pd.DataFrame(rows, columns=PLAN_COLS)
    return df, notes
