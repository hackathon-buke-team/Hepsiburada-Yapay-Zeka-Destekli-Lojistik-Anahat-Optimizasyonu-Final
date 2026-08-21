from datetime import datetime, timedelta

import pandas as pd
import pytest
from src.data import load_all, DATA_DIR
from src.schemas import PLAN_COLS
from src.simulator import DeclaredRow, parse_legs, trace_vehicle
from src.timeutil import travel_minutes


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def _row(**kw):
    base = {"Araç ID": "V0001", "Araç Tipi": "Spot", "Araç türü": "Tır",
            "Çıkış Transfer Merkezi": "İstanbul", "Varış Transfer Merkezi": "Yalova",
            "Çıkış Tarihi": "29.06.2026", "Çıkış Saati": "11:00",
            "Varış Tarihi": "29.06.2026", "Varış Saati": "11:56",
            "Talep ID": "D00001", "Taşınan Desi": 10000.0,
            "Yolculuk süresi": 56, "Varış elleçleme süresi": 100,
            "Çıkış Elleçleme süresi": 100, "SLA cezası": 0.0,
            "Toplam maliyet": 0.0}
    base.update(kw)
    return base


def test_parse_legs_preserves_declared_rows_and_existing_items():
    frame = pd.DataFrame([
        _row(**{
            "Talep ID": "D00001", "Taşınan Desi": 100.0,
            "Yolculuk süresi": 60.0,
            "Varış elleçleme süresi": 1.0,
            "Çıkış Elleçleme süresi": 1.0,
            "SLA cezası": 0.0, "Toplam maliyet": 82.0,
        }),
        _row(**{
            "Talep ID": "D00002", "Taşınan Desi": 200.0,
            "Yolculuk süresi": 60.0,
            "Varış elleçleme süresi": 0.0,
            "Çıkış Elleçleme süresi": 2.0,
            "SLA cezası": 1.25, "Toplam maliyet": 165.25,
        }),
        _row(**{
            "Araç ID": "V0002", "Araç Tipi": "Kiralık",
            "Çıkış Saati": "13:00", "Varış Saati": "13:56",
            "Talep ID": "", "Taşınan Desi": 0.0,
            "Yolculuk süresi": 56.0,
            "Varış elleçleme süresi": 0.0,
            "Çıkış Elleçleme süresi": 0.0,
            "SLA cezası": 0.0, "Toplam maliyet": 1052.22,
        }),
    ], columns=PLAN_COLS)

    legs = parse_legs(frame)

    assert legs[0].items == [("D00001", 100.0), ("D00002", 200.0)]
    assert legs[0].declared_rows == [
        DeclaredRow(
            item_id="D00001", desi=100.0, travel_minutes=60.0,
            arrival_handling_minutes=1.0,
            departure_handling_minutes=1.0,
            sla_penalty=0.0, total_cost=82.0,
        ),
        DeclaredRow(
            item_id="D00002", desi=200.0, travel_minutes=60.0,
            arrival_handling_minutes=0.0,
            departure_handling_minutes=2.0,
            sla_penalty=1.25, total_cost=165.25,
        ),
    ]
    assert legs[1].items == []
    assert legs[1].declared_rows == [
        DeclaredRow(
            item_id=None, desi=0.0, travel_minutes=56.0,
            arrival_handling_minutes=0.0,
            departure_handling_minutes=0.0,
            sla_penalty=0.0, total_cost=1052.22,
        )
    ]


def test_single_leg_cost_pdf_example(data):
    # Q&A örneği (spot Tır, 10.000 desi): 100 dk yükleme + yol + 100 dk indirme
    # İstanbul->Yalova: 56 dk yol, 60 km => kullanım 256 dk = 4,2667 saat
    # maliyet = 487,5 * 256/60 + 25*60 = 2080 + 1500 = 3580 TL
    plan = pd.DataFrame([_row()], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 1
    tr = trace_vehicle(legs, data)
    assert tr.violations == []
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)   # 11:00 - 100 dk
    assert tr.usage_end == datetime(2026, 6, 29, 13, 36)    # 11:56 + 100 dk
    assert abs(tr.usage_hours - 256 / 60) < 1e-9
    assert tr.total_km == 60
    assert abs(tr.cost - 3580.0) < 0.01


def test_multi_demand_same_leg_single_handling(data):
    # Aynı bacakta 2 talep: elleçleme TOPLAM desi üzerinden tek işlem
    plan = pd.DataFrame([
        _row(**{"Talep ID": "D00001", "Taşınan Desi": 6000.0}),
        _row(**{"Talep ID": "D00002", "Taşınan Desi": 4000.0}),
    ], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 1 and len(legs[0].items) == 2
    tr = trace_vehicle(legs, data)
    assert abs(tr.cost - 3580.0) < 0.01     # 10.000 desi toplam, aynı sonuç


def test_chained_legs_stay_aboard_no_double_handling(data):
    # V0001: İstanbul->Yalova->Eskişehir; D00001 gemide kalıyor (milk-run),
    # D00002 Yalova'da iniyor. Yalova'da D00001 için elleçleme YOK.
    lane2 = data.lanes[("Yalova", "Eskişehir")]
    t2 = travel_minutes(lane2.hours["Tır"])
    dep2 = datetime(2026, 6, 29, 13, 0)
    plan = pd.DataFrame([
        _row(**{"Talep ID": "D00001", "Taşınan Desi": 5000.0}),
        _row(**{"Talep ID": "D00002", "Taşınan Desi": 5000.0}),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "Eskişehir",
                "Çıkış Saati": "13:00", "Varış Saati": "15:50",
                "Talep ID": "D00001", "Taşınan Desi": 5000.0}),
    ], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert len(legs) == 2
    tr = trace_vehicle(legs, data)
    assert tr.violations == []
    # Yükleme (10.000 desi, 100 dk) 09:20'de başlar
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)
    # Yalova olayları: yalnız D00002'nin indirilmesi (50 dk, 11:56->12:46)
    yalova_events = [e for e in tr.events if e.tm == "Yalova"]
    assert len(yalova_events) == 1
    assert yalova_events[0].kind == "unload"
    assert abs(yalova_events[0].desi - 5000) < 1e-6
    # 2. bacakta yeni yük yok: load_start == dep; kullanım sonu = varış + 50 dk
    assert tr.leg_times[1]["load_start"] == dep2
    assert tr.usage_end == dep2 + timedelta(minutes=t2 + 50)
    assert tr.total_km == 60 + lane2.km


def test_wait_time_included_in_usage(data):
    # Araç Yalova'da bekleyip ikinci sefer yapıyor; bekleme kullanım süresine dahil
    plan = pd.DataFrame([
        _row(),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "İstanbul",
                "Çıkış Saati": "15:30", "Varış Saati": "16:26",
                "Talep ID": "D00003", "Taşınan Desi": 10000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert tr.violations == []
    # bacak 1: 09:20 yükleme -> 11:56 varış -> 13:36 indirme biter
    # bacak 2: yükleme 13:50 (>= 13:36 OK), kalkış 15:30, varış 16:26, indirme 18:06
    assert tr.usage_start == datetime(2026, 6, 29, 9, 20)
    assert tr.usage_end == datetime(2026, 6, 29, 18, 6)
    assert abs(tr.usage_hours - 526 / 60) < 1e-9
    # maliyet: 487,5*526/60 + 25*120 = 4273,75 + 3000 = 7273,75
    assert abs(tr.cost - 7273.75) < 0.01


def test_overlap_load_before_previous_unload_flagged(data):
    # İkinci bacak kalkışı o kadar erken ki yükleme, önceki indirme bitmeden başlıyor
    plan = pd.DataFrame([
        _row(),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "İstanbul",
                "Çıkış Saati": "14:00", "Varış Saati": "14:56",
                "Talep ID": "D00003", "Taşınan Desi": 10000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    # yükleme 12:20 < önceki indirme bitişi 13:36 -> ihlal
    assert any("önceki işlem" in v for v in tr.violations)


def test_missing_lane_still_checks_capacity_and_chain(data):
    plan = pd.DataFrame([
        _row(),
        _row(**{"Çıkış Transfer Merkezi": "İstanbul",
                "Varış Transfer Merkezi": "İstanbul",   # matriste yok (self-loop)
                "Çıkış Saati": "18:00", "Varış Saati": "18:30",
                "Talep ID": "D00009", "Taşınan Desi": 30000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert tr.leg_times[1] is None
    joined = " | ".join(tr.violations)
    assert "matriste olmayan hat" in joined
    assert "kapasite aşımı" in joined
    assert "bacak zinciri kopuk" in joined      # Yalova -> İstanbul kopuk


def test_kiralik_pricing_branch(data):
    plan = pd.DataFrame([_row(**{"Araç Tipi": "Kiralık"})], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert tr.violations == []
    # kiralık Tır: 291,666667*256/60 + 13*60 = 1244,44 + 780 = 2024,44
    assert abs(tr.cost - 2024.4444) < 0.01


def test_empty_kiralik_leg_travel_only(data):
    plan = pd.DataFrame([_row(**{"Araç Tipi": "Kiralık", "Talep ID": "",
                                 "Taşınan Desi": 0.0})], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert legs[0].items == []
    tr = trace_vehicle(legs, data)
    assert tr.violations == []
    assert abs(tr.usage_hours - 56 / 60) < 1e-9
    # 291,666667*56/60 + 13*60 = 272,22 + 780 = 1052,22
    assert abs(tr.cost - 1052.2222) < 0.01


def test_duplicate_demand_id_same_leg_flagged(data):
    plan = pd.DataFrame([
        _row(**{"Taşınan Desi": 4000.0}),
        _row(**{"Taşınan Desi": 3000.0}),   # aynı D00001 aynı bacakta tekrar
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert any("tekrarlı talep ID" in v for v in tr.violations)


def test_demand_part_desi_change_between_legs_flagged(data):
    plan = pd.DataFrame([
        _row(**{"Taşınan Desi": 5000.0}),
        _row(**{"Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "Eskişehir",
                "Çıkış Saati": "13:30", "Varış Saati": "16:20",
                "Taşınan Desi": 4000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert any("bacaklar arasında desi değişiyor" in v for v in tr.violations)
    assert any("yaratılamaz/kaybolamaz" in v for v in tr.violations)


@pytest.mark.parametrize(
    ("column", "other_value"),
    [("Araç Tipi", "Kiralık"), ("Araç türü", "Kamyon")],
)
def test_mixed_vehicle_fields_within_same_leg_group_flagged(
        data, column, other_value):
    second = _row(**{"Talep ID": "D00002", "Taşınan Desi": 5000.0})
    second[column] = other_value
    plan = pd.DataFrame([
        _row(**{"Taşınan Desi": 5000.0}),
        second,
    ], columns=PLAN_COLS)
    legs = parse_legs(plan)
    assert any(column in v and "aynı bacak grubunda" in v
               for v in legs[0].violations)
    tr = trace_vehicle(legs, data)
    assert any(column in v and "aynı bacak grubunda" in v
               for v in tr.violations)


def test_mixed_vehicle_type_chain_flagged(data):
    plan = pd.DataFrame([
        _row(),
        _row(**{"Araç türü": "Kamyonet",
                "Çıkış Transfer Merkezi": "Yalova",
                "Varış Transfer Merkezi": "İstanbul",
                "Çıkış Saati": "16:00", "Varış Saati": "16:56",
                "Talep ID": "D00003", "Taşınan Desi": 6000.0}),
    ], columns=PLAN_COLS)
    tr = trace_vehicle(parse_legs(plan), data)
    assert any("tutarsız" in v for v in tr.violations)
