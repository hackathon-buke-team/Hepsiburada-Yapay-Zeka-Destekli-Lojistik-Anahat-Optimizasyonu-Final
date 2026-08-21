# Faz 1: Temel — Veri Katmanı + Hakem Simülatörü + Backtest Altyapısı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Yarışma verilerini tipli yükleyen, tüm yuvarlama/kapasite kurallarını birebir uygulayan bağımsız bir hakem simülatörü ve tahmin backtest altyapısı kurmak.

**Architecture:** Saf-Python çekirdek (pandas yalnız I/O ve backtest gridinde): `data.py` Excel'leri doğrulayarak yükler; `timeutil.py` dakika/saat yuvarlama kurallarını tek yerde toplar; `ledger.py` günlük elleçleme (gece yarısı oransal bölünmeli) ve tır-ziyaret defterlerini tutar; `simulator.py` yalnızca çıktı Excel formatındaki DataFrame'leri okuyup maliyeti/cezayı/ihlalleri sıfırdan hesaplar; `backtest.py` tahmin modelleri için grid + WMAPE altyapısı sağlar.

**Tech Stack:** Python 3.11, pandas ≥2.0, openpyxl, pytest. (OR-Tools/LightGBM bu fazda YOK.)

## Global Constraints

- Çalışma dizini: `C:\Users\darkb\Desktop\hepsiburada-stage2` (git deposu; her task sonunda commit).
- Veri dizini: `datas\` — dosyalar salt-okunur, asla değiştirilmez.
- Elleçleme süresi: 0,01 dk/desi; yükleme ve indirme AYRI birer elleçlemedir.
- Tüm süreler (yol, elleçleme) **en yakın büyük tam dakikaya** yuvarlanır (0,92 saat = 55,2 dk → 56 dk).
- SLA cezası = geciken desi × ⌈gecikme saati⌉ × 0,4 TL; SLA başlangıcı talep tamamlanma anı (09:00/17:00), bitişi NİHAİ varış TM'de elleçleme bitişi; erken/tam zamanında = 0 ceza.
- Araç maliyeti = saatlik ücret × kullanım süresi (ilk yükleme elleçleme başlangıcından son indirme elleçleme bitişine; bekleme dahil) + km ücreti × toplam km.
- Elleçleme ve tır kapasiteleri günlük, 00:00 reset; gece yarısını aşan elleçleme desisi süreye ORANSAL bölünür (23:30'da 10.000 desi → 3.000 o gün / 7.000 ertesi gün).
- Tır kapasitesi yalnız "Tır" tipini sayar (kiralık+spot; gelen+giden); araç HAREKET ETMEDEN boşaltılıp yeniden yüklenirse tek ziyaret = 1 kapasite; gün içinde ikinci geliş yeniden sayılır.
- Kiralık araçlar: her gün kendi hattında tam sayıda çıkar, uğrama/dönüş yapmaz. Boş kiralık bacağı planda `Talep ID = ""` ve `Taşınan Desi = 0` satırıyla gösterilir. Kiralık araçlara gün başına BENZERSİZ `V`-ID verilir (simülatör bacak zincirini araç ID bazında denetler).
- Boş spot bacağı plana yazılmaz (yalnızca yüklü bacaklar).
- Çıktı formatları: `TALEP TAHMİNİ.xlsx` / `TAŞIMA PLANI.xlsx` şablon kolonları birebir; Talep ID `D00001` (+`-1` bölme ekleri), Araç ID `V0001`; tarih `DD.MM.YYYY`, saat `HH:MM`.
- Konsol çıktısı yazan her script UTF-8 wrapper kullanır: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')`.
- Float karşılaştırmalarında tolerans 1e-6; dakika hesaplarında float artefaktına karşı `round(x, 6)` sonrası `ceil`.

---

### Task 1: Repo iskeleti + test altyapısı

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `src/__init__.py`, `tests/__init__.py`

**Interfaces:**
- Consumes: —
- Produces: `pytest` komutu çalışır durumda; `src.*` importları `pythonpath=.` üzerinden çözülür.

- [ ] **Step 1: Dosyaları oluştur**

`requirements.txt`:
```
pandas>=2.0
openpyxl>=3.1
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
pythonpath = .
```

`.gitignore`:
```
__pycache__/
.pytest_cache/
*.pyc
outputs/
.venv/
```

`src/__init__.py` ve `tests/__init__.py`: boş dosyalar.

- [ ] **Step 2: Bağımlılıkları kur ve pytest'i doğrula**

Run: `pip install -r requirements.txt` sonra `python -m pytest`
Expected: `no tests ran` (exit code 5 — normal, henüz test yok)

- [ ] **Step 3: Commit**

```powershell
git add requirements.txt pytest.ini .gitignore src/__init__.py tests/__init__.py
git commit -m "chore: repo iskeleti ve test altyapisi"
```

---

### Task 2: timeutil — yuvarlama kuralları (PDF örnekleri birebir test)

**Files:**
- Create: `src/timeutil.py`
- Test: `tests/test_timeutil.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `travel_minutes(hours: float) -> int` — yol saatini yukarı-tam-dakikaya çevirir
  - `handling_minutes(desi: float) -> int` — desi×0,01 dk, yukarı-tam-dakika; `desi<=0 → 0`
  - `late_hours(deadline: datetime, completion: datetime) -> int` — ⌈gecikme saati⌉, gecikme yoksa 0
  - `parse_dt(tarih: str, saat: str) -> datetime` — `"29.06.2026","10:00"` → datetime
  - `fmt_date(dt: datetime) -> str` (`DD.MM.YYYY`), `fmt_time(dt: datetime) -> str` (`HH:MM`)
  - Sabitler: `HANDLING_MIN_PER_DESI = 0.01`, `SLA_TL_PER_DESI_HOUR = 0.4`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_timeutil.py`:
```python
from datetime import datetime
from src.timeutil import (travel_minutes, handling_minutes, late_hours,
                          parse_dt, fmt_date, fmt_time)


# --- PDF'lerdeki işlenmiş örnekler ---

def test_travel_rounding_pdf_example():
    # İstanbul->Yalova 0,92 saat = 55,2 dk -> 56 (son-gelen-message madde 4)
    assert travel_minutes(0.92) == 56

def test_handling_pdf_examples():
    assert handling_minutes(5000) == 50     # şartname örneği
    assert handling_minutes(10000) == 100   # Q&A kullanım süresi örneği
    assert handling_minutes(22400) == 224   # dolu tır

def test_late_hours_pdf_examples():
    d = datetime(2026, 7, 8, 9, 0)
    assert late_hours(d, datetime(2026, 7, 8, 10, 0)) == 1    # tam 1 saat
    assert late_hours(d, datetime(2026, 7, 8, 11, 20)) == 3   # 2s20d -> 3
    assert late_hours(d, datetime(2026, 7, 8, 9, 1)) == 1     # 1 dk -> 1 saat
    assert late_hours(d, datetime(2026, 7, 8, 9, 0)) == 0     # tam zamanında
    assert late_hours(d, datetime(2026, 7, 8, 8, 0)) == 0     # erken

# --- kenar durumlar ---

def test_travel_exact_minute_not_rounded_up():
    assert travel_minutes(1.0) == 60
    assert travel_minutes(23.82) == 1430   # 1429,2 -> 1430 (Tekirdağ-Mardin)

def test_handling_fractional_and_zero():
    assert handling_minutes(31) == 1       # 0,31 dk -> 1
    assert handling_minutes(150) == 2      # 1,5 dk -> 2
    assert handling_minutes(100) == 1      # tam 1 dk
    assert handling_minutes(0) == 0

def test_float_artifact_guard():
    # 4.6*60 = 275.99999... olabilir; 276 kalmalı, 277'ye taşmamalı
    assert travel_minutes(4.6) == 276

def test_datetime_helpers_roundtrip():
    dt = parse_dt("29.06.2026", "09:05")
    assert dt == datetime(2026, 6, 29, 9, 5)
    assert fmt_date(dt) == "29.06.2026"
    assert fmt_time(dt) == "09:05"
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_timeutil.py -v`
Expected: `ModuleNotFoundError: No module named 'src.timeutil'`

- [ ] **Step 3: Implementasyon**

`src/timeutil.py`:
```python
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
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_timeutil.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```powershell
git add src/timeutil.py tests/test_timeutil.py
git commit -m "feat: yuvarlama/zaman kurallari (PDF ornekleri birebir test)"
```

---

### Task 3: data.py — Excel yükleyiciler + şema doğrulama

**Files:**
- Create: `src/data.py`
- Test: `tests/test_data.py`

**Interfaces:**
- Consumes: `datas\*.xlsx`
- Produces:
  - `VehicleType(name, capacity_desi: int, rental_hourly: float, rental_per_km: float, spot_hourly: float, spot_per_km: float)` (frozen dataclass)
  - `Lane(origin, dest, km: int, hours: dict[str, float], sla_days: int)` (frozen dataclass; `hours` anahtarı araç adı)
  - `RentalRoute(origin, dest, count: int, vehicle: str)` (frozen dataclass)
  - `CompetitionData(vehicles: dict[str, VehicleType], lanes: dict[tuple[str, str], Lane], rentals: list[RentalRoute], handling_cap: dict[str, float], tir_cap: dict[str, int], demand: pd.DataFrame, tms: list[str])`
  - `demand` kolonları: `tarih` (datetime64), `cikis`, `varis`, `talep_id`, `toplam_desi` (int64), `slot` (`'09:00'`/`'17:00'`)
  - `load_all(data_dir: Path = DATA_DIR) -> CompetitionData`
  - `DATA_DIR = Path(r"C:\Users\darkb\Desktop\hepsiburada-stage2\datas")`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_data.py`:
```python
import pytest
from src.data import load_all, DATA_DIR


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def test_vehicles(data):
    assert set(data.vehicles) == {"Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"}
    tir = data.vehicles["Tır"]
    assert tir.capacity_desi == 22400
    assert tir.spot_per_km == 25
    assert abs(tir.spot_hourly - 487.5) < 1e-6
    assert data.vehicles["Kamyonet"].capacity_desi == 5600


def test_lanes(data):
    assert len(data.lanes) == 306  # 18*17 tam yönlü graf
    ist_yal = data.lanes[("İstanbul", "Yalova")]
    assert ist_yal.km == 60
    assert abs(ist_yal.hours["Tır"] - 0.92) < 1e-6
    assert ist_yal.sla_days == 1
    assert data.lanes[("Tekirdağ", "Mardin")].sla_days == 2


def test_rentals(data):
    assert len(data.rentals) == 12
    assert sum(r.count for r in data.rentals) == 14
    ist_yalova = [r for r in data.rentals
                  if (r.origin, r.dest) == ("İstanbul", "Yalova")]
    assert len(ist_yalova) == 1 and ist_yalova[0].count == 2
    assert all(r.origin in {"İstanbul", "Kocaeli", "Yalova"} for r in data.rentals)


def test_capacities(data):
    assert len(data.handling_cap) == 18
    assert len(data.tir_cap) == 18
    assert data.tir_cap["Yalova"] == 4
    assert data.tir_cap["Balıkesir"] == 1
    zero_caps = {tm for tm, c in data.tir_cap.items() if c == 0}
    assert zero_caps == {"Kütahya", "Isparta", "Bilecik", "Zonguldak",
                         "Sivas", "Karaman", "Denizli"}


def test_demand(data):
    d = data.demand
    assert len(d) == 66024
    assert set(d["slot"].unique()) == {"09:00", "17:00"}
    assert d["talep_id"].is_unique
    assert "Kocaeli" not in set(d["varis"])          # Kocaeli asla varış değil
    assert d.groupby(["tarih", "cikis", "varis", "slot"]).size().max() == 1
    od_pairs = set(zip(d["cikis"], d["varis"]))
    assert len(od_pairs) == 289
    assert od_pairs <= set(data.lanes)               # her talep çifti matriste var


def test_tms(data):
    assert len(data.tms) == 18
    assert "İstanbul" in data.tms and "Mardin" in data.tms
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_data.py -v`
Expected: `ModuleNotFoundError: No module named 'src.data'`

- [ ] **Step 3: Implementasyon**

`src/data.py`:
```python
"""Yarışma Excel'lerini tipli, doğrulanmış domain nesnelerine yükler."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(r"C:\Users\darkb\Desktop\hepsiburada-stage2\datas")

VEHICLE_NAMES = ["Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"]

_HOUR_COLS = {
    "Tır": "Tir_Suresi_Saat",
    "Kamyon": "Kamyon_Suresi_Saat",
    "Hafif Kamyon": "Hafif_Kamyon_Suresi_Saat",
    "Kamyonet": "Kamyonet_Suresi_Saat",
}


@dataclass(frozen=True)
class VehicleType:
    name: str
    capacity_desi: int
    rental_hourly: float
    rental_per_km: float
    spot_hourly: float
    spot_per_km: float


@dataclass(frozen=True)
class Lane:
    origin: str
    dest: str
    km: int
    hours: dict
    sla_days: int


@dataclass(frozen=True)
class RentalRoute:
    origin: str
    dest: str
    count: int
    vehicle: str


@dataclass
class CompetitionData:
    vehicles: dict
    lanes: dict
    rentals: list
    handling_cap: dict
    tir_cap: dict
    demand: pd.DataFrame
    tms: list


def _load_vehicles(data_dir: Path) -> dict:
    df = pd.read_excel(data_dir / "Araç_Kapasite_Maliyet_Saat.xlsx")
    out = {}
    for _, r in df.iterrows():
        v = VehicleType(
            name=r["Araç Adı"],
            capacity_desi=int(r["Kapasite (desi)"]),
            rental_hourly=float(r["Kiralık Araç Saatlik Kira (TL)"]),
            rental_per_km=float(r["Kiralık Araç Kilometre Başına Maliyet (TL)"]),
            spot_hourly=float(r["Spot Araç Saatlik Kira (TL)"]),
            spot_per_km=float(r["Spot Kilometre Başına Maliyet (TL)"]),
        )
        out[v.name] = v
    assert set(out) == set(VEHICLE_NAMES), f"beklenmeyen araç seti: {set(out)}"
    return out


def _load_lanes(data_dir: Path) -> dict:
    df = pd.read_excel(data_dir / "sehirler_arasi_lojistik.xlsx")
    lanes = {}
    for _, r in df.iterrows():
        lane = Lane(
            origin=r["cikis"], dest=r["varis"], km=int(r["mesafe_km"]),
            hours={v: float(r[c]) for v, c in _HOUR_COLS.items()},
            sla_days=int(r["hedef_teslim_gun"]),
        )
        lanes[(lane.origin, lane.dest)] = lane
    assert len(lanes) == 306, f"306 hat bekleniyordu: {len(lanes)}"
    return lanes


def _load_rentals(data_dir: Path) -> list:
    df = pd.read_excel(data_dir / "Kiralık_Araclar.xlsx")
    return [RentalRoute(r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"],
                        int(r["Araç sayısı"]), r["Araç Türü"])
            for _, r in df.iterrows()]


def _load_demand(data_dir: Path) -> pd.DataFrame:
    df = pd.read_excel(data_dir / "teknofest26_gelismis.xlsx")
    df = df.rename(columns={"talep_tamamlanma_saati": "slot"})
    # '9:00' -> '09:00' normalizasyonu
    df["slot"] = df["slot"].astype(str).str.strip().replace({"9:00": "09:00"})
    assert set(df["slot"].unique()) == {"09:00", "17:00"}, df["slot"].unique()
    df["toplam_desi"] = df["toplam_desi"].astype("int64")
    return df[["tarih", "cikis", "varis", "talep_id", "toplam_desi", "slot"]]


def load_all(data_dir: Path = DATA_DIR) -> CompetitionData:
    vehicles = _load_vehicles(data_dir)
    lanes = _load_lanes(data_dir)
    rentals = _load_rentals(data_dir)

    hc = pd.read_excel(data_dir / "Ellecleme-kapasite.xlsx")
    handling_cap = dict(zip(hc["transfer_merkezi"], hc["ellecleme_kapasite"].astype(float)))

    tc = pd.read_excel(data_dir / "tir_kapasiteleri v2.xlsx")
    tir_cap = dict(zip(tc["transfer_merkezi"], tc["tir_kapasitesi"].astype(int)))

    demand = _load_demand(data_dir)
    tms = sorted({o for o, _ in lanes} | {d for _, d in lanes})

    assert len(tms) == 18
    assert set(handling_cap) == set(tms) == set(tir_cap)
    for tm, cap in handling_cap.items():
        assert cap > 0, f"{tm} elleçleme kapasitesi <= 0"

    return CompetitionData(vehicles=vehicles, lanes=lanes, rentals=rentals,
                           handling_cap=handling_cap, tir_cap=tir_cap,
                           demand=demand, tms=tms)
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_data.py -v`
Expected: 6 passed (birkaç saniye sürer — 2 MB Excel okunuyor)

- [ ] **Step 5: Commit**

```powershell
git add src/data.py tests/test_data.py
git commit -m "feat: veri katmani - dogrulamali Excel yukleyiciler"
```

---

### Task 4: ledger.py — elleçleme ve tır kapasite defterleri

**Files:**
- Create: `src/ledger.py`
- Test: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `src.timeutil.handling_minutes`
- Produces:
  - `HandlingLedger(capacity: dict[str, float])`
    - `.add(tm: str, start: datetime, desi: float) -> datetime` — işlemi kaydeder, bitiş anını döndürür; desiyi günlere dakika-oransal paylaştırır
    - `.used: dict[tuple[str, date], float]`
    - `.violations() -> list[str]`
  - `TirLedger(capacity: dict[str, int])`
    - `.add_event(tm: str, day: date, vehicle_id: str, visit_id: int) -> None` — aynı `(vehicle_id, visit_id)` aynı `(tm, day)`'de bir kez sayılır
    - `.count(tm: str, day: date) -> int`
    - `.violations() -> list[str]`
  - Ziyaret semantiği (simülatör bunu kullanır): araç zincirinde bacak `k`'nın kalkış ziyareti `visit_id=k`, varış ziyareti `visit_id=k+1`. Böylece bacak `k` varışı ile bacak `k+1` kalkışı (aynı TM, hareket yok) AYNI ziyaret sayılır = 1 kapasite.

- [ ] **Step 1: Failing testleri yaz**

`tests/test_ledger.py`:
```python
from datetime import date, datetime
from src.ledger import HandlingLedger, TirLedger


def test_midnight_proportional_split_pdf_example():
    # 29.06 23:30'da 10.000 desi: süre 100 dk -> 30 dk o gün, 70 dk ertesi gün
    # => 3.000 desi 29.06'ya, 7.000 desi 30.06'ya yazılır (son-gelen-message m.5)
    led = HandlingLedger({"İstanbul": 394786.0})
    end = led.add("İstanbul", datetime(2026, 6, 29, 23, 30), 10000)
    assert end == datetime(2026, 6, 30, 1, 10)
    assert abs(led.used[("İstanbul", date(2026, 6, 29))] - 3000) < 1e-6
    assert abs(led.used[("İstanbul", date(2026, 6, 30))] - 7000) < 1e-6


def test_same_day_no_split():
    led = HandlingLedger({"Yalova": 513171.0})
    end = led.add("Yalova", datetime(2026, 6, 29, 10, 0), 5000)
    assert end == datetime(2026, 6, 29, 10, 50)
    assert abs(led.used[("Yalova", date(2026, 6, 29))] - 5000) < 1e-6
    assert ("Yalova", date(2026, 6, 30)) not in led.used


def test_handling_capacity_violation_detected():
    led = HandlingLedger({"Denizli": 36868.0})
    led.add("Denizli", datetime(2026, 6, 29, 8, 0), 30000)
    assert led.violations() == []
    led.add("Denizli", datetime(2026, 6, 29, 12, 0), 10000)
    v = led.violations()
    assert len(v) == 1 and "Denizli" in v[0]


def test_zero_desi_noop():
    led = HandlingLedger({"Mersin": 100.0})
    end = led.add("Mersin", datetime(2026, 6, 29, 8, 0), 0)
    assert end == datetime(2026, 6, 29, 8, 0)
    assert led.used == {}


def test_tir_visit_counted_once_per_visit():
    # Bacak k varışı (visit k+1) + bacak k+1 kalkışı (visit k+1) = TEK ziyaret.
    led = TirLedger({"Eskişehir": 10})
    d = date(2026, 6, 29)
    led.add_event("Eskişehir", d, "V0001", visit_id=1)  # bacak 0 varışı
    led.add_event("Eskişehir", d, "V0001", visit_id=1)  # bacak 1 kalkışı (hareketsiz)
    assert led.count("Eskişehir", d) == 1
    # Gün içinde İKİNCİ ziyaret (araç gidip geri geldi) ayrıca sayılır
    led.add_event("Eskişehir", d, "V0001", visit_id=3)
    assert led.count("Eskişehir", d) == 2


def test_tir_capacity_violation():
    led = TirLedger({"Balıkesir": 1})
    d = date(2026, 6, 29)
    led.add_event("Balıkesir", d, "V0001", 1)
    assert led.violations() == []
    led.add_event("Balıkesir", d, "V0002", 1)
    v = led.violations()
    assert len(v) == 1 and "Balıkesir" in v[0]
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_ledger.py -v`
Expected: `ModuleNotFoundError: No module named 'src.ledger'`

- [ ] **Step 3: Implementasyon**

`src/ledger.py`:
```python
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

    def violations(self) -> list:
        return [
            f"Elleçleme kapasitesi aşıldı: {tm} {d}: {used:.1f} > {self.capacity[tm]:.1f}"
            for (tm, d), used in sorted(self.used.items())
            if used > self.capacity[tm] + 1e-6
        ]


class TirLedger:
    def __init__(self, capacity: dict):
        self.capacity = capacity
        self._visits = defaultdict(set)

    def add_event(self, tm: str, day: date, vehicle_id: str, visit_id: int) -> None:
        self._visits[(tm, day)].add((vehicle_id, visit_id))

    def count(self, tm: str, day: date) -> int:
        return len(self._visits.get((tm, day), ()))

    def violations(self) -> list:
        return [
            f"Tır kapasitesi aşıldı: {tm} {d}: {len(v)} > {self.capacity[tm]}"
            for (tm, d), v in sorted(self._visits.items())
            if len(v) > self.capacity[tm]
        ]
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_ledger.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```powershell
git add src/ledger.py tests/test_ledger.py
git commit -m "feat: ellecleme (gece yarisi oransal) ve tir ziyaret defterleri"
```

---

### Task 5: schemas.py — çıktı şablonları + format validator

**Files:**
- Create: `src/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: `src.data.CompetitionData` (TM adları, araç adları, hatlar için)
- Produces:
  - `FORECAST_COLS: list[str]` — `["Talep ID", "Tarih", "Talep Tamamlama Saati", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Tahmin Edilen Desi"]`
  - `PLAN_COLS: list[str]` — `["Araç ID", "Araç Tipi", "Araç türü", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Çıkış Tarihi", "Çıkış Saati", "Varış Tarihi", "Varış Saati", "Talep ID", "Taşınan Desi", "Yolculuk süresi", "Varış elleçleme süresi", "Çıkış Elleçleme süresi", "SLA cezası", "Toplam maliyet"]`
  - `DEMAND_ID_RE`, `SPLIT_ID_RE`, `VEHICLE_ID_RE`, `DATE_RE`, `TIME_RE` (derlenmiş regex)
  - `base_demand_id(talep_id: str) -> str` — `"D00001-2-1"` → `"D00001"`
  - `validate_forecast(df: pd.DataFrame, data) -> list[str]` — hata listesi (boş = geçerli)
  - `validate_plan(df: pd.DataFrame, data) -> list[str]` — kural: Spot satırında `Taşınan Desi > 0` ve geçerli Talep ID zorunlu; Kiralık satırında `Talep ID = ""` + `Taşınan Desi = 0` (boş zorunlu sefer) kabul edilir

- [ ] **Step 1: Failing testleri yaz**

`tests/test_schemas.py`:
```python
import pandas as pd
import pytest
from src.data import load_all, DATA_DIR
from src.schemas import (FORECAST_COLS, PLAN_COLS, base_demand_id,
                         validate_forecast, validate_plan)


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _valid_forecast_df():
    return pd.DataFrame([
        {"Talep ID": "D00001", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Yalova", "Tahmin Edilen Desi": 12345.0},
        {"Talep ID": "D00002", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "17:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Yalova", "Tahmin Edilen Desi": 0.0},
    ], columns=FORECAST_COLS)


def _valid_plan_df():
    return pd.DataFrame([
        {"Araç ID": "V0001", "Araç Tipi": "Spot", "Araç türü": "Tır",
         "Çıkış Transfer Merkezi": "İstanbul", "Varış Transfer Merkezi": "Yalova",
         "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",
         "Varış Tarihi": "29.06.2026", "Varış Saati": "11:56",
         "Talep ID": "D00001", "Taşınan Desi": 10000.0,
         "Yolculuk süresi": 56, "Varış elleçleme süresi": 100,
         "Çıkış Elleçleme süresi": 100, "SLA cezası": 0.0,
         "Toplam maliyet": 3580.0},
    ], columns=PLAN_COLS)


def test_base_demand_id():
    assert base_demand_id("D00001") == "D00001"
    assert base_demand_id("D00001-2") == "D00001"
    assert base_demand_id("D00001-2-1") == "D00001"


def test_valid_forecast_passes(data):
    assert validate_forecast(_valid_forecast_df(), data) == []


def test_forecast_bad_id_and_tm(data):
    df = _valid_forecast_df()
    df.loc[0, "Talep ID"] = "X001"                  # kötü ID
    df.loc[1, "Varış Transfer Merkezi"] = "Ankara"  # ağda olmayan TM
    errs = validate_forecast(df, data)
    assert len(errs) == 2


def test_forecast_wrong_columns(data):
    df = _valid_forecast_df().rename(columns={"Tarih": "tarih"})
    errs = validate_forecast(df, data)
    assert errs and "kolon" in errs[0].lower()


def test_valid_plan_passes(data):
    assert validate_plan(_valid_plan_df(), data) == []


def test_plan_bad_rows(data):
    df = _valid_plan_df()
    df.loc[0, "Araç ID"] = "A1"              # kötü araç ID
    errs = validate_plan(df, data)
    assert any("Araç ID" in e for e in errs)

    df2 = _valid_plan_df()
    df2.loc[0, "Araç Tipi"] = "Rental"       # Spot/Kiralık dışı
    df2.loc[0, "Çıkış Saati"] = "9:00"       # HH:MM değil
    errs2 = validate_plan(df2, data)
    assert len(errs2) == 2


def test_plan_split_ids_valid(data):
    df = _valid_plan_df()
    df.loc[0, "Talep ID"] = "D00001-1-2"
    assert validate_plan(df, data) == []


def test_plan_kiralik_empty_leg_allowed(data):
    # Boş çıkması zorunlu kiralık sefer: Talep ID "" + desi 0 kabul edilir
    df = _valid_plan_df()
    df.loc[0, "Araç Tipi"] = "Kiralık"
    df.loc[0, "Talep ID"] = ""
    df.loc[0, "Taşınan Desi"] = 0.0
    assert validate_plan(df, data) == []
    # ...ama Spot'ta boş bacak yazılamaz
    df.loc[0, "Araç Tipi"] = "Spot"
    assert validate_plan(df, data) != []
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'src.schemas'`

- [ ] **Step 3: Implementasyon**

`src/schemas.py`:
```python
"""Çıktı şablonları (birebir kolonlar) ve format doğrulama.

Formata uymayan çözümler değerlendirmeye ALINMAZ — bu modül son savunma hattı.
"""
from __future__ import annotations

import re

import pandas as pd

FORECAST_COLS = ["Talep ID", "Tarih", "Talep Tamamlama Saati",
                 "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                 "Tahmin Edilen Desi"]

PLAN_COLS = ["Araç ID", "Araç Tipi", "Araç türü",
             "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
             "Çıkış Tarihi", "Çıkış Saati", "Varış Tarihi", "Varış Saati",
             "Talep ID", "Taşınan Desi", "Yolculuk süresi",
             "Varış elleçleme süresi", "Çıkış Elleçleme süresi",
             "SLA cezası", "Toplam maliyet"]

DEMAND_ID_RE = re.compile(r"^D\d{5}$")
SPLIT_ID_RE = re.compile(r"^D\d{5}(-\d+)*$")
VEHICLE_ID_RE = re.compile(r"^V\d{4,}$")
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def base_demand_id(talep_id: str) -> str:
    return talep_id.split("-")[0]


def _is_empty(v) -> bool:
    return pd.isna(v) or str(v).strip() == ""


def _check_cols(df: pd.DataFrame, expected: list) -> list:
    if list(df.columns) != expected:
        return [f"Kolonlar şablonla birebir değil. Beklenen: {expected}, "
                f"bulunan: {list(df.columns)}"]
    return []


def validate_forecast(df: pd.DataFrame, data) -> list:
    errs = _check_cols(df, FORECAST_COLS)
    if errs:
        return errs
    tms = set(data.tms)
    for i, r in df.iterrows():
        if not DEMAND_ID_RE.match(str(r["Talep ID"])):
            errs.append(f"satır {i}: Talep ID formatı geçersiz: {r['Talep ID']}")
        if not DATE_RE.match(str(r["Tarih"])):
            errs.append(f"satır {i}: Tarih DD.MM.YYYY değil: {r['Tarih']}")
        if str(r["Talep Tamamlama Saati"]) not in ("09:00", "17:00"):
            errs.append(f"satır {i}: Saat 09:00/17:00 değil: {r['Talep Tamamlama Saati']}")
        if r["Çıkış Transfer Merkezi"] not in tms:
            errs.append(f"satır {i}: bilinmeyen çıkış TM: {r['Çıkış Transfer Merkezi']}")
        if r["Varış Transfer Merkezi"] not in tms:
            errs.append(f"satır {i}: bilinmeyen varış TM: {r['Varış Transfer Merkezi']}")
        if not (float(r["Tahmin Edilen Desi"]) >= 0):
            errs.append(f"satır {i}: negatif desi")
    if df["Talep ID"].duplicated().any():
        errs.append("Talep ID tekrarı var")
    return errs


def validate_plan(df: pd.DataFrame, data) -> list:
    errs = _check_cols(df, PLAN_COLS)
    if errs:
        return errs
    tms = set(data.tms)
    vehicles = set(data.vehicles)
    for i, r in df.iterrows():
        if not VEHICLE_ID_RE.match(str(r["Araç ID"])):
            errs.append(f"satır {i}: Araç ID formatı geçersiz: {r['Araç ID']}")
        if r["Araç Tipi"] not in ("Spot", "Kiralık"):
            errs.append(f"satır {i}: Araç Tipi Spot/Kiralık değil: {r['Araç Tipi']}")
        if r["Araç türü"] not in vehicles:
            errs.append(f"satır {i}: bilinmeyen araç türü: {r['Araç türü']}")
        for col in ("Çıkış Transfer Merkezi", "Varış Transfer Merkezi"):
            if r[col] not in tms:
                errs.append(f"satır {i}: bilinmeyen TM: {r[col]}")
        if (r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"]) not in data.lanes:
            errs.append(f"satır {i}: matriste olmayan hat")
        for col in ("Çıkış Tarihi", "Varış Tarihi"):
            if not DATE_RE.match(str(r[col])):
                errs.append(f"satır {i}: {col} DD.MM.YYYY değil: {r[col]}")
        for col in ("Çıkış Saati", "Varış Saati"):
            if not TIME_RE.match(str(r[col])):
                errs.append(f"satır {i}: {col} HH:MM değil: {r[col]}")
        desi = float(r["Taşınan Desi"])
        if r["Araç Tipi"] == "Kiralık" and _is_empty(r["Talep ID"]):
            if desi != 0:
                errs.append(f"satır {i}: boş kiralık bacağında desi 0 olmalı")
        else:
            if not SPLIT_ID_RE.match(str(r["Talep ID"])):
                errs.append(f"satır {i}: Talep ID formatı geçersiz: {r['Talep ID']}")
            if not desi > 0:
                errs.append(f"satır {i}: Taşınan Desi <= 0 (boş bacak yazılmaz)")
    return errs
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```powershell
git add src/schemas.py tests/test_schemas.py
git commit -m "feat: cikti sablonlari ve format validator"
```

---

### Task 6: simulator.py (1/2) — bacak ayrıştırma, araç zaman çizelgesi, maliyet

**Files:**
- Create: `src/simulator.py`
- Test: `tests/test_simulator_cost.py`

**Interfaces:**
- Consumes: `src.timeutil.*`, `src.data.CompetitionData`
- Produces:
  - `Leg` (dataclass): `vehicle_id: str, kind: str ('Spot'|'Kiralık'), vtype: str, origin: str, dest: str, dep: datetime, items: list[tuple[str, float]]` (talep_id, desi çiftleri; boş kiralık bacağında `items=[]`)
  - `parse_legs(plan_df: pd.DataFrame) -> list[Leg]` — satırları `(Araç ID, Çıkış TM, Varış TM, Çıkış Tarihi, Çıkış Saati)` ile gruplar; boş Talep ID'li satırların items'ı boş kalır
  - `HandlingEvent` (dataclass): `tm: str, start: datetime, end: datetime, desi: float, kind: str ('load'|'unload')`
  - `VehicleTrace` (dataclass): `vehicle_id, kind, vtype, legs: list[Leg]`, `usage_start, usage_end: datetime, usage_hours: float, total_km: int, cost: float`, `events: list[HandlingEvent]`, `leg_times: list[dict|None]` (bacak başına `{"load_start","dep","arr","unload_end","loaded","unloaded"}`; matriste olmayan hat → `None`), `violations: list[str]`
  - `trace_vehicle(legs: list[Leg], data) -> VehicleTrace`. Kurallar:
    - Yükleme elleçlemesi kalkıştan GERİYE: `load_start = dep - handling_minutes(bu bacakta YENİ yüklenen desi)`
    - Varış = kalkış + `travel_minutes(lane.hours[vtype])`
    - Bir sonraki bacakta da aynı (talep_id, desi) ile devam eden yük gemide kalır (ara TM'de elleçleme YOK); inen desi varışta elleçlenir
    - Kullanım = ilk yükleme başlangıcı → son indirme bitişi (beklemeler dahil)
    - Maliyet = saatlik (Spot/Kiralık'a göre) × kullanım saati + km ücreti × Σ km
    - İhlal tespitleri: kapasite aşımı, bacak zinciri kopukluğu (origin ≠ önceki dest), yükleme önceki işlem bitmeden başlıyor

- [ ] **Step 1: Failing testleri yaz**

`tests/test_simulator_cost.py`:
```python
from datetime import datetime, timedelta

import pandas as pd
import pytest
from src.data import load_all, DATA_DIR
from src.schemas import PLAN_COLS
from src.simulator import parse_legs, trace_vehicle
from src.timeutil import travel_minutes


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _row(**kw):
    base = {"Araç ID": "V0001", "Araç Tipi": "Spot", "Araç türü": "Tır",
            "Çıkış Transfer Merkezi": "İstanbul", "Varış Transfer Merkezi": "Yalova",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "11:56",
            "Talep ID": "D00001", "Taşınan Desi": 10000.0,
            "Yolculuk süresi": 56, "Varış elleçleme süresi": 100,
            "Çıkış Elleçleme süresi": 100, "SLA cezası": 0.0,
            "Toplam maliyet": 0.0}
    base.update(kw)
    return base


def test_single_leg_cost_pdf_example(data):
    # Q&A örneği (spot Tır, 10.000 desi): 100 dk yükleme + yol + 100 dk indirme
    # İstanbul->Yalova: 56 dk yol, 60 km => kullanım 256 dk = 4,2667 saat
    # maliyet = 487,5 * 256/60 + 25*60 = 2080 + 1500 = 3580 TL
    plan = pd.DataFrame([_row()], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 1
    tr = trace_vehicle(legs, data)
    assert tr.violations == []
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)   # 11:00 - 100 dk
    assert tr.usage_end == datetime(2026, 6, 29, 13, 36)    # 11:56 + 100 dk
    assert abs(tr.usage_hours - 256 / 60) < 1e-9
    assert tr.total_km == 60
    assert abs(tr.cost - 3580.0) < 0.01


def test_multi_demand_same_leg_single_handling(data):
    # Aynı bacakta 2 talep: elleçleme TOPLAM desi üzerinden tek işlem
    plan = pd.DataFrame([
        _row(**{"Talep ID": "D00001", "Taşınan Desi": 6000.0}),
        _row(**{"Talep ID": "D00002", "Taşınan Desi": 4000.0}),
    ], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 1 and len(legs[0].items) == 2
    tr = trace_vehicle(legs, data)
    assert abs(tr.cost - 3580.0) < 0.01     # 10.000 desi toplam, aynı sonuç


def test_chained_legs_stay_aboard_no_double_handling(data):
    # V0001: İstanbul->Yalova->Eskişehir; D00001 gemide kalıyor (milk-run),
    # D00002 Yalova'da iniyor. Yalova'da D00001 için elleçleme YOK.
    lane2 = data.lanes[("Yalova", "Eskişehir")]
    t2 = travel_minutes(lane2.hours["Tır"])
    dep2 = datetime(2026, 6, 29, 13, 0)
    plan = pd.DataFrame([
        _row(**{"Talep ID": "D00001", "Taşınan Desi": 5000.0}),
        _row(**{"Talep ID": "D00002", "Taşınan Desi": 5000.0}),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "Eskişehir",
                "Çıkış Saati": "13:00", "Varış Saati": "23:59",  # simülatör yeniden hesaplar
                "Talep ID": "D00001", "Taşınan Desi": 5000.0}),
    ], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 2
    tr = trace_vehicle(legs, data)
    assert tr.violations == []
    # Yükleme (10.000 desi, 100 dk) 09:20'de başlar
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)
    # Yalova olayları: yalnız D00002'nin indirilmesi (50 dk, 11:56->12:46)
    yalova_events = [e for e in tr.events if e.tm == "Yalova"]
    assert len(yalova_events) == 1
    assert yalova_events[0].kind == "unload"
    assert abs(yalova_events[0].desi - 5000) < 1e-6
    # 2. bacakta yeni yük yok: load_start == dep; kullanım sonu = varış + 50 dk
    assert tr.leg_times[1]["load_start"] == dep2
    assert tr.usage_end == dep2 + timedelta(minutes=t2 + 50)
    assert tr.total_km == 60 + lane2.km


def test_wait_time_included_in_usage(data):
    # Araç Yalova'da bekleyip ikinci sefer yapıyor; bekleme kullanım süresine dahil
    plan = pd.DataFrame([
        _row(),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "İstanbul",
                "Çıkış Saati": "15:30", "Varış Saati": "16:26",
                "Talep ID": "D00003", "Taşınan Desi": 10000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert tr.violations == []
    # bacak 1: 09:20 yükleme -> 11:56 varış -> 13:36 indirme biter
    # bacak 2: yükleme 13:50 (>= 13:36 OK), kalkış 15:30, varış 16:26, indirme 18:06
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)
    assert tr.usage_end == datetime(2026, 6, 29, 18, 6)
    assert abs(tr.usage_hours - 526 / 60) < 1e-9
    # maliyet: 487,5*526/60 + 25*120 = 4273,75 + 3000 = 7273,75
    assert abs(tr.cost - 7273.75) < 0.01


def test_overlap_load_before_previous_unload_flagged(data):
    # İkinci bacak kalkışı o kadar erken ki yükleme, önceki indirme bitmeden başlıyor
    plan = pd.DataFrame([
        _row(),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "İstanbul",
                "Çıkış Saati": "14:00", "Varış Saati": "14:56",
                "Talep ID": "D00003", "Taşınan Desi": 10000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    # yükleme 12:20 < önceki indirme bitişi 13:36 -> ihlal
    assert any("önceki işlem" in v for v in tr.violations)
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_simulator_cost.py -v`
Expected: `ModuleNotFoundError: No module named 'src.simulator'`

- [ ] **Step 3: Implementasyon**

`src/simulator.py`:
```python
"""Hakem simülatörü (bölüm 1): plan bacaklarını ayrıştırır, araç zaman
çizelgesini ve maliyetini KURAL-BİREBİR yeniden hesaplar.

Kural kaynakları: şartname + Q&A + son-gelen-message. Optimizer'ın iç
durumunu görmez; yalnız çıktı-format DataFrame'leri okur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

from src.timeutil import handling_minutes, parse_dt, travel_minutes


@dataclass
class Leg:
    vehicle_id: str
    kind: str            # 'Spot' | 'Kiralık'
    vtype: str           # 'Tır' | 'Kamyon' | 'Hafif Kamyon' | 'Kamyonet'
    origin: str
    dest: str
    dep: datetime
    items: list          # [(talep_id, desi), ...]; boş kiralık bacağında []


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


def parse_legs(plan_df: pd.DataFrame) -> list:
    legs = []
    group_cols = ["Araç ID", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                  "Çıkış Tarihi", "Çıkış Saati"]
    for (vid, origin, dest, dtarih, dsaat), g in plan_df.groupby(group_cols, sort=False):
        items = [(str(t), float(d))
                 for t, d in zip(g["Talep ID"], g["Taşınan Desi"])
                 if not _is_empty_id(t)]
        legs.append(Leg(
            vehicle_id=vid, kind=g["Araç Tipi"].iloc[0], vtype=g["Araç türü"].iloc[0],
            origin=origin, dest=dest, dep=parse_dt(str(dtarih), str(dsaat)),
            items=items,
        ))
    legs.sort(key=lambda l: (l.vehicle_id, l.dep))
    return legs


def trace_vehicle(legs: list, data) -> VehicleTrace:
    """Tek bir aracın bacak zincirini zaman çizelgesine çevirir."""
    assert legs and all(l.vehicle_id == legs[0].vehicle_id for l in legs)
    legs = sorted(legs, key=lambda l: l.dep)
    tr = VehicleTrace(vehicle_id=legs[0].vehicle_id, kind=legs[0].kind,
                      vtype=legs[0].vtype, legs=legs)
    vt = data.vehicles[tr.vtype]
    hourly = vt.spot_hourly if tr.kind == "Spot" else vt.rental_hourly
    per_km = vt.spot_per_km if tr.kind == "Spot" else vt.rental_per_km

    prev_items = {}          # önceki bacaktan gemide kalanlar {talep_id: desi}
    prev_unload_end = None
    prev_dest = None

    for i, leg in enumerate(legs):
        lane = data.lanes.get((leg.origin, leg.dest))
        if lane is None:
            tr.violations.append(f"{leg.vehicle_id}: matriste olmayan hat "
                                 f"{leg.origin}->{leg.dest}")
            tr.leg_times.append(None)
            continue
        if prev_dest is not None and leg.origin != prev_dest:
            tr.violations.append(f"{leg.vehicle_id}: bacak zinciri kopuk "
                                 f"({prev_dest} -> {leg.origin})")
        cur_items = dict(leg.items)
        if sum(cur_items.values()) > vt.capacity_desi + 1e-6:
            tr.violations.append(
                f"{leg.vehicle_id}: kapasite aşımı "
                f"({sum(cur_items.values()):.0f} > {vt.capacity_desi})")

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
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_simulator_cost.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```powershell
git add src/simulator.py tests/test_simulator_cost.py
git commit -m "feat: simulator bolum 1 - bacak ayristirma, zaman cizelgesi, maliyet"
```

---

### Task 7: simulator.py (2/2) — SLA, kapsama, kiralık kuralları, tam simülasyon

**Files:**
- Modify: `src/simulator.py` (sona ekle)
- Test: `tests/test_simulator_full.py`

**Interfaces:**
- Consumes: Task 6'nın tüm çıktıları + `src.ledger.*` + `src.schemas.base_demand_id`
- Produces:
  - `SimResult` (dataclass): `vehicle_cost: float, sla_penalty: float, total_cost: float, violations: list[str], per_vehicle: pd.DataFrame, per_demand: pd.DataFrame`
  - `simulate(plan_df: pd.DataFrame, forecast_df: pd.DataFrame, data, rental_days: list | None = None) -> SimResult`
    - Tahminden talep kayıtları: hazır anı = `Tarih` + `Talep Tamamlama Saati`; deadline = hazır + `sla_days`×24 saat
    - Talep tamamlanma anı = kronolojik SON indirmenin bitişi; teslim sayılması için son varış TM'si tahminin varış TM'si olmalı
    - Ceza = parça desisi × `late_hours` × 0,4
    - Denetimler: (a) teslim bütünlüğü (bölme toplamı = tahmin desisi, doğru nihai varış), (b) yükleme hazır-anından önce başlamamış (yalnız talebin çıkış TM'sindeki ilk yüklemede), (c) parça rota sürekliliği + araç-değişimli aktarmalarda zamanlama (sonraki yükleme ≥ önceki indirme bitişi; aynı araçta gemide kalanlarda kontrol yok — trace zaten garanti eder), (d) elleçleme/tır kapasiteleri (tır yalnız `Araç türü == 'Tır'`; ziyaret: bacak k kalkış=visit k, varış=visit k+1), (e) kiralık: her kiralık bacak 12 rotadan biriyle eşleşmeli; `rental_days` verilirse her gün × rota için tam `count` çıkış, (f) kiralık araç aynı gün tek bacak, (g) Task 6 trace ihlalleri
  - NOT: `rental_days=None` (varsayılan) günlük kiralık zorunluluğunu denetlemez — birim testler küçük planlarla çalışabilsin diye. Uçtan uca pipeline MUTLAKA `rental_days=[29 Haz..5 Tem]` ile çağırır.

- [ ] **Step 1: Failing testleri yaz**

`tests/test_simulator_full.py`:
```python
from datetime import date

import pandas as pd
import pytest
from src.data import load_all, DATA_DIR
from src.schemas import FORECAST_COLS, PLAN_COLS
from src.simulator import simulate


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _forecast(rows):
    return pd.DataFrame(rows, columns=FORECAST_COLS)


def _plan(rows):
    return pd.DataFrame(rows, columns=PLAN_COLS)


F1 = {"Talep ID": "D00001", "Tarih": "29.06.2026",
      "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
      "Varış Transfer Merkezi": "Yalova", "Tahmin Edilen Desi": 10000.0}

P1 = {"Araç ID": "V0001", "Araç Tipi": "Spot", "Araç türü": "Tır",
      "Çıkış Transfer Merkezi": "İstanbul", "Varış Transfer Merkezi": "Yalova",
      "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",
      "Varış Tarihi": "29.06.2026", "Varış Saati": "11:56",
      "Talep ID": "D00001", "Taşınan Desi": 10000.0,
      "Yolculuk süresi": 56, "Varış elleçleme süresi": 100,
      "Çıkış Elleçleme süresi": 100, "SLA cezası": 0.0, "Toplam maliyet": 3580.0}


def test_on_time_no_penalty(data):
    res = simulate(_plan([P1]), _forecast([F1]), data)
    assert res.violations == []
    assert abs(res.vehicle_cost - 3580.0) < 0.01
    assert res.sla_penalty == 0.0
    assert abs(res.total_cost - 3580.0) < 0.01


def test_sla_penalty_pdf_example(data):
    # 6.000 desi, deadline'ı 56 dk aşan teslim -> 1 saat -> 2.400 TL
    f = dict(F1, **{"Tahmin Edilen Desi": 6000.0})
    p = dict(P1, **{"Taşınan Desi": 6000.0,
                    "Çıkış Tarihi": "30.06.2026", "Çıkış Saati": "08:00",
                    "Varış Tarihi": "30.06.2026", "Varış Saati": "08:56",
                    "Çıkış Elleçleme süresi": 60, "Varış elleçleme süresi": 60})
    # varış 08:56 + 60 dk indirme = 09:56; deadline 30.06 09:00 -> 56 dk geç -> 1 saat
    res = simulate(_plan([p]), _forecast([f]), data)
    assert res.violations == []
    assert abs(res.sla_penalty - 2400.0) < 0.01


def test_split_demand_sums_checked(data):
    p1 = dict(P1, **{"Talep ID": "D00001-1", "Taşınan Desi": 6000.0})
    p2 = dict(P1, **{"Araç ID": "V0002", "Talep ID": "D00001-2",
                     "Taşınan Desi": 4000.0})
    res = simulate(_plan([p1, p2]), _forecast([F1]), data)
    assert res.violations == []
    # eksik bölme yakalanır
    res2 = simulate(_plan([p1]), _forecast([F1]), data)
    assert any("D00001" in v and "desi" in v.lower() for v in res2.violations)


def test_undelivered_demand_flagged(data):
    f2 = dict(F1, **{"Talep ID": "D00002", "Varış Transfer Merkezi": "Manisa"})
    res = simulate(_plan([P1]), _forecast([F1, f2]), data)
    assert any("D00002" in v for v in res.violations)


def test_loading_before_ready_flagged(data):
    # Hazır anı 09:00; kalkış 09:30 => yükleme 07:50'de başlar -> İHLAL
    p = dict(P1, **{"Çıkış Saati": "09:30", "Varış Saati": "10:26"})
    res = simulate(_plan([p]), _forecast([F1]), data)
    assert any("hazır" in v.lower() for v in res.violations)


def test_consolidation_two_vehicles_double_handling(data):
    # İstanbul->Eskişehir talebi Yalova üzerinden 2 araçla (konsolidasyon):
    # Yalova'da indirme (V0001) + yeniden yükleme (V0002) = 2 elleçleme;
    # SLA nihai Eskişehir'de biter.
    f = {"Talep ID": "D00001", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Eskişehir", "Tahmin Edilen Desi": 5000.0}
    leg1 = dict(P1, **{"Taşınan Desi": 5000.0, "Çıkış Saati": "10:00",
                       "Varış Saati": "10:56",
                       "Çıkış Elleçleme süresi": 50, "Varış elleçleme süresi": 50})
    # V0001 indirmesi 10:56+50dk = 11:46'da biter; V0002 yüklemesi 12:40-50dk=11:50 OK
    leg2 = {"Araç ID": "V0002", "Araç Tipi": "Spot", "Araç türü": "Kamyon",
            "Çıkış Transfer Merkezi": "Yalova", "Varış Transfer Merkezi": "Eskişehir",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "12:40",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "23:59",  # yeniden hesaplanır
            "Talep ID": "D00001", "Taşınan Desi": 5000.0,
            "Yolculuk süresi": 0, "Varış elleçleme süresi": 50,
            "Çıkış Elleçleme süresi": 50, "SLA cezası": 0.0, "Toplam maliyet": 0.0}
    res = simulate(_plan([leg1, leg2]), _forecast([f]), data)
    assert res.violations == []
    assert res.sla_penalty == 0.0    # tamamlanma < 30.06 09:00 deadline


def test_consolidation_bad_transfer_timing_flagged(data):
    # V0002, V0001'in indirmesi bitmeden yüklemeye başlıyor -> ihlal
    f = {"Talep ID": "D00001", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Eskişehir", "Tahmin Edilen Desi": 5000.0}
    leg1 = dict(P1, **{"Taşınan Desi": 5000.0, "Çıkış Saati": "10:00",
                       "Varış Saati": "10:56"})
    leg2 = {"Araç ID": "V0002", "Araç Tipi": "Spot", "Araç türü": "Kamyon",
            "Çıkış Transfer Merkezi": "Yalova", "Varış Transfer Merkezi": "Eskişehir",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",  # yükleme 10:10!
            "Varış Tarihi": "29.06.2026", "Varış Saati": "23:59",
            "Talep ID": "D00001", "Taşınan Desi": 5000.0,
            "Yolculuk süresi": 0, "Varış elleçleme süresi": 50,
            "Çıkış Elleçleme süresi": 50, "SLA cezası": 0.0, "Toplam maliyet": 0.0}
    res = simulate(_plan([leg1, leg2]), _forecast([f]), data)
    assert any("aktarma" in v.lower() for v in res.violations)


def test_kiralik_route_and_daily_count(data):
    # Tek kiralık İst->Yalova Tır çıkışı; rota geçerli ama o gün 2 olmalıydı
    # + diğer 11 rota tamamen eksik -> rental_days verilince ihlaller listelenir
    p = dict(P1, **{"Araç Tipi": "Kiralık"})
    res = simulate(_plan([p]), _forecast([F1]), data,
                   rental_days=[date(2026, 6, 29)])
    kiralik_viols = [v for v in res.violations if "Kiralık" in v]
    assert len(kiralik_viols) == 12   # İst->Yalova 1!=2 + 11 eksik rota
    # rental_days verilmezse günlük zorunluluk denetlenmez
    res2 = simulate(_plan([p]), _forecast([F1]), data)
    assert [v for v in res2.violations if "Kiralık" in v] == []


def test_kiralik_off_route_flagged(data):
    # İstanbul->Mardin kiralık rotası yok -> ihlal (rental_days olmasa bile)
    f = dict(F1, **{"Varış Transfer Merkezi": "Mardin"})
    p = dict(P1, **{"Araç Tipi": "Kiralık", "Varış Transfer Merkezi": "Mardin",
                    "Varış Saati": "23:59"})
    res = simulate(_plan([p]), _forecast([f]), data)
    assert any("rota" in v.lower() for v in res.violations)
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_simulator_full.py -v`
Expected: `ImportError: cannot import name 'simulate'`

- [ ] **Step 3: Implementasyon — `src/simulator.py` dosyasının sonuna ekle**

```python
# --- Bölüm 2: tam simülasyon ---
from src.ledger import HandlingLedger, TirLedger
from src.schemas import base_demand_id
from src.timeutil import SLA_TL_PER_DESI_HOUR, late_hours


@dataclass
class SimResult:
    vehicle_cost: float
    sla_penalty: float
    total_cost: float
    violations: list
    per_vehicle: pd.DataFrame
    per_demand: pd.DataFrame


def _forecast_records(forecast_df: pd.DataFrame, data, violations: list) -> dict:
    """talep_id -> dict(ready, origin, dest, desi, deadline)"""
    out = {}
    for _, r in forecast_df.iterrows():
        key = (r["Çıkış Transfer Merkezi"], r["Varış Transfer Merkezi"])
        lane = data.lanes.get(key)
        if lane is None:
            violations.append(f"{r['Talep ID']}: matriste olmayan tahmin hattı {key}")
            continue
        ready = parse_dt(str(r["Tarih"]), str(r["Talep Tamamlama Saati"]))
        out[str(r["Talep ID"])] = {
            "ready": ready,
            "origin": key[0],
            "dest": key[1],
            "desi": float(r["Tahmin Edilen Desi"]),
            "deadline": ready + timedelta(hours=24 * lane.sla_days),
        }
    return out


def simulate(plan_df: pd.DataFrame, forecast_df: pd.DataFrame, data,
             rental_days: list = None) -> SimResult:
    violations = []
    demands = _forecast_records(forecast_df, data, violations)
    legs = parse_legs(plan_df)

    by_vehicle = {}
    for leg in legs:
        by_vehicle.setdefault(leg.vehicle_id, []).append(leg)
    traces = {vid: trace_vehicle(v_legs, data) for vid, v_legs in by_vehicle.items()}

    handling = HandlingLedger(data.handling_cap)
    tir = TirLedger(data.tir_cap)
    part_moves = {}   # talep_id -> [(dep, load_start, unload_end, origin, dest, vid)]
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
                     leg.origin, leg.dest, tr.vehicle_id))
                cur = deliveries.setdefault(base, {}).get(talep_id)
                if cur is None or lt["unload_end"] > cur[1]:
                    deliveries[base][talep_id] = (desi, lt["unload_end"], leg.dest)
                if rec["origin"] == leg.origin and lt["load_start"] < rec["ready"]:
                    violations.append(
                        f"{talep_id}: yükleme talep hazır olmadan başlıyor "
                        f"({lt['load_start']:%d.%m %H:%M} < {rec['ready']:%d.%m %H:%M})")

    # parça rota sürekliliği + araç-değişimli aktarma zamanlaması
    for tid, moves in part_moves.items():
        moves.sort(key=lambda m: m[0])
        for m1, m2 in zip(moves, moves[1:]):
            _, _, ue1, _, d1, v1 = m1
            _, ls2, _, o2, _, v2 = m2
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
    if rental_days is not None:
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
    } for tr in traces.values()])
    return SimResult(
        vehicle_cost=vehicle_cost,
        sla_penalty=sla_penalty,
        total_cost=vehicle_cost + sla_penalty,
        violations=violations,
        per_vehicle=per_vehicle,
        per_demand=pd.DataFrame(demand_rows),
    )
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_simulator_full.py -v`
Expected: 9 passed. Ayrıca tüm suite: `python -m pytest` → önceki testlerle birlikte hepsi geçmeli.

- [ ] **Step 5: Commit**

```powershell
git add src/simulator.py tests/test_simulator_full.py
git commit -m "feat: simulator bolum 2 - SLA, kapsama, kiralik kurallari, defter entegrasyonu"
```

---

### Task 8: backtest.py — tahmin backtest altyapısı + naive/DOW-medyan baseline

**Files:**
- Create: `src/backtest.py`
- Test: `tests/test_backtest.py`

**Interfaces:**
- Consumes: `src.data.CompetitionData.demand`
- Produces:
  - `EXCLUDE_2026: set[date]` — tatiller (1 Oca, 19-22 Mar, 23 Nis, 1 May, 19 May, 25-31 May) + her ayın son 2 günü (Oca-Haz)
  - `build_grid(demand: pd.DataFrame, start: date, end: date) -> pd.DataFrame` — kolonlar `cikis, varis, slot, tarih, desi`; 289 OD × 2 slot × tarih aralığı tam grid, görülmeyen hücre 0
  - `wmape(actual: pd.Series, forecast: pd.Series) -> float` — `sum(|a-f|)/sum(a)`
  - `bias(actual: pd.Series, forecast: pd.Series) -> float` — `sum(f-a)/sum(a)`
  - `naive_lastweek(train: pd.DataFrame, targets: pd.DataFrame) -> pd.Series` — hedef grid satırları için 7 gün önceki değer (yoksa 0)
  - `dow_median(train: pd.DataFrame, targets: pd.DataFrame, k: int = 4, exclude: set = EXCLUDE_2026) -> pd.Series` — hedef tarihten geriye, `exclude` dışındaki son `k` aynı-DOW gözleminin medyanı (griddeki 0'lar dahil)
  - `run_backtest(demand: pd.DataFrame, model_fn, test_start: date, test_end: date) -> dict` — `{"wmape": float, "bias": float}`; `model_fn(train_df, targets_grid) -> pd.Series`

- [ ] **Step 1: Failing testleri yaz**

`tests/test_backtest.py`:
```python
from datetime import date

import pandas as pd
import pytest
from src.backtest import (EXCLUDE_2026, build_grid, wmape, bias,
                          naive_lastweek, dow_median, run_backtest)
from src.data import load_all, DATA_DIR


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def test_exclude_calendar():
    assert date(2026, 5, 27) in EXCLUDE_2026      # Kurban
    assert date(2026, 6, 29) not in EXCLUDE_2026
    assert date(2026, 3, 31) in EXCLUDE_2026      # ay sonu
    assert date(2026, 3, 30) in EXCLUDE_2026      # sondan bir önceki
    assert date(2026, 2, 28) in EXCLUDE_2026      # Şubat sonu (28 gün!)


def test_build_grid_shape_and_zero_fill(data):
    g = build_grid(data.demand, date(2026, 6, 15), date(2026, 6, 28))
    assert len(g) == 289 * 2 * 14
    assert (g["desi"] >= 0).all()
    total_in_window = data.demand[
        (data.demand["tarih"] >= "2026-06-15")
        & (data.demand["tarih"] <= "2026-06-28")]["toplam_desi"].sum()
    assert g["desi"].sum() == total_in_window


def test_metrics():
    a = pd.Series([100.0, 0.0, 50.0])
    f = pd.Series([80.0, 10.0, 50.0])
    assert abs(wmape(a, f) - 30 / 150) < 1e-9
    assert abs(bias(a, f) - (-10) / 150) < 1e-9


def test_backtest_naive_reproduces_eda(data):
    # EDA bulgusu: son 2 haftada naive-geçen-hafta ~%29,7 WMAPE
    r = run_backtest(data.demand, naive_lastweek, date(2026, 6, 15), date(2026, 6, 28))
    assert 0.25 < r["wmape"] < 0.34


def test_backtest_dow_median_beats_naive(data):
    rn = run_backtest(data.demand, naive_lastweek, date(2026, 6, 15), date(2026, 6, 28))
    rm = run_backtest(data.demand,
                      lambda tr, tg: dow_median(tr, tg, k=4),
                      date(2026, 6, 15), date(2026, 6, 28))
    assert rm["wmape"] < rn["wmape"]
    assert abs(rm["bias"]) < 0.10   # bayram-dışlamalı medyan düşük bias'lı
```

- [ ] **Step 2: Testin FAIL ettiğini doğrula**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: `ModuleNotFoundError: No module named 'src.backtest'`

- [ ] **Step 3: Implementasyon**

`src/backtest.py`:
```python
"""Tahmin backtest altyapısı: tam grid, WMAPE/bias, baseline modeller.

Grid kuralı: talep verisinde görünmeyen (tarih, OD, slot) hücresi desi=0
demektir (EDA: her aktif hücre tam 1 satır).
"""
from __future__ import annotations

import calendar
from datetime import date

import pandas as pd

_HOLIDAYS = [
    date(2026, 1, 1),
    date(2026, 3, 19), date(2026, 3, 20), date(2026, 3, 21), date(2026, 3, 22),
    date(2026, 4, 23),
    date(2026, 5, 1),
    date(2026, 5, 19),
    date(2026, 5, 25), date(2026, 5, 26), date(2026, 5, 27), date(2026, 5, 28),
    date(2026, 5, 29), date(2026, 5, 30), date(2026, 5, 31),
]


def _month_ends() -> list:
    out = []
    for m in range(1, 7):
        last = calendar.monthrange(2026, m)[1]
        out += [date(2026, m, last), date(2026, m, last - 1)]
    return out


EXCLUDE_2026 = set(_HOLIDAYS) | set(_month_ends())


def build_grid(demand: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    ods = demand[["cikis", "varis"]].drop_duplicates()
    dates = pd.DataFrame({"tarih": pd.date_range(start, end, freq="D")})
    slots = pd.DataFrame({"slot": ["09:00", "17:00"]})
    grid = ods.merge(dates, how="cross").merge(slots, how="cross")
    actual = demand.groupby(["cikis", "varis", "tarih", "slot"], as_index=False)[
        "toplam_desi"].sum()
    grid = grid.merge(actual, on=["cikis", "varis", "tarih", "slot"], how="left")
    grid["desi"] = grid["toplam_desi"].fillna(0).astype(float)
    return grid.drop(columns=["toplam_desi"])


def wmape(actual: pd.Series, forecast: pd.Series) -> float:
    return float((actual - forecast).abs().sum() / actual.sum())


def bias(actual: pd.Series, forecast: pd.Series) -> float:
    return float((forecast - actual).sum() / actual.sum())


def naive_lastweek(train: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
    hist = build_grid(train, train["tarih"].min().date(), train["tarih"].max().date())
    hist_idx = hist.set_index(["cikis", "varis", "slot", "tarih"])["desi"]
    keys = list(zip(targets["cikis"], targets["varis"], targets["slot"],
                    targets["tarih"] - pd.Timedelta(days=7)))
    return pd.Series([hist_idx.get(k, 0.0) for k in keys], index=targets.index)


def dow_median(train: pd.DataFrame, targets: pd.DataFrame, k: int = 4,
               exclude: set = EXCLUDE_2026) -> pd.Series:
    hist = build_grid(train, train["tarih"].min().date(), train["tarih"].max().date())
    hist = hist[~hist["tarih"].dt.date.isin(exclude)].copy()
    hist["dow"] = hist["tarih"].dt.dayofweek
    hist = hist.sort_values("tarih")
    grouped = {key: g[["tarih", "desi"]].to_numpy()
               for key, g in hist.groupby(["cikis", "varis", "slot", "dow"])}
    out = []
    for _, t in targets.iterrows():
        key = (t["cikis"], t["varis"], t["slot"], t["tarih"].dayofweek)
        arr = grouped.get(key)
        if arr is None:
            out.append(0.0)
            continue
        past = [d for dt_, d in arr if dt_ < t["tarih"]][-k:]
        out.append(float(pd.Series(past).median()) if past else 0.0)
    return pd.Series(out, index=targets.index)


def run_backtest(demand: pd.DataFrame, model_fn, test_start: date,
                 test_end: date) -> dict:
    train = demand[demand["tarih"] < pd.Timestamp(test_start)]
    targets = build_grid(
        demand[(demand["tarih"] >= pd.Timestamp(test_start))
               & (demand["tarih"] <= pd.Timestamp(test_end))],
        test_start, test_end)
    forecast = model_fn(train, targets)
    return {"wmape": wmape(targets["desi"], forecast),
            "bias": bias(targets["desi"], forecast)}
```

- [ ] **Step 4: Testlerin PASS ettiğini doğrula**

Run: `python -m pytest tests/test_backtest.py -v`
Expected: 5 passed (dow_median gerçek veriyle ~1-2 dk sürebilir; kabul)

- [ ] **Step 5: Tüm suite + commit**

Run: `python -m pytest`
Expected: Task 2-8'in tüm testleri geçer (~48 test), hepsi yeşil

```powershell
git add src/backtest.py tests/test_backtest.py
git commit -m "feat: backtest altyapisi - grid, WMAPE, naive ve DOW-medyan baseline"
```

---

## Faz 1 Bitiş Kriterleri

- `python -m pytest` → tümü yeşil; PDF'lerdeki 5 işlenmiş örnek birebir testlerde (0,92s→56dk; 5.000 desi→50dk; kullanım süresi 3580 TL örneği; 6.000 desi→2.400 TL SLA; 23:30→3.000/7.000 oransal bölünme).
- Simülatör el yapımı planları doğru puanlıyor (maliyet + ceza + ihlaller) ve konsolidasyon/aktarma zamanlamasını denetliyor.
- Backtest EDA bulgularını yeniden üretiyor (naive ~%29,7; DOW-medyan daha iyi, |bias|<0,10).
- Sonraki fazlar bu arayüzlerin üstüne kurulur: Faz 2 (tahmin motoru) `backtest.py` ile kalibre edilir; Faz 3 (optimizer) her çözümünü `simulate()` ile puanlar; Faz 6 (export) `schemas.py` validator'ından geçmeden dosya yazmaz.
