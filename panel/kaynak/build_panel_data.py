#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage-2-step-3/{datas,out}/*.xlsx  ->  panel/src/data/panel.json

Anahat Sevkiyat Panosu'nun (React dashboard) tek veri dosyasını üretir.
Her alan şartname veri setlerinden ya da bizim nihai çıktımızdan birebir okunur;
panoda elle yazılmış tek bir sayı yoktur.

Üretilen bölümler
  centres   18 transfer merkezi: konum, elleçleme kotası, tır kotası
  lanes     306 yönlü hat: mesafe, SLA günü, araç türü başına süre
  vtypes    4 araç türü: kapasite, kiralık/spot saatlik ve km maliyeti
  rented    12 zorunlu kiralık rota
  legs      nihai plandaki her araç hareketi (bacak)
  vehicles  fiziksel araç: bacakları, doluluğu, maliyeti, zincir uzunluğu
  daily     çıkış tarihi başına özet
  load      merkez-gün elleçleme tüketimi ve kota kullanımı
  tirv      merkez-gün tır ziyareti ve kota kullanımı
  forecast  7 günlük talep tahminimiz (bizim çıktımız)
  history   179 günlük geçmiş hacim + takvim bayrakları
  stages    Stage 0-3 maliyet merdiveni (sunum veri dosyasından)
"""
from __future__ import annotations

import sys

import calendar
import json
import math
import pathlib
import statistics
import unicodedata
from datetime import date, datetime, timedelta

import openpyxl

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = pathlib.Path(__file__).resolve().parent            # panel/kaynak
ROOT = HERE.parents[1]                                    # hb-final
PIPE = ROOT / "stage-2-step-3"
DATAS = PIPE / "datas"
OUTDIR = PIPE / "out"
DECK = ROOT / "sunum" / "kaynak" / "deck_data.json"
DEST = HERE.parent / "src" / "data" / "panel.json"

GEO = {
    "Balıkesir": (39.6484, 27.8826), "Bilecik": (40.1426, 29.9793),
    "Denizli": (37.7765, 29.0864),   "Erzincan": (39.7500, 39.5000),
    "Eskişehir": (39.7767, 30.5206), "Isparta": (37.7648, 30.5566),
    "İstanbul": (41.0082, 28.9784),  "Karaman": (37.1759, 33.2287),
    "Kocaeli": (40.7654, 29.9408),   "Kütahya": (39.4242, 29.9833),
    "Manisa": (38.6191, 27.4289),    "Mardin": (37.3212, 40.7245),
    "Mersin": (36.8121, 34.6415),    "Sivas": (39.7477, 37.0179),
    "Şanlıurfa": (37.1591, 38.7969), "Tekirdağ": (40.9780, 27.5110),
    "Yalova": (40.6550, 29.2769),    "Zonguldak": (41.4564, 31.7987),
}

HOLIDAYS = {                                   # src/backtest.py ile birebir aynı liste
    date(2026, 1, 1): "Yılbaşı",
    date(2026, 3, 19): "Ramazan arifesi",
    date(2026, 3, 20): "Ramazan Bayramı 1. gün",
    date(2026, 3, 21): "Ramazan Bayramı 2. gün",
    date(2026, 3, 22): "Ramazan Bayramı 3. gün",
    date(2026, 4, 23): "Ulusal Egemenlik ve Çocuk Bayramı",
    date(2026, 5, 1): "Emek ve Dayanışma Günü",
    date(2026, 5, 19): "Gençlik ve Spor Bayramı",
    date(2026, 5, 25): "Kurban Bayramı öncesi",
    date(2026, 5, 26): "Kurban Bayramı arifesi",
    date(2026, 5, 27): "Kurban Bayramı 1. gün",
    date(2026, 5, 28): "Kurban Bayramı 2. gün",
    date(2026, 5, 29): "Kurban Bayramı 3. gün",
    date(2026, 5, 30): "Kurban Bayramı 4. gün",
    date(2026, 5, 31): "Kurban Bayramı sonrası",
}


def find(fname: str) -> pathlib.Path:
    """Dosya adları diskte NFD biçiminde olabilir; NFC ile eşleştir."""
    want = unicodedata.normalize("NFC", fname)
    for p in DATAS.iterdir():
        if unicodedata.normalize("NFC", p.name) == want:
            return p
    raise FileNotFoundError(f"{fname} bulunamadı: {DATAS}")


def rows(src, sheet: str | None = None) -> list[tuple]:
    path = src if isinstance(src, pathlib.Path) else find(src)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    out = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] is not None]
    wb.close()
    return out


def hhmm(s) -> int:
    """'17:36' / time(17,36) -> gün içi dakika."""
    if hasattr(s, "hour"):
        return s.hour * 60 + s.minute
    h, m = str(s).split(":")[:2]
    return int(h) * 60 + int(m)


def dmy(s) -> date:
    """'29.06.2026' -> date."""
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    d, m, y = str(s).split(".")
    return date(int(y), int(m), int(d))


# ══════════════════════ 1 · statik ağ ══════════════════════
hand = {r[0]: float(r[1]) for r in rows("Ellecleme-kapasite.xlsx")}
tir = {r[0]: int(r[1]) for r in rows("tir_kapasiteleri v2.xlsx")}
lane_rows = rows("sehirler_arasi_lojistik.xlsx")
rented_rows = rows("Kiralık_Araclar.xlsx")
veh_rows = rows("Araç_Kapasite_Maliyet_Saat.xlsx")

assert set(hand) == set(tir) == set(GEO), "merkez listeleri uyuşmuyor"
names = sorted(hand, key=lambda n: (-hand[n], n))
IX = {n: i for i, n in enumerate(names)}

centres = [{"n": n, "lat": GEO[n][0], "lon": GEO[n][1],
            "hand": round(hand[n]), "tir": tir[n]} for n in names]

seen_od = {(r[1], r[2]) for r in rows("teknofest26_gelismis.xlsx")}
lanes = [{"a": IX[r[0]], "b": IX[r[1]], "km": int(r[2]), "sla": int(r[7]),
          "dur": {"Tır": float(r[3]), "Kamyon": float(r[4]),
                  "Hafif Kamyon": float(r[5]), "Kamyonet": float(r[6])},
          "seen": 1 if (r[0], r[1]) in seen_od else 0}
         for r in lane_rows]
LANE = {(l["a"], l["b"]): l for l in lanes}

vtypes = [{"n": r[0], "cap": int(r[1]),
           "rent_h": float(r[2]), "rent_km": float(r[3]),
           "spot_h": float(r[4]), "spot_km": float(r[5])} for r in veh_rows]
CAP = {v["n"]: v["cap"] for v in vtypes}

rented = [{"a": IX[r[0]], "b": IX[r[1]], "n": int(r[2]), "t": r[3].strip()}
          for r in rented_rows]

# ══════════════════════ 2 · nihai plan ══════════════════════
plan = rows(OUTDIR / "Tasima-plani.xlsx")
assert len(plan) > 5000, len(plan)

# bacak = (araç, çıkış, varış, çıkış tarihi, çıkış saati) ; satırlar talep parçalarıdır
legmap: dict[tuple, dict] = {}
order: list[tuple] = []
for r in plan:
    vid, kind, vt = r[0], r[1].strip(), r[2].strip()
    key = (vid, r[3], r[4], r[5], r[6])
    L = legmap.get(key)
    if L is None:
        L = legmap[key] = {
            "v": vid, "kind": kind, "vt": vt,
            "a": IX[r[3]], "b": IX[r[4]],
            "dd": r[5], "dt": r[6], "ad": r[7], "at": r[8],
            "desi": 0.0, "parts": 0, "sla": 0.0, "cost": 0.0,
            # yolculuk süresi bacak başına sabittir; elleçleme süreleri değil
            "trav": int(r[11]), "hun": 0, "hld": 0,
            "load": 0.0, "drop": 0.0,
            "ids": [], "idset": set(),
        }
        order.append(key)
    L["desi"] += float(r[10])
    L["parts"] += 1
    L["sla"] += float(r[14])
    L["cost"] += float(r[15])
    # Şartname çıktısında elleçleme süresi, parça o uçta GERÇEKTEN
    # yüklenip indirildiğinde dolar; aktarmadan geçen parçada 0'dır.
    L["hld"] += int(r[13])
    L["hun"] += int(r[12])
    if int(r[13]) > 0:
        L["load"] += float(r[10])
    if int(r[12]) > 0:
        L["drop"] += float(r[10])
    L["idset"].add(str(r[9]).split("-")[0])
    if len(L["ids"]) < 24:
        L["ids"].append(r[9])

D0 = min(dmy(L["dd"]) for L in legmap.values())


def tmin(d, t) -> int:
    """ufuk başlangıcından itibaren dakika."""
    return (dmy(d) - D0).days * 1440 + hhmm(t)


legs = []
for k in order:
    L = legmap[k]
    L["desi"] = round(L["desi"])
    L["load"] = round(L["load"])
    L["drop"] = round(L["drop"])
    L["sla"] = round(L["sla"], 2)
    L["cost"] = round(L["cost"], 2)
    L["t0"] = tmin(L["dd"], L["dt"])
    L["t1"] = tmin(L["ad"], L["at"])
    L["km"] = LANE[(L["a"], L["b"])]["km"]
    L["cap"] = CAP[L["vt"]]
    L["fill"] = round(100.0 * L["desi"] / L["cap"], 1)
    legs.append(L)

# ══════════════════════ 3 · fiziksel araçlar ══════════════════════
vmap: dict[str, dict] = {}
for i, L in enumerate(legs):
    V = vmap.get(L["v"])
    if V is None:
        V = vmap[L["v"]] = {"id": L["v"], "kind": L["kind"], "vt": L["vt"],
                            "cap": L["cap"], "legs": [], "desi": 0, "cost": 0.0,
                            "sla": 0.0, "km": 0, "parts": 0}
    V["legs"].append(i)
    V["desi"] = max(V["desi"], L["desi"])       # zincirde tepe yük
    V["cost"] += L["cost"]
    V["sla"] += L["sla"]
    V["km"] += L["km"]
    V["parts"] += L["parts"]

vehicles = []
for V in vmap.values():
    ls = [legs[i] for i in V["legs"]]
    ls.sort(key=lambda L: L["t0"])
    V["legs"] = [i for i in sorted(V["legs"], key=lambda i: legs[i]["t0"])]
    V["stops"] = len(ls)                        # bacak sayısı
    V["t0"], V["t1"] = ls[0]["t0"], ls[-1]["t1"]
    V["use"] = V["t1"] - V["t0"]
    V["dd"] = ls[0]["dd"]
    V["path"] = [ls[0]["a"]] + [L["b"] for L in ls]
    # yol üstü yük alma: ara durakta, önceki bacakta bulunmayan bir talep biniyorsa
    V["pickup"] = 1 if any(ls[i]["idset"] - ls[i - 1]["idset"] for i in range(1, len(ls))) else 0
    V["picked"] = len(set().union(*(ls[i]["idset"] - ls[i - 1]["idset"]
                                    for i in range(1, len(ls)))) if len(ls) > 1 else set())
    V["fill"] = round(100.0 * V["desi"] / V["cap"], 1)
    V["cost"] = round(V["cost"], 2)
    V["sla"] = round(V["sla"], 2)
    vehicles.append(V)
vehicles.sort(key=lambda V: V["id"])
VIX = {V["id"]: i for i, V in enumerate(vehicles)}
for L in legs:
    L["vi"] = VIX[L["v"]]

# ══════════════════════ 4 · gün bazlı özet ══════════════════════
dates = sorted({dmy(L["dd"]) for L in legs})
daily = []
for d in dates:
    dl = [L for L in legs if dmy(L["dd"]) == d]
    dv = {L["v"] for L in dl}
    daily.append({
        "d": d.strftime("%d.%m.%Y"), "iso": d.isoformat(), "dow": d.weekday(),
        "legs": len(dl), "vehicles": len(dv),
        "desi": round(sum(L["desi"] for L in dl)),
        "cost": round(sum(L["cost"] for L in dl), 2),
        "sla": round(sum(L["sla"] for L in dl), 2),
        "km": sum(L["km"] for L in dl),
        "rent": len({L["v"] for L in dl if L["kind"] == "Kiralık"}),
        "spot": len({L["v"] for L in dl if L["kind"] == "Spot"}),
    })

# ══════════════════════ 5 · merkez-gün kota tüketimi ══════════════════════
# Elleçleme kotası merkez başına GÜNLÜKTÜR ve 00:00'da sıfırlanır; gece yarısını
# aşan bir işlem iki güne süresiyle ORANTILI bölünür (şartname kuralı).
#
# İki defter tutuyoruz:
#   defter  — hakemin saydığı: o merkezde gerçekten yüklenen/indirilen desi.
#             Aktarmadan geçen yük o merkezde elleçlenmez, sayılmaz.
#   üst     — kötümser sınır: bacağın tüm desisi iki uca da yazılır.
#             Yalnız karşılaştırma için; hiçbir kural bunu talep etmez.
ndays = (max(dmy(L["ad"]) for L in legs) - D0).days + 1


def spread(grid: dict, ci: int, start_min: int, minutes: int, desi: float) -> None:
    """[start, start+minutes) penceresini gün sınırlarına oransal dağıt."""
    if desi <= 0:
        return
    if minutes <= 0:
        grid[(ci, start_min // 1440)] = grid.get((ci, start_min // 1440), 0.0) + desi
        return
    end = start_min + minutes
    m = start_min
    while m < end:
        day = m // 1440
        nxt = min(end, (day + 1) * 1440)
        grid[(ci, day)] = grid.get((ci, day), 0.0) + desi * (nxt - m) / minutes
        m = nxt


book: dict[tuple, float] = {}
upper: dict[tuple, float] = {}
for L in legs:
    spread(book, L["a"], L["t0"] - L["hld"], L["hld"], L["load"])
    spread(book, L["b"], L["t1"], L["hun"], L["drop"])
    spread(upper, L["a"], L["t0"] - L["hld"], L["hld"], L["desi"])
    spread(upper, L["b"], L["t1"], L["hun"], L["desi"])

loadgrid = [[round(book.get((c, d), 0.0)) for d in range(ndays)] for c in range(18)]
loadgrid_ust = [[round(upper.get((c, d), 0.0)) for d in range(ndays)] for c in range(18)]

tirv: dict[tuple, int] = {}
for L in legs:
    if L["vt"] != "Tır":
        continue
    tirv[(L["a"], L["t0"] // 1440)] = tirv.get((L["a"], L["t0"] // 1440), 0) + 1
    tirv[(L["b"], L["t1"] // 1440)] = tirv.get((L["b"], L["t1"] // 1440), 0) + 1
tirgrid = [[tirv.get((c, d), 0) for d in range(ndays)] for c in range(18)]

# ══════════════════════ 6 · hat bazlı akış ══════════════════════
flow: dict[tuple, dict] = {}
for L in legs:
    f = flow.setdefault((L["a"], L["b"]), {"a": L["a"], "b": L["b"], "legs": 0,
                                           "desi": 0, "cost": 0.0, "sla": 0.0})
    f["legs"] += 1
    f["desi"] += L["desi"]
    f["cost"] += L["cost"]
    f["sla"] += L["sla"]
laneflow = sorted(({**f, "cost": round(f["cost"], 2), "sla": round(f["sla"], 2)}
                   for f in flow.values()), key=lambda f: -f["desi"])

# ══════════════════════ 7 · tahmin (bizim çıktımız) ══════════════════════
fc_rows = rows(OUTDIR / "Talep-tahmini.xlsx")
fc_daily: dict[date, float] = {}
fc_slot = {9: 0.0, 17: 0.0}
fc_lane: dict[tuple, float] = {}
for r in fc_rows:
    d = dmy(r[1])
    v = float(r[5])
    fc_daily[d] = fc_daily.get(d, 0.0) + v
    fc_slot[hhmm(r[2]) // 60] = fc_slot.get(hhmm(r[2]) // 60, 0.0) + v
    fc_lane[(IX[r[3]], IX[r[4]])] = fc_lane.get((IX[r[3]], IX[r[4]]), 0.0) + v
forecast = {
    "rows": len(fc_rows),
    "zero": sum(1 for r in fc_rows if float(r[5]) == 0),
    "total": round(sum(fc_daily.values())),
    "daily": [{"iso": d.isoformat(), "d": d.strftime("%d.%m"), "dow": d.weekday(),
               "desi": round(v)} for d, v in sorted(fc_daily.items())],
    "slot": {str(k): round(v) for k, v in sorted(fc_slot.items())},
    "lane": [{"a": a, "b": b, "desi": round(v)} for (a, b), v in
             sorted(fc_lane.items(), key=lambda kv: -kv[1])[:60]],
}

# ══════════════════════ 8 · geçmiş veri ══════════════════════
hist_daily: dict[date, float] = {}
hist_dow: dict[int, list[float]] = {}
for r in rows("teknofest26_gelismis.xlsx"):
    d = r[0].date()
    hist_daily[d] = hist_daily.get(d, 0.0) + float(r[4])

MONTH_ENDS = set()
for m in range(1, 6):
    last = calendar.monthrange(2026, m)[1]
    MONTH_ENDS |= {date(2026, m, last), date(2026, m, last - 1)}
EXCLUDED = set(HOLIDAYS) | MONTH_ENDS
median_normal = statistics.median(v for d, v in hist_daily.items() if d not in EXCLUDED)

hdays = sorted(hist_daily)
for d in hdays:
    if d not in EXCLUDED:
        hist_dow.setdefault(d.weekday(), []).append(hist_daily[d])

TR_AY = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz"}
history = {
    "start": hdays[0].isoformat(), "dow0": hdays[0].weekday(),
    "median": round(median_normal),
    "days": [round(hist_daily[d]) for d in hdays],
    "flag": [(2 if d in MONTH_ENDS else 1) if d in EXCLUDED else 0 for d in hdays],
    "dowmed": {str(k): round(statistics.median(v)) for k, v in sorted(hist_dow.items())},
    "excluded": [{
        "iso": d.isoformat(), "d": f"{d.day:02d} {TR_AY[d.month]}",
        "v": round(hist_daily.get(d, 0.0)),
        "r": round(hist_daily.get(d, 0.0) / median_normal, 4),
        "me": 1 if d in MONTH_ENDS else 0,
        "h": HOLIDAYS.get(d, ""),
    } for d in sorted(EXCLUDED)],
}

# ══════════════════════ 9 · aşama merdiveni ══════════════════════
stages = json.loads(DECK.read_text(encoding="utf-8"))

# ══════════════════════ 10 · yaz ══════════════════════
total_cost = round(sum(L["cost"] for L in legs), 2)
meta = {
    "horizon": [dates[0].strftime("%d.%m.%Y"), dates[-1].strftime("%d.%m.%Y")],
    "start": D0.isoformat(), "ndays": ndays,
    "plan_rows": len(plan), "legs": len(legs), "vehicles": len(vehicles),
    "rent_vehicles": sum(1 for V in vehicles if V["kind"] == "Kiralık"),
    "spot_vehicles": sum(1 for V in vehicles if V["kind"] == "Spot"),
    "chains": sum(1 for V in vehicles if V["stops"] > 1),
    "pickups": sum(V["pickup"] for V in vehicles),
    "total_cost": total_cost,
    "sla_cost": round(sum(L["sla"] for L in legs), 2),
    "desi": round(sum(L["desi"] for L in legs)),
    "km": sum(L["km"] for L in legs),
    "avg_fill": round(statistics.mean(V["fill"] for V in vehicles if V["kind"] == "Spot"), 2),
    "avg_fill_leg": round(statistics.mean(L["fill"] for L in legs if L["kind"] == "Spot"), 2),
}

for L in legs:                                  # set JSON'a yazılamaz
    L.pop("idset", None)
    L.pop("dropdesi", None)

out = {"meta": meta, "centres": centres, "lanes": lanes, "vtypes": vtypes,
       "rented": rented, "legs": legs, "vehicles": vehicles, "daily": daily,
       "loadgrid": loadgrid, "loadgrid_ust": loadgrid_ust,
       "tirgrid": tirgrid, "laneflow": laneflow,
       "forecast": forecast, "history": history, "stages": stages}

DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8")

# ── tutarlılık kapıları ─────────────────────────────────────────────────
assert len(centres) == 18 and len(lanes) == 306
assert sum(l["seen"] for l in lanes) == 289
assert sum(1 for c in centres if c["tir"] == 0) == 7
assert sum(r["n"] for r in rented) == 14 and len(rented) == 12
assert abs(total_cost - stages["stages"]["Stage 3"]["total_cost"]) < 1.0, \
    (total_cost, stages["stages"]["Stage 3"]["total_cost"])
assert meta["vehicles"] == stages["stages"]["Stage 3"]["routes"], \
    (meta["vehicles"], stages["stages"]["Stage 3"]["routes"])

# Yayınlanan planda 0 hakem ihlali var; elleçleme defteri de bunu doğrulamalı.
over = [(centres[c]["n"], d, loadgrid[c][d], centres[c]["hand"])
        for c in range(18) for d in range(ndays)
        if loadgrid[c][d] > centres[c]["hand"] * 1.0005]
assert not over, f"elleçleme kotası aşımı: {over[:5]}"

# Her talep parçası tam olarak bir kez yüklenip bir kez indirilmeli.
tot_load = sum(L["load"] for L in legs)
tot_drop = sum(L["drop"] for L in legs)
assert abs(tot_load - tot_drop) < 1, (tot_load, tot_drop)

print(f"panel ok  {DEST}  {DEST.stat().st_size:,} bayt")
print(f"  {meta['legs']} bacak · {meta['vehicles']} araç "
      f"({meta['rent_vehicles']} kiralık / {meta['spot_vehicles']} spot)")
print(f"  {meta['chains']} zincir · {meta['pickups']} yol-üstü yük alma "
      f"· {meta['total_cost']:,.2f} ₺ · ort. spot doluluk %{meta['avg_fill']}")
peak = max(100 * loadgrid[c][d] / centres[c]["hand"]
           for c in range(18) for d in range(ndays))
print(f"  elleçleme defteri: 0 aşım · tepe kullanım %{peak:.1f} "
      f"· elleçlenen {tot_load:,.0f} desi (yükleme = indirme)")
