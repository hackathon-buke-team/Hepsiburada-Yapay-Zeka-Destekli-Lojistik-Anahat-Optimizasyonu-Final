from datetime import date, time
from types import SimpleNamespace

import pandas as pd
import pytest
from src.data import DATA_DIR, Lane, RentalRoute, VehicleType, load_all
from src.export import write_forecast_xlsx
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


def _referee_data(rentals=()):
    one_hour = {"Kamyonet": 1.0}
    return SimpleNamespace(
        vehicles={
            "Kamyonet": VehicleType(
                "Kamyonet", 5600,
                rental_hourly=30.0, rental_per_km=0.5,
                spot_hourly=60.0, spot_per_km=1.0,
            )
        },
        lanes={
            ("A", "B"): Lane("A", "B", 60, dict(one_hour), 1),
            ("B", "C"): Lane("B", "C", 60, dict(one_hour), 1),
            ("A", "C"): Lane("A", "C", 120, dict(one_hour), 1),
        },
        rentals=list(rentals),
        handling_cap={"A": 100_000, "B": 100_000, "C": 100_000},
        tir_cap={"A": 100, "B": 100, "C": 100},
    )


def _pair_forecast():
    return _forecast([
        {
            "Talep ID": "D00001", "Tarih": "29.06.2026",
            "Talep Tamamlama Saati": "09:00",
            "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "B",
            "Tahmin Edilen Desi": 100.0,
        },
        {
            "Talep ID": "D00002", "Tarih": "29.06.2026",
            "Talep Tamamlama Saati": "09:00",
            "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "C",
            "Tahmin Edilen Desi": 200.0,
        },
    ])


def _valid_pair_plan():
    return _plan([
        {
            "Araç ID": "VPAIR", "Araç Tipi": "Spot",
            "Araç türü": "Kamyonet",
            "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "B",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "09:03",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "10:03",
            "Talep ID": "D00001", "Taşınan Desi": 100.0,
            "Yolculuk süresi": 60.0, "Varış elleçleme süresi": 1.0,
            "Çıkış Elleçleme süresi": 1.0, "SLA cezası": 0.0,
            "Toplam maliyet": 82.0,
        },
        {
            "Araç ID": "VPAIR", "Araç Tipi": "Spot",
            "Araç türü": "Kamyonet",
            "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "B",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "09:03",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "10:03",
            "Talep ID": "D00002", "Taşınan Desi": 200.0,
            "Yolculuk süresi": 60.0, "Varış elleçleme süresi": 0.0,
            "Çıkış Elleçleme süresi": 2.0, "SLA cezası": 0.0,
            "Toplam maliyet": 164.0,
        },
        {
            "Araç ID": "VPAIR", "Araç Tipi": "Spot",
            "Araç türü": "Kamyonet",
            "Çıkış Transfer Merkezi": "B", "Varış Transfer Merkezi": "C",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "10:04",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "11:04",
            "Talep ID": "D00002", "Taşınan Desi": 200.0,
            "Yolculuk süresi": 60.0, "Varış elleçleme süresi": 2.0,
            "Çıkış Elleçleme süresi": 0.0, "SLA cezası": 0.0,
            "Toplam maliyet": 0.0,
        },
    ])


def _late_pair_plan():
    plan = _valid_pair_plan()
    plan.at[0, "Toplam maliyet"] = 542.0
    plan.at[1, "Toplam maliyet"] = 1084.0
    plan.at[2, "Çıkış Tarihi"] = "30.06.2026"
    plan.at[2, "Çıkış Saati"] = "09:04"
    plan.at[2, "Varış Tarihi"] = "30.06.2026"
    plan.at[2, "Varış Saati"] = "10:04"
    plan.at[2, "SLA cezası"] = 160.0
    plan.at[2, "Toplam maliyet"] = 160.0
    return plan


def _assert_row_declaration_violation(
        result, column, item_id, segment, departure):
    expected_tokens = (
        "VPAIR", segment, departure, item_id, column, "beyan=", "beklenen=",
    )
    matches = [
        violation for violation in result.violations
        if all(token in violation for token in expected_tokens)
    ]
    assert matches, result.violations


def test_simulator_accepts_valid_pair_declarations():
    result = simulate(
        _valid_pair_plan(), _pair_forecast(), _referee_data(), rental_days=[])

    assert result.violations == []
    assert result.vehicle_cost == 246.0
    assert result.sla_penalty == 0.0
    assert result.total_cost == 246.0


@pytest.mark.parametrize(
    ("row_index", "item_id", "segment", "departure"),
    [
        (0, "D00001", "A->B", "29.06.2026 09:03"),
        (1, "D00002", "A->B", "29.06.2026 09:03"),
        (2, "D00002", "B->C", "29.06.2026 10:04"),
    ],
)
def test_every_row_must_declare_full_matrix_travel(
        row_index, item_id, segment, departure):
    plan = _valid_pair_plan()
    plan.at[row_index, "Yolculuk süresi"] += 1.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "Yolculuk süresi", item_id, segment, departure)


@pytest.mark.parametrize(
    ("column", "item_id"),
    [
        ("Çıkış Elleçleme süresi", "D00001"),
        ("Varış elleçleme süresi", "D00001"),
    ],
)
def test_new_and_unloaded_rows_require_exact_handling_share(column, item_id):
    plan = _valid_pair_plan()
    plan.at[0, column] = 0.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, column, item_id, "A->B", "29.06.2026 09:03")


def test_stay_onboard_rows_require_zero_intermediate_handling():
    plan = _valid_pair_plan()
    plan.at[1, "Varış elleçleme süresi"] = 2.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "Varış elleçleme süresi", "D00002", "A->B",
        "29.06.2026 09:03")


@pytest.mark.parametrize(
    ("column", "value"),
    [("Çıkış Elleçleme süresi", 2.0), ("Varış elleçleme süresi", 0.0)],
)
def test_carried_final_row_has_zero_departure_and_real_arrival_handling(
        column, value):
    plan = _valid_pair_plan()
    plan.at[2, column] = value

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, column, "D00002", "B->C", "29.06.2026 10:04")


def test_sla_must_be_zero_before_final_destination():
    plan = _valid_pair_plan()
    plan.at[1, "SLA cezası"] = 1.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "SLA cezası", "D00002", "A->B", "29.06.2026 09:03")


def test_final_unload_sla_must_match_original_forecast_deadline():
    exact = simulate(
        _late_pair_plan(), _pair_forecast(), _referee_data(), rental_days=[])
    assert exact.violations == []
    assert exact.vehicle_cost == 1626.0
    assert exact.sla_penalty == 160.0

    for declared in (0.0, 160.0000011):
        plan = _late_pair_plan()
        plan.at[2, "SLA cezası"] = declared
        result = simulate(
            plan, _pair_forecast(), _referee_data(), rental_days=[])
        _assert_row_declaration_violation(
            result, "SLA cezası", "D00002", "B->C",
            "30.06.2026 09:04")


def test_vehicle_cost_is_only_on_unique_new_rows():
    plan = _valid_pair_plan()
    plan.at[2, "Toplam maliyet"] = 1.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "Araç maliyeti payı", "D00002", "B->C",
        "29.06.2026 10:04")


def test_vehicle_cost_rows_are_proportional_within_one_cent():
    plan = _valid_pair_plan()
    plan.at[0, "Toplam maliyet"] = 83.0
    plan.at[1, "Toplam maliyet"] = 163.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "Araç maliyeti payı", "D00001", "A->B",
        "29.06.2026 09:03")
    _assert_row_declaration_violation(
        result, "Araç maliyeti payı", "D00002", "A->B",
        "29.06.2026 09:03")


def test_duplicated_chain_cost_is_rejected():
    plan = _valid_pair_plan()
    plan.at[2, "Toplam maliyet"] = 246.0

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    _assert_row_declaration_violation(
        result, "Araç maliyeti payı", "D00002", "B->C",
        "29.06.2026 10:04")
    assert any(
        "VPAIR" in violation
        and "Fiziksel iz araç maliyeti toplamı" in violation
        and "beyan=492.0" in violation
        and "beklenen=246.0" in violation
        for violation in result.violations
    ), result.violations
    assert result.vehicle_cost == 246.0
    assert result.sla_penalty == 0.0
    assert result.total_cost == 246.0


def test_sla_tolerance_boundary_is_inclusive():
    for offset in (-0.000001, 0.000001):
        plan = _late_pair_plan()
        plan.at[2, "SLA cezası"] = 160.0 + offset
        result = simulate(
            plan, _pair_forecast(), _referee_data(), rental_days=[])
        assert result.violations == []

    plan = _late_pair_plan()
    plan.at[2, "SLA cezası"] = 160.0000011
    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])
    _assert_row_declaration_violation(
        result, "SLA cezası", "D00002", "B->C", "30.06.2026 09:04")


def test_vehicle_cost_tolerance_boundary_is_inclusive():
    for offset in (-0.01, 0.01):
        plan = _valid_pair_plan()
        plan.at[0, "Toplam maliyet"] = 82.0 + offset
        result = simulate(
            plan, _pair_forecast(), _referee_data(), rental_days=[])
        assert result.violations == []

    plan = _valid_pair_plan()
    plan.at[0, "Toplam maliyet"] = 82.010001
    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])
    _assert_row_declaration_violation(
        result, "Araç maliyeti payı", "D00001", "A->B",
        "29.06.2026 09:03")
    assert any("Fiziksel iz araç maliyeti toplamı" in v
               for v in result.violations)


def test_physical_vehicle_cost_sum_must_match():
    plan = _valid_pair_plan()
    plan.at[1, "Toplam maliyet"] = 164.010001

    result = simulate(plan, _pair_forecast(), _referee_data(), rental_days=[])

    assert any(
        "VPAIR" in violation
        and "Fiziksel iz araç maliyeti toplamı" in violation
        and "beyan=246.010001" in violation
        and "beklenen=246.0" in violation
        for violation in result.violations
    ), result.violations


def _empty_rental_plan(total_cost=60.0):
    return _plan([{
        "Araç ID": "VEMPTY", "Araç Tipi": "Kiralık",
        "Araç türü": "Kamyonet",
        "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "B",
        "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "09:00",
        "Varış Tarihi": "29.06.2026", "Varış Saati": "10:00",
        "Talep ID": "", "Taşınan Desi": 0.0,
        "Yolculuk süresi": 60.0, "Varış elleçleme süresi": 0.0,
        "Çıkış Elleçleme süresi": 0.0, "SLA cezası": 0.0,
        "Toplam maliyet": total_cost,
    }])


def test_empty_rented_row_owns_full_vehicle_cost():
    data = _referee_data([RentalRoute("A", "B", 1, "Kamyonet")])

    exact = simulate(_empty_rental_plan(), _forecast([]), data, rental_days=[])
    assert exact.violations == []
    assert exact.vehicle_cost == 60.0

    zero = simulate(
        _empty_rental_plan(total_cost=0.0), _forecast([]), data,
        rental_days=[])
    assert any(
        "VEMPTY" in violation
        and "A->B" in violation
        and "29.06.2026 09:00" in violation
        and "talep <boş>" in violation
        and "Araç maliyeti payı" in violation
        and "beyan=0.0" in violation
        and "beklenen=60.0" in violation
        for violation in zero.violations
    ), zero.violations


@pytest.mark.parametrize("failure", ["spot", "missing_route", "two_rows"])
def test_empty_trace_requires_one_matching_rental_declaration(failure):
    rentals = [RentalRoute("A", "B", 1, "Kamyonet")]
    data = _referee_data(rentals)
    plan = _empty_rental_plan()
    if failure == "spot":
        plan.at[0, "Araç Tipi"] = "Spot"
        plan.at[0, "Toplam maliyet"] = 120.0
    elif failure == "missing_route":
        data = _referee_data()
    else:
        second = plan.iloc[[0]].copy()
        plan.at[0, "Toplam maliyet"] = 30.0
        second.at[second.index[0], "Toplam maliyet"] = 30.0
        plan = pd.concat([plan, second], ignore_index=True)

    result = simulate(plan, _forecast([]), data, rental_days=[])

    assert any("Boş fiziksel iz" in violation
               for violation in result.violations), result.violations


def test_missing_forecast_evidence_is_explicit_and_skips_only_sla_comparison():
    forecast = _pair_forecast().iloc[[0]].reset_index(drop=True)

    result = simulate(
        _valid_pair_plan(), forecast, _referee_data(), rental_days=[])

    assert any("D00002: tahmin dosyasında olmayan talep" in violation
               for violation in result.violations)
    assert not any(
        "D00002" in violation and "SLA cezası" in violation
        for violation in result.violations
    )


def test_missing_matrix_evidence_is_explicit_and_skips_only_travel_comparison():
    data = _referee_data()
    del data.lanes[("B", "C")]

    result = simulate(
        _valid_pair_plan(), _pair_forecast(), data, rental_days=[])

    assert any("matriste olmayan hat B->C" in violation
               for violation in result.violations)
    assert not any(
        "B->C" in violation and "Yolculuk süresi" in violation
        for violation in result.violations
    )
    assert not any(
        "Araç maliyeti payı" in violation
        or "Fiziksel iz araç maliyeti toplamı" in violation
        for violation in result.violations
    )


def test_on_time_no_penalty(data):
    res = simulate(_plan([P1]), _forecast([F1]), data, rental_days=[])
    assert res.violations == []
    assert abs(res.vehicle_cost - 3580.0) < 0.01
    assert res.sla_penalty == 0.0
    assert abs(res.total_cost - 3580.0) < 0.01


def test_declared_arrival_must_match_matrix_travel(data):
    wrong = dict(P1, **{"Varış Saati": "12:00"})

    result = simulate(_plan([wrong]), _forecast([F1]), data, rental_days=[])

    assert any("beyan varış" in violation and "matris varışı" in violation
               for violation in result.violations)


def test_same_leg_rows_require_one_declared_arrival(data):
    first = dict(P1, **{"Taşınan Desi": 5000.0,
                        "Varış elleçleme süresi": 50,
                        "Çıkış Elleçleme süresi": 50,
                        "Toplam maliyet": 1790.0})
    second = dict(P1, **{"Talep ID": "D00002",
                         "Taşınan Desi": 5000.0,
                         "Varış Saati": "12:00",
                         "Varış elleçleme süresi": 50,
                         "Çıkış Elleçleme süresi": 50,
                         "Toplam maliyet": 1790.0})

    result = simulate(
        _plan([first, second]),
        _forecast([
            dict(F1, **{"Tahmin Edilen Desi": 5000.0}),
            dict(F1, **{"Talep ID": "D00002",
                        "Tahmin Edilen Desi": 5000.0}),
        ]),
        data,
        rental_days=[],
    )

    assert any("aynı bacak grubunda beyan varış tutarsız" in violation
               for violation in result.violations)


def test_sla_penalty_pdf_example(data):
    # 6.000 desi, deadline'ı 56 dk aşan teslim -> 1 saat -> 2.400 TL
    f = dict(F1, **{"Tahmin Edilen Desi": 6000.0})
    p = dict(P1, **{"Taşınan Desi": 6000.0,
                    "Çıkış Tarihi": "30.06.2026", "Çıkış Saati": "08:00",
                    "Varış Tarihi": "30.06.2026", "Varış Saati": "08:56",
                    "Çıkış Elleçleme süresi": 60, "Varış elleçleme süresi": 60,
                    "SLA cezası": 2400.0, "Toplam maliyet": 5330.0})
    # varış 08:56 + 60 dk indirme = 09:56; deadline 30.06 09:00 -> 56 dk geç -> 1 saat
    res = simulate(_plan([p]), _forecast([f]), data, rental_days=[])
    assert res.violations == []
    assert abs(res.sla_penalty - 2400.0) < 0.01


def test_split_demand_sums_checked(data):
    p1 = dict(P1, **{"Talep ID": "D00001-1", "Taşınan Desi": 6000.0,
                     "Varış elleçleme süresi": 60,
                     "Çıkış Elleçleme süresi": 60,
                     "Toplam maliyet": 2930.0})
    p2 = dict(P1, **{"Araç ID": "V0002", "Talep ID": "D00001-2",
                     "Taşınan Desi": 4000.0,
                     "Varış elleçleme süresi": 40,
                     "Çıkış Elleçleme süresi": 40,
                     "Toplam maliyet": 2605.0})
    res = simulate(_plan([p1, p2]), _forecast([F1]), data, rental_days=[])
    assert res.violations == []
    # eksik bölme yakalanır
    res2 = simulate(_plan([p1]), _forecast([F1]), data, rental_days=[])
    assert any("D00001" in v and "desi" in v.lower() for v in res2.violations)


def test_undelivered_demand_flagged(data):
    f2 = dict(F1, **{"Talep ID": "D00002", "Varış Transfer Merkezi": "Manisa"})
    res = simulate(_plan([P1]), _forecast([F1, f2]), data, rental_days=[])
    assert any("D00002" in v for v in res.violations)


def test_duplicate_forecast_id_flagged_without_overwrite(data):
    duplicate = dict(F1, **{"Tahmin Edilen Desi": 9000.0})
    res = simulate(_plan([P1]), _forecast([F1, duplicate]), data,
                   rental_days=[])
    assert any("tahmin dosyasında tekrarlı talep ID" in v
               for v in res.violations)
    assert len(res.per_demand) == 1
    assert res.per_demand.iloc[0]["desi"] == 10000.0
    assert res.per_demand.iloc[0]["teslim_desi"] == 10000.0


def test_loading_before_ready_flagged(data):
    # Hazır anı 09:00; kalkış 09:30 => yükleme 07:50'de başlar -> İHLAL
    p = dict(P1, **{"Çıkış Saati": "09:30", "Varış Saati": "10:26"})
    res = simulate(_plan([p]), _forecast([F1]), data, rental_days=[])
    assert any("hazır" in v.lower() for v in res.violations)


def test_simulator_rejects_noncanonical_forecast_slot_clearly(data):
    forecast = dict(F1, **{"Talep Tamamlama Saati": "09:00:01"})

    with pytest.raises(ValueError, match="Geçersiz forecast saati.*09:00:01"):
        simulate(_plan([P1]), _forecast([forecast]), data, rental_days=[])


def test_exported_forecast_artifact_is_simulator_ready_for_rental_modes(
        tmp_path, data):
    forecast = _forecast([
        dict(F1, **{"Tahmin Edilen Desi": 5000.0}),
        dict(F1, **{"Talep ID": "D00002",
                    "Talep Tamamlama Saati": "17:00",
                    "Tahmin Edilen Desi": 5000.0}),
    ])
    path = write_forecast_xlsx(
        forecast,
        tmp_path / "Talep-tahmini.xlsx",
        data,
        date(2026, 6, 29),
        date(2026, 6, 29),
        ods=[("İstanbul", "Yalova")],
    )
    artifact = pd.read_excel(path)
    plan = _plan([
        dict(P1, **{"Taşınan Desi": 5000.0,
                    "Çıkış Saati": "10:00", "Varış Saati": "10:56",
                    "Çıkış Elleçleme süresi": 50,
                    "Varış elleçleme süresi": 50,
                    "Toplam maliyet": 2767.5}),
        dict(P1, **{"Araç ID": "V0002", "Talep ID": "D00002",
                    "Taşınan Desi": 5000.0,
                    "Çıkış Saati": "18:00", "Varış Saati": "18:56",
                    "Çıkış Elleçleme süresi": 50,
                    "Varış elleçleme süresi": 50,
                    "Toplam maliyet": 2767.5}),
    ])

    assert artifact["Talep Tamamlama Saati"].tolist() == [
        time(9), time(17)]

    explicit = simulate(plan, artifact, data, rental_days=[])
    automatic = simulate(plan, artifact, data)

    assert explicit.violations == []
    assert len(automatic.violations) == 12
    assert all(
        violation.startswith("Kiralık ihlali 2026-06-29:")
        for violation in automatic.violations
    )


def test_consolidation_two_vehicles_double_handling(data):
    # İstanbul->Eskişehir talebi Yalova üzerinden 2 araçla (konsolidasyon):
    # Yalova'da indirme (V0001) + yeniden yükleme (V0002) = 2 elleçleme;
    # SLA nihai Eskişehir'de biter.
    f = {"Talep ID": "D00001", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Eskişehir", "Tahmin Edilen Desi": 5000.0}
    leg1 = dict(P1, **{"Taşınan Desi": 5000.0, "Çıkış Saati": "10:00",
                       "Varış Saati": "10:56",
                       "Çıkış Elleçleme süresi": 50,
                       "Varış elleçleme süresi": 50,
                       "Toplam maliyet": 2767.5})
    # V0001 indirmesi 10:56+50dk = 11:46'da biter; V0002 yüklemesi 12:40-50dk=11:50 OK
    leg2 = {"Araç ID": "V0002", "Araç Tipi": "Spot", "Araç türü": "Kamyon",
            "Çıkış Transfer Merkezi": "Yalova", "Varış Transfer Merkezi": "Eskişehir",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "12:40",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "15:18",
            "Talep ID": "D00001", "Taşınan Desi": 5000.0,
            "Yolculuk süresi": 158, "Varış elleçleme süresi": 50,
            "Çıkış Elleçleme süresi": 50, "SLA cezası": 0.0,
            "Toplam maliyet": 5232.475}
    res = simulate(_plan([leg1, leg2]), _forecast([f]), data, rental_days=[])
    assert res.violations == []
    assert res.sla_penalty == 0.0    # tamamlanma < 30.06 09:00 deadline


def test_transfer_cannot_create_or_lose_desi(data):
    f = dict(F1, **{"Varış Transfer Merkezi": "Eskişehir",
                    "Tahmin Edilen Desi": 5000.0})
    leg1 = dict(P1, **{"Taşınan Desi": 5000.0, "Çıkış Saati": "10:00",
                       "Varış Saati": "10:56",
                       "Çıkış Elleçleme süresi": 50,
                       "Varış elleçleme süresi": 50,
                       "Toplam maliyet": 2767.5})
    leg2 = {"Araç ID": "V0002", "Araç Tipi": "Spot", "Araç türü": "Kamyon",
            "Çıkış Transfer Merkezi": "Yalova", "Varış Transfer Merkezi": "Eskişehir",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "12:30",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "15:08",
            "Talep ID": "D00001", "Taşınan Desi": 4000.0,
            "Yolculuk süresi": 158, "Varış elleçleme süresi": 40,
            "Çıkış Elleçleme süresi": 40, "SLA cezası": 0.0,
            "Toplam maliyet": 5126.391666666666}
    res = simulate(_plan([leg1, leg2]), _forecast([f]), data, rental_days=[])
    assert any("bacaklar arasında desi değişiyor" in v
               and "yaratılamaz/kaybolamaz" in v for v in res.violations)


def test_consolidation_bad_transfer_timing_flagged(data):
    # V0002, V0001'in indirmesi bitmeden yüklemeye başlıyor -> ihlal
    f = {"Talep ID": "D00001", "Tarih": "29.06.2026",
         "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
         "Varış Transfer Merkezi": "Eskişehir", "Tahmin Edilen Desi": 5000.0}
    leg1 = dict(P1, **{"Taşınan Desi": 5000.0, "Çıkış Saati": "10:00",
                       "Varış Saati": "10:56",
                       "Çıkış Elleçleme süresi": 50,
                       "Varış elleçleme süresi": 50,
                       "Toplam maliyet": 2767.5})
    leg2 = {"Araç ID": "V0002", "Araç Tipi": "Spot", "Araç türü": "Kamyon",
            "Çıkış Transfer Merkezi": "Yalova", "Varış Transfer Merkezi": "Eskişehir",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",  # yükleme 10:10!
            "Varış Tarihi": "29.06.2026", "Varış Saati": "13:38",
            "Talep ID": "D00001", "Taşınan Desi": 5000.0,
            "Yolculuk süresi": 158, "Varış elleçleme süresi": 50,
            "Çıkış Elleçleme süresi": 50, "SLA cezası": 0.0,
            "Toplam maliyet": 5232.475}
    res = simulate(_plan([leg1, leg2]), _forecast([f]), data, rental_days=[])
    assert any("aktarma" in v.lower() for v in res.violations)


@pytest.mark.parametrize(
    ("column", "other_value"),
    [("Araç Tipi", "Kiralık"), ("Araç türü", "Kamyon")],
)
def test_same_leg_group_vehicle_fields_reach_simulation_violations(
        data, column, other_value):
    f1 = dict(F1, **{"Tahmin Edilen Desi": 5000.0})
    f2 = dict(F1, **{"Talep ID": "D00002", "Tahmin Edilen Desi": 5000.0})
    p1 = dict(P1, **{"Taşınan Desi": 5000.0,
                     "Varış elleçleme süresi": 50,
                     "Çıkış Elleçleme süresi": 50,
                     "Toplam maliyet": 1790.0})
    p2 = dict(P1, **{"Talep ID": "D00002", "Taşınan Desi": 5000.0,
                     "Varış elleçleme süresi": 50,
                     "Çıkış Elleçleme süresi": 50,
                     "Toplam maliyet": 1790.0})
    p2[column] = other_value
    res = simulate(_plan([p1, p2]), _forecast([f1, f2]), data,
                   rental_days=[])
    assert any(column in v and "aynı bacak grubunda" in v
               for v in res.violations)


def test_kiralik_route_and_daily_count(data):
    # Tek kiralık İst->Yalova Tır çıkışı; rota geçerli ama o gün 2 olmalıydı
    # + diğer 11 rota tamamen eksik. None, forecast gününü otomatik denetler.
    p = dict(P1, **{"Araç Tipi": "Kiralık",
                    "Toplam maliyet": 2024.4444444444446})
    res = simulate(_plan([p]), _forecast([F1]), data)
    kiralik_viols = [v for v in res.violations if "Kiralık" in v]
    assert len(kiralik_viols) == 12   # İst->Yalova 1!=2 + 11 eksik rota
    assert all(str(date(2026, 6, 29)) in v for v in kiralik_viols)

    # Açık boş liste API seviyesinde zorunlu kiralık kontrolünü kapatır.
    res2 = simulate(_plan([p]), _forecast([F1]), data, rental_days=[])
    assert [v for v in res2.violations if "Kiralık" in v] == []


def test_default_rental_days_use_unique_forecast_dates(data):
    f2 = dict(F1, **{"Talep ID": "D00002", "Tarih": "30.06.2026"})
    res = simulate(_plan([]), _forecast([F1, f2]), data)
    kiralik_viols = [v for v in res.violations if "Kiralık" in v]
    assert len(kiralik_viols) == 24
    assert any(str(date(2026, 6, 29)) in v for v in kiralik_viols)
    assert any(str(date(2026, 6, 30)) in v for v in kiralik_viols)


def test_default_rental_days_extend_to_last_cargo_day(data):
    # Q&A: kiralık filo dağıtım bitene kadar her gün çıkar. Kargo 06.07'de
    # teslim ediliyorsa kiralık denetimi 06.07'yi de kapsar (07.07'yi değil).
    p = dict(P1, **{"Çıkış Tarihi": "05.07.2026", "Çıkış Saati": "22:00",
                    "Varış Tarihi": "05.07.2026", "Varış Saati": "22:56",
                    "SLA cezası": 544000.0, "Toplam maliyet": 547580.0})
    res = simulate(_plan([p]), _forecast([F1]), data)
    kiralik_viols = [v for v in res.violations if "Kiralık ihlali" in v]
    days = {v.split(":")[0].rsplit(" ", 1)[-1] for v in kiralik_viols}
    assert "2026-06-29" in days
    assert "2026-07-05" in days
    assert "2026-07-06" in days          # sarkma günü de denetlenir
    assert "2026-07-07" not in days      # dağıtımın bittiği günden sonrası değil
    assert len(kiralik_viols) == 12 * 8  # 12 rota x 8 gün (29.06 - 06.07)


def test_kiralik_off_route_flagged(data):
    # İstanbul->Mardin kiralık rotası yok -> ihlal (rental_days olmasa bile)
    f = dict(F1, **{"Varış Transfer Merkezi": "Mardin"})
    p = dict(P1, **{"Araç Tipi": "Kiralık", "Varış Transfer Merkezi": "Mardin",
                    "Varış Tarihi": "30.06.2026", "Varış Saati": "08:31",
                    "Yolculuk süresi": 1291,
                    "Toplam maliyet": 25421.916666666668})
    res = simulate(_plan([p]), _forecast([f]), data, rental_days=[])
    assert any("rota" in v.lower() for v in res.violations)


def test_empty_plan_result_schema(data):
    res = simulate(_plan([]), _forecast([]), data)
    assert list(res.per_vehicle.columns) == ["vehicle_id", "kind", "vtype",
                                             "legs", "km", "usage_hours", "cost"]
    assert list(res.per_demand.columns) == ["talep_id", "desi",
                                            "teslim_desi", "ceza"]
    assert res.total_cost == 0.0
    assert res.violations == []


def test_kiralik_multiday_same_id_flagged(data):
    p1 = dict(P1, **{"Araç Tipi": "Kiralık"})
    p2 = dict(P1, **{"Araç Tipi": "Kiralık",
                     "Çıkış Tarihi": "30.06.2026",
                     "Varış Tarihi": "30.06.2026"})
    f2 = dict(F1, **{"Talep ID": "D00002", "Tarih": "30.06.2026"})
    res = simulate(_plan([p1, p2]), _forecast([F1, f2]), data, rental_days=[])
    assert not any("beyan varış" in v for v in res.violations)
    assert any("birden fazla günde" in v for v in res.violations)


def test_wrong_origin_pickup_flagged(data):
    # Tahmin İstanbul->Yalova; plan Eskişehir'den yükleyip Yalova'ya götürüyor.
    # Fiziksel olarak imkansız rota ihlalsiz geçmemeli.
    p = dict(P1, **{"Çıkış Transfer Merkezi": "Eskişehir",
                    "Çıkış Saati": "12:00", "Varış Saati": "14:50",
                    "Yolculuk süresi": 170,
                    "Toplam maliyet": 7606.25})
    res = simulate(_plan([p]), _forecast([F1]), data, rental_days=[])
    assert any("tahmin çıkışından başlamıyor" in v for v in res.violations)
