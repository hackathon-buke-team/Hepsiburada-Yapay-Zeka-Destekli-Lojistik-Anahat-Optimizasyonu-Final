#!/usr/bin/env python3
"""Üretilen taşıma planını bağımsız olarak denetler (teslim öncesi kontrol).

``main.py`` çıktısını diskten geri okur ve iki şeyi doğrular:

1. **Bölüm 5 şeması** — tek sayfa, 16 kolon, ad ve sıra birebir.
2. **Hakem simülasyonu** — ``src.simulator.simulate`` planı girdi talep
   tablosuna karşı yeniden fiyatlandırır; kapasite, SLA, kiralık filo,
   tır ziyaret ve rota sürekliliği kuralları yeniden denetlenir.

Değerlendirme çalıştırmasının parçası DEĞİLDİR; ``main.py`` bu dosyayı
kullanmaz.

    python tools/verify_output.py
    python tools/verify_output.py --plan out/Tasima-plani.xlsx \\
        --input data/one_week_backtest.xlsx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contract import (OUTPUT_DIR, OUTPUT_FILENAME, read_demand_table,  # noqa: E402
                          resolve_input_path)
from src.data import load_all  # noqa: E402
from src.schemas import PLAN_COLS  # noqa: E402
from src.simulator import simulate  # noqa: E402


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path,
                        default=ROOT / OUTPUT_DIR / OUTPUT_FILENAME)
    parser.add_argument("--input", type=Path, default=None)
    args = parser.parse_args()

    plan_path = args.plan
    if not plan_path.is_file():
        print(f"HATA: plan dosyası yok: {plan_path}")
        return 1

    input_path = args.input or resolve_input_path(ROOT)
    data = load_all(ROOT / "datas", with_demand=False)
    demand, id_map, _notes = read_demand_table(input_path, data)

    plan = pd.read_excel(plan_path)
    print(f"Plan   : {plan_path}  ({len(plan)} satır)")
    print(f"Girdi  : {input_path}  ({len(demand)} talep)")

    failures = 0
    if list(plan.columns) != PLAN_COLS:
        print("HATA: kolon şeması birebir değil.")
        print(f"  beklenen: {PLAN_COLS}")
        print(f"  bulunan : {list(plan.columns)}")
        failures += 1
    else:
        print("Şema  : 16 kolon, ad ve sıra birebir  ✔")

    # Hakem, plandaki kimliklerle aynı kimlik uzayını görmelidir: çıktıda
    # girdideki özgün kimlikler yazılıdır, bu yüzden talep tablosu da
    # özgün kimlikleriyle verilir.
    referee_demand = demand.copy()
    referee_demand["Talep ID"] = [
        id_map.get(value, value) for value in referee_demand["Talep ID"]]

    result = simulate(plan, referee_demand, data)
    print(f"Araç maliyeti : {result.vehicle_cost:>16,.2f} TL")
    print(f"SLA cezası    : {result.sla_penalty:>16,.2f} TL")
    print(f"TOPLAM        : {result.total_cost:>16,.2f} TL")
    declared = float(pd.to_numeric(plan["Toplam maliyet"]).sum())
    print(f"Beyan toplamı : {declared:>16,.2f} TL "
          f"(fark {abs(declared - result.total_cost):.4f} TL)")

    if result.violations:
        failures += 1
        print(f"HATA: {len(result.violations)} hakem ihlali:")
        for violation in result.violations[:25]:
            print(f"  - {violation}")
        if len(result.violations) > 25:
            print(f"  ... (+{len(result.violations) - 25})")
    else:
        print("Hakem : 0 ihlal  ✔")

    if abs(declared - result.total_cost) > 0.01:
        failures += 1
        print("HATA: beyan edilen toplam maliyet hakemle uzlaşmıyor.")

    print("SONUÇ : " + ("BAŞARILI" if failures == 0 else "BAŞARISIZ"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
