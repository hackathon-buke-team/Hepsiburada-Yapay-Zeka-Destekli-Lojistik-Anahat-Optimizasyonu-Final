# Anahat Kontrol Panosu v2 — tasarım şartnamesi

**Tarih:** 2026-08-29 · **Depo:** Hepsiburada Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu (Final)
**Kapsam:** `panel/` altındaki jüri panosunun ikinci sürümü — hem web (Vercel) hem masaüstü (.exe).

---

## 1. Sorun

`panel/` altında altı görünümlü bir React panosu ve bir pywebview/PyInstaller exe kabuğu
zaten mevcut. Ancak:

1. **Hiç derlenmemiş.** `node_modules`, `dist`, `dist-tek`, `dist-exe` yok; `pywebview`
   kurulu değil. `panel/README.md` var olmayan bir `.exe` dosyasını tarif ediyor.
   (2026-08-29'da doğrulandı: `npm ci` 5 sn'de tamamlandı, `tsc -b` **0 hata** verdi —
   kod sağlam, sadece hiç derlenmemiş.)
2. **İddiaları kanıtlamıyor.** Hakem simülatörü 17 kural (gerçekte `simulator.py`'de 28
   ihlal noktası + 4 defter mesajı + 6 beyan denetimi, `chain.py`'de 8 yapısal değişmez)
   denetliyor; pano bunlardan yalnız 2'sini görsel kanıtlıyor. "Hakem ihlali **0**"
   `App.tsx:118`'de string sabiti.
3. **Şartnamenin puanladığı eksenler ekranda yok.** Bölüm 10 çalışma süresini resmen
   değerlendirmeye alıyor (tavan 100 dk); panonun kaynağında "saniye" kelimesi geçmiyor.
   Bölüm 7 genelleştirilebilirlik: üç ölçülmüş senaryo panoda sıfır.
4. **Hazır veri çizilmiyor.** `laneflow` (207 kayıt), `fill_cdf` (4×41 nokta),
   `lanes[].dur` (1.224 değer), `vtypes`'ın 20 parametresinden 16'sı hiç okunmuyor.
5. **Ekranda çelişen sayı çiftleri var.** Bir çelişki jürinin geri kalan tüm grafiklere
   şüpheyle bakmasına yeter.
6. **Canlılık bedava duruyor.** Ölçüldü: `build_plan` 0,14 sn, hakem `simulate()` 0,56 sn
   → panodan tetiklenen tam senaryo + bağımsız denetim ~1,2 sn. Hiç kullanılmıyor.

## 2. Hedef

Jüri karşısında panonun **iddia değil kanıt** sunması; hem çevrimdışı bir `.exe` hem de
paylaşılabilir bir web adresi olarak çalışması; exe'de algoritmanın **canlı** koşabilmesi.

---

## 3. Değişmez ilkeler

### İ1 — `final-teslim/src/` dokunulmaz
Şartname Bölüm 8 algoritmaya müdahaleyi puanlamaya olumsuz yansıtıyor. Hiçbir dosyası
değiştirilmez. İhtiyaç duyulan ara metrikler iki yoldan alınır:

- **Tüketilmeyen dönüş değerleri:** `SimResult.per_vehicle` (665 satır),
  `SimResult.per_demand` (4.046 satır), `PlanEvaluation.notes` (11 kaydırma gerekçesi),
  `HandlingLedger.used`, `TirLedger.count()`.
- **Bağımsız yeniden ölçüm:** modül fonksiyonları (`candidates.plan_lane_day`,
  `optimize._allocate_tir`) dışarıdan çağrılıp sayılır. Bu, enstrümantasyondan daha güçlü
  bir iddiadır: *"algoritmanın içine sayaç koymadık, dışarıdan aynı sonucu ölçtük."*

### İ2 — Panoda elle yazılmış sayı yasak
`REG_TESTS=592`, `'0'` hakem ihlali, `'zorunlu 12 rota · 14 araç/gün'`, `LAB` tablosunun
tüm ölçümleri üretilen JSON'a bağlanır. Bağlanamayan kalırsa ekranda kaynağı yazılır.

### İ3 — Her yeni sayı tutarlılık kapısından geçer
`build_panel_data.py`'nin mevcut 10 assert'i genişletilir (bugün eksik olan `tirgrid`
kapısı dahil); yeni üreticiler kendi kapılarını taşır.

### İ4 — Dış bağlantı yok
CDN, font sunucusu, harita servisi, yerel HTTP sunucusu — hiçbiri. Bu, hem çevrimdışı
çalışmayı hem de kurumsal makinede güvenlik duvarı/port sorunsuzluğunu garantiler.

---

## 4. Mimari

```
final-teslim/src/                     ← DOKUNULMAZ (teslim paketi)
        ↑ import (yalnız okur / çağırır)
panel/kaynak/
   ├── build_panel_data.py   genişletilir → src/data/panel.json
   ├── probe.py          YENİ  bağımsız ölçüm + hakem defteri → src/data/kanit.json
   ├── build_iz.py       YENİ  talep düzeyi rota izleri       → src/data/iz.json
   └── senaryolar.py     YENİ  ön koşulmuş what-if senaryoları → src/data/senaryo.json
        ↓
panel/src/   (React · TypeScript · tek kod tabanı)
        ↓                                  ↓
   vite build                        vite build --mode tek
   dist/  → Vercel                   dist-tek/index.html
                                            ↓
                              desktop/app.py + desktop/kopru.py (js_api)
                              + final-teslim/src gömülü (PyInstaller)
                                            ↓
                              dist-exe/Anahat-Sevkiyat-Panosu.exe
```

### 4.1 Canlılık köprüsü — `js_api`, HTTP sidecar değil

Yerel HTTP sunucusu port çakışması, güvenlik duvarı uyarısı ve kurumsal makinede engel
üretir; İ4'ü de bozar. Bunun yerine:

```python
webview.create_window(..., js_api=Kopru())
```

JS tarafı `window.pywebview.api.kosu_baslat({...})` çağırır. Uzun koşular Python'da bir
iş parçacığında yürür; olaylar bir listeye yazılır, JS 150 ms'de bir `api.poll()` ile
okur. Geri çağırma karmaşası ve kilitlenme riski yok.

### 4.2 Kip tespiti

`window.pywebview` yoksa (web) pano otomatik **KAYITLI** kipine düşer ve aynı arayüzü
`senaryo.json` üzerinden sürer. Tepede kip rozeti daima görünür:

| Ortam | Rozet | Canlı yetenekler |
|---|---|---|
| `.exe` | 🟢 **CANLI** | koşu, hakem denetimi, sabotaj, what-if (3 kademe) |
| Web    | 🟡 **KAYITLI** | ön koşulmuş senaryoların oynatımı; her kartta koşu damgası + parmak izi |

Hangi kipte olunduğu asla belirsiz kalmaz.

### 4.3 Durum birleştirme (yeni özelliklerin ön koşulu)

Bugün durum üç yerde: `App.filter`, `MapView`'ın yerel `pick/focus/zoom/mode/t`'si,
`Fleet`'in yerel `selId/q/sort`'u. Sonuçları: sekme değişiminde `MapView` unmount oluyor;
"Filo tablosunda aç" seçili aracı taşımıyor; global tür süzgeci Fleet çiplerinde
görünmüyor; URL'de yalnız sekme hash'i var.

Hikâye kipi, komut paleti, derin bağlantı ve panik tuşunun **hepsi** tek serileştirilebilir
duruma bağlı. Bu yüzden:

- Tüm durum tek bir `usePano()` store'unda toplanır (`panel/src/pano.ts`).
- URL hash'ine serileştirilir: `#harita?d=01.07.2026&vt=Kamyon&v=V0187&z=2.4&m=zaman&t=1830`
- Görünümler unmount edilmez; `display:none` ile saklanır.

---

## 5. Veri katmanı

### 5.1 `panel.json` genişletmeleri

| Alan | Neden |
|---|---|
| `legs[].ids` kırpması **kaldırılır** | Bugün 24'te kesiliyor; 7 bacakta 27 talep ID kalıcı kayıp. Talep izleme buna bağlı. |
| `meta.built_at`, `meta.hash` | Veri damgası — "bu sayılar hangi koşudan" |
| `meta.fingerprint` | `evaluation.forecast_fingerprint` / `plan_fingerprint` |
| `meta.desi_teslim` (4.977.975) | 6,57 M ile uzlaştırma için |

### 5.2 `kanit.json` (YENİ) — `probe.py` üretir

| Blok | İçerik | Kaynak |
|---|---|---|
| `hakem` | kural × aşama ızgarası; her kural için denetlenen kayıt sayısı + ihlal sayısı | `simulator.py` dönüşleri, aşama planları |
| `uzlasma` | beyan toplamı, hakem toplamı, fark (0,0000 ₺), toleranslar | `export.py`, `evaluation.py` |
| `defter` | pano hesabı ↔ hakem defteri çapraz doğrulaması (137 elleçleme hücresi, 67 tır hücresi, 198 ziyaret, 24 tam dolu) | `HandlingLedger.used`, `TirLedger` |
| `stage0` | 1.886 hat-gün, 41.484 karma, budama sayaçları, 9 tır tahsisi kazanç listesi | `plan_lane_day`, `_allocate_tir` yeniden çağrılarak |
| `erteleme` | 835 karar, 1.004.475 desi, 1.230.148,60 ₺ iç fiyat; objective'in üç bileşeni | `LaneDayPlan.carry_cost` |
| `notlar` | Stage 0'da 11 kaydırma gerekçesi, Stage 3'te 0 | `PlanEvaluation.notes` |
| `talep_sla` | 1.119/4.046 gecikmeli talep, gecikenler desinin %21,2'si | `SimResult.per_demand` |
| `arac` | araç başına km/kullanım saati/maliyet dağılımı | `SimResult.per_vehicle` |
| `sure` | aşama süreleri, uçtan uca, hacim→süre üç nokta | ölçüm |
| `uyum` | 16 kolon şema karşılaştırması, Bölüm 3-11 kontrol listesi, statik tarama sonuçları, manifest alanları | `contract.py`, dosya taraması |
| `genelleme` | 3 senaryo (farklı yıl / farklı hafta / %125) + %250 fizikî sınır | mevcut ölçümler |
| `karsi_olgu` | erteleme kapalı 24,95 M₺, k=3 +205.902 ₺, kiralık tır rezervasyonu 12 ihlal … | mevcut ölçümler |
| `test` | `pytest --json-report` özeti, kural→test eşlemesi | pytest |
| `sabitler` | TIR_MIN_DESI, MAX_TIR_PER_LANE, MAX_CARRY_DESI, CARRY_VAR_TL, MAX_CHAIN_STOPS, STAGE3_MIN_SAVING_TL, toleranslar | modül sabitleri okunarak |

### 5.3 `iz.json` (YENİ) — `build_iz.py` üretir

2.926 talebin bacak bacak rotası (1.343'ü aktarmalı, 12 bacağa kadar), hazır olma saati,
deadline (`ready + 24sa × lane.sla`), gerçek teslim anı, gecikme saati, ceza. Ayrıca bacak
sayısı dağılımı (1→1.542, 2→675, 3→412, 4→283, 5+→14) ve bölünme sayaçları (181 talep →
525 parça, 182 talep çok araca).

### 5.4 `senaryo.json` (YENİ) — `senaryolar.py` üretir

8–12 what-if senaryosu ön koşulur (parametre, sonuç maliyet, araç, SLA, ihlal, süre, koşu
damgası, parmak izi). Web'de KAYITLI kipinin kaynağı; exe'de canlı koşunun karşılaştırma
tabanı.

---

## 6. Görünüm haritası (6 → 9)

| # | Görünüm | Durum | Ana eklemeler |
|---|---|---|---|
| 1 | ÖZET | güçlendirilir | `fill_cdf` doluluk kayması eğrisi · kazanç şelalesi (araç −6,84 M / SLA +1,60 M / net −5,25 M ₺) · merdiven sütunları tıklanabilir · takım kimliği + 997307 |
| 2 | HARİTA | güçlendirilir | yay yön okları · zaman kipinde legend · demo klibi (ilk kalkıştan başlar, bitince durur) · yay memoizasyonu · durum korunur |
| 3 | FİLO | güçlendirilir | iki sekme: **Araçlar** (sayfalama) + **Talepler** (Talep ID → durak durak rota, deadline, gecikme) · maliyet ayrıştırma kutusu · araç türü karşı-olgu tablosu |
| 4 | KORİDOR | **YENİ** | `laneflow` 207 kayıt: sıralanabilir tablo (bacak, desi, araç maliyeti, SLA cezası, ceza payı %, ₺/desi) + haritada ceza payı renk katmanı |
| 5 | KISIT | güçlendirilir | hakem defteri kural×aşama ızgarası · uzlaşma kartı (0,0000 ₺) · kısıt sağlığı sayaçları · kiralık 12×10 doğrulama ızgarası · SLA dürüstlük paneli · "kotası 0" ↔ "kullanılmadı" ayrımı · çapraz doğrulama |
| 6 | TAHMİN | güçlendirilir | bias, `n_cells`, hata histogramı, en kötü 10 hücre · satır düzeyi ayrıştırma · desi uzlaştırma şelalesi · "60 hat" → 289 |
| 7 | MODEL | güçlendirilir | Stage 0 arama uzayı hunisi · erteleme paneli · karar kuralı sabitleri · ortak kabul kapısı · karşı-olgu tablosu · zincir gerekçe kartı |
| 8 | UYUM | **YENİ** | 16 kolon şema karşılaştırması · Bölüm 3-11 kontrol listesi · süre paneli (100 dk ↔ ~150 sn) · genelleştirilebilirlik 3 senaryo + %250 · dayanıklılık |
| 9 | KOŞU | **YENİ** | CANLI/KAYITLI rozeti · koşu konsolu · "planı şimdi denetle" + dosya bırakma · sabotaj demosu · what-if 3 kademe · determinizm/parmak izi |

**Üst katman (rail'de değil, kısayolla):**
`P` sunum kipi · `Space`/`→` hikâye kipi (10 durak) · `Ctrl+K` komut paleti ·
`?` jüri cevap kartları · `Esc` panik sıfırlama · `Z` kartı büyüt · `L` işaret kalemi.

---

## 7. Onarım listesi (yeni özellikten önce)

| Çelişki | Karar |
|---|---|
| Doluluk %79,3 (`meta.avg_fill`, tüm filo) vs %79,03 (Stage 3, spot) | İkisi de doğru, farklı tanım → etiketler ayrılır |
| "%30 altı" 30 (`spot_below_30`) vs histogramda 29 | Tek tanımdan hesaplanır |
| 4,98 M desi (tahmin) vs 6,57 M (bacak toplamı) | Uzlaştırma şelalesi + `Σload = Σdrop = 4.977.975` satırı |
| "60 hat" vs 289 | Etiket: "289 hattın en yoğun 60'ı" |
| Tatil 13 (legend) vs 15 (metin) | Bayrak önceliği açıklanır |
| `REG_TESTS`, `'0 ihlal'`, `'12 rota · 14 araç'`, `LAB` | Üretilen JSON'a bağlanır |
| `ids[]` 24'te kırpma | Kaldırılır |
| `tirgrid` tutarlılık kapısı yok | Assert eklenir |
| Tır sayımı `(araç, ziyaret)` tekilleştirmesi yok | Hakemle hizalanır |
| `tir.over` KPI tonu koşulsuz yeşil | Koşullu yapılır |
| `manifest.takim_id = "BASVURU_NUMARANIZI_YAZIN"` | UYUM'da **sarı uyarı**, asla yeşil |
| Pipeline `'30.06'` ve `daily[1]/[2]` sabit indeks | Veriden türetilir |

---

## 8. Paketleme

### 8.1 Exe sağlamlaştırma
- `app.py`: `try/except` + `ctypes MessageBoxW` yedeği (bugün `--windowed` exe'de hata
  hiçbir yere yazılmıyor — en olası başarısızlık kipi "çift tıkladım, hiçbir şey olmadı")
- WebView2 yoksa → HTML'i varsayılan tarayıcıda açan yedek yol
- `maximized=True` (bugün 1680×980 sabit; 1366×768'de taşıyor)
- `build_exe.py`: `import webview` ön kontrolü; exe üretilmezse sıfırdan farklı çıkış kodu;
  hata hâlinde `.stage` temizliği
- `--version-file` metadata + `--console` teşhis varyantı
- Tek komut: `npm run paket` = `build:tek` → `build:exe`
- **Yedek plan:** `dist-tek/index.html` USB'de (herhangi bir tarayıcıda çift tıkla açılır)

### 8.2 Web
- `vercel.json`: CSP (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`),
  `X-Frame-Options: DENY` / `frame-ancestors 'none'`, `Permissions-Policy`
- Yarışma öncesi Vercel Deployment Protection (parola) açılır — bugün `noindex` var ama
  URL'yi bilen herkes erişiyor
- `npm audit`: `esbuild ≤0.24.2` / `vite ≤6.4.2` açığı yalnız **geliştirme sunucusunu**
  ilgilendiriyor; üretim çıktısı etkilenmiyor. `vite@8` kırıcı yükseltmesi sunum sonrasına
  bırakılır.

---

## 9. Yapılmayacaklar (YAGNI)

- **Ağırlıklı puan tablosu uydurulmaz** — şartnamede yok. Eksenler yalnız: maliyet, süre,
  hatasızlık (4 koşul), Bölüm 8 değişiklik niteliği.
- Kısıt tanımları alıntılanırken kaynak **`stage-2-step-3`** altındaki Gelişmiş Çözüm
  şartnamesi + 16 sayfalık Q&A gösterilir; `TEKNIK_GEREKSINIMLER.pdf` değil (orada yoklar).
- Harita/grafik kütüphanesi eklenmez — çevrimdışı ve tek dosya kalması bu seçimin sonucu.
- Çok kullanıcılı özellik, giriş sistemi, veritabanı yok.
- Pano "bağımsız denetleyici" diye konumlandırılmaz — elleçleme defterini planın beyan
  sütunlarından kuruyor. **Çapraz doğrulama** olarak sunulur: iki bağımsız hesap aynı sayıyı
  buldu.
- `vite@8` yükseltmesi sunum öncesi yapılmaz.

---

## 10. Kabul ölçütleri

1. `npm ci && npm run build` → 0 hata, `dist/` üretilir.
2. `npm run paket` → `dist-exe/Anahat-Sevkiyat-Panosu.exe` üretilir ve **açılır**;
   WebView2 yoksa kullanıcıya görünür bir mesaj verir.
3. `python kaynak/build_panel_data.py && python kaynak/probe.py && python kaynak/build_iz.py`
   → tüm tutarlılık kapıları geçer.
4. Panoda elle yazılmış tek bir jüri-kritik sayı kalmaz (grep ile doğrulanır).
5. Bölüm 7'deki çelişki listesinin tamamı kapanır.
6. Exe'de "Koşuyu başlat" 1,2 sn'de plan + hakem sonucu üretir; web'de aynı arayüz KAYITLI
   rozetiyle senaryodan okur.
7. Sunum kipi 1280×720 ve 1920×1080'de taşma yapmaz.
8. `Esc` her ekrandan bilinen bir zemine döner.

---

## 11. Sıralama

| Faz | İş | Çıktı |
|---|---|---|
| 0 | Derleme zinciri + exe sağlamlaştırma | çalışan `.exe` ve `dist/` |
| 1 | Onarım listesi (Bölüm 7) | çelişkisiz pano |
| 2 | Durum birleştirme (`pano.ts` + URL) | derin bağlantı, durum korunumu |
| 3 | Veri genişletme (`probe.py`, `build_iz.py`, `senaryolar.py`) | `kanit.json`, `iz.json`, `senaryo.json` |
| 4 | Yeni görünümler (KORİDOR, UYUM + KISIT/TAHMİN/MODEL/FİLO güçlendirmeleri) | 8 görünüm |
| 5 | Sunum katmanı (sunum kipi, hikâye, komut paleti, cevap kartları) | canlı demo hazır |
| 6 | Canlılık (`kopru.py`, KOŞU görünümü, sabotaj, what-if) | 9 görünüm |
| 7 | Web güvenlik başlıkları + son paketleme | yayına hazır |
