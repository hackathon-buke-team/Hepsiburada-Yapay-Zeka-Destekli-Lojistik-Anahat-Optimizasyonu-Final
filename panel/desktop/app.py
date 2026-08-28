#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anahat Sevkiyat Panosu — masaüstü kabuğu.

Panonun tamamı tek bir HTML dosyasına gömülüdür (panel/dist-tek/index.html).
Bu betik onu yerel bir pencerede açar: internet bağlantısı, kurulum ya da
tarayıcı ayarı gerekmez. Windows'ta WebView2 (Edge) motoru kullanılır.

Hiçbir başarısızlık sessiz kalmaz: pano bulunamazsa, pywebview yüklenemezse ya
da pencere açılamazsa kullanıcıya bir ileti kutusu gösterilir ve HTML varsayılan
tarayıcıda açılmaya çalışılır. Konsolsuz (--windowed) bir .exe'de stderr'e yazmak
kullanıcıya hiçbir şey göstermez; bu yüzden ileti kutusu şart.

Geliştirirken:      python desktop/app.py
Tek dosya .exe:     npm run paket
"""
from __future__ import annotations

import os
import pathlib
import sys
import traceback
import webbrowser

APP_TITLE = "Anahat Sevkiyat Panosu · Takım Büke · TEKNOFEST 2026"

#: Pencerenin açılış tavanı; ekran küçükse aşağı çekilir.
TAVAN_W, TAVAN_H = 1680, 980
#: Pencere bunun altına inmez.
TABAN_W, TABAN_H = 900, 600


class PanoYok(RuntimeError):
    """Gömülü pano HTML'i bulunamadı."""


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
    raise PanoYok(
        "Pano dosyası bulunamadı.\n\n"
        "Geliştirme ortamındaysanız önce derleyin:\n"
        "    cd panel && npm run build:tek"
    )


def pencere_olcusu(ekran_w: int, ekran_h: int) -> tuple[int, int]:
    """Ekrana sığan açılış ölçüsü — kenarlarda %8 pay bırakır.

    Sabit 1680x980 açılış, 1366x768 bir jüri dizüstüsünde ya da projeksiyon
    çıkışında pencereyi ekrandan taşırıyordu.
    """
    w = min(TAVAN_W, int(ekran_w * 0.92))
    h = min(TAVAN_H, int(ekran_h * 0.92))
    return max(w, TABAN_W), max(h, TABAN_H)


def hata_goster(baslik: str, mesaj: str) -> None:
    """Konsolsuz (.exe) ortamda da görünen hata bildirimi."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, mesaj, baslik, 0x10)
    except Exception:
        print(f"{baslik}: {mesaj}", file=sys.stderr)


def _ekran_olcusu() -> tuple[int, int]:
    """Birincil ekranın piksel ölçüsü; okunamazsa güvenli varsayılan."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return TAVAN_W, TAVAN_H


def main() -> int:
    try:
        index = find_index()
    except PanoYok as e:
        hata_goster("Anahat Sevkiyat Panosu", str(e))
        return 2

    try:
        import webview
    except Exception:
        hata_goster(
            "Anahat Sevkiyat Panosu",
            "Pencere motoru (pywebview) yüklenemedi.\n"
            "Pano varsayılan tarayıcınızda açılacak.",
        )
        webbrowser.open(index.as_uri())
        return 3

    w, h = pencere_olcusu(*_ekran_olcusu())
    try:
        webview.create_window(
            APP_TITLE,
            url=index.as_uri(),
            width=w,
            height=h,
            min_size=(TABAN_W, TABAN_H),
            background_color="#070a0f",
            text_select=True,
            confirm_close=False,
        )
        # gui=None -> platform varsayılanı (Windows'ta EdgeChromium/WebView2)
        webview.start(debug=bool(os.environ.get("PANO_DEBUG")))
    except Exception:
        hata_goster(
            "Anahat Sevkiyat Panosu",
            "Pencere açılamadı — bu bilgisayarda WebView2 (Edge) çalışma zamanı "
            "bulunmuyor olabilir.\n\nPano varsayılan tarayıcınızda açılacak.\n\n"
            + traceback.format_exc(limit=2),
        )
        webbrowser.open(index.as_uri())
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
