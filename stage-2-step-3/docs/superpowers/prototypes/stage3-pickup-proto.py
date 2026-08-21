"""REFERANS PROTOTIPI — URETIM KODU DEGILDIR.

Stage 3 "rota ortasinda yuk alma" (Tier A) fikrinin buyuklugunu olcmek icin
yazildi. Olculen sonuc, 26 Temmuz 2026:

    Stage 2 taban : 11.313.338,286111113 TL
    Bu prototip   : 11.233.363,250000004 TL
    Tasarruf      :      79.975,036111109 TL   (0 ihlal, beyan = hakem)

Tasarim, bulunan uc hata ve uretim plani icin:
    docs/superpowers/plans/2026-07-26-stage3-midroute-pickup.md

Bu dosya bilerek repoda tutuluyor: yeni bir oturumun olcumu sifirdan yapmasina
gerek kalmasin. Uretim kodu (src/pickup.py) sifirdan, TDD ile yazilacaktir —
buradaki kod test edilmemistir, tek bir yol icin yazilmistir, kopyalanmamalidir.

Calistirma (depo kokunden):
    python docs/superpowers/prototypes/stage3-pickup-proto.py
"""
import sys, time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.chain import physical_routes
from src.data import load_all
from src.evaluation import evaluate_legs
from src.forecast import forecast_horizon, to_forecast_frame
from src.milkrun import (_decimal, _final_sla_tl, _leg_key,
                         _scheduled_direct_total_tl, _trial_candidate_valid,
                         _vehicle_cost_tl, run_milk_run_stage)
from src.optimize import PlannedLeg, build_plan, prepare_frame
from src.repair import run_same_lane_stage
from src.timeutil import handling_minutes, travel_minutes


def route_desi(items):
    return int(sum(Decimal(str(d)) for _p, d in items))


def price_route(segments, data):
    """Bir fiziksel rotanın (araç maliyeti + SLA) toplamını yeniden hesaplar."""
    km = Decimal("0")
    for s in segments:
        km += _decimal(data.lanes[(s.origin, s.dest)].km, "km")
    vehicle = _vehicle_cost_tl(segments[0].vtype, segments[0].load_start,
                               segments[-1].unload_end, km, data)
    sla = Decimal("0")
    for i, s in enumerate(segments):
        following = segments[i + 1].items if i + 1 < len(segments) else []
        ids = {id(p) for p, _d in following}
        dropped = [(p, d) for p, d in s.items if id(p) not in ids]
        sla += _final_sla_tl(dropped, s.unload_end)
    return vehicle + sla, vehicle


def rebuild(segments, data, pickup_at=None, pickup_items=(), drop_at=None):
    """Zaman çizelgesini baştan kurar; pickup_at segment indeksinde yükleme."""
    out = []
    clock = segments[0].load_start
    carry = None
    for i, s in enumerate(segments):
        items = list(s.items)
        # Alınan yük YALNIZ yükleme durağından KENDİ varış durağına kadar
        # taşınır; hedefini geçip devam etmesi hem yanlış SLA hem yanlış
        # kapasite demek olurdu.
        if pickup_at is not None and pickup_at < i <= drop_at:
            items = items + list(pickup_items)
        load_start = clock if i == 0 else clock
        if i == 0:
            dep = load_start + timedelta(minutes=handling_minutes(route_desi(items)))
        else:
            dep = clock
        lane = data.lanes[(s.origin, s.dest)]
        arr = dep + timedelta(minutes=travel_minutes(float(lane.hours[s.vtype])))
        # bu durakta inen yük
        following = segments[i + 1].items if i + 1 < len(segments) else []
        ids = {id(p) for p, _d in following}
        dropped = [(p, d) for p, d in items if id(p) not in ids
                   and not (pickup_at is not None and i <= pickup_at
                            and id(p) in {id(pp) for pp, _ in pickup_items})]
        # pickup varışı da bu durakta olabilir
        drop_desi = route_desi(dropped)
        # unload_end = İNDİRMENİN bittiği an. SLA bu ana göre hesaplanır;
        # sonraki yükleme bunu GECİKTİRMEZ (yük çoktan teslim edilmiştir).
        unload_end = arr + timedelta(minutes=handling_minutes(drop_desi))
        # Jüri S6: aynı durakta indir + yükle iki ARDIŞIK işlemdir; araç
        # ancak yükleme de bitince hareket eder. Yani sonraki segmentin
        # kalkışı gecikir, ama bu duraktaki SLA damgası gecikmez.
        depart_after = unload_end
        if pickup_at is not None and i == pickup_at:
            depart_after = unload_end + timedelta(
                minutes=handling_minutes(route_desi(pickup_items)))
        out.append(PlannedLeg(
            kind=s.kind, vtype=s.vtype, origin=s.origin, dest=s.dest,
            load_start=load_start if i == 0 else dep, dep=dep, arr=arr,
            unload_end=unload_end, items=items, cost=0.0, penalty=0.0,
            chain_id=s.chain_id, chain_seq=s.chain_seq))
        clock = depart_after

    # Beyan kolonları: fiziksel rotanın araç maliyeti YALNIZ segment 0'da,
    # SLA her durakta kendi inen yükü için (milkrun ile aynı sözleşme).
    km = Decimal("0")
    for s in out:
        km += _decimal(data.lanes[(s.origin, s.dest)].km, "km")
    vehicle = _vehicle_cost_tl(out[0].vtype, out[0].load_start,
                               out[-1].unload_end, km, data)
    for i, s in enumerate(out):
        following = out[i + 1].items if i + 1 < len(out) else []
        ids = {id(p) for p, _d in following}
        dropped = [(p, d) for p, d in s.items if id(p) not in ids]
        s.penalty = float(_final_sla_tl(dropped, s.unload_end))
        s.cost = float(vehicle) if i == 0 else 0.0
    return out


def main():
    data = load_all()
    fc = to_forecast_frame(forecast_horizon(data.demand, date(2026, 6, 29), date(2026, 7, 5)))
    days = [date(2026, 6, 29) + timedelta(days=i) for i in range(7)]
    s1 = run_same_lane_stage(build_plan(data, prepare_frame(fc), days), fc, data)
    s2 = run_milk_run_stage(s1.selected, fc, data)
    print("Stage 2 taban:", Decimal(str(s2.selected.result.total_cost)))

    legs = deepcopy(s2.selected.legs)
    routes = physical_routes(legs)
    print("fiziksel rota:", len(routes))

    # Donör havuzu: tek bacaklı, yüklü, Spot, zincirsiz
    donors = [r[0] for r in routes if len(r) == 1 and r[0].kind == "Spot" and r[0].items]
    chains = [r for r in routes if len(r) > 1]
    print("donör (tek bacak Spot):", len(donors), "| zincir:", len(chains))

    cap = {vt: int(data.vehicles[vt].capacity_desi) for vt in data.vehicles}
    cand = []
    examined = 0
    rented_targets = 0
    for ri, route in enumerate(routes):
        # JÜRİ KURALI: "Kiralık araçlarla uğrama yapılmaz." Kiralık rotalar
        # yük alma hedefi OLAMAZ. (Ayrıca maliyetleri kiralık tarifesinden
        # hesaplanır; spot tarifesiyle fiyatlamak sessiz bir hata olurdu.)
        if route[0].kind != "Spot":
            rented_targets += 1
            continue
        for i in range(len(route) - 1):          # ara duraklar
            hub = route[i].dest
            hub_time = route[i].unload_end
            later = {route[j].dest: j for j in range(i + 1, len(route))}
            for di, d in enumerate(donors):
                examined += 1
                if d.origin != hub or d.dest not in later:
                    continue
                if d.load_start < hub_time:
                    # yük hub'da hazır olmalı; zincir vardığında yükleyebiliriz
                    pass
                if any(p.ready > hub_time for p, _x in d.items):
                    continue
                add = route_desi(d.items)
                # kapasite: pickup'tan SONRAKİ her segment
                ok = all(route_desi(route[j].items) + add <= cap[route[0].vtype]
                         for j in range(i + 1, later[d.dest] + 1))
                if not ok:
                    continue
                old_route_cost, _ = price_route(list(route), data)
                old_donor_cost = _scheduled_direct_total_tl(d, data)
                new_segs = rebuild(list(route), data, pickup_at=i,
                                   pickup_items=d.items, drop_at=later[d.dest])
                new_route_cost, _ = price_route(new_segs, data)
                delta = new_route_cost - (old_route_cost + old_donor_cost)
                if delta < 0:
                    cand.append((delta, ri, i, di, new_segs))
    print("kiralık olduğu için atlanan rota:", rented_targets)
    print(f"incelenen (rota-durak, donör) çifti: {examined:,}")
    print("kârlı aday:", len(cand))
    if not cand:
        print("TIER A: 0 kârlı aday"); return

    cand.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
    used_routes, used_donors = set(), set()
    accepted = []
    rejected_by_ledger = 0
    # Kabul edilen her hamleden SONRAKİ durumu taşıyarak ilerle; muhafız
    # birden çok yük almayı BİRİKTİREREK doğrulamalı.
    state = {ri: list(route) for ri, route in enumerate(routes)}
    dropped = set()
    for delta, ri, i, di, new_segs in cand:
        if ri in used_routes or di in used_donors:
            continue
        trial = []
        for rj, route in enumerate(routes):
            if rj in dropped_routes if False else False:
                continue
            if rj == ri:
                trial.extend(new_segs); continue
            if len(route) == 1 and (id(route[0]) in dropped
                                    or id(route[0]) == id(donors[di])):
                continue
            trial.extend(state[rj])
        if not _trial_candidate_valid(trial, data):
            rejected_by_ledger += 1
            continue
        used_routes.add(ri); used_donors.add(di)
        state[ri] = new_segs
        dropped.add(id(donors[di]))
        accepted.append((delta, ri, di, new_segs))
    print("defter muhafızı reddi:", rejected_by_ledger)
    print("çakışmasız kabul:", len(accepted),
          "| analitik tasarruf:", -sum(a[0] for a in accepted))

    final = []
    for ri, route in enumerate(routes):
        if len(route) == 1 and id(route[0]) in dropped:
            continue
        final.extend(state[ri])
    print("segment:", len(final))
    ev = evaluate_legs(sorted(final, key=_leg_key), fc, data, fix=True)
    ev = evaluate_legs(sorted(final, key=_leg_key), fc, data, fix=True)
    tot = Decimal(str(ev.result.total_cost))
    print("=== HAKEMLİ SONUÇ ===")
    print("  ihlal      :", len(ev.result.violations))
    for v in ev.result.violations[:5]: print("    -", v)
    print("  araç       :", ev.result.vehicle_cost)
    print("  SLA        :", ev.result.sla_penalty)
    print("  TOPLAM     :", tot)
    print("  Stage 2'ye göre:", Decimal(str(s2.selected.result.total_cost)) - tot, "TL")


if __name__ == "__main__":
    main()