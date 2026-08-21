from datetime import datetime, timedelta

import pytest

from src.candidates import Part
from src.chain import LegFlow, analyze_leg_flows, physical_routes
from src.optimize import PlannedLeg


READY = datetime(2026, 6, 29, 9)


def _part(part_id, desi, *, dest="C"):
    return Part(
        part_id=part_id,
        base_id=part_id,
        desi=desi,
        ready=READY,
        deadline=READY + timedelta(days=1),
        dest=dest,
    )


def _leg(items, *, origin="A", dest="B", kind="Spot",
         vtype="Kamyonet", chain_id=None, chain_seq=0):
    load_start = READY + timedelta(hours=2 * chain_seq)
    dep = load_start + timedelta(minutes=1)
    arr = dep + timedelta(hours=1)
    return PlannedLeg(
        kind=kind,
        vtype=vtype,
        origin=origin,
        dest=dest,
        load_start=load_start,
        dep=dep,
        arr=arr,
        unload_end=arr + timedelta(minutes=1),
        items=list(items),
        chain_id=chain_id,
        chain_seq=chain_seq,
    )


def test_physical_routes_keep_standalones_separate_and_group_chain():
    standalone_first = _leg([])
    chain_second = _leg(
        [], origin="B", dest="C", chain_id=7, chain_seq=1)
    chain_first = _leg([], chain_id=7, chain_seq=0)
    standalone_second = _leg([], origin="C", dest="D")

    routes = physical_routes([
        standalone_first,
        chain_second,
        chain_first,
        standalone_second,
    ])

    assert routes == [
        (standalone_first,),
        (chain_first, chain_second),
        (standalone_second,),
    ]
    assert routes[0][0] is standalone_first
    assert routes[1][0] is chain_first
    assert routes[1][1] is chain_second
    assert routes[2][0] is standalone_second


def test_pair_chain_flows_are_input_aligned():
    p_b = _part("to-b", 100, dest="B")
    p_c = _part("to-c", 200)
    first = _leg(
        [(p_b, 100), (p_c, 200)], chain_id=7, chain_seq=0)
    second = _leg(
        [(p_c, 200)], origin="B", dest="C", chain_id=7, chain_seq=1)

    flows = analyze_leg_flows([first, second])

    assert flows[0].loaded == ((p_b, 100), (p_c, 200))
    assert flows[0].carried == ((p_c, 200),)
    assert flows[0].unloaded == ((p_b, 100),)
    assert flows[1] == LegFlow(
        loaded=(), carried=(), unloaded=((p_c, 200),))
    assert flows[0].carried[0][0] is flows[1].unloaded[0][0]
    assert flows[0].loaded[0] is first.items[0]
    assert flows[0].carried[0] is first.items[1]
    assert flows[1].unloaded[0] is second.items[0]

    reversed_flows = analyze_leg_flows([second, first])

    assert reversed_flows[0] == flows[1]
    assert reversed_flows[1] == flows[0]
    assert reversed_flows[0].unloaded[0][0] is p_c
    assert reversed_flows[1].loaded[0][0] is p_b


def test_standalone_loads_and_unloads_every_item():
    item = (_part("standalone", 100, dest="B"), 100)
    leg = _leg([item])

    flow = analyze_leg_flows([leg])[0]

    assert flow.loaded == tuple(leg.items)
    assert flow.carried == ()
    assert flow.unloaded == tuple(leg.items)
    assert flow.loaded[0] is item
    assert flow.unloaded[0] is item


def test_distinct_equal_parts_are_not_one_physical_part():
    first_part = _part("equal", 100)
    second_part = _part("equal", 100)
    assert first_part == second_part
    assert first_part is not second_part
    first = _leg(
        [(first_part, 100)], chain_id=7, chain_seq=0)
    second = _leg(
        [(second_part, 100)], origin="B", dest="C",
        chain_id=7, chain_seq=1)

    flows = analyze_leg_flows([first, second])

    assert flows[0] == LegFlow(
        loaded=((first_part, 100),),
        carried=(),
        unloaded=((first_part, 100),),
    )
    assert flows[1] == LegFlow(
        loaded=((second_part, 100),),
        carried=(),
        unloaded=((second_part, 100),),
    )
    assert flows[0].unloaded[0][0] is first_part
    assert flows[1].loaded[0][0] is second_part


@pytest.mark.parametrize("sequences", [[1], [0, 2], [0, 0]])
def test_chain_requires_zero_based_contiguous_sequence(sequences):
    edges = [("A", "B"), ("B", "C")]
    legs = [
        _leg([], origin=edges[index][0], dest=edges[index][1],
             chain_id=7, chain_seq=sequence)
        for index, sequence in enumerate(sequences)
    ]

    with pytest.raises(ValueError) as caught:
        physical_routes(legs)

    assert "chain 7" in str(caught.value)
    assert "chain_seq" in str(caught.value)


def test_distinct_chain_ids_form_distinct_physical_routes():
    seven_second = _leg(
        [], origin="B", dest="C", chain_id=7, chain_seq=1)
    eight_first = _leg([], chain_id=8, chain_seq=0)
    seven_first = _leg([], chain_id=7, chain_seq=0)
    eight_second = _leg(
        [], origin="B", dest="C", chain_id=8, chain_seq=1)

    routes = physical_routes([
        seven_second,
        eight_first,
        seven_first,
        eight_second,
    ])

    assert routes == [
        (seven_first, seven_second),
        (eight_first, eight_second),
    ]
    assert routes[0][0] is seven_first
    assert routes[0][1] is seven_second
    assert routes[1][0] is eight_first
    assert routes[1][1] is eight_second


def test_chain_requires_connected_topology():
    first = _leg([], chain_id=7, chain_seq=0)
    second = _leg(
        [], origin="C", dest="D", chain_id=7, chain_seq=1)

    with pytest.raises(ValueError) as caught:
        physical_routes([first, second])

    assert "B" in str(caught.value)
    assert "C" in str(caught.value)


@pytest.mark.parametrize(
    ("second_kind", "second_vtype", "expected"),
    [
        ("Kiralık", "Kamyonet", "mixed kind"),
        ("Spot", "Kamyon", "mixed vehicle type"),
    ],
)
def test_chain_requires_one_kind_and_vehicle_type(
        second_kind, second_vtype, expected):
    first = _leg([], chain_id=7, chain_seq=0)
    second = _leg(
        [], origin="B", dest="C", kind=second_kind,
        vtype=second_vtype, chain_id=7, chain_seq=1)

    with pytest.raises(ValueError, match=rf"chain 7: {expected}"):
        physical_routes([first, second])


def test_chain_rejects_duplicate_part_in_one_segment():
    part = _part("duplicate", 100, dest="B")
    leg = _leg(
        [(part, 100), (part, 100)], chain_id=7, chain_seq=0)

    with pytest.raises(ValueError, match="duplicate Part"):
        analyze_leg_flows([leg])


def test_chain_rejects_desi_change_for_same_part():
    part = _part("changed", 100)
    first = _leg([(part, 100)], chain_id=7, chain_seq=0)
    second = _leg(
        [(part, 99)], origin="B", dest="C", chain_id=7, chain_seq=1)

    with pytest.raises(ValueError) as caught:
        analyze_leg_flows([first, second])

    assert "100" in str(caught.value)
    assert "99" in str(caught.value)


def test_chain_rejects_disappear_then_reappear():
    part = _part("reappearing", 100)
    first = _leg([(part, 100)], chain_id=7, chain_seq=0)
    middle = _leg(
        [], origin="B", dest="C", chain_id=7, chain_seq=1)
    last = _leg(
        [(part, 100)], origin="C", dest="D", chain_id=7, chain_seq=2)

    with pytest.raises(ValueError, match="non-contiguous Part"):
        analyze_leg_flows([first, middle, last])
