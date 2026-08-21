"""Yarışma Excel'lerini tipli, doğrulanmış domain nesnelerine yükler."""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "datas"

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


def _resolve_file(data_dir: Path, filename: str) -> Path:
    """Dosya adını Unicode normalizasyon biçiminden bağımsız çözer.

    Önce birebir dener; bulunamazsa dizindeki adları NFC'ye normalize
    ederek karşılaştırır (NTFS'te NFD kalmış adlar için). Bulunamazsa
    denenen adları listeleyen net bir hata verir.
    """
    p = data_dir / filename
    if p.exists():
        return p
    target = unicodedata.normalize("NFC", filename)
    for cand in data_dir.iterdir():
        if unicodedata.normalize("NFC", cand.name) == target:
            return cand
    raise FileNotFoundError(
        f"{ascii(filename)} bulunamadı ({data_dir}); mevcut dosyalar: "
        + ", ".join(ascii(c.name) for c in data_dir.iterdir()))


def _require_unique(df: pd.DataFrame, columns: list[str], label: str) -> None:
    duplicate_mask = df.duplicated(subset=columns, keep=False)
    if duplicate_mask.any():
        duplicates = df.loc[duplicate_mask, columns].drop_duplicates().to_dict("records")
        raise ValueError(f"Tekrar eden {label}: {duplicates}")


def _validated_numbers(
        values: pd.Series, label: str, *, allow_zero: bool,
        require_integer: bool = False) -> pd.Series:
    numbers = pd.to_numeric(values, errors="coerce")
    invalid_mask = numbers.isna() | ~numbers.map(math.isfinite)
    if invalid_mask.any():
        raise ValueError(f"{label} sayısal ve sonlu olmalı: {values[invalid_mask].tolist()}")
    if allow_zero:
        invalid_sign = numbers < 0
        sign_message = "negatif olamaz"
    else:
        invalid_sign = numbers <= 0
        sign_message = "pozitif olmalı"
    if invalid_sign.any():
        raise ValueError(f"{label} {sign_message}: {values[invalid_sign].tolist()}")
    if require_integer and (numbers % 1 != 0).any():
        raise ValueError(f"{label} tam sayı olmalı: {values[(numbers % 1 != 0)].tolist()}")
    return numbers


def _load_capacity_table(
        data_dir: Path, filename: str, key_column: str, value_column: str,
        label: str, *, allow_zero: bool, require_integer: bool) -> dict:
    df = pd.read_excel(_resolve_file(data_dir, filename))
    _require_unique(df, [key_column], f"{label} kaydı")
    capacities = _validated_numbers(
        df[value_column], label, allow_zero=allow_zero,
        require_integer=require_integer)
    if require_integer:
        capacities = capacities.astype(int)
    else:
        capacities = capacities.astype(float)
    return dict(zip(df[key_column], capacities))


def _load_vehicles(data_dir: Path) -> dict:
    df = pd.read_excel(_resolve_file(data_dir, "Araç_Kapasite_Maliyet_Saat.xlsx"))
    _require_unique(df, ["Araç Adı"], "araç kaydı")
    capacities = _validated_numbers(
        df["Kapasite (desi)"], "Araç kapasitesi", allow_zero=False,
        require_integer=True)
    out = {}
    for (_, r), capacity in zip(df.iterrows(), capacities):
        v = VehicleType(
            name=r["Araç Adı"],
            capacity_desi=int(capacity),
            rental_hourly=float(r["Kiralık Araç Saatlik Kira (TL)"]),
            rental_per_km=float(r["Kiralık Araç Kilometre Başına Maliyet (TL)"]),
            spot_hourly=float(r["Spot Araç Saatlik Kira (TL)"]),
            spot_per_km=float(r["Spot Kilometre Başına Maliyet (TL)"]),
        )
        out[v.name] = v
    if set(out) != set(VEHICLE_NAMES):
        raise ValueError(f"Beklenmeyen araç seti: {set(out)}")
    return out


def _load_lanes(data_dir: Path) -> dict:
    df = pd.read_excel(_resolve_file(data_dir, "sehirler_arasi_lojistik.xlsx"))
    _require_unique(df, ["cikis", "varis"], "hat kaydı")
    lanes = {}
    for _, r in df.iterrows():
        lane = Lane(
            origin=r["cikis"], dest=r["varis"], km=int(r["mesafe_km"]),
            hours={v: float(r[c]) for v, c in _HOUR_COLS.items()},
            sla_days=int(r["hedef_teslim_gun"]),
        )
        lanes[(lane.origin, lane.dest)] = lane
    if len(lanes) != 306:
        raise ValueError(f"306 hat bekleniyordu: {len(lanes)}")
    return lanes


def _load_rentals(data_dir: Path) -> list:
    df = pd.read_excel(_resolve_file(data_dir, "Kiralık_Araclar.xlsx"))
    origin_column = "Çıkış Transfer Merkezi"
    dest_column = "Varış Transfer Merkezi"
    vehicle_column = "Araç Türü"
    _require_unique(
        df, [origin_column, dest_column, vehicle_column], "kiralık araç rotası")
    counts = _validated_numbers(
        df["Araç sayısı"], "Kiralık araç sayısı", allow_zero=False,
        require_integer=True)

    rentals = []
    for (_, r), count in zip(df.iterrows(), counts):
        origin, dest, vehicle = r[origin_column], r[dest_column], r[vehicle_column]
        if not isinstance(origin, str) or not origin.strip():
            raise ValueError(f"Kiralık araç çıkış merkezi geçersiz: {origin!r}")
        if not isinstance(dest, str) or not dest.strip():
            raise ValueError(f"Kiralık araç varış merkezi geçersiz: {dest!r}")
        if origin == dest:
            raise ValueError(f"Kiralık araç rotasının çıkış ve varışı aynı: {origin!r}")
        if vehicle not in VEHICLE_NAMES:
            raise ValueError(f"Kiralık araç türü geçersiz: {vehicle!r}")
        rentals.append(RentalRoute(origin, dest, int(count), vehicle))
    return rentals


def _validate_rental_routes(rentals: list, lanes: dict) -> None:
    missing_routes = sorted({
        (rental.origin, rental.dest)
        for rental in rentals
        if (rental.origin, rental.dest) not in lanes
    })
    if missing_routes:
        raise ValueError(
            f"Kiralık araç rotaları hat matrisinde bulunamadı: {missing_routes}")


def _load_demand(data_dir: Path) -> pd.DataFrame:
    df = pd.read_excel(_resolve_file(data_dir, "teknofest26_gelismis.xlsx"))
    df = df.rename(columns={"talep_tamamlanma_saati": "slot"})
    df["tarih"] = pd.to_datetime(df["tarih"])
    # '9:00' -> '09:00' normalizasyonu
    df["slot"] = df["slot"].astype(str).str.strip().replace({"9:00": "09:00"})
    _require_unique(df, ["talep_id"], "talep kimliği")
    _require_unique(df, ["tarih", "cikis", "varis", "slot"], "talep kaydı")
    slots = set(df["slot"].unique())
    if slots != {"09:00", "17:00"}:
        raise ValueError(f"Beklenmeyen talep saatleri: {sorted(slots)}")
    df["toplam_desi"] = df["toplam_desi"].astype("int64")
    return df[["tarih", "cikis", "varis", "talep_id", "toplam_desi", "slot"]]


def load_all(data_dir: Path = DATA_DIR, *,
             with_demand: bool = True) -> CompetitionData:
    """Statik referans verilerini (ve istenirse geçmiş talebi) yükler.

    ``with_demand=False`` yalnızca *entegrasyon* içindir: final backtest
    çalıştırmasında tahmin modülü çağrılmaz (Bölüm 2), dolayısıyla 66 bin
    satırlık geçmiş talep tablosunun okunması gereksiz çalışma süresi
    harcar. Varsayılan davranış değişmemiştir.
    """
    data_dir = Path(data_dir)
    vehicles = _load_vehicles(data_dir)
    lanes = _load_lanes(data_dir)
    rentals = _load_rentals(data_dir)
    _validate_rental_routes(rentals, lanes)

    handling_cap = _load_capacity_table(
        data_dir, "Ellecleme-kapasite.xlsx", "transfer_merkezi",
        "ellecleme_kapasite", "Elleçleme kapasitesi", allow_zero=False,
        require_integer=False)
    tir_cap = _load_capacity_table(
        data_dir, "tir_kapasiteleri v2.xlsx", "transfer_merkezi",
        "tir_kapasitesi", "Tır kapasitesi", allow_zero=True,
        require_integer=True)

    demand = (_load_demand(data_dir) if with_demand
              else pd.DataFrame(
                  columns=["tarih", "cikis", "varis", "talep_id",
                           "toplam_desi", "slot"]))
    tms = sorted({o for o, _ in lanes} | {d for _, d in lanes})

    if len(tms) != 18:
        raise ValueError(f"18 transfer merkezi bekleniyordu: {len(tms)}")
    if not set(handling_cap) == set(tms) == set(tir_cap):
        raise ValueError(
            "Hat, elleçleme ve tır kapasitesi transfer merkezleri eşleşmiyor")

    return CompetitionData(vehicles=vehicles, lanes=lanes, rentals=rentals,
                           handling_cap=handling_cap, tir_cap=tir_cap,
                           demand=demand, tms=tms)
