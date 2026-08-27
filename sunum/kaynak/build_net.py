#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage-2-step-3/datas/*.xlsx  ->  kaynak/net_data.json

Slayt 3'teki pop-up'ların beslendiği ağ verisi: 18 transfer merkezinin elleçleme
ve tır kapasitesi, 306 yönlü hattın mesafe/SLA'sı ve geçmişte talep görülüp
görülmediği, 12 kiralık rota, 4 araç tipinin kapasite ve maliyeti.

Koordinatlar şehir merkezlerinin enlem/boylamıdır (harita çizimi için);
kalan tüm alanlar şartname veri setlerinden birebir okunur.
"""
import calendar, json, pathlib, statistics, unicodedata
from datetime import date
import openpyxl

HERE = pathlib.Path(__file__).resolve().parent
DATAS = HERE.parents[1] / "stage-2-step-3" / "datas"
PLAN = HERE.parents[1] / "stage-2-step-3" / "out" / "Tasima-plani.xlsx"   # nihai planımız
OUT = HERE / "net_data.json"

# şehir merkezi enlem/boylam — yalnız harita konumlandırma için
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


def find(fname):
    """Dosya adları diskte NFD (ayrık birleşik işaret) biçiminde; NFC ile eşleştir."""
    want = unicodedata.normalize("NFC", fname)
    for p in DATAS.iterdir():
        if unicodedata.normalize("NFC", p.name) == want:
            return p
    raise FileNotFoundError(f"{fname} bulunamadı: {DATAS}")


def rows(fname, sheet=None):
    path = fname if isinstance(fname, pathlib.Path) else find(fname)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    return [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] is not None]


hand = {r[0]: float(r[1]) for r in rows("Ellecleme-kapasite.xlsx")}
tir = {r[0]: int(r[1]) for r in rows("tir_kapasiteleri v2.xlsx")}
lane_rows = rows("sehirler_arasi_lojistik.xlsx")
rented = [[r[0], r[1], int(r[2]), r[3]] for r in rows("Kiralık_Araclar.xlsx")]
veh = [[r[0], int(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])]
       for r in rows("Araç_Kapasite_Maliyet_Saat.xlsx")]

seen = set()
for r in rows("teknofest26_gelismis.xlsx"):
    seen.add((r[1], r[2]))

names = sorted(hand, key=lambda n: (-hand[n], n))
idx = {n: i for i, n in enumerate(names)}
assert set(names) == set(tir) == set(GEO), "merkez listeleri uyuşmuyor"

centres = [{"n": n, "lat": GEO[n][0], "lon": GEO[n][1],
            "h": round(hand[n]), "t": tir[n]} for n in names]

lanes = [[idx[r[0]], idx[r[1]], int(r[2]), int(r[7]), 1 if (r[0], r[1]) in seen else 0]
         for r in lane_rows]

# ── milk-run örneği: nihai planımızdan gerçek bir 4 duraklı zincir ──────────
CHAIN_VEHICLE = "V0225"
plan = [r for r in rows(PLAN) if r[0] == CHAIN_VEHICLE]
assert plan, f"{CHAIN_VEHICLE} taşıma planında yok"

legs = []                                     # (çıkış, varış, varış tarihi, varış saati) -> desi
for r in plan:
    key = (r[3], r[4], r[7], r[8])
    for leg in legs:
        if leg[0] == key:
            leg[1] += r[10]
            leg[2] += 1
            break
    else:
        legs.append([key, r[10], 1])

fmt = lambda d, t: f"{d[:5]} {t}"             # "30.06.2026","17:36" -> "30.06 17:36"
stops = [{"n": legs[0][0][0], "t": fmt(plan[0][5], plan[0][6]),
          "load": int(legs[0][1]), "drop": 0, "parts": int(legs[0][2])}]
for i, (key, desi, parts) in enumerate(legs):
    nxt = int(legs[i + 1][1]) if i + 1 < len(legs) else 0
    stops.append({"n": key[1], "t": fmt(key[2], key[3]),
                  "load": nxt, "drop": int(desi) - nxt,
                  "parts": int(parts) - (int(legs[i + 1][2]) if i + 1 < len(legs) else 0)})

chain = {"vehicle": CHAIN_VEHICLE, "type": plan[0][2],
         "cap": next(v[1] for v in veh if v[0] == plan[0][2]),
         "stops": stops}
assert len(stops) == 5 and stops[-1]["load"] == 0, stops

# ── zaman aritmetiği örneği: planımızdan tek bacaklı, tam dolu bir sefer ────
TRIP_VEHICLE = "V0187"
tr = [r for r in rows(PLAN) if r[0] == TRIP_VEHICLE]
assert len(tr) == 1, f"{TRIP_VEHICLE} tek satırlık bir sefer değil"
tr = tr[0]
lane = next(r for r in lane_rows if r[0] == tr[3] and r[1] == tr[4])
vt = next(v for v in veh if v[0] == tr[2])
trip = {"v": tr[0], "type": tr[2], "from": tr[3], "to": tr[4],
        "desi": int(tr[10]), "cap": vt[1], "km": int(lane[2]), "sla": int(lane[7]),
        "hload": int(tr[13]), "travel": int(tr[11]), "hunload": int(tr[12]),
        "dep": tr[6], "arr": tr[8], "rate_h": vt[4], "rate_km": vt[5],
        "cost": round(float(tr[15]), 2)}
use = trip["hload"] + trip["travel"] + trip["hunload"]
calc = use / 60 * trip["rate_h"] + trip["km"] * trip["rate_km"]
assert abs(calc - trip["cost"]) < 0.01, (calc, trip["cost"])   # plandaki maliyetle birebir
assert trip["desi"] == trip["cap"], "örnek sefer tam dolu değil"
trip["use"] = use

# ── plandaki tüm bacakların çıkış saati dağılımı (dakika çözünürlüğü kanıtı) ─
legs = {}
for r in rows(PLAN):
    legs[(r[0], r[3], r[4], r[5], r[6])] = r[6]
hours = [0] * 24
mins = [0] * 60
for t in legs.values():
    h, m = t.split(":")
    hours[int(h)] += 1
    mins[int(m)] += 1
clock = {"legs": len(legs), "hours": hours, "mins": mins,
         "night": sum(hours[:6]), "on_hour": mins[0]}

# ── günlük toplam desi + dışlanan 23 tarih (slayt 5 pop-up'ları) ───────────
daily = {}
for r in rows("teknofest26_gelismis.xlsx"):
    d = r[0].date()
    daily[d] = daily.get(d, 0.0) + r[4]

HOLIDAYS = {                                  # src/backtest.py ile birebir aynı liste
    date(2026, 1, 1): "Yılbaşı",
    date(2026, 3, 19): "Ramazan arifesi",
    date(2026, 3, 20): "Ramazan B. 1. gün",
    date(2026, 3, 21): "Ramazan B. 2. gün",
    date(2026, 3, 22): "Ramazan B. 3. gün",
    date(2026, 4, 23): "Ulusal Egemenlik",
    date(2026, 5, 1): "Emek ve Dayanışma",
    date(2026, 5, 19): "Gençlik ve Spor B.",
    date(2026, 5, 25): "Kurban öncesi",
    date(2026, 5, 26): "Kurban arifesi",
    date(2026, 5, 27): "Kurban B. 1. gün",
    date(2026, 5, 28): "Kurban B. 2. gün",
    date(2026, 5, 29): "Kurban B. 3. gün",
    date(2026, 5, 30): "Kurban B. 4. gün",
    date(2026, 5, 31): "Kurban sonrası",
}
MONTH_ENDS = set()
for m in range(1, 6):                         # yalnız Ocak–Mayıs; Haziran tahmin ufkunda
    last = calendar.monthrange(2026, m)[1]
    MONTH_ENDS |= {date(2026, m, last), date(2026, m, last - 1)}
EXCLUDED = set(HOLIDAYS) | MONTH_ENDS

median_normal = statistics.median(v for d, v in daily.items() if d not in EXCLUDED)
TR_AY = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz"}
excluded = [{"d": f"{d.day:02d} {TR_AY[d.month]}", "iso": d.isoformat(),
             "v": round(daily.get(d, 0.0)),
             "r": round(daily.get(d, 0.0) / median_normal, 4),
             "me": d in MONTH_ENDS, "h": HOLIDAYS.get(d, "")}
            for d in sorted(EXCLUDED)]
assert len(excluded) == 23, len(excluded)

first = min(daily)
cal = {"start": first.isoformat(), "dow0": first.weekday(),
       "median": round(median_normal),
       "days": [round(daily[d]) for d in sorted(daily)],
       "flag": [(2 if d in MONTH_ENDS else 1) if d in EXCLUDED else 0
                for d in sorted(daily)]}

net = {"centres": centres, "lanes": lanes, "rented": rented,
       "vehicles": veh, "chain": chain, "trip": trip, "clock": clock,
       "excluded": excluded, "cal": cal}

assert len(centres) == 18, len(centres)
assert len(lanes) == 306, len(lanes)
assert sum(l[4] for l in lanes) == 289, sum(l[4] for l in lanes)
assert sum(1 for c in centres if c["t"] == 0) == 7
assert sum(r[2] for r in rented) == 14 and len(rented) == 12

OUT.write_text(json.dumps(net, ensure_ascii=False, separators=(",", ":")),
               encoding="utf-8")
print(f"net ok  {OUT}  {OUT.stat().st_size} bayt  ·  "
      f"{len(centres)} merkez · {len(lanes)} hat · {sum(l[4] for l in lanes)} talep görülen")
