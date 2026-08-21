"""Bütün README grafiklerinin beslendiği tek veri çıkarım adımı.

Boru hattını bir kez kurar, ölçümleri ``docs/figures/chart_data.json`` dosyasına
yazar. Grafik çizen kod bu JSON'dan okur; böylece figürler yeniden üretilebilir
ve çizim kodu ağır hesabı tekrar etmez.

Çalıştırma:  python docs/figures/extract_chart_data.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd

from src.backtest import EXCLUDE_2026, build_grid, dow_median, naive_lastweek, wmape
from src.chain import physical_routes
from src.data import load_all
from src.forecast import (calendar_multipliers, forecast_horizon,
                          to_forecast_frame)
from src.milkrun import MAX_CHAIN_STOPS, run_milk_run_stage
from src.optimize import build_plan, prepare_frame
from src.pickup import run_pickup_stage
from src.repair import run_same_lane_stage

HORIZON_START = date(2026, 6, 29)
HORIZON_END = date(2026, 7, 5)
OUT = Path(__file__).resolve().parent / "chart_data.json"


def _spot_fills(legs, data) -> list[float]:
    """Fiziksel Spot rotalarının doluluk oranları (ağırlıksız)."""
    return [
        float(Fraction(Decimal(str(route[0].desi)))
              / data.vehicles[route[0].vtype].capacity_desi)
        for route in physical_routes(legs)
        if route[0].kind == "Spot"
    ]


def _stage_block(legs, data) -> dict:
    routes = physical_routes(legs)
    fills = _spot_fills(legs, data)
    return {
        "segments": len(legs),
        "routes": len(routes),
        "rented_routes": sum(r[0].kind == "Kiralık" for r in routes),
        "spot_routes": sum(r[0].kind == "Spot" for r in routes),
        "vehicle_mix": dict(sorted(Counter(r[0].vtype for r in routes).items())),
        "chain_size_counts": dict(sorted(Counter(len(r) for r in routes).items())),
        "spot_fills": fills,
        "spot_below_30": sum(f < 0.30 for f in fills),
    }


def main() -> None:
    data = load_all()
    demand = data.demand
    out: dict = {"meta": {"max_chain_stops": MAX_CHAIN_STOPS}}

    # ---------- 1. Ham veri ve temizleme hunisi ----------
    history_grid = build_grid(
        demand, demand["tarih"].min().date(), demand["tarih"].max().date())
    kept_grid = history_grid[
        ~history_grid["tarih"].dt.date.isin(EXCLUDE_2026)]
    out["cleaning"] = {
        "raw_rows": int(len(demand)),
        "history_days": int(demand["tarih"].nunique()),
        "od_in_history": int(demand[["cikis", "varis"]].drop_duplicates().shape[0]),
        "od_in_lane_matrix": int(len(data.lanes)),
        "transfer_centres": int(len(data.tms)),
        "history_grid_rows": int(len(history_grid)),
        "excluded_dates": int(len(EXCLUDE_2026)),
        "training_grid_rows": int(len(kept_grid)),
        "excluded_grid_rows": int(len(history_grid) - len(kept_grid)),
    }

    # ---------- 2. Geçmiş günlük hacim + ay-sonu vurgusu ----------
    daily = (demand.assign(_day=demand["tarih"].dt.date)
             .groupby("_day", as_index=False)["toplam_desi"].sum()
             .rename(columns={"_day": "day", "toplam_desi": "desi"}))
    month_end_days = {d for d in daily["day"]
                      if (d + timedelta(days=1)).day == 1}
    out["history_daily"] = {
        "days": [str(d) for d in daily["day"]],
        "desi": [int(v) for v in daily["desi"]],
        "month_end_days": sorted(str(d) for d in month_end_days),
        "holidays": sorted(str(d) for d in EXCLUDE_2026 if d not in month_end_days),
    }

    # ---------- 3. Takvim çarpanları ----------
    out["calendar_multipliers"] = calendar_multipliers(demand)

    # ---------- 4. Tahmin vs aynı-gün geçmiş ortalaması ----------
    forecast_frame = to_forecast_frame(
        forecast_horizon(demand, HORIZON_START, HORIZON_END))
    forecast_frame["_day"] = pd.to_datetime(
        forecast_frame["Tarih"], format="%d.%m.%Y")
    per_day = (forecast_frame.groupby(forecast_frame["_day"].dt.date)
               ["Tahmin Edilen Desi"].sum())

    # Geçmişteki aynı haftagünü ortalaması: takvim etkisi olan günler hariç,
    # yani "sıradan bir salı ne kadar taşır" sorusunun düz cevabı.
    normal_daily = daily[~daily["day"].isin(EXCLUDE_2026)].copy()
    normal_daily["dow"] = pd.to_datetime(normal_daily["day"]).dt.dayofweek
    dow_mean = normal_daily.groupby("dow")["desi"].mean()

    horizon_days = [HORIZON_START + timedelta(days=i)
                    for i in range((HORIZON_END - HORIZON_START).days + 1)]
    out["forecast_vs_dow"] = {
        "days": [str(d) for d in horizon_days],
        "labels": [d.strftime("%d %b") for d in horizon_days],
        "forecast": [int(per_day.get(d, 0)) for d in horizon_days],
        "dow_mean": [float(dow_mean[d.weekday()]) for d in horizon_days],
        "total_forecast": int(forecast_frame["Tahmin Edilen Desi"].sum()),
        "rows": int(len(forecast_frame)),
        "zero_rows": int((forecast_frame["Tahmin Edilen Desi"] == 0).sum()),
    }

    # ---------- 5. Frozen backtest: naive / DOW-medyan / bizim model ----------
    windows = {
        "Normal hafta\n15-21 Haz": (date(2026, 6, 15), date(2026, 6, 21)),
        "Ay sonu haftası\n30 Mar-5 Nis": (date(2026, 3, 30), date(2026, 4, 5)),
    }
    ods = demand[["cikis", "varis"]].drop_duplicates()
    backtest = {}
    keys = ["tarih", "cikis", "varis", "slot"]
    for label, (w_start, w_end) in windows.items():
        train = demand[demand["tarih"] < pd.Timestamp(w_start)]
        # Tek bir hedef çerçeve; her model AYNI satır sırasına karşı hesaplanır.
        actual = (build_grid(demand, w_start, w_end, ods=ods)
                  .sort_values(keys, kind="mergesort").reset_index(drop=True))
        naive = naive_lastweek(train, actual)
        base = dow_median(train, actual, k=4)
        # Bizim model kendi sıralamasını döndürür; pozisyona güvenmeyip
        # anahtarlar üzerinden geri birleştiriyoruz.
        ours = forecast_horizon(train, w_start, w_end, ods=ods)
        merged = actual.merge(ours[keys + ["forecast"]], on=keys, how="left")
        if merged["forecast"].isna().any():
            raise ValueError(f"{label}: tahmin gridi hedef gridi kapsamıyor")
        backtest[label] = {
            "naive": wmape(actual["desi"], naive),
            "dow_median": wmape(actual["desi"], base),
            "ours": wmape(actual["desi"], merged["forecast"]),
        }
    out["backtest"] = backtest

    # ---------- 6. Üç aşamanın planları ----------
    days = [HORIZON_START + timedelta(days=i)
            for i in range((HORIZON_END - HORIZON_START).days + 1)]
    source = build_plan(data, prepare_frame(forecast_frame.drop(columns="_day")),
                        days)
    stage1 = run_same_lane_stage(source, forecast_frame.drop(columns="_day"), data)
    stage2 = run_milk_run_stage(
        stage1.selected, forecast_frame.drop(columns="_day"), data)
    stage3 = run_pickup_stage(
        stage2.selected, forecast_frame.drop(columns="_day"), data)

    stages = {
        "Stage 0": stage1.baseline,
        "Stage 1": stage1.selected,
        "Stage 2": stage2.selected,
        "Stage 3": stage3.selected,
    }
    out["stages"] = {}
    for label, evaluation in stages.items():
        block = _stage_block(evaluation.legs, data)
        block["vehicle_cost"] = float(evaluation.result.vehicle_cost)
        block["sla_penalty"] = float(evaluation.result.sla_penalty)
        block["total_cost"] = float(evaluation.result.total_cost)
        block["violations"] = len(evaluation.result.violations)
        block["plan_rows"] = int(len(evaluation.plan_frame))
        out["stages"][label] = block

    m = stage2.metrics
    out["milkrun_metrics"] = {
        "groups_considered": m.groups_considered,
        "pairs_evaluated": m.pairs_evaluated,
        "triples_evaluated": m.triples_evaluated,
        "chains_accepted": m.chains_accepted,
        "chain_size_mix": dict(m.chain_size_mix),
        "source_vehicles_replaced": m.source_vehicles_replaced,
        "parts_consolidated": m.parts_consolidated,
        "desi_consolidated": m.desi_consolidated,
        "chain_type_mix": dict(m.chain_type_mix),
        "local_saving_tl": float(m.local_saving_tl),
    }

    p = stage3.metrics
    out["pickup_metrics"] = {
        "routes_considered": p.routes_considered,
        "rented_routes_skipped": p.rented_routes_skipped,
        "donors_available": p.donors_available,
        "pairs_examined": p.pairs_examined,
        "profitable_candidates": p.profitable_candidates,
        "pickups_accepted": p.pickups_accepted,
        "rejected_by_ledger": p.rejected_by_ledger,
        "donor_vehicles_removed": p.donor_vehicles_removed,
        "parts_picked_up": p.parts_picked_up,
        "desi_picked_up": p.desi_picked_up,
        "pickup_type_mix": dict(p.pickup_type_mix),
        "local_saving_tl": float(p.local_saving_tl),
    }

    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
