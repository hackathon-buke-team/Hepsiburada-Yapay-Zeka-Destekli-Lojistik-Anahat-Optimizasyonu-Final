# -*- coding: utf-8 -*-
"""build_exe.py'nin ön kontrollerinin testleri (PyInstaller çalıştırmadan)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_exe  # noqa: E402


def test_on_kontrol_html_yoksa_hata_dondurur(monkeypatch, tmp_path):
    monkeypatch.setattr(build_exe, "SINGLE", tmp_path / "yok.html")
    hata = build_exe.on_kontrol()
    assert hata is not None and "build:tek" in hata


def test_on_kontrol_pywebview_yoksa_hata_dondurur(monkeypatch, tmp_path):
    html = tmp_path / "index.html"
    html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(build_exe, "SINGLE", html)
    monkeypatch.setattr(build_exe, "_pywebview_var", lambda: False)
    hata = build_exe.on_kontrol()
    assert hata is not None and "pywebview" in hata


def test_on_kontrol_hepsi_tamamsa_none_dondurur(monkeypatch, tmp_path):
    html = tmp_path / "index.html"
    html.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(build_exe, "SINGLE", html)
    monkeypatch.setattr(build_exe, "_pywebview_var", lambda: True)
    assert build_exe.on_kontrol() is None
