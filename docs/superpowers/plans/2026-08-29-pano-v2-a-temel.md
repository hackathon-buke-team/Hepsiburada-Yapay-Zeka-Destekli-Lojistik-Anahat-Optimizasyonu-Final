# Pano v2 · A Planı — Temel (derleme · onarım · durum) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Panoyu ilk kez derlenebilir/çalışır hâle getirmek, ekrandaki tüm sayı çelişkilerini ve elle yazılmış sabitleri kapatmak, ve tüm durumu URL'ye serileştirilebilir tek bir store'da toplamak.

**Architecture:** `final-teslim/src/` hiç değiştirilmez. Veri üretimi `panel/kaynak/build_panel_data.py` içinde genişletilir ve her yeni sayı bir `assert` kapısıyla korunur. Pano tarafında dağınık durum (`App.filter` + `MapView` yerel + `Fleet` yerel) tek bir `panel/src/pano.ts` store'una toplanır ve URL hash'ine serileştirilir; görünümler artık unmount edilmez.

**Tech Stack:** Python 3.11 + openpyxl (veri üretimi) · React 18 + TypeScript 5.6 + Vite 5 (pano) · vitest 2 (saf fonksiyon testleri) · pywebview + PyInstaller (masaüstü)

**Spec:** `docs/superpowers/specs/2026-08-29-pano-v2-design.md`

## Global Constraints

- `final-teslim/src/` altındaki hiçbir dosya değiştirilmez (şartname Bölüm 8).
- Panoda dış istek yok: CDN, font sunucusu, harita servisi, yerel HTTP sunucusu yasak.
- `npm run build` (`tsc -b` · `strict` · `noUnusedLocals` · `noUnusedParameters`) **0 hata** vermek zorunda.
- Panoda elle yazılmış jüri-kritik sayı bırakılmaz; bağlanamayan varsa ekranda kaynağı yazılır.
- Her yeni türetilmiş sayı `build_panel_data.py` içinde bir `assert` ile korunur.
- Türkçe arayüz metni; sayı biçimi `tr-TR` (binlik `.`, ondalık `,`).
- Ölçülmüş gerçekler (bu plan bunlara dayanıyor, yeniden ölçme):
  - deck `Stage 3.avg_fill = 79.03` = spot araçların **çıkış bacağı** doluluk ortalaması (ölçüldü: 79,0243)
  - pano `meta.avg_fill = 79.34` = spot araçların **tepe yük** doluluk ortalaması (ölçüldü: 79,3369)
  - deck `spot_below_30 = 30` (çıkış tanımı) · pano histogramı `29` (tepe tanımı)
  - Farkı yaratan tek araç: **V0541**, Kamyonet, 4 durak, Erzincan→Mardin→Şanlıurfa→Mersin→Zonguldak; çıkış %25,9 → Mardin'de yük alıp %30,3
  - `Σload = Σdrop = 4.977.975 desi` (= `forecast.total`); `meta.desi = 6.565.183` bacak toplamı, aktarma katsayısı 1,319
  - `tsc -b` bugün 0 hata veriyor; `npm ci` 75 paket

---

### Task 1: Masaüstü bağımlılıkları ve tek dosyalık HTML

**Files:**
- Create: `panel/requirements.txt`
- Modify: `panel/package.json` (scripts)
- Test: elle doğrulama (aşağıdaki komutlar)

**Interfaces:**
- Consumes: yok
- Produces: `panel/dist-tek/index.html` (Task 3 ve 4 bunu tüketir); `npm run paket` script'i

- [ ] **Step 1: Panel için ayrı bir requirements dosyası yaz**

`panel/requirements.txt`:

```
# Anahat Sevkiyat Panosu — masaüstü (.exe) ve veri üretimi bağımlılıkları.
# Teslim paketinin (final-teslim/requirements.txt) bağımlılıkları BUNA DAHİL DEĞİLDİR;
# pano ayrı bir araçtır ve değerlendirmeye girmez.
openpyxl>=3.1
pywebview>=5.0
pyinstaller>=6.0
```

- [ ] **Step 2: Bağımlılıkları kur ve doğrula**

Run:
```bash
cd panel && pip install -r requirements.txt && python -c "import webview; print('pywebview', webview.__version__)"
```
Expected: sürüm numarası basılır (bugün kurulu DEĞİL; `pip show pywebview` → "Package(s) not found").

- [ ] **Step 3: `paket` script'ini ekle**

`panel/package.json` içindeki `"scripts"` bloğuna ekle (mevcut satırları koru):

```json
    "paket": "npm run build:tek && npm run build:exe",
    "test": "vitest run"
```

- [ ] **Step 4: Tek dosyalık HTML'i üret**

Run:
```bash
cd panel && npm run build:tek && ls -la dist-tek/
```
Expected: `dist-tek/index.html` tek dosya, ~1,5–2 MB (panel.json gömülü).

- [ ] **Step 5: Tarayıcıda açılışını doğrula**

Run:
```bash
cd panel && python -c "import pathlib,webbrowser; webbrowser.open(pathlib.Path('dist-tek/index.html').resolve().as_uri())"
```
Expected: Pano açılır, ÖZET görünümü gelir, konsol hatası yok. Bu dosya aynı zamanda jüri masasındaki **yedek plandır** (exe açılmazsa USB'den çift tıkla açılır).

- [ ] **Step 6: Commit**

```bash
git add panel/requirements.txt panel/package.json
git commit -m "pano: masaüstü bağımlılıkları ve tek komutluk paket script'i"
```

---

### Task 2: `app.py` sağlamlaştırma — sessiz ölümü kapat

**Files:**
- Modify: `panel/desktop/app.py`
- Test: `panel/desktop/test_app.py` (yeni)

**Interfaces:**
- Consumes: `panel/dist-tek/index.html` (Task 1)
- Produces: `pencere_olcusu(ekran_w, ekran_h) -> tuple[int,int]`, `hata_goster(baslik, mesaj) -> None`, `find_index() -> pathlib.Path` (artık `PanoYok` fırlatır)

**Neden:** Bugün tek hata yolu `raise SystemExit(...)` ve mesaj stderr'e yazılıyor. `--windowed` PyInstaller exe'sinde stderr yoktur → kullanıcı hiçbir şey görmeden exe kapanır. `webview.start()` de hiçbir `try/except` ile sarılmamış: WebView2 yoksa aynı sessiz ölüm. Jüri masasındaki en olası başarısızlık kipi "çift tıkladım, hiçbir şey olmadı". Ayrıca pencere 1680×980 sabit açılıyor; 1366×768 bir dizüstünde taşıyor.

- [ ] **Step 1: Başarısız testi yaz**

`panel/desktop/test_app.py`:

```python
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
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `cd panel && python -m pytest desktop/test_app.py -v`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'pencere_olcusu'`

- [ ] **Step 3: `app.py`'yi yeniden yaz**

`panel/desktop/app.py` dosyasının tamamını şununla değiştir:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anahat Sevkiyat Panosu — masaüstü kabuğu.

Panonun tamamı tek bir HTML dosyasına gömülüdür (panel/dist-tek/index.html).
Bu betik onu yerel bir pencerede açar: internet bağlantısı, kurulum ya da
tarayıcı ayarı gerekmez. Windows'ta WebView2 (Edge) motoru kullanılır.

Hiçbir başarısızlık sessiz kalmaz: pano bulunamazsa, WebView2 yoksa ya da
pencere açılamazsa kullanıcıya bir ileti kutusu gösterilir ve HTML varsayılan
tarayıcıda açılmaya çalışılır.

Geliştirirken:      python desktop/app.py
Tek dosya .exe:     python desktop/build_exe.py
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
    """Ekrana sığan açılış ölçüsü — kenarlarda %8 pay bırakır."""
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
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `cd panel && python -m pytest desktop/test_app.py -v`
Expected: 4 test PASS

- [ ] **Step 5: Pencereyi gerçekten aç**

Run: `cd panel && python desktop/app.py`
Expected: Pano penceresi açılır (ekrana sığmış boyutta). Kapat.

- [ ] **Step 6: Commit**

```bash
git add panel/desktop/app.py panel/desktop/test_app.py
git commit -m "pano: masaüstü kabuğunda sessiz ölümü kapat (ileti kutusu + tarayıcı yedeği + ekrana sığan pencere)"
```

---

### Task 3: `build_exe.py` sağlamlaştırma

**Files:**
- Modify: `panel/desktop/build_exe.py`
- Test: `panel/desktop/test_build_exe.py` (yeni)

**Interfaces:**
- Consumes: `panel/dist-tek/index.html` (Task 1), `panel/desktop/app.py` (Task 2)
- Produces: `panel/dist-exe/Anahat-Sevkiyat-Panosu.exe`

**Neden:** Bugün betik yalnız `dist-tek/index.html` varlığını kontrol ediyor. `pywebview` kurulu değilse PyInstaller "hidden import not found" **uyarısı** verip 0 dönüş koduyla başarılı biter ve açılışta sessizce ölen bir exe üretir. Ayrıca PyInstaller başarısız olursa erken `return` `shutil.rmtree(STAGE)` satırına ulaşmıyor, ve exe hiç oluşmasa bile betik 0 dönüyor.

- [ ] **Step 1: Başarısız testi yaz**

`panel/desktop/test_build_exe.py`:

```python
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
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `cd panel && python -m pytest desktop/test_build_exe.py -v`
Expected: FAIL — `AttributeError: module 'build_exe' has no attribute 'on_kontrol'`

- [ ] **Step 3: `build_exe.py`'yi yeniden yaz**

`panel/desktop/build_exe.py` dosyasının tamamını şununla değiştir:

```python
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
    """pywebview kurulu mu? Kurulu değilse PyInstaller sessizce bozuk exe üretir."""
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
      StringStruct('CompanyName', 'Takım Büke · TEKNOFEST 2026'),
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
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `cd panel && python -m pytest desktop/ -v`
Expected: 7 test PASS (Task 2'nin 4'ü + bu 3'ü)

- [ ] **Step 5: Commit**

```bash
git add panel/desktop/build_exe.py panel/desktop/test_build_exe.py
git commit -m "pano: exe derleyicisine ön kontrol, güvenilir çıkış kodu ve sürüm üstverisi"
```

---

### Task 4: Exe'yi üret ve açılışını doğrula

**Files:**
- Modify: yok (yalnız üretim ve doğrulama)

**Interfaces:**
- Consumes: Task 1, 2, 3
- Produces: `panel/dist-exe/Anahat-Sevkiyat-Panosu.exe` — ilk kez var olan çalışan exe

- [ ] **Step 1: Paketi üret**

Run: `cd panel && npm run paket`
Expected: `hazır  …\dist-exe\Anahat-Sevkiyat-Panosu.exe  ·  NN,N MB`, çıkış kodu 0

- [ ] **Step 2: Exe'yi çalıştır**

Run: `cd panel && ./dist-exe/Anahat-Sevkiyat-Panosu.exe &`
Expected: 2–5 sn içinde pano penceresi açılır (onefile açma gecikmesi normaldir). ÖZET görünümü gelir, harita sekmesi çalışır. Pencereyi kapat.

- [ ] **Step 3: Yedek dosyayı yerine koy**

Run:
```bash
cd panel && mkdir -p ../zzips/pano-yedek && cp dist-tek/index.html ../zzips/pano-yedek/pano-tek-dosya.html && ls -la ../zzips/pano-yedek/
```
Expected: Tek dosyalık HTML kopyalandı. Jüri masasında exe açılmazsa bu dosya herhangi bir tarayıcıda çift tıkla açılır.

- [ ] **Step 4: README'nin exe iddiasını gerçek boyutla düzelt**

`panel/README.md` içindeki masaüstü satırında geçen `(~15 MB)` ifadesini Step 1'de ölçülen gerçek boyutla değiştir.

- [ ] **Step 5: Commit**

```bash
git add panel/README.md zzips/pano-yedek/
git commit -m "pano: ilk çalışan exe üretildi, tek dosyalık yedek USB kopyası eklendi"
```

---

### Task 5: Veri üreticisi onarımı — kırpma, tır tekilleştirme, yeni meta alanları

**Files:**
- Modify: `panel/kaynak/build_panel_data.py:183-184`, `:303-309`, `:385-399`, `:415-434`
- Modify: `panel/src/types.ts:3-20` (Meta arayüzü)

**Interfaces:**
- Consumes: yok
- Produces: `panel.json` içinde yeni alanlar — `meta.desi_teslim: number`, `meta.avg_fill_cikis: number`, `meta.spot_below_30_cikis: number`, `meta.spot_below_30_tepe: number`, `meta.built_at: string` (ISO), `meta.src_plan: string` (16 hane), `meta.src_forecast: string` (16 hane), `meta.transfer_carpani: number`. `legs[].ids` artık kırpılmaz.

**Neden:**
1. `legs[].ids` 24'te kırpılıyor → 7 bacakta toplam 27 talep kimliği kalıcı kayıp; `Fleet.tsx:499`'daki "önceki bacaktan devreden yük" rozeti o bacaklarda yanlış negatif verebiliyor. B planındaki talep izleme de buna bağlı.
2. Tır ızgarası hakemin `(araç, ziyaret)` tekilleştirmesini uygulamıyor: bacağın kalkışına +1, varışına +1 yazıyor. Zincirdeki ara durakta indir+yükle hakem için **tek** ziyaret. Bugün örtüşmesinin tek sebebi 99 tırın tamamının tek bacaklı (`stops=1`) olması — plana tek bir çok bacaklı tır zinciri girse pano hakemde olmayan hayalî bir ihlal gösterirdi.
3. Elleçleme için tutarlılık kapısı var, tır için yok (asimetri).
4. `%79,03` ↔ `%79,34` ve `30` ↔ `29` çelişkilerinin kökü iki farklı doluluk tanımı; ikisini de üretip birbirini doğrulatacağız.

- [ ] **Step 1: `ids` kırpmasını kaldır**

`panel/kaynak/build_panel_data.py:183-184`'te:

```python
    L["idset"].add(str(r[9]).split("-")[0])
    if len(L["ids"]) < 24:
        L["ids"].append(r[9])
```

şununla değiştir:

```python
    L["idset"].add(str(r[9]).split("-")[0])
    L["ids"].append(r[9])
```

- [ ] **Step 2: Tır ızgarasını hakemin sayım kuralıyla hizala**

`panel/kaynak/build_panel_data.py:303-309`'daki blok:

```python
tirv: dict[tuple, int] = {}
for L in legs:
    if L["vt"] != "Tır":
        continue
    tirv[(L["a"], L["t0"] // 1440)] = tirv.get((L["a"], L["t0"] // 1440), 0) + 1
    tirv[(L["b"], L["t1"] // 1440)] = tirv.get((L["b"], L["t1"] // 1440), 0) + 1
tirgrid = [[tirv.get((c, d), 0) for d in range(ndays)] for c in range(18)]
```

şununla değiştir:

```python
# Hakem (src/ledger.py TirLedger) ziyaretleri (araç, ziyaret_no) çifti olarak
# TEKİLLEŞTİRİR: bacak j'nin kalkışı ziyaret j, varışı ziyaret j+1'dir. Böylece
# zincirdeki ara durakta "indir + yükle" aynı gün içindeyse TEK ziyaret sayılır.
tirv: dict[tuple, set] = {}
for V in vehicles:
    if V["vt"] != "Tır":
        continue
    for j, i in enumerate(V["legs"]):
        L = legs[i]
        tirv.setdefault((L["a"], L["t0"] // 1440), set()).add((V["id"], j))
        tirv.setdefault((L["b"], L["t1"] // 1440), set()).add((V["id"], j + 1))
tirgrid = [[len(tirv.get((c, d), ())) for d in range(ndays)] for c in range(18)]
```

- [ ] **Step 3: `hashlib` içe aktarımını ekle**

`panel/kaynak/build_panel_data.py:29` civarındaki içe aktarma bloğuna (`import math` satırının hemen üstüne) ekle:

```python
import hashlib
```

- [ ] **Step 4: Yeni meta alanlarını üret**

`panel/kaynak/build_panel_data.py`'de `meta = { ... }` sözlüğünün (satır ~385-399) hemen **üstüne** ekle:

```python
def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


# İki farklı doluluk tanımı — panoda ayrı ayrı etiketlenir:
#   çıkış  = aracın İLK bacağındaki doluluk (aşama ölçümünün / deck'in tanımı)
#   tepe   = zincir boyunca taşıdığı EN YÜKSEK yük (panonun tanımı)
# Tek bacaklı araçlarda ikisi aynıdır; yalnız yolda yük alan zincirlerde ayrışır.
spot_v = [V for V in vehicles if V["kind"] == "Spot"]
first_leg = [legs[V["legs"][0]] for V in spot_v]
```

Ardından `meta` sözlüğüne şu satırları ekle (mevcut anahtarları koru, `"avg_fill_leg"` satırından sonra):

```python
    "avg_fill_cikis": round(statistics.mean(L["fill"] for L in first_leg), 2),
    "spot_below_30_cikis": sum(1 for L in first_leg if L["fill"] < 30),
    "spot_below_30_tepe": sum(1 for V in spot_v if V["fill"] < 30),
    "desi_teslim": round(sum(L["load"] for L in legs)),
    "transfer_carpani": round(sum(L["desi"] for L in legs) / sum(L["load"] for L in legs), 3),
    "built_at": datetime.now().isoformat(timespec="seconds"),
    "src_plan": _sha(OUTDIR / "Tasima-plani.xlsx"),
    "src_forecast": _sha(OUTDIR / "Talep-tahmini.xlsx"),
```

- [ ] **Step 5: Yeni tutarlılık kapılarını ekle**

`panel/kaynak/build_panel_data.py`'nin sonundaki kapı bloğuna (satır ~434, `assert abs(tot_load - tot_drop) < 1` satırından **sonra**) ekle:

```python
# Tır ziyaret kotası — elleçleme için kapı vardı, bunun için yoktu.
tir_over = [(centres[c]["n"], d, tirgrid[c][d], centres[c]["tir"])
            for c in range(18) for d in range(ndays)
            if tirgrid[c][d] > centres[c]["tir"]]
assert not tir_over, f"tır ziyaret kotası aşımı: {tir_over[:5]}"

# Panonun ÇIKIŞ doluluğu ile aşama ölçümü bağımsız iki hesaptır; eşleşmeleri
# gerekir. Eşleşmezse ya tanım kaydı ya da veri bayatladı.
S3 = stages["stages"]["Stage 3"]
assert abs(meta["avg_fill_cikis"] - S3["avg_fill"]) < 0.02, \
    (meta["avg_fill_cikis"], S3["avg_fill"])
assert meta["spot_below_30_cikis"] == S3["spot_below_30"], \
    (meta["spot_below_30_cikis"], S3["spot_below_30"])

# Teslim edilen desi = tahmin toplamı (aktarma tekrarı olmadan).
assert meta["desi_teslim"] == forecast["total"], \
    (meta["desi_teslim"], forecast["total"])

# Kırpma kaldırıldı: her plan satırının kimliği bacaklarda temsil edilmeli.
assert sum(len(L["ids"]) for L in legs) == len(plan), \
    (sum(len(L["ids"]) for L in legs), len(plan))
```

- [ ] **Step 6: Üreticiyi çalıştır, tüm kapıların geçtiğini gör**

Run: `cd panel && python kaynak/build_panel_data.py`
Expected: `panel ok …` çıktısı, hiçbir `AssertionError` yok. Beklenen değerler: `avg_fill_cikis ≈ 79.02`, `spot_below_30_cikis = 30`, `spot_below_30_tepe = 29`, `desi_teslim = 4977975`, `transfer_carpani ≈ 1.319`.

- [ ] **Step 7: Yeni alanları TypeScript şemasına ekle**

`panel/src/types.ts` içindeki `Meta` arayüzüne ekle (mevcut alanları koru):

```typescript
  /** spot araçların ÇIKIŞ bacağı doluluk ortalaması — aşama ölçümüyle aynı tanım */
  avg_fill_cikis: number
  /** çıkışta %30 altında yüklenen spot araç sayısı (aşama ölçümüyle aynı tanım) */
  spot_below_30_cikis: number
  /** tepe yükte %30 altında kalan spot araç sayısı (pano tanımı) */
  spot_below_30_tepe: number
  /** aktarma tekrarı olmadan gerçekten teslim edilen desi (= forecast.total) */
  desi_teslim: number
  /** bacak toplamı / teslim edilen — aktarmadan gelen çarpan */
  transfer_carpani: number
  built_at: string
  src_plan: string
  src_forecast: string
```

- [ ] **Step 8: Derlemeyi doğrula**

Run: `cd panel && npx tsc -b`
Expected: çıkış kodu 0, hata yok

- [ ] **Step 9: Commit**

```bash
git add panel/kaynak/build_panel_data.py panel/src/types.ts panel/src/data/panel.json
git commit -m "veri: ids kırpması kaldırıldı, tır ziyaretleri hakemle hizalandı, iki doluluk tanımı ve koşu damgası üretiliyor"
```

---

### Task 6: Elle yazılmış sabitleri veriye bağla

**Files:**
- Modify: `panel/src/App.tsx:44-70`, `:110-125`
- Modify: `panel/src/views/MapView.tsx:33-38`
- Modify: `panel/src/views/Pipeline.tsx:205-233`

**Interfaces:**
- Consumes: `D.meta`, `D.stages.stages[k].violations`, `D.rented`, `D.history.days`, `D.forecast.daily` (Task 5)
- Produces: yok (yalnız mevcut metinlerin kaynağı değişir)

**Neden:** Ön yazı *"panodaki her sayı teslim ettiğimiz çıktılardan üretilir; elle yazılmış tek bir değer yoktur"* diyor. Bugün bu doğru değil: `App.tsx:118`'de `{ v: '0', l: 'hakem ihlali' }` düz string; `App.tsx:47/61`'de `'665 fiziksel araç · 1.064 bacak'` ve `'179 günlük geçmiş'` elle yazılı; `MapView.tsx:33`'te `'zorunlu 12 rota · 14 araç/gün'` elle yazılı. Jüri kaynağı sorarsa bunlar açık hedef.

- [ ] **Step 1: `App.tsx`'te hakem ihlalini veriden oku**

`panel/src/App.tsx`'in içe aktarma bloğuna `STAGES` ve `S`'yi ekle:

```typescript
import { D, FILTER0, S, STAGES, useSlice, type Filter } from './store'
```

`VIEWS` dizisinin **üstüne** ekle:

```typescript
/** Hakem simülatörünün her aşamada bulduğu ihlal sayısı — veriden okunur. */
const VIOL_TOTAL = STAGES.reduce((a, k) => a + Number(S(k).violations), 0)
```

`kpis` içindeki süzgeçsiz dalda `{ v: '0', l: 'hakem ihlali', c: 'ok' }` satırını şununla değiştir:

```typescript
            { v: n0(VIOL_TOTAL), l: 'hakem ihlali', c: VIOL_TOTAL === 0 ? 'ok' : 'bad' },
```

`styles.css`'te KPI şeridinin yalnız `.brand`, `.ok`, `.blue` tonları tanımlı — `.bad`
yok. Ekle (satır 156 civarı, `.kstrip .k.blue .v` satırının altına):

```css
.kstrip .k.bad .v { color: var(--bad); }
```

`--bad` değişkeni `:root`'ta tanımlı değilse `--warn`'ın yanına ekle:
`--bad: #ff5c5c;`

- [ ] **Step 2: Görünüm alt başlıklarını veriden üret**

`panel/src/App.tsx`'te `VIEWS` dizisindeki üç `sub` alanını değiştir:

`filo` girdisinde:
```typescript
    sub: `${n0(D.meta.vehicles)} fiziksel araç · ${n0(D.meta.legs)} bacak · her aracın rotası`,
```

`talep` girdisinde:
```typescript
    sub: `${n0(D.history.days.length)} günlük geçmiş · ${n0(D.forecast.daily.length)} günlük tahminimiz`,
```

`harita` girdisinde (mevcut metni koru — zaten veri iddiası içermiyor).

`VIEWS` dizisi `D` ve `n0`'a bağımlı hâle geldiği için, dizinin tanımı bu iki içe aktarmadan **sonra** gelmelidir; dosyada zaten öyledir.

- [ ] **Step 3: `MapView.tsx`'te katman ipuçlarını veriden üret**

`panel/src/views/MapView.tsx:33-38`'deki `LAYERS` dizisini şununla değiştir:

```typescript
const RENT_ROUTES = D.rented.length
const RENT_PER_DAY = D.rented.reduce((a, r) => a + r.n, 0)
const MAX_STOPS = D.stages.meta.max_chain_stops

const LAYERS: { k: LayerKey; label: string; color: string; hint: string }[] = [
  {
    k: 'kiralik',
    label: 'Kiralık rotalar',
    color: C.warn,
    hint: `zorunlu ${RENT_ROUTES} rota · ${RENT_PER_DAY} araç/gün`,
  },
  { k: 'spot', label: 'Spot atamalar', color: C.blue, hint: 'tek bacaklı spot seferler' },
  {
    k: 'zincir',
    label: 'Konsolidasyon zincirleri',
    color: C.brand,
    hint: `milk-run · 2–${MAX_STOPS} durak`,
  },
  { k: 'pickup', label: 'Yol üstü yük alma', color: C.pink, hint: 'ara durakta yük alan zincirler' },
]
```

`D`'nin bu dosyada içe aktarıldığından emin ol (zaten `store`'dan geliyor).

- [ ] **Step 4: `Pipeline.tsx`'te bağlanamayan sabitlere kaynak etiketi ekle**

`panel/src/views/Pipeline.tsx:211-212`'deki yorum bloğunu ve `LAB` tanımını koru; `LAB` sabitinin hemen **altına** ekle:

```typescript
/** LAB ve REG_TESTS panel.json'da taşınmayan deney/koşu ölçümleridir; kaynağı
    ekranda açıkça yazılır. B planında kanit.json'a bağlanacaklar. */
const LAB_KAYNAK = 'deney kütüğü · Stage 1–3 kabul raporları'
const TEST_KAYNAK = 'pytest koşusu · final-teslim/tests'
```

`TRIED` tablosunun render edildiği kartın altına (dosyadaki `TRIED.map` bloğunun kapanışından sonra) tek satırlık kaynak notu ekle:

```tsx
<p className="fine c-dim" style={{ marginTop: 10 }}>
  Bu tablodaki ölçümler plan çıktısından değil, {LAB_KAYNAK}'ndan gelir.
</p>
```

`REG_TESTS`'in gösterildiği yere (dosyada `n0(REG_TESTS)` geçen satır) aynı biçimde `{TEST_KAYNAK}` notunu ekle.

- [ ] **Step 5: Elle yazılmış sayı kalmadığını doğrula**

Run:
```bash
cd panel/src && grep -rn "665\|1\.064\|1064\|'0', l:\|179 günlük\|12 rota\|14 araç" --include=*.tsx --include=*.ts .
```
Expected: Yalnız `LAB` bloğu ve `REG_TESTS` eşleşir (ikisinin de ekranda kaynağı yazıyor). `App.tsx` ve `MapView.tsx`'ten eşleşme gelmez.

- [ ] **Step 6: Derle ve gözle doğrula**

Run: `cd panel && npx tsc -b && npm run build:tek`
Expected: 0 hata. Tarayıcıda açıp üst KPI şeridinde "hakem ihlali 0" ve FİLO alt başlığında doğru sayıların göründüğünü kontrol et.

- [ ] **Step 7: Commit**

```bash
git add panel/src/App.tsx panel/src/views/MapView.tsx panel/src/views/Pipeline.tsx
git commit -m "pano: elle yazılmış sayılar veriye bağlandı, bağlanamayanlara kaynak etiketi eklendi"
```

---

### Task 7: İki doluluk tanımını ayır ve V0541 hikâyesini göster

**Files:**
- Modify: `panel/src/views/Overview.tsx:200-215` (KPI), `:428-445` (doluluk dağılımı kartı)
- Modify: `panel/src/App.tsx` (üst KPI şeridi etiketi)

**Interfaces:**
- Consumes: `D.meta.avg_fill`, `D.meta.avg_fill_cikis`, `D.meta.spot_below_30_cikis`, `D.meta.spot_below_30_tepe` (Task 5)
- Produces: yok

**Neden:** Aynı ekranda `%79,3` ve `%79,0` yan yana duruyor; aynı kartta `30` ve `29` çelişiyor. İkisi de doğru ama farklı tanım. Ölçüldü: fark **tek araçtan** geliyor — V0541 (Kamyonet, 4 durak) Erzincan'dan %25,9 dolulukla çıkıp Mardin'de yük alarak %30,3'e çıkıyor. Bu, Stage 3'ün yol-üstü yük alma mekanizmasının tek araçta görünen kanıtıdır; gizlenecek değil gösterilecek bir şeydir.

- [ ] **Step 1: Üst KPI şeridinde tanımı etikete yaz**

`panel/src/App.tsx`'te süzgeçsiz `kpis` dalındaki doluluk satırını değiştir:

```typescript
            { v: pct(D.meta.avg_fill), l: 'tepe spot doluluk', c: 'ok' },
```

Süzgeçli daldaki satırı da aynı şekilde `'tepe spot doluluk'` yap.

- [ ] **Step 2: ÖZET KPI'ında her iki tanımı göster**

`panel/src/views/Overview.tsx`'te "Ort. spot doluluk" KPI kutusunun değerini ve alt satırını değiştir:

```tsx
{
  v: pct(D.meta.avg_fill),
  l: 'tepe spot doluluk',
  d: `çıkışta %${D.meta.avg_fill_cikis.toLocaleString('tr-TR')} · aşama ölçümüyle birebir`,
}
```

(Mevcut kutunun alan adlarını koru; yalnız `l` ve alt satır metnini değiştir.)

- [ ] **Step 3: Doluluk dağılımı kartındaki 30/29 çelişkisini hikâyeye çevir**

`panel/src/views/Overview.tsx:428-445` aralığındaki doluluk dağılımı kartının alt notunu şununla değiştir:

```tsx
<p className="fine c-dim" style={{ marginTop: 8 }}>
  Histogram <b>tepe yükü</b> ölçer: zincir boyunca taşınan en yüksek desi.
  Tepe yükte %30 altında kalan {n0(D.meta.spot_below_30_tepe)} spot araç var;
  <b> çıkışta</b> %30 altında yüklenen {n0(D.meta.spot_below_30_cikis)} araç.
  Aradaki tek araç <b>V0541</b> — Erzincan'dan %25,9 dolulukla çıkıyor, Mardin'de
  yol üstünde yük alıp %30,3'e çıkıyor. Stage 3'ün yaptığı iş tam olarak budur.
</p>
```

- [ ] **Step 4: Derle ve gözle doğrula**

Run: `cd panel && npx tsc -b && npm run build:tek`
Expected: 0 hata. Tarayıcıda ÖZET görünümünde artık aynı metriğin iki farklı değeri etiketsiz görünmüyor.

- [ ] **Step 5: Commit**

```bash
git add panel/src/App.tsx panel/src/views/Overview.tsx
git commit -m "pano: çıkış/tepe doluluk tanımları ayrıldı; 30-29 farkı V0541 örneğiyle anlatılıyor"
```

---

### Task 8: Kalan etiket onarımları — hat sayısı, tatil sayısı, desi uzlaştırma, sabit tarih

**Files:**
- Modify: `panel/src/views/Demand.tsx:214-219`, `:236-241`, `:276-282`, `:461-471`
- Modify: `panel/src/views/Pipeline.tsx:495-512`

**Interfaces:**
- Consumes: `D.meta.desi_teslim`, `D.meta.transfer_carpani` (Task 5), `D.stages.cleaning.od_in_history`
- Produces: yok

**Neden:** (a) `forecast.lane` top-60 kesiti olduğu hâlde pano "7 gün · 60 hat" diyor; gerçek hat sayısı 289 (`4.046 = 7 gün × 2 slot × 289`). (b) Aynı ekranda legend "resmî tatil · 13 gün", yan kart "15 resmî tatil" diyor — fark, `flag` dizisinde ay sonu bayrağının tatil bayrağını ezmesinden (30-31 Mayıs hem tatil hem ay sonu). (c) `Pipeline`'da `4.977.975` ve `6.565.183` aynı tabloda uzlaştırma notu olmadan yan yana. (d) `Pipeline.tsx:495-499`'da `'30.06'` dizesi ve `daily[1]`/`daily[2]` indeksleri sabit; ufuk bir gün kayarsa yanlış günü ay sonu ilan eder.

- [ ] **Step 1: Hat sayısı etiketini düzelt**

`panel/src/views/Demand.tsx:218` civarındaki KPI alt satırını değiştir:

```tsx
d={`${daily.length} gün · ${n0(D.stages.cleaning.od_in_history)} aktif hat`}
```

`:463` civarındaki hat kartının alt başlığını değiştir:

```tsx
sub={`${n0(D.stages.cleaning.od_in_history)} aktif hattın en yoğun ${FC.lane.length}'ı`}
```

`:466-469` civarındaki "ilk 12 hat %X" notunda payda olarak `FC.total` yerine gösterilen 60 hattın toplamını kullan ve etiketi buna göre yaz:

```tsx
const top60Sum = FC.lane.reduce((a, l) => a + l.desi, 0)
```
notu:
```tsx
en yoğun 12 hat, listelenen {FC.lane.length} hattın %{((topSum / top60Sum) * 100).toFixed(1)}'ini taşıyor
```

- [ ] **Step 2: Tatil sayısı çelişkisini açıkla**

`panel/src/views/Demand.tsx:236-241`'deki legend satırında tatil etiketini değiştir:

```tsx
`resmî tatil · ${flagN[1]} gün (yalnız tatil)`
```

ve `:276-282`'deki kart metnine ekle:

```tsx
15 resmî tatil + 10 ay sonu günü = 23 ayrı tarih; 2 gün (30–31 Mayıs) hem tatil
hem ay sonu olduğu için ısı haritasında ay sonu rengiyle çizilir — bu yüzden
legend'da "yalnız tatil" {flagN[1]} gün görünür.
```

- [ ] **Step 3: Desi uzlaştırma satırını ekle**

`panel/src/views/Pipeline.tsx:502-512` aralığındaki `KvTable`'ın hemen altına ekle:

```tsx
<p className="fine c-dim" style={{ marginTop: 8 }}>
  İki sayı farklı şeyi ölçer: <b>{n0(D.meta.desi_teslim)} desi</b> gerçekten
  teslim edilen yüktür (Σyükleme = Σindirme, tahmin toplamıyla birebir).
  <b> {n0(D.meta.desi)} desi</b> ise bacak toplamıdır — aktarma merkezinden geçen
  yük her bacakta yeniden sayılır. Oran <b>{D.meta.transfer_carpani.toLocaleString('tr-TR')}×</b>,
  yani hub-and-spoke ağının ölçüsü.
</p>
```

- [ ] **Step 4: Sabit ay sonu tarihini veriden türet**

`panel/src/views/Pipeline.tsx:495-499`'daki sabit metni değiştir. Önce dosyanın üst kısmına ekle:

```typescript
/** Tahmin ufkundaki ay sonu günü — veriden bulunur, sabit yazılmaz. */
const ME_IX = D.forecast.daily.findIndex((x, i, arr) => {
  const nxt = arr[i + 1]
  return nxt ? new Date(nxt.iso).getUTCDate() === 1 : false
})
```

Sonra metni şu biçimde kur (ME_IX bulunamazsa cümleyi hiç basma):

```tsx
{ME_IX >= 0 && (
  <>
    {D.forecast.daily[ME_IX].d} ay sonu: tahmin{' '}
    {n0(D.forecast.daily[ME_IX].desi)} desiye düşüyor, ertesi gün{' '}
    {n0(D.forecast.daily[ME_IX + 1].desi)} desiye fırlıyor.
  </>
)}
```

- [ ] **Step 5: Derle ve gözle doğrula**

Run: `cd panel && npx tsc -b && npm run build:tek`
Expected: 0 hata. TALEP görünümünde "289 aktif hat", MODEL görünümünde uzlaştırma notu görünür.

- [ ] **Step 6: Commit**

```bash
git add panel/src/views/Demand.tsx panel/src/views/Pipeline.tsx
git commit -m "pano: hat sayısı, tatil sayımı ve desi uzlaştırması düzeltildi; ay sonu günü veriden türetiliyor"
```

---

### Task 9: Tek serileştirilebilir durum — `pano.ts`

**Files:**
- Create: `panel/src/pano.ts`
- Create: `panel/src/pano.test.ts`
- Modify: `panel/package.json` (vitest devDependency)

**Interfaces:**
- Consumes: `Filter` (mevcut `store.ts`), `ViewId` (`App.tsx`)
- Produces:
  - `export interface PanoState { view: string; date: string; kind: 'all'|'Kiralık'|'Spot'; vt: string; chainsOnly: boolean; pickupOnly: boolean; sel: string; focus: number; mode: 'akis'|'zaman'; t: number; speed: number; zoom: number; panx: number; pany: number; layers: Record<string, boolean>; q: string }`
  - `export const PANO0: PanoState`
  - `export function toHash(s: PanoState): string`
  - `export function fromHash(h: string): PanoState`
  - `export function toFilter(s: PanoState): Filter`

**Neden:** Bugün durum üç ayrı yerde. Sonuçları: sekme değişiminde `MapView` unmount olup kip/zaman/zoom/seçim kayboluyor; "Filo tablosunda aç" seçili aracı taşımıyor; `Filter.kind`/`chainsOnly`/`pickupOnly`'yi hiçbir arayüz kurmuyor (ölü kod); URL'de yalnız sekme hash'i var. Hikâye kipi, komut paleti ve derin bağlantı (B ve C planları) tamamen buna bağlı.

- [ ] **Step 1: vitest'i kur**

Run: `cd panel && npm i -D vitest@^2.1.8`
Expected: `added N packages`

- [ ] **Step 2: Başarısız testi yaz**

`panel/src/pano.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import { PANO0, fromHash, toHash } from './pano'

describe('toHash', () => {
  it('varsayılan durumda yalnız görünümü yazar', () => {
    expect(toHash(PANO0)).toBe('#ozet')
  })

  it('varsayılandan farklı alanları sorgu dizesi olarak ekler', () => {
    const h = toHash({ ...PANO0, view: 'harita', date: '01.07.2026', sel: 'V0187' })
    expect(h.startsWith('#harita?')).toBe(true)
    expect(h).toContain('d=01.07.2026')
    expect(h).toContain('v=V0187')
  })

  it('varsayılana eşit alanları yazmaz', () => {
    const h = toHash({ ...PANO0, view: 'filo' })
    expect(h).toBe('#filo')
  })
})

describe('fromHash', () => {
  it('boş girdide varsayılanı döndürür', () => {
    expect(fromHash('')).toEqual(PANO0)
    expect(fromHash('#')).toEqual(PANO0)
  })

  it('bilinmeyen görünümü yok sayar', () => {
    expect(fromHash('#yokboyle').view).toBe(PANO0.view)
  })

  it('bilinmeyen anahtarları sessizce atar', () => {
    const s = fromHash('#harita?d=01.07.2026&zzz=9')
    expect(s.view).toBe('harita')
    expect(s.date).toBe('01.07.2026')
  })

  it('sayısal alanları çözer, bozuk sayıda varsayılana düşer', () => {
    expect(fromHash('#harita?z=2.5').zoom).toBe(2.5)
    expect(fromHash('#harita?z=abc').zoom).toBe(PANO0.zoom)
  })

  it('katman anahtarlarını çözer', () => {
    const s = fromHash('#harita?l=kiralik,zincir')
    expect(s.layers).toEqual({ kiralik: true, spot: false, zincir: true, pickup: false })
  })
})

describe('gidiş-dönüş', () => {
  it('her alanı koruyarak dönüştürür', () => {
    const s = {
      ...PANO0,
      view: 'harita',
      date: '03.07.2026',
      kind: 'Spot' as const,
      vt: 'Kamyon',
      chainsOnly: true,
      pickupOnly: true,
      sel: 'V0541',
      focus: 7,
      mode: 'zaman' as const,
      t: 1830,
      speed: 16,
      zoom: 2.4,
      panx: -120,
      pany: 40,
      layers: { kiralik: false, spot: true, zincir: true, pickup: false },
      q: 'mersin',
    }
    expect(fromHash(toHash(s))).toEqual(s)
  })
})
```

- [ ] **Step 3: Testi çalıştır, başarısız olduğunu gör**

Run: `cd panel && npx vitest run src/pano.test.ts`
Expected: FAIL — `Failed to resolve import "./pano"`

- [ ] **Step 4: `pano.ts`'yi yaz**

`panel/src/pano.ts`:

```typescript
/* Panonun TÜM durumu tek yerde ve URL'ye serileştirilebilir.
   Görünümler bu durumu okur; kendi yerel kopyalarını tutmazlar. Böylece
   sekme değişiminde hiçbir şey kaybolmaz, her ekran paylaşılabilir bir
   adrese sahip olur ve hikâye kipi tek bir durum uygulamasıyla çalışır. */
import type { Filter } from './store'

export const VIEW_IDS = ['ozet', 'harita', 'filo', 'kisit', 'talep', 'model'] as const
export const LAYER_KEYS = ['kiralik', 'spot', 'zincir', 'pickup'] as const

export interface PanoState {
  view: string
  /** '' = tüm ufuk */
  date: string
  kind: 'all' | 'Kiralık' | 'Spot'
  vt: string
  chainsOnly: boolean
  pickupOnly: boolean
  /** seçili araç kimliği, '' = seçim yok */
  sel: string
  /** odaklı merkez indeksi, -1 = odak yok */
  focus: number
  mode: 'akis' | 'zaman'
  /** zaman kipinde ufuk başlangıcından dakika */
  t: number
  speed: number
  zoom: number
  panx: number
  pany: number
  layers: Record<string, boolean>
  /** filo arama kutusu */
  q: string
}

export const PANO0: PanoState = {
  view: 'ozet',
  date: '',
  kind: 'all',
  vt: 'all',
  chainsOnly: false,
  pickupOnly: false,
  sel: '',
  focus: -1,
  mode: 'akis',
  t: 0,
  speed: 6,
  zoom: 1,
  panx: 0,
  pany: 0,
  layers: { kiralik: true, spot: true, zincir: true, pickup: true },
  q: '',
}

/** Kısa URL anahtarları — hash okunabilir kalsın diye tek harfli. */
const NUM: [keyof PanoState, string][] = [
  ['focus', 'f'],
  ['t', 't'],
  ['speed', 's'],
  ['zoom', 'z'],
  ['panx', 'px'],
  ['pany', 'py'],
]
const STR: [keyof PanoState, string][] = [
  ['date', 'd'],
  ['kind', 'k'],
  ['vt', 'vt'],
  ['sel', 'v'],
  ['q', 'q'],
]
const BOOL: [keyof PanoState, string][] = [
  ['chainsOnly', 'c'],
  ['pickupOnly', 'p'],
]

const allLayers = (l: Record<string, boolean>) => LAYER_KEYS.every((k) => l[k])

export function toHash(s: PanoState): string {
  const q = new URLSearchParams()
  for (const [key, sh] of STR) {
    const v = s[key] as string
    if (v !== (PANO0[key] as string)) q.set(sh, v)
  }
  for (const [key, sh] of NUM) {
    const v = s[key] as number
    if (v !== (PANO0[key] as number)) q.set(sh, String(v))
  }
  for (const [key, sh] of BOOL) {
    if (s[key] !== PANO0[key]) q.set(sh, '1')
  }
  if (s.mode !== PANO0.mode) q.set('m', s.mode)
  if (!allLayers(s.layers)) q.set('l', LAYER_KEYS.filter((k) => s.layers[k]).join(','))
  const qs = q.toString()
  return '#' + s.view + (qs ? '?' + qs : '')
}

export function fromHash(h: string): PanoState {
  const raw = h.startsWith('#') ? h.slice(1) : h
  const [viewPart, queryPart] = raw.split('?')
  const s: PanoState = { ...PANO0, layers: { ...PANO0.layers } }
  if (viewPart && (VIEW_IDS as readonly string[]).includes(viewPart)) s.view = viewPart
  if (!queryPart) return s

  const q = new URLSearchParams(queryPart)
  for (const [key, sh] of STR) {
    const v = q.get(sh)
    if (v !== null) (s[key] as string) = v
  }
  for (const [key, sh] of NUM) {
    const v = q.get(sh)
    if (v === null) continue
    const n = Number(v)
    if (Number.isFinite(n)) (s[key] as number) = n
  }
  for (const [key, sh] of BOOL) {
    if (q.get(sh) === '1') (s[key] as boolean) = true
  }
  const m = q.get('m')
  if (m === 'akis' || m === 'zaman') s.mode = m
  const l = q.get('l')
  if (l !== null) {
    const on = new Set(l.split(',').filter(Boolean))
    for (const k of LAYER_KEYS) s.layers[k] = on.has(k)
  }
  if (s.kind !== 'Kiralık' && s.kind !== 'Spot') s.kind = 'all'
  return s
}

/** Mevcut görünümlerin beklediği süzgeç biçimi. */
export function toFilter(s: PanoState): Filter {
  return {
    date: s.date,
    kind: s.kind,
    vt: s.vt,
    chainsOnly: s.chainsOnly,
    pickupOnly: s.pickupOnly,
  }
}
```

- [ ] **Step 5: Testleri çalıştır, geçtiğini gör**

Run: `cd panel && npx vitest run src/pano.test.ts`
Expected: 10 test PASS

- [ ] **Step 6: Derlemeyi doğrula**

Run: `cd panel && npx tsc -b`
Expected: 0 hata

- [ ] **Step 7: Commit**

```bash
git add panel/src/pano.ts panel/src/pano.test.ts panel/package.json panel/package-lock.json
git commit -m "pano: tüm durumu URL'ye serileştiren tek store (pano.ts) ve testleri"
```

---

### Task 10: Durumu bağla — görünüm korunumu, seçim taşıma, Esc panik

**Files:**
- Modify: `panel/src/App.tsx` (durum yönetimi, görünüm render'ı, kısayollar)
- Modify: `panel/src/views/MapView.tsx` (yerel `pick/focus/mode/t/speed/zoom/pan/layers` → prop)
- Modify: `panel/src/views/Fleet.tsx` (yerel `selId/q/kind/vt/onlyChains/onlyPickup` → prop)
- Modify: `panel/src/views/Constraints.tsx` (SLA satırı aracı taşısın)
- Modify: `panel/src/styles.css`

**Interfaces:**
- Consumes: `PanoState`, `PANO0`, `toHash`, `fromHash`, `toFilter` (Task 9)
- Produces: `ViewProps` genişler → `{ st: PanoState; set: (p: Partial<PanoState>) => void; filter: Filter; setFilter: (f: Filter | ((p: Filter) => Filter)) => void; go: (v: string) => void }`

**Uyumluluk kararı:** `setFilter`'ı **dört** görünüm kullanıyor (`Overview`, `MapView`,
`Fleet`, `Constraints` — toplam 11 çağrı). Hepsini `set`'e çevirmek gereksiz risk;
`setFilter` `ViewProps`'ta kalır ve `set` üzerine ince bir sarmalayıcı olarak yazılır.
`Filter`'ın beş alanı (`date`, `kind`, `vt`, `chainsOnly`, `pickupOnly`) `PanoState`'te
**aynı adlarla** bulunduğu için yayma doğrudan çalışır. Böylece yalnız `MapView` ve
`Fleet`'in derin yerel durumu taşınır; `Overview` ve `Constraints` olduğu gibi kalır.

**Neden:** `App.tsx:169`'da görünümler `{view === 'harita' && <MapView/>}` ve `key={view}` ile render ediliyor; her sekme değişiminde `MapView` unmount oluyor. `MapView.tsx:780`'deki "Filo tablosunda aç" düğmesi yalnız `go('filo')` çağırıyor, `Fleet` seçili aracı kendi yerel `selId`'sinde tuttuğu için tablo seçimsiz açılıyor. `Constraints.tsx:447-451`'de SLA satırına tıklanınca yalnız tarih taşınıyor, bacağın aracı kayboluyor.

- [ ] **Step 1: `App.tsx`'te durumu tek kaynağa çevir**

`useState<ViewId>` ve `useState<Filter>` çiftini şununla değiştir:

```typescript
const [st, setSt] = useState<PanoState>(() => fromHash(location.hash))
const set = useCallback((p: Partial<PanoState>) => setSt((s) => ({ ...s, ...p })), [])
const go = useCallback((v: string) => set({ view: v }), [set])
const filter = useMemo(() => toFilter(st), [st])
const slice = useSlice(filter)
```

Hash eşitlemesini tek bir etkiye indir:

```typescript
useEffect(() => {
  const h = toHash(st)
  if (location.hash !== h) history.replaceState(null, '', h)
}, [st])

useEffect(() => {
  const onHash = () => setSt(fromHash(location.hash))
  addEventListener('hashchange', onHash)
  return () => removeEventListener('hashchange', onHash)
}, [])
```

- [ ] **Step 2: Görünümleri unmount etmeyi bırak**

`App.tsx`'teki `<main>` bloğunu şununla değiştir:

```tsx
<main className={'view' + (cur.flush ? ' flush' : '')}>
  {VIEWS.map((v) => (
    <div key={v.id} className="vwrap" hidden={v.id !== st.view}>
      {v.id === 'ozet' && <Overview {...props} />}
      {v.id === 'harita' && <MapView {...props} />}
      {v.id === 'filo' && <Fleet {...props} />}
      {v.id === 'kisit' && <Constraints {...props} />}
      {v.id === 'talep' && <Demand {...props} />}
      {v.id === 'model' && <Pipeline {...props} />}
    </div>
  ))}
</main>
```

`panel/src/styles.css`'e ekle:

```css
.vwrap { display: contents; }
.vwrap[hidden] { display: none !important; }
```

- [ ] **Step 3: `ViewProps`'u genişlet**

`App.tsx`'te:

```typescript
export interface ViewProps {
  st: PanoState
  set: (p: Partial<PanoState>) => void
  filter: Filter
  setFilter: (f: Filter | ((p: Filter) => Filter)) => void
  go: (v: string) => void
}
```

`setFilter` uyumluluk sarmalayıcısını `App.tsx`'te tanımla — `Filter`'ın beş alanı
`PanoState`'te aynı adlarla bulunduğu için yayma doğrudan çalışır:

```typescript
const setFilter = useCallback(
  (f: Filter | ((p: Filter) => Filter)) =>
    setSt((s) => ({ ...s, ...(typeof f === 'function' ? f(toFilter(s)) : f) })),
  [],
)
```

ve
```typescript
const props: ViewProps = { st, set, filter, setFilter, go }
```

- [ ] **Step 4: Esc panik sıfırlaması ve kısayol koruması ekle**

`App.tsx`'teki klavye etkisini şununla değiştir:

```typescript
useEffect(() => {
  const yaziyor = (t: EventTarget | null) =>
    t instanceof HTMLInputElement ||
    t instanceof HTMLTextAreaElement ||
    (t instanceof HTMLElement && t.isContentEditable)

  const h = (e: KeyboardEvent) => {
    if (yaziyor(e.target)) return
    if (e.key === 'Escape') {
      // panik: süzgeç, seçim, odak, katman, zoom, kip — hepsi bilinen zemine
      setSt((s) => ({ ...PANO0, view: s.view }))
      return
    }
    const i = Number(e.key)
    if (i >= 1 && i <= VIEWS.length) setSt((s) => ({ ...s, view: VIEWS[i - 1].id }))
  }
  addEventListener('keydown', h)
  return () => removeEventListener('keydown', h)
}, [])
```

Ekranın sağ altına kalıcı ipucu ekle (App'in `.main` bloğunun sonuna):

```tsx
<div className="hint-esc">Esc: sıfırla · 1-6: görünüm</div>
```

`styles.css`:
```css
.hint-esc {
  position: fixed; right: 12px; bottom: 8px; z-index: 30;
  font-size: 10.5px; color: var(--faint); pointer-events: none;
  letter-spacing: 0.02em;
}
```

- [ ] **Step 5: `MapView.tsx`'i store'a bağla**

`MapView`'daki şu `useState` çağrılarını kaldır ve `props.st` / `props.set` üzerinden oku-yaz:
`pick` → `st.sel` (araç kimliği; nesne gerektiğinde `D.vehicles.find(v => v.id === st.sel)`),
`focus` → `st.focus`, `mode` → `st.mode`, `t` → `st.t`, `speed` → `st.speed`,
`layers` → `st.layers`, zoom/pan → `st.zoom` / `st.panx` / `st.pany`.

`play` (oynat/duraklat) **yerel kalır** — URL'de taşınması anlamsız.

"Seçimi temizle" düğmesini tam sıfırlamaya çevir:

```typescript
onClick={() => set({ ...PANO0, view: 'harita' })}
```

"Filo tablosunda aç" düğmesini seçimi taşıyacak şekilde değiştir:

```typescript
onClick={() => set({ view: 'filo', sel: v.id })}
```

- [ ] **Step 6: `Fleet.tsx`'i store'a bağla**

`selId` yerel state'ini kaldır, `st.sel` kullan; seçim `set({ sel: id })` ile yazılır.
`q` arama kutusunu `st.q` / `set({ q })` ile bağla.
Yerel `kind`/`vt`/`onlyChains`/`onlyPickup` state'lerini kaldır; `st.kind` / `st.vt` /
`st.chainsOnly` / `st.pickupOnly` kullan — böylece ÖZET donut'undan gelen tür süzgeci
Fleet çiplerinde de görünür ve iki paralel süzgeç sistemi ortadan kalkar.

Seçili araç görünür değilse ona kaydır:

```typescript
useEffect(() => {
  if (!st.sel) return
  document.getElementById('arac-' + st.sel)?.scrollIntoView({ block: 'center' })
}, [st.sel])
```

Tablo satırlarına `id={'arac-' + v.id}` ekle.

- [ ] **Step 7: `Constraints.tsx`'te SLA satırının aracını taşı**

`Constraints.tsx:447-451`'deki tıklama işleyicisini değiştir:

```typescript
onClick={() => set({ view: 'filo', date: l.dd, sel: l.v })}
```

- [ ] **Step 8: Derle ve testleri koştur**

Run: `cd panel && npx tsc -b && npx vitest run`
Expected: 0 derleme hatası, tüm testler PASS

- [ ] **Step 9: Elle doğrula**

Run: `cd panel && npm run dev`
Kontrol listesi:
- ÖZET'te bir gün seç → HARİTA'ya geç → tarih süzgeci taşındı mı?
- HARİTA'da zaman kipine geç, yakınlaştır → FİLO'ya geç → HARİTA'ya dön: kip, zoom ve zaman korundu mu?
- HARİTA'da bir araca tıkla → "Filo tablosunda aç" → FİLO'da o araç seçili ve görünür mü?
- Adres çubuğundaki hash'i kopyala, yeni sekmede aç → aynı ekran mı geldi?
- `Esc` → her şey sıfırlandı mı (katmanlar ve zoom dahil)?

- [ ] **Step 10: Commit**

```bash
git add panel/src/App.tsx panel/src/views/MapView.tsx panel/src/views/Fleet.tsx panel/src/views/Constraints.tsx panel/src/styles.css
git commit -m "pano: tüm görünümler tek store'a bağlandı — durum korunumu, derin bağlantı, seçim taşıma, Esc sıfırlama"
```

---

### Task 11: Web yayın başlıkları ve dokümantasyon

**Files:**
- Modify: `panel/vercel.json`
- Modify: `panel/README.md`
- Modify: `README.md` (kök — pano yolunu düzelt)

**Interfaces:**
- Consumes: yok
- Produces: yok

**Neden:** `vercel.json`'da CSP, `X-Frame-Options`/`frame-ancestors` ve `Permissions-Policy` yok; uygulama tamamen kendi kendine yeterli olduğu için katı bir politika bedelsiz uygulanabilir. Kök `README.md` panoyu `sunum/index.html` olarak tarif ediyor; gerçek pano `panel/` altında.

- [ ] **Step 1: Güvenlik başlıklarını ekle**

`panel/vercel.json`'daki tüm yollara uygulanan `headers` girdisine ekle (mevcut üç başlığı koru):

```json
        { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=(), payment=(), usb=()" }
```

`connect-src 'none'` panonun hiç ağ isteği yapmadığını **tarayıcı düzeyinde** zorlar — İ4'ün makine tarafından denetlenen hâli.

- [ ] **Step 2: Yerel derlemede CSP'yi doğrula**

Run: `cd panel && npm run build && npx vite preview --port 4173 &`
Tarayıcıda `http://localhost:4173` aç, geliştirici konsolunda CSP ihlali olmadığını gör. (`vite preview` `vercel.json` başlıklarını uygulamaz; bu adım yalnız uygulamanın gerçekten dış istek yapmadığını doğrular — `Network` sekmesinde yalnız yerel dosyalar görünmeli.)

- [ ] **Step 3: Kök README'nin pano yolunu düzelt**

Kök `README.md`'deki depo düzeni ağacında `sunum/` altındaki `index.html Anahat sevkiyat panosu (interaktif)` satırını kaldır ve `panel/` girdisi ekle:

```
├── panel/                     ← Anahat Sevkiyat Panosu (jüri kontrol panosu)
│   ├── src/                      React arayüzü — 6 görünüm
│   ├── kaynak/                   panel.json üreteci (tek gerçeğin kaynağı)
│   ├── desktop/                  pywebview kabuğu + .exe derleyici
│   └── README.md                 panonun kendi dokümantasyonu
```

- [ ] **Step 4: `panel/README.md`'yi güncelle**

Derleme bölümüne `npm run paket` ve `npm test` satırlarını ekle; "Panoda ne var" tablosuna Task 7'de eklenen çıkış/tepe doluluk ayrımını bir cümleyle yaz.

- [ ] **Step 5: Tam doğrulama koşusu**

Run:
```bash
cd panel && python kaynak/build_panel_data.py && npx tsc -b && npx vitest run && python -m pytest desktop/ -q && npm run build && npm run paket
```
Expected: Hepsi 0 çıkış kodu; `dist/` ve `dist-exe/Anahat-Sevkiyat-Panosu.exe` üretildi.

- [ ] **Step 6: Commit**

```bash
git add panel/vercel.json panel/README.md README.md
git commit -m "pano: katı CSP ve güvenlik başlıkları, dokümantasyon pano yolunu düzeltti"
```

---

## Sonraki planlar

- **B planı** — veri ve kanıt: `probe.py` (`kanit.json`), `build_iz.py` (`iz.json`), KORİDOR ve UYUM görünümleri, KISIT/TAHMİN/MODEL/FİLO güçlendirmeleri.
- **C planı** — sunum katmanı ve canlılık: sunum kipi, hikâye kipi, komut paleti, jüri cevap kartları, `kopru.py` js_api, KOŞU görünümü, sabotaj demosu, what-if.
