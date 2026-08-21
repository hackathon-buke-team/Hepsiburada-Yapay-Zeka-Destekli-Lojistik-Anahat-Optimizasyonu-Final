from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from src.candidates import Part
from src.data import Lane, VehicleType
from src.optimize import PlannedLeg
from src.schedule import _assign_ids, _fix_handling, to_plan_frame
from src.schemas import FORECAST_COLS, PLAN_COLS
from src.simulator import simulate


BASE_TIME = datetime(2026, 6, 29, 8)


def _part(base_id, desi=100, *, part_id=None, dest="C"):
    return Part(
        part_id=base_id if part_id is None else part_id,
        base_id=base_id,
        desi=desi,
        ready=BASE_TIME,
        deadline=BASE_TIME + timedelta(days=1),
        dest=dest,
    )


def _leg(items=(), *, dep, origin="A", dest="B", kind="Spot",
         vtype="Kamyonet", chain_id=None, chain_seq=0,
         vehicle_id=None, item_ids=None):
    arr = dep + timedelta(hours=1)
    return PlannedLeg(
        kind=kind,
        vtype=vtype,
        origin=origin,
        dest=dest,
        load_start=dep - timedelta(minutes=1),
        dep=dep,
        arr=arr,
        unload_end=arr + timedelta(minutes=1),
        items=list(items),
        vehicle_id=vehicle_id,
        item_ids=[] if item_ids is None else item_ids,
        chain_id=chain_id,
        chain_seq=chain_seq,
    )


def test_chain_segments_share_one_vehicle_id():
    earlier = _leg(
        dep=BASE_TIME, origin="X", dest="Y", vtype="Kamyon")
    chain_first = _leg(
        dep=BASE_TIME + timedelta(hours=2),
        origin="A",
        dest="B",
        vtype="Kamyon",
        chain_id=41,
        chain_seq=0,
    )
    chain_second = _leg(
        dep=BASE_TIME + timedelta(hours=4),
        origin="B",
        dest="C",
        vtype="Kamyon",
        chain_id=41,
        chain_seq=1,
    )
    later = _leg(
        dep=BASE_TIME + timedelta(hours=6),
        origin="Y",
        dest="Z",
        vtype="Kamyon",
    )

    _assign_ids([later, chain_second, earlier, chain_first])

    assert (
        earlier.vehicle_id,
        chain_first.vehicle_id,
        chain_second.vehicle_id,
        later.vehicle_id,
    ) == ("V0001", "V0002", "V0002", "V0003")
    assert [
        (leg.kind, leg.vtype) for leg in (chain_first, chain_second)
    ] == [("Spot", "Kamyon"), ("Spot", "Kamyon")]


def test_same_physical_part_reuses_item_id_and_desi():
    delivered_at_first_stop = _part(
        "D00001", 125, part_id="first-stop", dest="B")
    shared = _part("D00001", 275, part_id="last-stop", dest="C")
    chain_first = _leg(
        [(delivered_at_first_stop, 125), (shared, 275)],
        dep=BASE_TIME + timedelta(hours=1),
        chain_id=7,
        chain_seq=0,
    )
    chain_second = _leg(
        [(shared, 275)],
        dep=BASE_TIME + timedelta(hours=3),
        origin="B",
        dest="C",
        chain_id=7,
        chain_seq=1,
    )

    _assign_ids([chain_second, chain_first])

    assert chain_first.item_ids == ["D00001-1", "D00001-2"]
    assert chain_second.item_ids == ["D00001-2"]
    assert chain_first.items[1][0] is shared
    assert chain_second.items[0][0] is shared
    assert (shared.desi, chain_first.items[1][1],
            chain_second.items[0][1]) == (275, 275, 275)


def test_unique_split_parts_get_one_suffix_each():
    later_split = _part(
        "D00001", 40, part_id="a-later-split", dest="C")
    repeated = _part(
        "D00001", 60, part_id="z-earlier-chain-part", dest="C")
    chain_first = _leg(
        [(repeated, 60)],
        dep=BASE_TIME + timedelta(hours=1),
        chain_id=9,
        chain_seq=0,
    )
    chain_second = _leg(
        [(repeated, 60)],
        dep=BASE_TIME + timedelta(hours=3),
        origin="B",
        dest="C",
        chain_id=9,
        chain_seq=1,
    )
    standalone = _leg(
        [(later_split, 40)],
        dep=BASE_TIME + timedelta(hours=5),
        origin="A",
        dest="C",
    )

    _assign_ids([standalone, chain_second, chain_first])

    assert (
        chain_first.item_ids,
        chain_second.item_ids,
        standalone.item_ids,
    ) == (["D00001-1"], ["D00001-1"], ["D00001-2"])
    assert {
        *chain_first.item_ids,
        *chain_second.item_ids,
        *standalone.item_ids,
    } == {"D00001-1", "D00001-2"}


def test_distinct_equal_part_objects_still_get_distinct_suffixes():
    first = _part("D00003", 100)
    second = _part("D00003", 100)
    assert first == second
    assert first is not second
    leg = _leg(
        [(first, 100), (second, 100)],
        dep=BASE_TIME + timedelta(hours=1),
    )

    _assign_ids([leg])

    assert leg.item_ids == ["D00003-1", "D00003-2"]


def test_single_unique_part_keeps_base_id():
    shared = _part("D00002", 90)
    chain_first = _leg(
        [(shared, 90)],
        dep=BASE_TIME + timedelta(hours=1),
        chain_id=13,
        chain_seq=0,
    )
    chain_second = _leg(
        [(shared, 90)],
        dep=BASE_TIME + timedelta(hours=3),
        origin="B",
        dest="C",
        chain_id=13,
        chain_seq=1,
    )

    _assign_ids([chain_second, chain_first])

    assert chain_first.item_ids == ["D00002"]
    assert chain_second.item_ids == ["D00002"]


def test_direct_vehicle_and_item_order_regression():
    spot_c_part = _part(
        "D00009", 30, part_id="spot-c", dest="D")
    rented_part = _part(
        "D00009", 40, part_id="rented", dest="Z")
    spot_b_part = _part(
        "D00009", 50, part_id="spot-b", dest="C")
    spot_c = _leg(
        [(spot_c_part, 30)],
        dep=BASE_TIME + timedelta(hours=1),
        origin="C",
        dest="D",
    )
    rented = _leg(
        [(rented_part, 40)],
        dep=BASE_TIME + timedelta(hours=3),
        origin="Y",
        dest="Z",
        kind="Kiralık",
    )
    spot_b = _leg(
        [(spot_b_part, 50)],
        dep=BASE_TIME + timedelta(hours=1),
        origin="B",
        dest="C",
    )

    _assign_ids([spot_c, rented, spot_b])

    assert (
        spot_c.vehicle_id,
        rented.vehicle_id,
        spot_b.vehicle_id,
    ) == ("V0003", "V0001", "V0002")
    assert (
        spot_c.item_ids,
        rented.item_ids,
        spot_b.item_ids,
    ) == (["D00009-2"], ["D00009-3"], ["D00009-1"])


def test_malformed_chain_fails_before_any_id_assignment():
    standalone = _leg(
        [(_part("D00011"), 100)],
        dep=BASE_TIME,
        vehicle_id="vehicle-before-1",
        item_ids=["item-before-1"],
    )
    chain_first = _leg(
        [(_part("D00012"), 100)],
        dep=BASE_TIME + timedelta(hours=1),
        chain_id=23,
        chain_seq=0,
        vehicle_id="vehicle-before-2",
        item_ids=["item-before-2"],
    )
    chain_gap = _leg(
        [(_part("D00013"), 100)],
        dep=BASE_TIME + timedelta(hours=2),
        origin="B",
        dest="C",
        chain_id=23,
        chain_seq=2,
        vehicle_id="vehicle-before-3",
        item_ids=["item-before-3"],
    )
    legs = [standalone, chain_gap, chain_first]
    original_item_ids = [leg.item_ids for leg in legs]

    with pytest.raises(ValueError, match="chain_seq"):
        _assign_ids(legs)

    assert [leg.vehicle_id for leg in legs] == [
        "vehicle-before-1",
        "vehicle-before-3",
        "vehicle-before-2",
    ]
    assert [leg.item_ids for leg in legs] == [
        ["item-before-1"],
        ["item-before-3"],
        ["item-before-2"],
    ]
    assert all(
        leg.item_ids is original
        for leg, original in zip(legs, original_item_ids)
    )


def _schedule_data(handling_cap=None):
    one_hour = {"Kamyonet": 1.0, "Tır": 1.0}
    lanes = {
        ("A", "B"): Lane("A", "B", 60, dict(one_hour), 1),
        ("B", "C"): Lane("B", "C", 60, dict(one_hour), 1),
        ("A", "C"): Lane(
            "A", "C", 120, {"Kamyonet": 2.0, "Tır": 2.0}, 1),
    }
    vehicles = {
        name: VehicleType(name, 20_000, 0.0, 0.0, 0.0, 0.0)
        for name in ("Kamyonet", "Tır")
    }
    return SimpleNamespace(
        lanes=lanes,
        vehicles=vehicles,
        rentals=[],
        handling_cap=(handling_cap or {
            "A": 100_000, "B": 100_000, "C": 100_000,
        }),
        tir_cap={"A": 100, "B": 100, "C": 100},
    )


def _chain_part(part_id, desi, dest, *, deadline=None):
    ready = datetime(2026, 6, 29, 7)
    return Part(
        part_id=part_id,
        base_id=part_id,
        desi=desi,
        ready=ready,
        deadline=(deadline or ready + timedelta(days=1)),
        dest=dest,
    )


def _pair_chain():
    deadline = datetime(2026, 6, 29, 8, 30)
    to_b = _chain_part("D00001", 100, "B", deadline=deadline)
    to_c = _chain_part("D00002", 200, "C", deadline=deadline)
    first = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8, 3),
        arr=datetime(2026, 6, 29, 9, 3),
        unload_end=datetime(2026, 6, 29, 9, 4),
        items=[(to_b, 100), (to_c, 200)],
        cost=float(Decimal("246")), chain_id=71, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="B", dest="C",
        load_start=datetime(2026, 6, 29, 9, 4),
        dep=datetime(2026, 6, 29, 9, 4),
        arr=datetime(2026, 6, 29, 10, 4),
        unload_end=datetime(2026, 6, 29, 10, 6),
        items=[(to_c, 200)], cost=0.0, chain_id=71, chain_seq=1,
    )
    return [first, second]


def _carry_chain(*, vtype="Kamyonet"):
    to_b = _chain_part("D00005", 100, "B")
    to_c = _chain_part("D00006", 900, "C")
    first = PlannedLeg(
        kind="Spot", vtype=vtype, origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8, 10),
        arr=datetime(2026, 6, 29, 9, 10),
        unload_end=datetime(2026, 6, 29, 9, 11),
        items=[(to_b, 100), (to_c, 900)], chain_id=72, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype=vtype, origin="B", dest="C",
        load_start=datetime(2026, 6, 29, 9, 11),
        dep=datetime(2026, 6, 29, 9, 11),
        arr=datetime(2026, 6, 29, 10, 11),
        unload_end=datetime(2026, 6, 29, 10, 20),
        items=[(to_c, 900)], chain_id=72, chain_seq=1,
    )
    return [first, second]


def _transfer_chain():
    to_b = _chain_part("D00001", 100, "B")
    from_b = _chain_part("D00002", 200, "C")
    first = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8, 1),
        arr=datetime(2026, 6, 29, 9, 1),
        unload_end=datetime(2026, 6, 29, 9, 2),
        items=[(to_b, 100)], cost=float(Decimal("246")),
        chain_id=73, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="B", dest="C",
        load_start=datetime(2026, 6, 29, 9, 2),
        dep=datetime(2026, 6, 29, 9, 4),
        arr=datetime(2026, 6, 29, 10, 4),
        unload_end=datetime(2026, 6, 29, 10, 6),
        items=[(from_b, 200)], cost=0.0, chain_id=73, chain_seq=1,
    )
    return [first, second]


def _timestamps(legs):
    return [
        (leg.load_start, leg.dep, leg.arr, leg.unload_end)
        for leg in legs
    ]


def _midnight_chain():
    to_b = _chain_part("D00007", 1_000, "B")
    to_c = _chain_part("D00008", 9_000, "C")
    first = PlannedLeg(
        kind="Spot", vtype="Tır", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 23, 30),
        dep=datetime(2026, 6, 30, 1, 10),
        arr=datetime(2026, 6, 30, 2, 10),
        unload_end=datetime(2026, 6, 30, 2, 20),
        items=[(to_b, 1_000), (to_c, 9_000)],
        chain_id=74, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype="Tır", origin="B", dest="C",
        load_start=datetime(2026, 6, 30, 2, 20),
        dep=datetime(2026, 6, 30, 2, 20),
        arr=datetime(2026, 6, 30, 3, 20),
        unload_end=datetime(2026, 6, 30, 4, 50),
        items=[(to_c, 9_000)], chain_id=74, chain_seq=1,
    )
    return [first, second]


def test_pair_chain_declares_one_physical_vehicle_and_part_ids():
    frame, notes = to_plan_frame(_pair_chain(), _schedule_data(), fix=False)

    assert notes == []
    assert list(frame[[
        "Araç ID", "Araç Tipi", "Araç türü",
        "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
        "Talep ID", "Taşınan Desi",
    ]].itertuples(index=False, name=None)) == [
        ("V0001", "Spot", "Kamyonet", "A", "B", "D00001", 100),
        ("V0001", "Spot", "Kamyonet", "A", "B", "D00002", 200),
        ("V0001", "Spot", "Kamyonet", "B", "C", "D00002", 200),
    ]


def test_chain_declares_only_actual_handling():
    frame, _notes = to_plan_frame(
        _pair_chain(), _schedule_data(), fix=False)

    assert frame["Çıkış Elleçleme süresi"].tolist() == [1, 2, 0]
    assert frame["Varış elleçleme süresi"].tolist() == [1, 0, 2]


def test_chain_declares_full_travel_on_every_row():
    frame, _notes = to_plan_frame(
        _pair_chain(), _schedule_data(), fix=False)

    assert frame["Yolculuk süresi"].tolist() == [60, 60, 60]


def test_chain_declares_sla_only_on_final_unload():
    frame, _notes = to_plan_frame(
        _pair_chain(), _schedule_data(), fix=False)

    assert frame["SLA cezası"].tolist() == [40.0, 0.0, 160.0]


def test_chain_allocates_continuous_vehicle_cost_once():
    frame, _notes = to_plan_frame(
        _pair_chain(), _schedule_data(), fix=False)

    vehicle_portions = [
        total - penalty
        for total, penalty in zip(
            frame["Toplam maliyet"], frame["SLA cezası"])
    ]
    assert vehicle_portions == [82.0, 164.0, 0.0]
    assert frame["Toplam maliyet"].tolist() == [122.0, 164.0, 160.0]
    assert frame["Toplam maliyet"].sum() == 446.0


def test_chain_requires_later_segment_cost_zero():
    legs = _pair_chain()
    legs[1].cost = 1.0

    with pytest.raises(ValueError) as caught:
        to_plan_frame(legs, _schedule_data(), fix=False)

    message = str(caught.value)
    assert "chain 71" in message
    assert "cost" in message.lower()
    assert "zero" in message.lower()


def test_empty_rented_standalone_owns_full_cost():
    leg = PlannedLeg(
        kind="Kiralık", vtype="Kamyonet", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8),
        arr=datetime(2026, 6, 29, 9),
        unload_end=datetime(2026, 6, 29, 9),
        items=[], cost=321.5,
    )

    frame, notes = to_plan_frame([leg], _schedule_data(), fix=False)

    assert notes == []
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["Talep ID"] == ""
    assert row["Taşınan Desi"] == 0
    assert row["Çıkış Elleçleme süresi"] == 0
    assert row["Varış elleçleme süresi"] == 0
    assert row["SLA cezası"] == 0.0
    assert row["Toplam maliyet"] == 321.5


def test_direct_frame_semantics_are_unchanged():
    deadline = datetime(2026, 6, 29, 8, 30)
    first = _chain_part("D00003", 1, "B", deadline=deadline)
    second = _chain_part("D00004", 6, "B", deadline=deadline)
    leg = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8, 1),
        arr=datetime(2026, 6, 29, 9, 1),
        unload_end=datetime(2026, 6, 29, 9, 2),
        items=[(first, 1), (second, 6)], cost=100.1,
        penalty=9_999.0,
    )

    frame, notes = to_plan_frame([leg], _schedule_data(), fix=False)

    assert notes == []
    assert list(frame.columns) == PLAN_COLS
    assert frame.to_dict("records") == [
        {
            "Araç ID": "V0001", "Araç Tipi": "Spot",
            "Araç türü": "Kamyonet", "Çıkış Transfer Merkezi": "A",
            "Varış Transfer Merkezi": "B", "Çıkış Tarihi": "29.06.2026",
            "Çıkış Saati": "08:01", "Varış Tarihi": "29.06.2026",
            "Varış Saati": "09:01", "Talep ID": "D00003",
            "Taşınan Desi": 1, "Yolculuk süresi": 60,
            "Varış elleçleme süresi": 1,
            "Çıkış Elleçleme süresi": 1, "SLA cezası": 0.4,
            "Toplam maliyet": 14.7,
        },
        {
            "Araç ID": "V0001", "Araç Tipi": "Spot",
            "Araç türü": "Kamyonet", "Çıkış Transfer Merkezi": "A",
            "Varış Transfer Merkezi": "B", "Çıkış Tarihi": "29.06.2026",
            "Çıkış Saati": "08:01", "Varış Tarihi": "29.06.2026",
            "Varış Saati": "09:01", "Talep ID": "D00004",
            "Taşınan Desi": 6, "Yolculuk süresi": 60,
            "Varış elleçleme süresi": 1,
            "Çıkış Elleçleme süresi": 1,
            "SLA cezası": 2.4000000000000004,
            "Toplam maliyet": 88.2,
        },
    ]


def test_handling_ledger_uses_drop_not_onboard_desi():
    legs = _carry_chain(vtype="Tır")
    notes = []

    _fix_handling(
        legs,
        _schedule_data({"A": 1_000, "B": 100, "C": 900}),
        notes,
    )

    assert notes == []


def test_chain_segments_are_unshiftable():
    legs = _transfer_chain()
    before = _timestamps(legs)
    notes = []

    _fix_handling(
        legs,
        _schedule_data({"A": 100, "B": 250, "C": 200}),
        notes,
    )

    assert _timestamps(legs) == before
    assert len(notes) == 1
    assert notes[0].startswith("Elleçleme düzeltmesi bacak bulamadı:")
    assert "'B'" in notes[0]
    assert "300.0, 250" in notes[0]


def test_unresolved_chain_handling_is_rejected_by_simulator():
    legs = _transfer_chain()
    before = _timestamps(legs)
    data = _schedule_data({"A": 100, "B": 250, "C": 200})
    forecast = pd.DataFrame([
        {
            "Talep ID": "D00001", "Tarih": "29.06.2026",
            "Talep Tamamlama Saati": "07:00",
            "Çıkış Transfer Merkezi": "A", "Varış Transfer Merkezi": "B",
            "Tahmin Edilen Desi": 100,
        },
        {
            "Talep ID": "D00002", "Tarih": "29.06.2026",
            "Talep Tamamlama Saati": "07:00",
            "Çıkış Transfer Merkezi": "B", "Varış Transfer Merkezi": "C",
            "Tahmin Edilen Desi": 200,
        },
    ], columns=FORECAST_COLS)

    frame, notes = to_plan_frame(legs, data)
    result = simulate(frame, forecast, data, rental_days=[])

    assert _timestamps(legs) == before
    assert len(frame) == 2
    assert list(frame.columns) == PLAN_COLS
    assert any(note.startswith("Elleçleme düzeltmesi bacak bulamadı:")
               for note in notes)
    assert [
        violation for violation in result.violations
        if violation.startswith("Elleçleme kapasitesi aşıldı:")
    ] == [
        "Elleçleme kapasitesi aşıldı: B 2026-06-29: 300.0 > 250.0"
    ]


def test_unrelated_direct_leg_can_shift_around_chain_overload():
    chain = _carry_chain()
    direct_part = _chain_part("D00009", 950, "C")
    direct = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="B", dest="C",
        load_start=datetime(2026, 6, 29, 11),
        dep=datetime(2026, 6, 29, 11, 10),
        arr=datetime(2026, 6, 29, 12, 10),
        unload_end=datetime(2026, 6, 29, 12, 20),
        items=[(direct_part, 950)],
    )
    chain_before = _timestamps(chain)
    notes = []

    _fix_handling(
        [*chain, direct],
        _schedule_data({"A": 10_000, "B": 1_000, "C": 10_000}),
        notes,
    )

    assert _timestamps(chain) == chain_before
    assert _timestamps([direct]) == [(
        datetime(2026, 6, 30, 0, 0),
        datetime(2026, 6, 30, 0, 10),
        datetime(2026, 6, 30, 1, 10),
        datetime(2026, 6, 30, 1, 20),
    )]
    assert len(notes) == 1
    assert notes[0].startswith("Elleçleme düzeltmesi:")
    assert "2026-06-29" in notes[0]


def test_chain_handling_keeps_proportional_midnight_split():
    cases = [
        (
            2_999,
            "Elleçleme düzeltmesi bacak bulamadı: "
            "('A', datetime.date(2026, 6, 29), 3000.0, 2999)",
        ),
        (
            6_999,
            "Elleçleme düzeltmesi bacak bulamadı: "
            "('A', datetime.date(2026, 6, 30), 7000.0, 6999)",
        ),
    ]

    for cap, expected_note in cases:
        notes = []
        _fix_handling(
            _midnight_chain(),
            _schedule_data({"A": cap, "B": 100_000, "C": 100_000}),
            notes,
        )
        assert notes == [expected_note]


def test_empty_multi_segment_chain_is_invalid():
    first = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="A", dest="B",
        load_start=datetime(2026, 6, 29, 8),
        dep=datetime(2026, 6, 29, 8),
        arr=datetime(2026, 6, 29, 9),
        unload_end=datetime(2026, 6, 29, 9),
        items=[], cost=246.0, chain_id=75, chain_seq=0,
    )
    second = PlannedLeg(
        kind="Spot", vtype="Kamyonet", origin="B", dest="C",
        load_start=datetime(2026, 6, 29, 9),
        dep=datetime(2026, 6, 29, 9),
        arr=datetime(2026, 6, 29, 10),
        unload_end=datetime(2026, 6, 29, 10),
        items=[], cost=0.0, chain_id=75, chain_seq=1,
    )

    with pytest.raises(ValueError, match="empty multi-segment"):
        to_plan_frame([first, second], _schedule_data(), fix=False)
