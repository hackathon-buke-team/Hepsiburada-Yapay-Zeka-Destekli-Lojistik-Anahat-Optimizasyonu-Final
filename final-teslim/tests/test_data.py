from pathlib import Path

import pandas as pd
import pytest

import src.data as data_module
from src.data import DATA_DIR, RentalRoute, load_all


@pytest.fixture(scope="module")
def data():
    return load_all(DATA_DIR)


def test_vehicles(data):
    assert set(data.vehicles) == {"Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"}
    tir = data.vehicles["Tır"]
    assert tir.capacity_desi == 22400
    assert tir.spot_per_km == 25
    assert abs(tir.spot_hourly - 487.5) < 1e-6
    assert data.vehicles["Kamyonet"].capacity_desi == 5600


def test_lanes(data):
    assert len(data.lanes) == 306  # 18*17 tam yönlü graf
    ist_yal = data.lanes[("İstanbul", "Yalova")]
    assert ist_yal.km == 60
    assert abs(ist_yal.hours["Tır"] - 0.92) < 1e-6
    assert ist_yal.sla_days == 1
    assert data.lanes[("Tekirdağ", "Mardin")].sla_days == 2


def test_rentals(data):
    assert len(data.rentals) == 12
    assert sum(r.count for r in data.rentals) == 14
    ist_yalova = [r for r in data.rentals
                  if (r.origin, r.dest) == ("İstanbul", "Yalova")]
    assert len(ist_yalova) == 1 and ist_yalova[0].count == 2
    assert all(r.origin in {"İstanbul", "Kocaeli", "Yalova"} for r in data.rentals)


def test_capacities(data):
    assert len(data.handling_cap) == 18
    assert len(data.tir_cap) == 18
    assert data.tir_cap["Yalova"] == 4
    assert data.tir_cap["Balıkesir"] == 1
    zero_caps = {tm for tm, c in data.tir_cap.items() if c == 0}
    assert zero_caps == {"Kütahya", "Isparta", "Bilecik", "Zonguldak",
                         "Sivas", "Karaman", "Denizli"}


def test_demand(data):
    d = data.demand
    assert len(d) == 66024
    assert set(d["slot"].unique()) == {"09:00", "17:00"}
    assert d["talep_id"].is_unique
    assert "Kocaeli" not in set(d["varis"])          # Kocaeli asla varış değil
    assert d.groupby(["tarih", "cikis", "varis", "slot"]).size().max() == 1
    od_pairs = set(zip(d["cikis"], d["varis"]))
    assert len(od_pairs) == 289
    assert od_pairs <= set(data.lanes)               # her talep çifti matriste var


def test_tms(data):
    assert len(data.tms) == 18
    assert "İstanbul" in data.tms and "Mardin" in data.tms


def test_resolve_file_nfc_nfd(tmp_path):
    import unicodedata
    import pytest as _pytest
    from src.data import _resolve_file
    # NFD adla kaydedilmiş dosya NFC istekle bulunur
    nfd_name = unicodedata.normalize("NFD", "Araç_test.xlsx")
    (tmp_path / nfd_name).write_bytes(b"x")
    assert _resolve_file(tmp_path, "Araç_test.xlsx").read_bytes() == b"x"
    # birebir mevcut ad direkt bulunur
    (tmp_path / "duz.xlsx").write_bytes(b"y")
    assert _resolve_file(tmp_path, "duz.xlsx").name == "duz.xlsx"
    # hiç yoksa net FileNotFoundError
    with _pytest.raises(FileNotFoundError):
        _resolve_file(tmp_path, "yok.xlsx")


def _mock_excel(tmp_path, monkeypatch, filename, frame):
    (tmp_path / filename).touch()
    monkeypatch.setattr(
        data_module.pd, "read_excel", lambda _path: frame.copy())


def _vehicle_frame():
    return pd.DataFrame({
        "Araç Adı": ["Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"],
        "Kapasite (desi)": [22400, 16800, 11200, 5600],
        "Kiralık Araç Saatlik Kira (TL)": [1, 1, 1, 1],
        "Kiralık Araç Kilometre Başına Maliyet (TL)": [1, 1, 1, 1],
        "Spot Araç Saatlik Kira (TL)": [1, 1, 1, 1],
        "Spot Kilometre Başına Maliyet (TL)": [1, 1, 1, 1],
    })


def _rental_frame():
    return pd.DataFrame({
        "Çıkış Transfer Merkezi": ["İstanbul"],
        "Varış Transfer Merkezi": ["Yalova"],
        "Araç sayısı": [1],
        "Araç Türü": ["Tır"],
    })


def test_data_dir_is_relative_to_project_root():
    project_root = Path(data_module.__file__).resolve().parents[1]
    assert DATA_DIR == project_root / "datas"
    assert DATA_DIR.is_absolute()


def test_duplicate_vehicle_records_raise_value_error(tmp_path, monkeypatch):
    frame = _vehicle_frame()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    filename = "Araç_Kapasite_Maliyet_Saat.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match="Tekrar eden araç kaydı"):
        data_module._load_vehicles(tmp_path)


@pytest.mark.parametrize("bad_capacity", [0, -1, "geçersiz"])
def test_invalid_vehicle_capacity_raises_value_error(
        tmp_path, monkeypatch, bad_capacity):
    frame = _vehicle_frame()
    frame["Kapasite (desi)"] = frame["Kapasite (desi)"].astype(object)
    frame.loc[0, "Kapasite (desi)"] = bad_capacity
    filename = "Araç_Kapasite_Maliyet_Saat.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match="Araç kapasitesi"):
        data_module._load_vehicles(tmp_path)


def test_duplicate_lane_records_raise_value_error(tmp_path, monkeypatch):
    frame = pd.DataFrame({
        "cikis": ["İstanbul", "İstanbul"],
        "varis": ["Yalova", "Yalova"],
    })
    filename = "sehirler_arasi_lojistik.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match="Tekrar eden hat kaydı"):
        data_module._load_lanes(tmp_path)


@pytest.mark.parametrize(
    ("value", "allow_zero", "require_integer", "message"),
    [
        (-1, True, True, "Tır kapasitesi negatif olamaz"),
        ("geçersiz", False, False, "Elleçleme kapasitesi sayısal"),
        (0, False, False, "Elleçleme kapasitesi pozitif olmalı"),
    ],
)
def test_invalid_transfer_capacity_raises_value_error(
        tmp_path, monkeypatch, value, allow_zero, require_integer, message):
    frame = pd.DataFrame({"tm": ["İstanbul"], "kapasite": [value]})
    filename = "kapasite.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match=message):
        data_module._load_capacity_table(
            tmp_path, filename, "tm", "kapasite",
            "Tır kapasitesi" if allow_zero else "Elleçleme kapasitesi",
            allow_zero=allow_zero, require_integer=require_integer)


def test_duplicate_transfer_capacity_records_raise_value_error(
        tmp_path, monkeypatch):
    frame = pd.DataFrame({
        "tm": ["İstanbul", "İstanbul"],
        "kapasite": [1, 2],
    })
    filename = "kapasite.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match="Tekrar eden Tır kapasitesi kaydı"):
        data_module._load_capacity_table(
            tmp_path, filename, "tm", "kapasite", "Tır kapasitesi",
            allow_zero=True, require_integer=True)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("Araç sayısı", 0, "Kiralık araç sayısı pozitif olmalı"),
        ("Araç sayısı", -1, "Kiralık araç sayısı pozitif olmalı"),
        ("Araç sayısı", "geçersiz", "Kiralık araç sayısı sayısal"),
        ("Varış Transfer Merkezi", "İstanbul", "çıkış ve varışı aynı"),
        ("Araç Türü", "Bisiklet", "Kiralık araç türü geçersiz"),
    ],
)
def test_invalid_rental_route_raises_value_error(
        tmp_path, monkeypatch, column, value, message):
    frame = _rental_frame()
    frame["Araç sayısı"] = frame["Araç sayısı"].astype(object)
    frame.loc[0, column] = value
    filename = "Kiralık_Araclar.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match=message):
        data_module._load_rentals(tmp_path)


def test_duplicate_rental_routes_raise_value_error(tmp_path, monkeypatch):
    frame = pd.concat([_rental_frame(), _rental_frame()], ignore_index=True)
    filename = "Kiralık_Araclar.xlsx"
    _mock_excel(tmp_path, monkeypatch, filename, frame)

    with pytest.raises(ValueError, match="Tekrar eden kiralık araç rotası"):
        data_module._load_rentals(tmp_path)


def test_rental_route_must_exist_in_lane_matrix():
    rental = RentalRoute("İstanbul", "Yalova", 1, "Tır")

    with pytest.raises(ValueError, match="hat matrisinde bulunamadı"):
        data_module._validate_rental_routes([rental], {})
