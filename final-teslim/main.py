#!/usr/bin/env python3
"""TEKNOFEST Final Backtest — tek giriş noktası (Bölüm 3).

    python main.py

Argümansız, etkileşimsiz ve internetsiz çalışır. Sırasıyla:

1. Bölüm 4 talep tablosunu okur (``TEKNOFEST_INPUT_FILE`` ortam değişkeni,
   yoksa ``data/one_week_backtest.xlsx``),
2. ufku girdideki ``Tarih`` kolonundan türetir (kodda gömülü takvim tarihi
   yoktur — Bölüm 7),
3. YALNIZCA optimizasyon boru hattını çalıştırır (Bölüm 2: tahmin modülü
   çağrılmaz),
4. Bölüm 5 şemasındaki ``out/Tasima-plani.xlsx`` dosyasını yazar.

Optimizasyon boru hattı (Stage 0 → 3) yarışmaya teslim edilen kaynak
kodların aynısıdır; bu dosya yalnız bir orkestratördür. Her aşama
tamamlandığında çıktı dosyası o ana kadarki en iyi planla güncellenir;
böylece beklenmedik bir hata veya zaman aşımı hâlinde bile geçerli bir
taşıma planı diskte hazır bulunur (Bölüm 10).
"""
from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.contract import (  # noqa: E402
    OUTPUT_DIR, OUTPUT_FILENAME, horizon_days, read_demand_table,
    resolve_input_path, write_final_plan)
from src.data import load_all  # noqa: E402
from src.evaluation import evaluate_legs, summarize_evaluation  # noqa: E402
from src.milkrun import run_milk_run_stage  # noqa: E402
from src.optimize import build_plan, prepare_frame  # noqa: E402
from src.pickup import run_pickup_stage  # noqa: E402
from src.repair import run_same_lane_stage  # noqa: E402

#: Bölüm 10 — değerlendirme zaman aşımı (dakika). Ortam değişkeniyle
#: daraltılabilir; 0 verilirse süre sınırı uygulanmaz.
TIME_BUDGET_MINUTES = float(os.environ.get("TEKNOFEST_TIME_BUDGET_MIN", "100"))
#: Bütçenin bu oranı iyileştirme aşamalarına ayrılır; kalan pay çıktının
#: yazılması ve sürecin düzgün sonlanması içindir.
SEARCH_BUDGET_FRACTION = 0.90


def _use_utf8_console() -> None:
    """Türkçe çıktıyı cp1252 borularında da basılabilir tutar."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


def _log(message: str) -> None:
    print(message, flush=True)


def _report(label: str, evaluation, data) -> None:
    metrics = summarize_evaluation(evaluation, data)
    _log(f"[{label}]")
    _log(f"    Araç maliyeti : {metrics.vehicle_cost:>16,.2f} TL")
    _log(f"    SLA cezası    : {metrics.sla_penalty:>16,.2f} TL")
    _log(f"    TOPLAM        : {metrics.total_cost:>16,.2f} TL")
    _log(f"    Segment       : {len(evaluation.legs)}")
    _log(f"    Fiziksel rota : {metrics.rented_legs + metrics.spot_legs} "
         f"({metrics.rented_legs} kiralık, {metrics.spot_legs} Spot)")
    _log(f"    Plan satırı   : {len(evaluation.plan_frame)}")
    _log(f"    İhlal         : {metrics.violations}")


class Publisher:
    """Çıktıyı her aşamadan sonra güncelleyen atomik yayıncı.

    Bölüm 10 "beklenen çıktı dosyası üretilmez" durumunu hatalı sayar. Bu
    yüzden geçerli ilk plan elde edilir edilmez yazılır; sonraki her aşama
    dosyanın üzerine atomik olarak yazar. Beklenmedik bir hata ya da dış
    zaman aşımı hâlinde diskte her zaman geçerli bir plan bulunur.
    """

    def __init__(self, destination: Path, data, id_map: dict) -> None:
        self.destination = destination
        self.data = data
        self.id_map = id_map
        self.published_label: str | None = None
        self.published: object | None = None

    def publish(self, label: str, evaluation) -> bool:
        if evaluation is self.published:
            return True
        try:
            write_final_plan(
                evaluation.plan_frame, self.destination, self.data,
                self.id_map)
        except Exception:  # noqa: BLE001 - yayın hatası koşuyu bitirmemeli
            _log(f"    ! {label} yayınlanamadı:")
            _log(traceback.format_exc().rstrip())
            return False
        self.published_label = label
        self.published = evaluation
        _log(f"    → çıktı güncellendi ({label})")
        return True


#: Süre sınırında terk edilmiş (hâlâ çalışan) arama iş parçacığı var mı.
ABANDONED = threading.Event()


def _seconds_left(started: float) -> float:
    """Aramaya ayrılan bütçeden kalan saniye (sınırsızsa ``inf``)."""
    if TIME_BUDGET_MINUTES <= 0:
        return float("inf")
    budget = TIME_BUDGET_MINUTES * 60.0 * SEARCH_BUDGET_FRACTION
    return budget - (time.perf_counter() - started)


def _call_with_deadline(function, arguments: tuple, seconds: float):
    """``function(*arguments)``'ı süre sınırıyla çalıştırır.

    Arama aşamaları kendi içlerinde bölünemediği için sınır, ayrı bir
    daemon iş parçacığına ``join(timeout)`` uygulanarak konur. Süre
    dolarsa sonuç terk edilir; iş parçacığı daemon olduğundan yorumlayıcı
    kapanışını engellemez. Bölüm 10'daki 100 dakikalık zaman aşımının
    hiçbir koşulda aşılmaması bu mekanizmaya dayanır.
    """
    if seconds == float("inf"):
        # Süre sınırı kapalı (TEKNOFEST_TIME_BUDGET_MIN=0): iş parçacığına
        # gerek yok, ama hata yakalama sözleşmesi aynı kalmalı.
        try:
            return function(*arguments), None
        except BaseException as error:  # noqa: BLE001
            return None, error

    box: dict = {}

    def target() -> None:
        try:
            box["value"] = function(*arguments)
        except BaseException as error:  # noqa: BLE001
            box["error"] = error

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(max(0.0, seconds))
    if worker.is_alive():
        ABANDONED.set()
        return None, TimeoutError("süre sınırı aşıldı")
    if "error" in box:
        return None, box["error"]
    return box.get("value"), None


def _run_stage(name: str, runner, current, frame, data, started: float):
    """Bir iyileştirme aşamasını güvenle çalıştırır.

    Aşama reddedilirse, süre sınırını aşarsa veya beklenmedik bir hata
    verirse elde kalan en iyi (refere edilmiş) plan korunur.
    """
    remaining = _seconds_left(started)
    if remaining <= 0:
        _log(f"[{name}] atlandı: arama bütçesi tükendi")
        return current, False

    stage_started = time.perf_counter()
    decision, error = _call_with_deadline(
        runner, (current, frame, data), remaining)
    seconds = time.perf_counter() - stage_started

    if isinstance(error, TimeoutError):
        _log(f"[{name}] süre sınırında terk edildi ({seconds:.1f} sn); "
             "önceki plan korunuyor")
        return current, False
    if error is not None:
        _log(f"[{name}] hata nedeniyle atlandı; önceki plan korunuyor:")
        _log("".join(traceback.format_exception(
            type(error), error, error.__traceback__)).rstrip())
        return current, False

    saving = Decimal(str(decision.saving_tl))
    if decision.accepted:
        _log(f"[{name}] kabul edildi; tasarruf {saving:,.2f} TL "
             f"({seconds:.1f} sn)")
    else:
        _log(f"[{name}] reddedildi (tasarruf {saving:,.2f} TL, "
             f"{seconds:.1f} sn); önceki plan korunuyor")
    return decision.selected, decision.accepted


def main() -> int:
    _use_utf8_console()
    started = time.perf_counter()

    # --- Bölüm 4: girdi -------------------------------------------------
    input_path = resolve_input_path(ROOT)
    _log(f"Girdi talep tablosu : {input_path}")

    # Tahmin modülü çağrılmaz (Bölüm 2), bu yüzden geçmiş talep tablosu da
    # okunmaz; kalan statik referans veriler değişmeden kullanılır.
    data = load_all(ROOT / "datas", with_demand=False)
    frame, id_map, notes = read_demand_table(input_path, data)
    for note in notes:
        _log(f"    - {note}")

    days = horizon_days(frame)
    _log(f"Talep satırı        : {len(frame)}  |  toplam desi: "
         f"{int(frame['Tahmin Edilen Desi'].sum()):,}")
    _log(f"Ufuk (girdiden)     : {days[0]:%d.%m.%Y} - {days[-1]:%d.%m.%Y} "
         f"({len(days)} gün)")

    publisher = Publisher(ROOT / OUTPUT_DIR / OUTPUT_FILENAME, data, id_map)

    # --- Stage 0: temel plan --------------------------------------------
    legs = build_plan(data, prepare_frame(frame), days)
    _log(f"Stage 0 bacak       : {len(legs)}  "
         f"({time.perf_counter() - started:.1f} sn)")

    # --- Stage 1: aynı-hat onarım ---------------------------------------
    # Stage 1 hem temel planı (baseline) hem adayını üretir; hata hâlinde
    # temel plan ayrıca değerlendirilir, böylece yayınlanacak bir plan
    # her koşulda oluşur.
    stage_started = time.perf_counter()
    stage1, error = _call_with_deadline(
        run_same_lane_stage, (legs, frame, data), _seconds_left(started))
    if error is None:
        seconds = time.perf_counter() - stage_started
        _report("Stage 0 temel plan", stage1.baseline, data)
        publisher.publish("Stage 0", stage1.baseline)
        saving = Decimal(str(stage1.saving_tl))
        if stage1.accepted:
            _log(f"[Stage 1 aynı-hat onarım] kabul edildi; tasarruf "
                 f"{saving:,.2f} TL ({seconds:.1f} sn)")
            publisher.publish("Stage 1", stage1.selected)
        else:
            _log(f"[Stage 1 aynı-hat onarım] reddedildi (tasarruf "
                 f"{saving:,.2f} TL, {seconds:.1f} sn); temel plan korunuyor")
        best = stage1.selected
    else:
        _log("[Stage 1 aynı-hat onarım] tamamlanamadı; temel plan "
             "yayınlanacak:")
        if not isinstance(error, TimeoutError):
            _log("".join(traceback.format_exception(
                type(error), error, error.__traceback__)).rstrip())
        best = evaluate_legs(legs, frame, data, fix=True)
        _report("Stage 0 temel plan", best, data)
        publisher.publish("Stage 0", best)

    # --- Stage 2-3: milk-run ve rota-ortası yük alma ---------------------
    for name, runner in (("Stage 2 milk-run", run_milk_run_stage),
                         ("Stage 3 rota-ortası yük alma", run_pickup_stage)):
        best, accepted = _run_stage(name, runner, best, frame, data, started)
        if accepted:
            publisher.publish(name, best)

    optimize_seconds = time.perf_counter() - started

    # --- Bölüm 5: çıktı --------------------------------------------------
    # Diskteki dosya en iyi plandan geriyse (bir ara yayın başarısız olmuş
    # olabilir) son bir kez denenir. Hiç yayın yapılamadıysa istisna
    # yükselir ve çıkış kodu sıfırdan farklı olur — sessizce yanlış bir
    # çıktı bırakmaktansa hatanın görünmesi yeğdir.
    if not publisher.publish("son plan", best) and publisher.published is None:
        write_final_plan(
            best.plan_frame, publisher.destination, data, id_map)
        publisher.published = best

    published = publisher.published if publisher.published is not None else best
    _report("Yayınlanan plan", published, data)
    for violation in published.result.violations[:20]:
        _log(f"    ! {violation}")
    if len(published.result.violations) > 20:
        _log(f"    ! ... (+{len(published.result.violations) - 20} ihlal daha)")

    _log(f"Optimizasyon süresi : {optimize_seconds:.1f} sn")
    _log(f"Toplam süre         : {time.perf_counter() - started:.1f} sn")
    _log(f"Çıktı               : {publisher.destination}")
    return 0


if __name__ == "__main__":
    code = main()
    if ABANDONED.is_set():
        # Süre sınırında terk edilmiş bir arama iş parçacığı hâlâ CPU
        # tüketiyor olabilir. Çıktı atomik olarak yazıldığı için süreci
        # doğrudan sonlandırmak güvenlidir ve süre aşımını engeller.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)
    sys.exit(code)
