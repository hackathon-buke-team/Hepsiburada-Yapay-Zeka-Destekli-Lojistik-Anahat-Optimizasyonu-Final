"""Çıktı şablonları (birebir kolonlar) ve format doğrulama.

Formata uymayan çözümler değerlendirmeye ALINMAZ — bu modül son savunma hattı.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date, datetime, time, timedelta

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

# Kanonik talep kimliği ``D00001``; 99.999'dan fazla talep satırı gelirse
# genişlik doğal olarak artar (Bölüm 7 genelleştirilebilirlik).
DEMAND_ID_RE = re.compile(r"^D\d{5,}$")
SPLIT_ID_RE = re.compile(r"^D\d{5,}(-\d+)*$")
VEHICLE_ID_RE = re.compile(r"^V\d{4,}$")
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

FORECAST_CELL_COLS = ["Tarih", "Talep Tamamlama Saati",
                      "Çıkış Transfer Merkezi", "Varış Transfer Merkezi"]
PLAN_NUMERIC_COLS = ["Taşınan Desi", "Yolculuk süresi",
                     "Varış elleçleme süresi", "Çıkış Elleçleme süresi",
                     "SLA cezası", "Toplam maliyet"]
PLAN_LEG_COLS = ["Araç ID", "Çıkış Transfer Merkezi",
                 "Varış Transfer Merkezi", "Çıkış Tarihi", "Çıkış Saati"]


def base_demand_id(talep_id: str) -> str:
    return talep_id.split("-")[0]


def _is_empty(v) -> bool:
    return pd.isna(v) or str(v).strip() == ""


def _num(v):
    """Hücre değerini sonlu float'a çevirir; geçersizse None döner."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _valid_date(v) -> bool:
    text = str(v)
    if not DATE_RE.fullmatch(text):
        return False
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        return False
    return True


def _valid_time(v) -> bool:
    text = str(v)
    if not TIME_RE.fullmatch(text):
        return False
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        return False
    return True


def _canonical_forecast_time(value) -> str | None:
    if isinstance(value, time):
        if value.second or value.microsecond:
            return None
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        if value.second or value.microsecond:
            return None
        return value.strftime("%H:%M")

    text = str(value).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if parsed.second == 0:
            return parsed.strftime("%H:%M")
    return None


def _check_cols(df: pd.DataFrame, expected: list) -> list:
    if list(df.columns) != expected:
        return [f"Kolonlar şablonla birebir değil. Beklenen: {expected}, "
                f"bulunan: {list(df.columns)}"]
    return []


def validate_forecast(df: pd.DataFrame, data) -> list:
    errs = _check_cols(df, FORECAST_COLS)
    if errs:
        return errs
    if df.empty:
        return ["Forecast boş olamaz"]

    tms = set(data.tms)
    lanes = set(data.lanes)
    for i, r in df.iterrows():
        if not DEMAND_ID_RE.match(str(r["Talep ID"])):
            errs.append(f"satır {i}: Talep ID formatı geçersiz: {r['Talep ID']}")
        if not _valid_date(r["Tarih"]):
            errs.append(f"satır {i}: Tarih geçerli DD.MM.YYYY değil: {r['Tarih']}")
        slot = _canonical_forecast_time(r["Talep Tamamlama Saati"])
        if slot not in ("09:00", "17:00"):
            errs.append(
                f"satır {i}: Saat 09:00/17:00 değil: "
                f"{r['Talep Tamamlama Saati']}"
            )

        origin = r["Çıkış Transfer Merkezi"]
        dest = r["Varış Transfer Merkezi"]
        if origin not in tms:
            errs.append(f"satır {i}: bilinmeyen çıkış TM: {origin}")
        if dest not in tms:
            errs.append(f"satır {i}: bilinmeyen varış TM: {dest}")
        if origin in tms and dest in tms:
            if origin == dest:
                errs.append(f"satır {i}: çıkış ve varış TM aynı olamaz")
            elif (origin, dest) not in lanes:
                errs.append(f"satır {i}: matriste olmayan hat")

        val = _num(r["Tahmin Edilen Desi"])
        if val is None:
            errs.append(f"satır {i}: Tahmin Edilen Desi sayısal değil veya sonlu değil: "
                        f"{r['Tahmin Edilen Desi']}")
        elif val < 0:
            errs.append(f"satır {i}: negatif desi")
    if df["Talep ID"].duplicated().any():
        errs.append("Talep ID tekrarı var")
    logical_cells = [
        (row["Tarih"],
         _canonical_forecast_time(row["Talep Tamamlama Saati"]),
         row["Çıkış Transfer Merkezi"],
         row["Varış Transfer Merkezi"])
        for _, row in df.iterrows()
    ]
    if len(logical_cells) != len(set(logical_cells)):
        errs.append("Aynı tarih/saat/çıkış/varış forecast hücresi tekrarı var")
    return errs


def _grid_date(value, label: str) -> tuple[date | None, str | None]:
    if not isinstance(value, date) or pd.isna(value):
        return None, f"{label} gerçek bir date/datetime olmalı: {value!r}"
    if isinstance(value, datetime):
        return value.date(), None
    return value, None


def _grid_ods(ods, data) -> tuple[set[tuple], list]:
    if ods is None:
        ods = data.demand[["cikis", "varis"]]

    if isinstance(ods, pd.DataFrame):
        if {"cikis", "varis"} <= set(ods.columns):
            pairs = ods[["cikis", "varis"]].itertuples(index=False, name=None)
        elif set(FORECAST_CELL_COLS[2:]) <= set(ods.columns):
            pairs = ods[FORECAST_CELL_COLS[2:]].itertuples(index=False, name=None)
        else:
            return set(), [
                "OD tablosu cikis/varis veya Çıkış/Varış Transfer Merkezi "
                "kolonlarını içermeli"
            ]
    else:
        try:
            pairs = iter(ods)
        except TypeError:
            return set(), ["ods, OD çiftlerinden oluşan yinelenebilir bir değer olmalı"]

    result = set()
    for pair in pairs:
        if isinstance(pair, str):
            return set(), [f"Geçersiz OD çifti: {pair!r}"]
        try:
            origin, dest = pair
        except (TypeError, ValueError):
            return set(), [f"Geçersiz OD çifti: {pair!r}"]
        result.add((origin, dest))
    return result, []


def _format_grid_cells(cells: list[tuple], limit: int = 5) -> str:
    ordered = sorted(cells, key=lambda c: (str(c[0]), str(c[1]), c[2], str(c[3])))
    samples = [f"{o}→{d} {day:%d.%m.%Y} {slot}"
               for o, d, day, slot in ordered[:limit]]
    if len(ordered) > limit:
        samples.append("...")
    return ", ".join(samples)


def validate_forecast_grid(df: pd.DataFrame, data, start, end, ods=None) -> list:
    """Forecast'un OD × gün × 09:00/17:00 gridini eksiksiz doğrular."""
    errs = validate_forecast(df, data)
    if list(df.columns) != FORECAST_COLS:
        return errs

    start_date, start_error = _grid_date(start, "start")
    end_date, end_error = _grid_date(end, "end")
    errs.extend(error for error in (start_error, end_error) if error)
    if start_error or end_error:
        return errs
    if start_date > end_date:
        errs.append(
            f"start, end'den sonra olamaz: {start_date} > {end_date}")
        return errs

    od_pairs, od_errors = _grid_ods(ods, data)
    errs.extend(od_errors)
    if od_errors:
        return errs

    days = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    expected = {
        (origin, dest, day, slot)
        for origin, dest in od_pairs
        for day in days
        for slot in ("09:00", "17:00")
    }

    actual = Counter()
    outside = []
    for i, row in df.iterrows():
        try:
            row_date = datetime.strptime(str(row["Tarih"]), "%d.%m.%Y").date()
        except ValueError:
            continue
        slot = _canonical_forecast_time(row["Talep Tamamlama Saati"])
        if slot is None:
            continue
        cell = (row["Çıkış Transfer Merkezi"],
                row["Varış Transfer Merkezi"], row_date, slot)
        actual[cell] += 1
        if not start_date <= row_date <= end_date:
            outside.append((i, cell))

    missing = [cell for cell in expected if actual[cell] == 0]
    extra = []
    for cell, count in actual.items():
        extra.extend([cell] * (count - int(cell in expected)))

    if missing:
        errs.append(
            f"Eksik forecast hücresi: {len(missing)} adet; örnekler: "
            f"{_format_grid_cells(missing)}")
    if extra:
        errs.append(
            f"Fazla forecast hücresi: {len(extra)} adet; örnekler: "
            f"{_format_grid_cells(extra)}")
    if outside:
        samples = [f"satır {i} ({_format_grid_cells([cell])})"
                   for i, cell in outside[:5]]
        if len(outside) > 5:
            samples.append("...")
        errs.append(
            f"Tarih aralığı dışında satır: {len(outside)} adet; örnekler: "
            + ", ".join(samples))
    return errs


def validate_plan(df: pd.DataFrame, data) -> list:
    errs = _check_cols(df, PLAN_COLS)
    if errs:
        return errs
    if df.empty:
        return ["Plan boş olamaz"]

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
            if not _valid_date(r[col]):
                errs.append(f"satır {i}: {col} geçerli DD.MM.YYYY değil: {r[col]}")
        for col in ("Çıkış Saati", "Varış Saati"):
            if not _valid_time(r[col]):
                errs.append(f"satır {i}: {col} geçerli HH:MM değil: {r[col]}")

        is_kiralik_empty = (r["Araç Tipi"] == "Kiralık"
                            and _is_empty(r["Talep ID"]))
        if not is_kiralik_empty and not SPLIT_ID_RE.match(str(r["Talep ID"])):
            errs.append(f"satır {i}: Talep ID formatı geçersiz: {r['Talep ID']}")

        numeric_values = {}
        for col in PLAN_NUMERIC_COLS:
            val = _num(r[col])
            numeric_values[col] = val
            if val is None:
                errs.append(f"satır {i}: {col} sayısal değil veya sonlu değil: {r[col]}")
            elif val < 0:
                errs.append(f"satır {i}: {col} negatif olamaz")

        desi = numeric_values["Taşınan Desi"]
        if desi is not None and desi >= 0:
            if is_kiralik_empty:
                if desi != 0:
                    errs.append(f"satır {i}: boş kiralık bacağında desi 0 olmalı")
            elif desi == 0:
                errs.append(f"satır {i}: Taşınan Desi <= 0 (boş bacak yazılmaz)")

    for leg, group in df.groupby(PLAN_LEG_COLS, sort=False, dropna=False):
        for col in ("Araç Tipi", "Araç türü"):
            if group[col].nunique(dropna=False) > 1:
                errs.append(f"araç+bacak {leg}: {col} tutarsız")
    return errs
