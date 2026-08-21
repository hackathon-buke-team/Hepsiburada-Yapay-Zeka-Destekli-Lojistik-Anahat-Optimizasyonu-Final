# Değişiklik Kaydı — Gelişmiş Çözüm teslimi → Final teslimi

*Final Backtest — Teknik Gereksinimler*, **Bölüm 8** uyarınca bu dosya, önceki
aşamada teslim edilen `Kaynak Kodlar` paketi ile bu paket arasındaki **tüm**
farkları listeler.

> **Özet:** Algoritma, model ve çözüm mantığı **değişmemiştir**. Yapılan
> değişiklikler Bölüm 3–7'deki entegrasyon gereksinimlerine yöneliktir.
> Kanıt: aynı talep tablosuyla çalıştırıldığında `main.py`, önceki aşamada
> teslim edilen `Tasima-plani.xlsx` ile **hücre hücre birebir aynı** dosyayı
> üretir (5.523 satır × 16 kolon → **0 farklı hücre**, toplam maliyet
> 11.232.476,731944446 TL, 0 hakem ihlali).

---

## 1. Değişmeyenler

Aşağıdaki modüller **tek karakter dahi değişmemiştir**:

| Modül | Rolü |
|---|---|
| `src/optimize.py` | Stage 0 — kiralık doldurma, tır ziyaret bütçesi, hat-gün araç karması, boşaltma günleri |
| `src/candidates.py` | Araç karması numaralandırması, kesin maliyet modeli, erteleme kararı |
| `src/repair.py` | Stage 1 — aynı-hat onarımı |
| `src/milkrun.py` | Stage 2 — ≤4 duraklı milk-run zincirleri |
| `src/pickup.py` | Stage 3 — rota ortasında yük alma (Tier A) |
| `src/chain.py` | Fiziksel rota doğrulaması ve bacak-başına yük akışı |
| `src/schedule.py` | Dakika çizelgeleyici, kimlik atama, elleçleme düzeltmesi |
| `src/ledger.py` | Elleçleme ve tır ziyaret defterleri |
| `src/simulator.py` | Hakem simülatörü |
| `src/evaluation.py` | Çizelgeleme/hakem/kabul sınırı |
| `src/export.py` | Excel yazımı ve doğrulaması |
| `src/timeutil.py` | Yuvarlama ve zaman kuralları |
| `src/forecast.py`, `src/backtest.py`, `src/frozen_backtest.py` | Tahmin modülü — **final koşusunda çağrılmaz** (Bölüm 2), referans olarak pakette bırakıldı |
| `tests/` (528 test) | Regresyon testleri |
| `run.py` | Önceki teslimin uçtan uca hattı — referans, değerlendirmede çalıştırılmaz |
| `datas/` | Statik referans verileri |

---

## 2. Eklenen dosyalar

### 2.1 `main.py` — Bölüm 3 (tek giriş noktası) · **YENİ**

Kök dizinde, argümansız çalışan ince orkestratör. Yaptığı tek şey mevcut
aşamaları sırayla çağırmaktır:

```
resolve_input_path → read_demand_table → load_all
  → build_plan (Stage 0) → run_same_lane_stage (Stage 1)
  → run_milk_run_stage (Stage 2) → run_pickup_stage (Stage 3)
  → write_final_plan
```

`run.py`'den farkları — hepsi Bölüm 2–7 gereği:

| # | Fark | Gerekçe |
|---|---|---|
| 1 | `forecast_horizon` / `to_forecast_frame` / `write_forecast_xlsx` çağrılmaz; `src.forecast` **import bile edilmez** | Bölüm 2: final koşusunda tahmin modülü çalıştırılmamalı |
| 2 | `HORIZON_START = date(2026, 6, 29)` / `HORIZON_END = date(2026, 7, 5)` sabitleri **yok**; ufuk `Tarih` kolonundan türetilir | Bölüm 7: gömülü takvim tarihi yasak |
| 3 | `run.py`'deki `STAGE0_*`…`STAGE3_*` sabit sonuç kapıları (`_require_stage*`) **yok** | Bu kapılar tek bir veri setinin ölçülmüş sonucuna sabitlenmiştir; bilinmeyen bir veri setinde tanım gereği hata verirler (Bölüm 10: sıfırdan farklı çıkış kodu = hatalı çalıştırma). Aşamaların *kendi* kabul kuralı (`accepts_candidate`: 0 ihlal **ve** daha düşük maliyet) değişmeden korunmuştur. |
| 4 | Yalnız `Tasima-plani.xlsx` yazılır (`Talep-tahmini.xlsx` yazılmaz) | Bölüm 5: beklenen çıktı tek dosya |
| 5 | **Kademeli yayın:** geçerli ilk plan (Stage 0) elde edilir edilmez çıktı dosyası yazılır, kabul edilen her aşama dosyayı atomik olarak günceller | Bölüm 10: "beklenen çıktı dosyası üretilmez" hatalı çalıştırma sayılır |
| 6 | **Sert süre sınırı:** her arama aşaması ayrı bir daemon iş parçacığında, kalan bütçeyle sınırlı çalıştırılır; sınır dolarsa aşama terk edilir, önceki plan korunur ve süreç çıkış kodu 0 ile biter (`TEKNOFEST_TIME_BUDGET_MIN`, varsayılan 100) | Bölüm 10: 100 dakikayı aşan çalıştırma hatalı sayılır; arama aşamaları kendi içlerinde bölünemediği için sınır dışarıdan konur |
| 7 | Her aşama ayrıca `try/except` ile sarmalanır; hata hâlinde önceki aşamanın planı korunur | Bölüm 10: sıfırdan farklı çıkış kodu hatalı çalıştırma sayılır |
| 8 | `load_all(..., with_demand=False)` | Bölüm 2 gereği okunmayacak 66 bin satırlık geçmiş talep tablosunun ayrıştırılması ~8 sn çalışma süresi harcıyordu (Bölüm 10: süre ölçülüyor) |

### 2.2 `src/contract.py` — girdi/çıktı sözleşmesi · **YENİ**

Bölüm 4 ve Bölüm 5'in tamamı bu modülde toplanmıştır. İçinde tek bir
optimizasyon kararı yoktur.

* `resolve_input_path` — `TEKNOFEST_INPUT_FILE`, sonra
  `data/one_week_backtest.xlsx` (Bölüm 4'ün iki erişim yöntemi de desteklenir).
* `read_demand_table` — 6 kolonluk tabloyu okur; kolon adlarını Unicode (NFC)
  ve büyük/küçük harf toleransıyla eşler, tarih/saat/desi hücrelerini
  (`datetime.time`, `"09:00"`, `"09:00:00"`, Excel seri numarası, gün kesri…)
  kanonik biçime çevirir ve projenin kendi tahmin çıktısıyla **aynı**
  `FORECAST_COLS` DataFrame'ini üretir.
* **Talep kimliği eşlemesi** — girdideki kimlikler iç boru hattının kullandığı
  kanonik `D00001` biçimine eşlenir, çıktıda özgün kimlikler geri yazılır
  (bölünmüş parçalarda `-1`, `-2` soneki korunur). Sıralama anahtarı
  `src/forecast.py::assign_talep_ids` ile **birebir aynıdır**
  (`tarih, cikis, varis, slot`); dolayısıyla girdi bu projenin kendi tahmin
  çıktısı olduğunda eşleme **özdeşliktir** ve boru hattı bit-birebir aynı
  planı üretir. Amaç: girdi kimlikleri kanonik biçimde olmasa bile
  (`REQ_1`, `TALEP-7`…) iç doğrulayıcıların ve hakem simülatörünün kimlik
  sözleşmesinin bozulmaması.
* `horizon_days` — ufku `Tarih` kolonunun en küçük/en büyük değerinden
  kesintisiz gün listesi olarak türetir (Bölüm 7).
* `write_final_plan` — 16 kolonu şablon sırasıyla yazar; yazımdan sonra
  dosyayı diskten geri okuyup kolon adı/sırasını ve satır sayısını
  doğrular, ancak ondan sonra atomik `os.replace` yapar (Bölüm 5/10:
  şemaya birebir uymayan çıktı hatalı sayılır). Hücre değerleri de
  karşılaştırılır; Excel'in ~17 anlamlı basamaklık hassasiyetinden doğan
  farklar (ör. `3347.8859374999997` → `3347.8859375`) tolere edilir,
  ötesindeki farklar uyarı olarak basılır fakat yayını engellemez.

### 2.3 Diğer yeni dosyalar

| Dosya | Rolü |
|---|---|
| `teknofest_manifest.json` | Bölüm 6 |
| `requirements-dev.txt` | Yalnız test bağımlılığı (`pytest`); değerlendirme koşusu gerektirmez |
| `tests/test_contract.py` | `src/contract.py` için 64 yeni test (mevcut 528 test değişmedi) |
| `data/one_week_backtest.xlsx` | Bölüm 4 yedek girdi yolu — ekibin kendi tahmin çıktısı |
| `tools/make_test_input.py` | Bölüm 7 öz-denetimi: sentetik girdi üretici (değerlendirmede çalışmaz) |
| `tools/verify_output.py` | Üretilen planı diskten okuyup hakem simülatöründen geçirir (değerlendirmede çalışmaz) |
| `README.md`, `DEGISIKLIKLER.md`, `KONTROL_LISTESI.md` | Dokümantasyon ve Bölüm 11 kontrol listesi |

---

## 3. Değiştirilen dosyalar (tamamı)

Yalnızca **iki** modülde değişiklik vardır; ikisi de davranışı genişletir,
mevcut davranışı değiştirmez.

### 3.1 `src/data.py` — `load_all` için opsiyonel `with_demand`

```diff
-def load_all(data_dir: Path = DATA_DIR) -> CompetitionData:
+def load_all(data_dir: Path = DATA_DIR, *,
+             with_demand: bool = True) -> CompetitionData:
+    """Statik referans verilerini (ve istenirse geçmiş talebi) yükler.
+
+    ``with_demand=False`` yalnızca *entegrasyon* içindir: final backtest
+    çalıştırmasında tahmin modülü çağrılmaz (Bölüm 2), dolayısıyla 66 bin
+    satırlık geçmiş talep tablosunun okunması gereksiz çalışma süresi
+    harcar. Varsayılan davranış değişmemiştir.
+    """
     data_dir = Path(data_dir)
@@
-    demand = _load_demand(data_dir)
+    demand = (_load_demand(data_dir) if with_demand
+              else pd.DataFrame(
+                  columns=["tarih", "cikis", "varis", "talep_id",
+                           "toplam_desi", "slot"]))
```

* **Neden:** `teknofest26_gelismis.xlsx` (66.024 satır) yalnızca tahmin
  modülünün geçmiş veri kaynağıdır. Final koşusunda tahmin çalıştırılmadığı
  için (Bölüm 2) bu dosyanın ayrıştırılması saf kayıptır — ölçülen maliyeti
  **~8,2 sn**. Bölüm 10 çalışma süresini değerlendirmeye kattığı için
  kaldırıldı.
* **Etki:** Varsayılan `with_demand=True` olduğundan `run.py` ve 528 testin
  tamamı değişmeden çalışır. `data.demand` alanı optimizasyon yolunda hiçbir
  yerde okunmaz (yalnızca `schemas.validate_forecast_grid`'in tahmin gridi
  doğrulamasında, `ods=None` verildiğinde kullanılır).

### 3.2 `src/schemas.py` — talep kimliği regex genişliği

```diff
-DEMAND_ID_RE = re.compile(r"^D\d{5}$")
-SPLIT_ID_RE = re.compile(r"^D\d{5}(-\d+)*$")
+# Kanonik talep kimliği ``D00001``; 99.999'dan fazla talep satırı gelirse
+# genişlik doğal olarak artar (Bölüm 7 genelleştirilebilirlik).
+DEMAND_ID_RE = re.compile(r"^D\d{5,}$")
+SPLIT_ID_RE = re.compile(r"^D\d{5,}(-\d+)*$")
```

* **Neden:** Bölüm 7 — değerlendirme veri setinin hacmi bildirilmiyor.
  Kanonik kimlik biçimi 99.999 satırdan sonra doğal olarak 6 haneye çıkar;
  eski regex bunu şema hatası sayıp çalıştırmayı düşürürdü.
* **Etki:** Kural yalnızca **genişletildi**; 5 haneli her kimlik eskisi gibi
  geçerlidir. Mevcut veri setinde (4.046 satır) hiçbir davranış değişmez.

---

## 4. Doğrulama kanıtı

| Kontrol | Sonuç |
|---|---|
| `python main.py` (referans veri seti) | Çıkış kodu 0, ~150 sn |
| Üretilen `Tasima-plani.xlsx` ↔ önceki teslim | **0 farklı hücre** (5.523 × 16) |
| Toplam maliyet | 11.232.476,731944446 TL (aynı) |
| Hakem ihlali | 0 |
| `python -m pytest -q` | 592/592 geçti (528 mevcut + 64 yeni) |
| `main.py` import grafiği | `src.forecast` / `src.backtest` / `src.frozen_backtest` **ulaşılamıyor** (Bölüm 2) |
| Statik analiz | `input()`, ağ çağrısı, `pip install`, IDE/Colab bağımlılığı yok |
| Farklı yıl + 4 günlük ufuk + `REQ_` kimlikler + `HH:MM` (25–28.05.2025, 1.808 satır) | Çıkış kodu 0, 0 ihlal, beyan-hakem farkı 0,0000 TL, 171 sn |
| Farklı hafta + %125 hacim + `HH:MM:SS` (02–08.09.2026, 2.925 satır) | Çıkış kodu 0, 0 ihlal, 143 sn |
| %250 hacim (elleçleme kapasitesi fizikî olarak yetersiz) | Stage 0 planı üretildi ve yayınlandı; 69 elleçleme ihlalinin tamamı talebin günlük kapasiteyi aşmasından kaynaklanıyor, Stage 1 adayı doğru biçimde reddedildi — çökme yok |
| Kademeli yayın (zorla sonlandırma) | Süreç Stage 2 ortasında öldürüldüğünde bile diskte 3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru bir `Tasima-plani.xlsx` bulundu |
| Sert süre sınırı (`TEKNOFEST_TIME_BUDGET_MIN=0.6`) | Stage 2 terk edildi, Stage 1 planı yayınlandı, çıkış kodu 0, 32,4 sn, 0 ihlal |
| Temiz sanal ortam (pandas 2.3.3 / numpy 2.4.6 / openpyxl 3.1.5) | `python main.py` uçtan uca çalıştı, çıktı referansla birebir aynı |
