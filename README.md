# Hepsiburada — Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu

**TEKNOFEST 2026 · Takım Büke · Final Aşaması (Backtest)**

Bu depo, yarışmanın **Final Backtest** aşaması için hazırlanan çalıştırılabilir teslim
paketini, onu üreten Gelişmiş Çözüm aşaması çalışma deposunu, jüri sunum materyallerini
ve tüm doğrulama kanıtlarını bir arada tutar.

---

## Sonuç özeti

| | Değer |
|---|---|
| **Toplam maliyet** | **11.232.476,73 TL** — temel plandan **−%31,84** |
| **Hakem ihlali** | **0** (her aşamada) |
| Araç maliyeti / SLA cezası | 8.616.944,73 TL / 2.615.532,00 TL |
| Fiziksel araç | 1.269 → **665** |
| Spot araç doluluğu | %48,02 → **%79,03** |
| Uçtan uca çalışma süresi | ~150 sn (referans veri setinde) |
| Regresyon testi | **592 / 592** geçiyor |

Maliyet merdiveni — her aşama bir öncekini girdi alır ve **yalnızca hakem simülatörü
0 ihlalle daha düşük maliyet onaylarsa** kabul edilir:

| Aşama | Araç maliyeti (TL) | SLA cezası (TL) | **Toplam (TL)** | İhlal | Araç |
|---|---:|---:|---:|---:|---:|
| Stage 0 — temel plan | 15.460.592,57 | 1.020.367,20 | **16.480.959,77** | 0 | 1.269 |
| Stage 1 — aynı-hat onarım | 12.510.401,25 | 2.169.783,60 | **14.680.184,85** | 0 | 1.092 |
| Stage 2 — milk-run (≤4 durak) | 8.752.512,29 | 2.560.826,00 | **11.313.338,29** | 0 | 693 |
| **Stage 3 — rota-ortası yük alma** | **8.616.944,73** | **2.615.532,00** | **11.232.476,73** | **0** | **665** |

---

## Hızlı başlangıç

Değerlendirmeye giren paket `final-teslim/` altındadır:

```bash
cd final-teslim
pip install -r requirements.txt
python main.py
```

Çıktı: **`final-teslim/out/Tasima-plani.xlsx`** (tek sayfa, 16 kolon, şablon birebir).

Girdi dosyası sırasıyla iki yoldan aranır:

| Öncelik | Yöntem | Değer |
|---|---|---|
| 1 | Ortam değişkeni | `TEKNOFEST_INPUT_FILE` (mutlak yol) |
| 2 | Sabit göreli yol | `data/one_week_backtest.xlsx` |

```powershell
# Windows PowerShell
$env:TEKNOFEST_INPUT_FILE = "C:\yol\one_week_backtest.xlsx"
python main.py
```

---

## Depo düzeni

```
.
├── final-teslim/              ← ★ FİNAL TESLİM PAKETİ (değerlendirmeye giren kod)
│   ├── main.py                   Bölüm 3: tek giriş noktası, argümansız
│   ├── teknofest_manifest.json   Bölüm 6 manifest
│   ├── requirements.txt          Bölüm 9: yalnız pandas + openpyxl
│   ├── README.md                 Paketin kendi dokümantasyonu
│   ├── DEGISIKLIKLER.md          Bölüm 8: önceki teslimden farkların tamamı
│   ├── KONTROL_LISTESI.md        Bölüm 11: teslim öncesi kontrol listesi
│   ├── src/                      Algoritma + hakem simülatörü
│   ├── tests/                    592 regresyon testi
│   ├── tools/                    Sentetik girdi üretici + bağımsız çıktı denetleyici
│   ├── datas/                    Statik referans verileri (değişmez)
│   ├── data/                     Bölüm 4 yedek girdi yolu
│   └── out/                      Üretilen Tasima-plani.xlsx
│
├── stage-2-step-3/            ← Gelişmiş Çözüm aşaması çalışma deposu
│   ├── README.md                 En zengin teknik anlatım (ölçülmüş tüm tablolar)
│   ├── ARCHITECTURE.md           Derin teknik referans
│   ├── PLAN.md / ROADMAP.md      Durum panosu ve yol haritası
│   ├── run.py                    Tahmin + optimizasyon uçtan uca hattı
│   ├── docs/figures/             README grafikleri + yeniden üretim betikleri
│   ├── docs/superpowers/         Aşama planları, tasarım şartnameleri, kabul raporları
│   └── *.pdf                     Jüri Q&A ve aşama bilgilendirme dokümanları
│
├── panel/                     ← Anahat Sevkiyat Panosu (jüri kontrol panosu)
│   ├── src/                      React arayüzü — altı görünüm
│   ├── kaynak/                   panel.json üreteci (tek gerçeğin kaynağı)
│   ├── desktop/                  pywebview kabuğu + .exe derleyici
│   └── README.md                 panonun kendi dokümantasyonu
│
├── sunum/
│   ├── v2.html                   Jüri sunumu (16 slayt)
│   └── dokumanlar/               Jüri sunumu için hazırlanan Word dökümanları
│
├── zzips/                     Teslim edilen orijinal zip arşivleri
├── TEKNIK_GEREKSINIMLER.pdf   Final Backtest teknik gereksinimleri (Bölüm 1-11)
├── Talep-tahmini.xlsx         Gelişmiş Çözüm aşamasında teslim edilen tahmin
└── Tasima-plani.xlsx          Gelişmiş Çözüm aşamasında teslim edilen plan
```

---

## Çözümün yapısı

### Talep tahmini

```
tahmin = DOW_medyan_tabanı(k=4, tatiller/ay sonları hariç) × takvim_çarpanı(gün)
```

Üç ölçülmüş takvim çarpanı: ay sonundan bir önceki gün ×0,6752 · ayın son günü
**×0,0198** · ayın ilk günü ×1,2072. Ay sonu çöküşü veride beş ay boyunca istisnasız
gözlendi; 30 Haziran'ı normal bir salı sayan bir model tek başına ~1,1 milyon desi hata
üretirdi.

Frozen (tek atışlık) backtest — eğitim penceresi hedeften önce kesilir, ufuk içinde
yeniden eğitim yoktur:

| Pencere | Naive | DOW medyanı | **Bizim model** |
|---|---:|---:|---:|
| Normal hafta · 15–21 Haz | 0,2592 | 0,2174 | **0,2174** |
| Ay sonu haftası · 30 Mar – 5 Nis | 0,6972 | 0,5328 | **0,4464** |

> **Not:** Final değerlendirmesinde tahmin modülü çalıştırılmaz (Teknik Gereksinimler
> Bölüm 2). `main.py` `src.forecast`'i import bile etmez.

### Optimizasyon merdiveni

```
Stage 0 · temel plan
  Zorunlu kiralık filo → tır ziyaret bütçesi → spot araç karması + devir

Stage 1 · aynı-hat onarım
  1.003 donör değerlendirildi → 177 hamle kabul → 177 Spot araç silindi

Stage 2 · milk-run (≤4 durak)
  93 grup · 5.426 çift + 96.369 çoklu kombinasyon → 227 zincir kabul

Stage 3 · rota ortasında yük alma (Tier A)
  227 hedef rota × 340 donör = 135.660 çift → 28 yük alma kabul
```

### Hakem simülatörü

`src/simulator.py`, planlayıcıdan tamamen bağımsız yazılmış **ikinci bir uygulamadır**.
Yalnızca çıktı DataFrame'lerini okur; maliyeti, SLA'yı ve 17 kuralı sıfırdan yeniden
hesaplar. Bir aday plan hakemden **0 ihlalle** geçmezse kabul edilmez. Aramanın kendi
aritmetiğiyle bulduğu tasarruf ile hakemin ölçtüğü fark, kuruşun milyonda birine kadar
aynı sayı olmak zorundadır.

---

## Final Backtest gereksinim karşılıkları

| Bölüm | Gereksinim | Bu pakette |
|---|---|---|
| 2 | Yalnızca optimizasyon; tahmin modülü çağrılmaz | `main.py` import grafiğinde `src.forecast`/`backtest`/`frozen_backtest` **yok** |
| 3 | Kök dizinde `main.py`, argümansız, etkileşimsiz | `final-teslim/main.py` — `input()` yok, dosya seçici yok |
| 4 | Girdi: env değişkeni **veya** `data/one_week_backtest.xlsx` | `src/contract.py::resolve_input_path`, `read_demand_table` |
| 5 | Çıktı: `Tasima-plani.xlsx`, tek sayfa, 16 kolon birebir | `src/contract.py::write_final_plan` — yazımdan sonra diskten geri okuyup şemayı yeniden doğrular, sonra atomik `os.replace` |
| 6 | `teknofest_manifest.json` | `final-teslim/teknofest_manifest.json` |
| 7 | Gömülü takvim tarihi yok | Ufuk `Tarih` kolonundan türetilir; 3 farklı hafta/hacimle ölçüldü |
| 8 | Değişiklikler yalnız entegrasyon amaçlı | 2 modülde davranış genişletme; aynı girdide **0 farklı hücre** |
| 9 | `requirements.txt`, çalışma anında `pip install` yok | `pandas` + `openpyxl` |
| 10 | 100 dk zaman aşımı, çıktı üretilmeli, çıkış kodu 0 | Kademeli yayın + sert süre sınırı (`TEKNOFEST_TIME_BUDGET_MIN`) |

Madde madde doğrulama: [`final-teslim/KONTROL_LISTESI.md`](final-teslim/KONTROL_LISTESI.md)

---

## Genelleştirilebilirlik kanıtı (Bölüm 7)

| Senaryo | Ufuk | Talep | Desi | Süre | İhlal | Kazanç |
|---|---|---:|---:|---:|---:|---:|
| Referans (teslim edilen) | 29.06.2026 – 05.07.2026 | 4.046 | 4.977.975 | 150 sn | 0 | −%31,8 |
| Farklı yıl + 4 günlük ufuk + `REQ_` kimlikler + `HH:MM` | 25.05.2025 – 28.05.2025 | 1.808 | 1.214.316 | 171 sn | 0 | −%45,8 |
| Farklı hafta + %125 hacim + `HH:MM:SS` | 02.09.2026 – 08.09.2026 | 2.925 | 6.222.428 | 143 sn | 0 | −%28,0 |

---

## Teslim öncesi tek işlem

> ⚠ `final-teslim/teknofest_manifest.json` içindeki `takim_id` alanı hâlâ yer tutucudur
> (`"BASVURU_NUMARANIZI_YAZIN"`). Teslimden önce başvuru numaranızı yazın.

---

## Notlar

* `stage-2-step-3/` dizini kendi başına bir git deposuydu. Bu depoya dosyalarıyla
  birlikte dahil edebilmek için `.git` dizini `.git-yedek` adına taşındı ve
  `.gitignore`'a eklendi. Geri almak için:
  `mv stage-2-step-3/.git-yedek stage-2-step-3/.git`
* Statik referans verileri (`datas/`) salt-okunurdur ve değiştirilmemelidir.
* `datas/tir_kapasiteleri v2.xlsx` jürinin güncellediği sürümdür — v1 kullanılmamalıdır.
