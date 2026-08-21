from datetime import date, datetime, time
from types import SimpleNamespace

import pandas as pd
import pytest
from src.data import load_all, DATA_DIR
from src.schemas import (FORECAST_COLS, PLAN_COLS, base_demand_id,
                         validate_forecast, validate_forecast_grid,
                         validate_plan)


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


def _forecast_grid_df(ods, start, end):
    rows = []
    for day in pd.date_range(start, end):
        for origin, dest in ods:
            for slot in ("09:00", "17:00"):
                rows.append({
                    "Talep ID": f"D{len(rows) + 1:05d}",
                    "Tarih": day.strftime("%d.%m.%Y"),
                    "Talep Tamamlama Saati": slot,
                    "Çıkış Transfer Merkezi": origin,
                    "Varış Transfer Merkezi": dest,
                    "Tahmin Edilen Desi": 0.0,
                })
    return pd.DataFrame(rows, columns=FORECAST_COLS)


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


def test_forecast_accepts_excel_time_cells(data):
    df = _valid_forecast_df()
    df.loc[0, "Talep Tamamlama Saati"] = time(9, 0)
    df.loc[1, "Talep Tamamlama Saati"] = time(17, 0)

    assert validate_forecast(df, data) == []


def test_forecast_rejects_logical_duplicate_across_time_representations(data):
    rows = _valid_forecast_df().iloc[[0]].to_dict("records")
    duplicate = rows[0].copy()
    duplicate["Talep ID"] = "D00002"
    duplicate["Talep Tamamlama Saati"] = time(9, 0)
    df = pd.DataFrame([rows[0], duplicate], columns=FORECAST_COLS)

    errors = validate_forecast(df, data)

    assert any("forecast hücresi tekrarı" in error for error in errors)


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


def test_forecast_grid_uses_historical_active_ods_by_default(data):
    ods = list(data.demand[["cikis", "varis"]].drop_duplicates(
    ).itertuples(index=False, name=None))
    df = _forecast_grid_df(ods, date(2026, 6, 29), date(2026, 6, 29))
    assert validate_forecast_grid(
        df, data, date(2026, 6, 29), datetime(2026, 6, 29, 23, 59)) == []


def test_forecast_grid_reports_missing_extra_and_outside_rows(data):
    ods = [("İstanbul", "Yalova")]
    df = _forecast_grid_df(ods, date(2026, 6, 29), date(2026, 6, 30))
    df = df.iloc[1:].copy()
    outside = df.iloc[[0]].copy()
    outside["Talep ID"] = "D00999"
    outside["Tarih"] = "01.07.2026"
    df = pd.concat([df, outside], ignore_index=True)

    errors = validate_forecast_grid(
        df, data, date(2026, 6, 29), date(2026, 6, 30), ods=ods)

    assert any("Eksik forecast hücresi: 1" in error for error in errors)
    assert any("Fazla forecast hücresi: 1" in error for error in errors)
    assert any("Tarih aralığı dışında satır: 1" in error for error in errors)


def test_forecast_grid_rejects_non_date_boundaries_and_reverse_range(data):
    df = _valid_forecast_df()
    errors = validate_forecast_grid(
        df, data, "29.06.2026", date(2026, 6, 29),
        ods=[("İstanbul", "Yalova")])
    assert any("start gerçek bir date/datetime olmalı" in error
               for error in errors)

    errors = validate_forecast_grid(
        df, data, date(2026, 6, 30), date(2026, 6, 29),
        ods=[("İstanbul", "Yalova")])
    assert any("start, end'den sonra olamaz" in error for error in errors)


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


def test_numeric_garbage_reported_not_crash(data):
    rows = _valid_forecast_df().to_dict("records")
    rows[0]["Tahmin Edilen Desi"] = "onbin"
    df = pd.DataFrame(rows, columns=FORECAST_COLS)
    errs = validate_forecast(df, data)
    assert any("sayısal değil" in e for e in errs)

    prows = _valid_plan_df().to_dict("records")
    prows[0]["Taşınan Desi"] = "çok"
    dfp = pd.DataFrame(prows, columns=PLAN_COLS)
    errs2 = validate_plan(dfp, data)
    assert any("sayısal değil" in e for e in errs2)


@pytest.mark.parametrize("validator, columns, empty_error", [
    (validate_forecast, FORECAST_COLS, "Forecast boş olamaz"),
    (validate_plan, PLAN_COLS, "Plan boş olamaz"),
])
def test_empty_outputs_rejected(data, validator, columns, empty_error):
    assert validator(pd.DataFrame(columns=columns), data) == [empty_error]


def test_forecast_requires_real_calendar_date(data):
    df = _valid_forecast_df()
    df.loc[0, "Tarih"] = "29.02.2025"
    errs = validate_forecast(df, data)
    assert any("geçerli DD.MM.YYYY" in e for e in errs)

    df.loc[0, "Tarih"] = "29.02.2024"
    assert validate_forecast(df, data) == []


def test_plan_requires_real_calendar_dates(data):
    df = _valid_plan_df()
    df.loc[0, "Çıkış Tarihi"] = "31.06.2026"
    df.loc[0, "Varış Tarihi"] = "00.07.2026"
    errs = validate_plan(df, data)
    assert any("Çıkış Tarihi" in e and "geçerli" in e for e in errs)
    assert any("Varış Tarihi" in e and "geçerli" in e for e in errs)


@pytest.mark.parametrize("column, value", [
    ("Çıkış Saati", "24:00"),
    ("Varış Saati", "23:60"),
])
def test_plan_rejects_out_of_range_times(data, column, value):
    df = _valid_plan_df()
    df.loc[0, column] = value
    errs = validate_plan(df, data)
    assert any(column in e and "geçerli HH:MM" in e for e in errs)


def test_plan_accepts_clock_boundaries(data):
    df = _valid_plan_df()
    df.loc[0, "Çıkış Saati"] = "00:00"
    df.loc[0, "Varış Saati"] = "23:59"
    assert validate_plan(df, data) == []


@pytest.mark.parametrize("value", [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="inf"),
    pytest.param(float("-inf"), id="minus-inf"),
])
def test_forecast_rejects_non_finite_desi(data, value):
    df = _valid_forecast_df()
    df.loc[0, "Tahmin Edilen Desi"] = value
    errs = validate_forecast(df, data)
    assert any("Tahmin Edilen Desi" in e and "sonlu değil" in e for e in errs)


def test_forecast_rejects_self_loop(data):
    df = _valid_forecast_df()
    df.loc[0, "Varış Transfer Merkezi"] = "İstanbul"
    errs = validate_forecast(df, data)
    assert any("çıkış ve varış TM aynı" in e for e in errs)


def test_forecast_rejects_lane_missing_from_matrix(data):
    df = _valid_forecast_df().iloc[[0]].copy()
    data_without_lanes = SimpleNamespace(tms=data.tms, lanes={})
    errs = validate_forecast(df, data_without_lanes)
    assert any("matriste olmayan hat" in e for e in errs)


def test_forecast_rejects_duplicate_cell(data):
    df = _valid_forecast_df()
    df.loc[1, "Talep Tamamlama Saati"] = "09:00"
    errs = validate_forecast(df, data)
    assert any("forecast hücresi tekrarı" in e for e in errs)


@pytest.mark.parametrize("column", [
    "Taşınan Desi",
    "Yolculuk süresi",
    "Varış elleçleme süresi",
    "Çıkış Elleçleme süresi",
    "SLA cezası",
    "Toplam maliyet",
])
@pytest.mark.parametrize("value", [
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="inf"),
    pytest.param(float("-inf"), id="minus-inf"),
])
def test_plan_rejects_non_finite_numeric_outputs(data, column, value):
    df = _valid_plan_df()
    df[column] = value
    errs = validate_plan(df, data)
    assert any(column in e and "sonlu değil" in e for e in errs)


@pytest.mark.parametrize("column", [
    "Taşınan Desi",
    "Yolculuk süresi",
    "Varış elleçleme süresi",
    "Çıkış Elleçleme süresi",
    "SLA cezası",
    "Toplam maliyet",
])
def test_plan_rejects_negative_numeric_outputs(data, column):
    df = _valid_plan_df()
    df.loc[0, column] = -1
    errs = validate_plan(df, data)
    assert any(column in e and "negatif olamaz" in e for e in errs)


@pytest.mark.parametrize("column, conflicting_value", [
    ("Araç Tipi", "Kiralık"),
    ("Araç türü", "Kamyon"),
])
def test_plan_requires_vehicle_fields_consistent_within_leg(
        data, column, conflicting_value):
    rows = _valid_plan_df().to_dict("records")
    second = rows[0].copy()
    second["Talep ID"] = "D00002"
    second[column] = conflicting_value
    df = pd.DataFrame([rows[0], second], columns=PLAN_COLS)
    errs = validate_plan(df, data)
    assert any(f"{column} tutarsız" in e for e in errs)
