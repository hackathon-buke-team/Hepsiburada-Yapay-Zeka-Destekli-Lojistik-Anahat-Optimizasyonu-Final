# TEKNOFEST Final Backtest — Teslim Paketi

Hepsiburada · Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu — **Final aşaması**

Bu paket, *Final Backtest — Teknik Gereksinimler* dokümanına uyacak şekilde
hazırlanmış çalıştırılabilir teslimdir. Optimizasyon algoritması, yarışmanın
Gelişmiş Çözüm aşamasında teslim edilen kaynak kodların **aynısıdır**; bu
pakette yapılan değişiklikler yalnızca entegrasyon amaçlıdır ve tamamı
[`DEGISIKLIKLER.md`](DEGISIKLIKLER.md) dosyasında satır satır listelenmiştir.

> **Kanıt:** Aynı talep tablosuyla çalıştırıldığında `python main.py`, önceki
> aşamada teslim edilen `Tasima-plani.xlsx` ile **hücre hücre birebir aynı**
> dosyayı üretir — 5.523 satır × 16 kolon, **0 farklı hücre**, 11.232.476,73 TL,
> 0 hakem ihlali.

---

## Hızlı başlangıç

```bash
pip install -r requirements.txt
python main.py
```

Çıktı: **`out/Tasima-plani.xlsx`**

Girdi dosyası sırasıyla şu iki yoldan aranır (Bölüm 4 — her ikisi de
desteklenir):

| Öncelik | Yöntem | Değer |
|---|---|---|
| 1 | Ortam değişkeni | `TEKNOFEST_INPUT_FILE` (mutlak yol) |
| 2 | Sabit göreli yol | `data/one_week_backtest.xlsx` |

```bash
# Linux / macOS
TEKNOFEST_INPUT_FILE=/mutlak/yol/one_week_backtest.xlsx python main.py

# Windows PowerShell
$env:TEKNOFEST_INPUT_FILE = "C:\yol\one_week_backtest.xlsx"; python main.py
```

Paketle birlikte gelen `data/one_week_backtest.xlsx`, ekibin kendi tahmin
modülünün ürettiği 29.06.2026–05.07.2026 talep tablosudur; ek bir dosya
verilmezse `python main.py` bu tabloyla uçtan uca çalışır.

---

## Gereksinim karşılıkları

| Bölüm | Gereksinim | Bu pakette |
|---|---|---|
| 3 | Kök dizinde `main.py`, argümansız, etkileşimsiz | [`main.py`](main.py) — `input()` yok, dosya seçici yok, IDE/Colab bağımlılığı yok |
| 2 | Yalnızca optimizasyon; tahmin modülü çağrılmaz | `main.py`'den ulaşılabilen modüller arasında `src.forecast`, `src.backtest`, `src.frozen_backtest` **yoktur** (import grafiğiyle doğrulandı) |
| 4 | Girdi: env değişkeni **veya** `data/one_week_backtest.xlsx`, 6 kolonluk şema | `src/contract.py` → `resolve_input_path`, `read_demand_table` |
| 5 | Çıktı: `Tasima-plani.xlsx`, tek sayfa, 16 kolon birebir | `src/contract.py` → `write_final_plan`; yazımdan sonra diskten geri okuyup kolon adı/sırasını ve satır sayısını yeniden doğrular, sonra atomik `os.replace` yapar |
| 6 | `teknofest_manifest.json` | [`teknofest_manifest.json`](teknofest_manifest.json) |
| 7 | Gömülü takvim tarihi yok, farklı hafta/hacimle çalışır | Ufuk `Tarih` kolonundan türetilir; ölçülen senaryolar aşağıda |
| 9 | `requirements.txt`, çalışma anında `pip install` yok | [`requirements.txt`](requirements.txt) — yalnız `pandas` + `openpyxl` |
| 10 | 100 dk zaman aşımı, çıktı üretilmeli, çıkış kodu 0 | Referans veri setinde uçtan uca **~150 sn**; ayrıca kademeli yayın + sert süre sınırı (aşağıda) |

---

## Boru hattı (main.py ne yapıyor)

```
Bölüm 4 talep tablosu
        │
        ▼
 src/contract.py ─── şema/tip normalizasyonu, kanonik talep kimlikleri,
        │            ufkun girdiden türetilmesi
        ▼
 src/optimize.py ─── Stage 0: kiralık doldurma + tır ziyaret bütçesi +
        │            hat-gün araç karması + boşaltma günleri
        ▼
 src/repair.py ───── Stage 1: aynı-hat onarımı
        ▼
 src/milkrun.py ──── Stage 2: ≤4 duraklı milk-run zincirleri
        ▼
 src/pickup.py ───── Stage 3: rota ortasında yük alma (Tier A)
        ▼
 src/simulator.py ── hakem: her aşamayı kural-birebir yeniden fiyatlandırır;
        │            yalnız **0 ihlalle daha ucuz** aday kabul edilir
        ▼
 out/Tasima-plani.xlsx   (16 kolon, tek sayfa)
```

Her aşama bir öncekini girdi alır. Aday reddedilirse (tasarruf yok veya ihlal
var) **bir önceki aşamanın planı korunur**.

### Bölüm 10 güvenlikleri

İki mekanizma, "çıktı üretilmez" ve "zaman aşımı" hatalarını engeller:

1. **Kademeli yayın.** Geçerli ilk plan (Stage 0) elde edilir edilmez
   `out/Tasima-plani.xlsx` yazılır; sonraki her kabul edilen aşama dosyayı
   atomik olarak günceller. Beklenmedik bir hata hâlinde diskte her zaman
   geçerli bir taşıma planı bulunur.
2. **Sert süre sınırı.** Arama aşamaları kendi içlerinde bölünemediği için
   her biri ayrı bir daemon iş parçacığında, kalan bütçeyle sınırlı olarak
   çalıştırılır. Sınır dolarsa aşama terk edilir, o ana kadarki en iyi plan
   korunur ve süreç normal biçimde (çıkış kodu 0) sonlanır. Bütçe
   `TEKNOFEST_TIME_BUDGET_MIN` ile ayarlanır (varsayılan **100**, Bölüm 10
   ile aynı); bunun %90'ı aramaya, kalanı çıktının yazılmasına ayrılır.

Ölçülmüş davranış (`TEKNOFEST_TIME_BUDGET_MIN=0.6`, yani 36 sn bütçe):

```
[Stage 1 aynı-hat onarım] kabul edildi; tasarruf 1,800,774.93 TL (13.4 sn)
    → çıktı güncellendi (Stage 1)
[Stage 2 milk-run] süre sınırında terk edildi (11.4 sn); önceki plan korunuyor
[Stage 3 rota-ortası yük alma] atlandı: arama bütçesi tükendi
Toplam süre : 32.4 sn      → çıkış kodu 0, geçerli plan diskte (0 ihlal)
```

---

## Doğrulama

### 1. Referans veri setinde sonuç değişmedi

| Aşama | Araç maliyeti (TL) | SLA cezası (TL) | **Toplam (TL)** | İhlal |
|---|---:|---:|---:|---:|
| Stage 0 — temel plan | 15.460.592,57 | 1.020.367,20 | **16.480.959,77** | 0 |
| Stage 1 — aynı-hat onarım | 12.510.401,25 | 2.169.783,60 | **14.680.184,85** | 0 |
| Stage 2 — milk-run | 8.752.512,29 | 2.560.826,00 | **11.313.338,29** | 0 |
| **Stage 3 — rota-ortası yük alma** | **8.616.944,73** | **2.615.532,00** | **11.232.476,73** | **0** |

Üretilen dosya ile önceki teslim arasındaki fark: **0 hücre**.

### 2. Bölüm 7 — farklı hafta, farklı hacim, farklı biçim

`tools/make_test_input.py` mevcut talep tablosundan sentetik girdi türetir
(tarih kaydırma, hacim ölçekleme, ufuk kısaltma, kimlik ve saat biçimi
değiştirme). `tools/verify_output.py` üretilen planı diskten geri okuyup
bağımsız olarak hakem simülatöründen geçirir.

```bash
python tools/make_test_input.py --shift-days -400 --scale 0.35 --days 4 \
    --id-prefix "REQ_" --time-style hhmm --out /tmp/farkli_hafta.xlsx
TEKNOFEST_INPUT_FILE=/tmp/farkli_hafta.xlsx python main.py
python tools/verify_output.py --input /tmp/farkli_hafta.xlsx
```

| Senaryo | Ufuk | Talep | Desi | Süre | İhlal | Kazanç |
|---|---|---:|---:|---:|---:|---:|
| Referans (teslim edilen) | 29.06.2026 – 05.07.2026 (7 gün) | 4.046 | 4.977.975 | 150 sn | 0 | −31,8 % |
| Farklı yıl + 4 günlük ufuk + `REQ_` kimlikler + `HH:MM` | 25.05.2025 – 28.05.2025 | 1.808 | 1.214.316 | 171 sn | 0 | −45,8 % |
| Farklı hafta + %125 hacim + `D…` kimlikler + `HH:MM:SS` | 02.09.2026 – 08.09.2026 | 2.925 | 6.222.428 | 143 sn | 0 | −28,0 % |

Her üç senaryoda da çıkış kodu 0, şema birebir, beyan edilen toplam maliyet
ile hakem toplamı arasındaki fark 0,0000 TL.

> **Fizikî sınır — bilinçli not.** Ağın elleçleme kapasitesi referans hafta
> için zaten neredeyse tamamen doludur: İstanbul, 01.07.2026 — o günün
> yükleme + indirme talebi 395.825 desi, günlük kapasite 394.786 desi.
> Yani hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme
> kısıtı **hiçbir plan tarafından** sağlanamaz; bu bir kod kusuru değil,
> veri setinin fizikî olarak çözümsüz olmasıdır.
>
> %250 hacimli sentetik veri setinde ölçülen davranış tam olarak budur:
> Stage 0 temel planı 69 elleçleme kapasitesi ihlaliyle üretildi
> (ihlallerin tamamı, o gün o merkezde talebin kapasiteyi aşmasından
> kaynaklanıyor — ör. Erzincan 80.160 desi / kapasite 58.673), Stage 1
> adayı bu nedenle **doğru biçimde reddedildi** ve temel plan korundu.
> Kod bu koşulda da çökmedi ve Bölüm 5 şemasına birebir uyan bir plan
> yazdı. Bu senaryoda Stage 2 araması kombinatoryal olarak büyüyor (grup
> başına C(n,4)); sert süre sınırı da tam bu durum için vardır — sınır
> dolduğunda aşama terk edilir ve o ana kadarki plan yayınlanır.
>
> Bu senaryoda süreç Stage 2'nin ortasında **zorla sonlandırıldığında**
> bile diskte 3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru bir
> `Tasima-plani.xlsx` bulundu — kademeli yayının sağladığı garanti budur.

### 3. Regresyon testleri

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

592 test — 528'i önceki teslimden değişmeden gelir, 64'ü bu paketle eklenen
`src/contract.py` entegrasyon katmanını kapsar.

### 4. Temiz sanal ortam

`python -m venv` ile kurulan, yalnızca `requirements.txt` bağımlılıklarını
içeren temiz bir ortamda (pandas 2.3.3, numpy 2.4.6, openpyxl 3.1.5)
`python main.py` uçtan uca çalıştırıldı: çıkış kodu 0, çıktı referans
teslimle birebir aynı.

---

## Dosya düzeni

```
final-teslim/
├── main.py                    ← Bölüm 3: tek giriş noktası (YENİ)
├── teknofest_manifest.json    ← Bölüm 6 (YENİ)
├── KONTROL_LISTESI.md         ← Bölüm 11 kontrol listesi (YENİ)
├── DEGISIKLIKLER.md           ← Bölüm 8 değişiklik kaydı (YENİ)
├── requirements.txt           ← Bölüm 9 (çalışma zamanı)
├── requirements-dev.txt       ← yalnız test
├── data/
│   └── one_week_backtest.xlsx ← Bölüm 4 yedek girdi yolu
├── datas/                     ← statik referans veriler (DEĞİŞMEDİ)
│   ├── Araç_Kapasite_Maliyet_Saat.xlsx
│   ├── Ellecleme-kapasite.xlsx
│   ├── Kiralık_Araclar.xlsx
│   ├── sehirler_arasi_lojistik.xlsx
│   ├── tir_kapasiteleri v2.xlsx
│   └── teknofest26_gelismis.xlsx   (geçmiş talep — final koşusunda okunmaz)
├── out/
│   └── Tasima-plani.xlsx      ← Bölüm 5 çıktısı
├── src/
│   ├── contract.py            ← girdi/çıktı sözleşmesi (YENİ, entegrasyon)
│   ├── optimize.py  candidates.py  repair.py  milkrun.py  pickup.py
│   ├── chain.py  schedule.py  ledger.py                  ← algoritma (DEĞİŞMEDİ)
│   ├── simulator.py  evaluation.py  export.py            ← hakem (DEĞİŞMEDİ)
│   ├── data.py  schemas.py                               ← bkz. DEGISIKLIKLER.md
│   ├── timeutil.py                                       ← (DEĞİŞMEDİ)
│   └── forecast.py  backtest.py  frozen_backtest.py      ← tahmin, ÇAĞRILMAZ
├── tests/                     ← 592 regresyon testi
├── tools/
│   ├── make_test_input.py     ← Bölüm 7 sentetik girdi üretici (opsiyonel)
│   └── verify_output.py       ← çıktı denetleyici (opsiyonel)
└── run.py                     ← önceki teslimin tahmin+optimizasyon hattı
                                 (DEĞİŞMEDİ, referans; değerlendirmede çalışmaz)
```

`tools/` ve `tests/` klasörleri ile `run.py` değerlendirme koşusunun parçası
değildir; `main.py` bunların hiçbirini içe aktarmaz.

---

## Notlar

* **Çalışma anında internet erişimi gerekmez.** `main.py` içinde `pip
  install`, ağ çağrısı veya kullanıcı etkileşimi yoktur.
* **Docker sunulmamıştır.** Bölüm 9'un varsayılan/beklenen yolu olan düz
  Python + `requirements.txt` yolu sunulmakta ve doğrulanmış olarak teslim
  edilmektedir.
* **Statik referans veriler** (`datas/`) değerlendirme sırasında
  değiştirilmeyecek verilerdir ve teslim paketindeki hâliyle kullanılır.
* **`teknofest26_gelismis.xlsx`** yalnızca tahmin modülünün geçmiş veri
  kaynağıdır. Final koşusunda tahmin çalıştırılmadığı için bu dosya
  okunmaz (`load_all(..., with_demand=False)`), böylece ~8 sn çalışma
  süresi tasarruf edilir. Dosya, `run.py`'nin referans olarak
  çalışabilmesi için pakette bırakılmıştır.
