#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anahat Sevkiyat Panosu — masaüstü kabuğu.

Panonun tamamı tek bir HTML dosyasına gömülüdür (panel/dist-tek/index.html).
Bu betik onu yerel bir pencerede açar: internet bağlantısı, kurulum ya da
tarayıcı ayarı gerekmez. Windows'ta WebView2 (Edge) motoru kullanılır.

Geliştirirken:      python desktop/app.py
Tek dosya .exe:     python desktop/build_exe.py
"""
from __future__ import annotations

import os
import pathlib
import sys

import webview

APP_TITLE = "Anahat Sevkiyat Panosu · Takım Büke · TEKNOFEST 2026"


def resource_dir() -> pathlib.Path:
    """PyInstaller ile paketlendiğinde veriler _MEIPASS altına açılır."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return pathlib.Path(base)
    return pathlib.Path(__file__).resolve().parent.parent


def find_index() -> pathlib.Path:
    """Gömülü tek dosyalık panoyu bul; yoksa çok dosyalı yapıya düş."""
    root = resource_dir()
    for rel in ("pano/index.html", "dist-tek/index.html", "dist/index.html"):
        p = root / rel
        if p.is_file():
            return p
    raise SystemExit(
        "Pano dosyası bulunamadı.\n"
        "Önce derleyin:  npm run build:tek   (panel/ klasöründe)"
    )


def main() -> int:
    index = find_index()
    webview.create_window(
        APP_TITLE,
        url=index.as_uri(),
        width=1680,
        height=980,
        min_size=(1100, 700),
        background_color="#070a0f",
        text_select=True,
        confirm_close=False,
    )
    # gui=None -> platform varsayılanı (Windows'ta EdgeChromium/WebView2)
    webview.start(debug=bool(os.environ.get("PANO_DEBUG")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
