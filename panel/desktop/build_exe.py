#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""panel/dist-tek/index.html  ->  panel/dist-exe/Anahat-Sevkiyat-Panosu.exe

Tek dosyalık, kurulum gerektirmeyen bir Windows uygulaması üretir.
Pano HTML'i .exe'nin içine gömülür; çalışırken internet ya da yerel sunucu
gerekmez.

Kullanım:
    cd panel
    npm run paket            # build:tek + build:exe zinciri
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
VERSION = "2.0.0"


def _pywebview_var() -> bool:
    """pywebview kurulu mu?

    Kurulu değilse PyInstaller yalnızca 'hidden import not found' UYARISI verir,
    0 dönüş koduyla başarılı biter ve açılışta sessizce ölen bir exe üretir.
    """
    try:
        import webview  # noqa: F401
    except Exception:
        return False
    return True


def on_kontrol() -> str | None:
    """Derlemeyi engelleyen ilk sorunu döndür; sorun yoksa None."""
    if not SINGLE.is_file():
        return (
            f"{SINGLE} yok.\n"
            "Önce tek dosyalık HTML'i üretin:  npm run build:tek"
        )
    if not _pywebview_var():
        return (
            "pywebview kurulu değil. Onsuz üretilen .exe açılışta sessizce ölür.\n"
            "Kurulum:  pip install -r requirements.txt"
        )
    return None


def _version_file() -> pathlib.Path:
    """SmartScreen itibarı için exe sürüm/üretici üstverisi."""
    major, minor, patch = (int(x) for x in VERSION.split("."))
    p = STAGE / "surum.txt"
    p.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041f04b0', [
      StringStruct('CompanyName', 'Takim Buke - TEKNOFEST 2026'),
      StringStruct('FileDescription', 'Anahat Sevkiyat Panosu'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', '{NAME}'),
      StringStruct('OriginalFilename', '{NAME}.exe'),
      StringStruct('ProductName', 'Anahat Sevkiyat Panosu'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1055, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return p


def main() -> int:
    hata = on_kontrol()
    if hata:
        print("HATA: " + hata)
        return 1

    if STAGE.exists():
        shutil.rmtree(STAGE)
    pano = STAGE / "pano"
    pano.mkdir(parents=True)
    shutil.copy2(SINGLE, pano / "index.html")

    sep = ";" if sys.platform == "win32" else ":"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", NAME,
        "--distpath", str(DIST),
        "--workpath", str(STAGE / "work"),
        "--specpath", str(STAGE),
        "--add-data", f"{pano}{sep}pano",
        "--hidden-import", "webview.platforms.edgechromium",
        "--hidden-import", "clr_loader",
    ]
    if sys.platform == "win32":
        args += ["--version-file", str(_version_file())]
    icon = HERE / "pano.ico"
    if icon.is_file():
        args += ["--icon", str(icon)]
    args.append(str(HERE / "app.py"))

    print("PyInstaller çalışıyor…")
    try:
        r = subprocess.run(args, cwd=str(PANEL))
        kod = r.returncode
    finally:
        # Erken dönüşte de temizlensin: eskiden PyInstaller hatasında .stage kalıyordu.
        shutil.rmtree(STAGE, ignore_errors=True)

    if kod != 0:
        print(f"HATA: PyInstaller {kod} döndürdü.")
        return kod

    exe = DIST / f"{NAME}.exe"
    if not exe.is_file():
        print(f"HATA: PyInstaller 0 döndürdü ama {exe} oluşmadı.")
        return 1

    mb = exe.stat().st_size / 1e6
    print(f"\nhazır  {exe}  ·  {mb:,.1f} MB")
    print("Çift tıklayıp açabilirsiniz; kurulum ve internet gerekmez.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
