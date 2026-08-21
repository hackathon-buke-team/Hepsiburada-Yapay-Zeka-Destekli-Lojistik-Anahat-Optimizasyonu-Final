from datetime import date, datetime
from src.ledger import HandlingLedger, TirLedger


def test_midnight_proportional_split_pdf_example():
    # 29.06 23:30'da 10.000 desi: süre 100 dk -> 30 dk o gün, 70 dk ertesi gün
    # => 3.000 desi 29.06'ya, 7.000 desi 30.06'ya yazılır (son-gelen-message m.5)
    led = HandlingLedger({"İstanbul": 394786.0})
    end = led.add("İstanbul", datetime(2026, 6, 29, 23, 30), 10000)
    assert end == datetime(2026, 6, 30, 1, 10)
    assert abs(led.used[("İstanbul", date(2026, 6, 29))] - 3000) < 1e-6
    assert abs(led.used[("İstanbul", date(2026, 6, 30))] - 7000) < 1e-6


def test_same_day_no_split():
    led = HandlingLedger({"Yalova": 513171.0})
    end = led.add("Yalova", datetime(2026, 6, 29, 10, 0), 5000)
    assert end == datetime(2026, 6, 29, 10, 50)
    assert abs(led.used[("Yalova", date(2026, 6, 29))] - 5000) < 1e-6
    assert ("Yalova", date(2026, 6, 30)) not in led.used


def test_handling_capacity_violation_detected():
    led = HandlingLedger({"Denizli": 36868.0})
    led.add("Denizli", datetime(2026, 6, 29, 8, 0), 30000)
    assert led.violations() == []
    led.add("Denizli", datetime(2026, 6, 29, 12, 0), 10000)
    v = led.violations()
    assert len(v) == 1 and "Denizli" in v[0]


def test_zero_desi_noop():
    led = HandlingLedger({"Mersin": 100.0})
    end = led.add("Mersin", datetime(2026, 6, 29, 8, 0), 0)
    assert end == datetime(2026, 6, 29, 8, 0)
    assert led.used == {}


def test_tir_visit_counted_once_per_visit():
    # Bacak k varışı (visit k+1) + bacak k+1 kalkışı (visit k+1) = TEK ziyaret.
    led = TirLedger({"Eskişehir": 10})
    d = date(2026, 6, 29)
    led.add_event("Eskişehir", d, "V0001", visit_id=1)  # bacak 0 varışı
    led.add_event("Eskişehir", d, "V0001", visit_id=1)  # bacak 1 kalkışı (hareketsiz)
    assert led.count("Eskişehir", d) == 1
    # Gün içinde İKİNCİ ziyaret (araç gidip geri geldi) ayrıca sayılır
    led.add_event("Eskişehir", d, "V0001", visit_id=3)
    assert led.count("Eskişehir", d) == 2


def test_tir_capacity_violation():
    led = TirLedger({"Balıkesir": 1})
    d = date(2026, 6, 29)
    led.add_event("Balıkesir", d, "V0001", 1)
    assert led.violations() == []
    led.add_event("Balıkesir", d, "V0002", 1)
    v = led.violations()
    assert len(v) == 1 and "Balıkesir" in v[0]


def test_unknown_tm_reported_not_crash():
    from datetime import date, datetime
    led = HandlingLedger({"Mersin": 100.0})
    led.add("Atlantis", datetime(2026, 6, 29, 8, 0), 500)
    v = led.violations()
    assert len(v) == 1 and "Atlantis" in v[0]
    tled = TirLedger({"Mersin": 5})
    tled.add_event("Atlantis", date(2026, 6, 29), "V0001", 1)
    tv = tled.violations()
    assert len(tv) == 1 and "Atlantis" in tv[0]
