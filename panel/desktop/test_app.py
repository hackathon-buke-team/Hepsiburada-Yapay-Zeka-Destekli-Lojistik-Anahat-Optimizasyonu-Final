# -*- coding: utf-8 -*-
"""app.py'nin saf yardımcılarının testleri (GUI başlatmadan)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import app  # noqa: E402


def test_pencere_olcusu_buyuk_ekranda_tavan_uygulanir():
    assert app.pencere_olcusu(2560, 1440) == (1680, 980)


def test_pencere_olcusu_kucuk_ekrana_sigar():
    w, h = app.pencere_olcusu(1366, 768)
    assert w <= 1366 and h <= 768
    assert w >= 900 and h >= 600


def test_pencere_olcusu_cok_kucuk_ekranda_asgari_korunur():
    w, h = app.pencere_olcusu(800, 600)
    assert (w, h) == (900, 600)


def test_find_index_bulamazsa_PanoYok_firlatir(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "resource_dir", lambda: tmp_path)
    with pytest.raises(app.PanoYok):
        app.find_index()


def test_find_index_gomulu_panoyu_once_secer(monkeypatch, tmp_path):
    for rel in ("pano/index.html", "dist-tek/index.html", "dist/index.html"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(app, "resource_dir", lambda: tmp_path)
    assert app.find_index() == tmp_path / "pano" / "index.html"
