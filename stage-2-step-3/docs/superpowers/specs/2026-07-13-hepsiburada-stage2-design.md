# Teknofest Hepsiburada Gelişmiş Çözüm — Sistem Tasarımı

**Tarih:** 13 Temmuz 2026
**Mimari:** Hibrit dekompozisyon (günlük MILP + dakika çizelgeleyici + hakem simülatörü)
**Hedef:** Yarışmayı kazanmak — tahmin doğruluğu ve optimizasyon maliyetinde üst sıra, format/kural ihlali riski sıfır.

## 1. Problem Özeti

İki bağlı görev:

1. **Talep tahmini:** 29 Haziran 09:00 – 5 Temmuz 17:00 arası, geçmişte görülen 289 OD çifti × 2 slot (09:00/17:00) × 7 gün = 4.046 satır tahmin. Her kombinasyon için satır zorunlu (düşük değerli de olsa). Talep ID formatı `D00001…`. Gerçek taleple karşılaştırılarak puanlanır.
2. **Taşıma planı:** Kendi tahmin ettiğimiz talepleri saat bazlı araç planıyla taşı. Optimizasyon başarısı kendi tahminlerimiz üzerinden değerlendirilir. Araç ID `V0001…`, talep bölme `D00001-1/-2` (özyinelemeli `-1-1`).

**Maliyet modeli:**
- Araç maliyeti = saatlik kira × kullanım süresi (çıkış elleçleme + bekleme + yol + varış elleçleme) + km × km-maliyeti.
- SLA cezası = geciken desi × ⌈gecikme saati⌉ × 0,4 TL. SLA saati talep tamamlanma anında başlar (09:00/17:00), varış TM'de elleçleme bittiğinde durur. SLA = hat bazında 1 gün (≤773 km) veya 2 gün (≥782 km).
- Elleçleme süresi 0,01 dk/desi (yükleme ve indirme ayrı ayrı); araç içindeki tüm yük aynı anda elleçlenmiş sayılır; süreler en yakın büyük tam dakikaya yuvarlanır.

**Kısıtlar:**
- TM başına günlük elleçleme kapasitesi (desi, gelen+giden+konsolidasyon toplamı, 00:00 reset, gece yarısı aşan işlemde oransal bölünme).
- TM başına günlük tır kapasitesi (sadece Tır tipi; kiralık+spot; gelen+giden ayrımsız; hareketsiz boşalt-yükle = 1 sayılır; 00:00 reset).
- 14 kiralık araç (12 hat) her gün çıkmak zorunda (boş bile olsa), uğrama/dönüş yok, sadece kendi hattında.
- Spot araçlar: sınırsız sefer, uğrama (milk-run) serbest, dolu dönüş serbest; boş dönüş plana yazılmaz.
- Zaman çözünürlüğü dakika; araç günün her dakikası çıkabilir.

**Değerlendirme notları:** Runtime üst sınırı sonradan açıklanacak (dakikalar mertebesi hedeflenir); formata uymayan çözüm değerlendirilmez; kaynak kod teslim edilir.

## 2. Tasarımı Yönlendiren EDA Bulguları (kanıtlı)

| Bulgu | Tasarım kararı |
|---|---|
| Ay sonu çöküşü: son gün ~%1-3, sondan bir önceki 0.6-0.7×, sonraki iş günü 1.1-1.9× (5/5 ayda deterministik). 30 Haz ufkun içinde. | Takvim çarpanı katmanı — en yüksek ROI'li tahmin bileşeni |
| DOW baskın (Pzt 1.93×, Paz 0.10×); 17:00 slotu desinin %91'i; backtest: son 4-8 aynı-DOW medyanı (bayram hariç) %22.4 WMAPE vs naive %29.7 | Taban model = robust DOW istatistiği; ML challenger sadece kanıtlarsa girer |
| Yalova hatları 24 Oca-2 Şub'da açıldı; Kocaeli hiç varış değil; Pazar günü sadece ~90 hat aktif | Ocak verisi Yalova hatlarında yasak; *→Kocaeli grid dışı; aralıklılık kuralı |
| Kiralık filo ~42.2k TL/gün batık; doldurma 0.07-0.10 TL/desi; ~112k desi/gün boş trunk | Optimizer'da kiralık öncelikli katman + rider adayları |
| Tır kapasitesi darboğazı: Yalova 4 (Pzt ihtiyaç ~20), Balıkesir 1 (kiralıkla dolu), 7 TM'de 0; Eskişehir/Kocaeli/Mersin bol | Hub seti ve tır-slot ataması MILP kısıtı |
| Pzt 29 Haz: 8+ TM'de gelen+giden desi kapasitenin %130-140'ı | Gün-aşırı kaydırma + 00:00 reset istismarı + konsolidasyonu Çrş-Cmt'ye itme |
| SLA gevşek: min direkt slack 11.3 saat; 09:00→17:00 dalga birleştirme 289 hatta güvenli; küçük artıkta ceza < adanmış araç | "Bekle+ceza" resmi aday tipi; SLA soft constraint |
| Araç merdiveni: ≤5600 Kamyonet; 5600-7200: <165 km Kamyon / >165 km Hafif; 7200-12000 Kamyon; üstü Tır; İstanbul↔Yalova'da 2 Kamyon > 1 Tır | Aday üretici kuralları |

## 3. Mimari

```
datas/*.xlsx
   │
   ▼
src/data.py        Excel yükleyiciler → tipli, doğrulanmış domain nesneleri
   │                (TM, Hat, AraçTipi, KiralıkHat, Kapasiteler, TalepGeçmişi)
   ▼
src/forecast.py    Tahmin motoru → Forecast[4046 satır]
   │                taban DOW modeli + takvim çarpanları + aralıklılık + slot bölüşümü
   ▼
src/candidates.py  Talep başına rota aday kümesi (direkt / kiralık / rider / 1-hub / bekle+ceza)
   │
   ▼
src/optimize.py    Günlük CP-SAT MILP → araç sayıları, atamalar, konsolidasyon kararları
   │                (gün-gün, devreden yüklerle; geri-besleme döngüsü)
   ▼
src/schedule.py    Dakika çizelgeleyici → çıkış/varış dakikaları, kapasite defterleri,
   │                gece yarısı oransal bölünme, V-ID/D-ID üretimi
   ▼
src/simulator.py   HAKEM SİMÜLATÖRÜ — bağımsız yeniden hesap: maliyet kalemleri +
   │                tüm kural denetimleri; yalnızca çıktı Excel'lerini okur
   ▼
src/export.py      Şablon-birebir Excel yazımı + format validator (yazmadan önce denetim)

run.py             Uçtan uca pipeline (tek komut, runtime ölçümü dahil)
tests/             Unit + property testler; PDF'teki 4 işlenmiş örnek birebir test
experiments/       Backtest, kalibrasyon, ablasyon defterleri
```

### 3.1 data.py — Veri katmanı
- Tüm Excel'ler tek modülden, şema doğrulamalı yüklenir (kolon adı/tipi assert).
- Türetilmiş sabitler: hız (Tır 65, Kamyon 70, Hafif 75, Kamyonet 80 km/s — matristen doğrulanır), hat sözlüğü, SLA saatleri (24/48).
- Çıktı: immutable dataclass'lar; her modül aynı nesneleri kullanır (tek doğruluk kaynağı).

### 3.2 forecast.py — Tahmin motoru
- **Taban:** (OD, slot, DOW) başına Mayıs-Haziran'daki son 6-8 aynı-DOW gözleminin 0.5·medyan + 0.5·ortalama karışımı. Eğitimden dışlanan tarihler: 19 May, 25-31 May (Kurban), her ayın son iki günü, resmi tatiller.
- **Takvim çarpanları:** 29 Haz ×α₁ (~0.7), 30 Haz ×α₂ (~0.02), 1 Tem ×α₃ (~1.3-1.9; 30 Haz'un bastırılmış hacminin 1 Tem'e transferi ayrıca modellenir), 5 Tem Pazar profili. α'lar 5 ay-geçişinden hat-grubu bazında kalibre edilir (hat bazında veri yetmezse global).
- **Aralıklılık:** (OD, slot, DOW) görülme oranı <%20 ise tahmin ~0 (satır dosyada kalır, değer 0 veya minik pozitif — kalibrasyonda karar verilir).
- **Slot bölüşümü:** Top-30 hatta gün toplamı tahmin edilip hattın istikrarlı 09:00 payıyla bölünür (slot korelasyonu 0.36-0.79); kuyruk hatlarda slotlar bağımsız (Croston tarzı: görülme olasılığı × koşullu medyan).
- **Challenger (zaman kaldıkça):** LightGBM (lag/DOW/ay-sonu/hat özellikleri) — çift pencereli backtest'te tabanı ≥1 WMAPE puanı geçerse hat bazında seçici devreye girer, geçemezse atılır.
- **Doğrulama:** backtest pencereleri 15-28 Haz VE 8-21 Haz; metrikler WMAPE + bias, segment bazında (top-30/kuyruk, slot, DOW).

### 3.3 candidates.py — Rota adayları
Her (talep, gün) için sıralı aday kümesi:
1. **Direkt** — merdiven kuralına göre 1-2 araç tipi kombinasyonu,
2. **Kiralık trunk** — OD 12 hattan biriyse,
3. **Rider** — kiralık ilk bacak + aktarma + spot ikinci bacak (detour <1.25),
4. **1-hub aktarma** — hub ∈ {Eskişehir, Kocaeli, Mersin, Yalova, İstanbul}, detour <1.15, tır-slot/elleçleme uygunsa; Kütahya/Bilecik yalnız Kamyon cross-dock,
5. **Bekle+ceza** — sonraki dalga/gün + ⌈saat⌉×0,4 TL/desi maliyeti,
6. **Milk-run** (v2, zaman kalırsa) — aynı yönlü 2-3 duraklı spot rotalar (ör. İstanbul→Yalova→Balıkesir).

### 3.4 optimize.py — Günlük MILP (OR-Tools CP-SAT)
- **Dekompozisyon:** Gün bazlı (kapasiteler günlük); önceki günden devreden yükler girdi. 7 (+2 taşma) gün sırayla çözülür. Gerekirse ileriye bakış: gün d çözülürken d+1 talebinin özet gölgesi (kapasite rezervasyonu) eklenir.
- **Değişkenler:** hat×tip×gün tamsayı araç sayısı; talep→aday atama (talep bölünebilir: continuous pay veya desi-int); hub akış değişkenleri; kiralık doluluk.
- **Kısıtlar:** elleçleme desi/gün-TM, tır adedi/gün-TM (kiralık dahil), araç kapasitesi, kiralık zorunlu çıkış, aday-SLA uygunluğu.
- **Amaç:** Σ araç maliyeti + Σ ceza maliyeti (kuruşa ölçekli tamsayı).
- **Geri-besleme:** çizelgeleyici dakika düzeyinde uygunsuzluk bulursa (elleçleme penceresi taşması vb.) ilgili güne kesme kısıtı eklenip yeniden çözülür (maks 3 iterasyon; sonra güvenli fallback: yükü sonraki dalgaya kaydır).
- **Local search (kalite katmanı):** MILP çözümü üzerinde swap/merge/rebalance hamleleri; simülatör puanıyla kabul (hill-climb / simulated annealing hafif).

### 3.5 schedule.py — Dakika çizelgeleyici
- Girdi: günlük araç/atama kararları. Çıktı: her aracın dakikalı zaman çizelgesi.
- Elleçleme defteri: TM×gün desi sayacı; gece yarısı aşan işlemler oransal bölünür (23:30 kaydırma taktiği bilinçli kullanılır: peak Pazartesi 17:00 yükleri gece geç saatte elleçlenip Salı kotasından düşürülebilir).
- Yuvarlama: transfer + elleçleme süreleri en yakın büyük tam dakika; çıkış/varış `HH:MM`.
- ID üretimi: `V0001…` araçlar (takip edilebilir; aynı spot araç gün içinde çok sefer), `D…-1/-2` bölmeler.

### 3.6 simulator.py — Hakem simülatörü (bağımsız çift implementasyon)
- Girdi: SADECE iki çıktı Excel'i (+ ham veri dosyaları). Optimizer iç durumunu görmez.
- Yeniden hesap: her aracın kullanım süresi ve maliyeti, her talebin elleçleme bitişi ve SLA cezası, kapasite defterleri.
- Denetimler: kapasite aşımı yok, kiralık kuralları (her gün çıkış, rota sapması yok, uğrama yok), tır kapasitesi (gelen+giden, kiralık dahil), talep bütünlüğü (tahmin dosyası ↔ plan dosyası ID eşleşmesi, bölme toplamları), format kuralları.
- Çıktı: kalem kalem maliyet raporu + ihlal listesi (boşsa plan teslim edilebilir).
- **Test seti:** PDF'lerdeki işlenmiş örnekler birebir unit test: (a) 5000 desi → 50 dk elleçleme; (b) 6000 desi 1 saat geç → 2.400 TL; (c) 10.000 desi, 5 saatlik hat → 500 dk kullanım (560 dk 1 saat beklemeli); (d) 23:30'da 10.000 desi → 3.000/7.000 oransal bölünme; (e) 0,92 saat transfer → 56 dk yuvarlama.

### 3.7 export.py — Format güvencesi
- Şablonlarla birebir kolon adları/sırası/tipleri (`TALEP TAHMİNİ.xlsx`, `TAŞIMA PLANI.xlsx`).
- Tarih `DD.MM.YYYY`, saat `HH:MM`, ID formatları regex denetimli.
- Validator geçmeden dosya yazılmaz; yazılan dosya geri okunup simülatörden geçirilir.

## 4. Riskler ve Kararlar

| Risk | Karar/Önlem |
|---|---|
| Tır kapasitesi semantiği (gelen+giden birlikte sayılıyor; kiralık dahil) — Balıkesir/Tekirdağ fiilen spot tıra kapalı | Muhafazakâr yorum benimsendi (gelen+giden ortak havuz); bu TM'lere spot tır planlanmaz. Q&A oturumunda teyit sorusu sorulacak |
| Runtime limiti belirsiz | Tasarım hedefi: uçtan uca <5 dk; CP-SAT gün başına saniye mertebesi; her bileşen süre loglar |
| Tahmin-optimizasyon bağı: optimizasyon kendi tahminimizle puanlanıyor → plan aşamasında talep belirsizliği YOK (deterministik). Tek bağ: tahmini şişirmek plan maliyetini şişirir, düşürmek WMAPE bozar | Tahmin bias'ı ~0 tutulur (WMAPE simetrik cezalandırır); plan tahmin dosyasındaki desilerle birebir tutarlı üretilir; "belirsizliğe karşı yedek kapasite" gibi bir kavram bilinçli olarak yok |
| Sıfır tahminli satırların kabulü (0 mı, minik pozitif mi?) | Varsayılan 0; Q&A/format teyidi alınamazsa 1 desi minik pozitif alternatifi hazır |
| MILP'in dakika detayından habersizliği | SLA slack ≥11.3 saat tampon + çizelgeleyici geri-besleme döngüsü |
| Çift implementasyon uyuşmazlığı (optimizer maliyeti ≠ simülatör maliyeti) | Simülatör her zaman hakem; CI'da her plan simülatörden geçer; fark >0 ise build kırmızı |

## 5. Test Stratejisi
- **Unit:** PDF örnekleri (5+ adet, madde 3.6) + yuvarlama/oransal bölünme kenar durumları + format validator.
- **Property:** rastgele küçük senaryolar → simülatör kısıt ihlali bulamamalı; bölünen taleplerin desi toplamı korunmalı.
- **Backtest:** tahmin çift pencere; optimizer için "bilinen geçmiş hafta" senaryosu (ör. 15-21 Haz gerçek talebiyle plan üret, maliyeti raporla — regresyon metriği).
- **Uçtan uca:** `run.py` tek komut; çıktılar simülatör + validator'dan temiz geçmeli; runtime raporu.

## 6. İş Sırası (rahat tempo, her aşama teslim edilebilir)
1. **Temel:** repo iskeleti, data.py, simulator.py çekirdeği, PDF örnek testleri, backtest harness.
2. **Tahmin v1:** taban model + takvim çarpanları + kalibrasyon deneyi → `TALEP TAHMİNİ.xlsx`.
3. **Plan v1 (direkt-only):** candidates (1,2,5) + günlük MILP + çizelgeleyici → ilk geçerli plan + maliyet baseline.
4. **Konsolidasyon:** rider + 1-hub adayları + peak-Pazartesi taktikleri → maliyet iterasyonları (her adım simülatör puanıyla ölçülür).
5. **Kalite katmanları:** local search, LightGBM challenger, muhafazakâr kuantil deneyi, milk-run v2.
6. **Sertleştirme:** property testler, runtime optimizasyonu, son format denetimi, kaynak kod paketleme.

## 7. Kapsam Dışı
- Gerçek zamanlı/stokastik yeniden planlama (yarışma tek atımlık plan istiyor).
- 2+ hub'lı zincirler (marjinal getiri düşük, SLA/elleçleme riski yüksek — veri desteklemiyor).
- Kuş uçuşu mesafe hesabı (yasak; matris birebir kullanılır).
