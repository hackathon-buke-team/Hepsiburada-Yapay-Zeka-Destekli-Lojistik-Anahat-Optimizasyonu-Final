from datetime import datetime
from src.timeutil import (travel_minutes, handling_minutes, late_hours,
                          parse_dt, fmt_date, fmt_time)


# --- PDF'lerdeki işlenmiş örnekler ---

def test_travel_rounding_pdf_example():
    # İstanbul->Yalova 0,92 saat = 55,2 dk -> 56 (son-gelen-message madde 4)
    assert travel_minutes(0.92) == 56

def test_handling_pdf_examples():
    assert handling_minutes(5000) == 50     # şartname örneği
    assert handling_minutes(10000) == 100   # Q&A kullanım süresi örneği
    assert handling_minutes(22400) == 224   # dolu tır

def test_late_hours_pdf_examples():
    d = datetime(2026, 7, 8, 9, 0)
    assert late_hours(d, datetime(2026, 7, 8, 10, 0)) == 1    # tam 1 saat
    assert late_hours(d, datetime(2026, 7, 8, 11, 20)) == 3   # 2s20d -> 3
    assert late_hours(d, datetime(2026, 7, 8, 9, 1)) == 1     # 1 dk -> 1 saat
    assert late_hours(d, datetime(2026, 7, 8, 9, 0)) == 0     # tam zamanında
    assert late_hours(d, datetime(2026, 7, 8, 8, 0)) == 0     # erken

# --- kenar durumlar ---

def test_travel_exact_minute_not_rounded_up():
    assert travel_minutes(1.0) == 60
    assert travel_minutes(23.82) == 1430   # 1429,2 -> 1430 (Tekirdağ-Mardin)

def test_handling_fractional_and_zero():
    assert handling_minutes(31) == 1       # 0,31 dk -> 1
    assert handling_minutes(150) == 2      # 1,5 dk -> 2
    assert handling_minutes(100) == 1      # tam 1 dk
    assert handling_minutes(0) == 0

def test_float_artifact_guard():
    # 4.6*60 = 275.99999... olabilir; 276 kalmalı, 277'ye taşmamalı
    assert travel_minutes(4.6) == 276

def test_datetime_helpers_roundtrip():
    dt = parse_dt("29.06.2026", "09:05")
    assert dt == datetime(2026, 6, 29, 9, 5)
    assert fmt_date(dt) == "29.06.2026"
    assert fmt_time(dt) == "09:05"
