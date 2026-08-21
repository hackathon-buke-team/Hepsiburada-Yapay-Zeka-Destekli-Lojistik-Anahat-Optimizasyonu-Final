#!/usr/bin/env python3
"""Bölüm 7 (genelleştirilebilirlik) için sentetik girdi üretici.

Teknik gereksinimler dokümanı, kodun "farklı bir hafta ve farklı bir talep
hacmiyle" ekip tarafından test edilmesini öneriyor. Bu araç tam olarak bunu
üretir: mevcut bir Bölüm 4 talep tablosunu alır, tarihleri kaydırır,
hacmi ölçekler, ufku kısaltır ve istenirse kimlik/saat biçimlerini
değiştirir.

Değerlendirme çalıştırmasının parçası DEĞİLDİR; ``main.py`` bu dosyayı
kullanmaz.

Örnek:

    python tools/make_test_input.py --shift-days 120 --scale 1.6 \\
        --out /tmp/farkli_hafta.xlsx
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.schemas import FORECAST_COLS  # noqa: E402

DEFAULT_SOURCE = ROOT / "data" / "one_week_backtest.xlsx"


def _parse_date(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.strptime(str(value).strip(), "%d.%m.%Y")


def _parse_slot(value) -> str:
    text = unicodedata.normalize("NFC", str(value)).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError(f"Saat çözümlenemedi: {value!r}")


def build(source: Path, *, shift_days: int, scale: float, days: int | None,
          id_prefix: str, time_style: str, keep_zero: bool) -> pd.DataFrame:
    frame = pd.read_excel(source)
    frame.columns = [unicodedata.normalize("NFC", str(c)).strip()
                     for c in frame.columns]
    missing = [c for c in FORECAST_COLS if c not in frame.columns]
    if missing:
        raise SystemExit(f"Kaynak tabloda eksik kolon: {missing}")

    frame = frame.loc[:, FORECAST_COLS].copy()
    dates = frame["Tarih"].map(_parse_date)
    slots = frame["Talep Tamamlama Saati"].map(_parse_slot)

    if days is not None:
        first = dates.min()
        keep = dates < first + timedelta(days=days)
        frame, dates, slots = frame[keep], dates[keep], slots[keep]

    shifted = dates + timedelta(days=shift_days)
    desi = (pd.to_numeric(frame["Tahmin Edilen Desi"], errors="coerce")
            .fillna(0.0) * scale).round().clip(lower=0).astype("int64")

    out = pd.DataFrame({
        "Talep ID": [f"{id_prefix}{i}" for i in range(1, len(frame) + 1)],
        "Tarih": [d.strftime("%d.%m.%Y") for d in shifted],
        "Talep Tamamlama Saati": [
            f"{s}:00" if time_style == "hhmmss" else s for s in slots],
        "Çıkış Transfer Merkezi": frame["Çıkış Transfer Merkezi"].values,
        "Varış Transfer Merkezi": frame["Varış Transfer Merkezi"].values,
        "Tahmin Edilen Desi": desi.values,
    })
    if not keep_zero:
        out = out[out["Tahmin Edilen Desi"] > 0].reset_index(drop=True)
    return out.loc[:, FORECAST_COLS]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shift-days", type=int, default=0,
                        help="Tüm tarihleri bu kadar gün kaydır")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Desi hacmini bu katsayıyla ölçekle")
    parser.add_argument("--days", type=int, default=None,
                        help="Ufku ilk N güne kısalt")
    parser.add_argument("--id-prefix", default="D",
                        help="Talep ID öneki (kanonik olmayan biçimi test "
                             "etmek için ör. 'TALEP-')")
    parser.add_argument("--time-style", choices=("hhmm", "hhmmss"),
                        default="hhmmss")
    parser.add_argument("--keep-zero", action="store_true",
                        help="Sıfır desili satırları koru")
    args = parser.parse_args()

    frame = build(
        args.source, shift_days=args.shift_days, scale=args.scale,
        days=args.days, id_prefix=args.id_prefix,
        time_style=args.time_style, keep_zero=args.keep_zero)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(args.out, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Sheet1")

    span = sorted({d for d in frame["Tarih"]})
    print(f"{args.out}: {len(frame)} satır, "
          f"{int(frame['Tahmin Edilen Desi'].sum()):,} desi, "
          f"{len(span)} farklı tarih")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
