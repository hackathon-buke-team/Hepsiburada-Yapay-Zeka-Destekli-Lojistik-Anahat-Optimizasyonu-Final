"""Taşıma planı orkestrasyonu (build_plan) ve çizelge (to_plan_frame)
testleri — Q&A sarkma-günü kiralık kuralı ve oransal süre beyanları."""
import itertools
from collections import Counter
from dataclasses import replace
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

import run as run_module
from src.chain import physical_routes
from src.candidates import Part
from src.data import DATA_DIR, load_all
from src.evaluation import PlanEvaluation, forecast_fingerprint
from src.export import require_plan_total
from src.forecast import forecast_horizon, to_forecast_frame
from src.milkrun import MilkRunDecision, MilkRunMetrics
from src.optimize import PlannedLeg, build_plan, prepare_frame, rented_departure
from src.pickup import PickupMetrics
from src.repair import (RepairMetrics, Stage1Decision, run_same_lane_stage)
from src.schedule import to_plan_frame
from src.schemas import PLAN_COLS, PLAN_NUMERIC_COLS
from src.simulator import SimResult, simulate
from src.timeutil import handling_minutes, travel_minutes

H_START = date(2026, 6, 29)


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _frame(rows):
    """Küçük sentetik tahmin çerçevesi (şablon kolonları + hazırlık)."""
    import pandas as pd
    from src.schemas import FORECAST_COLS
    df = pd.DataFrame(rows, columns=FORECAST_COLS)
    return prepare_frame(df)


def _row(tid, day, slot, origin, dest, desi):
    return {"Talep ID": tid, "Tarih": day.strftime("%d.%m.%Y"),
            "Talep Tamamlama Saati": slot, "Çıkış Transfer Merkezi": origin,
            "Varış Transfer Merkezi": dest, "Tahmin Edilen Desi": desi}


def _stage_evaluation(total, marker):
    result = SimResult(
        vehicle_cost=total,
        sla_penalty=0,
        total_cost=total,
        violations=[],
        per_vehicle=pd.DataFrame(),
        per_demand=pd.DataFrame(),
    )
    plan_row = {column: marker for column in PLAN_COLS}
    for column in PLAN_NUMERIC_COLS:
        plan_row[column] = 0
    plan_row["Talep ID"] = ""
    return PlanEvaluation(
        legs=[],
        plan_frame=pd.DataFrame([plan_row], columns=PLAN_COLS),
        result=result,
        notes=(),
    )


def _stage_decision(*, accepted, baseline_total=100, candidate_total=90,
                    saving=None):
    baseline = _stage_evaluation(baseline_total, "baseline")
    candidate = _stage_evaluation(candidate_total, "candidate")
    metrics = RepairMetrics(0, 0, 0, 0, 0, Decimal("0"))
    if saving is None:
        saving = Decimal(str(baseline_total)) - Decimal(str(candidate_total))
    return Stage1Decision(
        baseline=baseline,
        candidate=candidate,
        selected=candidate if accepted else baseline,
        repair_metrics=metrics,
        accepted=accepted,
        saving_tl=saving,
    )


def _stage0_gate_case(monkeypatch):
    expected = {
        "vehicle_cost": Decimal("100"),
        "sla_penalty": Decimal("20"),
        "total_cost": Decimal("120"),
    }
    constants = {
        "STAGE0_FORECAST_ROWS": 1,
        "STAGE0_FORECAST_DESI": Decimal("100"),
        "STAGE0_FORECAST_IDS": frozenset({"D1"}),
        "STAGE0_LEGS": 2,
        "STAGE0_RENTED_LEGS": 1,
        "STAGE0_SPOT_LEGS": 1,
        "STAGE0_PLAN_ROWS": 2,
        "STAGE0_VEHICLE_COST": expected["vehicle_cost"],
        "STAGE0_SLA_PENALTY": expected["sla_penalty"],
        "STAGE0_TOTAL_COST": expected["total_cost"],
    }
    for name, value in constants.items():
        monkeypatch.setattr(run_module, name, value)

    forecast = pd.DataFrame({
        "Talep ID": ["D1"],
        "Tahmin Edilen Desi": [100],
    })
    legs = [
        SimpleNamespace(kind="Kiralık", vtype="Kamyonet", desi=100),
        SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=50),
    ]
    result = SimpleNamespace(
        vehicle_cost=expected["vehicle_cost"],
        sla_penalty=expected["sla_penalty"],
        total_cost=expected["total_cost"],
        violations=[],
    )
    evaluation = SimpleNamespace(
        legs=legs,
        plan_frame=pd.DataFrame(index=range(2)),
        result=result,
    )
    data = SimpleNamespace(
        vehicles={"Kamyonet": SimpleNamespace(capacity_desi=100)})
    return forecast, evaluation, data, expected


@pytest.mark.parametrize(
    "cost_field", ["vehicle_cost", "sla_penalty", "total_cost"])
def test_stage0_entry_accepts_exact_cent_cost_difference(
        monkeypatch, cost_field):
    forecast, evaluation, data, expected = _stage0_gate_case(monkeypatch)
    setattr(
        evaluation.result,
        cost_field,
        expected[cost_field] + Decimal("0.01"),
    )

    run_module._require_stage0_entry(forecast, evaluation, data)


@pytest.mark.parametrize(
    ("cost_field", "label"),
    [
        ("vehicle_cost", "araç maliyeti"),
        ("sla_penalty", "SLA cezası"),
        ("total_cost", "toplam maliyet"),
    ],
)
def test_stage0_entry_rejects_cost_just_over_cent(
        monkeypatch, cost_field, label):
    forecast, evaluation, data, expected = _stage0_gate_case(monkeypatch)
    setattr(
        evaluation.result,
        cost_field,
        expected[cost_field] + Decimal("0.010001"),
    )

    with pytest.raises(RuntimeError, match=label):
        run_module._require_stage0_entry(forecast, evaluation, data)


def test_stage0_entry_aggregates_nonfinite_costs(monkeypatch):
    forecast, evaluation, data, _expected = _stage0_gate_case(monkeypatch)
    evaluation.result.vehicle_cost = Decimal("NaN")
    evaluation.result.sla_penalty = Decimal("Infinity")
    evaluation.result.total_cost = Decimal("-Infinity")

    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage0_entry(forecast, evaluation, data)

    message = str(caught.value)
    assert "araç maliyeti hesaplanamadı" in message
    assert "SLA cezası hesaplanamadı" in message
    assert "toplam maliyet hesaplanamadı" in message


def test_stage0_entry_aggregates_every_independent_mismatch(monkeypatch):
    _forecast, evaluation, data, _expected = _stage0_gate_case(monkeypatch)
    malformed_forecast = pd.DataFrame({
        "Talep ID": ["unexpected", "extra"],
        "Tahmin Edilen Desi": ["not-a-number", 1],
    })
    evaluation.legs = [SimpleNamespace()]
    evaluation.plan_frame = pd.DataFrame(index=[0])
    evaluation.result.violations = None
    evaluation.result.vehicle_cost = Decimal("101")
    evaluation.result.sla_penalty = "not-a-number"
    evaluation.result.total_cost = Decimal("Infinity")

    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage0_entry(
            malformed_forecast, evaluation, data)

    message = str(caught.value)
    expected_details = (
        "forecast satırı 2 != 1",
        "forecast desi hesaplanamadı",
        "forecast ID seti eşleşmiyor",
        "bacak 1 != 2",
        "kiralık bacak hesaplanamadı",
        "Spot bacak hesaplanamadı",
        "plan satırı 1 != 2",
        "ihlal hesaplanamadı",
        "araç maliyeti 101 != 100 ±0.01",
        "SLA cezası hesaplanamadı",
        "toplam maliyet hesaplanamadı",
    )
    assert all(detail in message for detail in expected_details)


def test_flush_days_dispatch_full_rented_fleet(data):
    """Q&A: dağıtım bitene kadar kiralık filo her gün çıkar (boş olsa bile)."""
    frame = _frame([_row("D00001", H_START, "17:00",
                         "Manisa", "Mardin", 2000)])
    days = [H_START + timedelta(days=i) for i in range(2)]
    legs = build_plan(data, frame, days, flush_days=2)
    expected = sum(rr.count for rr in data.rentals)
    for offset in range(4):  # 2 ufuk + 2 boşaltma günü
        day = H_START + timedelta(days=offset)
        rented = [l for l in legs
                  if l.kind == "Kiralık" and l.dep.date() == day]
        assert len(rented) == expected, f"{day}: {len(rented)} != {expected}"
    # Boşaltma günlerindeki kiralık bacaklar boş olabilir (Talep ID'siz
    # yazılır); son gün hiç yük kalmamalı.
    last = H_START + timedelta(days=3)
    assert all(l.desi == 0 for l in legs
               if l.kind == "Kiralık" and l.dep.date() == last)


def test_flush_day_rented_departure_policy(data):
    """Tır kiralıklar boşaltma gününde de 17:00 politikasını korur (tır
    ziyaret düzeni ufuk günleriyle aynı kalır); Tır-olmayan kiralıklar
    erken (gece yarısı + tam yükleme) kalkar."""
    frame = _frame([_row("D00001", H_START, "17:00",
                         "Manisa", "Mardin", 2000)])
    legs = build_plan(data, frame, [H_START], flush_days=1)
    flush = H_START + timedelta(days=1)
    for rr in data.rentals:
        day_dep = rented_departure(rr, data.vehicles, flush, early=False)
        early_dep = rented_departure(rr, data.vehicles, flush, early=True)
        legs_rr = [l for l in legs if l.kind == "Kiralık"
                   and l.origin == rr.origin and l.dest == rr.dest
                   and l.dep.date() == flush]
        assert len(legs_rr) == rr.count
        for leg in legs_rr:
            if rr.vehicle == "Tır":
                assert leg.dep == day_dep      # 17:00 politikası korunur
            else:
                assert leg.dep == early_dep    # gece yarısı + tam yükleme


def test_end_to_end_small_scenario_zero_violations(data):
    """Sentetik küçük senaryo: plan -> çizelge -> simülatör 0 ihlal.

    Sarkma bilinçli olarak tetiklenir (uzun hat, son gün talebi) — böylece
    otomatik kiralık-günü uzatması ve boşaltma günü kiralıkları gerçek
    akışta denetlenir.
    """
    frame = _frame([
        _row("D00001", H_START, "17:00", "İstanbul", "Yalova", 30000),
        _row("D00002", H_START, "17:00", "Manisa", "Mardin", 2000),
        _row("D00003", H_START + timedelta(days=1), "17:00",
             "Tekirdağ", "Mardin", 5000),   # ~24 saatlik hat -> sarkma
    ])
    days = [H_START + timedelta(days=i) for i in range(2)]
    legs = build_plan(data, frame, days)
    plan_df, notes = to_plan_frame(legs, data)
    res = simulate(plan_df, frame.drop(columns=["_ready", "_day"]), data)
    assert res.violations == []
    # Teslim bütünlüğü: her talep tam teslim
    assert (res.per_demand["desi"] == res.per_demand["teslim_desi"]).all()


def test_plan_frame_per_row_handling_minutes(data):
    """Q&A: maliyet ve süre desi payında dağıtılır — her satır kendi
    desisinin elleçleme süresini (yukarı yuvarlı) beyan eder."""
    ready = datetime(2026, 6, 29, 17, 0)
    lane = data.lanes[("İstanbul", "Yalova")]
    parts = [
        (Part("D00001", "D00001", 1476, ready,
              ready + timedelta(hours=24), dest="Yalova"), 1476),
        (Part("D00002", "D00002", 20924, ready,
              ready + timedelta(hours=24), dest="Yalova"), 20924),
    ]
    total = sum(d for _, d in parts)
    load_start = ready
    dep = load_start + timedelta(minutes=handling_minutes(total))
    arr = dep + timedelta(minutes=travel_minutes(lane.hours["Tır"]))
    leg = PlannedLeg(kind="Spot", vtype="Tır", origin="İstanbul",
                     dest="Yalova", load_start=load_start, dep=dep, arr=arr,
                     unload_end=arr + timedelta(
                         minutes=handling_minutes(total)),
                     items=parts, cost=3580.0)
    plan_df, _ = to_plan_frame([leg], data, fix=False)
    assert len(plan_df) == 2
    for _, row in plan_df.iterrows():
        expected = handling_minutes(row["Taşınan Desi"])
        assert row["Çıkış Elleçleme süresi"] == expected
        assert row["Varış elleçleme süresi"] == expected
        # Yolculuk süresi oransal dağıtılmaz (Q&A) — bacak süresi tam yazılır
        assert row["Yolculuk süresi"] == travel_minutes(lane.hours["Tır"])
    # Maliyet paylaşımı desi oranında kalır ve toplamı verir
    assert abs(plan_df["Toplam maliyet"].sum() - 3580.0) < 0.01


def test_full_horizon_same_lane_stage_accepts_fixed_stage0_baseline(data):
    horizon_end = H_START + timedelta(days=6)
    forecast = to_forecast_frame(forecast_horizon(
        data.demand, H_START, horizon_end))
    forecast_before = forecast.copy(deep=True)
    fingerprint_before = forecast_fingerprint(forecast)
    days = [H_START + timedelta(days=offset) for offset in range(7)]
    source = build_plan(data, prepare_frame(forecast), days)
    source_before = deepcopy(source)

    decision = run_same_lane_stage(source, forecast, data)

    assert (
        len(forecast),
        int(forecast["Tahmin Edilen Desi"].sum()),
        forecast["Talep ID"].nunique(),
    ) == (4046, 4977975, 4046)
    assert forecast_fingerprint(forecast) == fingerprint_before
    pd.testing.assert_frame_equal(forecast, forecast_before)
    assert source == source_before

    baseline = decision.baseline
    assert (
        len(baseline.legs),
        sum(leg.kind == "Kiralık" for leg in baseline.legs),
        sum(leg.kind == "Spot" for leg in baseline.legs),
        len(baseline.plan_frame),
    ) == (1269, 126, 1143, 3167)
    cent = Decimal("0.01")
    assert tuple(
        Decimal(str(value)).quantize(cent)
        for value in (
            baseline.result.vehicle_cost,
            baseline.result.sla_penalty,
            baseline.result.total_cost,
        )
    ) == (
        Decimal("15460592.57"),
        Decimal("1020367.20"),
        Decimal("16480959.77"),
    )
    assert baseline.result.violations == []

    candidate = decision.candidate
    assert decision.accepted is True
    assert decision.selected is candidate
    assert decision.saving_tl >= Decimal("1.00")
    assert Decimal(str(candidate.result.total_cost)) < Decimal(
        str(baseline.result.total_cost))
    assert candidate.result.violations == []
    require_plan_total(candidate.plan_frame, candidate.result.total_cost)

    def part_inventory(legs):
        return Counter(
            (
                part.base_id,
                part.part_id,
                part.ready,
                part.deadline,
                part.carried_before,
                part.dest,
                Decimal(str(part.desi)),
                Decimal(str(desi)),
            )
            for leg in legs
            for part, desi in leg.items
        )

    for evaluated in (baseline, candidate):
        occurrences = Counter(
            id(part)
            for leg in evaluated.legs
            for part, _desi in leg.items
        )
        assert occurrences
        assert set(occurrences.values()) == {1}
    assert part_inventory(candidate.legs) == part_inventory(baseline.legs)
    assert sum(leg.kind == "Kiralık" for leg in candidate.legs) == 126
    assert sum(leg.kind == "Spot" for leg in candidate.legs) < 1143


def test_main_keeps_memory_forecast_for_build_and_reloaded_for_all_stages(
        tmp_path, monkeypatch):
    memory_forecast = pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)
    ])
    reloaded_forecast = memory_forecast.copy()
    decision = _stage_decision(accepted=True)
    data = SimpleNamespace(demand=object())
    prepared = object()
    source_legs = [SimpleNamespace(kind="Spot")]
    calls = []
    prepared_frames = []
    referee_frames = []

    monkeypatch.setattr(run_module, "OUT_DIR", tmp_path)
    monkeypatch.setattr(run_module, "load_all", lambda: data)
    monkeypatch.setattr(run_module, "forecast_horizon", lambda *args: object())
    monkeypatch.setattr(
        run_module, "to_forecast_frame", lambda forecast: memory_forecast)
    monkeypatch.setattr(
        run_module, "forecast_fingerprint", lambda frame: ("same",),
        raising=False)

    def fake_write_forecast(frame, path, *args):
        calls.append(("write-forecast", frame))
        return path

    def fake_prepare(frame):
        calls.append(("prepare", frame))
        prepared_frames.append(frame)
        return prepared

    def fake_build(competition_data, frame, days):
        assert frame is prepared
        return source_legs

    def fake_stage(legs, forecast, competition_data):
        calls.append(("stage1", forecast))
        referee_frames.append(forecast)
        assert legs is source_legs
        return decision

    def fake_milk_run(baseline, forecast, competition_data):
        calls.append(("stage2", forecast))
        referee_frames.append(forecast)
        assert baseline is decision.selected
        return SimpleNamespace(
            baseline=decision.selected,
            candidate=decision.selected,
            selected=decision.selected,
            metrics=SimpleNamespace(),
            accepted=True,
            saving_tl=Decimal("10.00"),
        )

    def fake_pickup(baseline, forecast, competition_data):
        calls.append(("stage3", forecast))
        referee_frames.append(forecast)
        assert baseline is decision.selected
        return SimpleNamespace(
            baseline=decision.selected,
            candidate=decision.selected,
            selected=decision.selected,
            metrics=SimpleNamespace(),
            accepted=True,
            saving_tl=Decimal("60000.00"),
        )

    monkeypatch.setattr(run_module, "write_forecast_xlsx", fake_write_forecast)
    monkeypatch.setattr(run_module.pd, "read_excel", lambda path: reloaded_forecast)
    monkeypatch.setattr(run_module, "prepare_frame", fake_prepare)
    monkeypatch.setattr(run_module, "build_plan", fake_build)
    monkeypatch.setattr(
        run_module, "run_same_lane_stage", fake_stage, raising=False)
    monkeypatch.setattr(
        run_module, "run_milk_run_stage", fake_milk_run, raising=False)
    monkeypatch.setattr(
        run_module, "run_pickup_stage", fake_pickup, raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage3_entry", lambda *args: None, raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage3_result", lambda *args: None,
        raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage0_entry", lambda *args: None, raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage1_entry", lambda *args: None, raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage2_entry", lambda *args: None, raising=False)
    monkeypatch.setattr(
        run_module, "_require_stage2_result", lambda *args: None,
        raising=False)
    monkeypatch.setattr(
        run_module, "_print_pipeline_metrics", lambda *args: None,
        raising=False)
    monkeypatch.setattr(
        run_module, "_stage_and_publish", lambda *args: calls.append(("publish",)),
        raising=False)

    run_module.main()

    assert len(prepared_frames) == 1
    assert prepared_frames[0] is memory_forecast
    assert referee_frames == [reloaded_forecast] * 3
    assert [name for name, *_ in calls if name.startswith("stage")] == [
        "stage1", "stage2", "stage3"]


@pytest.mark.parametrize("failing_step", ["stage2", "stage3", "publication"])
def test_main_never_prints_completion_after_stage_or_publication_exception(
        tmp_path, monkeypatch, capsys, failing_step):
    forecast = pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)
    ])
    decision = _stage_decision(accepted=True)
    publication_calls = []

    monkeypatch.setattr(run_module, "OUT_DIR", tmp_path)
    monkeypatch.setattr(
        run_module, "load_all", lambda: SimpleNamespace(demand=object()))
    monkeypatch.setattr(run_module, "forecast_horizon", lambda *args: object())
    monkeypatch.setattr(
        run_module, "to_forecast_frame", lambda _forecast: forecast)
    monkeypatch.setattr(
        run_module, "forecast_fingerprint", lambda _frame: ("same",))
    monkeypatch.setattr(
        run_module, "write_forecast_xlsx",
        lambda _frame, path, *_args: path)
    monkeypatch.setattr(run_module.pd, "read_excel", lambda _path: forecast)
    monkeypatch.setattr(run_module, "prepare_frame", lambda _frame: object())
    monkeypatch.setattr(run_module, "build_plan", lambda *_args: [])
    monkeypatch.setattr(
        run_module, "run_same_lane_stage", lambda *_args: decision)
    monkeypatch.setattr(run_module, "_require_stage0_entry", lambda *_args: None)
    monkeypatch.setattr(run_module, "_require_stage1_entry", lambda *_args: None)
    monkeypatch.setattr(run_module, "_require_stage2_entry", lambda *_args: None)
    monkeypatch.setattr(run_module, "_require_stage2_result", lambda *_args: None)
    monkeypatch.setattr(run_module, "_require_stage3_entry", lambda *_args: None)
    monkeypatch.setattr(run_module, "_require_stage3_result", lambda *_args: None)
    monkeypatch.setattr(
        run_module, "_print_pipeline_metrics", lambda *_args: None)

    def fake_decision(saving):
        return SimpleNamespace(
            baseline=decision.selected,
            candidate=decision.selected,
            selected=decision.selected,
            metrics=SimpleNamespace(),
            accepted=True,
            saving_tl=saving,
        )

    def fail_stage2(*_args):
        raise OSError("stage 2 failed")

    def fail_stage3(*_args):
        raise OSError("stage 3 failed")

    def fail_publication(*args):
        publication_calls.append(args)
        raise OSError("publication failed")

    monkeypatch.setattr(
        run_module, "run_milk_run_stage",
        fail_stage2 if failing_step == "stage2"
        else lambda *_args: fake_decision(Decimal("10.00")))
    monkeypatch.setattr(
        run_module, "run_pickup_stage",
        fail_stage3 if failing_step == "stage3"
        else lambda *_args: fake_decision(Decimal("60000.00")))
    expected_message = {
        "stage2": "stage 2 failed",
        "stage3": "stage 3 failed",
        "publication": "publication failed",
    }[failing_step]
    expected_publications = 1 if failing_step == "publication" else 0
    monkeypatch.setattr(run_module, "_stage_and_publish", fail_publication)

    with pytest.raises(OSError, match=expected_message):
        run_module.main()

    assert len(publication_calls) == expected_publications
    assert "Yayın tamamlandı" not in capsys.readouterr().out


@pytest.mark.parametrize("rejected_stage", ["stage1", "stage2", "stage3"])
def test_any_stage_rejection_preserves_both_official_files(
        tmp_path, monkeypatch, rejected_stage):
    decision, data = _make_stage1_decision(monkeypatch)
    stage1 = decision
    stage2 = _make_stage2_decision(decision)
    stage3 = _make_stage3_decision(stage2)
    if rejected_stage == "stage1":
        stage1 = Stage1Decision(
            baseline=decision.baseline,
            candidate=decision.candidate,
            selected=decision.selected,
            repair_metrics=decision.repair_metrics,
            accepted=False,
            saving_tl=decision.saving_tl,
        )
        expected_message = "kabul"
    elif rejected_stage == "stage2":
        stage2 = _make_stage2_decision(
            decision, accepted=False, saving=Decimal("0.50"))
        stage3 = _make_stage3_decision(stage2)
        expected_message = "Stage 2 reddedildi"
    else:
        stage3 = _make_stage3_decision(
            stage2, accepted=False, saving=Decimal("100.00"))
        expected_message = "Stage 3 reddedildi"

    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "official"
    staging_dir.mkdir()
    output_dir.mkdir()
    staged_forecast = staging_dir / "Talep-tahmini.xlsx"
    staged_forecast.write_bytes(b"staged-forecast")
    official_plan = output_dir / "Tasima-plani.xlsx"
    official_forecast = output_dir / "Talep-tahmini.xlsx"
    official_plan.write_bytes(b"old-plan")
    official_forecast.write_bytes(b"old-forecast")

    monkeypatch.setattr(
        run_module, "write_plan_xlsx",
        lambda *a: pytest.fail("reddedilen aşama plan yazmamalı"))
    monkeypatch.setattr(
        run_module, "verify_plan_artifact",
        lambda *a, **kw: pytest.fail("reddedilen aşama doğrulama yapmamalı"),
        raising=False)
    monkeypatch.setattr(
        run_module, "publish_workbooks",
        lambda *a: pytest.fail("reddedilen aşama yayınlamamalı"),
        raising=False)

    with pytest.raises(RuntimeError, match=expected_message):
        run_module._stage_and_publish(
            stage1, stage2, stage3, staged_forecast, ("fingerprint",),
            data, staging_dir, output_dir)

    assert official_plan.read_bytes() == b"old-plan"
    assert official_forecast.read_bytes() == b"old-forecast"


# ---------------------------------------------------------------------------
# Task 8: Stage 1 entry gate, Stage 2 entry gate, staged pipeline tests
# ---------------------------------------------------------------------------

def _make_stage1_decision(monkeypatch):
    """Build a Stage1Decision that exactly matches the accepted constants."""
    monkeypatch.setattr(run_module, "STAGE1_SEGMENTS", 1092)
    monkeypatch.setattr(run_module, "STAGE1_PHYSICAL_ROUTES", 1092)
    monkeypatch.setattr(run_module, "STAGE1_RENTED_ROUTES", 126)
    monkeypatch.setattr(run_module, "STAGE1_SPOT_ROUTES", 966)
    monkeypatch.setattr(run_module, "STAGE1_PLAN_ROWS", 3167)
    monkeypatch.setattr(run_module, "STAGE1_VEHICLE_COST",
                        Decimal("12510401.245833337"))
    monkeypatch.setattr(run_module, "STAGE1_SLA_PENALTY",
                        Decimal("2169783.600000002"))
    monkeypatch.setattr(run_module, "STAGE1_TOTAL_COST",
                        Decimal("14680184.845833339"))
    monkeypatch.setattr(run_module, "STAGE1_GLOBAL_SAVING",
                        Decimal("1800774.926388895"))
    monkeypatch.setattr(run_module, "STAGE1_DONORS_CONSIDERED", 1003)
    monkeypatch.setattr(run_module, "STAGE1_MOVES_ACCEPTED", 177)
    monkeypatch.setattr(run_module, "STAGE1_PARTS_MOVED", 394)
    monkeypatch.setattr(run_module, "STAGE1_DESI_MOVED", 59852)
    monkeypatch.setattr(run_module, "STAGE1_SPOT_REMOVED", 177)
    monkeypatch.setattr(run_module, "STAGE1_LOCAL_SAVING",
                        Decimal("1800774.926388888876856333333"))

    baseline_eval = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=Decimal("15460592.572222233"),
            sla_penalty=Decimal("1020367.2000000012"),
            total_cost=Decimal("16480959.772222234"),
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * 3167, columns=["A"]),
        legs=[SimpleNamespace(kind="Kiralık", vtype="Tır", desi=0)] * 126
             + [SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=0)] * 966,
    )
    candidate_eval = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=Decimal("12510401.245833337"),
            sla_penalty=Decimal("2169783.600000002"),
            total_cost=Decimal("14680184.845833339"),
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * 3167, columns=["A"]),
        legs=[SimpleNamespace(kind="Kiralık", vtype="Tır", desi=0)] * 126
             + [SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=0)] * 966,
    )
    metrics = RepairMetrics(
        donors_considered=1003,
        moves_accepted=177,
        parts_moved=394,
        desi_moved=59852,
        spot_legs_removed=177,
        local_saving_tl=Decimal("1800774.926388888876856333333"),
    )
    saving = (Decimal("16480959.772222234")
              - Decimal("14680184.845833339"))
    decision = Stage1Decision(
        baseline=baseline_eval,
        candidate=candidate_eval,
        selected=candidate_eval,
        repair_metrics=metrics,
        accepted=True,
        saving_tl=saving,
    )

    data = SimpleNamespace(
        vehicles={"Kamyonet": SimpleNamespace(capacity_desi=10000)})

    # Patch physical_routes to return direct-only routes (no chains)
    routes = []
    for leg in candidate_eval.legs:
        routes.append([leg])
    monkeypatch.setattr(run_module, "physical_routes",
                        lambda legs: routes)
    # Stub plan frames carry no template columns; fingerprint identity is
    # covered by the real artifact tests, so a marker keeps these seams pure.
    monkeypatch.setattr(
        run_module, "plan_fingerprint",
        lambda frame: ("fingerprint", id(frame)), raising=False)

    return decision, data


def _make_stage2_decision(stage1_decision, *, accepted=True,
                          saving=Decimal("10.00"), selected=None,
                          baseline=None):
    """Build a MilkRunDecision whose reported saving matches its referee."""
    stage1_selected = stage1_decision.selected
    stage1_total = Decimal(str(stage1_selected.result.total_cost))
    candidate = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=Decimal(
                str(stage1_selected.result.vehicle_cost)) - saving,
            sla_penalty=Decimal(str(stage1_selected.result.sla_penalty)),
            total_cost=stage1_total - saving,
            violations=[],
        ),
        plan_frame=pd.DataFrame([{"A": 2}] * 3167, columns=["A"]),
        legs=list(stage1_selected.legs),
    )
    if baseline is None:
        baseline = stage1_selected
    if selected is None:
        selected = candidate if accepted else baseline
    return SimpleNamespace(
        baseline=baseline,
        candidate=candidate,
        selected=selected,
        metrics=MilkRunMetrics(
            groups_considered=93,
            pairs_evaluated=5426,
            chains_accepted=308,
            source_vehicles_replaced=616,
            segments_created=616,
            parts_consolidated=2084,
            desi_consolidated=1666745,
            local_saving_tl=saving,
            chain_type_mix=(("Kamyon", 275), ("Kamyonet", 33)),
        ),
        accepted=accepted,
        saving_tl=saving,
    )


def _make_stage3_decision(stage2_decision, *, accepted=True,
                          saving=Decimal("60000.00"), selected=None,
                          baseline=None, local_saving=None):
    """Build a PickupDecision whose reported saving matches its referee."""
    stage2_selected = stage2_decision.selected
    stage2_total = Decimal(str(stage2_selected.result.total_cost))
    candidate = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=Decimal(
                str(stage2_selected.result.vehicle_cost)) - saving,
            sla_penalty=Decimal(str(stage2_selected.result.sla_penalty)),
            total_cost=stage2_total - saving,
            violations=[],
        ),
        plan_frame=pd.DataFrame([{"A": 3}] * 3167, columns=["A"]),
        legs=list(stage2_selected.legs),
    )
    if baseline is None:
        baseline = stage2_selected
    if selected is None:
        selected = candidate if accepted else baseline
    return SimpleNamespace(
        baseline=baseline,
        candidate=candidate,
        selected=selected,
        metrics=PickupMetrics(
            routes_considered=227,
            rented_routes_skipped=126,
            donors_available=340,
            pairs_examined=135660,
            profitable_candidates=56,
            pickups_accepted=28,
            rejected_by_ledger=0,
            donor_vehicles_removed=28,
            parts_picked_up=82,
            desi_picked_up=65754,
            local_saving_tl=saving if local_saving is None else local_saving,
            pickup_type_mix=(("Kamyon", 11), ("Kamyonet", 17)),
        ),
        accepted=accepted,
        saving_tl=saving,
    )


def test_stage1_entry_accepts_only_complete_report_values(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    run_module._require_stage1_entry(decision, data)


def test_stage1_entry_requires_accepted_selected_candidate(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    rejected = Stage1Decision(
        baseline=decision.baseline,
        candidate=decision.candidate,
        selected=decision.baseline,
        repair_metrics=decision.repair_metrics,
        accepted=False,
        saving_tl=decision.saving_tl,
    )
    with pytest.raises(RuntimeError, match="kabul"):
        run_module._require_stage1_entry(rejected, data)


@pytest.mark.parametrize(
    "field",
    ["vehicle_cost", "sla_penalty", "total_cost", "global_saving"],
)
def test_stage1_entry_rejects_each_raw_cost_difference(monkeypatch, field):
    decision, data = _make_stage1_decision(monkeypatch)
    eval_ns = decision.selected.result
    original = getattr(eval_ns, field if field != "global_saving" else "total_cost",
                       None)
    setattr(eval_ns, field if field != "global_saving" else "total_cost",
            Decimal(str(999999999)))
    with pytest.raises(RuntimeError, match=field):
        run_module._require_stage1_entry(decision, data)
    setattr(eval_ns, field if field != "global_saving" else "total_cost", original)


@pytest.mark.parametrize(
    "field",
    ["donors_considered", "moves_accepted", "parts_moved",
     "desi_moved", "spot_legs_removed"],
)
def test_stage1_entry_rejects_each_count_and_repair_metric_difference(
        monkeypatch, field):
    decision, data = _make_stage1_decision(monkeypatch)
    rm = decision.repair_metrics
    original = getattr(rm, field)
    bad = RepairMetrics(
        donors_considered=rm.donors_considered + (1 if field == "donors_considered" else 0),
        moves_accepted=rm.moves_accepted + (1 if field == "moves_accepted" else 0),
        parts_moved=rm.parts_moved + (1 if field == "parts_moved" else 0),
        desi_moved=rm.desi_moved + (1 if field == "desi_moved" else 0),
        spot_legs_removed=rm.spot_legs_removed + (1 if field == "spot_legs_removed" else 0),
        local_saving_tl=rm.local_saving_tl,
    )
    decision = Stage1Decision(
        baseline=decision.baseline,
        candidate=decision.candidate,
        selected=decision.selected,
        repair_metrics=bad,
        accepted=decision.accepted,
        saving_tl=decision.saving_tl,
    )
    with pytest.raises(RuntimeError, match=field):
        run_module._require_stage1_entry(decision, data)


def test_stage1_entry_requires_direct_only_physical_routes(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)

    class FakeChain:
        vtype = "Tır"
        kind = "Spot"

    chain_leg = FakeChain()
    monkeypatch.setattr(run_module, "physical_routes",
                        lambda legs: [[chain_leg]])
    with pytest.raises(RuntimeError, match="zincir"):
        run_module._require_stage1_entry(decision, data)


def test_stage1_entry_aggregates_independent_mismatches(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    rm = decision.repair_metrics
    bad_rm = RepairMetrics(
        donors_considered=rm.donors_considered + 1,
        moves_accepted=rm.moves_accepted + 1,
        parts_moved=rm.parts_moved + 1,
        desi_moved=rm.desi_moved + 1,
        spot_legs_removed=rm.spot_legs_removed + 1,
        local_saving_tl=rm.local_saving_tl,
    )
    decision = Stage1Decision(
        baseline=decision.baseline,
        candidate=decision.candidate,
        selected=decision.selected,
        repair_metrics=bad_rm,
        accepted=decision.accepted,
        saving_tl=decision.saving_tl,
    )
    with pytest.raises(RuntimeError, match="donors_considered") as exc_info:
        run_module._require_stage1_entry(decision, data)
    msg = str(exc_info.value)
    assert "moves_accepted" in msg
    assert "parts_moved" in msg
    assert "desi_moved" in msg
    assert "spot_legs_removed" in msg


def test_main_order_runs_every_stage_behind_its_own_gate(
        monkeypatch, tmp_path):
    monkeypatch.setattr(run_module, "OUT_DIR", tmp_path)
    events = []
    monkeypatch.setattr(run_module, "load_all",
                        lambda: SimpleNamespace(demand=object()))
    monkeypatch.setattr(run_module, "forecast_horizon", lambda *a: object())
    monkeypatch.setattr(run_module, "to_forecast_frame", lambda f: pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)]))
    monkeypatch.setattr(run_module, "forecast_fingerprint", lambda f: ("fp",))
    monkeypatch.setattr(run_module, "write_forecast_xlsx",
                        lambda *a: tmp_path / "f.xlsx")
    monkeypatch.setattr(run_module.pd, "read_excel", lambda p: pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)]))
    monkeypatch.setattr(run_module, "prepare_frame", lambda f: object())
    monkeypatch.setattr(run_module, "build_plan", lambda *a: [])
    monkeypatch.setattr(run_module, "physical_routes", lambda l: [])

    s0_decision = _stage_decision(accepted=True)
    s1_decision = _stage_decision(accepted=True)
    s2_decision = SimpleNamespace(
        baseline=s1_decision.selected,
        candidate=s1_decision.selected,
        selected=s1_decision.selected,
        metrics=SimpleNamespace(),
        accepted=True,
        saving_tl=Decimal("10.00"),
    )
    s3_decision = SimpleNamespace(
        baseline=s1_decision.selected,
        candidate=s1_decision.selected,
        selected=s1_decision.selected,
        metrics=SimpleNamespace(),
        accepted=True,
        saving_tl=Decimal("60000.00"),
    )
    data_obj = SimpleNamespace(vehicles={})

    def fake_s0(legs, forecast, data):
        events.append("stage0")
        return s0_decision

    def fake_s1(baseline, forecast, data):
        events.append("stage1")
        return s1_decision

    def fake_s2(baseline, forecast, data):
        events.append("stage2")
        return s3_decision

    def fake_stage0_gate(*a):
        events.append("gate0")

    def fake_stage1_gate(*a):
        events.append("gate1")

    def fake_stage2_gate(*a):
        events.append("gate2")

    def fake_stage3_gate(*a):
        events.append("gate3")

    def fake_publish(*a):
        events.append("publish")

    monkeypatch.setattr(run_module, "run_same_lane_stage", fake_s0)
    monkeypatch.setattr(run_module, "run_milk_run_stage", fake_s1)
    monkeypatch.setattr(run_module, "run_pickup_stage", fake_s2)
    monkeypatch.setattr(run_module, "_require_stage0_entry", fake_stage0_gate)
    monkeypatch.setattr(run_module, "_require_stage1_entry", fake_stage1_gate)
    monkeypatch.setattr(run_module, "_require_stage2_entry", fake_stage2_gate)
    monkeypatch.setattr(
        run_module, "_require_stage2_result", lambda *a: None)
    monkeypatch.setattr(run_module, "_require_stage3_entry", fake_stage3_gate)
    monkeypatch.setattr(
        run_module, "_require_stage3_result", lambda *a: None)
    monkeypatch.setattr(run_module, "_print_pipeline_metrics",
                        lambda *a: None)
    monkeypatch.setattr(run_module, "_stage_and_publish", fake_publish)

    run_module.main()

    assert events == [
        "stage0", "gate0", "gate1", "stage1", "gate2",
        "stage2", "gate3", "publish",
    ]


def test_stage1_rejection_never_calls_stage2_or_publication(
        monkeypatch, tmp_path):
    monkeypatch.setattr(run_module, "OUT_DIR", tmp_path)
    events = []
    monkeypatch.setattr(run_module, "load_all",
                        lambda: SimpleNamespace(demand=object()))
    monkeypatch.setattr(run_module, "forecast_horizon", lambda *a: object())
    monkeypatch.setattr(run_module, "to_forecast_frame", lambda f: pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)]))
    monkeypatch.setattr(run_module, "forecast_fingerprint", lambda f: ("fp",))
    monkeypatch.setattr(run_module, "write_forecast_xlsx",
                        lambda *a: tmp_path / "f.xlsx")
    monkeypatch.setattr(run_module.pd, "read_excel", lambda p: pd.DataFrame([
        _row("D00001", H_START, "09:00", "A", "B", 1)]))
    monkeypatch.setattr(run_module, "prepare_frame", lambda f: object())
    monkeypatch.setattr(run_module, "build_plan", lambda *a: [])
    monkeypatch.setattr(run_module, "physical_routes", lambda l: [])

    s0_decision = _stage_decision(accepted=True)
    s1_rejected = _stage_decision(accepted=False, saving=Decimal("0.50"))

    def fake_s0(legs, forecast, data):
        events.append("stage0")
        return s0_decision

    def fake_s1(baseline, forecast, data):
        events.append("stage1")
        return s1_rejected

    def fake_stage0_gate(*a):
        events.append("gate0")

    def fake_stage1_gate(*a):
        events.append("gate1")
        raise RuntimeError("Stage 1 rejected")

    def fake_publish(*a):
        events.append("publish")

    monkeypatch.setattr(run_module, "run_same_lane_stage", fake_s0)
    monkeypatch.setattr(run_module, "run_milk_run_stage", fake_s1)
    monkeypatch.setattr(run_module, "_require_stage0_entry", fake_stage0_gate)
    monkeypatch.setattr(run_module, "_require_stage1_entry", fake_stage1_gate)
    monkeypatch.setattr(run_module, "_print_pipeline_metrics",
                        lambda *a: None)
    monkeypatch.setattr(run_module, "_stage_and_publish", fake_publish)

    with pytest.raises(RuntimeError, match="Stage 1 rejected"):
        run_module.main()

    assert events == ["stage0", "gate0", "gate1"]
    assert "stage2" not in events
    assert "publish" not in events


def test_stage2_entry_accepts_exact_stage1_selected_baseline(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    run_module._require_stage2_entry(decision, _make_stage2_decision(decision))


def test_stage2_entry_requires_stage1_selected_baseline(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    look_alike = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=decision.selected.result.vehicle_cost,
            sla_penalty=decision.selected.result.sla_penalty,
            total_cost=decision.selected.result.total_cost,
            violations=[],
        ),
        plan_frame=decision.selected.plan_frame,
        legs=decision.selected.legs,
    )
    assert look_alike is not decision.selected
    milk_decision = _make_stage2_decision(decision, baseline=look_alike)
    with pytest.raises(RuntimeError, match="baseline"):
        run_module._require_stage2_entry(decision, milk_decision)


def test_stage2_entry_requires_acceptance_candidate_selection_and_raw_saving(
        monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)

    # 1) not accepted
    with pytest.raises(RuntimeError, match="kabul"):
        run_module._require_stage2_entry(
            decision, _make_stage2_decision(decision, accepted=False))

    # 2) selected is not candidate
    with pytest.raises(RuntimeError, match="seçim"):
        run_module._require_stage2_entry(
            decision,
            _make_stage2_decision(decision, selected=decision.selected))

    # 3) saving < 1 TL
    with pytest.raises(RuntimeError, match="tasarruf"):
        run_module._require_stage2_entry(
            decision, _make_stage2_decision(decision, saving=Decimal("0.50")))


def test_stage2_entry_requires_reported_saving_to_match_referee(monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(decision)
    lying = SimpleNamespace(
        baseline=milk_decision.baseline,
        candidate=milk_decision.candidate,
        selected=milk_decision.selected,
        metrics=milk_decision.metrics,
        accepted=True,
        saving_tl=Decimal("2842495.53"),
    )
    with pytest.raises(RuntimeError, match="hakem farkı"):
        run_module._require_stage2_entry(decision, lying)


def test_stage2_rejection_never_writes_or_publishes(tmp_path, monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(
        decision, accepted=False, saving=Decimal("0.50"))
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "out"
    staging_dir.mkdir()
    output_dir.mkdir()
    events = []

    def fake_write(*a):
        events.append("write")
        return a[1]

    def fake_verify(*a, **kw):
        return SimpleNamespace(total_cost=Decimal("0"))

    def fake_publish(*a):
        events.append("publish")

    monkeypatch.setattr(run_module, "write_plan_xlsx", fake_write)
    monkeypatch.setattr(run_module, "verify_plan_artifact", fake_verify,
                        raising=False)
    monkeypatch.setattr(run_module, "publish_workbooks", fake_publish,
                        raising=False)

    with pytest.raises(RuntimeError, match="Stage 2 reddedildi"):
        run_module._stage_and_publish(
            decision, milk_decision, _make_stage3_decision(milk_decision),
            staging_dir / "forecast.xlsx", ("fp",),
            data, staging_dir, output_dir)

    assert "write" not in events
    assert "publish" not in events


def test_stage3_artifacts_verify_stage2_baseline_before_selected(
        tmp_path, monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(decision)
    pickup_decision = _make_stage3_decision(milk_decision)
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "out"
    staging_dir.mkdir()
    output_dir.mkdir()
    events = []

    def fake_write(frame, path, data):
        events.append(f"write-{path.name}")
        path.write_bytes(b"x")
        return path

    def fake_verify(plan_path, forecast_path, data, **kw):
        events.append(f"verify-{plan_path.name}")
        return SimpleNamespace(
            total_cost=(milk_decision.selected.result.total_cost
                        if plan_path.name == "Stage2-baseline.xlsx"
                        else pickup_decision.selected.result.total_cost))

    def fake_publish(*a):
        events.append("publish")

    monkeypatch.setattr(run_module, "write_plan_xlsx", fake_write)
    monkeypatch.setattr(run_module, "verify_plan_artifact", fake_verify,
                        raising=False)
    monkeypatch.setattr(run_module, "publish_workbooks", fake_publish,
                        raising=False)

    run_module._stage_and_publish(
        decision, milk_decision, pickup_decision,
        staging_dir / "forecast.xlsx", ("fp",),
        data, staging_dir, output_dir)

    assert events == [
        "write-Stage2-baseline.xlsx",
        "verify-Stage2-baseline.xlsx",
        "write-Tasima-plani.xlsx",
        "verify-Tasima-plani.xlsx",
        "publish",
    ]


def test_staged_baseline_is_stage2_selected_not_stage1(
        tmp_path, monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(decision)
    pickup_decision = _make_stage3_decision(milk_decision)
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "out"
    staging_dir.mkdir()
    output_dir.mkdir()
    written_frames = []

    def fake_write(frame, path, data):
        written_frames.append((path.name, frame))
        path.write_bytes(b"x")
        return path

    def fake_verify(plan_path, *a, **kw):
        return SimpleNamespace(
            total_cost=(milk_decision.selected.result.total_cost
                        if plan_path.name == "Stage2-baseline.xlsx"
                        else pickup_decision.selected.result.total_cost))

    monkeypatch.setattr(run_module, "write_plan_xlsx", fake_write)
    monkeypatch.setattr(run_module, "verify_plan_artifact", fake_verify,
                        raising=False)
    monkeypatch.setattr(run_module, "publish_workbooks", lambda *a: None,
                        raising=False)

    run_module._stage_and_publish(
        decision, milk_decision, pickup_decision,
        staging_dir / "forecast.xlsx", ("fp",),
        data, staging_dir, output_dir)

    assert written_frames[0] == (
        "Stage2-baseline.xlsx", milk_decision.selected.plan_frame)
    assert written_frames[1] == (
        "Tasima-plani.xlsx", pickup_decision.selected.plan_frame)


def test_stage3_artifact_saving_under_the_floor_never_publishes(
        tmp_path, monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(decision)
    pickup_decision = _make_stage3_decision(milk_decision)
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "out"
    staging_dir.mkdir()
    output_dir.mkdir()
    output_dir / "Tasima-plani.xlsx"
    (output_dir / "Tasima-plani.xlsx").write_bytes(b"old")
    publish_calls = []
    verify_calls = []

    def fake_write(frame, path, data):
        path.write_bytes(b"x")
        return path

    # One kuruş short of the pinned Stage 3 floor: the in-memory decision is
    # fine, but the independently refereed artifacts must still refuse.
    baseline_total = Decimal(str(milk_decision.selected.result.total_cost))
    candidate_total = baseline_total - (
        run_module.STAGE3_MIN_SAVING_TL - Decimal("0.01"))

    def fake_verify(plan_path, forecast_path, data, **kw):
        verify_calls.append(plan_path.name)
        if len(verify_calls) == 1:
            return SimpleNamespace(total_cost=baseline_total)
        return SimpleNamespace(total_cost=candidate_total)

    monkeypatch.setattr(run_module, "write_plan_xlsx", fake_write)
    monkeypatch.setattr(run_module, "verify_plan_artifact", fake_verify,
                        raising=False)
    monkeypatch.setattr(run_module, "publish_workbooks",
                        lambda *a: publish_calls.append(a), raising=False)

    with pytest.raises(RuntimeError, match="49999.99"):
        run_module._stage_and_publish(
            decision, milk_decision, pickup_decision,
            staging_dir / "forecast.xlsx", ("fp",),
            data, staging_dir, output_dir)

    assert publish_calls == []
    assert verify_calls == [
        "Stage2-baseline.xlsx", "Tasima-plani.xlsx"]


def test_success_uses_existing_plan_first_publication(
        tmp_path, monkeypatch):
    decision, data = _make_stage1_decision(monkeypatch)
    milk_decision = _make_stage2_decision(decision)
    pickup_decision = _make_stage3_decision(milk_decision)
    staging_dir = tmp_path / "staging"
    output_dir = tmp_path / "out"
    staging_dir.mkdir()
    output_dir.mkdir()
    publish_calls = []

    def fake_write(frame, path, data):
        path.write_bytes(b"x")
        return path

    def fake_verify(plan_path, *a, **kw):
        return SimpleNamespace(
            total_cost=(milk_decision.selected.result.total_cost
                        if plan_path.name == "Stage2-baseline.xlsx"
                        else pickup_decision.selected.result.total_cost))

    def fake_publish(staged_plan, staged_forecast,
                     plan_dest, forecast_dest):
        publish_calls.append(("plan", plan_dest))
        publish_calls.append(("forecast", forecast_dest))

    monkeypatch.setattr(run_module, "write_plan_xlsx", fake_write)
    monkeypatch.setattr(run_module, "verify_plan_artifact", fake_verify,
                        raising=False)
    monkeypatch.setattr(run_module, "publish_workbooks", fake_publish,
                        raising=False)

    run_module._stage_and_publish(
        decision, milk_decision, pickup_decision,
        staging_dir / "forecast.xlsx", ("fp",),
        data, staging_dir, output_dir)

    assert publish_calls[0] == ("plan", output_dir / "Tasima-plani.xlsx")
    assert publish_calls[1] == ("forecast", output_dir / "Talep-tahmini.xlsx")


# ---------------------------------------------------------------------------
# Stage 2 frozen-result gate: the stage that produces the submitted workbook
# is pinned to its accepted values exactly like Stage 0 and Stage 1.
# ---------------------------------------------------------------------------

def _make_stage2_result_case(monkeypatch):
    """Build a Stage1/Stage2 pair that exactly matches the Stage 2 constants.

    The fixture is derived from ``run.STAGE2_*`` on purpose: its job is to prove
    the GATE LOGIC rejects drift, not to re-assert the constants. The constants
    themselves are verified by the real ``python run.py`` and by the independent
    reconstruction script, so deriving here keeps the suite correct when the
    accepted result legitimately moves (e.g. a MAX_CHAIN_STOPS change).
    """
    stage1_total = run_module.STAGE1_TOTAL_COST
    stage2_total = run_module.STAGE2_TOTAL_COST

    chain_legs = []
    chain_routes = []
    chain_id = 0
    for size, count in run_module.STAGE2_CHAIN_SIZE_MIX:
        for _ in range(count):
            route = [
                SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=0,
                                chain_id=chain_id, chain_seq=seq)
                for seq in range(size)
            ]
            chain_legs.extend(route)
            chain_routes.append(route)
            chain_id += 1

    chain_segments = len(chain_legs)
    direct_total = run_module.STAGE2_SEGMENTS - chain_segments
    rented = run_module.STAGE2_RENTED_ROUTES
    direct_legs = [
        SimpleNamespace(kind="Kiralık", vtype="Tır", desi=0,
                        chain_id=None, chain_seq=0)
        for _ in range(rented)
    ] + [
        SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=0,
                        chain_id=None, chain_seq=0)
        for _ in range(direct_total - rented)
    ]
    routes = [[leg] for leg in direct_legs] + chain_routes
    legs = direct_legs + chain_legs

    # The fixture must satisfy the same identities the real plan does.
    assert len(legs) == run_module.STAGE2_SEGMENTS
    assert len(routes) == run_module.STAGE2_PHYSICAL_ROUTES
    assert chain_segments == run_module.STAGE2_SEGMENTS_CREATED
    assert len(chain_routes) == run_module.STAGE2_CHAINS_ACCEPTED
    assert sum(1 for r in routes if r[0].kind == "Spot") == (
        run_module.STAGE2_SPOT_ROUTES)

    stage1_selected = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=run_module.STAGE1_VEHICLE_COST,
            sla_penalty=run_module.STAGE1_SLA_PENALTY,
            total_cost=stage1_total,
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * run_module.STAGE1_PLAN_ROWS, columns=["A"]),
        legs=[],
    )
    stage1 = SimpleNamespace(selected=stage1_selected)

    candidate = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=run_module.STAGE2_VEHICLE_COST,
            sla_penalty=run_module.STAGE2_SLA_PENALTY,
            total_cost=stage2_total,
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * run_module.STAGE2_PLAN_ROWS, columns=["A"]),
        legs=legs,
    )
    metrics = MilkRunMetrics(
        groups_considered=run_module.STAGE2_GROUPS_CONSIDERED,
        pairs_evaluated=run_module.STAGE2_PAIRS_EVALUATED,
        chains_accepted=run_module.STAGE2_CHAINS_ACCEPTED,
        source_vehicles_replaced=run_module.STAGE2_SOURCE_VEHICLES_REPLACED,
        segments_created=run_module.STAGE2_SEGMENTS_CREATED,
        parts_consolidated=run_module.STAGE2_PARTS_CONSOLIDATED,
        desi_consolidated=run_module.STAGE2_DESI_CONSOLIDATED,
        local_saving_tl=run_module.STAGE2_LOCAL_SAVING,
        chain_type_mix=run_module.STAGE2_CHAIN_TYPE_MIX,
        triples_evaluated=run_module.STAGE2_TRIPLES_EVALUATED,
        chain_size_mix=run_module.STAGE2_CHAIN_SIZE_MIX,
    )
    stage2 = SimpleNamespace(
        baseline=stage1_selected,
        candidate=candidate,
        selected=candidate,
        metrics=metrics,
        accepted=True,
        saving_tl=stage1_total - stage2_total,
    )

    monkeypatch.setattr(run_module, "physical_routes", lambda legs: routes)
    data = SimpleNamespace(
        vehicles={"Kamyonet": SimpleNamespace(capacity_desi=5600)})
    return stage1, stage2, data


def test_stage2_result_accepts_the_exact_accepted_run(monkeypatch):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    run_module._require_stage2_result(stage1, stage2, data)


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("vehicle_cost", "stage2_vehicle_cost"),
        ("sla_penalty", "stage2_sla_penalty"),
        ("total_cost", "stage2_total_cost"),
    ],
)
def test_stage2_result_rejects_any_raw_cost_drift(monkeypatch, field, label):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    current = getattr(stage2.selected.result, field)
    setattr(stage2.selected.result, field, current + Decimal("0.000000001"))
    with pytest.raises(RuntimeError, match=label):
        run_module._require_stage2_result(stage1, stage2, data)


@pytest.mark.parametrize(
    "field",
    ["groups_considered", "pairs_evaluated", "triples_evaluated",
     "chains_accepted", "source_vehicles_replaced", "segments_created",
     "parts_consolidated", "desi_consolidated"],
)
def test_stage2_result_rejects_each_metric_drift(monkeypatch, field):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    stage2.metrics = replace(stage2.metrics, **{field: getattr(
        stage2.metrics, field) + 1})
    with pytest.raises(RuntimeError, match=field):
        run_module._require_stage2_result(stage1, stage2, data)


def test_stage2_result_rejects_a_collapsed_milk_run(monkeypatch):
    """Losing the chains must fail loudly rather than publish quietly."""
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    stage2.selected.result.total_cost = Decimal("14680184.845833339")
    stage2.metrics = replace(
        stage2.metrics, chains_accepted=0, chain_size_mix=(),
        source_vehicles_replaced=0, segments_created=0,
        local_saving_tl=Decimal("0"))
    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage2_result(stage1, stage2, data)
    message = str(caught.value)
    assert "stage2_total_cost" in message
    assert "chains_accepted" in message
    assert "chain_size_mix" in message
    assert "stage2_global_saving" in message


def test_stage2_result_rejects_a_rented_or_tir_chain(monkeypatch):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    routes = run_module.physical_routes(stage2.selected.legs)
    chain = next(route for route in routes if len(route) > 1)
    chain[0].kind = "Kiralık"
    with pytest.raises(RuntimeError, match="Q&A 11.1"):
        run_module._require_stage2_result(stage1, stage2, data)


def test_stage2_result_rejects_a_chain_longer_than_the_cap(monkeypatch):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    routes = run_module.physical_routes(stage2.selected.legs)
    chain = next(route for route in routes
                 if len(route) == run_module.MAX_CHAIN_STOPS)
    chain.append(SimpleNamespace(kind="Spot", vtype="Kamyonet", desi=0,
                                 chain_id=chain[0].chain_id, chain_seq=9))
    with pytest.raises(RuntimeError, match="zincir uzunluğu"):
        run_module._require_stage2_result(stage1, stage2, data)


def test_stage2_result_rejects_a_mixed_vehicle_type_chain(monkeypatch):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    routes = run_module.physical_routes(stage2.selected.legs)
    chain = next(route for route in routes if len(route) > 1)
    chain[1].vtype = "Kamyon"
    with pytest.raises(RuntimeError, match="araç türü değişiyor"):
        run_module._require_stage2_result(stage1, stage2, data)


def test_stage2_result_aggregates_every_independent_mismatch(monkeypatch):
    stage1, stage2, data = _make_stage2_result_case(monkeypatch)
    stage2.selected.plan_frame = pd.DataFrame([{"A": 1}] * 10, columns=["A"])
    stage2.metrics = replace(
        stage2.metrics, groups_considered=0, pairs_evaluated=0,
        chain_type_mix=(), local_saving_tl=Decimal("1"))
    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage2_result(stage1, stage2, data)
    message = str(caught.value)
    for label in ("stage2_plan_rows", "groups_considered", "pairs_evaluated",
                  "chain_type_mix", "stage2_local_saving"):
        assert label in message


# ---------------------------------------------------------------------------
# Stage 3 gates: mid-route pickup is now the stage that publishes, so its
# entry conditions and its frozen result are pinned like every stage before.
# ---------------------------------------------------------------------------

def test_stage3_entry_accepts_the_exact_accepted_run(monkeypatch):
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    run_module._require_stage3_entry(stage2, _make_stage3_decision(stage2))


def test_stage3_entry_requires_stage2_selected_baseline(monkeypatch):
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    look_alike = SimpleNamespace(
        result=stage2.selected.result,
        plan_frame=stage2.selected.plan_frame,
        legs=stage2.selected.legs,
    )
    with pytest.raises(RuntimeError, match="baseline identity mismatch"):
        run_module._require_stage3_entry(
            stage2, _make_stage3_decision(stage2, baseline=look_alike))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"accepted": False}, "Stage 3 kabul değil"),
        ({"saving": Decimal("49999.99")}, "< 50000.00"),
    ],
)
def test_stage3_entry_rejects_a_rejected_or_undersized_run(
        monkeypatch, kwargs, message):
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    with pytest.raises(RuntimeError, match=message):
        run_module._require_stage3_entry(
            stage2, _make_stage3_decision(stage2, **kwargs))


def test_stage3_entry_requires_the_candidate_to_be_selected(monkeypatch):
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    with pytest.raises(RuntimeError, match="seçimi aday değil"):
        run_module._require_stage3_entry(
            stage2, _make_stage3_decision(stage2, selected=stage2.selected))


def test_stage3_entry_requires_reported_saving_to_match_referee(monkeypatch):
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    honest = _make_stage3_decision(stage2)
    lying = SimpleNamespace(
        baseline=honest.baseline,
        candidate=honest.candidate,
        selected=honest.selected,
        metrics=honest.metrics,
        accepted=True,
        saving_tl=Decimal("70000.00"),
    )
    with pytest.raises(RuntimeError, match="hakem farkı"):
        run_module._require_stage3_entry(stage2, lying)


def test_stage3_entry_requires_local_saving_to_reconcile_with_referee(
        monkeypatch):
    """The gate that caught every mid-route pickup defect so far.

    The greedy search adds up what each accepted pickup should save; the
    referee measures what the whole plan actually costs. A pickup priced on
    the wrong timestamp, at the wrong tariff, or carrying cargo past its own
    stop makes those two numbers disagree, and nothing else notices.
    """
    decision, _data = _make_stage1_decision(monkeypatch)
    stage2 = _make_stage2_decision(decision)
    with pytest.raises(RuntimeError, match="uzlaşmıyor"):
        run_module._require_stage3_entry(
            stage2,
            _make_stage3_decision(stage2, local_saving=Decimal("60000.000002")))

    # A difference inside the tolerance is the float round-trip, not a defect.
    run_module._require_stage3_entry(
        stage2,
        _make_stage3_decision(stage2, local_saving=Decimal("60000.0000005")))


def _make_stage3_result_case(monkeypatch):
    """Build a Stage2/Stage3 pair that exactly matches the Stage 3 constants.

    Derived from ``run.STAGE3_*`` on purpose: the job here is to prove the
    GATE LOGIC rejects drift. The constants themselves are asserted by the
    real ``python run.py`` and by the full-horizon test in test_pickup.py.
    """
    identifiers = itertools.count(1)

    def part(dest):
        return SimpleNamespace(dest=dest, base_id=f"D{next(identifiers):05d}")

    def leg(kind, vtype, dest, items, chain_id, chain_seq):
        return SimpleNamespace(
            kind=kind, vtype=vtype, origin="H", dest=dest, desi=0,
            items=items, chain_id=chain_id, chain_seq=chain_seq)

    chain_routes = []
    chain_id = 0
    pickups_left = run_module.STAGE3_PICKUPS_ACCEPTED
    for size, count in run_module.STAGE2_CHAIN_SIZE_MIX:
        for _ in range(count):
            parts = [part(f"T{seq}") for seq in range(size)]
            route = [
                leg("Spot", "Kamyonet", f"T{seq}",
                    [(carried, 1) for carried in parts[seq:]], chain_id, seq)
                for seq in range(size)
            ]
            if pickups_left:
                # Cargo taken on at stop 0 and dropped at stop 1: it is absent
                # from the previous segment, so the gate sees exactly one
                # mid-route loading on this route.
                route[1].items = route[1].items + [(part("T1"), 1)]
                pickups_left -= 1
            chain_routes.append(route)
            chain_id += 1
    assert pickups_left == 0

    chain_legs = [segment for route in chain_routes for segment in route]
    direct_count = run_module.STAGE3_SEGMENTS - len(chain_legs)
    rented = run_module.STAGE3_RENTED_ROUTES
    direct_legs = [
        leg("Kiralık", "Tır", "R", [(part("R"), 1)], None, 0)
        for _ in range(rented)
    ] + [
        leg("Spot", "Kamyonet", "S", [(part("S"), 1)], None, 0)
        for _ in range(direct_count - rented)
    ]
    routes = [[single] for single in direct_legs] + chain_routes
    legs = direct_legs + chain_legs

    assert len(legs) == run_module.STAGE3_SEGMENTS
    assert len(routes) == run_module.STAGE3_PHYSICAL_ROUTES
    assert len(chain_routes) == run_module.STAGE3_CHAIN_ROUTES
    assert sum(1 for route in routes if route[0].kind == "Spot") == (
        run_module.STAGE3_SPOT_ROUTES)

    # Tier A leaves chain shapes untouched, so the Stage 2 side of the gate
    # only needs the same chain-length multiset and the right route count.
    stage2_chain_shape = [size
                          for size, count in run_module.STAGE2_CHAIN_SIZE_MIX
                          for _ in range(count)]
    stage2_routes = [
        [object()] for _ in range(run_module.STAGE2_PHYSICAL_ROUTES
                                  - len(stage2_chain_shape))
    ] + [[object()] * size for size in stage2_chain_shape]
    assert len(stage2_routes) == run_module.STAGE2_PHYSICAL_ROUTES

    stage2_selected = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=run_module.STAGE2_VEHICLE_COST,
            sla_penalty=run_module.STAGE2_SLA_PENALTY,
            total_cost=run_module.STAGE2_TOTAL_COST,
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * run_module.STAGE2_PLAN_ROWS, columns=["A"]),
        legs=[],
    )
    stage2 = SimpleNamespace(selected=stage2_selected)

    candidate = SimpleNamespace(
        result=SimpleNamespace(
            vehicle_cost=run_module.STAGE3_VEHICLE_COST,
            sla_penalty=run_module.STAGE3_SLA_PENALTY,
            total_cost=run_module.STAGE3_TOTAL_COST,
            violations=[],
        ),
        plan_frame=pd.DataFrame(
            [{"A": 1}] * run_module.STAGE3_PLAN_ROWS, columns=["A"]),
        legs=legs,
    )
    stage3 = SimpleNamespace(
        baseline=stage2_selected,
        candidate=candidate,
        selected=candidate,
        metrics=PickupMetrics(
            routes_considered=run_module.STAGE3_ROUTES_CONSIDERED,
            rented_routes_skipped=run_module.STAGE3_RENTED_ROUTES_SKIPPED,
            donors_available=run_module.STAGE3_DONORS_AVAILABLE,
            pairs_examined=run_module.STAGE3_PAIRS_EXAMINED,
            profitable_candidates=run_module.STAGE3_PROFITABLE_CANDIDATES,
            pickups_accepted=run_module.STAGE3_PICKUPS_ACCEPTED,
            rejected_by_ledger=run_module.STAGE3_REJECTED_BY_LEDGER,
            donor_vehicles_removed=run_module.STAGE3_DONOR_VEHICLES_REMOVED,
            parts_picked_up=run_module.STAGE3_PARTS_PICKED_UP,
            desi_picked_up=run_module.STAGE3_DESI_PICKED_UP,
            local_saving_tl=run_module.STAGE3_LOCAL_SAVING,
            pickup_type_mix=run_module.STAGE3_PICKUP_TYPE_MIX,
        ),
        accepted=True,
        saving_tl=run_module.STAGE3_GLOBAL_SAVING,
    )

    # The Stage 2 evaluation carries no legs, so the seam can tell the two
    # sides of the gate apart without reaching into run.py.
    monkeypatch.setattr(run_module, "physical_routes",
                        lambda legs: routes if legs else stage2_routes)
    data = SimpleNamespace(
        vehicles={"Kamyonet": SimpleNamespace(capacity_desi=5600)})
    return stage2, stage3, data


def test_stage3_result_accepts_the_exact_accepted_run(monkeypatch):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    run_module._require_stage3_result(stage2, stage3, data)


@pytest.mark.parametrize(
    ("field", "label"),
    [
        ("vehicle_cost", "stage3_vehicle_cost"),
        ("sla_penalty", "stage3_sla_penalty"),
        ("total_cost", "stage3_total_cost"),
    ],
)
def test_stage3_result_rejects_any_raw_cost_drift(monkeypatch, field, label):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    current = getattr(stage3.selected.result, field)
    setattr(stage3.selected.result, field, current + Decimal("0.000000001"))
    with pytest.raises(RuntimeError, match=label):
        run_module._require_stage3_result(stage2, stage3, data)


@pytest.mark.parametrize(
    "field",
    ["routes_considered", "rented_routes_skipped", "donors_available",
     "pairs_examined", "profitable_candidates", "rejected_by_ledger",
     "donor_vehicles_removed", "parts_picked_up", "desi_picked_up"],
)
def test_stage3_result_rejects_each_metric_drift(monkeypatch, field):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    stage3.metrics = replace(
        stage3.metrics, **{field: getattr(stage3.metrics, field) + 1})
    with pytest.raises(RuntimeError, match=field):
        run_module._require_stage3_result(stage2, stage3, data)


def test_stage3_result_rejects_a_collapsed_pickup_search(monkeypatch):
    """Losing the pickups must fail loudly rather than publish quietly."""
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    stage3.selected.result.total_cost = run_module.STAGE2_TOTAL_COST
    stage3.metrics = replace(
        stage3.metrics, pickups_accepted=0, donor_vehicles_removed=0,
        parts_picked_up=0, desi_picked_up=0, pickup_type_mix=(),
        local_saving_tl=Decimal("0"))
    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage3_result(stage2, stage3, data)
    message = str(caught.value)
    for label in ("stage3_total_cost", "pickups_accepted", "pickup_type_mix",
                  "stage3_global_saving", "stage3_local_saving"):
        assert label in message


def test_stage3_result_rejects_a_rented_route_taking_cargo_mid_route(
        monkeypatch):
    """Q&A: 'Kiralık araçlarla uğrama yapılmaz' — checked on the plan itself."""
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    routes = run_module.physical_routes(stage3.selected.legs)
    chain = next(route for route in routes if len(route) > 1)
    for segment in chain:
        segment.kind = "Kiralık"
    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage3_result(stage2, stage3, data)
    message = str(caught.value)
    assert "kiralık rotada rota-ortası yükleme" in message
    assert "stage3_rented_routes" in message


def test_stage3_result_rejects_cargo_dropped_past_its_destination(monkeypatch):
    """A picked-up load that rides past its own stop is a wrong plan."""
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    routes = run_module.physical_routes(stage3.selected.legs)
    chain = next(route for route in routes if len(route) > 2)
    stranded = SimpleNamespace(dest="T1", base_id="D99999")
    chain[-1].items = list(chain[-1].items) + [(stranded, 1)]
    with pytest.raises(RuntimeError,
                       match="D99999: T2 indirme durağı ama nihai varışı T1"):
        run_module._require_stage3_result(stage2, stage3, data)


def test_stage3_result_rejects_a_changed_chain_topology(monkeypatch):
    """Tier A may not lengthen a route; pinned counts alone would allow it."""
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    routes = run_module.physical_routes(stage3.selected.legs)
    two_stop = next(route for route in routes if len(route) == 2)
    grown = SimpleNamespace(
        kind="Spot", vtype="Kamyonet", origin="H", dest="T2", desi=0,
        items=list(two_stop[-1].items), chain_id=two_stop[0].chain_id,
        chain_seq=2)
    two_stop.append(grown)
    with pytest.raises(RuntimeError,
                       match="Tier A rota topolojisini değiştirdi"):
        run_module._require_stage3_result(stage2, stage3, data)


def test_stage3_result_rejects_a_wrong_vehicle_reduction(monkeypatch):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    routes = run_module.physical_routes(stage3.selected.legs)
    routes.append([SimpleNamespace(
        kind="Spot", vtype="Kamyonet", origin="H", dest="S", desi=0,
        items=[(SimpleNamespace(dest="S", base_id="D77777"), 1)],
        chain_id=None, chain_seq=0)])
    with pytest.raises(RuntimeError, match="stage3_vehicles_removed"):
        run_module._require_stage3_result(stage2, stage3, data)


def test_stage3_result_rejects_a_lost_mid_route_pickup(monkeypatch):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    routes = run_module.physical_routes(stage3.selected.legs)
    picked = next(
        route for route in routes
        if len(route) > 1
        and any(id(part) not in {id(other) for other, _d in route[0].items}
                for part, _desi in route[1].items))
    picked[1].items = [
        item for item in picked[1].items
        if id(item[0]) in {id(other) for other, _d in picked[0].items}]
    with pytest.raises(RuntimeError,
                       match="rota-ortası yükleme yapan segment"):
        run_module._require_stage3_result(stage2, stage3, data)


def test_stage3_result_aggregates_every_independent_mismatch(monkeypatch):
    stage2, stage3, data = _make_stage3_result_case(monkeypatch)
    stage3.selected.plan_frame = pd.DataFrame([{"A": 1}] * 10, columns=["A"])
    stage3.metrics = replace(
        stage3.metrics, routes_considered=0, pairs_examined=0,
        pickup_type_mix=(), local_saving_tl=Decimal("1"))
    with pytest.raises(RuntimeError) as caught:
        run_module._require_stage3_result(stage2, stage3, data)
    message = str(caught.value)
    for label in ("stage3_plan_rows", "routes_considered", "pairs_examined",
                  "pickup_type_mix", "stage3_local_saving"):
        assert label in message
