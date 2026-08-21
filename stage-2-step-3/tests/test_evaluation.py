from copy import deepcopy as real_deepcopy
from datetime import datetime, time, timedelta
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import pandas as pd
import pytest

import src.evaluation as evaluation_module
from src.candidates import Part
from src.data import DATA_DIR, load_all
from src.evaluation import (PlanEvaluation, PlanMetrics, accepts_candidate,
                            evaluate_legs, forecast_fingerprint,
                            improvement_tl, summarize_evaluation)
from src.export import write_plan_xlsx
from src.optimize import PlannedLeg
from src.schemas import FORECAST_COLS, PLAN_COLS
from src.simulator import SimResult
from src.timeutil import handling_minutes, travel_minutes


FORECAST_ROW = {
    "Talep ID": "D00001",
    "Tarih": "29.06.2026",
    "Talep Tamamlama Saati": "09:00",
    "Çıkış Transfer Merkezi": "İstanbul",
    "Varış Transfer Merkezi": "Yalova",
    "Tahmin Edilen Desi": 38,
}


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _forecast(*rows):
    return pd.DataFrame(rows, columns=FORECAST_COLS)


def _direct_kamyonet(data, desi=100):
    ready = datetime(2026, 6, 29, 9)
    lane = data.lanes[("İstanbul", "Yalova")]
    vehicle = data.vehicles["Kamyonet"]
    load_start = ready
    dep = load_start + timedelta(minutes=handling_minutes(desi))
    arr = dep + timedelta(minutes=travel_minutes(lane.hours["Kamyonet"]))
    unload_end = arr + timedelta(minutes=handling_minutes(desi))
    usage_hours = (unload_end - load_start).total_seconds() / 3600
    part = Part(
        "D00001", "D00001", desi, ready, ready + timedelta(days=1),
        dest="Yalova")
    return PlannedLeg(
        kind="Spot",
        vtype="Kamyonet",
        origin="İstanbul",
        dest="Yalova",
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=unload_end,
        items=[(part, desi)],
        cost=vehicle.spot_hourly * usage_hours + vehicle.spot_per_km * lane.km,
    )


def _metric_leg(kind, vtype, desi, part_id):
    ready = datetime(2026, 6, 29, 9)
    items = []
    if desi:
        part = Part(
            part_id, part_id, desi, ready, ready + timedelta(days=1),
            dest="Yalova")
        items = [(part, desi)]
    return PlannedLeg(
        kind=kind,
        vtype=vtype,
        origin="İstanbul",
        dest="Yalova",
        load_start=ready,
        dep=ready,
        arr=ready,
        unload_end=ready,
        items=items,
    )


def _metric_chain(initial_desi, remaining_desi, chain_id):
    ready = datetime(2026, 6, 29, 9)
    first_drop = Part(
        f"B-{chain_id}", f"B-{chain_id}", initial_desi - remaining_desi,
        ready, ready + timedelta(days=1), dest="B")
    final_drop = Part(
        f"C-{chain_id}", f"C-{chain_id}", remaining_desi,
        ready, ready + timedelta(days=1), dest="C")
    first = PlannedLeg(
        kind="Spot",
        vtype="Kamyonet",
        origin="A",
        dest="B",
        load_start=ready,
        dep=ready,
        arr=ready + timedelta(hours=1),
        unload_end=ready + timedelta(hours=1),
        items=[
            (first_drop, initial_desi - remaining_desi),
            (final_drop, remaining_desi),
        ],
        chain_id=chain_id,
        chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot",
        vtype="Kamyonet",
        origin="B",
        dest="C",
        load_start=first.unload_end,
        dep=first.unload_end,
        arr=first.unload_end + timedelta(hours=1),
        unload_end=first.unload_end + timedelta(hours=1),
        items=[(final_drop, remaining_desi)],
        chain_id=chain_id,
        chain_seq=1,
    )
    return [first, second]


def _evaluation(total_cost, *, legs=None, vehicle_cost=0, sla_penalty=0,
                violations=()):
    result = SimResult(
        vehicle_cost=vehicle_cost,
        sla_penalty=sla_penalty,
        total_cost=total_cost,
        violations=list(violations),
        per_vehicle=pd.DataFrame(),
        per_demand=pd.DataFrame(),
    )
    return PlanEvaluation(
        legs=[] if legs is None else legs,
        plan_frame=pd.DataFrame(columns=PLAN_COLS),
        result=result,
        notes=(),
    )


@pytest.fixture
def artifact_data():
    vehicle = SimpleNamespace(
        capacity_desi=5600,
        rental_hourly=30,
        rental_per_km=0.5,
        spot_hourly=60,
        spot_per_km=1,
    )
    lane = SimpleNamespace(
        km=60,
        hours={"Kamyonet": 1},
        sla_days=1,
    )
    return SimpleNamespace(
        vehicles={"Kamyonet": vehicle},
        lanes={("A", "B"): lane},
        rentals=[],
        handling_cap={"A": 100_000, "B": 100_000},
        tir_cap={"A": 100, "B": 100},
        tms=["A", "B"],
    )


def _artifact_workbooks(tmp_path):
    forecast = pd.DataFrame([{
        "Talep ID": "D00001",
        "Tarih": "29.06.2026",
        "Talep Tamamlama Saati": "09:00",
        "Çıkış Transfer Merkezi": "A",
        "Varış Transfer Merkezi": "B",
        "Tahmin Edilen Desi": 100,
    }], columns=FORECAST_COLS)
    plan = pd.DataFrame([{
        "Araç ID": "V0001",
        "Araç Tipi": "Spot",
        "Araç türü": "Kamyonet",
        "Çıkış Transfer Merkezi": "A",
        "Varış Transfer Merkezi": "B",
        "Çıkış Tarihi": "29.06.2026",
        "Çıkış Saati": "09:01",
        "Varış Tarihi": "29.06.2026",
        "Varış Saati": "10:01",
        "Talep ID": "D00001",
        "Taşınan Desi": 100,
        "Yolculuk süresi": 60,
        "Varış elleçleme süresi": 1,
        "Çıkış Elleçleme süresi": 1,
        "SLA cezası": 0,
        "Toplam maliyet": 122,
    }], columns=PLAN_COLS)
    forecast_path = tmp_path / "forecast.xlsx"
    plan_path = tmp_path / "plan.xlsx"
    forecast.to_excel(forecast_path, index=False)
    plan.to_excel(plan_path, index=False)
    return forecast, plan, forecast_path, plan_path


def test_fingerprint_normalizes_slot_and_desi():
    text_and_int = _forecast(FORECAST_ROW)
    time_and_float = _forecast(dict(
        FORECAST_ROW,
        **{"Talep Tamamlama Saati": time(9), "Tahmin Edilen Desi": 38.0},
    ))

    assert forecast_fingerprint(text_and_int) == forecast_fingerprint(
        time_and_float)


def test_fingerprint_is_order_independent():
    second = dict(
        FORECAST_ROW,
        **{"Talep ID": "D00002", "Talep Tamamlama Saati": "17:00",
           "Tahmin Edilen Desi": 72},
    )
    forward = _forecast(FORECAST_ROW, second)
    reverse = forward.iloc[::-1].copy()

    assert forecast_fingerprint(forward) == forecast_fingerprint(reverse)


@pytest.mark.parametrize(
    ("column", "changed_value"),
    [
        ("Talep ID", "D00002"),
        ("Tarih", "30.06.2026"),
        ("Talep Tamamlama Saati", "17:00"),
        ("Çıkış Transfer Merkezi", "Yalova"),
        ("Varış Transfer Merkezi", "İstanbul"),
        ("Tahmin Edilen Desi", 39),
    ],
    ids=["id", "date", "slot", "origin", "destination", "desi"],
)
def test_fingerprint_detects_each_row_value(column, changed_value):
    changed = dict(FORECAST_ROW)
    changed[column] = changed_value

    assert forecast_fingerprint(_forecast(FORECAST_ROW)) != forecast_fingerprint(
        _forecast(changed))


def test_plan_fingerprint_matches_plan_xlsx_round_trip(
        tmp_path, artifact_data):
    _forecast_frame, plan, _forecast_path, _plan_path = _artifact_workbooks(
        tmp_path)
    row = plan.iloc[0].to_dict()
    row.update({
        "Araç Tipi": "Kiralık",
        "Talep ID": "",
        "Taşınan Desi": 0,
        "SLA cezası": 0.30000000000000004,
    })
    in_memory = pd.DataFrame([row], columns=PLAN_COLS)
    path = write_plan_xlsx(
        in_memory, tmp_path / "round-trip-plan.xlsx", artifact_data)
    reloaded = pd.read_excel(path)

    assert str(in_memory.loc[0, "SLA cezası"]) == "0.30000000000000004"
    assert reloaded.loc[0, "SLA cezası"] == 0.3
    assert pd.isna(reloaded.loc[0, "Talep ID"])
    assert evaluation_module.plan_fingerprint(
        in_memory) == evaluation_module.plan_fingerprint(reloaded)


def test_plan_fingerprint_is_order_independent(tmp_path):
    _forecast_frame, plan, _forecast_path, _plan_path = _artifact_workbooks(
        tmp_path)
    second = plan.copy()
    second.loc[0, "Araç ID"] = "V0002"
    forward = pd.concat([plan, second], ignore_index=True)

    assert evaluation_module.plan_fingerprint(
        forward) == evaluation_module.plan_fingerprint(forward.iloc[::-1])


def test_plan_fingerprint_preserves_row_multiplicity(tmp_path):
    _forecast_frame, plan, _forecast_path, _plan_path = _artifact_workbooks(
        tmp_path)
    duplicated = pd.concat([plan, plan], ignore_index=True)

    assert evaluation_module.plan_fingerprint(
        duplicated) != evaluation_module.plan_fingerprint(plan)


def test_plan_fingerprint_requires_exact_columns(tmp_path):
    _forecast_frame, plan, _forecast_path, _plan_path = _artifact_workbooks(
        tmp_path)

    with pytest.raises(ValueError, match="Plan kolonları"):
        evaluation_module.plan_fingerprint(plan.drop(columns=["SLA cezası"]))


def test_evaluate_deep_copies_once_without_source_mutation(data, monkeypatch):
    source = [_direct_kamyonet(data)]
    source_snapshot = real_deepcopy(source)
    source_part = source[0].items[0][0]
    calls = []

    def tracking_deepcopy(value):
        calls.append(value)
        return real_deepcopy(value)

    monkeypatch.setattr(evaluation_module, "deepcopy", tracking_deepcopy)

    evaluation = evaluate_legs(
        source,
        _forecast(dict(FORECAST_ROW, **{"Tahmin Edilen Desi": 100})),
        data,
    )

    assert len(calls) == 1
    assert calls[0] is source
    assert evaluation.legs is not source
    assert evaluation.legs[0].items[0][0] is not source_part
    assert source == source_snapshot
    assert isinstance(evaluation.notes, tuple)
    assert list(evaluation.plan_frame.columns) == PLAN_COLS


def test_evaluate_returns_violations(data):
    evaluation = evaluate_legs(
        [_direct_kamyonet(data)],
        _forecast(dict(FORECAST_ROW, **{"Tahmin Edilen Desi": 101})),
        data,
    )

    assert any(
        "D00001: teslim edilen desi 100.0 != tahmin 101.0" in violation
        for violation in evaluation.result.violations
    )


def test_evaluate_raises_schema_error(data, monkeypatch):
    monkeypatch.setattr(
        evaluation_module,
        "validate_plan",
        lambda frame, competition_data: ["first schema error", "second schema error"],
    )

    with pytest.raises(ValueError) as caught:
        evaluate_legs(
            [_direct_kamyonet(data)],
            _forecast(dict(FORECAST_ROW, **{"Tahmin Edilen Desi": 100})),
            data,
        )

    assert "first schema error" in str(caught.value)
    assert "second schema error" in str(caught.value)


def test_evaluate_raises_reconciliation_error(data, monkeypatch):
    reconciliation_error = ValueError("reconciliation failed")

    def reject_total(frame, expected_total):
        raise reconciliation_error

    monkeypatch.setattr(
        evaluation_module, "require_plan_total", reject_total)

    with pytest.raises(ValueError) as caught:
        evaluate_legs(
            [_direct_kamyonet(data)],
            _forecast(dict(FORECAST_ROW, **{"Tahmin Edilen Desi": 100})),
            data,
        )

    assert caught.value is reconciliation_error


def test_direct_stage0_stage1_metric_semantics_are_unchanged(data):
    legs = [
        _metric_leg("Spot", "Kamyonet", 2800, "D00001"),
        _metric_leg("Spot", "Hafif Kamyon", 3600, "D00002"),
        _metric_leg("Kiralık", "Tır", 0, "D00003"),
    ]
    evaluation = _evaluation(
        Decimal("12.999999"),
        legs=legs,
        vehicle_cost=Decimal("12.34"),
        sla_penalty=Decimal("0.66"),
        violations=("one", "two"),
    )

    assert summarize_evaluation(evaluation, data) == PlanMetrics(
        vehicle_cost=Decimal("12.34"),
        sla_penalty=Decimal("0.66"),
        total_cost=Decimal("12.999999"),
        rented_legs=1,
        spot_legs=2,
        vehicle_mix=(("Hafif Kamyon", 1), ("Kamyonet", 1), ("Tır", 1)),
        average_spot_fill=Fraction(1, 2),
        spot_below_30_percent=0,
        violations=2,
    )


def test_chain_metrics_count_one_physical_spot_route(data):
    evaluation = _evaluation(
        0,
        legs=_metric_chain(2000, 500, chain_id=7),
    )

    metrics = summarize_evaluation(evaluation, data)

    assert metrics.rented_legs == 0
    assert metrics.spot_legs == 1
    assert metrics.vehicle_mix == (("Kamyonet", 1),)


def test_chain_fill_uses_initial_onboard_load(data):
    evaluation = _evaluation(
        0,
        legs=_metric_chain(2800, 560, chain_id=7),
    )

    fill = summarize_evaluation(evaluation, data).average_spot_fill

    assert fill == Fraction(1, 2)
    assert fill != Fraction(1, 10)
    assert fill != Fraction(3, 10)


def test_physical_below_thirty_threshold_is_strict(data):
    evaluation = _evaluation(
        0,
        legs=(
            _metric_chain(1679, 679, chain_id=7)
            + _metric_chain(1680, 680, chain_id=8)
        ),
    )

    metrics = summarize_evaluation(evaluation, data)

    assert metrics.spot_legs == 2
    assert metrics.spot_below_30_percent == 1


def test_malformed_metric_chain_raises(data):
    legs = _metric_chain(2000, 500, chain_id=7)
    legs[1].chain_seq = 2

    with pytest.raises(ValueError, match="chain_seq"):
        summarize_evaluation(_evaluation(0, legs=legs), data)


def test_strict_below_thirty_percent(data):
    evaluation = _evaluation(
        0,
        legs=[
            _metric_leg("Spot", "Kamyonet", 1679, "D00001"),
            _metric_leg("Spot", "Kamyonet", 1680, "D00002"),
        ],
    )

    assert summarize_evaluation(evaluation, data).spot_below_30_percent == 1


@pytest.mark.parametrize(
    ("saving", "accepted"),
    [
        (Decimal("0.999999"), False),
        (Decimal("1.00"), True),
        (Decimal("1.000001"), True),
    ],
)
def test_raw_inclusive_saving(saving, accepted):
    baseline = _evaluation(Decimal("100"))
    candidate = _evaluation(Decimal("100") - saving)

    assert improvement_tl(baseline, candidate) == saving
    assert accepts_candidate(baseline, candidate) is accepted


@pytest.mark.parametrize(
    ("baseline_violations", "candidate_violations"),
    [(("baseline violation",), ()), ((), ("candidate violation",))],
)
def test_both_sides_require_zero_violations(
        baseline_violations, candidate_violations):
    baseline = _evaluation(Decimal("100"), violations=baseline_violations)
    candidate = _evaluation(Decimal("90"), violations=candidate_violations)

    assert accepts_candidate(baseline, candidate) is False


def test_artifact_reloads_and_resimulates(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)

    result = evaluation_module.verify_plan_artifact(
        plan_path,
        forecast_path,
        artifact_data,
        expected_total=Decimal("122"),
        expected_forecast_fingerprint=forecast_fingerprint(forecast),
        expected_plan_fingerprint=evaluation_module.plan_fingerprint(plan),
    )

    assert result.violations == []
    assert Decimal(str(result.total_cost)) == Decimal("122.0")


def test_artifact_detects_forecast_change(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    expected_fingerprint = forecast_fingerprint(forecast)
    changed = pd.read_excel(forecast_path)
    changed.loc[0, "Tahmin Edilen Desi"] += 1
    changed.to_excel(forecast_path, index=False)

    with pytest.raises(ValueError, match="fingerprint"):
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122"),
            expected_forecast_fingerprint=expected_fingerprint,
            expected_plan_fingerprint=evaluation_module.plan_fingerprint(plan),
        )


def test_artifact_total_tolerance(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    fingerprint = forecast_fingerprint(forecast)

    evaluation_module.verify_plan_artifact(
        plan_path,
        forecast_path,
        artifact_data,
        expected_total=Decimal("122.01"),
        expected_forecast_fingerprint=fingerprint,
        expected_plan_fingerprint=evaluation_module.plan_fingerprint(plan),
    )

    with pytest.raises(ValueError, match="total"):
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122.010001"),
            expected_forecast_fingerprint=fingerprint,
            expected_plan_fingerprint=evaluation_module.plan_fingerprint(plan),
        )


def test_artifact_declared_reconciliation(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    plan.loc[0, "Toplam maliyet"] += 1
    plan.to_excel(plan_path, index=False)
    expected_plan_fingerprint = evaluation_module.plan_fingerprint(plan)

    with pytest.raises(ValueError, match="Toplam maliyet uzlaşmıyor"):
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122"),
            expected_forecast_fingerprint=forecast_fingerprint(forecast),
            expected_plan_fingerprint=expected_plan_fingerprint,
        )


def test_artifact_rejects_violation(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    plan.loc[0, "Varış Saati"] = "23:59"
    plan.to_excel(plan_path, index=False)
    expected_plan_fingerprint = evaluation_module.plan_fingerprint(plan)

    with pytest.raises(ValueError) as caught:
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122"),
            expected_forecast_fingerprint=forecast_fingerprint(forecast),
            expected_plan_fingerprint=expected_plan_fingerprint,
        )

    assert "beyan varış" in str(caught.value)


def test_artifact_detects_vehicle_id_change(tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    expected_plan_fingerprint = evaluation_module.plan_fingerprint(plan)
    changed = pd.read_excel(plan_path)
    changed.loc[0, "Araç ID"] = "V0002"
    changed.to_excel(plan_path, index=False)

    with pytest.raises(ValueError, match="Plan fingerprint"):
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122"),
            expected_forecast_fingerprint=forecast_fingerprint(forecast),
            expected_plan_fingerprint=expected_plan_fingerprint,
        )


def test_artifact_detects_referee_ignored_declaration(
        tmp_path, artifact_data):
    forecast, plan, forecast_path, plan_path = _artifact_workbooks(tmp_path)
    expected_plan_fingerprint = evaluation_module.plan_fingerprint(plan)
    changed = pd.read_excel(plan_path)
    changed.loc[0, "SLA cezası"] = 1
    changed.to_excel(plan_path, index=False)

    with pytest.raises(ValueError, match="Plan fingerprint"):
        evaluation_module.verify_plan_artifact(
            plan_path,
            forecast_path,
            artifact_data,
            expected_total=Decimal("122"),
            expected_forecast_fingerprint=forecast_fingerprint(forecast),
            expected_plan_fingerprint=expected_plan_fingerprint,
        )
