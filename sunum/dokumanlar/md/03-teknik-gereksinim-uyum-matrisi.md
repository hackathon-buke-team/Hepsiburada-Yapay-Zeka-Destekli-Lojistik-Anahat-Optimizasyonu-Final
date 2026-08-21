# Teknik Gereksinim Uyum Matrisi

TEKNOFEST 2026 · Hepsiburada — Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu
Takım: Büke · Aşama: Final Backtest · Paket: `final-teslim/`

---

## 1. Amaç ve Okuma Kılavuzu

### 1.1 Bu belge ne için var

Final değerlendirmesi, kodumuzun bize önceden bildirilmeyen bir talep tablosuyla tek komutla çalıştırılması ve ürettiği taşıma planının puanlanması üzerine kuruludur. Bu süreçte iki tür risk vardır: **format riski** (çıktı şemasından sapan çalıştırma değerlendirmeye alınmaz) ve **kural riski** (planın fiziksel veya sözleşmesel bir kısıtı ihlal etmesi). Bu belge, her iki riskin de madde madde kapatıldığını göstermek için yazılmıştır.

Belgenin omurgası tek bir yapıdır; Bölüm 2 ve Bölüm 4'teki her madde aşağıdaki dört adımı sırayla tekrarlar:

1. **Jüri ne istedi** — resmî dokümandan alıntı veya sadık özet.
2. **Biz ne yaptık** — somut uygulama, hangi mekanizma ile.
3. **Kanıt** — dosya adı, fonksiyon adı, ölçülmüş sayı, test adı veya jüri Q&A soru numarası.
4. **Risk / not** — varsa bilinen sınır, açık yorum konusu veya bilinçli muhafazakârlık.

Hiçbir iddia kanıtsız bırakılmamıştır. Bir sayı yazıyorsa o sayı ya teslim edilen çıktı dosyasından, ya hakem simülatörünün bağımsız hesabından, ya da bir regresyon testinin sabitlediği değerden gelir.

### 1.2 Kaynak dokümanlar

Bu matrisin dayandığı dört bağlayıcı kaynak vardır:

| Kaynak | Kapsam | Bu belgedeki karşılığı |
|---|---|---|
| Final Backtest — Teknik Gereksinimler | Bölüm 1-11, entegrasyon ve teslim kuralları | Bölüm 2 ve Bölüm 3 |
| Teknofest Gelişmiş Çözüm Aşaması Bilgilendirme | Problem tanımı, veri setleri, EK KISIT 1-2, çözüm formatları | Bölüm 4 |
| Gelişmiş Çözüm Soru-Cevap Oturumu Öncesi Gelen Sorular | 11 takımın soruları ve jürinin bağlayıcı cevapları | Bölüm 5 |
| Jüriden gelen ek netleştirme mesajı | Boş spot araç, HH:MM, yukarı yuvarlama, gece yarısı oransal bölme | Bölüm 5 |

### 1.3 Bir bakışta sonuç

| Ölçüt | Değer |
|---|---|
| Toplam maliyet (teslim edilen plan) | 11.232.476,73 TL |
| Temel plana göre iyileşme | -%31,84 |
| Hakem simülatörü ihlali | 0 (dört aşamanın hepsinde) |
| Beyan edilen maliyet ile hakem hesabı farkı | 0,0000 TL |
| Çıktı boyutu | 5.523 satır x 16 kolon, tek sayfa |
| Önceki teslimle fark | 0 farklı hücre |
| Uçtan uca çalışma süresi | Yaklaşık 150 saniye (sınır 100 dakika) |
| Regresyon testi | 592 test, tamamı geçiyor |
| Değişen algoritma modülü sayısı | 0 |

### 1.4 Terimler

- **Aşama (stage):** Optimizasyon boru hattının dört adımından biri. Stage 0 temel plan, Stage 1 aynı-hat onarım (same-lane repair), Stage 2 milk-run zincirleme, Stage 3 rota-ortası yük alma (mid-route pickup).
- **Hakem (referee):** `src/simulator.py`. Planlayıcıdan bağımsız yazılmış ikinci uygulama; yalnız çıktı tablolarını ve statik referans veriyi okuyup maliyeti ve kuralları sıfırdan yeniden hesaplar.
- **Bacak (leg):** Tek bir araç hareketi (çıkış TM'den varış TM'ye).
- **Fiziksel rota (physical route):** Tek bir `Araç ID` altındaki bacak zinciri. Bir milk-run zinciri dört bacaklı olsa bile tek fiziksel rotadır.
- **Defter (ledger):** Günlük kapasite sayaçları. `HandlingLedger` elleçleme desisini, `TirLedger` tır ziyaretlerini tutar.
- **İhlal (violation):** Hakemin ürettiği, planın kabul edilemez olduğunu gösteren kural bozulması. SLA gecikmesi ihlal değildir; fiyatlanmış bir maliyet kalemidir.

---

## 2. Final Backtest Teknik Gereksinimler — Bölüm Bölüm Uyum

### 2.1 Bölüm 1 — Genel Bakış ve Süreç

**Jüri ne istedi.** Kodun teknik gereksinimlere göre güncellenmesi, paketin organizasyona iletilmesi, teknik ekibin kodu önceden bildirilmeyen uygun herhangi bir 1 haftalık veri setiyle çalıştırması ve ilk hatasız çalıştırmanın ürettiği plan ile o çalıştırmanın süresinin değerlendirmeye girmesi.

**Biz ne yaptık.** Paketi üç ayrı belgeyle birlikte hazırladık: `README.md` (nasıl çalıştırılır ve neyin kanıtı nerede), `DEGISIKLIKLER.md` (Bölüm 8 için satır satır fark kaydı), `KONTROL_LISTESI.md` (Bölüm 11 için madde madde doğrulama). Paket kök dizininde `main.py`, `requirements.txt` ve `teknofest_manifest.json` bulunur. Çalıştırma, tek komutla ve hiçbir ön hazırlık gerektirmeden tamamlanır.

**Kanıt.** `final-teslim/` kök dizini; `python main.py` referans veri setinde çıkış kodu 0 ile yaklaşık 150 saniyede tamamlanır ve `out/Tasima-plani.xlsx` üretir.

**Risk / not.** Değerlendirme "ilk hatasız çalıştırma" üzerinden yapıldığı için ikinci bir şans yoktur. Bu nedenle Bölüm 10'daki iki güvenlik mekanizmasını (kademeli yayın ve sert süre sınırı) yalnız zaman aşımı için değil, her türlü beklenmedik hata için tasarladık; ayrıntısı Bölüm 2.10'da.

---

### 2.2 Bölüm 2 — Kapsam Netliği: Neden Sadece Optimizasyon

**Jüri ne istedi.** "Final değerlendirmesi sırasında talep tahmini modülünüz çalıştırılmayacaktır. Bunun yerine, optimizasyon modülünüze doğrudan bir talep tablosu beslenecektir." Ayrıca: "Kodunuzun final çalıştırmasında tahmin modülünüzü çağırmamanız gerekir — bu hem gereksiz çalışma süresi harcar hem de değerlendirmenin amacıyla çelişir."

**Biz ne yaptık.** İki bağımsız katmanla kapattık.

Birincisi yapısaldır: `main.py`'nin içe aktarma listesi yalnız `src.contract`, `src.data`, `src.evaluation`, `src.milkrun`, `src.optimize`, `src.pickup`, `src.repair` modüllerini içerir. `src.forecast`, `src.backtest` ve `src.frozen_backtest` modüllerine `main.py`'den başlayan içe aktarma grafiğinde **hiçbir yoldan ulaşılamaz**. Tahmin modülleri pakette bırakılmıştır ama yalnız `run.py` (önceki teslimin referans hattı) ve testler tarafından çağrılır.

İkincisi davranışsaldır: `main.py`, statik referans verilerini `load_all(ROOT / "datas", with_demand=False)` ile yükler. Bu bayrak, tahmin modülünün geçmiş veri kaynağı olan 66.024 satırlık `teknofest26_gelismis.xlsx` dosyasının hiç açılmamasını sağlar.

**Kanıt.** İçe aktarma grafiği taraması `KONTROL_LISTESI.md` 2. maddesinde kayıtlıdır. `with_demand` bayrağının etkisi ölçülmüştür: `with_demand=True` ile 8,20 saniye, `with_demand=False` ile 0,08 saniye — 8,12 saniyelik saf kazanç. `main.py` ayrıca `Talep-tahmini.xlsx` yazmaz; tek çıktı `out/Tasima-plani.xlsx`'tir.

**Risk / not.** `data.demand` alanı boş kalır. `main.py`'den ulaşılabilen kodda bu alanı okuyan tek yer `src/schemas.py` içindeki `validate_forecast_grid` fonksiyonudur ve o fonksiyon tahmin gridi doğrulamasına aittir; `main.py` yolundan hiç çağrılmaz. Alanı bir de `run.py` okur, ama o dosya değerlendirmede çalıştırılmaz. Davranışsal kanıt: `tests/test_contract.py` içindeki 64 entegrasyon testinin tamamı `with_demand=False` verisiyle geçer ve üretilen çıktı, `with_demand=True` ile üretilmiş önceki teslimle 0 farklı hücredir.

---

### 2.3 Bölüm 3 — Tek Giriş Noktası: main.py

**Jüri ne istedi.** Kök dizinde `main.py` bulunmalı; `python main.py` hiçbir ek argüman, ortam kurulum adımı veya kullanıcı etkileşimi olmadan uçtan uca çalışmalı: girdiyi okumalı, optimizasyonu çalıştırmalı, çıktıyı yazmalı. Çalışma etkileşimsiz bir ortamda gerçekleşecek; `input()` bekleyen, dosya seçim penceresi açan veya belirli bir IDE/not defteri ortamına özel kod bulunmamalı. `main.py` ince bir orkestratör olabilir.

**Biz ne yaptık.** `main.py` 299 satırlık, argümansız bir orkestratördür ve içinde **tek bir optimizasyon kararı yoktur**. Yaptığı şey şudur:

```
resolve_input_path        (Bölüm 4 girdi çözümü)
load_all(with_demand=False)
read_demand_table         (Bölüm 4 şema/tip normalizasyonu)
horizon_days              (Bölüm 7 ufuk türetimi)
build_plan                (Stage 0)
run_same_lane_stage       (Stage 1)
run_milk_run_stage        (Stage 2)
run_pickup_stage          (Stage 3)
write_final_plan          (Bölüm 5 atomik yazım)
```

Yol çözümü çalışma dizininden bağımsızdır: `ROOT = Path(__file__).resolve().parent` alınıp `sys.path`'in başına eklenir, `datas/`, `data/` ve `out/` bu köke göre çözülür. Konsol çıktısı UTF-8'e alınır (`_use_utf8_console`) — Türkçe log satırlarının cp1252 boru hatlarında süreç düşürmesini engellemek için.

**Kanıt.** Statik tarama sonucu: `input()`, `urllib`, `requests`, `socket`, `subprocess`, `pip install`, `tkinter`, `get_ipython`, `google.colab` ifadelerinin hiçbiri yoktur (`KONTROL_LISTESI.md` 8. madde). Farklı bir dizinden `python /mutlak/yol/main.py` çalıştırıldı: girdi, `datas/` ve `out/` yolları betiğe göre doğru çözüldü, çıkış kodu 0.

**Risk / not.** `main.py` her koşulda 0 döner. Tek bilinçli istisna: hiç yayın yapılamamışsa ve son yazma denemesi de başarısızsa hata yükseltilir. Gerekçe kodda açıkça yazılıdır — sessizce yanlış bir çıktı bırakmaktansa hatanın görünmesi yeğdir.

---

### 2.4 Bölüm 4 — Girdi (Input) Sözleşmesi

**Jüri ne istedi.** Dosyaya erişim için iki yöntemden en az biri desteklenmeli: `TEKNOFEST_INPUT_FILE` ortam değişkeni (mutlak yol) veya `data/one_week_backtest.xlsx` sabit göreli yolu. Format: Excel (.xlsx), tek sayfa (`Sheet1`). Şema 6 kolon, ad ve sıra birebir. Kapsadığı süre yaklaşık 1 haftalık bir dönem; kesin tarihler önceden bildirilmeyecek. Statik referans veriler değiştirilmeyecek.

**Biz ne yaptık.** Girdi sözleşmesinin tamamı `src/contract.py` modülünde toplanmıştır. **İki erişim yönteminin ikisi de desteklenir** ve sırayla denenir.

Statik referans veriler (`datas/` klasörü: araç filosu, hat/mesafe matrisi, elleçleme kapasiteleri, tır kapasiteleri, kiralık araç listesi) teslim paketindeki hâliyle ve **yalnız okuma amaçlı** kullanılır; boru hattı bu dosyaların hiçbirini yeniden yazmaz. `load_all` yüklemede sert doğrulama yapar — 306 hat, 18 transfer merkezi ve merkez kümelerinin birbiriyle tutarlılığı zorunludur. Değerlendirmede değişen tek girdi talep tablosudur.

#### 2.4.1 Girdi kolon şeması (tam tablo)

Aşağıdaki tablonun "Kolon adı" sütunu, `src/schemas.py` içindeki `FORECAST_COLS` sabitinin birebir içeriğidir; adlar kodda bu sırayla sabittir. Kalan sütunlar, her kolonun kabul ettiği girdi biçimlerini ve onu kanonik hâle getiren fonksiyonu gösterir.

| # | Kolon adı (birebir) | Açıklama | Beklenen tip | Kabul edilen girdi biçimleri | Kanonik hâle getiren fonksiyon |
|---|---|---|---|---|---|
| 1 | Talep ID | Benzersiz talep kimliği | metin | Herhangi bir metin; kanonik olmayan kimlikler eşlenir | `read_demand_table` kanonik kimlik ataması |
| 2 | Tarih | Talebin ait olduğu tarih | tarih (gg.aa.yyyy) | `pd.Timestamp`, `datetime`, `date`, Excel seri numarası, `%d.%m.%Y`, `%d/%m/%Y`, `%d-%m-%Y`, `%Y-%m-%d`, `%Y/%m/%d`, `%d.%m.%y` | `_to_date` |
| 3 | Talep Tamamlama Saati | Talebin tamamlanma zamanı | saat (ss:dd:ss) | `datetime.time`, `pd.Timestamp`, `datetime`, `Timedelta`, Excel gün kesri (0,375), saat sayısı, `%H:%M`, `%H:%M:%S`, `%H.%M`, `%H:%M:%S.%f` | `_to_hhmm` |
| 4 | Çıkış Transfer Merkezi | Talebin çıkış noktası | metin | Merkez adı; NFC normalizasyonu ve büyük/küçük harf toleransıyla eşlenir | `_resolve_center` |
| 5 | Varış Transfer Merkezi | Talebin varış noktası | metin | Merkez adı; aynı tolerans | `_resolve_center` |
| 6 | Tahmin Edilen Desi | Taşınacak hacim/ağırlık (desi) | sayı | Sayı veya sayıya çevrilebilir metin; yuvarlanır, negatifler sıfırlanır | `_to_desi` |

#### 2.4.2 Erişim yöntemi çözümü

| Öncelik | Yöntem | Davranış |
|---|---|---|
| 1 | `TEKNOFEST_INPUT_FILE` ortam değişkeni | Değer kırpılır, çevresindeki tek ve çift tırnaklar soyulur, göreli verilmişse pakete göre çözülür |
| 2 | `data/one_week_backtest.xlsx` | Ortam değişkeni tanımlı değilse veya gösterdiği dosya yoksa bu yola düşülür |

Aday listesi sırayla taranır ve ilk gerçekten var olan dosya kullanılır. İkisi de yoksa denenen tüm yolları listeleyen açık bir hata verilir.

Dosya `pd.read_excel(path)` ile açılır; sayfa adı kodda sabitlenmemiştir, çalışma kitabının **ilk sayfası** okunur. Bölüm 4 sayfayı `Sheet1` olarak tarif etse de, gelen dosyanın sayfası başka adlandırılmışsa koşu yine de düşmez.

#### 2.4.3 Kolon adı ve tip toleransı

Kolon eşlemesi iki kademelidir. Önce her girdi kolonunun karşılaştırma anahtarı üretilir: Unicode NFC normalizasyonu, ardışık boşlukların teke indirilmesi ve büyük/küçük harf duyarsızlaştırma. Böylece `"  talep id "`, `"TARİH"`, `"Talep  Tamamlama Saati"` gibi varyantlar eşleşir. Ad eşlemesi tamamlanamazsa ve tabloda tam 6 kolon varsa, Bölüm 4'ün "ad ve sıra birebir" garantisine dayanılarak **konum eşlemesine** düşülür ve bu durum açık bir not olarak konsola basılır. Kolon sayısı 6 değilse hata verilir.

Satır düzeyinde çözümlenemeyen hücreler sessizce silinmez; dört ayrı sayaç tutulur (geçersiz tarih, geçersiz saat, geçersiz desi, hat matrisinde olmayan çıkış/varış) ve her biri "N satır atlandı" biçiminde rapor edilir.

#### 2.4.4 Kanonik talep kimliği eşlemesi

Girdideki kimlikler `D00001`, `D00002` biçiminde olmayabilir. Bu durumda iç boru hattı ve hakem simülatörünün kimlik sözleşmesi bozulur. Çözümümüz çift yönlü eşlemedir: satırlar `(tarih, çıkış, varış, saat)` anahtarıyla kararlı biçimde sıralanır ve `D00001`den başlayarak kanonik kimlikler atanır; `id_map` sözlüğü kanonikten özgüne eşlemeyi tutar. Plan diske yazılmadan hemen önce `restore_demand_ids` kimlikleri girdideki özgün hâllerine geri çevirir; bölünmüş parça soneki (`-1`, `-2`) korunur.

Sıralama anahtarı, kendi tahmin modülümüzdeki kimlik atayıcının anahtarıyla **birebir aynıdır**. Bunun sonucu şudur: girdi bu projenin kendi tahmin çıktısıysa eşleme **özdeşliktir** ve boru hattı bit-birebir aynı planı üretir.

**Kanıt.** `src/contract.py` içinde `resolve_input_path`, `read_demand_table`, `_to_date`, `_to_hhmm`, `_to_desi`, `_resolve_columns`, `restore_demand_ids`. Testler: `tests/test_contract.py` içinde 64 test — saat/tarih/desi tip toleransları, numpy skalerleri (`np.int64(9)` → `09:00`, `np.float64(0.375)` → `09:00`), bool değerlerin saat/tarih olarak yorumlanmaması, girdi yolu çözümünün dört senaryosu, kolon adı toleransı, hat elemesi ve notları, boş tablo hatası, kanonik olmayan kimliklerin eşlenip geri döndürülmesi. Referans girdide ölçüldü: 4.046 satırın tamamı geçti, 0 satır atlandı, kanonik kimlikler özgün kimliklerle birebir aynı.

**Risk / not.** Şartname günlük iki sabit slot (09:00 ve 17:00) vaat etse de `read_demand_table` bu kısıtı **uygulamaz**; herhangi bir geçerli `HH:MM` slotunu kabul eder. Bu bilinçli bir Bölüm 7 kararıdır: bilinmeyen bir veri setinde farklı bir slot gelirse koşuyu düşürmek yerine planlamayı sürdürmeyi tercih ettik. Dürüst sınır: aday üretiminde günlük birleşik yükleme dalgası için 17:00 bir politika çıpası olarak kullanılır; slotlar tamamen farklıysa plan geçerli kalır ama optimal olmayabilir, çünkü her talebin gerçek hazır olma anı kendi slotundan hesaplanır.

---

### 2.5 Bölüm 5 — Çıktı (Output) Sözleşmesi

**Jüri ne istedi.** Dosya adı `Tasima-plani.xlsx`, manifestte belirtilen çıktı klasörü altında. Format Excel (.xlsx), tek sayfa. Şema 16 kolon, ad ve sıra birebir. "Kolon adı, sırası veya sayısı bu şemadan farklıysa çalıştırma şema hatası olarak değerlendirilir."

**Biz ne yaptık.** Çıktı sözleşmesi `src/schemas.py` içindeki `PLAN_COLS` sabitiyle tanımlanır ve `src/contract.py` içindeki `write_final_plan` tarafından uygulanır.

#### 2.5.1 Çıktı kolon şeması (tam tablo)

| # | Kolon adı (birebir, harf harf) | İçerik | Tip | Doğrulama kuralı |
|---|---|---|---|---|
| 1 | Araç ID | Fiziksel araç kimliği | metin | `^V\d{4,}$` biçimi zorunlu; zincirin tüm bacakları aynı kimliği paylaşır |
| 2 | Araç Tipi | Spot veya Kiralık | metin | Yalnız `Spot` veya `Kiralık`; bacak içinde tek değer |
| 3 | Araç türü | Tır, Kamyon, Hafif Kamyon, Kamyonet | metin | Referans veride tanımlı 4 türden biri; bacak içinde tek değer |
| 4 | Çıkış Transfer Merkezi | Bacağın kalkış merkezi | metin | 18 merkezden biri; çıkış-varış çifti hat matrisinde bulunmalı |
| 5 | Varış Transfer Merkezi | Bacağın varış merkezi | metin | 18 merkezden biri; hat matrisinde bulunmalı |
| 6 | Çıkış Tarihi | Kalkış tarihi | metin (gg.aa.yyyy) | Biçim doğrulaması ve gerçek takvim günü kontrolü |
| 7 | Çıkış Saati | Kalkış saati | metin (SS:DD) | Biçim doğrulaması ve gerçek saat kontrolü |
| 8 | Varış Tarihi | Varış tarihi | metin (gg.aa.yyyy) | Aynı kontroller |
| 9 | Varış Saati | Varış saati | metin (SS:DD) | Aynı kontroller |
| 10 | Talep ID | Taşınan talebin kimliği | metin | `^D\d{5,}(-\d+)*$`; boş kiralık bacağında boş olabilir |
| 11 | Taşınan Desi | Bu satırdaki desi | sayı | Sonlu ve negatif olmayan; boş kiralık satırında 0, diğerlerinde pozitif |
| 12 | Yolculuk süresi | Bacağın seyir süresi (dakika) | sayı | Hat matrisindeki değerin yukarı yuvarlanmışına birebir eşit olmalı |
| 13 | Varış elleçleme süresi | İndirme elleçlemesi (dakika) | sayı | Satır indiriliyorsa satır desisinin elleçlemesi, aksi hâlde 0 |
| 14 | Çıkış Elleçleme süresi | Yükleme elleçlemesi (dakika) | sayı | Satır yeni yükleniyorsa satır desisinin elleçlemesi, aksi hâlde 0 |
| 15 | SLA cezası | Bu satıra düşen ceza (TL) | sayı | Yalnız nihai varışta inen yükte pozitif olabilir |
| 16 | Toplam maliyet | Araç maliyeti payı artı SLA cezası (TL) | sayı | Fiziksel rota toplamı hakem hesabıyla uzlaşmalı |

#### 2.5.2 Yazım prosedürü — beş adım

`write_final_plan` yazımı beş adımda yapar ve her adım bir kapıdır:

1. **Yazımdan önce şema doğrulaması.** `validate_plan` kanonik kimliklerle çalıştırılır. En ufak şema hatasında `ValueError` yükselir ve **hedef dosyaya hiç dokunulmaz**.
2. **Kimlik geri çevirimi ve kolon sabitleme.** `restore_demand_ids` ile özgün kimlikler geri yazılır, ardından `.loc[:, PLAN_COLS]` ile 16 kolon şablon sırasına sabitlenir.
3. **Geçici dosyaya yazım.** Hedef dizinde gizli önekli bir geçici dosya açılır, `to_excel(index=False)` ile tek sayfa yazılır, `Taşınan Desi` kolonuna resmî şablonun `0.000` hücre biçimi uygulanır.
4. **Diskten geri okuyup yeniden doğrulama.** Geçici dosya `pd.read_excel` ile geri okunur; kolon listesi `PLAN_COLS`a birebir eşit değilse veya satır sayısı değiştiyse `ValueError`. Hücre değerleri de karşılaştırılır.
5. **Atomik taşıma.** `os.replace` ile geçici dosya yerine konur. Geçici dosya her koşulda temizlenir.

**Kanıt.** Teslim edilen `out/Tasima-plani.xlsx`: 5.523 satır x 16 kolon, tek sayfa. `tools/verify_output.py` planı diskten geri okuyup bağımsız olarak hakem simülatöründen geçirir: 0 ihlal, beyan edilen toplam ile hakem toplamı arasındaki fark 0,0000 TL. Testler: bozuk `Araç türü` verildiğinde hedef dosyanın hiç oluşmadığı, iç içe klasörün otomatik oluşturulduğu, başarılı yazımdan sonra dizinde geçici dosya artığı kalmadığı ayrı ayrı çivilenmiştir.

**Risk / not.** Adım 4'te **şema farkı ölümcül, değer farkı uyarıdır**. Bunun gerekçesi Bölüm 10'dur: Excel hücreleri yaklaşık 17 anlamlı basamak saklar ve `3347.8859374999997` değeri diskten `3347.8859375` olarak geri gelir. Bu veri bozulması değil, dosya biçiminin doğal hassasiyetidir; karşılaştırma bu yüzden bağıl toleransla yapılır. Toleransın ötesindeki farklar uyarı olarak basılır ama yayını engellemez — çıktısız kalmak bir uyarıdan çok daha ağır bir sonuçtur.

---

### 2.6 Bölüm 6 — teknofest_manifest.json

**Jüri ne istedi.** Kök dizine, belirtilen alanları içeren bir `teknofest_manifest.json` dosyası eklenmesi zorunlu.

**Biz ne yaptık.** Dosya kök dizinde bulunur ve tüm alanları doldurulmuştur.

| Alan | Değer | Doğrulama |
|---|---|---|
| `takim_id` | `BASVURU_NUMARANIZI_YAZIN` | **Yer tutucu — bkz. Bölüm 8** |
| `takim_adi` | `Büke` | Doğrulanmalı |
| `python_surumu` | `3.11` | Paket Python 3.11.2 ile test edildi |
| `kurulum_komutlari` | `["pip install -r requirements.txt"]` | Temiz sanal ortamda doğrulandı |
| `calistirma_komutu` | `python main.py` | Argümansız çalışıyor |
| `girdi_ortam_degiskeni` | `TEKNOFEST_INPUT_FILE` | Kodda birebir aynı sabit |
| `girdi_yedek_yolu` | `data/one_week_backtest.xlsx` | Kodda birebir aynı sabit |
| `cikti_klasoru` | `out/` | Kodda birebir aynı sabit |
| `beklenen_ciktilar` | `["Tasima-plani.xlsx"]` | Kodda birebir aynı sabit |
| `notlar` | Doldurulmuş | Kapsam, ufuk türetimi, süre ve yayın davranışı açıklanmış |

**Kanıt.** Manifest alanları ile koddaki sabitler karşılıklı kontrol edildi: `INPUT_ENV_VAR`, `INPUT_FALLBACK_PATH`, `OUTPUT_DIR`, `OUTPUT_FILENAME` sabitleri manifest değerleriyle birebir aynıdır.

**Risk / not.** `takim_id` alanı hâlâ yer tutucudur. Bu, teslim öncesi kalan **tek** işlemdir ve Bölüm 8'de uyarı olarak öne çıkarılmıştır.

---

### 2.7 Bölüm 7 — Genelleştirilebilirlik

**Jüri ne istedi.** "Belirli bir takvim tarihine/haftasına sabitlenmiş sabit değerler içermemelidir. Tarih aralığı, girdi dosyasındaki Tarih kolonundan dinamik olarak türetilmelidir." Ayrıca talep sayısı/hacmi geliştirme verisinden farklı olabilir; kodun makul ölçüde farklı büyüklüklerde de çalışması beklenir.

**Biz ne yaptık.** Üç ayrı düzeltme yaptık.

**Ufuk türetimi.** `horizon_days` fonksiyonu ufku yalnızca girdinin `Tarih` kolonundan türetir: benzersiz tarihler ayrıştırılır, en küçük ve en büyük arasındaki **tüm günler kesintisiz** döner. Arada talebi olmayan bir gün varsa bile o gün listede yer alır, çünkü boru hattı "bir sonraki dalga ertesi gündür" zincirini varsayar. Önceki teslimde bulunan `HORIZON_START` ve `HORIZON_END` sabitleri `main.py`'ye taşınmamıştır.

**Kimlik genişliği.** Kanonik kimlik `D00001` biçimindedir; 100.000. satırda biçim doğal olarak `D100000`a genişler. Bunun şema hatası sayılmaması için kimlik doğrulama düzenli ifadeleri `D\d{5}` → `D\d{5,}` olarak **genişletildi**. Bu yalnızca bir genişletmedir; 5 haneli her kimlik eskisi gibi geçerlidir.

**Sabit sonuç kapılarının kaldırılması.** Önceki teslimin `run.py` dosyasında aşamaların ölçülmüş sonuçlarına çivilenmiş sabitler vardır (`STAGE0_*` … `STAGE3_*`). Bunlar geliştirme veri setinin sonuçlarına sabitlenmiştir ve bilinmeyen bir veri setinde tanım gereği hata verirler. `main.py`'ye taşınmamışlardır. Aşamaların **kendi** kabul kuralı (0 ihlal ve en az 1,00 TL tasarruf) değişmeden korunmuştur.

**Kanıt.** Bölüm 7'nin ölçülmüş kanıtı Bölüm 7 başlığı altında ayrıca tablolanmıştır (bu belgenin 7. bölümü).

**Risk / not.** Ufuk aralığı 31 günü aşarsa yalnızca **uyarı** basılır, çalışma sürer. Gerekçe: aykırı tek bir tarih hücresi yüzünden koşuyu düşürmek, Bölüm 10 açısından çok daha ağır bir sonuçtur.

---

### 2.8 Bölüm 8 — İzin Verilen Kod Değişikliği Kapsamı

**Jüri ne istedi.** "Bu doküman kapsamında yapacağınız güncellemeler, kodunuzu bu teknik gereksinimlere uyumlu hale getirmek içindir — algoritmanızı iyileştirmek veya yeniden tasarlamak için değildir." Karşılaştırma, önceki teslim ile bu paket arasında yapılacak; değişikliklerin niteliğine göre aksiyon alınacak.

**Biz ne yaptık.** Bu bölümü üç başlıkta belgeliyoruz: değişmeyenler, eklenenler, değişenler.

#### 2.8.1 Değişmeyen modüller (tek karakter dahi değişmemiştir)

| Modül | Rolü |
|---|---|
| `src/optimize.py` | Stage 0 — kiralık doldurma, tır ziyaret bütçesi, hat-gün araç karması, boşaltma günleri |
| `src/candidates.py` | Araç karması tam sayımı, kesin maliyet modeli, erteleme kararı |
| `src/repair.py` | Stage 1 — aynı-hat onarımı |
| `src/milkrun.py` | Stage 2 — en fazla 4 duraklı milk-run zincirleri |
| `src/pickup.py` | Stage 3 — rota ortasında yük alma (Tier A) |
| `src/chain.py` | Fiziksel rota doğrulaması ve bacak başına yük akışı |
| `src/schedule.py` | Dakika çizelgeleyici, kimlik atama, elleçleme düzeltmesi |
| `src/ledger.py` | Elleçleme ve tır ziyaret defterleri |
| `src/simulator.py` | Hakem simülatörü |
| `src/evaluation.py` | Çizelgeleme, hakem çağrısı, kabul sınırı |
| `src/export.py` | Excel yazımı ve doğrulaması |
| `src/timeutil.py` | Yuvarlama ve zaman kuralları |
| `src/forecast.py`, `src/backtest.py`, `src/frozen_backtest.py` | Tahmin modülü — final koşusunda çağrılmaz |
| `tests/` (528 test) | Regresyon testleri |
| `run.py` | Önceki teslimin uçtan uca hattı — referans, değerlendirmede çalıştırılmaz |
| `datas/` | Statik referans verileri |

Bu listeyi ayrıca bağımsız olarak doğruladık. `src/` klasöründeki on altı değişmeyen modülün tamamı (`__init__`, `backtest`, `candidates`, `chain`, `evaluation`, `export`, `forecast`, `frozen_backtest`, `ledger`, `milkrun`, `optimize`, `pickup`, `repair`, `schedule`, `simulator`, `timeutil`), `run.py` dosyası ve önceki teslimden gelen 18 test dosyasının hepsi, geliştirme deposundaki karşılıklarıyla **bayt bayt aynıdır**; bayt karşılaştırması (`cmp`) hiçbir fark bildirmemiştir. Fark bildiren yalnız iki dosya vardır: `src/data.py` ve `src/schemas.py`. Pakette yeni olan iki kaynak dosya ise `main.py` ve `src/contract.py`'dir.

#### 2.8.2 Eklenen dosyalar

| Dosya | Rolü | İçinde optimizasyon kararı var mı |
|---|---|---|
| `main.py` | Bölüm 3 tek giriş noktası | Hayır — yalnız aşamaları sırayla çağırır ve kabul bayrağını okur |
| `src/contract.py` | Bölüm 4 ve Bölüm 5 sözleşmeleri | Hayır — yalnız girdi/çıktı normalizasyonu |
| `teknofest_manifest.json` | Bölüm 6 | Hayır |
| `requirements-dev.txt` | Yalnız test bağımlılığı | Hayır |
| `tests/test_contract.py` | 64 yeni entegrasyon testi | Hayır |
| `data/one_week_backtest.xlsx` | Bölüm 4 yedek girdi yolu | Hayır — veri dosyası |
| `tools/make_test_input.py` | Bölüm 7 sentetik girdi üretici | Hayır — değerlendirmede çalışmaz |
| `tools/verify_output.py` | Çıktı denetleyici | Hayır — değerlendirmede çalışmaz |
| `README.md`, `DEGISIKLIKLER.md`, `KONTROL_LISTESI.md` | Dokümantasyon | Hayır |

#### 2.8.3 Değişen iki modül — diff ve gerekçe

**Değişiklik 1: `src/data.py` — `load_all` için opsiyonel `with_demand` bayrağı**

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

*Gerekçe.* `teknofest26_gelismis.xlsx` (66.024 satır) yalnızca tahmin modülünün geçmiş veri kaynağıdır. Final koşusunda tahmin çalıştırılmadığı için (Bölüm 2) bu dosyanın ayrıştırılması saf kayıptır. Ölçülen maliyet 8,20 saniye; bayrakla 0,08 saniyeye iner. Bölüm 10 çalışma süresini değerlendirmeye kattığı için kaldırıldı.

*Etki analizi.* Varsayılan `with_demand=True` olduğundan `run.py` ve 528 mevcut testin tamamı değişmeden çalışır. `data.demand` alanı optimizasyon yolunda hiçbir yerde okunmaz.

**Değişiklik 2: `src/schemas.py` — talep kimliği düzenli ifade genişliği**

```diff
-DEMAND_ID_RE = re.compile(r"^D\d{5}$")
-SPLIT_ID_RE = re.compile(r"^D\d{5}(-\d+)*$")
+# Kanonik talep kimliği ``D00001``; 99.999'dan fazla talep satırı gelirse
+# genişlik doğal olarak artar (Bölüm 7 genelleştirilebilirlik).
+DEMAND_ID_RE = re.compile(r"^D\d{5,}$")
+SPLIT_ID_RE = re.compile(r"^D\d{5,}(-\d+)*$")
```

*Gerekçe.* Bölüm 7 — değerlendirme veri setinin hacmi bildirilmiyor. Kanonik kimlik biçimi 99.999 satırdan sonra doğal olarak 6 haneye çıkar; eski düzenli ifade bunu şema hatası sayıp çalıştırmayı düşürürdü.

*Etki analizi.* Kural yalnızca **genişletildi**; 5 haneli her kimlik eskisi gibi geçerlidir. Mevcut 4.046 satırlık veri setinde hiçbir davranış değişmez.

#### 2.8.4 "0 farklı hücre" kanıtı

Bölüm 8'in doğrulanabilir tek kanıtı, aynı girdiyle üretilen çıktının değişmemesidir.

| Karşılaştırma | Sonuç |
|---|---|
| `python main.py` (referans veri seti) çıktısı ile önceki teslimin `Tasima-plani.xlsx` dosyası | **0 farklı hücre** (5.523 satır x 16 kolon) |
| Toplam maliyet | 11.232.476,731944446 TL — birebir aynı |
| Hakem ihlali | 0 — birebir aynı |
| Aşama sonuçları | Stage 0 16.480.959,77 TL, Stage 1 14.680.184,85 TL, Stage 2 11.313.338,29 TL, Stage 3 11.232.476,73 TL — hepsi birebir aynı |
| Regresyon testleri | 592/592 geçti (528 mevcut değişmeden + 64 yeni) |

Bu tablo şunu söyler: girdi/çıktı katmanı tamamen yenilenmiş olmasına rağmen, algoritma aynı girdide **kuruşu kuruşuna ve hücresi hücresine** aynı planı üretmektedir. Algoritmaya dokunulmadığının en güçlü kanıtı budur.

**Risk / not.** `main.py`'nin `run.py`'den sekiz farkı vardır ve her birinin gerekçesi Bölüm 2-7'ye dayanır; tam liste `DEGISIKLIKLER.md` bölüm 2.1'dedir. Bunlardan üçü davranış eklemesidir (kademeli yayın, sert süre sınırı, aşama başına hata yalıtımı) ve hiçbiri bir optimizasyon kararı vermez; yalnızca "hangi planın yayınlanacağını" değil, "yayınlanmış bir planın her koşulda diskte bulunmasını" güvence altına alır.

---

### 2.9 Bölüm 9 — Kurulum ve Bağımlılıklar

**Jüri ne istedi.** Kök dizinde `requirements.txt` (veya `pyproject.toml`) bulunmalı. Değerlendirme ortamında internet erişimi olmayacak; çalışma anında otomatik `pip install` yapılmamalı. Docker isteğe bağlıdır; varsayılan/beklenen yol düz Python artı `requirements.txt`'tir.

**Biz ne yaptık.** `requirements.txt` yalnız iki çalışma zamanı bağımlılığı içerir:

```
pandas>=2.0,<3.0
openpyxl>=3.1,<4.0
```

Test bağımlılığı (`pytest`) ayrı bir dosyada (`requirements-dev.txt`) tutulur ve değerlendirme koşusu için gerekmez. `main.py` içinde `pip install`, ağ çağrısı, `subprocess` veya kullanıcı etkileşimi yoktur.

**Kanıt.** Temiz sanal ortam testi: `python -m venv` ile kurulan, yalnızca `requirements.txt` bağımlılıklarını içeren izole ortamda (pandas 2.3.3, numpy 2.4.6, openpyxl 3.1.5) `python main.py` uçtan uca çalıştırıldı — çıkış kodu 0, çıktı referans teslimle birebir aynı. Statik tarama: `urllib`, `requests`, `socket`, `subprocess`, `pip install` ifadelerinin hiçbiri yok.

**Risk / not.** Docker sunulmamıştır. Bölüm 9'un varsayılan/beklenen yolu olan düz Python yolu sunulmakta ve doğrulanmış olarak teslim edilmektedir. Bu bilinçli bir tercihtir: Docker'ı ana yöntem olarak sunmak, sade Python yolunun ayrıca doğrulanmasını gerektirirdi ve ek bir arıza yüzeyi açardı.

---

### 2.10 Bölüm 10 — Puanlama Mantığı

**Jüri ne istedi.** Kod `python main.py` ile çalıştırılır; ilk hatasız çalıştırmanın ürettiği çıktı ve süresi resmî sonuçtur. Zaman aşımı 100 dakika. Hatalı çalıştırma sayılan durumlar: çıkış kodu sıfırdan farklı, zaman aşımı, beklenen çıktı üretilmemesi, Bölüm 5 şemasına birebir uyulmaması.

**Biz ne yaptık.** Dört hata sınıfının her biri için ayrı bir mekanizma vardır.

**Zaman aşımına karşı: sert süre sınırı.** Arama aşamaları kendi içlerinde bölünemediği için sınır dışarıdan konur. Her aşama, kalan bütçeyle sınırlı bir daemon iş parçacığında çalıştırılır. Bütçe `TEKNOFEST_TIME_BUDGET_MIN` ortam değişkeniyle ayarlanır; varsayılan **100** (Bölüm 10 ile aynı) ve bunun **yüzde 90'ı aramaya**, kalan yüzde 10'u çıktının yazılmasına ayrılır. Sınır dolduğunda aşama terk edilir ve önceki plan korunur. Terk edilmiş bir iş parçacığı hâlâ CPU tüketiyor olabileceği için, süreç çıktı diske atomik olarak yazıldıktan sonra doğrudan sonlandırılır.

**Çıktı üretilmemesine karşı: kademeli yayın.** Geçerli ilk plan (Stage 0) elde edilir edilmez `out/Tasima-plani.xlsx` yazılır; kabul edilen her aşama dosyayı atomik olarak günceller. Yazım hedef dizindeki geçici dosyaya yapılır ve ancak tüm doğrulamalar geçtikten sonra `os.replace` ile yerine konur — yarım yazılmış dosya asla görünmez.

**Sıfırdan farklı çıkış koduna karşı: aşama başına hata yalıtımı.** Stage 1 için yedek değerlendirme yolu, Stage 2 ve Stage 3 için tam istisna yakalama, yayın için ayrı yakalama vardır. Hata hâlinde tam yığın izi basılır ve önceki plan korunur.

**Şema hatasına karşı: iki kat doğrulama.** Yazımdan önce `validate_plan`, yazımdan sonra diskten geri okuyup kolon listesi ve satır sayısı karşılaştırması.

**Kanıt — ölçülmüş süre sınırı davranışı.** `TEKNOFEST_TIME_BUDGET_MIN=0.6` (36 saniyelik bütçe) ile:

```
[Stage 1 aynı-hat onarım] kabul edildi; tasarruf 1.800.774,93 TL (13,4 sn)
    -> çıktı güncellendi (Stage 1)
[Stage 2 milk-run] süre sınırında terk edildi (11,4 sn); önceki plan korunuyor
[Stage 3 rota-ortası yük alma] atlandı: arama bütçesi tükendi
Toplam süre: 32,4 sn -> çıkış kodu 0, geçerli plan diskte (0 ihlal)
```

**Kanıt — kademeli yayın.** %250 hacimli sentetik veri setinde süreç Stage 2'nin ortasında zorla sonlandırıldığında diskte **3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru** bir `Tasima-plani.xlsx` bulundu.

**Kanıt — süre.** Referans veri setinde uçtan uca yaklaşık 150 saniye; farklı hafta senaryolarında 143 ve 171 saniye. Sınırın çok altında.

**Risk / not.** Süreç açılışı, girdi okuma ve Stage 0 çağrısı süre sınırı altında **değildir**. Bunu ölçtük: içe aktarma 1,14 saniye, statik veri yükleme 0,08 saniye, girdi okuma 0,57 saniye, Stage 0 temel planı 0,38 saniye — toplam yaklaşık 2,2 saniye, yani yaklaşık 150 saniyelik koşunun yüzde 1,5'i. Sınır, zamanın gerçekte harcandığı yerde (Stage 1, 2, 3 kombinatoryal aramaları) uygulanmaktadır.

---

### 2.11 Bölüm 11 — Teslim Öncesi Kontrol Listesi

Bu bölümün tamamı, bu belgenin **3. bölümünde** madde madde ele alınmıştır.

---

## 3. Bölüm 11 Kontrol Listesi — Madde Madde Doğrulama

Aşağıdaki tablo, Teknik Gereksinimler dokümanının 11. bölümündeki on maddenin her biri için "nasıl doğrulandı" ve "sonuç" üçlüsünü verir.

### 3.1 Madde 1 — main.py kök dizinde ve argümansız çalışıyor

**Nasıl doğrulandı.** `python main.py` referans veri setiyle çalıştırıldı; ayrıca temiz sanal ortamda ve farklı bir çalışma dizininden mutlak yolla çalıştırıldı.
**Sonuç.** Çıkış kodu 0, yaklaşık 150 saniye. Farklı dizinden çağrıldığında girdi, `datas/` ve `out/` yolları betiğe göre doğru çözüldü.

### 3.2 Madde 2 — main.py sadece optimizasyon adımını çalıştırıyor

**Nasıl doğrulandı.** `main.py`'den başlayan içe aktarma grafiği tarandı. Ayrıca davranışsal kontrol: `load_all(..., with_demand=False)` çağrısı, tahminin geçmiş veri kaynağının hiç okunmadığını garanti eder.
**Sonuç.** `src.forecast`, `src.backtest`, `src.frozen_backtest` modüllerine hiçbir yoldan ulaşılamıyor. `Talep-tahmini.xlsx` yazılmıyor; tek çıktı `Tasima-plani.xlsx`.

### 3.3 Madde 3 — Girdi, Bölüm 4 format/şema/erişim yöntemleriyle okunabiliyor

**Nasıl doğrulandı.** İki erişim yöntemi de testlerle kapsandı (ortam değişkeni öncelikli, dosya yoksa yedek yola düşme dahil). Kolon adı toleransı, altı tarih biçimi, sekiz saat biçimi ve numpy skalerleri parametrik testlerle çivilendi.
**Sonuç.** Her iki yöntem de destekleniyor. Referans girdide 4.046 satırın tamamı çözümlendi, 0 satır atlandı.

### 3.4 Madde 4 — Çıktı, Bölüm 5 format/şema/konumla yazılıyor

**Nasıl doğrulandı.** Yazımdan önce `validate_plan`, yazımdan sonra diskten geri okuma ve kolon listesi/satır sayısı karşılaştırması. Ayrıca `tools/verify_output.py` ile bağımsız hakem denetimi.
**Sonuç.** `out/Tasima-plani.xlsx`, tek sayfa, 16 kolon ad ve sıra birebir, 5.523 satır. Hakem denetimi 0 ihlal, beyan/hakem farkı 0,0000 TL.

### 3.5 Madde 5 — Kod sabit tarih/hacim varsayımı içermiyor

**Nasıl doğrulandı.** Ufuk yalnız `Tarih` kolonundan türetiliyor; aynı hafta 2019, 2026 ve 2031 yıllarına taşınıp sonucun kaymadığı testle çivilendi. İki uçtan uca sentetik senaryo çalıştırıldı.
**Sonuç.** 25-28.05.2025 (farklı yıl, 4 günlük ufuk, %35 hacim, `REQ_` kimlikler, `HH:MM`) ve 02-08.09.2026 (%125 hacim, `HH:MM:SS`) senaryolarının ikisinde de çıkış kodu 0 ve 0 hakem ihlali.

### 3.6 Madde 6 — requirements.txt güncel ve eksiksiz

**Nasıl doğrulandı.** Temiz sanal ortamda yalnız `requirements.txt` bağımlılıklarıyla kurulum ve uçtan uca koşu.
**Sonuç.** `pandas>=2.0,<3.0` ve `openpyxl>=3.1,<4.0` — başka çalışma zamanı bağımlılığı yok. Çıkış kodu 0.

### 3.7 Madde 7 — teknofest_manifest.json dolduruldu ve kök dizine eklendi

**Nasıl doğrulandı.** Manifest alanları koddaki sabitlerle karşılıklı kontrol edildi.
**Sonuç.** Dosya kök dizinde ve tüm alanları dolu. **Tek istisna: `takim_id` alanı yer tutucu durumda** — bkz. Bölüm 8.

### 3.8 Madde 8 — Çalışma anında internet erişimi veya kullanıcı etkileşimi gerektiren kod yok

**Nasıl doğrulandı.** Statik tarama: `input()`, `urllib`, `requests`, `socket`, `subprocess`, `pip install`, `tkinter`, `get_ipython`, `google.colab`.
**Sonuç.** Hiçbiri bulunmadı.

### 3.9 Madde 9 — Değişiklikler sadece entegrasyon amaçlı

**Nasıl doğrulandı.** Modül modül fark analizi; algoritma modüllerinin bayt karşılaştırması; aynı girdiyle üretilen çıktının önceki teslimle hücre karşılaştırması.
**Sonuç.** Değişen dosya sayısı **2** (`src/data.py`, `src/schemas.py`), ikisi de yalnızca davranış genişleten. Çıktı farkı **0 hücre**. Ayrıntı: `DEGISIKLIKLER.md`.

### 3.10 Madde 10 — Temiz sanal ortamda baştan sona test edildi

**Nasıl doğrulandı.** `python -m venv` ile izole ortam kuruldu; pandas 2.3.3, numpy 2.4.6, openpyxl 3.1.5.
**Sonuç.** `python main.py` uçtan uca çalıştı, çıkış kodu 0, çıktı referans teslimle birebir aynı.

### 3.11 Kontrol listesi özeti

| # | Madde | Durum |
|---|---|---|
| 1 | main.py kök dizinde, argümansız | Tamam |
| 2 | Yalnız optimizasyon, tahmin çağrılmıyor | Tamam |
| 3 | Girdi Bölüm 4 uyumlu | Tamam (iki yöntem de) |
| 4 | Çıktı Bölüm 5 uyumlu | Tamam |
| 5 | Sabit tarih/hacim varsayımı yok | Tamam (iki senaryo ölçüldü) |
| 6 | requirements.txt eksiksiz | Tamam |
| 7 | teknofest_manifest.json dolduruldu | Kısmi — `takim_id` yer tutucu |
| 8 | İnternet/etkileşim yok | Tamam |
| 9 | Değişiklikler entegrasyon amaçlı | Tamam (0 farklı hücre) |
| 10 | Temiz sanal ortamda test edildi | Tamam |

---

## 4. Gelişmiş Çözüm Aşaması Şartnamesi Uyumu

Final Backtest, Gelişmiş Çözüm aşamasının problem tanımını değiştirmez; yalnızca çalıştırma ve teslim biçimini standartlaştırır. Bu nedenle şartnamenin her kuralı final koşusunda da geçerlidir. Aşağıda şartnamenin altı ana bölümü ve iki ek kısıtı, uygulamalarıyla eşleştirilmiştir.

### 4.1 Bölüm 1 — Talep Veri Seti

**Jüri ne istedi.** Talep verisi "Talep Tamamlanma Saati" bilgisi içerir; her gün için yalnız iki sabit saat vardır (09:00 ve 17:00). Talep tamamlanma saati, taleplerin transfer merkezlerinde elleçlemeye hazır bulunduğu andır ve aynı zamanda SLA süresinin başlangıç saatidir. Her talep için `D00001` biçiminde talep kimliği oluşturulmalıdır.

**Biz ne yaptık.** Girdi tablosundaki `Talep Tamamlama Saati` değeri, her talebin hazır olma anı olarak alınır: `hazır = Tarih + saat`. SLA vadesi bu andan itibaren hesaplanır. Talep kimlikleri kanonik `D00001` biçimindedir ve çıktıda girdideki özgün kimlikler geri yazılır.

**Kanıt.** Referans girdide 4.046 satır, toplam 4.977.975 desi; her satır bir talep kimliği taşır. Hakem, hiçbir plan satırının talep tablosunda karşılığı olmadığını tespit ederse ihlal yazar; teslim edilen planda böyle bir ihlal yoktur.

**Risk / not.** Girdideki bir talep kimliği tekrar ediyorsa, kanonik kimlikler benzersiz üretildiği için boru hattı bozulmaz; ancak çıktıda o iki talep aynı özgün kimlikle görünür, çünkü sözleşme gereği girdideki kimlikleri geri yazıyoruz.

### 4.2 Bölüm 2 — Araç Maliyetleri

**Jüri ne istedi.** Toplam Araç Maliyeti = (Saatlik Kiralama Maliyeti x Kullanım Süresi) + (Kat Edilen Mesafe x Kilometre Başı Maliyet).

**Biz ne yaptık.** Maliyet, fiziksel rota başına **tek sürekli kullanım penceresi** üzerinden hesaplanır: ilk yükleme başlangıcından son indirme bitişine kadar geçen tüm süre. Bu pencere çıkış elleçlemesini, tüm seyirleri, ara durak elleçlemelerini ve varsa beklemeleri kapsar. Mesafe, hat matrisinden okunan gerçek kilometrelerin toplamıdır; kuş uçuşu hesap yapılmaz.

Referans verideki tarifeler:

| Araç türü | Kapasite (desi) | Spot saatlik (TL) | Spot km başı (TL) | Kiralık saatlik (TL) | Kiralık km başı (TL) |
|---|---:|---:|---:|---:|---:|
| Tır | 22.400 | 487,50 | 25 | 291,67 | 13 |
| Kamyon | 12.000 | 318,25 | 21 | 208,33 | 10 |
| Hafif Kamyon | 7.200 | 364,58 | 20 | 208,33 | 10 |
| Kamyonet | 5.600 | 197,92 | 18 | 156,25 | 6 |

**Kanıt.** `src/simulator.py`, planlayıcıdan bağımsız olarak bu formülü uygular ve her plan satırının beyan ettiği maliyet payını denetler. Fiziksel rota düzeyinde beyan edilen maliyetlerin toplamı hakem hesabıyla en fazla 0,01 TL sapabilir; ölçülen sapma 0,0000 TL'dir. Jürinin işlenmiş örneği birebir yeniden üretilir: spot Tır, 10.000 desi, İstanbul-Yalova hattı — 100 dakika yükleme, 56 dakika yol, 100 dakika indirme, toplam 256 dakika; 487,50 x 256/60 + 25 x 60 = 3.580 TL.

**Risk / not.** Kullanım süresi saate yuvarlanmaz; kesirli saat olarak hesaplanır. Bu, jürinin verdiği "500 dakika" ve "560 dakika" örnekleriyle tutarlıdır.

### 4.3 Bölüm 3 — Kiralık Araç Listesi

**Jüri ne istedi.** "Kiralık araçlarla uğrama yapamazsınız. Kiralık araçlar sadece size verilen iki transfer merkezi arasında çalışırlar ve bu rotadan asla sapamazlar. Size verilen kiralık araçlar haricinde kiralık araç kullanamazsınız. Talep yetersiz olsa bile kiralık araçları çıkarmak zorundasınızdır."

**Biz ne yaptık.** Kiralık filo referans veriden okunur: **12 rota, günde 14 araç** (10 Tır + 4 Kamyon).

| Rota | Adet | Araç türü |
|---|---:|---|
| İstanbul - Yalova | 2 | Tır |
| İstanbul - Eskişehir | 2 | Tır |
| Kocaeli - Yalova | 1 | Tır |
| İstanbul - Manisa | 1 | Tır |
| İstanbul - Balıkesir | 1 | Tır |
| İstanbul - Tekirdağ | 1 | Tır |
| Kocaeli - İstanbul | 1 | Tır |
| Kocaeli - Tekirdağ | 1 | Tır |
| Yalova - Eskişehir | 1 | Kamyon |
| Kocaeli - Balıkesir | 1 | Kamyon |
| Kocaeli - Eskişehir | 1 | Kamyon |
| Yalova - Tekirdağ | 1 | Kamyon |

Zorunlu çıkış kuralı, kod düzeyinde koşulsuzdur: havuz boş olsa bile her rota için tanımlı sayıda bacak üretilir. Kiralık bacaklar hiçbir aşamada silinemez, zincire alınamaz ve rotalarından saptırılamaz.

**Kanıt.** Ölçüldü: 9 günün her birinde tam 14 kiralık bacak, toplam **126 kiralık bacak**; bunların 35'i boştur (28'i iki boşaltma gününde, 7'si ufuk günlerinde) ve boş bacakların maliyeti 104.545,11 TL'dir. Kiralık filo bir yük değil bir kaldıraçtır: 126 bacak toplam 459.936,67 TL'ye — nihai planın araç maliyetinin %5,34'ü, Stage 0 temel planının araç maliyetinin ise %2,97'si — 867.524 desi (toplam hacmin %17,4'ü) taşır. Hakem, her denetim günü için her kiralık rotanın bacak sayısını tanımlı adetle karşılaştırır; teslim edilen planda kiralık ihlali yoktur.

**Risk / not.** Kiralık araç kimliklerinin günler arası kalıcılığı bir yorum konusudur. Biz **gün bazlı benzersiz kimlik** kullanıyoruz; bu daha muhafazakâr yorumdur ve hakem tarafında "kiralık araç aynı gün birden fazla bacak" ile "bir kimlik birden fazla günde" kontrolleriyle desteklenir.

### 4.4 Bölüm 4 — Elleçleme Kapasitesi

**Jüri ne istedi.** "Bu kapasiteler günlüktür, yani 24 saat içinde yapılabilecek maksimum elleçleme işlemini ifade eder. Elleçleme kapasitesini kesinlikle geçemezsiniz. Kapasiteyi aşma durumunda yükleri bekletip ertesi gün göndermeniz beklenmektedir." Konsolidasyonda elleçleme iki kez yapılır.

**Biz ne yaptık.** İki katmanlı bir yapı kullanıyoruz.

**Uygulama katmanı:** `src/schedule.py` içindeki `_fix_handling`, aşan `(merkez, gün)` çiftlerini iteratif olarak onarır. Her turda akışlar ve defter sıfırdan kurulur, aşımı gerçekten besleyen kaydırılabilir bacaklar arasından **en küçük desili olan** ertesi günün 00:00'ına taşınır. Tur başına en fazla bir bacak taşınır ve en fazla 500 tur dönülür. Kaydırma kullanım süresini değiştirmez, yalnız takvimdeki yeri kayar — yani araç maliyeti sabit kalır, ödenen bedel SLA cezası olur. Bu, şartnamenin "kapasiteyi aşma durumunda yükleri bekletip ertesi gün göndermeniz beklenmektedir" cümlesinin doğrudan karşılığıdır.

Kaydırılabilirlik dört koşula bağlıdır: bacak bir zincirin parçası olmamalı (zincir sürekliliği kırılır), boş olmamalı, `Spot` olmalı (kiralık her gün çıkmak zorundadır), ve `Tır` olmamalı (kaydırma tır ziyaret gününü değiştirip tır kapasitesini bozar).

**Denetim katmanı:** `src/ledger.py` içindeki `HandlingLedger`, elleçleme desisini gece yarılarında süreye orantılı bölerek günlük kovalara yazar. Hakem bu defteri bağımsız olarak yeniden kurar.

**Kanıt.** Stage 0 planında ölçülen etki: **11 kaydırma**, hepsi Denizli merkezinde (kapasite 36.868,61 desi — 18 merkezin en küçüğü). Araç maliyeti hiç değişmedi (15.460.592,57 TL), SLA cezası 1.017.967,60 TL'den 1.020.367,20 TL'ye çıktı (**+2.399,60 TL**). Düzeltme kapatıldığında hakem 1 elleçleme ihlali yazar (Denizli 02.07.2026: 38.449 > 36.869); açıkken sonuç **0** elleçleme ihlalidir. Teslim edilen planda en yüksek doluluk oranları: Karaman 02.07 %95,9 (42.022 / 43.830 desi), İstanbul 01.07 %92,7 (365.807 / 394.786 desi), Zonguldak 02.07 %88,2, Yalova 01.07 %85,4. Hiçbiri aşılmamıştır.

**Risk / not.** Referans hafta için ağın elleçleme kapasitesi neredeyse tamamen doludur: İstanbul, 01.07.2026 — o günün yükleme artı indirme talebi 395.825 desi, günlük kapasite 394.786 desi. Hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme kısıtı **hiçbir plan tarafından** sağlanamaz; bu bir kod kusuru değil, veri setinin fizikî olarak çözümsüz olmasıdır. %250 hacimli sentetik veri setinde ölçülen davranış tam olarak budur: Stage 0 temel planı 69 elleçleme ihlaliyle üretildi (örneğin Erzincan 80.160 desi talep, kapasite 58.673), Stage 1 adayı bu nedenle doğru biçimde reddedildi ve temel plan korundu. Kod çökmedi ve Bölüm 5 şemasına birebir uyan bir plan yazdı.

### 4.5 Bölüm 5 — Transfer Merkezleri Matrisi

**Jüri ne istedi.** Excel'de merkezler arası mesafeler, araç tipine göre seyir süreleri ve kilometre bilgileri vardır. "Bu aşamada kuş uçuşu ile kilometre hesabı yapmanızı beklemiyoruz. Kilometreyi direkt bu exceldeki bilgilere uygun kullanacaksınız." Ayrıca hatlar arası SLA süreleri gün bazında verilmiştir.

**Biz ne yaptık.** Hat matrisi tipli nesnelere yüklenir ve **tam 306 hat** ile **tam 18 transfer merkezi** olduğu yüklemede sert biçimde doğrulanır; sapma olursa süreç hata ile durur. Her hat için kilometre, dört araç türü için seyir saati ve SLA gün sayısı okunur. Kilometre ve seyir süresi hesaplarında başka hiçbir kaynak kullanılmaz.

SLA vadesi: `vade = hazır olma anı + 24 x SLA_gün` saat. Veri setinde 306 hattın 204'ü 1 günlük, 102'si 2 günlük SLA'ya sahiptir.

**Kanıt.** `src/data.py` yükleme doğrulaması (306 hat, 18 merkez, hat/elleçleme/tır kapasitesi merkez kümelerinin eşitliği). Hakem her plan satırında `Yolculuk süresi` hücresinin hat matrisindeki değerin yukarı yuvarlanmışına **birebir eşit** olmasını arar; teslim edilen planda uyumsuzluk yoktur.

**Risk / not.** Bir hat matriste yoksa hakem "matriste olmayan hat" ihlali yazar ve o bacak için maliyet karşılaştırması yapmaz — kanıt yoksa uydurma bir beklenen değer üretilmez. Bu, girdi verisinde beklenmedik bir merkez adı gelirse hatanın gizlenmemesini sağlar.

### 4.6 Bölüm 6 — Tır Kapasiteleri

**Jüri ne istedi.** "Belirtilen kapasite giden tır ve gelen tır ayrımı yapılmaksızın işlem görebilecek maksimum tır sayısını ifade eder. Tır kapasitesini aşamazsınız. Günlük olarak ifade edilmiştir."

**Biz ne yaptık.** Jürinin Q&A'da güncelleyeceğini bildirdiği **v2 dosyası** kullanılır. Referans veride toplam günlük tır ziyaret kapasitesi 69'dur:

| Merkez | Kapasite | Merkez | Kapasite |
|---|---:|---|---:|
| Kocaeli | 12 | Yalova | 4 |
| Mersin | 11 | Tekirdağ | 2 |
| Eskişehir | 10 | Balıkesir | 1 |
| İstanbul | 10 | Bilecik | 0 |
| Erzincan | 5 | Denizli | 0 |
| Mardin | 5 | Isparta | 0 |
| Şanlıurfa | 5 | Karaman | 0 |
| Manisa | 4 | Kütahya | 0 |
| | | Sivas | 0 |
| | | Zonguldak | 0 |

Kritik tasarım kararı: **zorunlu kiralık tırlar, planlama başlamadan önce bütçeden düşülür.** Her gün, her kiralık rota için kalkış ve varış anları tam yük varsayımıyla hesaplanır ve araç Tır ise hem çıkış merkezinin hem varış merkezinin o günkü kotasından bir ziyaret düşülür.

**Kanıt.** Karşı-olgu ölçümü: bu ön rezervasyon kaldırılırsa plan **12 tır kapasitesi ihlali** üretir (Balıkesir 2 > 1, Tekirdağ 4 > 2, Manisa 5 > 4 dahil). Rezervasyonla ihlal sayısı 0'dır ve hakem bunu bağımsız olarak doğrular. Teslim edilen planda en yoğun nokta İstanbul 01.07 ve 02.07'de 9/10 ziyarettir; kapasitesi 0 olan yedi merkeze hiç tır ziyareti yazılmamıştır.

**Risk / not.** Balıkesir ve Tekirdağ'ın v2 kapasiteleri (1 ve 2) zorunlu kiralık tır varışlarını **tam olarak** karşılar; bu iki merkezde spot tır için hiç boşluk kalmaz. Bu bir kısıt değil, veri setinin yapısıdır ve ön rezervasyon sayesinde ihlale dönüşmez.

### 4.7 EK KISIT 1 — Elleçleme Süresi

**Jüri ne istedi.** Elleçleme süresi desi başına 0,01 dakikadır. "Bu yarışma kapsamında bir araç içerisinde taşınan tüm gönderiler için elleçleme işleminin aynı anda başladığı ve aynı anda tamamlandığı varsayılır. Yarışmacılar aynı araç içerisindeki desiyi bölerek bir kısmını daha erken elleçlenmiş kabul edemezler. Araçtan inecek tüm gönderiler, elleçleme tamamlandıktan sonra aynı varış zamanına sahip olacaktır." SLA için araç varış anı değil, elleçlemenin tamamlanma anı esas alınır.

**Biz ne yaptık.** Fiziksel zaman çizelgesi bacak düzeyinde **tek toplu işlem** kullanır: yükleme süresi, o bacakta yeni yüklenen toplam desinin elleçlemesidir; indirme süresi, o durakta inen toplam desinin elleçlemesidir. Aynı durakta inen tüm gönderiler **tek bir indirme bitiş anını** paylaşır ve SLA'ları bu tek ana göre hesaplanır. Yükleme ve indirme ayrı ayrı hesaplanır ve her biri bir üst tam dakikaya yuvarlanır.

Yuvarlama tek bir kaynaktan yapılır. Kayan nokta artefaktına karşı önce altı haneye yuvarlama uygulanır, sonra yukarı yuvarlanır — böylece `8.05 * 60` çarpımının verdiği 483,00000000000006 gibi bir değer yanlışlıkla 484'e taşmaz (Mersin↔Denizli Kamyonet bacakları; veri setinde bu durumdaki hat-araç çifti 2 tanedir).

**Kanıt.** Jürinin örnekleri birebir yeniden üretilir: 5.000 desi → 50 dakika, 10.000 desi → 100 dakika, tam yüklü Tır (22.400 desi) → 224 dakika. İstanbul-Yalova Tır seyri 0,92 saat = 55,2 dakika → **56 dakika**. Hakem her plan satırında beyan edilen elleçleme sürelerini bağımsız olarak yeniden hesaplar.

**Risk / not.** Beyan kolonlarındaki değerlerle fiziksel zaman çizelgesi arasında görünürde bir fark vardır ve bu kasıtlıdır. Çizelge, bacağın **toplam** desisi üzerinden tek bir işlem kullanır; beyan kolonları ise tablo talep bazlı olduğu için **satır** desisinin elleçlemesini yazar. Örnek: 1 ve 6 desilik iki kalem taşıyan bir bacakta gerçek elleçleme 1 dakika, beyan edilen satırlar 1 + 1 = 2 dakikadır. Bu bir tutarsızlık değildir çünkü hakem tam olarak satır bazlı değeri bekler; beyan ile denetim aynı tanımı kullanır.

### 4.8 EK KISIT 2 — SLA Cezası

**Jüri ne istedi.** SLA sürecinin başlangıcı, ilgili talebin talep tamamlanma zamanıdır. SLA Cezası = Geciken Desi x Gecikme Süresi (Saat) x 0,4 TL. "Gecikme süresi saat bazında hesaplanacak olup, tam saat olmayan tüm gecikmeler bir üst tam saate yuvarlanacaktır." Ayrıca: "Eğer düşük talep sebebiyle bazı gönderileri bekletmek maliyet açısından daha faydalıysa gönderileri bekletebilirsiniz."

**Biz ne yaptık.** SLA saati talebin hazır olma anında başlar ve **orijinal varış merkezindeki indirme elleçlemesinin bitişinde** durur. Ara merkezlerdeki indirmeler saati durdurmaz. Gecikme dakika cinsinden ölçülüp bir üst tam saate yuvarlanır; ceza, geciken desi ile bu saat sayısının ve 0,40 TL'nin çarpımıdır.

Bekletme hakkını bilinçli olarak kullanıyoruz. Erteleme mekanizması, ertelenen yükün ertesi günkü taşıma bedelini ve doğacak SLA cezasını amaç fonksiyonuna dahil eder; yalnızca toplam maliyeti düşürdüğünde uygulanır.

**Kanıt.** Şartname örneği birebir yeniden üretilir: 6.000 desi, vadesini 1 saat aşan teslim → 6.000 x 1 x 0,40 = 2.400 TL. Jürinin "09:01'de tamamlanırsa 1 saat" netleştirmesi: 1 dakikalık gecikme 1 saat sayılır.

Erteleme mekanizmasının değeri ölçülmüştür: mekanizma tamamen kapatıldığında Stage 0 toplamı 16.480.959,77 TL yerine 24.954.608,68 TL olur. Yani 1.020.367,20 TL SLA cezası ödeyerek 9.494.016,11 TL araç maliyeti tasarruf edilir; net kazanç 8.473.648,91 TL. Her iki koşuda da ihlal 0'dır.

**Risk / not.** SLA cezası aşamalar boyunca **bilerek artmaktadır**: 1.020.367,20 TL'den 2.615.532,00 TL'ye. Buna karşılık araç maliyeti 15.460.592,57 TL'den 8.616.944,73 TL'ye düşer. Jüri gizli bir SLA tavanı koymadığı ve gecikmeyi 0,40 TL/desi/saat ile fiyatladığı için doğru hedef saf toplam maliyettir. SLA gecikmesi hakem tarafında bir **ihlal değil**, fiyatlanmış bir maliyet kalemidir.

### 4.9 Çözüm Bölümü — Çıktı Formatları ve Takip Edilebilirlik

**Jüri ne istedi.** "Bu aşamada konsolidasyon senaryosu da olduğu için araçlarınızın takip edilebilir olması gerekmektedir. Bu nedenle araç ID eklemenizi bekliyoruz. Araç ID formatı `V0001` gibi olmalıdır." Ayrıca elleçleme süresi varış ve çıkış olarak ayrılmıştır. "Beklediğimiz format aşağıdaki gibidir ve bu formata uymayan takımların sonuçları kesinlikle değerlendirmeye alınmayacaktır."

**Biz ne yaptık.** Araç kimliği **fiziksel rota başına** atanır, bacak başına değil. Bir milk-run zincirinin dört bacağı tek bir `V####` kimliğini paylaşır; böylece araç plan dosyasında baştan sona izlenebilir. Kimlik atama sırası tamamen belirlenimcidir: rotalar kiralık öncelikli, sonra kalkış zamanı, çıkış merkezi ve varış merkezine göre sıralanır.

Talep kimliği tarafında bölünme sonekleri fiziksel parça başına verilir. Bir talep tek fiziksel parçadan oluşuyorsa temel kimliğini korur; birden fazlaysa ilk fiziksel görünme sırasına göre `-1`, `-2` sonekleri alır. Aktarmada kimlik değişmez.

**Kanıt.** Teslim edilen planda 5.523 satır, 665 fiziksel araç, 1.064 segment. Zincir topolojisi doğrulaması yayınlanan Excel üzerinden yapıldı: 665 aracın hepsinde 0 topoloji hatası. Bacak sayısına göre araç dağılımı: 438 tek bacaklı, 127 iki duraklı, 28 üç duraklı, 72 dört duraklı = 665. Çıktıda 525 tireli (bölünmüş) satır vardır ve sonekler 1'den 5'e kadardır.

**Risk / not.** Bölünme sonekleri **yalnızca tahmin çıkış merkezinde** üretilir; hub aktarmalarında aynı kimlik devam eder. Bu, hakemin "rota tahmin çıkışından başlamıyor" kontrolünün doğru çalışması için zorunludur ve kod düzeyinde bir sözleşme olarak korunmuştur.

---

## 5. Jüri Soru-Cevap Uyum Matrisi

Jüri Q&A dokümanındaki 11 takımın soruları ve resmî cevapları ile şartname sonundaki soru-cevap eki ve ek netleştirme mesajı satır satır kodla eşleştirilmiştir. Aşağıdaki tabloda **kural**, **bizim uygulamamız** ve **kod konumu** üçlüsü verilmiştir.

### 5.1 Bağlayıcı cevaplar ve karşılıkları

| # | Kural (jüri cevabı) | Bizim uygulamamız | Kod konumu |
|---|---|---|---|
| 1 | Tır kapasiteleri güncellenecektir; yeni kapasiteler paylaşılacak (OptiVision S1, ROTAI S3, Budapeşte S2, OpAI S2) | Güncellenmiş `tir_kapasiteleri v2.xlsx` kullanılır: Balıkesir 0 → 1, Tekirdağ 1 → 2 | `src/data.py` tır kapasitesi yüklemesi |
| 2 | Kiralık araçlar da tır kapasitesini tüketir; kiralık tırlar tır kapasitesi kapsamındadır (HititRoute S11, Astra S1, Budapeşte S3) | Zorunlu kiralık tırlar planlamadan ÖNCE bütçeden düşülür; kaldırılırsa 12 ihlal doğar | `src/optimize.py` `_seed_context` |
| 3 | Tır kapasitesi yalnız Tır araç tipini kapsar; diğer araç türleri için kapasite yoktur (HititRoute S10, HİB LOGİ S7) | Yalnız `Araç türü == Tır` olan rotalar tır defterine yazılır; Kamyon/Hafif Kamyon/Kamyonet hiç sayılmaz | `src/simulator.py` tır defteri beslemesi |
| 4 | Kapasite giden ve gelen tır ayrımı yapılmaksızın günlük toplam tır sayısıdır (şartname Bölüm 6) | Her tır için hem çıkış hem varış merkezi ayrı ayrı düşülür; üç yerde birden uygulanır | `src/optimize.py` kiralık rezervasyonu, tır tahsisi, boşaltma günü |
| 5 | Aynı araç aynı TM'de hareket etmeden boşaltılıp tekrar yüklenirse 1 tır kapasitesi tüketir (şartname soru 7, Astra S2 netleştirmesi) | Tır defteri `(araç, ziyaret)` çiftlerini kümede tutar; bacak i'nin varışı ile bacak i+1'in kalkışı aynı ziyaret kimliğini paylaşır | `src/ledger.py` `TirLedger.add_event` |
| 6 | Dönüş yapan spot araç, döndüğü TM farklı olduğu için tır kapasitesi tüketir (HititRoute S13) | Araç gidip döndüğünde bacak indeksi ilerlediği için ziyaret kimliği farklı olur ve ayrı sayılır | `src/simulator.py` ziyaret kimliği türetimi |
| 7 | Tır kapasiteleri 00:00'da sıfırlanır (şartname soru 6) | Defter anahtarı `(merkez, gün)` çiftidir; günler bacağın kesin kalkış ve varış tarihlerinden alınır | `src/ledger.py` |
| 8 | Elleçleme kapasiteleri 00:00'da sıfırlanır (şartname soru 5) | Aynı defter yapısı; günlük kovalar | `src/ledger.py` `HandlingLedger` |
| 9 | Gece yarısını aşan elleçleme oransal bölünür: 23:30'da 10.000 desi → 3.000 / 7.000 (Astra S2, ByteSis, ek mesaj) | İşlem gece yarılarında dilimlenir ve her güne dakika payı oranında desi yazılır; jüri örneği birim testle çivilenmiştir | `src/ledger.py` `HandlingLedger.add` |
| 10 | Elleçleme kapasitesi o merkezdeki tüm elleçlemeleri (çıkış ve varış) kapsar; süre her ikisi için 0,01 dk/desi (HititRoute S8) | Her bacak için hem yükleme hem indirme olayı aynı deftere yazılır | `src/simulator.py` elleçleme olayı üretimi |
| 11 | Bir araçtan x indirilip y yüklenirse kapasiteden x+y düşülür; konsolidasyonda 2x (HititRoute S9, HİB LOGİ S6) | Yük akışı analizi `yüklenen / taşınan / indirilen` ayrımı üretir; ara merkezde inip yeniden yüklenen yük iki kez sayılır, gemide kalan yük hiç sayılmaz | `src/chain.py` `analyze_leg_flows` → `src/schedule.py` |
| 12 | Gün-aşırı taşımada çıkış günü için çıkış TM, varış günü için varış TM kapasitesi hesaba katılır (HititRoute S6) | Yükleme olayı yükleme başlangıcı anına, indirme olayı varış anına yazılır; günler bu anlardan türer | `src/simulator.py`, `src/ledger.py` |
| 13 | Kullanım süresi bekleme, elleçleme ve seyir sürelerinin toplamıdır; 10.000 desi + 5 saat = 500 dakika, beklemeli örnek 560 dakika (OptiVision S3, HititRoute S12, Budapeşte S5, HİB LOGİ S5, OpAI S3) | Maliyet, ilk yükleme başlangıcından son indirme bitişine kadar tek sürekli pencere üzerinden hesaplanır | `src/simulator.py` araç izi maliyeti |
| 14 | Yalova'daki (ara duraktaki) elleçleme süresi de aracın kullanım süresine dahildir (HİB LOGİ S9) | Ara durak elleçlemeleri pencerenin içindedir; ayrıca zincir bacakları arasında boş bekleme üretilmez | `src/milkrun.py` zaman çizelgesi |
| 15 | SLA başlangıcı orijinal çıkış TM'sindeki talep tamamlanma anı, bitişi orijinal varış TM'de elleçleme süresinin bitiş anıdır (HititRoute S14, OptiVision S2) | Ceza yalnız `indirildi ve bacak varışı = talebin varışı` koşulunda yazılır; ara indirmeler ceza almaz | `src/schedule.py` SLA beyanı |
| 16 | Konsolidasyondaki tüm adımlar (indirme, bekleme, yeniden yükleme) SLA süresine dahildir (OptiVision S2) | Saat kesintisiz işler; hiçbir ara süre düşülmez | `src/simulator.py` SLA hesabı |
| 17 | Gecikme bir üst tam saate yuvarlanır; 09:01 = 1 saat (Astra S3, şartname EK KISIT 2) | Gecikme dakikası 60'a bölünüp yukarı yuvarlanır; gecikme yoksa 0 | `src/timeutil.py` `late_hours` |
| 18 | 1 günlük SLA tam 24 saat, 2 günlük 48 saattir (HİB LOGİ S8) | Vade = hazır olma anı + 24 x SLA_gün saat | `src/optimize.py` talep havuzu kurulumu |
| 19 | Süreleri en yakın büyük tam sayıya yuvarlayın: 0,92 saat = 55,2 dk → 56 (ek mesaj) | Seyir ve elleçleme süreleri tek kaynaktan yukarı yuvarlanır; kayan nokta artefaktı korumalı | `src/timeutil.py` `travel_minutes`, `handling_minutes` |
| 20 | Elleçleme süresini desi ile çarptıktan sonra aynı şekilde yukarı yuvarlayın (ek mesaj) | 0,01 dk/desi çarpımı yukarı yuvarlanır; 22.400 desi → 224 dakika | `src/timeutil.py` `handling_minutes` |
| 21 | Bir spot aracın tek seferde birden fazla TM'ye uğrayıp sırayla yük bırakması mümkündür; kiralık araçlar için uğrama mümkün değildir (OpAI S1) | Milk-run zincirleri yalnız `Spot` bacaklardan kurulur ve yalnız `Spot` segment üretir; kiralık bacak kaynak olamaz | `src/milkrun.py` kaynak uygunluk kapısı |
| 22 | Toplam sefer sayısı için üst sınır yoktur; kısıtlar dikkate alınarak sınırsız sefer yapılabilir (NEURON-LOG) | Durak sayısına kural sınırı yoktur; `MAX_CHAIN_STOPS = 4` bizim mühendislik tercihimizdir ve gerekçesi kodda belgelenmiştir | `src/milkrun.py` sabit tanımı ve yorumu |
| 23 | Bir araca farklı varış noktalarına gidecek yükler birlikte yüklenebilir (HİB LOGİ S4) | Zincir çıkışta tüm yükü tek seferde alır, her durakta yalnız o durağın yükünü bırakır | `src/milkrun.py` segment yükü kurulumu |
| 24 | Bir araçtan x yük indirilip y yük yüklenirse kapasiteden x+y düşülür (HİB LOGİ S6) — bu cümle rota ortasında yük almayı serbest bırakır | Stage 3, rotanın zaten uğradığı bir durakta yük alır; indirme ve yükleme iki ayrı olay olarak zamanlanır ve deftere yazılır | `src/pickup.py` rota yeniden kurulumu |
| 25 | Kiralık araçlarla uğrama yapılmaz; kiralık araçlar sadece iki TM arasında hareket eder (şartname soru 2, HititRoute S11, OpAI S1) | Kiralık rota ne zincir kaynağı ne yük alma hedefi olabilir; kiralık bir rotayı spot tarifesiyle fiyatlama girişimi hata fırlatır | `src/pickup.py` `_require_spot_route`, `src/milkrun.py` kaynak kapısı |
| 26 | Kiralık araçlar dönüş yapamaz; her gün için belirtilen sayıda ve türde kullanılmalıdır (şartname soru 3) | Her gün tam 14 kiralık bacak üretilir; hiçbiri silinemez, kaydırılamaz, zincire alınamaz | `src/optimize.py` kiralık doldurma |
| 27 | Talep yetersiz olsa bile kiralık araçları çıkarmak zorundasınız (şartname Bölüm 3) | Havuz boş olsa bile bacak üretilir; boş bacak `Talep ID` boş ve desi 0 ile yazılır | `src/optimize.py`, `src/schemas.py` boş kiralık istisnası |
| 28 | Kiralık aracın çıkış saatini o gün içinde olacak şekilde belirleyiniz (Astra S1) | Kiralık kalkış ufuk günlerinde 17:00 + tam yük elleçlemesi olarak sabitlenir (Tır 20:44, Kamyon 19:00); boşaltma günlerinde Tır dışı kiralıklar 00:00 + tam yük elleçlemesine çekilir (Kamyon 02:00), Tır kalkışı ise 20:44'te kalır — hepsi aynı takvim günü içinde | `src/optimize.py` `rented_departure`, `_rented_early` |
| 29 | Spot araçlarla dönüş yapabilirsiniz ancak boş spot araçları döndürmeyiniz (ek mesaj) | Optimizer boş dönüş bacağı üretmez; hakem boş fiziksel izin yalnız `Kiralık` olabileceğini şart koşar | `src/simulator.py` boş iz denetimi |
| 30 | Günün her dakikasında araç çıkarılabilir, elleçleme yapılabilir; zaman çözünürlüğü dakikadır (HititRoute S5) | Tüm zamanlar dakika çözünürlüğünde tutulur; hiçbir yerde saat veya vardiya kuantizasyonu yoktur | `src/candidates.py`, `src/optimize.py` |
| 31 | Mesai saati kavramı yoktur; transfer merkezleri 24 saat çalışır (ROTAI S1) | Zaman modelinde çalışma penceresi kavramı yoktur; kalkış ve elleçleme günün herhangi bir dakikasında olabilir | Tüm zamanlama modülleri |
| 32 | 09:00 ve 17:00 talep tamamlanma anıdır; tamamlanan talebi istediğiniz saatte çıkarabilirsiniz (ROTAI S4, HititRoute S7) | Yükleme, talebin hazır olma anından önce başlayamaz; sonrasında herhangi bir anda başlayabilir | `src/candidates.py`, `src/simulator.py` hazır olma denetimi |
| 33 | 09:00 ve 17:00 ayrı satırlarda gösterilmelidir (HititRoute S1, HİB LOGİ S2) | Girdi tablosunun her satırı ayrı bir talep olarak işlenir; tahmin çıktısında da her slot ayrı satırdır | `src/contract.py` satır işleme |
| 34 | Talep kimliklerini siz üretmelisiniz; tahmin dosyası ile plan dosyasındaki kimlikler birebir eşleşmelidir (HititRoute S2) | Kanonik kimlikler iç boru hattında kullanılır, çıktıya girdideki özgün kimlikler geri yazılır | `src/contract.py` `restore_demand_ids` |
| 35 | Talebi bölebilirsiniz; plan dosyasında `D00001-1` ve `D00001-2` biçiminde göstermelisiniz (şartname soru 1) | Bölünme fiziksel parça başına yapılır ve sonekler çıktı aşamasında düz numaralandırmayla verilir | `src/schedule.py` kimlik atama |
| 36 | İkincil bölünmelerde `D00001-1-1` biçiminde uzatılır (Astra S4) | Şema doğrulaması çok düzeyli soneki kabul eder; mevcut boru hattı tek düzeyli sonek üretir | `src/schemas.py` `SPLIT_ID_RE` |
| 37 | Geçmiş veride bulunmayan bir TM ikilisi için talep tahmin etmemelisiniz (HititRoute S3, Budapeşte S6) | Tahmin evreni yalnız geçmişte görülen 289 aktif hattan türetilir; final koşusunda tahmin çalışmaz | `src/forecast.py` OD evreni türetimi |
| 38 | Tahmin edilen desi 0,5'in altında olsa bile o satır sunulmalıdır (OpAI S5) | Yuvarlama sonucu 0 çıkan satırlar silinmez; referans tahmin çıktısında 4.046 satırın 1.121'i sıfır desidir | `src/forecast.py` çıktı üretimi |
| 39 | %10 minimum doluluk kuralı bu aşamada bulunmamaktadır; gönderiler gecikirse SLA cezası ödenir (Budapeşte S4) | Kodun hiçbir yerinde doluluk alt sınırı yoktur; amaç fonksiyonu saf toplam maliyettir | Kısıt yok — arama sonucu boş |
| 40 | Optimizasyon için zaman sınırlaması yoktur; 5 Temmuz talebi 7 Temmuz'da teslim edilebilir, SLA cezaları buna göre hesaplanır (HititRoute S4, ROTAI S5, Budapeşte S1, OpAI S6) | Ufuktan sonra 2 boşaltma günü eklenir; kalan yük gün başından itibaren ertelemesiz taşınır ve doğan ceza tam olarak fiyatlandırılır | `src/optimize.py` boşaltma günü mantığı |
| 41 | Gönderiler elleçleme tamamlandığı an yeni araca yüklenmelidir gibi bir kural yoktur; bekletmek faydalıysa bekletebilirsiniz (şartname EK KISIT 2) | Erteleme mekanizması ertelemenin gerçek bedelini (SLA + ertesi gün taşıma) amaç fonksiyonuna katar; ölçülen net kazanç 8.473.648,91 TL | `src/candidates.py` erteleme fiyatlaması |
| 42 | Konsolidasyon yapmak bir zorunluluk değildir (OptiVision S2) | Zincirlerimiz konsolidasyon değil milk-run yapar: yük ara merkezde inip yeniden yüklenmez, gemide kalır — çift elleçleme maliyeti hiç doğmaz | `src/milkrun.py` yük akışı |
| 43 | Ara merkezde indirme bittikten hemen sonra, bekleme olmaksızın yüklemeye başlanabilir; minimum süre yoktur (Astra S3) | Aktarmada yeni aracın yüklemesi, önceki aracın indirme elleçlemesinin bitişinden önce başlayamaz; sonrasında hemen başlayabilir | `src/simulator.py` aktarma zamanlaması |
| 44 | Kapasitelere uygun olarak aynı anda araç yükleme/boşaltma yapılabilir; kuyruk yönetimi simüle edilmez (Excelerators) | Merkez başına eşzamanlılık kısıtı modellenmez; yalnız günlük kapasite defteri uygulanır | `src/ledger.py` |
| 45 | Aynı gün İstanbul'dan başka güzergah için hareket etmek dönüş değildir; aynı ya da farklı spot araç kullanılabilir (ROTAI S2) | Spot araçlar için sefer sayısı sınırı yoktur; her fiziksel rota ayrı bir kimlik alır | `src/schedule.py` araç kimliği atama |
| 46 | Taşıma Planı çıktısında saat formatı SS:DD yeterlidir (OpAI S4) | Plan saatleri `HH:MM` metni olarak yazılır; saniyeli biçim şema doğrulamasında reddedilir | `src/schemas.py` `TIME_RE` |
| 47 | Optimizasyon başarınız kendi tahminlediğiniz talepler üzerinden değerlendirilir (HİB LOGİ S3) | Final koşusunda talep tablosu dışarıdan verilir; plan yalnız verilen tabloya göre kurulur ve hiçbir talep kaybolmaz | `src/optimize.py` tam teslim güvencesi |
| 48 | Veri seti görüldüğü gibidir; Kocaeli varışlı talep yoktur (A-Ra) | Kocaeli hiçbir zaman varış değildir; 306 hattın 289'unda talep görülür ve tahmin yalnız bu 289 hat için üretilir | `src/forecast.py` OD evreni |

### 5.2 Açık yorum riski olarak izlediğimiz konular

Aşağıdaki üç konuda jüri cevabı tek bir yoruma kapatmamaktadır. Her birinde **muhafazakâr** yorumu seçtik ve bunu açıkça belirtiyoruz.

**Kiralık araç kimliklerinin günler arası kalıcılığı.** Kiralık filo her gün aynı araçları mı çıkarıyor, yoksa her gün yeni bir araç mı? Biz gün bazlı benzersiz kimlik kullanıyoruz. Bu, "aynı araç aynı gün birden fazla bacak yapamaz" kuralını daha katı biçimde uygular ve hiçbir yorumda ihlal üretmez.

**Beyan edilen maliyet mi, yeniden hesaplanan maliyet mi puanlanıyor?** İkisinin de tutarlı olması için beyan edilen `Toplam maliyet` kolonunun toplamı hakem hesabıyla en fazla 0,01 TL sapabilecek biçimde zorlanır. Ölçülen sapma 0,0000 TL'dir; hangi yöntemle puanlanırsa puanlansın sonuç aynıdır.

**Desi = 0 satırlarının kabulü.** Jüri "sunulmalı" cevabını tahmin dosyası için vermiştir. Taşıma planında sıfır desili satır yalnız zorunlu boş kiralık bacaklarında görünür ve şema doğrulaması bunu yalnız `Araç Tipi = Kiralık` durumunda kabul eder; boş bir spot bacak yazılamaz.

---

## 6. Çıktı Şema Tuzakları

Şartname net: "Bu formata uymayan takımların sonuçları kesinlikle değerlendirmeye alınmayacaktır." Teknik Gereksinimler Bölüm 10 aynı şeyi tekrarlar: "Üretilen çıktı, Bölüm 5'teki şemaya birebir uymaz (eksik/fazla/yanlış adlı kolon, yanlış sıra)" hatalı çalıştırma sayılır. Format hatası, ne kadar iyi bir plan üretilmiş olursa olsun sonucu sıfırlar. Bu bölüm, şemada gerçekten tuzak olan noktaları ve bunları nasıl kapattığımızı anlatır.

### 6.1 Tuzak 1 — "Araç Tipi" ile "Araç türü" arasındaki büyük/küçük harf farkı

Şablonda 2. ve 3. kolonlar şunlardır:

- `Araç Tipi` — büyük **T**, ikinci kelime büyük harfle başlar
- `Araç türü` — küçük **t**, üstelik son harf `ü`

Bu iki kolon yan yanadır, aynı kelimeyle başlar ve farklı büyük/küçük harf düzeni kullanır. Elle yazılan veya "düzeltilen" bir kolon başlığı burada kolayca `Araç Türü` olur ve şema hatasına yol açar. Üstelik anlamları da farklıdır: `Araç Tipi` sahiplik biçimidir (`Spot` veya `Kiralık`), `Araç türü` fiziksel araç sınıfıdır (`Tır`, `Kamyon`, `Hafif Kamyon`, `Kamyonet`).

### 6.2 Tuzak 2 — Elleçleme kolonlarının hem sırası hem harf düzeni

Şablonda 13. ve 14. kolonlar şunlardır:

- 13. `Varış elleçleme süresi` — küçük **e**
- 14. `Çıkış Elleçleme süresi` — büyük **E**

İki tuzak birden vardır. Birincisi harf düzeni: aynı kelime iki kolonda farklı yazılmıştır. İkincisi ve daha sinsi olanı **sıra**: sezgi "önce çıkış, sonra varış" der, ama şablon **önce varış, sonra çıkış** ister. Kolonları anlamlı sırada yazan bir uygulama, adları doğru yazsa bile sıra hatası verir.

### 6.3 Tuzak 3 — Diğer harf düzeni ayrıntıları

| Kolon | Dikkat edilecek nokta |
|---|---|
| `Taşınan Desi` | Büyük **D** |
| `Yolculuk süresi` | Küçük **s** |
| `SLA cezası` | Küçük **c** |
| `Toplam maliyet` | Küçük **m** |
| `Çıkış Tarihi`, `Çıkış Saati`, `Varış Tarihi`, `Varış Saati` | Hepsinde ikinci kelime **büyük** harfle |

Girdi tarafında da bir tuzak vardır: `Talep Tamamlama Saati` — "Tamamlanma" değil, "Tamamlama". Şartname metninde "Talep Tamamlanma Saati" ifadesi geçse de şablon kolonu "Tamamlama"dır.

### 6.4 16 kolonun tam sırası ve tipleri

| Sıra | Kolon adı | Tip | Örnek değer |
|---|---|---|---|
| 1 | Araç ID | metin | V0001 |
| 2 | Araç Tipi | metin | Spot |
| 3 | Araç türü | metin | Tır |
| 4 | Çıkış Transfer Merkezi | metin | İstanbul |
| 5 | Varış Transfer Merkezi | metin | Yalova |
| 6 | Çıkış Tarihi | metin (gg.aa.yyyy) | 29.06.2026 |
| 7 | Çıkış Saati | metin (SS:DD) | 20:44 |
| 8 | Varış Tarihi | metin (gg.aa.yyyy) | 29.06.2026 |
| 9 | Varış Saati | metin (SS:DD) | 21:40 |
| 10 | Talep ID | metin | D00123-1 |
| 11 | Taşınan Desi | sayı | 10000,000 |
| 12 | Yolculuk süresi | sayı (dakika) | 56 |
| 13 | Varış elleçleme süresi | sayı (dakika) | 100 |
| 14 | Çıkış Elleçleme süresi | sayı (dakika) | 100 |
| 15 | SLA cezası | sayı (TL) | 0,0 |
| 16 | Toplam maliyet | sayı (TL) | 3580,0 |

Tablodaki örnek satır rastgele seçilmemiştir; jürinin işlenmiş örneğinin (spot Tır, İstanbul-Yalova hattı, 10.000 desi) birebir karşılığıdır: 100 dakika yükleme + 56 dakika yol + 100 dakika indirme = 256 dakika kullanım süresi, 487,50 x 256/60 + 25 x 60 = 3.580,00 TL. Kalkış 20:44, varış 21:40 — aradaki fark tam olarak 56 dakikadır.

### 6.5 Bu riski nasıl kapattık

Format riskini üç bağımsız katmanla kapattık.

**Katman 1 — Tek doğruluk kaynağı.** Kolon adları hiçbir yerde elle yazılmaz. `src/schemas.py` içinde `PLAN_COLS` adlı tek bir liste vardır ve çıktı çerçevesi doğrudan bu listeyle kurulur. Kolon adının yanlış yazılabileceği tek yer bu liste olduğu için, hata yüzeyi tek bir listedeki 16 kolon adına indirilmiştir.

**Katman 2 — Yazımdan önce doğrulama.** `validate_plan`, çerçevenin kolon listesini `PLAN_COLS` ile birebir karşılaştırır. Uyuşmazlık varsa **tek bir hata döndürüp diğer kontrolleri hiç çalıştırmaz** — yanlış kolonlu bir çerçevede satır bazlı erişim zaten anlamsız olurdu. Bu doğrulama başarısız olursa hedef dosyaya **hiç dokunulmaz**.

**Katman 3 — Yazımdan sonra diskten geri okuyup yeniden doğrulama.** Dosya geçici bir yola yazılır, `pd.read_excel` ile geri okunur ve kolon listesi ile satır sayısı yeniden karşılaştırılır. Ancak bu kontrol de geçerse `os.replace` ile atomik olarak yerine konur. Böylece "bellekte doğru ama diske yanlış yazıldı" sınıfı hatalar da yakalanır.

Ek olarak `tools/verify_output.py` betiği, yayınlanan dosyayı sıfırdan okuyup hakem simülatöründen geçirir ve şemayı bağımsız olarak bir kez daha doğrular.

**Kanıt.** Teslim edilen `out/Tasima-plani.xlsx`: 5.523 satır x 16 kolon, tek sayfa, kolon adları ve sırası şablonla birebir. Bozuk `Araç türü` değeri enjekte edildiğinde hedef dosyanın hiç oluşmadığı testle çivilenmiştir.

---

## 7. Genelleştirilebilirlik Kanıtı (Bölüm 7)

Bölüm 7 iki şey ister: gömülü takvim tarihi bulunmaması ve farklı hacimde çalışabilme. İkisini de ölçtük.

### 7.1 Üç ölçülmüş senaryo

Sentetik girdiler `tools/make_test_input.py` ile üretildi (tarih kaydırma, hacim ölçekleme, ufuk kısaltma, kimlik ve saat biçimi değiştirme). Üretilen planlar `tools/verify_output.py` ile diskten geri okunup bağımsız olarak hakem simülatöründen geçirildi.

| Senaryo | Ufuk | Talep satırı | Desi | Süre | İhlal | Kazanç |
|---|---|---:|---:|---:|---:|---:|
| Referans (teslim edilen) | 29.06.2026 - 05.07.2026 (7 gün) | 4.046 | 4.977.975 | 150 sn | 0 | -%31,8 |
| Farklı yıl, 4 günlük ufuk, %35 hacim, `REQ_` kimlikler, `HH:MM` biçimi | 25.05.2025 - 28.05.2025 (4 gün) | 1.808 | 1.214.316 | 171 sn | 0 | -%45,8 |
| Farklı hafta, %125 hacim, `D...` kimlikler, `HH:MM:SS` biçimi | 02.09.2026 - 08.09.2026 (7 gün) | 2.925 | 6.222.428 | 143 sn | 0 | -%28,0 |

Her üç senaryoda da çıkış kodu 0, şema birebir, beyan edilen toplam maliyet ile hakem toplamı arasındaki fark 0,0000 TL.

Bu tablo dört değişkeni aynı anda test eder: **yıl** (2025 ve 2026), **ufuk uzunluğu** (4 ve 7 gün), **hacim** (%35, %100, %125) ve **girdi biçimi** (üç farklı kimlik deseni, üç farklı saat biçimi).

### 7.2 Gömülü tarih olmadığının kanıtı

Ufuk yalnız girdinin `Tarih` kolonundan türetilir. Aynı haftanın 2019, 2026 ve 2031 yıllarına taşınmasıyla sonucun kaymadığı testle çivilenmiştir. Önceki teslimdeki `HORIZON_START` ve `HORIZON_END` sabitleri `main.py`'ye taşınmamıştır.

Tahmin tarafında dürüst bir istisna vardır ve belirtmek gerekir: eğitim verisi filtresindeki resmî tatil listesi 2026 takvimine özgü bir veri alanı sabitidir. Ancak bu liste **yalnızca eğitim verisi filtresidir**, hedef gün üretimini etkilemez ve final koşusunda tahmin modülü hiç çağrılmaz.

### 7.3 %250 hacim davranışı — fizikî sınır ve doğru davranış

Bölüm 7 "makul ölçüde farklı büyüklükler" der. Bu makul aralığın dışına çıkıldığında ne olduğunu da ölçtük, çünkü sessizce yanlış sonuç üretmemek Bölüm 7'nin açık gereğidir.

**Fizikî durum.** Ağın elleçleme kapasitesi referans hafta için zaten neredeyse tamamen doludur. En kritik nokta: İstanbul, 01.07.2026 — o günün yükleme artı indirme talebi 395.825 desi, günlük kapasite 394.786 desi. Yani hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme kısıtı **hiçbir plan tarafından** sağlanamaz. Bu bir kod kusuru değil, veri setinin fizikî olarak çözümsüz olmasıdır.

**Ölçülen davranış.** %250 hacimli sentetik veri setinde:

| Gözlem | Sonuç |
|---|---|
| Stage 0 temel planı | Üretildi ve yayınlandı |
| Elleçleme ihlali | 69 — tamamı, o gün o merkezde talebin kapasiteyi aşmasından kaynaklanıyor (örneğin Erzincan 80.160 desi talep, kapasite 58.673) |
| Stage 1 adayı | Doğru biçimde **reddedildi** — kabul kuralı temel planda da adayda da 0 ihlal arar |
| Çökme | Yok |
| Yazılan plan | Bölüm 5 şemasına birebir uyuyor |
| Stage 2 araması | Kombinatoryal olarak büyüdü; sert süre sınırı tam bu durum için vardır |
| Zorla sonlandırma testi | Süreç Stage 2'nin ortasında öldürüldüğünde diskte 3.710 satırlık, tek sayfalı, 16 kolonu doğru bir plan bulundu |

Bu davranış tam olarak istenen davranıştır: kod, çözülemez bir kısıt karşısında sessizce yanlış sonuç üretmez, çökmez, ve elde ettiği en iyi geçerli planı şemaya uygun biçimde yazar.

### 7.4 Kimlik ve biçim genelleştirmesi

| Değişken | Test edilen değerler | Sonuç |
|---|---|---|
| Talep kimliği deseni | `D00001...`, `REQ_1...`, tireli kimlikler | Kanonik eşleme kuruluyor, çıktıda özgün kimlik geri yazılıyor |
| Saat biçimi | `datetime.time`, `HH:MM`, `HH:MM:SS`, Excel gün kesri, Timedelta | Hepsi kanonik `HH:MM`e çevriliyor |
| Tarih biçimi | Altı metin biçimi, Excel seri numarası, üç Python tarih tipi | Hepsi `date`e çevriliyor |
| Kolon adı | Fazladan boşluk, büyük/küçük harf, Unicode NFD | Eşleniyor; eşlenemezse 6 kolonluk tabloda konum eşlemesine düşülüyor |
| Kimlik genişliği | 5 hane ve üzeri | `D\d{5,}` deseniyle kabul ediliyor |

---

## 8. Kalan Tek İşlem

> **UYARI — TESLİMDEN ÖNCE YAPILMASI GEREKEN TEK İŞLEM**
>
> `final-teslim/teknofest_manifest.json` dosyasındaki `takim_id` alanı şu anda
> yer tutucu durumdadır: alanın değeri `BASVURU_NUMARANIZI_YAZIN` metnidir,
> `takim_adi` alanının değeri ise `Büke` olarak girilmiştir.
>
> `takim_id` alanına **başvuru numarası** yazılmalıdır. Ayrıca `takim_adi` alanının doğru
> yazıldığı da kontrol edilmelidir.
>
> Teknik Gereksinimler Bölüm 6, bu dosyanın "teknik ekibin kodunuzu otomatik
> olarak kurup çalıştırabilmesi için gerekli" olduğunu belirtir. Manifest
> alanları eksik veya yanlışsa otomatik kurulum akışı kırılabilir.
>
> **Bu iki alan dışında paket teslime hazırdır.** Bölüm 11 kontrol listesinin
> diğer dokuz maddesi doğrulanmış durumdadır ve manifest dosyasının kalan tüm
> alanları koddaki sabitlerle birebir eşleşmektedir.

### 8.1 Değişiklik sonrası tekrar doğrulanması gerekenler

`takim_id` alanı bir metin alanıdır ve kod tarafından okunmaz; değiştirilmesi hiçbir davranışı etkilemez. Yine de teslim disiplini açısından değişiklikten sonra iki hızlı kontrol önerilir:

1. Dosyanın geçerli JSON olduğunun doğrulanması.
2. `python main.py` ile bir doğrulama koşusu — çıkış kodu 0 ve `out/Tasima-plani.xlsx` üretimi.

### 8.2 Paket teslim durumu özeti

| Gereksinim | Durum |
|---|---|
| Bölüm 3 — main.py tek giriş noktası | Hazır |
| Bölüm 4 — Girdi sözleşmesi (iki erişim yöntemi) | Hazır |
| Bölüm 5 — Çıktı sözleşmesi (16 kolon, atomik yazım) | Hazır |
| Bölüm 6 — teknofest_manifest.json | `takim_id` bekliyor |
| Bölüm 7 — Genelleştirilebilirlik | Hazır (üç senaryo ölçüldü) |
| Bölüm 8 — Değişiklik kapsamı | Hazır (0 farklı hücre kanıtı) |
| Bölüm 9 — Kurulum ve bağımlılıklar | Hazır (temiz ortamda doğrulandı) |
| Bölüm 10 — Puanlama güvenlikleri | Hazır (kademeli yayın + sert süre sınırı) |
| Bölüm 11 — Kontrol listesi | 10 maddenin 9'u tam, 1'i `takim_id` bekliyor |

---

## 9. Kapanış

Bu belge üç soruyu kanıtlı biçimde yanıtlamak için yazıldı.

**Format riski kapatıldı mı?** Evet. 16 kolonluk şema tek bir sabitten üretilir, yazımdan önce ve yazımdan sonra iki kez doğrulanır, atomik olarak yerine konur ve bağımsız bir araçla diskten geri okunup yeniden denetlenir. Teslim edilen dosya 5.523 satır x 16 kolon, tek sayfa, ad ve sıra birebirdir.

**Kural riski kapatıldı mı?** Evet. Jürinin verdiği 48 bağlayıcı cevabın her biri kod düzeyinde bir konuma bağlanmıştır ve planlayıcıdan bağımsız yazılmış hakem simülatörü bunları sıfırdan yeniden denetler. Teslim edilen planda 0 ihlal vardır ve beyan edilen maliyetle hakem hesabı arasındaki fark 0,0000 TL'dir.

**Bölüm 8 sınırı korundu mu?** Evet. On altı algoritma modülünün tamamı değişmemiştir; değişen iki modülde yapılan işlem yalnızca davranış genişletmedir. Bunun ölçülebilir kanıtı, aynı girdiyle üretilen çıktının önceki teslimle **0 farklı hücre** göstermesidir.

Geriye kalan tek işlem, manifest dosyasındaki başvuru numarasının yazılmasıdır.
