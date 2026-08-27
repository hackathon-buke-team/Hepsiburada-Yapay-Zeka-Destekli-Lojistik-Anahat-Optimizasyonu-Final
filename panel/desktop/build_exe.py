#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""panel/dist-tek/index.html  ->  panel/dist-exe/Anahat-Sevkiyat-Panosu.exe

Tek dosyalık, kurulum gerektirmeyen bir Windows uygulaması üretir.
Pano HTML'i .exe'nin içine gömülür; çalışırken internet ya da yerel sunucu
gerekmez.

Kullanım:
    cd panel
    npm run build:tek          # önce tek dosyalık HTML'i üret
    python desktop/build_exe.py
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = pathlib.Path(__file__).resolve().parent           # panel/desktop
PANEL = HERE.parent                                      # panel
SINGLE = PANEL / "dist-tek" / "index.html"
STAGE = HERE / ".stage"                                  # geçici derleme alanı
DIST = PANEL / "dist-exe"
NAME = "Anahat-Sevkiyat-Panosu"


def main() -> int:
    if not SINGLE.is_file():
        print("HATA: dist-tek/index.html yok. Önce `npm run build:tek` çalıştırın.")
        return 1

    # PyInstaller --add-data için tek dosyayı 'pano/' altında topla
    pano = STAGE / "pano"
    if STAGE.exists():
        shutil.rmtree(STAGE)
    pano.mkdir(parents=True)
    shutil.copy2(SINGLE, pano / "index.html")

    icon = HERE / "pano.ico"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", NAME,
        "--distpath", str(DIST),
        "--workpath", str(STAGE / "work"),
        "--specpath", str(STAGE),
        # Windows'ta ayırıcı ';' — pano/ klasörü .exe içine gömülür
        "--add-data", f"{pano}{';' if sys.platform == 'win32' else ':'}pano",
        "--hidden-import", "webview.platforms.edgechromium",
        "--hidden-import", "clr_loader",
        str(HERE / "app.py"),
    ]
    if icon.is_file():
        args[args.index("--windowed") + 1:args.index("--windowed") + 1] = ["--icon", str(icon)]

    print("PyInstaller çalışıyor…\n  " + " ".join(args[:10]) + " …")
    r = subprocess.run(args, cwd=str(PANEL))
    if r.returncode != 0:
        return r.returncode

    exe = DIST / f"{NAME}.exe"
    if exe.is_file():
        mb = exe.stat().st_size / 1e6
        print(f"\nhazır  {exe}  ·  {mb:,.1f} MB")
        print("Çift tıklayıp açabilirsiniz; kurulum ve internet gerekmez.")
    shutil.rmtree(STAGE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
