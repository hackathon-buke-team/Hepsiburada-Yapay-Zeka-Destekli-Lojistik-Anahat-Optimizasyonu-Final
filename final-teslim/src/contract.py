"""Final backtest entegrasyon katmanı (girdi/çıktı sözleşmesi).

Bu modül YENİDİR ve yalnızca *entegrasyon* sorumluluğu taşır — optimizasyon
algoritmasına ait tek bir karar burada verilmez. Görevi:

* Bölüm 4'teki talep tablosunu (dosya yolu, şema, tip toleransları) okuyup
  projenin kendi tahmin modülünün ürettiği kanonik ``FORECAST_COLS``
  DataFrame'ine birebir eşdeğer bir tabloya çevirmek,
* Talep kimliklerini iç boru hattının beklediği ``D00001`` biçimine
  (algoritmanın kimlik sırası korunacak şekilde) eşlemek ve çıktıda
  girdideki özgün kimliklere geri döndürmek,
* Ufku (tarih aralığını) girdi dosyasından türetmek — kodda gömülü takvim
  tarihi yoktur,
* Bölüm 5'teki 16 kolonluk taşıma planını atomik ve doğrulanmış biçimde
  yazmak.

Kimlik eşlemesi ``src.forecast.assign_talep_ids`` ile birebir aynı sıralama
anahtarını (``tarih, cikis, varis, slot``) kullanır; dolayısıyla girdi bu
projenin kendi tahmin çıktısı olduğunda eşleme özdeşliktir ve boru hattı
bit-birebir aynı planı üretir.
"""
from __future__ import annotations

import math
import os
import re
import tempfile
import unicodedata
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from src.schemas import (FORECAST_COLS, PLAN_COLS,
                         PLAN_NUMERIC_COLS, validate_plan)

#: Bölüm 4 — girdi dosyasının mutlak yolunu taşıyan ortam değişkeni.
INPUT_ENV_VAR = "TEKNOFEST_INPUT_FILE"
#: Bölüm 4 — ortam değişkeni yoksa kullanılacak sabit göreli yol.
INPUT_FALLBACK_PATH = Path("data") / "one_week_backtest.xlsx"
#: Bölüm 5/6 — çıktı klasörü ve dosya adı (manifest ile birebir aynı).
OUTPUT_DIR = Path("out")
OUTPUT_FILENAME = "Tasima-plani.xlsx"

#: Kanonik talep kimliği genişliği (``D00001``). Satır sayısı 99.999'u
#: aşarsa biçim doğal olarak genişler; şema regex'leri buna izin verir.
_ID_WIDTH = 5
_SORT_COLS = ["_tarih", "_cikis", "_varis", "_slot"]
_EXCEL_EPOCH = date(1899, 12, 30)
_CANONICAL_ID_RE = re.compile(r"^(D\d+)(?:-(\d+))?$")
#: Bu günden uzun bir ufuk beklenmiyor; aşılırsa yalnızca uyarı basılır
#: (Bölüm 4 "yaklaşık 1 haftalık bir dönem" diyor).
MAX_HORIZON_SPAN_DAYS = 31


class InputContractError(RuntimeError):
    """Girdi tablosu Bölüm 4 sözleşmesine hiçbir biçimde uymuyor."""


# --------------------------------------------------------------------------
# Metin / tip normalizasyonu
# --------------------------------------------------------------------------

def _nfc(value) -> str:
    """Unicode'u NFC'ye indirger ve kenar boşluklarını kırpar.

    Türkçe karakterli kolon ve merkez adları NTFS/Excel yolculuğunda NFD
    biçiminde kalabiliyor; karşılaştırmalar bu yüzden normalize edilir.
    """
    text = "" if value is None else str(value)
    return unicodedata.normalize("NFC", text).strip()


def _squeeze(value) -> str:
    """Karşılaştırma anahtarı: NFC + tek boşluk + küçük harf."""
    return re.sub(r"\s+", " ", _nfc(value)).casefold()


def _as_number(value) -> float | None:
    """Sayısal hücreyi sonlu ``float``'a çevirir; değilse ``None``.

    ``numpy.int64`` gibi tipler Python ``int``'in alt sınıfı olmadığı için
    ``isinstance`` kontrolü yeterli değildir; bu yardımcı, pandas'ın
    döndürdüğü tüm sayısal skalerleri kapsar.
    """
    if isinstance(value, (str, bytes, bool)) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_missing(value) -> bool:
    """``None``/``NaN``/``NaT`` gibi boş hücreleri tanır.

    ``pd.NaT`` ``datetime``'ın örneğidir; bu yüzden tip kontrollerinden
    önce ayrıca elenmesi gerekir.
    """
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(missing) if isinstance(missing, bool) else False


def _to_date(value) -> date | None:
    """Tarih hücresini ``datetime.date``'e çevirir; çevrilemezse ``None``."""
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Excel seri numarası (1900 tabanlı) — nadiren ham sayı olarak gelir.
    serial = _as_number(value)
    if serial is not None:
        return _EXCEL_EPOCH + timedelta(days=int(serial))

    text = _nfc(value)
    if not text:
        return None
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d",
                "%d.%m.%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="raise")
    except (TypeError, ValueError):
        return None
    return None if pd.isna(parsed) else parsed.to_pydatetime().date()


def _to_hhmm(value) -> str | None:
    """Saat hücresini ``HH:MM`` metnine çevirir; çevrilemezse ``None``.

    Bölüm 4 saatleri ``ss:dd:ss`` biçiminde bildirir; Excel bu hücreleri
    ``datetime.time``, metin veya gün kesri olarak geri verebilir. Saniye
    artığı varsa yarışmanın "en yakın büyük tam sayıya yuvarla" kuralıyla
    tutarlı olacak şekilde bir üst dakikaya yuvarlanır.
    """
    if _is_missing(value):
        return None

    total_seconds: float | None = None
    if isinstance(value, time):
        total_seconds = value.hour * 3600 + value.minute * 60 + value.second
    elif isinstance(value, pd.Timestamp):
        total_seconds = (value.hour * 3600 + value.minute * 60 + value.second)
    elif isinstance(value, datetime):
        total_seconds = value.hour * 3600 + value.minute * 60 + value.second
    elif isinstance(value, (pd.Timedelta, timedelta)):
        total_seconds = pd.Timedelta(value).total_seconds()
    elif _as_number(value) is not None:
        number = _as_number(value)
        # 0 <= x < 1 ise Excel gün kesri; değilse saat sayısı kabul edilir.
        total_seconds = (number * 86400.0 if 0.0 <= number < 1.0
                         else number * 3600.0)
    else:
        text = _nfc(value)
        if not text:
            return None
        for fmt in ("%H:%M", "%H:%M:%S", "%H.%M", "%H:%M:%S.%f"):
            try:
                parsed = datetime.strptime(text, fmt)
            except ValueError:
                continue
            total_seconds = (parsed.hour * 3600 + parsed.minute * 60
                             + parsed.second + parsed.microsecond / 1e6)
            break
        else:
            try:
                parsed = pd.to_datetime(text, errors="raise")
            except (TypeError, ValueError):
                return None
            if pd.isna(parsed):
                return None
            total_seconds = (parsed.hour * 3600 + parsed.minute * 60
                             + parsed.second)

    if total_seconds is None or not math.isfinite(total_seconds):
        return None
    minutes = int(math.ceil(round(total_seconds / 60.0, 6)))
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _to_desi(value) -> int | None:
    """Desi hücresini negatif olmayan tam sayıya çevirir."""
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return None
    number = float(number)
    if not math.isfinite(number):
        return None
    return max(0, int(round(number)))


# --------------------------------------------------------------------------
# Girdi (Bölüm 4)
# --------------------------------------------------------------------------

def resolve_input_path(root: Path | str = ".") -> Path:
    """Bölüm 4'teki iki erişim yöntemini sırayla dener.

    Önce ``TEKNOFEST_INPUT_FILE`` ortam değişkeni (mutlak yol), ardından
    ``data/one_week_backtest.xlsx`` sabit göreli yolu denenir.
    """
    root = Path(root).resolve()
    candidates: list[tuple[str, Path]] = []

    env_value = os.environ.get(INPUT_ENV_VAR, "").strip().strip('"').strip("'")
    if env_value:
        env_path = Path(env_value)
        if not env_path.is_absolute():
            env_path = root / env_path
        candidates.append((f"{INPUT_ENV_VAR}={env_value}", env_path))

    candidates.append((str(INPUT_FALLBACK_PATH), root / INPUT_FALLBACK_PATH))

    for _label, path in candidates:
        if path.is_file():
            return path

    tried = ", ".join(f"{label} -> {path}" for label, path in candidates)
    raise InputContractError(
        f"Girdi talep tablosu bulunamadı. Denenen yollar: {tried}")


def _resolve_columns(frame: pd.DataFrame, notes: list) -> dict:
    """Girdi kolonlarını ``FORECAST_COLS`` ile eşler.

    Önce normalize edilmiş ad eşlemesi denenir (NFC + boşluk + büyük/küçük
    harf toleranslı). Ad eşlemesi tamamlanamazsa ve tabloda tam olarak 6
    kolon varsa Bölüm 4'ün "ad ve sıra birebir" garantisine dayanarak
    konum eşlemesine düşülür.
    """
    by_key = {}
    for column in frame.columns:
        by_key.setdefault(_squeeze(column), column)

    mapping = {}
    missing = []
    for expected in FORECAST_COLS:
        actual = by_key.get(_squeeze(expected))
        if actual is None:
            missing.append(expected)
        else:
            mapping[expected] = actual

    if not missing:
        return mapping

    if len(frame.columns) == len(FORECAST_COLS):
        notes.append(
            "Girdi kolon adları birebir eşleşmedi, Bölüm 4 sırasına göre "
            f"konum eşlemesi kullanıldı (eksik adlar: {missing})")
        return dict(zip(FORECAST_COLS, list(frame.columns)))

    raise InputContractError(
        f"Girdi tablosunda beklenen kolonlar yok: {missing}; "
        f"bulunan kolonlar: {list(frame.columns)}")


def _resolve_center(value, centers_by_key: dict) -> str | None:
    return centers_by_key.get(_squeeze(value))


def read_demand_table(path: Path | str, data) -> tuple:
    """Bölüm 4 talep tablosunu kanonik tahmin DataFrame'ine çevirir.

    Döner: ``(frame, id_map, notes)``.

    * ``frame`` — ``FORECAST_COLS`` şemasında, ``Talep ID`` alanı kanonik
      (``D00001``) kimliklerle doldurulmuş DataFrame. Boru hattının hem
      optimizasyon hem hakem girdisi budur.
    * ``id_map`` — kanonik kimlik -> girdideki özgün kimlik.
    * ``notes`` — uygulanan toleransların insan-okur listesi.
    """
    path = Path(path)
    notes: list[str] = []
    try:
        raw = pd.read_excel(path)
    except Exception as error:  # noqa: BLE001 - dosya seviyesinde tek mesaj
        raise InputContractError(
            f"Girdi dosyası okunamadı ({path}): {error}") from error

    if raw.empty:
        raise InputContractError(f"Girdi tablosu boş: {path}")

    columns = _resolve_columns(raw, notes)
    centers_by_key = {_squeeze(tm): tm for tm in data.tms}

    records = []
    dropped_lane = 0
    dropped_date = 0
    dropped_time = 0
    dropped_desi = 0

    for position, row in enumerate(raw.to_dict("records")):
        raw_id = _nfc(row[columns["Talep ID"]])
        day = _to_date(row[columns["Tarih"]])
        slot = _to_hhmm(row[columns["Talep Tamamlama Saati"]])
        origin = _resolve_center(
            row[columns["Çıkış Transfer Merkezi"]], centers_by_key)
        dest = _resolve_center(
            row[columns["Varış Transfer Merkezi"]], centers_by_key)
        desi = _to_desi(row[columns["Tahmin Edilen Desi"]])

        if day is None:
            dropped_date += 1
            continue
        if slot is None:
            dropped_time += 1
            continue
        if desi is None:
            dropped_desi += 1
            continue
        if (origin is None or dest is None
                or (origin, dest) not in data.lanes):
            dropped_lane += 1
            continue

        records.append({
            "_pos": position,
            "_orig_id": raw_id or f"SATIR{position + 1}",
            "_tarih": day,
            "_slot": slot,
            "_cikis": origin,
            "_varis": dest,
            "_desi": desi,
        })

    for count, label in (
            (dropped_date, "geçersiz tarih"),
            (dropped_time, "geçersiz saat"),
            (dropped_desi, "geçersiz desi"),
            (dropped_lane, "hat matrisinde olmayan çıkış/varış")):
        if count:
            notes.append(f"{count} satır atlandı ({label})")

    if not records:
        raise InputContractError(
            f"Girdi tablosunda işlenebilir talep satırı yok: {path}")

    frame = pd.DataFrame(records)
    # Kanonik kimlik sırası src.forecast.assign_talep_ids ile birebir aynı:
    # (tarih, cikis, varis, slot) + kararlı sıralama. Girdi bu projenin
    # kendi tahmin çıktısıysa eşleme özdeşlik olur.
    frame = frame.sort_values(
        _SORT_COLS + ["_pos"], kind="mergesort").reset_index(drop=True)
    canonical_ids = [f"D{index:0{_ID_WIDTH}d}"
                     for index in range(1, len(frame) + 1)]

    id_map = dict(zip(canonical_ids, frame["_orig_id"].tolist()))
    dashed = sum(1 for original in id_map.values() if "-" in original)
    if dashed:
        # Bölünmüş parçalar şablon geleneğine göre "<kimlik>-1" biçiminde
        # yazılır (önceki aşamada teslim edilen plan da böyleydi). Özgün
        # kimlikte zaten tire varsa kök/sonek ayrımı okunurken belirsiz
        # kalabilir; bu biçim sözleşmesinin doğal bir sonucudur.
        notes.append(
            f"{dashed} talep kimliğinde tire var; bölünen parçalar "
            '"<kimlik>-1" biçiminde yazılacak')
    identity = all(canonical == original
                   for canonical, original in id_map.items())
    if identity:
        notes.append("Talep kimlikleri kanonik biçimde; eşleme özdeşlik")
    else:
        notes.append(
            f"{len(id_map)} talep kimliği kanonik biçime eşlendi "
            "(çıktıda özgün kimlikler geri yazılır)")

    canonical = pd.DataFrame({
        "Talep ID": canonical_ids,
        "Tarih": [day.strftime("%d.%m.%Y") for day in frame["_tarih"]],
        "Talep Tamamlama Saati": frame["_slot"].astype(str),
        "Çıkış Transfer Merkezi": frame["_cikis"],
        "Varış Transfer Merkezi": frame["_varis"],
        "Tahmin Edilen Desi": frame["_desi"].astype("int64"),
    })
    return canonical[FORECAST_COLS], id_map, notes


def horizon_days(frame: pd.DataFrame) -> list:
    """Ufku girdi tablosunun ``Tarih`` kolonundan türetir.

    Kodda gömülü takvim tarihi yoktur (Bölüm 7). En küçük ve en büyük
    tarih arasındaki tüm günler kesintisiz olarak döner; boru hattı gün
    zincirini kesintisiz varsayar (bir sonraki dalga = ertesi gün).
    """
    days = sorted({
        datetime.strptime(str(value), "%d.%m.%Y").date()
        for value in frame["Tarih"]
    })
    if not days:
        raise InputContractError("Girdi tablosundan ufuk türetilemedi")
    span = (days[-1] - days[0]).days
    if span > MAX_HORIZON_SPAN_DAYS:
        print(f"UYARI: girdi tarih aralığı {span + 1} gün "
              f"({days[0]:%d.%m.%Y} - {days[-1]:%d.%m.%Y}); beklenen ~1 hafta. "
              "Aykırı bir tarih hücresi olabilir.", flush=True)
    return [days[0] + timedelta(days=offset) for offset in range(span + 1)]


# --------------------------------------------------------------------------
# Çıktı (Bölüm 5)
# --------------------------------------------------------------------------

def restore_demand_ids(plan_frame: pd.DataFrame, id_map: dict) -> pd.DataFrame:
    """Plandaki kanonik kimlikleri girdideki özgün kimliklere geri çevirir.

    Bölünmüş parçalar plan içinde ``D00007-2`` biçiminde görünür; kök
    kimlik eşlenir, ``-2`` sonek aynen korunur.
    """
    if not id_map:
        return plan_frame

    def convert(value) -> str:
        if pd.isna(value):
            return ""
        text = str(value).strip()
        if not text:
            return ""
        match = _CANONICAL_ID_RE.match(text)
        if match is None:
            return text
        base, suffix = match.group(1), match.group(2)
        original = id_map.get(base)
        if original is None:
            return text
        return original if suffix is None else f"{original}-{suffix}"

    out = plan_frame.copy()
    out["Talep ID"] = [convert(value) for value in out["Talep ID"]]
    return out


def _format_plan_workbook(path: Path) -> None:
    """Resmî şablonun ``0.000`` desi hücre biçimini uygular."""
    workbook = load_workbook(path)
    sheet = workbook.active
    desi_col = PLAN_COLS.index("Taşınan Desi") + 1
    for row in range(2, sheet.max_row + 1):
        sheet.cell(row=row, column=desi_col).number_format = "0.000"
    workbook.save(path)


#: Excel hücreleri ~17 anlamlı basamak saklar; 3347.8859374999997 gibi bir
#: değer diskten 3347.8859375 olarak geri gelir. Bu, veri bozulması değil
#: dosya biçiminin doğal hassasiyetidir — round-trip karşılaştırması bu
#: yüzden bağıl toleransla yapılır.
_ROUNDTRIP_ABS_TOLERANCE = 1e-9
_ROUNDTRIP_REL_TOLERANCE = 1e-12


def _roundtrip_differences(written: pd.DataFrame, reloaded: pd.DataFrame,
                           limit: int = 5) -> list:
    """Diskten geri okunan planla yazılan plan arasındaki gerçek farklar."""
    numeric = set(PLAN_NUMERIC_COLS)
    differences = []
    written_rows = written.to_dict("records")
    reloaded_rows = reloaded.to_dict("records")

    for index, (left, right) in enumerate(zip(written_rows, reloaded_rows)):
        for column in PLAN_COLS:
            first, second = left[column], right[column]
            if column in numeric:
                try:
                    a, b = float(first), float(second)
                except (TypeError, ValueError):
                    if str(first).strip() != str(second).strip():
                        differences.append(
                            f"satır {index} [{column}]: {first!r} != "
                            f"{second!r}")
                    continue
                if math.isnan(a) and math.isnan(b):
                    continue
                allowed = max(_ROUNDTRIP_ABS_TOLERANCE,
                              abs(a) * _ROUNDTRIP_REL_TOLERANCE)
                if not abs(a - b) <= allowed:
                    differences.append(
                        f"satır {index} [{column}]: {a!r} != {b!r}")
                continue

            first_text = "" if pd.isna(first) else str(first).strip()
            second_text = "" if pd.isna(second) else str(second).strip()
            if first_text != second_text:
                differences.append(
                    f"satır {index} [{column}]: {first_text!r} != "
                    f"{second_text!r}")
            if len(differences) >= limit:
                return differences
        if len(differences) >= limit:
            break
    return differences


def write_final_plan(plan_frame: pd.DataFrame, destination: Path | str,
                     data, id_map: dict) -> Path:
    """Bölüm 5 şemasındaki taşıma planını atomik olarak yazar.

    Sıra: (1) kanonik kimliklerle şema doğrulaması, (2) özgün kimliklere
    geri eşleme, (3) geçici dosyaya yazım + hücre biçimi, (4) diskten geri
    okuyup kolon adı/sırasının ve satır sayısının korunduğunun
    doğrulanması, (5) atomik ``os.replace``.

    Hücre değerleri de karşılaştırılır; Excel'in ~17 anlamlı basamaklık
    hassasiyetinden doğan farklar tolere edilir, bunun ötesindeki farklar
    uyarı olarak basılır ancak yayını engellemez (Bölüm 10: çıktı
    üretilmemesi çok daha ağır bir sonuçtur).
    """
    errors = validate_plan(plan_frame, data)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Plan doğrulaması başarısız:\n{details}")

    final = restore_demand_ids(plan_frame, id_map)
    final = final.loc[:, PLAN_COLS]

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}-", suffix=".xlsx",
        dir=destination.parent)
    os.close(handle)
    temporary_path = Path(temporary_name)

    try:
        final.to_excel(temporary_path, index=False)
        _format_plan_workbook(temporary_path)

        reloaded = pd.read_excel(temporary_path)
        if list(reloaded.columns) != PLAN_COLS:
            raise ValueError(
                "Yazılan planın kolonları şablonla birebir değil. "
                f"Beklenen: {PLAN_COLS}, bulunan: {list(reloaded.columns)}")
        if len(reloaded) != len(final):
            raise ValueError(
                f"Yazılan plan satır sayısı değişti: {len(reloaded)} != "
                f"{len(final)}")
        # Şema hataları ölümcüldür (Bölüm 5/10); değer farkları ise
        # yalnızca uyarıdır — bir uyarı yüzünden çıktısız kalmak, Bölüm
        # 10'a göre çok daha ağır bir sonuçtur.
        differences = _roundtrip_differences(final, reloaded)
        if differences:
            print("UYARI: plan disk round-trip'inde beklenmedik fark:",
                  flush=True)
            for difference in differences:
                print(f"  - {difference}", flush=True)

        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)

    return destination
