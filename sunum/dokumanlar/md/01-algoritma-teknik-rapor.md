# Algoritma ve Teknik Rapor

TEKNOFEST 2026 · Hepsiburada · Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · Takım Büke · Final aşaması (backtest)

Bu belge, teslim edilen çözümün uçtan uca teknik anlatımıdır. Amacı, okuyucunun tek bir satır kaynak koda bakmadan çözümün her parçasını anlayabilmesidir. Belgede geçen her sayı, ya teslim paketindeki bir dosyadan ya bir ölçümden ya da jüri Soru-Cevap (Q&A) metninden gelir; iddiaların yanında kaynağı yazılıdır. Teknik terimlerde Türkçe karşılık kullanılmış, ilk geçtiği yerde parantez içinde İngilizcesi verilmiştir.

---

## 1. Yönetici Özeti

### 1.1 Problem

Bir haftalık talep tablosu veriliyor: her aktif transfer merkezi çifti (origin-destination, OD) için, her gün, 09:00 ve 17:00 talep tamamlanma anlarında oluşan desi miktarı. Bu talebin tamamı, 18 transfer merkezi ve 306 yönlü hattan oluşan bir ağ üzerinde, dört araç türüyle, dakika çözünürlüklü bir sevkiyat planına dönüştürülmelidir. Plan yalnızca "hangi araç hangi hatta çalışacak" sorusunu değil, "hangi dakikada yüklemeye başlayacak, hangi dakikada kalkacak, hangi dakikada varacak, hangi dakikada indirmeyi bitirecek" sorularını da cevaplamak zorundadır.

Kısıtlar operasyonel gerçeğe yakındır: her merkezin günlük elleçleme (handling) kapasitesi vardır ve **kesinlikle** aşılamaz; yedi merkezin tır işlem kapasitesi sıfırdır; 12 rotada 14 kiralık araç talep olmasa bile her gün sefere çıkmak zorundadır ve rotasından sapamaz; her hattın söz verilen teslim süresi (SLA) vardır ve aşılırsa desi başına saatlik ceza doğar.

### 1.2 Çözüm

Planı tek hamlede kurmuyoruz. Dört aşamalı bir **optimizasyon merdiveni** kuruyoruz: her aşama bir öncekinin planını girdi alır, kendi iyileştirmesini dener ve **yalnızca bağımsız hakem simülatörü (referee simulator) sıfır ihlalle daha düşük maliyet onaylarsa** kabul edilir. Reddedilen aday resmî çıktıyı değiştirmez; bir önceki aşamanın planı korunur.

- **Stage 0 — temel plan:** zorunlu kiralık filoyu doldur, kıt tır ziyaret bütçesini rezerve et, her (hat, gün) için araç sayısı karmasını tam sayımla (exhaustive enumeration) seç, taşınamayan yükü fiyatlandırılmış bir kararla ertele.
- **Stage 1 — aynı-hat onarımı (same-lane repair):** aynı hat ve gün üzerindeki düşük dolulukta bir spot aracın tüm yükünü mevcut bir araca taşı, o aracı plandan sil.
- **Stage 2 — milk-run zincirleme:** aynı çıkış merkezinden **tam olarak aynı dakikada** kalkan 2–4 ayrı spot aracı tek fiziksel araca zincirle; yük çıkışta bir kez yüklenir, her durakta yalnız o durağa ait desi iner.
- **Stage 3 — rota ortasında yük alma (mid-route pickup, Tier A):** zincir bir ara durakta yalnız indirmesin; oradan kalkacak yükü de alsın ve o yükü tek başına taşıyan aracı plandan sil.

### 1.3 Sonuç

| Aşama | Araç maliyeti (TL) | SLA cezası (TL) | Toplam (TL) | İhlal | Fiziksel araç |
|---|---:|---:|---:|---:|---:|
| Stage 0 — temel plan | 15.460.592,57 | 1.020.367,20 | **16.480.959,77** | 0 | 1.269 |
| Stage 1 — aynı-hat onarım | 12.510.401,25 | 2.169.783,60 | **14.680.184,85** | 0 | 1.092 |
| Stage 2 — milk-run (≤4 durak) | 8.752.512,29 | 2.560.826,00 | **11.313.338,29** | 0 | 693 |
| **Stage 3 — rota-ortası yük alma** | **8.616.944,73** | **2.615.532,00** | **11.232.476,73** | **0** | **665** |

Kümülatif tasarruf **5.248.483,04 TL**, yani **−%31,84**. Ortalama spot araç doluluğu **%48,02 → %79,03**. Fiziksel araç sayısı **1.269 → 665**. Her aşamada hakem ihlali sıfırdır.

### 1.4 Neden kazandık

Kazancın tamamı tek bir fikirden gelir: **maliyet aracın kendisindedir, yükün kendisinde değil.** Bir spot aracı yola çıkarmak sabit bir km bedeli ve saatlik bir kullanım bedeli doğurur; o araca fazladan desi koymak ise yalnızca birkaç dakikalık ek elleçleme demektir — ölçülmüş marjinal maliyet en ucuz araçta 0,06597 TL/desi, kiralık kamyonda 0,06944 TL/desidir. Bu yüzden merdivenin üç iyileştirme aşaması da aynı hamleyi farklı yollardan yapar: **bir aracı tamamen ortadan kaldırıp yükünü zaten yola çıkacak olan bir araca bindirmek.** Stage 1 bunu aynı hatta, Stage 2 aynı çıkış merkezinden aynı anda kalkan farklı hatlarda, Stage 3 ise zincirin geçtiği bir ara merkezde yapar. Jüri bu aşamada gizli bir SLA tavanı koymadığı ve gecikmeyi 0,4 TL/desi/saat ile fiyatlandırdığı için (Q&A, Budapeşte Soru 4), doğru hedef saf toplam maliyettir: araç maliyetinden **6.843.647,84 TL** kazanıp **1.595.164,80 TL** ceza ödemek bilinçli ve ölçülmüş bir takastır.

---

## 2. Problem Tanımı ve Maliyet Modeli

### 2.1 Amaç fonksiyonu

Şartname maliyeti iki kalemde tanımlar ve çözümün minimize ettiği tek büyüklük bunların toplamıdır:

```
Toplam Maliyet = Araç Maliyeti + SLA Cezası

Araç Maliyeti  = (Saatlik Kiralama Maliyeti x Kullanım Süresi)
                 + (Kat Edilen Mesafe x Kilometre Başı Maliyet)

SLA Cezası     = Geciken Desi x Gecikme Süresi (Saat) x 0,40 TL
```

Kilometre kuş uçuşu hesaplanmaz; şartname Bölüm 5 açıkça "Kilometreyi direkt bu exceldeki bilgilere uygun kullanacaksınız" der. Kod da mesafeyi yalnız `datas/sehirler_arasi_lojistik.xlsx` matrisinden okur (`src/pickup.py` içindeki `_route_km`, `src/milkrun.py` içindeki `_vehicle_cost_tl`).

### 2.2 Kullanım süresi: tek sürekli pencere

"Kullanım süresi" bu problemin en çok yanlış modellenebilecek kalemidir. Jüri üç ayrı takıma (OptiVision Soru 3, HititRoute Soru 12, Budapeşte Soru 5) aynı cevabı, aynı işlenmiş örnekle vermiştir; OpAI Soru 3 ve HİB LOGİ Soru 5 ile 9 aynı tanımı kısaca yineler:

> **Cevap:** Bekleme süreleri ve elleçleme süreleri araçların kullanım süresine dahildir. Tır çıkış elleçleme süresi 10000 x 0,010 = 100 dakika; Tır yol süresi = 5 saat; Tır varış elleçleme süresi 10000 x 0,010 = 100 dakika; **Toplam süre = 500 dakika**. (Bir saat bekleme eklenirse toplam 560 dakika olur.)

Çözümde kullanım süresi bu yüzden **tek sürekli pencere** olarak alınır: ilk yükleme başlangıcından (`load_start`) son indirme bitişine (`unload_end`) kadar geçen her dakika. Çok duraklı bir zincirde ara durakların indirme elleçlemeleri, duraklar arası seyir ve varsa bekleme bu pencerenin içindedir. Ayrı bir "seyir süresi" kalemi yoktur, dolayısıyla bekleme veya elleçleme sayılmayı unutamaz. Hakem simülatörü aynı formülü bağımsız olarak yeniden kurar: `usage_hours = (son unload_end − ilk load_start) / 3600`, saate yuvarlama yapılmaz.

Jürinin verdiği örnek testle çivilenmiştir: spot Tır, 10.000 desi, İstanbul→Yalova hattı, 256 dakika kullanım, 487,50 x 256/60 + 25 x 60 = **3.580 TL**.

### 2.3 SLA saati nerede başlar, nerede biter

Saat, talebin **orijinal çıkış merkezindeki tamamlanma anında** başlar (09:00 veya 17:00) ve **orijinal varış merkezinde indirme elleçlemesinin bittiği anda** durur. HititRoute Soru 14'ün cevabı bunu kelimesi kelimesine söyler: *"SLA başlangıcı orjinal çıkış tmsindeki talep tamamlanma anıdır. Bitişi ise orjinal varış tmde elleçleme süresinin bitiş anıdır."* Şartname EK KISIT 1 ayrıca "SLA için süre hesaplarken araç varış anını değil elleçlenme işleminin tamamlanma anını esas almanız gerekmektedir" der.

Bunun üç somut sonucu vardır ve üçü de kodda ayrı ayrı uygulanmıştır:

- **Ara merkezde inen yük ceza almaz.** Konsolidasyon veya milk-run nedeniyle bir yük ara bir merkezde inse bile saat işlemeye devam eder. `src/schedule.py` cezayı yalnız `unloaded and leg.dest == part.dest` koşulunda, yani parçanın kendi nihai varışında yazar.
- **Aracın varış anı değil, indirmenin bitişi esastır.** `arr` değil `unload_end` kullanılır.
- **SLA penceresi gün cinsindendir ve tam saate çevrilir.** HİB LOGİ Soru 8: *"Evet 24 saat ya da 48 saattir."* Kodda `deadline = ready + timedelta(hours=24 * lane.sla_days)`. Veri setindeki 306 hattın 204'ü 1 günlük, 102'si 2 günlük SLA'ya sahiptir.

### 2.4 Yuvarlama kuralları

Jürinin son gönderdiği netleştirme mesajı yuvarlamanın yönünü tartışmasız hâle getirir:

> "İstanbuldan Yalovaya bir tır çıkartıyorsunuz ve araç çıkış saati 10.14 ise transfer süresi 0,92 saat olduğundan transfer süresi 55,2 dakikadır. Bu durumda **56**'ya yuvarlamanızı bekliyoruz. Yani süreleri en yakın büyük tam sayıya yuvarlamanız beklenmektedir. Elleçleme süresini de aynı şekilde desi ile elleçleme süresini çarptıktan sonra en yakın büyük tam sayıya yuvarlayarak bulunuz."

Tüm yuvarlama tek bir dosyada, `src/timeutil.py` içinde toplanmıştır; projede başka hiçbir yerde süre aritmetiği tekrarlanmaz. Üç kural:

| Kural | Formül | Doğrulanmış örnek |
|---|---|---|
| Seyir süresi | `travel_minutes(saat) = ceil(saat x 60)` | 0,92 sa = 55,2 dk → 56 dk |
| Elleçleme süresi | `handling_minutes(desi) = ceil(desi x 0,01)` | 5.000 desi → 50 dk; dolu Tır 22.400 desi → 224 dk |
| SLA gecikmesi | `late_hours = ceil(gecikme dakikası / 60)` | 1 dakika gecikme → 1 saat; 2 sa 20 dk → 3 saat |

Yuvarlama fonksiyonu `math.ceil` çağırmadan önce değeri 6 haneye yuvarlar (`_ceil_guarded`). Gerekçesi ölçülmüş bir kayan nokta (float) artefaktıdır: hat matrisindeki bir seyir saati tam dakikaya denk geldiğinde çarpım tam sayının bir tık **üstünde** çıkabiliyor. Ölçülen gerçek örnek Mersin↔Denizli Kamyonet bacağıdır: 8,05 saat için 8,05 x 60 çarpımı Python'da 483,00000000000006 verir ve korumasız bir `ceil` bunu 483 yerine 484 dakikaya taşırdı. Veri setinde bu durumdaki hat-araç çifti tam olarak ikidir (Mersin→Denizli ve Denizli→Mersin, Kamyonet); koruma ikisini de doğru dakikada tutar. Kural `travel_minutes(4.6) == 276` gibi birim testleriyle çivilenmiştir.

Yükleme ve indirme elleçlemesi **ayrı ayrı** hesaplanır; jüri HititRoute Soru 8'de "Her ikisi için de süre aynıdır ve 0.01 dakika/desidir" demiştir. Ayrıca şartname EK KISIT 1 bir araçtaki tüm gönderilerin elleçlemesinin aynı anda başlayıp aynı anda bittiğini şart koşar: *"Yarışmacılar aynı araç içerisindeki desiyi bölerek bir kısmını daha erken elleçlenmiş kabul edemezler."* Bu yüzden fiziksel zaman çizelgesi bacak düzeyinde **tek toplu işlem** kullanır: `ceil(Σdesi x 0,01)`. Plan dosyasındaki satır başına elleçleme hücresi ise bu tek işlemin talep bazlı **beyanıdır**, toplanabilir bir zaman çizelgesi değildir. İki satırlık 550 + 550 desilik bir bacakta gerçek elleçleme `ceil(11)` = 11 dakika, beyan hücreleri 6 + 6 = 12 dakikadır; hakem simülatörü de tam olarak satır bazlı değeri bekler, dolayısıyla beyan ile denetim aynı tanımı kullanır.

### 2.5 Kapasite kısıtları

**Elleçleme kapasitesi** her transfer merkezi için günlüktür ve şartname Bölüm 4 "Elleçleme kapasitesini kesinlikle geçemezsiniz. Kapasiteyi aşma durumunda yükleri bekletip ertesi gün göndermeniz beklenmektedir" der. Kapasite hem çıkış hem varış elleçlemesini kapsar (HititRoute Soru 8) ve konsolidasyonda iki kez sayılır: HİB LOGİ Soru 6'nın cevabı *"bir araçtan x kadar yük indirilip y kadar yük yüklenirse kapasiteden x+y kadar yük düşülür"* biçimindedir. Kapasiteler 00:00'da sıfırlanır ve gece yarısını aşan bir elleçleme işlemi **süreye oransal** bölünür: 29.06'da 23:30'da başlayan 10.000 desilik (100 dakikalık) bir işlem, 29.06'ya 3.000 desi, 30.06'ya 7.000 desi yazar. Bu örnek `src/ledger.py` içindeki `HandlingLedger.add` tarafından birebir üretilir ve `tests/test_ledger.py` içinde doğrudan iddia edilir.

**Tır işlem kapasitesi** yalnız "Tır" araç tipini kapsar (HititRoute Soru 10: *"diğer araç türleri için herhangi bir kapasite kısıtı bulunmamaktadır"*), kiralık tırlar da bu kotayı tüketir (HititRoute Soru 11) ve giden/gelen ayrımı yapılmaz. Kritik incelik, şartname son sayfa Soru 7 ile Q&A'daki Astra netleştirmesinin birleşiminden çıkar: aynı araç bir merkezde **hareket etmeden** boşaltılıp yeniden yüklenirse 1 ziyaret sayılır, ama gidip geri dönerse 2 sayılır. Kod bunu `TirLedger` içinde `(araç kimliği, ziyaret numarası)` çiftlerinden oluşan bir **küme** ile modeller: bacak *i*'nin varışı ile bacak *i+1*'in kalkışı aynı ziyaret numarasını paylaşır, dolayısıyla küme onları tek eleman sayar.

### 2.6 Kiralık filo kuralları

12 rotada toplam 14 kiralık araç vardır (10 Tır + 4 Kamyon). Üç sert kural geçerlidir ve üçü de hem planlayıcıda hem hakemde ayrı ayrı uygulanır:

- **Talep olmasa bile her gün çıkarlar** (şartname Bölüm 3). Boş çıkan bacak, `Talep ID` hücresi boş ve `Taşınan Desi` sıfır olacak biçimde plana yazılır.
- **Uğrama (milk-run) yapamazlar** ve rotalarından sapamazlar (şartname Bölüm 3; Q&A OpAI Soru 11.1: *"kiralık araçlar için uğrama mümkün değildir"*). Kod kiralık bir bacağı hiçbir zaman zincire almaz, hiçbir zaman verici (donor) olarak silmez, hiçbir zaman yük alma hedefi yapmaz.
- **Dönüş yapmazlar.** Boş spot araç da plana yazılmaz — jürinin son mesajı: *"Boş araçları döndürmeyiniz."*

Bu kuralların ölçülmüş bedeli ve ölçülmüş getirisi birlikte anlatılmalıdır. Bedel: 126 kiralık bacağın 35'i boş çıkar ve bu boş bacaklar **104.545,11 TL** tutar. Getiri: aynı 126 bacak toplam **459.936,67 TL**'ye — nihai planın 8.616.944,73 TL'lik araç maliyetinin yalnız **%5,34'ü**, Stage 0 temel planının araç maliyetinin ise %2,97'si — **867.524 desi** (toplam hacmin %17,4'ü) taşır. Bu yüzden algoritma kiralık filoyu **her zaman spottan önce** ve acil yükle doldurur.

---

## 3. Veri Katmanı

### 3.1 Sekiz veri dosyası

Tüm statik referans veriler `datas/` klasöründedir ve `src/data.py` tarafından tipli, değişmez (immutable) alan nesnelerine yüklenir. Bu dosyalar salt okunurdur ve final değerlendirmesinde değiştirilmeyecektir (Teknik Gereksinimler Bölüm 4).

| Dosya | Yüklendiği yapı | Ölçülmüş içerik |
|---|---|---|
| `sehirler_arasi_lojistik.xlsx` | `lanes` | Tam olarak 306 yönlü hat; km, dört araç türü için seyir saati, hedef teslim günü (SLA) |
| `Araç_Kapasite_Maliyet_Saat.xlsx` | `vehicles` | 4 araç türü; kapasite, kiralık ve spot saatlik + km başı ücretler |
| `Kiralık_Araclar.xlsx` | `rentals` | 12 rota, 14 araç (10 Tır + 4 Kamyon) |
| `Ellecleme-kapasite.xlsx` | `handling_cap` | 18 merkez, hepsi pozitif |
| `tir_kapasiteleri v2.xlsx` | `tir_cap` | 18 merkez; toplam 69 ziyaret, yedi merkezde sıfır |
| `teknofest26_gelismis.xlsx` | `demand` | 66.024 geçmiş talep satırı, 01.01–28.06.2026, 179 gün |
| `TALEP TAHMİNİ.xlsx` | (şablon) | Tahmin çıktı biçimi örneği |
| `TAŞIMA PLANI.xlsx` | (şablon) | Plan çıktı biçimi örneği |

Ağın ölçüleri: **18 transfer merkezi**, 18 x 17 = **306 hat** (matris tamdır, tek bir eksik hat yoktur), geçmiş veride talep görülen **289 aktif OD çifti**. Kocaeli hiçbir zaman varış merkezi değildir, bu yüzden 306 hattın 289'unda talep oluşur.

**Araç merdiveni** (kapasite / spot saatlik / spot km başı):

| Araç türü | Kapasite (desi) | Spot TL/saat | Spot TL/km | Kiralık TL/saat | Kiralık TL/km |
|---|---:|---:|---:|---:|---:|
| Tır | 22.400 | 487,50 | 25 | 291,67 | 13 |
| Kamyon | 12.000 | 318,25 | 21 | 208,33 | 10 |
| Hafif Kamyon | 7.200 | 364,58 | 20 | 208,33 | 10 |
| Kamyonet | 5.600 | 197,92 | 18 | 156,25 | 6 |

Bu tablodaki iki gözlem algoritmanın iki tasarım kararını doğrudan belirler. Birincisi, **Hafif Kamyon Kamyon tarafından domine edilir**: hem daha küçük (7.200 < 12.000) hem saatlik daha pahalıdır (364,58 > 318,25). İkincisi, **Tır ancak yeterince büyük yüklerde kazanır**: km başına 25 TL ile Kamyonun 21 TL'sinden pahalıdır ve ölçüldüğünde 306 hattın 306'sında Kamyondan yavaştır.

### 3.2 Yükleme sırasındaki doğrulamalar

`src/data.py` verinin bütünlüğünü yükleme anında sert biçimde denetler; sapma hâlinde süreç `ValueError` ile durur:

- Hat sayısı tam **306**, transfer merkezi sayısı tam **18** olmalıdır.
- Hat matrisi, elleçleme kapasitesi ve tır kapasitesi tablolarının merkez kümeleri **birebir aynı** olmalıdır.
- Benzersizlik: araç adı, hat çifti, kiralık rota ve talep kimliği tekrar edemez.
- Sayısal alanlar sonlu ve işaretine uygun olmalıdır; tır kapasitesi negatif olmayan **tam sayı**, elleçleme kapasitesi pozitif olmalıdır.
- Kiralık rotalarda çıkış ile varış farklı olmalı, araç türü tanınmalı, adet pozitif tam sayı olmalı ve rota hat matrisinde bulunmalıdır.
- Geçmiş talep tablosunda saat `9:00` biçiminden `09:00` biçimine normalize edilir ve slot kümesinin `{09:00, 17:00}` olduğu doğrulanır.

### 3.3 Türkçe dosya adı sorunu: NFC ve NFD

Windows NTFS dosya sistemi Türkçe karakterli dosya adlarını Unicode'un **NFD** (ayrıştırılmış) biçiminde saklayabilir; Python'un yol karşılaştırması ise metni **NFC** (birleşik) biçimde bekler. Bu durumda `Araç_Kapasite_Maliyet_Saat.xlsx` gibi bir dosya diskte var olduğu hâlde "bulunamadı" hatası verir. `src/data.py` içindeki `_resolve_file` bunu çözer: önce adı birebir dener, bulamazsa dizindeki tüm adları NFC'ye normalize ederek karşılaştırır. Bulunamazsa mevcut dosyaları `ascii()` ile listeleyen net bir hata mesajı üretir — yani hata sessiz kalmaz.

Aynı normalizasyon mantığı girdi tablosunun **kolon adlarında** da uygulanır (`src/contract.py` içindeki `_squeeze`): NFC normalizasyonu + ardışık boşlukların teke indirilmesi + büyük/küçük harf duyarsızlığı. Böylece `"  talep id "`, `"TARİH"` veya `"Talep  Tamamlama Saati"` gibi varyantlar doğru kolona eşlenir.

### 3.4 tir_kapasiteleri v2 uyarısı

Bu, veri katmanının en kritik noktasıdır ve doğrudan bir jüri düzeltmesidir. Yarışmanın ilk paylaşılan tır kapasitesi dosyasında **Balıkesir 0** ve **Tekirdağ 1** yazıyordu; oysa zorunlu kiralık filo her gün Balıkesir'e 1 tır, Tekirdağ'a 2 tır göndermek zorundaydı. Bu çelişki dört ayrı takım tarafından jüriye bildirildi (OptiVision Soru 1, ROTAI Soru 3, Budapeşte Soru 2, OpAI Soru 2) ve jüri cevabı net oldu:

> **Cevap:** Tır kapasitelerinin buna uygun güncellenmesi gerekmektedir. Yeni tır kapasitelerini paylaşacağız.

Teslim paketi **güncellenmiş sürümü**, yani `datas/tir_kapasiteleri v2.xlsx` dosyasını kullanır: Balıkesir 0 → **1**, Tekirdağ 1 → **2**. Eski sürüm kullanılırsa plan tanım gereği ihlalli olur.

Güncellenmiş kapasiteler: Kocaeli 12, Mersin 11, Eskişehir 10, İstanbul 10, Erzincan 5, Mardin 5, Şanlıurfa 5, Manisa 4, Yalova 4, Tekirdağ 2, Balıkesir 1; Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas ve Zonguldak **sıfır**. Toplam 69 günlük tır ziyareti. Kapasitesi sıfır olan yedi merkeze hiçbir tır — kiralık dahil — gidemez; bu, çözümün zincirlerde Tır kullanmama kararının arkasındaki fizikî gerçektir.

---

## 4. Talep Tahmini Modeli

> **Önemli not — final aşamasında tahmin çalıştırılmaz.** Teknik Gereksinimler Bölüm 2 açıkça şunu söyler: *"Final değerlendirmesi sırasında talep tahmini (forecasting) modülünüz çalıştırılmayacaktır... main.py, sadece optimizasyon adımını çalıştırmalıdır — kendi tahmin modülünüzü çağırmamalıdır."* Teslim paketinde `main.py` bu kurala uyar: `src.forecast`, `src.backtest` ve `src.frozen_backtest` modüllerine import grafiğinden hiçbir yoldan ulaşılamaz. Buna rağmen bu bölüm yazılmıştır, çünkü (a) jüri önceki aşamayı da değerlendirmektedir ve (b) final koşusunun yedek girdisi olan `data/one_week_backtest.xlsx` tam olarak bu modülün çıktısıdır.

### 4.1 Model tek satırda

```
tahmin(hücre) = DOW_medyan_tabanı(OD, slot, haftagünü; k=4, tatil ve ay sonları hariç)
                x takvim_çarpanı(gün)
```

Taban model, her (çıkış, varış, slot, haftagünü) hücresi için **hedef tarihten kesin önce** gelen son dört gözlemin **medyanıdır**. Medyan seçilmesinin nedeni ortalamanın tek bir kampanya veya bayram gününden kalıcı olarak bozulmasıdır; k = 4 seçilmesinin nedeni mevsimsel kayma ile örneklem gürültüsü arasındaki dengedir.

### 4.2 Tam grid ve veri temizleme

Talep verisi seyrektir: bir (tarih, OD, slot) hücresi veride görünmüyorsa o hücrede talep **yoktur**, yani desi sıfırdır. `src/backtest.py` içindeki `build_grid` bunu somutlaştırır — OD çiftleri x {09:00, 17:00} x gün aralığı kartezyen çarpımını kurar, gerçek talebi birleştirir ve görünmeyen hücreyi sıfırla doldurur. Bu adım olmadan sıfırlar hiç modellenmez ve tahmin sistematik olarak yukarı sapar.

Eğitim verisinden **23 tarih** dışlanır: 15 resmî tatil/bayram günü (1 Ocak; 19–22 Mart Ramazan; 23 Nisan; 1 Mayıs; 19 Mayıs; 25–31 Mayıs Kurban) ve Ocak–Mayıs aylarının son iki günü. İki liste 30–31 Mayıs'ta kesiştiği için kümenin gerçek boyu 25 değil 23'tür.

| Seviye | Toplam | Kullanılan | Elenen |
|---|---:|---:|---:|
| Eğitim geçmişi (grid hücresi) | 103.462 | 90.168 | 13.294 (%12,8) |
| Tahmin dosyası (satır) | 4.046 | 2.925 optimizasyona | 1.121 (%27,7), desi = 0 |

İki nokta bilinçlidir. Birincisi, **dışlama yalnız eğitim verisine uygulanır**; hedef günler asla elenmez. Bu yüzden dışlama listesi bilerek yalnız Ocak–Mayıs'ı kapsar — Haziran'ın son iki günü (29–30 Haziran) tahmin ufkunun içindedir. İkincisi, **sıfır satırlar teslim edilen dosyada kalır**; jüri OpAI Soru 5'te *"tahmin edilen desi çok düşükse o satır çıkarılabilir mi?"* sorusuna **"Sunulmalı"** cevabını vermiştir. Sıfır satırlar optimizasyona geçmez, çünkü sıfır desi için araç çıkarılmaz.

### 4.3 Veride gördüğümüz şey: ay sonu çöküşü

Verinin en güçlü tek olgusu budur. Ayın son günü **beş ayın beşinde de istisnasız** normal bir günün yaklaşık %2'sine iner; en düşük gözlem 2.010 desidir. Bu tek gözlem tahmin puanını domine edebilecek büyüklüktedir: 30 Haziran'ı sıradan bir salı sayan bir model o gün tek başına yaklaşık 1,1 milyon desi hata üretir — ve **30 Haziran tahmin ufkunun tam ortasındadır**.

### 4.4 Takvim katmanı: üç ölçülmüş çarpan

Her gün dört rolden birine atanır (`src/forecast.py` içindeki `_calendar_role`) ve rol Python'un takvim modülünden türetilir; kodda gömülü tek bir tarih yoktur.

| Takvim rolü | Çarpan | Ham oranların medyanı |
|---|---:|---|
| Ay sonundan bir önceki gün | 0,6752 | 0,879 / 0,766 / 0,648 / 0,675 / 0,059 |
| Ayın son günü | **0,0198** | 0,0198 / 0,0254 / 0,0194 / 0,0088 / 0,0210 |
| Ayın ilk günü (toparlanma) | 1,2072 | 2,929 / 1,207 / 1,056 / 0,090 / 1,574 |
| Normal gün | 1,0000 | — |

Her çarpan, geçmişteki beş ay sonu olayının **oran medyanıdır**: o günün gerçekleşen toplam hacmi bölü aynı hücreler için sızıntısız hesaplanan DOW-medyan tabanının toplamı. Tabana bölmek, ay sonu etkisini haftagünü etkisinden **ayırır** — 30 Haziran bir salıdır, taban zaten salı hacmini yakalar, çarpan yalnızca "ay sonu olma" bilgisini ekler.

Medyanın önemi "ayın ilk günü" satırında görülür: ham oranlar arasında 1 Şubat'ın 2,929'u ve 1 Mayıs'ın (resmî tatil) 0,090'ı vardır. Medyan ikisini de dışarıda bırakıp 1,207 verir; ortalama alınsaydı çarpan 1,371 çıkardı. Rol başına en az iki geçerli oran yoksa güvenli **1,0** değerine düşülür — tek bir gözlemden çarpan uydurulmaz.

### 4.5 Üç sızıntı (leakage) koruması

Tahmin modelinin en kolay bozulacağı yer, gelecekteki gerçekleşen değerin modele sızmasıdır. Üç bağımsız koruma vardır:

1. **Çarpan kalibrasyonunda:** her olay günü için taban yalnızca `tarih < hedef gün` verisiyle hesaplanır. Bir test, taban fonksiyonunu bir "sızıntı bekçisi" ile değiştirip her çağrıda bu koşulu doğrular.
2. **Tabanda:** olay günlerinin kendisi taban hesabından dışlanır.
3. **Yapısal olarak:** `forecast_horizon`, kendisine verilen geçmiş veride tahmin başlangıcı veya sonrasına ait **tek bir satır** bulursa çalışmayı reddeder ve hata fırlatır. Sessizce sızıntı yapmaz.

Raporlanan başarım rakamları ayrıca **dondurulmuş (frozen)** bir çerçeveyle üretilir: eğitim verisi tek bir kesim tarihinde kesilir, OD evreni bile yalnız o eğitim geçmişinden türetilir (ufukta ilk kez görünen bir OD çifti evrene giremez) ve modele gerçekleşen etiketi bulunmayan hedef bilgisi verilir. Bu, gerçek yarışma koşulunun aynısıdır.

### 4.6 Frozen backtest sonuçları

| Pencere | Naive (geçen hafta) | DOW medyanı | **Bizim model** |
|---|---:|---:|---:|
| Normal hafta · 15–21 Haziran | 0,2592 | 0,2174 | **0,2174** |
| Ay sonu haftası · 30 Mart – 5 Nisan | 0,6972 | 0,5328 | **0,4464** |

Ölçüt WMAPE'dir (hacim ağırlıklı mutlak yüzde hata). Normal haftada bizim model ile düz DOW medyanı **birebir aynıdır**, çünkü o pencerede takvim rolü olan gün yoktur ve çarpan 1,0'dır — model gereksiz yere müdahale etmez. Ay sonu haftasında ise hata 0,5328'den 0,4464'e iner: takvim katmanı hatayı **%16,2** azaltır ve naive referansa göre **%36,0** iyileştirme sağlar. Yani katman zarar vermeden, yalnız gerektiğinde kazandırır.

### 4.7 Bilinçli olarak yapmadıklarımız

Aşağıdaki tekniklerin hiçbiri uygulanmamıştır ve bu bir eksiklik değil, gerekçelendirilmiş bir karardır:

- Aykırı değer (outlier) temizleme veya winsorize
- Logaritmik dönüşüm
- Ölçekleme / normalizasyon
- Yumuşatma (smoothing) veya ara değerleme (interpolation)
- Trend / mevsim ayrıştırma
- Harici makine öğrenmesi kütüphanesi — projede **scikit-learn, statsmodels, Prophet veya ARIMA yoktur**; `requirements.txt` yalnız `pandas` ve `openpyxl` içerir

Gerekçe: veri tam, düzenli ve **tek bir güçlü mevsimsellik (haftagünü)** ile **tek bir takvim olayı (ay sonu)** tarafından yönetiliyor. Robust medyan bu ikisini yakalıyor; fazlası doğrulanamayan karmaşıklık olurdu. Aykırı değer temizlemenin özel bir sakıncası da vardır: bu veri setindeki en büyük "aykırı" değerler tam olarak modellemek istediğimiz sinyalin kendisidir (ay sonu çöküşleri). Onları temizlemek, öğrenilecek olguyu silmek olurdu.

### 4.8 Çıktı ve kimlik ataması

Çıktı, 289 aktif OD x 7 gün x 2 slot = **4.046 satır**, toplam **4.977.975 desi**, 1.121'i sıfırdır. Günlük dağılım takvim katmanının imzasını taşır:

| Gün | Tahmin (desi) | Aynı haftagünü ortalaması | Oran |
|---|---:|---:|---:|
| 29 Haziran (Pazartesi) | 1.161.736 | 1.622.264 | 0,72 |
| **30 Haziran (Salı)** | **24.040** | 1.110.177 | **0,02** |
| 1 Temmuz (Çarşamba) | 1.305.721 | 1.016.846 | 1,28 |
| 2 Temmuz (Perşembe) | 978.038 | 953.021 | 1,03 |
| 3 Temmuz (Cuma) | 859.444 | 897.773 | 0,96 |
| 4 Temmuz (Cumartesi) | 591.542 | 619.547 | 0,96 |
| 5 Temmuz (Pazar) | 57.454 | 86.435 | 0,66 |

Fark üç günde toplanır: 29 Haziran bastırılmış, 30 Haziran çökmüş, 1 Temmuz toparlanmıştır. Kalan dört günde takvim çarpanı 1,0'dır; oranlardaki sapma yalnız haftagünü ortalamasının kendi gürültüsüdür (2–4 Temmuz'da 0,96–1,03; hacmi zaten en düşük gün olan 5 Temmuz Pazar'da 0,66).

Talep kimlikleri `D00001`, `D00002`, ... biçiminde, `(tarih, çıkış, varış, slot)` anahtarıyla **kararlı (stable) sıralama** yapıldıktan sonra atanır. Kararlı sıralama, girdi satır sırasından bağımsız aynı kimlik dizisini garanti eder. 99.999 satırdan fazla girdi gelirse sessiz kimlik çakışması yerine açık bir hata fırlatılır. Yuvarlama `round()` ile yapılır; bu "yarımı çifte yuvarla" davranışıdır ve 4.046 satırda tek yönlü sistematik sapma birikmesini önler.

---

## 5. Optimizasyon Merdiveni

### 5.1 Merdivenin mantığı ve ortak kabul kuralı

Dört aşamanın hepsi aynı sözleşmeyi paylaşır:

1. Aşama, önceki aşamanın **hakemden geçmiş** planını girdi alır.
2. Kendi arama uzayını **deterministik** (belirlenimci) biçimde tarar; hiçbir yerde rastgelelik, zaman damgası veya sözlük sırası bağımlılığı yoktur.
3. Aday plan tamamen kurulur, dakika çizelgesine çevrilir, şema doğrulamasından geçirilir ve **bağımsız hakem simülatörüyle** sıfırdan yeniden fiyatlandırılır.
4. Kabul kuralı üç koşulun hepsini ister: **temel planda 0 ihlal, aday planda 0 ihlal ve hakem toplamlarından hesaplanan tasarruf ≥ 1,00 TL.** Sınır dahildir: tam 1,00 TL kabul edilir, 0,999999 TL reddedilir.
5. Kabul edilmezse `selected = baseline` olur; yani bir aşama plana **asla zarar veremez**.

Bu tasarımın somut faydası ölçülmüştür: %250 hacimli sentetik bir veri setinde Stage 0 planı 69 elleçleme ihlaliyle üretildi (ihlallerin tamamı talebin fizikî kapasiteyi aşmasından kaynaklanıyordu), Stage 1 adayı bu nedenle **doğru biçimde reddedildi**, temel plan korundu, süreç çökmedi ve şemaya birebir uyan bir plan yazıldı.

### 5.2 Stage 0 — Temel plan üretimi

#### 5.2.1 Hangi problemi çözüyor

Stage 0'ın işi "iyi" bir plan değil, **doğru** bir plan üretmektir: her talep tam olarak teslim edilmiş, hiçbir kapasite aşılmamış, tüm zorunlu kiralık seferler çıkarılmış olmalıdır. Kasten "doğru ama saf" bir tabandır — yalnız aynı hat üzerinde konsolide eder, farklı hatların yüklerini birleştirmez. Bu yüzden spot doluluğu yalnız %48,02'dir ve bu düşüklük bir kusur değil, sonraki üç aşamanın kullanacağı fırsattır.

#### 5.2.2 Algoritma adım adım

**Adım 1 — Ufkun türetilmesi.** Planlama günleri girdi dosyasının `Tarih` kolonundan türetilir; en küçük ve en büyük tarih arasındaki tüm günler kesintisiz döner. Kodda gömülü takvim tarihi yoktur (Teknik Gereksinimler Bölüm 7).

**Adım 2 — Takvimin kurulması.** Ufka **2 boşaltma günü (flush day)** eklenir. Bu, jürinin *"5 temmuzda tahminlenen talepleri 7 temmuzda teslim edebilirsiniz"* cevabının doğrudan uygulamasıdır. 7 günlük ufuk 9 güne çıkar.

**Adım 3 — Tır bütçe takvimi ve zorunlu kiralıkların ön rezervasyonu.** Her (merkez, gün) için tır ziyaret bütçesi kurulur ve **planlama başlamadan önce** her kiralık tırın çıkış ve varış ziyareti bu bütçeden düşülür. Kalkış anı gerçek yüke değil **tam kapasiteye** göre sabitlenir (Tır için 17:00 + 224 dakika = 20:44), böylece varış **günü** yükten bağımsız olur ve rezervasyon birebir doğru kalır. Yükleme başlangıcı kalkıştan geriye doğru hesaplandığı için araç boş bekletilmez ve fazladan maliyet doğmaz.

Bu adımın gerekliliği karşı-olguyla ölçülmüştür: rezervasyon kaldırılırsa plan **12 tır kapasitesi ihlali** üretir (Balıkesir 2>1, Tekirdağ 4>2, Manisa 5>4 dahil). Rezervasyonla ihlal sıfırdır.

**Adım 4 — Günlük döngü.** Her ufuk günü için sırasıyla: o günün 09:00 ve 17:00 talepleri havuza eklenir; kiralık filo doldurulur; aday plan kümesi üretilir; kıt tır ziyaretleri dağıtılır; seçilen bacaklar yazılır ve taşınamayan yük havuzda kalır. Sıra kritiktir: **kiralık her zaman spottan önce doldurulur**, çünkü kiralık araç zaten yola çıkacaktır ve marjinal desi maliyeti çok düşüktür.

**Adım 5 — Kiralık doldurma (batık maliyet mantığı).** Hattın havuzu `(son teslim anı, hazır olma anı, parça kimliği)` sırasına dizilir — yani **en acil yük önce** — ve araçlar ilk-uyan (first-fit) mantığıyla doldurulur. Sığmayan parça bölünür. Mantığın gerekçesi ölçülmüştür: kiralık aracın km bileşeni ve seyir saati batıktır (sunk), yalnız elleçleme süresi yükle değişir. Marjinal maliyet kiralık Tır'da 0,09722, kiralık Kamyon'da 0,06944 TL/desidir.

**Adım 6 — Aday plan kümesinin üretimi.** Havuzdaki her dolu hat için, o hat-gününde spot Tır seçeneğinin üretilip üretilmeyeceğine karar verilir. Eşik `TIR_MIN_DESI = 12.000` desidir ve keyfî değildir: bu değer Kamyon kapasitesine eşittir, yani altındaki her yük tek bir Kamyona sığar. 306 hattın tamamında ve beş farklı desi değeri için tek Tır maliyeti tek Kamyon maliyetiyle karşılaştırıldı — **1.530 kontrolün hiçbirinde Tır ucuz çıkmadı**. Eşiğin üstünde, 12.000 < desi ≤ 22.400 aralığında ise tek Tır iki Kamyondan 1.224 kontrolün 1.220'sinde ucuzdur.

**Adım 7 — Araç karması tam sayımı.** Bir (hat, gün) için tüm araç sayısı karmaları dört iç içe döngüyle taranır. Üst sınırlar: Tır = min(⌈desi/22.400⌉+1, 3), Kamyon = ⌈desi/12.000⌉+1, Hafif Kamyon = 2 (sabit), Kamyonet = 1 (sabit). Sabit tavanların gerekçesi araç merdivenidir: Hafif Kamyon Kamyon tarafından domine edilir, Kamyonet ise yalnız "kuyruk" rolündedir — ölçüm bunu doğrular, 1.143 spot bacağın 950'si Kamyonet'tir ve ortalama doluluğu %40,15'tir, yani gerçekten küçük artıkları toplar.

Sayım üst sınırlarına eklenen +1 güvenlik payı (`COUNT_SLACK`) bilinçlidir: yükü daha çok araca bölmek elleçleme süresini kısaltıp SLA cezasını düşürebilir, bu seçenek açık tutulur.

**Adım 8 — İki budama (pruning) kuralı.** Her aday önce iki hızlı elemeden geçer: (a) toplam kapasite, yükün 5.600 desiden fazlasını açıkta bırakıyorsa aday elenir (erteleme sınırı zaten aşılacaktır); (b) en küçük aracı çıkarmak yükü hâlâ tamamen karşılıyorsa aday domine sayılır. İkinci kural araç maliyeti üzerinde kesin baskındır ama SLA cezası teorik olarak farklılaşabilir; bu yönüyle tam ispatlı değil, maliyet tabanlı bir budamadır. Elenen adayın alt kümesi zaten ayrı bir kombinasyon olarak numaralandırıldığı için arama kör kalmaz.

**Adım 9 — Kesin fiyatlandırma.** Budamayı geçen aday gerçekten doldurulur ve her dolu araç için tam zaman çizelgesi kurulur: `load_start = max(parçaların hazır olma anı)` → `dep = load_start + elleçleme` → `arr = dep + seyir` → `unload_end = arr + elleçleme`. Filo **saatlik ücrete göre artan** sırayla doldurulur (Kamyonet 197,92 < Kamyon 318,25 < Hafif Kamyon 364,58 < Tır 487,50), yani en acil yük hem en ucuz hem ortalama en hızlı araca biner.

**Adım 10 — Erteleme (carry-over) kararı.** Şartname EK KISIT 2 bunu açıkça serbest bırakır: *"Eğer düşük talep sebebiyle bazı gönderileri bekletmek maliyet açısından daha faydalıysa gönderileri bekletebilirsiniz."* Erteleme keyfî değildir, **fiyatlandırılır**: her ertelenen parça için (a) yarınki dalgayla varış varsayılarak gerçek SLA cezası ve (b) yarınki taşıma bedeli toplanır. (b) iki farklı fiyatla hesaplanır — yarın o hatta kendi talebi varsa yalnız marjinal elleçleme payı (0,12 TL/desi), yoksa o desiyi yarın **tek başına** taşımanın en ucuz araç maliyeti. Bu ikinci fiyat "boş güne ertelemek aracı sadece ileri atar" gerçeğini yakalar ve ölçülen çalışmada 137 kez devreye girmiştir.

Erteleme üç sert kuralla sınırlıdır: hat-gün başına en fazla **5.600 desi** (Kamyonet kapasitesi — ertelenen yükün yarın tek küçük araca sığacağı garantisi), boşaltma gününde tamamen **yasak**, ve bir parça en fazla **bir kez** ertelenebilir.

**Adım 11 — Kazanan adayın seçimi.** Amaç fonksiyonu `araç maliyeti + SLA cezası + erteleme maliyeti`; yeni aday ancak **kesin olarak** daha ucuzsa kazanır. Beraberlikte döngü sırasındaki ilk, yani en düşük sayımlı aday korunur — bu determinizmi garanti eder.

**Adım 12 — Tır ziyaretlerinin dağıtımı.** Kıt tır bütçesi **azalan getiriyle (greedy marginal gain)** dağıtılır: her turda tüm hatlar taranır, "bir tır daha eklemenin kazancı" hesaplanır, bütçe uygunluğu kesin kalkış/varış tarihleriyle kontrol edilir ve tur içindeki **en yüksek kazançlı tek hat** kabul edilir; sonra baştan taranır. İlk gelen almaz, en değerli alır.

**Adım 13 — Boşaltma günleri.** Ufuk bittikten sonra kiralık filo çıkmaya devam eder ve kalan yük gün başından itibaren, ertelemesiz taşınır.

**Adım 14 — Kapanış doğrulaması.** Fonksiyon sonunda havuzun tamamen boşaldığı `assert leftover == 0` ile doğrulanır. Bu, "her talep tam teslim edilir" garantisinin kod içindeki tek satırlık ispatıdır; hakem simülatörü aynı garantiyi bağımsız olarak teyit eder.

**Adım 15 — Elleçleme kapasitesi düzeltmesi.** Stage 0 modülleri elleçleme kapasitesini **modellemez**; bu bilinçli bir katman ayrımıdır. Kısıt `src/schedule.py` içindeki `_fix_handling` tarafından uygulanır: aşan (merkez, gün) çiftlerinde aşımı gerçekten besleyen **en küçük** spot (Tır olmayan, zincirsiz) bacak bütün olarak ertesi günün 00:00'ına kaydırılır. Kullanım süresi korunduğu için araç maliyeti değişmez, yalnız SLA cezası artar — bu, "kapasite ihlali kabul edilemez, gecikme fiyatlanabilir" şartname mantığına birebir uyar.

Ölçülmüş etki: **11 kaydırma**, hepsi Denizli'nin 02.07.2026 aşımından kaynaklanır (kapasite 36.868,61 — 18 merkezin en küçüğü); araç maliyeti değişmedi (15.460.592,57 TL), SLA cezası 1.017.967,60 TL'den 1.020.367,20 TL'ye çıktı (**+2.399,60 TL**). Düzeltme kapatıldığında hakem 1 elleçleme ihlali yazar; açıkken **sıfır** ihlal vardır. Yani sıfır ihlal, toplam maliyetin yalnız on binde 1,5'i karşılığında alınmıştır.

#### 5.2.3 Arama uzayı ve ölçülmüş sonuç

| Ölçüm | Değer |
|---|---:|
| Taranan hat-gün | 1.751 |
| Tır uygunluğu bulunan hat-gün | 45 |
| Toplam plan çağrısı | 1.886 |
| Numaralandırılan aday karma | 39.598 |
| Budamadan sonra fiyatlandırılan aday | 6.847 (%17,3) |
| Tekil araç fiyatlama çağrısı | 9.007 |
| Çalışma süresi | 0,46 sn |
| Üretilen bacak | 1.269 (126 kiralık + 1.143 spot) |
| Plan satırı | 3.167 |
| **Toplam maliyet** | **16.480.959,77 TL**, 0 ihlal |

Bir hat-gün için aday sayısı en az 17, en çok 143, ortalama 21,0'dır.

#### 5.2.4 Ertelemenin ölçülmüş değeri

Erteleme mekanizması tamamen kapatıldığında (`MAX_CARRY_DESI = 0`) Stage 0 çıktısı 1.943 bacak ve **24.954.608,68 TL** olur; SLA cezası sıfırdır. Erteleme açıkken 1.269 bacak ve 16.480.959,77 TL. Yani **1.020.367,20 TL SLA cezası ödeyerek 9.494.016,11 TL araç maliyeti tasarruf ediliyor**; net kazanç **8.473.648,91 TL (−%33,96)**. Her iki koşuda da ihlal sıfırdır.

### 5.3 Stage 1 — Aynı-hat onarımı

#### 5.3.1 Hangi problemi çözüyor

Stage 0 her (hat, gün) için ayrı ayrı karar verir. Bunun yan etkisi, aynı hat üzerinde farklı zamanlarda kalkan ve ikisi de yarı boş olan araçların ortaya çıkmasıdır. Stage 1 bu artığı toplar.

#### 5.3.2 Algoritma adım adım

**Adım 1 — Aşama sınırı ve sıranın önemi.** Onarım, ham Stage 0 çıktısı üzerinde değil, **elleçleme düzeltmesinden geçmiş** temel plan üzerinde çalışır. Bu bir stil tercihi değil, çalışma koşuludur ve ölçülmüştür: ham plana uygulandığında 535 denemenin **535'i de** reddedilir ve 0 hamle üretilir, çünkü plan zaten aşımlı olduğu için her deneme defterde düşer. Düzeltilmiş tabanla aynı kod **177 hamle** üretir.

**Adım 2 — Kanonik sıralama ve determinizm.** Bacak listesinin tamamı tek bir derin kopya (deepcopy) ile kopyalanır ve 12 alanlı anlamsal bir anahtarla sıralanır. Anahtar maliyet, ceza, araç kimliği ve talep kimliği alanlarını **dışarıda bırakır**; yalnız semantiğe bakar. Sonuç: girdi permütasyonu sonucu değiştiremez. Dört bacaklı bir planın **24 permütasyonunun tamamı** aynı imzayı ve aynı metrikleri üretir.

**Adım 3 — Uygunluk filtreleri.** Bir bacak ancak dört koşulu birden sağlarsa "doğrudan" sayılır: dolu olmalı, zincirin parçası olmamalı, taşıdığı her parçanın hedefi bacağın hedefine eşit olmalı, ve her parça tüm planda tam olarak bir kez geçmelidir. Verici (donor) ek olarak **Spot** olmalı ve **Tır olmamalıdır** — kiralık zorunlu olarak çıkacağı için silinemez, spot Tır ise hem kıt tır bütçesini tutar hem zaten en verimli araçtır.

**Adım 4 — Verici sıralaması.** Vericiler doluluk oranına göre **artan** sırada denenir; oran kesin kesir aritmetiğiyle (Fraction) hesaplanır, kayan nokta yuvarlaması yoktur. Yani en boş — dolayısıyla km ücretini en verimsiz kullanan — araç ilk elden çıkarılmaya çalışılır.

**Adım 5 — Alıcı taraması.** Her verici için plandaki tüm bacaklar taranır ve dört filtre uygulanır: alıcı vericinin kendisi olamaz, doğrudan olmalı, Spot veya Kiralık olmalı ve **(çıkış, varış) çifti vericininkiyle birebir aynı** olmalıdır. Aynı-hat kısıtı bu aşamanın hem adını hem güvenliğini verir: hiçbir yük hattını değiştirmez, hiçbir araç rotasından sapmaz.

**Adım 6 — Alıcının yeniden çizelgelenmesi.** Vericinin **tüm** kalemleri alıcıya olduğu gibi eklenir; talep **hiç bölünmez**. Elleçleme süresi birleşik toplamdan tek kez hesaplanır ve hem yükleme hem indirme için aynen kullanılır (şartname EK KISIT 1). Spot alıcıda çıpa yükleme başlangıcıdır; **kiralık alıcıda çıpa kalkıştır** — kalkış korunur, yükleme daha erken başlatılır. Yeniden hesaplanan kalkışın **tarihi** değişirse öneri tamamen reddedilir: kiralık araç gün içinde saatini kaydırabilir, ama gününü değiştiremez (Q&A Astra: *"Kiralık aracın çıkış saatini o gün içinde olacak şekilde belirleyiniz."*).

**Adım 7 — Yerel maliyet farkı.** Fark üç bacağın **tam** maliyeti (araç + SLA) üzerinden Decimal aritmetiğiyle hesaplanır ve **kesin negatif** olmalıdır. Sıfır deltalı "maliyet-nötr" hamleler reddedilir. Tasarrufun ana kaynağı vericinin km ücretinin tamamen ortadan kalkmasıdır.

**Adım 8 — Tam defter denemesi.** Maliyet kapısını geçen her öneri için, hamle uygulanmış planın **tamamı** kurulur ve elleçleme ile tır defterleri **sıfırdan** yeniden hesaplanır. Yalnız değişen iki bacak değil, plandaki 1.200'den fazla bacağın hepsi defterlenir — çünkü kapasiteler (merkez, gün) düzeyinde küresel kaynaklardır ve yerel bir hamle uzaktaki bir merkezi taşırabilir.

**Adım 9 — Aday seçimi.** Hayatta kalan adaylardan **en negatif** deltalı olan seçilir; delta eşitliğinde alıcının kanonik anahtarı karar verir. Uygulandığında verici bacak plandan silinir ve alıcı güncellenir. Bir alıcı birden çok verici kabul edebilir, ama yük almış bir bacak sonradan verici olamaz — bu, salınımı (oscillation) engeller ve tek geçişin sonlanmasını garanti eder.

#### 5.3.3 Arama uzayı ve ölçülmüş sonuç

| Ölçüm | Değer |
|---|---:|
| Verici havuzu | 1.134 (1.143 spot bacaktan 9 spot Tır çıkarılarak), 282 farklı hatta |
| Değerlendirilen verici | 1.003 (131'i daha önce alıcı olduğu için atlandı) |
| İncelenen (verici, alıcı) çifti | 4.035 — verici başına ortalama 4,02 |
| Maliyet/kapasite/gün kapılarında düşen | 3.792 (%94,0) |
| Tam defter denemesine gelen | 243 |
| Defterde reddedilen | 4 |
| Geçerli aday | 239 |
| **Kabul edilen hamle** | **177** |
| Taşınan parça / desi | 394 / 59.852 |
| Silinen spot araç | 177 (1.269 → 1.092 bacak) |
| **Küresel tasarruf** | **1.800.774,93 TL** |
| Çalışma süresi | 12,6–13,4 sn |

Kabul edilen hamle başına ortalama tasarruf 10.173,87 TL'dir. Araç karması değişimi yalnız Kamyonet'te olur: 950 → 773; Tır 99, Kamyon 196, Hafif Kamyon 24 sabit kalır — yani silinen 177 aracın hepsi Kamyonet'tir.

SLA cezası bu aşamada 1.020.367,20 TL'den 2.169.783,60 TL'ye **çıkar**. Bu bilinçli bir takastır: araç maliyeti 2.950.191,33 TL düşerken ceza 1.149.416,40 TL artar, net **−1.800.774,93 TL**. Jüri Budapeşte Soru 4'te minimum doluluk kuralının bu aşamada bulunmadığını ve *"gönderiler gecikirse SLA cezası ödenmesi gerekmektedir"* dediği için bu saf toplam maliyet minimizasyonudur; SLA gecikmesi hakemde bir **ihlal** değil, fiyatlanmış bir maliyet kalemidir.

### 5.4 Stage 2 — Milk-run zincirleme

#### 5.4.1 Hangi problemi çözüyor

Stage 1'den sonra hâlâ 966 spot araç vardır ve bunların 296'sının doluluğu %30'un altındadır. Ama bu araçlar **farklı hatlara** gitmektedir; aynı hatta birleştirilecek eşleri yoktur. Stage 2 farklı bir eksende birleştirir: **aynı çıkış merkezinden, tam olarak aynı yükleme anında kalkan 2–4 ayrı aracı tek fiziksel araca zincirler.** Yük çıkışta bir kez yüklenir, her durakta yalnız o durağa ait desi iner, gemide kalan yük ara merkezde **hiç elleçlenmez**.

Kuralın dayanağı açıktır:

> **Q&A Soru 11.1 (OpAI):** *"Bir aracın tek seferde birden fazla transfer merkezine uğrayıp sırayla yük bırakması mümkün mü?"* — **Cevap: "Spot araçlar için evet mümkündür fakat kiralık araçlar için uğrama mümkün değildir."**

> **Q&A Soru 3 (NEURON-LOG):** *"...toplam sefer sayısı için herhangi bir üst sınır bulunmakta mıdır?"* — **Cevap: "Evet kısıtlamalar dikkate alınarak sınırsız sefer yapabilirsiniz."**

Şartnamenin ÇÖZÜM bölümü (Taşıma planı formatını anlatan sayfa) ayrıca *"Kullanacağınız araçlara birçok farklı transfer merkezine gidecek yükleri yükleyebilirsiniz"* der; HİB LOGİ Soru 4'ün cevabı da aynıdır: *"Bir araca farklı yerlere gidecek gönderileri yükleyebilirsiniz."* Her iki resmî PDF ve jüri mesajı iki bağımsız metin çıkarıcıyla tarandı: **durak sayısına hiçbir kural sınırı yoktur**. `azami` ve `en çok` kelimeleri hiç geçmez; `maksimum` üç kez geçer ve üçü de elleçleme veya tır **kapasitesi** hakkındadır. `uğrama` yasağı beş ayrı yerde geçer ve **her seferinde yalnız kiralık araçlara** yöneliktir.

#### 5.4.2 Neden konsolidasyon değil, milk-run

Bu ayrım çözümün en değerli tasarım kararlarından biridir. **Konsolidasyon**, yükün bir ara merkezde indirilip başka bir araca yeniden yüklenmesidir; jüri HİB LOGİ Soru 6'da bunun bedelini söylemiştir: kapasiteden **2x** düşülür ve elleçleme iki kez yapılır. Üstelik jüri OptiVision Soru 2'de açıkça uyarır: *"Gerçek operasyonda da zamanla bir yarış olmaktadır bu nedenle bazı durumlarda konsolidasyon tercih edilememektedir. Konsolidasyon yapmak bir zorunluluk değildir."*

**Milk-run** ise yükü ara merkezde hiç indirmez; yük gemide kalır ve yalnız kendi durağında iner. Sonuç: ara merkezde **sıfır ek elleçleme kapasitesi**, **sıfır ek elleçleme süresi**, ve konsolidasyonun SLA baskısı hiç doğmaz. Bu yüzden aynı kazancı konsolidasyondan çok daha ucuza elde ederiz.

#### 5.4.3 Algoritma adım adım

**Adım 1 — Gruplama.** Uygun kaynak bacaklar `(çıkış merkezi, yükleme başlangıcı)` anahtarıyla gruplanır. Anahtar çok katıdır: iki bacağın aynı gruba girmesi için aynı merkezden ve **tam olarak aynı dakikada** yüklemeye başlaması gerekir; bir dakikalık fark bile grubu böler. Gerekçesi fizikseldir — zincir tek bir fiziksel araçtır ve o aracın tek bir yükleme anı vardır. Bekletme yapılsaydı bekleme süresi de araç maliyetine yazılırdı, bu yüzden modül hiç bekletmez.

**Adım 2 — Grup elemesi.** Bir grup en az iki üyeye ve en az iki **farklı varış merkezine** sahip değilse atlanır — aynı hatta giden iki araç zaten Stage 1'in konusudur.

**Adım 3 — Alt küme numaralandırması.** Her grupta tüm ikili kombinasyonlar ve k = 3, 4 için **tüm** alt kümeler üretilir. Örnekleme veya rastgeleleştirme yoktur.

**Adım 4 — Kapasite ön filtresi.** Toplam desi 12.000'i aşan alt küme hemen elenir. 12.000, en büyük Tır olmayan aracın (Kamyon) kapasitesidir; bu tavanı aşan bir alt küme hiçbir araç tipine sığmayacağından k! x 3 hesap hiç yapılmaz.

**Adım 5 — Durak sırası ve araç tipi taraması.** Her alt küme için **tüm durak sıraları** (k = 2 için 2, k = 3 için 6, k = 4 için 24 permütasyon) ve sığan **tüm Tır olmayan araç tipleri** (Kamyonet, Hafif Kamyon, Kamyon) fiyatlandırılır. Bir alt kümenin ürettiği aday sayısı en fazla k! x 3'tür. Ara hatlardan biri matriste yoksa o sıra atlanır — hat asla uydurulmaz.

**Tır neden zincirde yok?** Kural engeli yoktur; bu bilinçli ve belgelenmiş bir muhafazakârlıktır. Tır ziyaret kapasitesi kıt bir kaynaktır (yedi merkezde sıfır, Balıkesir 1, Tekirdağ 2) ve çok duraklı bir tır her durakta ayrı ziyaret tüketirdi. Bu kararın bedeli ayrıca ölçülmüştür (bkz. Bölüm 9.2): Tır'ı zincire katmak sonucu **18.100 TL daha kötü** yapıyor.

**Adım 6 — Zaman çizelgesi.** Saat yükleme başlangıcında başlar; çıkışta **tek bir birleşik yükleme** yapılır: `clock = load_start + handling(birleşik desi)`. Sonra her durak için `kalkış = clock`, `varış = kalkış + seyir`, `indirme bitişi = varış + handling(inen desi)`, `clock = indirme bitişi`. Yani bir sonraki bacak, önceki durağın indirme bitişinde kalkar; arada hiç bekleme yoktur.

**Adım 7 — Maliyet ve kabul.** Araç maliyeti **tek sürekli pencereden** hesaplanır ve rotanın tüm ara hatlarının km'leri toplanır. Her durakta o durakta inen kalemler için SLA cezası yazılır. Karşılaştırma tabanı, k kaynak bacağın mevcut çizelgesinden **yeniden hesaplanan** maliyet ve SLA toplamıdır — bacakların üzerinde yazılı maliyet alanlarına **hiç güvenilmez**. Bir test bu alanlara 99.999.999,25 gibi kasten bozuk değerler yazıp sonucun değişmediğini gösterir. Kabul için fark **kesin negatif** olmalıdır.

**Adım 8 — Küresel sıralama ve açgözlü (greedy) işleme.** Tüm gruplardan gelen adaylar tek listede beş bileşenli tam bir sıralamayla dizilir: en çok kazandıran önce; eşit tasarrufta **az duraklı** zincir yeğlenir; kalan üç bileşen tamamen anlamsaldır. Sonra çakışmayan adaylar sırayla işlenir — bir kaynak bacak daha kazançlı bir zincire gitmişse sonraki aday sessizce düşer.

**Adım 9 — Tam grafik doğrulaması.** Her aday, işlemeden önce **oluşacak tam grafik** üzerinde baştan doğrulanır: yük sürekliliği, segment başına araç kapasitesi, her parçanın yükleme anında hazır olması, elleçleme defteri (gece yarısı oransal bölme dahil) ve tır ziyaret defteri. Herhangi bir ihlal adayı düşürür ve **zincir kimliğini tüketmez** — reddedilen bir aday sonrakini engellemez.

**Adım 10 — Ufuk koruması.** Hiçbir zincir, temel plandaki yüklü bacakların **en geç indirme tarihini** aşamaz. Yani milk-run teslim ufkunu uzatmaz. Ölçüm bunu doğrular: son kargo teslimi hem Stage 1'de hem Stage 2'de 06.07.2026'dır.

#### 5.4.4 Arama uzayı

| Ölçüm | Değer |
|---|---:|
| Değerlendirilen grup | 93 |
| İkili kombinasyon | 5.426 |
| k ≥ 3 alt küme | 96.369 (k=3: 22.719 · k=4: 73.650) |
| Fiyatlandırılan varyant | 1.908.972 |
| **Kabul edilen zincir** | **227** |
| Zincir uzunluğu dağılımı | 2 durak: 127 · 3 durak: 28 · 4 durak: 72 |
| Değiştirilen kaynak araç | 626 |
| Birleştirilen parça / desi | 2.110 / 1.675.453 |
| Zincir araç türü karması | Kamyon 120 · Kamyonet 96 · Hafif Kamyon 11 |
| **Tasarruf** | **3.366.846,56 TL** |
| Çalışma süresi | yaklaşık 72 sn |

Kapasite süzgecinin etkisi ölçülmüştür — 12.000 desi tavanına sığan alt küme oranı k büyüdükçe hızla düşer: k = 2'de 5.426 alt kümenin 3.669'u (**%67,6**), k = 3'te 22.719'un 10.423'ü (**%45,9**), k = 4'te 73.650'nin 23.602'si (**%32,0**) sığar; geri kalanı fiyatlanmadan elenir. Fiyatlanan varyant sayısı bu üç satırın k! x 3 ile çarpımıdır: 22.014 + 187.614 + 1.699.344 = 1.908.972.

#### 5.4.5 Kritik ayrım: segment sayısı sabit kalır

Stage 2'de plan bacağı (segment) sayısı **1.092'de sabit kalır**, fiziksel araç sayısı ise 1.092'den 693'e iner. Zincir yeni bacak yaratmaz; *k* ayrı aracın işini **tek** fiziksel araca bindirir. Kimlik kontrolü: `1.092 − (626 − 227) = 693`, ve spot rota için `966 − (626 − 227) = 567`. Zincir uzunluğu dağılımı da tutarlıdır: `127 x 2 + 28 x 3 + 72 x 4 = 626`.

#### 5.4.6 Neden dört durak

`MAX_CHAIN_STOPS = 4` bir kural değil, ölçülmüş bir mühendislik takasıdır ve gerekçesi kodun içine yazılıdır:

| Durak tavanı | Hakem toplamı (TL) | Ek kazanç |
|---|---:|---:|
| 2 durak | 11.837.689,31 | — |
| 3 durak | 11.519.240,35 | −318.448,96 |
| **4 durak (kabul edilen)** | **11.313.338,29** | **−205.902,07** |
| 5 durak | uygulanabilir değil | — |

Beş duraklı zincir bu kaba kuvvet sayıcıyla uygulanabilir değildir: aktif gruplar C(n,5) = 254.992 alt küme barındırır ve her biri 120 durak sırası üzerinden fiyatlanmalıdır; deneme **13,5 dakika CPU ve 1,3 GB bellek** sonrasında sonuç vermemiştir. Ulaşmak için dal-sınır (branch-and-bound) türü budama gerekir ve bu bilinçli olarak kapsam dışı bırakılmıştır.

Dört duraklı zincirlerin üç duraklıları **yamyamlaştırdığını** (cannibalise) da not etmek gerekir: k = 3'te 122 üç duraklı zincir varken k = 4'te bu sayı 28'e iner ve 72 dört duraklı zincir doğar. Bu yüzden kabul edilen zincir sayısı 249'dan 227'ye düşerken değiştirilen kaynak araç sayısı 620'den 626'ya çıkar.

### 5.5 Stage 3 — Rota ortasında yük alma

#### 5.5.1 Hangi problemi çözüyor

Stage 2'ye kadar zincirlerimiz yalnız **indiriyordu**: araç çıkışta her şeyi yükler, her durakta bir kısmını bırakır, ara durakta yeni yük almaz. Jüri bunun tersini de açıkça serbest bırakır:

> **Q&A Soru 6 (HİB LOGİ):** *"...Aynı şekilde bir araçtan **x kadar yük indirilip y kadar yük yüklenirse** kapasiteden x+y kadar yük düşülür."*

Bu cümle bir aracın aynı merkezde hem indirip hem yükleyebildiğini söyler ve elleçleme aritmetiğini de verir. Yasak yalnız kiralıktadır.

#### 5.5.2 Tier A kısıtı

Alınan yükün varışı, rotanın **zaten uğradığı** bir durak olmak zorundadır. Böylece rota topolojisi hiç değişmez: durak dizisi, zincir uzunluğu, zincir kimliği ve araç tipi aynı kalır; `MAX_CHAIN_STOPS = 4` sınırı ve talep bölme sözleşmesi dokunulmadan durur. Kazanç, o yükü ayrı taşıyan aracın **tamamen ortadan kalkmasından** gelir.

Rotayı bir durak uzatan "Tier B" varyantı kapsam dışıdır; bağımsız bir ölçüm A+B için yaklaşık 146 bin TL görmüştür, yani ek yaklaşık 66 bin TL — ama 5 duraklı rota üretir ve ayrı bir karar konusudur.

#### 5.5.3 Algoritma adım adım

**Adım 1 — Hedef ve verici havuzları.** Hedef rota çok duraklı, tüm bacakları Spot ve tüm bacakları dolu olmalıdır. Verici (donör) rota tek bacaklı, dolu, Spot olmalı; taşıdığı **her** parçanın hedefi bacağın hedefine eşit olmalı (aktarma değil, doğrudan teslim), parça planda başka hiçbir bacakta geçmemeli ve parçanın **tamamı** taşınıyor olmalıdır. Bu son koşul kritiktir: Stage 3 hiçbir yeni talep bölmesi yaratmaz.

**Adım 2 — Yük alma durağı ve erişilebilir varış haritası.** Her hedef rota için, son segment hariç her durak bir yük alma noktası olabilir. Yük alma anı, aracın o merkezde **indirmeyi bitirdiği** andır. Sonraki duraklardan bir varış haritası kurulur ve bir varış birden fazla kez geçiyorsa **en erken** pozisyon kazanır — bu hem yükü en erken teslim eder hem ek yükü en az segmentte taşır.

**Adım 3 — Hazır olma kapısı.** Alınacak yükün herhangi bir parçası hub'da aracın indirmeyi bitirdiği anda hazır değilse aday hiç üretilmez. Model aracı hub'da boşta bekletmez, çünkü bekleme süresi de araç maliyetine dahildir (Q&A Soru 12).

**Adım 4 — Her segmentte kapasite.** Alınan yükün **bindiği andan indiği ana kadar geçtiği her segment** tek tek kontrol edilir. Sadece ilk segmenti kontrol etmek yeterli değildir, çünkü bağlayıcı segment pencerenin herhangi bir yerinde olabilir.

**Adım 5 — Rotanın yeniden zamanlanması.** Alınan yük yalnız (yük alma durağı, iniş durağı) yarı-açık aralığındaki segmentlerde gemidedir. Zaman çizelgesi baştan kurulur ve her segmentin yükleme başlangıcı, hakemin türeteceği değerle **tam eşit** olacak biçimde hesaplanır.

**Adım 6 — İki ayrı zaman damgası.** Bu, aşamanın en ince noktasıdır:

```
unload_end   = varış + handling(inen desi)        # SLA BU ana göre hesaplanır
depart_after = unload_end + handling(alınan desi) # sonraki segment BUNDAN kalkar
```

İnen kargo, indirmesi bittiği anda teslim edilmiştir; sonrasında başlayan **yükleme işlemi aracı geciktirir ama teslimatı geciktirmez**. Bu ayrımı karıştırmak sessiz bir hatadır ve prototipte **5.108,80 TL** fazla beyana yol açmıştır.

**Adım 7 — Kârlılık ve biriken muhafız.** Fark, yeni rota toplamı eksi (eski rota toplamı + vericinin tek başına maliyeti) olarak hesaplanır ve **kesin negatif** olmalıdır. Kabul edilen her aday, o ana kadar kabul edilmiş **tüm** hamleleri taşıyan bir deneme grafiği üzerinde defterlere karşı doğrulanır. Bu birikme şarttır: tek tek yasal iki hamle aynı günün elleçleme defterini birlikte taşırabilir. Bir regresyon testi tam bu durumu üretir ve iki hamleden birinin doğru biçimde reddedildiğini gösterir.

**Adım 8 — Çakışmasızlık.** Hedef rota başına en fazla bir yük alma, verici başına en fazla bir kabul yapılır. Bu bilinçli bir muhafazakârlıktır: her adayın fiyatı değişmemiş rota üzerinde hesaplandığı için ikinci bir yük alma, artık geçerli olmayan bir taban üzerinde fiyatlanmış olurdu.

#### 5.5.4 Arama uzayı ve ölçülmüş sonuç

| Ölçüm | Değer |
|---|---:|
| Hedef rota (çok duraklı, Spot) | 227 |
| Kiralık olduğu için atlanan rota | 126 |
| Verici havuzu (tek bacaklı, dolu, Spot) | 340 |
| İncelenen (rota-durak, verici) çifti | 135.660 |
| Kârlı aday | 56 |
| Defter reddi | 0 |
| **Çakışmasız kabul** | **28** |
| Silinen araç | 28 |
| Taşınan parça / desi | 82 / 65.754 |
| Hedef araç türü karması | Kamyon 11 · Kamyonet 17 |
| **Tasarruf** | **80.861,55 TL** |

Çift sayısının aritmetiği doğrulanabilir: 227 zincirin toplam (uzunluk − 1) değeri 399'dur ve 399 x 340 = 135.660.

Sonuç: fiziksel rota 693 → **665**, segment 1.092 → **1.064**, zincir sayısı 227'de sabit (topoloji değişmedi). Plan satırı 5.510 → 5.523 (+13); fark, alınan 82 parçadan 13'ünün bir ara duraktan geçmesindendir.

Bir yan kazanç da vardır: boşalt-yükle durağı tır defterinde **1** ziyaret tüketir, 2 değil — hakem, bacak *i*'nin varışıyla bacak *i+1*'in kalkışını aynı ziyaret numarası altına yazar.

### 5.6 Çizelgeleme katmanı ve beyan kolonları

Optimizasyon bacakları planlar; `src/schedule.py` onları 16 kolonluk beyan tablosuna çevirir. Sıra sabittir: kimlik atama → elleçleme onarımı → akış analizi → tır defteri → rota bütünlüğü → satır üretimi.

**Araç kimliği (V0001...)** fiziksel rota başına atanır, bacak başına değil. Bir zincirin tüm bacakları **tek** araç kimliği paylaşır — şartname *"araçlarınızın takip edilebilir olması gerekmektedir"* der ve bunun anlamı budur.

**Talep kimliği bölmesi (D00001-1, D00001-2)** yalnız bir talep gerçekten birden fazla fiziksel parçaya bölündüğünde üretilir. Tek parçalı talep temel kimliğini korur. Kritik ayrıntı: karşılaştırma değer eşitliğiyle değil **nesne kimliğiyle** yapılır, bu yüzden aynı desi ve aynı hedefe sahip iki ayrı parça yine ayrı sonek alır; buna karşılık milk-run boyunca aynı parça taşınıyorsa tüm bacaklarda **aynı** kimliği taşır. Ölçülen çıktıda 525 tireli satır vardır ve sonekler 1'den 5'e kadardır.

**Beyan kolonlarının üç ayrı kuralı** vardır ve üçü de hakem tarafından bağımsız denetlenir:

- **Yolculuk süresi** her satıra **tam** yazılır, desi payına bölünmez. Araç 60 dakika yol gider; 100 desilik kalem için 20, 200 desilik için 40 dakika gitmez.
- **Elleçleme süreleri** yalnız o satırın gerçekten yüklendiği veya indirildiği bacakta yazılır; gemide kalıp devam eden yük her iki kolonda da sıfır alır.
- **Araç maliyeti** fiziksel rotaya **yeni binen** yüklerin desi payına göre bölüştürülür; zincirin sonraki segmentlerinde payı sıfırdır, çünkü fiziksel araç bir kez ücretlendirilir.

Bu bölüşümün kayıpsız olduğu bir sezgi değil, **denetlenen bir sözleşmedir**: beyan edilen `Toplam maliyet` kolonunun toplamı, hakem simülatörünün bağımsız toplamına 0,01 TL toleransında eşit olmak zorundadır; uzlaşmazsa boru hattı durur. Teslim edilen dosyada ölçülen fark **0,0000 TL**'dir.

---

## 6. Hakem Simülatörü

### 6.1 Neden bağımsız ikinci uygulama

Bir optimizasyon projesinde en tehlikeli hata sınıfı, planlayıcının kendi hesabını kendisinin onaylamasıdır: modelde bir kural yanlış anlaşılmışsa, plan kendi içinde tutarlı ama gerçekte ihlalli çıkar ve hiçbir iç kontrol bunu yakalayamaz.

`src/simulator.py` bu riski yapısal olarak ortadan kaldırır. Planlayıcının hiçbir iç nesnesini görmez; yalnızca **16 kolonluk plan tablosunu, 6 kolonluk talep tablosunu ve statik referans veriyi** okur. Araç zaman çizelgesini, maliyeti ve SLA'yı sıfırdan kurar. Dolayısıyla optimizer ile hakem arasındaki **her uyuşmazlık gerçek bir hatadır** ve teslimden önce yakalanır.

Bağımlılık yönü de tek taraflıdır: hakem modülü, optimizasyon modüllerinin bağımlılık grafiğinin tamamen dışındadır.

### 6.2 On yedi kural

Hakemin denetlediği fiziksel kural kümesi belgelenmiştir:

| # | Kontrol |
|---|---|
| 1 | Bacak zinciri sürekliliği — bir bacağın çıkışı, öncekinin varışına eşit olmalı |
| 2 | Aynı bacakta tekrarlı talep kimliği |
| 3 | Araç kapasitesi aşımı |
| 4 | Hattın matriste var olması |
| 5 | Bir fiziksel araç boyunca araç tipi ve türü tutarlılığı |
| 6 | Yükleme, önceki işlem bitmeden başlayamaz |
| 7 | Yükleme, talep hazır olmadan başlayamaz |
| 8 | Rota, talebin tahmindeki çıkış merkezinden başlamalı |
| 9 | Araç değişimli aktarmada zamanlama — yeni yükleme, önceki indirme bitmeden başlayamaz |
| 10 | Teslim bütünlüğü — teslim edilen desi tahmin desisine eşit olmalı |
| 11 | SLA cezası — parça bazında, geciken desi x tam saat x 0,40 TL |
| 12 | Kiralık araç yalnız kendi rotasında |
| 13 | Kiralık araç günde en fazla bir bacak; gün başına benzersiz kimlik |
| 14 | Zorunlu kiralık sefer sayısı rota bazında birebir eşleşmeli |
| 15 | Elleçleme kapasitesi (merkez, gün) — gece yarısı oransal bölmeyle |
| 16 | Tır ziyaret kapasitesi (merkez, gün) |
| 17 | Plandaki her talep kimliği tahmin dosyasında bulunmalı |

Kod bugün bu tablodan daha fazlasını yapar: `src/simulator.py` içinde 29, defter modülü `src/ledger.py` içinde 4 olmak üzere toplam **33 ayrı ihlal mesajı üretim noktası** vardır (bunlardan ikisi, farklı alan adlarıyla çağrılan ortak beyan karşılaştırıcılarıdır; alan başına ayrı ayrı sayılırsa aile sayısı daha da artar). Tabloya girmeyenler sonradan eklenen **beyan denetimleridir**: yolculuk süresi hücresinin matris değerine tam eşitliği, satır bazlı elleçleme hücreleri, SLA cezası hücresi, araç maliyeti payı, fiziksel iz maliyet uzlaşması, boş kiralık iz üç şartı ve beyan varış ile matris varışının karşılaştırılması. Dürüst tespit: mimari dokümandaki 17 satırlık tablo bu eklemelerle güncellenmemiştir; kodun kendisi kaynaktır.

### 6.3 Kanıt yoksa karşılaştırma yok

Hakemin bilinçli bir tasarım ilkesi vardır: eksik veriye dayanarak **sahte bir "beklenen" değer üretmez.** Bir bacağın hattı matriste yoksa yolculuk süresi ve maliyet karşılaştırmaları atlanır, yalnız "matriste olmayan hat" ihlali yazılır. Bir talep tahmin dosyasında bulunamıyorsa SLA karşılaştırması atlanır, yalnız "tahmin dosyasında olmayan talep" kanıtı bir kez yazılır. Amaç, tek bir kök nedenden onlarca sahte ihlal türetmemektir.

### 6.4 Uzlaşma kapısı: kuruşun milyonda biri

Aşamaların kabul kapısına ek olarak, yayınlayan koşuda çok daha sıkı bir kontrol vardır: **aramanın kendi aritmetiğiyle iddia ettiği tasarruf ile hakemin iki tam maliyetinden hesapladığı fark, mutlak değerce 0,000001 TL'den fazla sapamaz.**

Bu kapı, Stage 3 prototipindeki dört hatanın üçünü tek başına yakalamıştır ve o üçünü **başka hiçbir kontrol fark etmiyordu**. Nedeni şudur: bir arama hatası kendi içinde tutarlıysa (aynı yanlış zamanlarla hem planlar hem fiyatlarsa), beyan ile hakem birbirine uyar, hakem sıfır ihlal yazar ve plan geçerli görünür — yalnızca gereğinden pahalıdır. Uzlaşma kapısı tam olarak bu sınıfı hedefler.

Ölçülen değerler kapının hassasiyetini gösterir. Stage 1'de yerel Decimal toplamı 1.800.774,926388888876856333333 TL, hakemin bağımsız hesabı 1.800.774,926388895 TL — fark yalnızca yaklaşık 6 x 10⁻⁹ TL'dir ve kapıyı açan değer **hakemin** değeridir. Stage 3'te yerel 80.861,554166666666057... TL, hakem 80.861,554166666 TL.

Ayrıca yayınlayan aşama için **50.000 TL** taban vardır. Gerekçe kabul raporunda açıkça yazılıdır: *"1,00 TL çok gevşek: arama tek kazara yük almaya çökse bile geçerdi."*

### 6.5 Yakaladığı gerçek hatalar

Hakem simülatörü, optimizer daha yazılmamışken bile iki optimizer-sınıfı hatayı yakalamıştır:

- **C1 — Yanlış çıkış merkezinden toplama.** Bir yükün, tahmin dosyasındaki çıkış merkezi yerine başka bir merkezden alınıp teslim edilmiş sayılması. Fiziksel olarak imkânsız olan bu durum, "rota tahmin çıkışından başlamıyor" kuralıyla kapatıldı.
- **C2 — Karışık araç türlü zincir.** Bir fiziksel rotanın bacaklarının farklı araç türleri beyan etmesi; bu, hem kapasite kontrolünü hem tır defterini atlatabilirdi. "Bir fiziksel araç boyunca tip ve tür tutarlılığı" kuralıyla kapatıldı.

**Stage 3 prototipindeki dört hata** ise uzlaşma kapısının değerini tek başına kanıtlar:

| Hata | Nitelik | Bedeli |
|---|---|---:|
| Kiralık rotayı yük alma hedefi almak | Kural ihlali; ayrıca spot tarifesiyle fiyatlama | — (kural) |
| Yük alınan durakta yanlış SLA zaman damgası | Yüklemeyi teslim süresine katmak | 5.108,80 TL fazla beyan |
| Alınan yükün hedefini geçmesi | SLA ve kapasiteyi bozar | 274,00 TL |
| Ara durakta yanlış indirme kümesi | Elleçleme şişer, sonraki segmentler kayar | 886,52 TL fazla maliyet |

Dördüncü hata özellikle öğreticidir: **kendi içinde tutarlıydı.** Prototip aynı yanlış zamanlarla hem planlayıp hem fiyatladığı için beyan-hakem kapısını da, uzlaşma kapısını da geçiyordu ve hakem sıfır ihlal yazıyordu; yalnızca gereğinden pahalı bir plan üretiyordu. Bu hata ancak üretim kodunun sonucu, devralınan prototip hedefiyle (11.233.363,25 TL) karşılaştırıldığında ortaya çıktı: üretim kodu indirme kümesini yük alma **sonrası** yük listelerinden türetiyordu ve hedefi 886,52 TL aşıyordu.

İlk üç hata yalnız uzlaşma kapısında görüldü; dört hatanın dördü için de ayrı birer regresyon testi yazıldı.

### 6.6 Diğer kalite kapıları

- **Determinizm.** Stage 2 ve Stage 3 aramaları aynı girdiyle ve **karıştırılmış** girdiyle çalıştırıldı; hepsinde plan ve tüm metrikler birebir aynı çıktı. Teslim edilen dosya girdi sırasına bağlı değildir.
- **Bağımsız yeniden inşa.** Ayrı bir süreçte dört aşama sıfırdan kuruldu, yayınlanan dosya optimizer durumuna hiç bakılmadan yeniden hakemlendi. Envanter korunumu doğrulandı: yüklenen ve teslim edilen çoklu kümeleri aynı, toplam **4.977.975 desi**.
- **Yalnız çalışma kitabından denetim.** Plan dosyası araç kimliğine göre gruplanıp kalkış anına göre sıralanarak topoloji denetlendi: bacak sayısına göre araç dağılımı 1 bacak 438, 2 bacak 127, 3 bacak 28, 4 bacak 72 = **665**; 28 rota-ortası yükleme; **0 topoloji hatası**.
- **Hakem canlı mı testi.** Tek bir `Yolculuk süresi` hücresine bir dakika eklendiğinde hakem ihlal yazar — yani denetim gerçekten çalışmaktadır.
- **Format = diskalifiye.** Şartname *"bu formata uymayan takımların sonuçları kesinlikle değerlendirmeye alınmayacaktır"* der. `src/schemas.py` son savunma hattıdır: kolon adlarını birebir doğrular (`Araç Tipi` ile `Araç türü` tuzağı, `Varış elleçleme` ile `Çıkış Elleçleme` büyük/küçük harf farkı dahil), tarih ve saat hücrelerinin gerçek takvim değeri olduğunu kontrol eder (31.06.2026 ve 23:60 reddedilir) ve sayısal kolonların sonlu, negatif olmayan değerler taşıdığını doğrular.

---

## 7. Final Entegrasyon Katmanı

### 7.1 main.py orkestratörü

Teknik Gereksinimler Bölüm 3, kök dizinde argümansız çalışan bir `main.py` ister ve *"main.py bunları sırayla çağıran ince bir orkestratör olabilir"* der. Teslim edilen `main.py` tam olarak budur: optimizasyona ait **tek bir karar** içermez, yalnızca aşamaları sırayla çağırır ve kabul bayrağını okur.

```
resolve_input_path -> read_demand_table -> load_all(with_demand=False)
  -> build_plan (Stage 0) -> run_same_lane_stage (Stage 1)
  -> run_milk_run_stage (Stage 2) -> run_pickup_stage (Stage 3)
  -> write_final_plan
```

Süreç `input()` beklemez, dosya seçici açmaz, IDE veya not defteri ortamına bağımlı değildir; ağ çağrısı, alt süreç veya çalışma anında `pip install` yoktur. Bağımlılıklar yalnız `pandas` ve `openpyxl`'dir.

Küçük ama ölçülmüş bir optimizasyon: statik veriler `with_demand=False` bayrağıyla yüklenir. Final koşusunda tahmin çalıştırılmadığı için 66.024 satırlık geçmiş talep tablosunun ayrıştırılması saf kayıptır — ölçülen maliyet **8,20 sn**, bayrakla **0,08 sn**. Bölüm 10 çalışma süresini değerlendirmeye kattığı için bu 8,12 sn kazanılmıştır.

### 7.2 Girdi sözleşmesi

Bölüm 4'ün **iki erişim yönteminin ikisi de** desteklenir ve sırayla denenir: önce `TEKNOFEST_INPUT_FILE` ortam değişkeni (değer kırpılır, tırnaklar soyulur, göreli verilmişse betiğin dizinine göre çözülür), sonra `data/one_week_backtest.xlsx`. Ortam değişkeni tanımlı ama dosya yoksa sessizce yedek yola düşülür.

Girdi tablosu satır satır normalize edilir ve tip toleransı geniştir. Tarih hücresi `pd.Timestamp`, `datetime`, `date`, Excel seri numarası (1899-12-30 epoch'u) veya altı farklı metin biçiminden gelebilir. Saat hücresi `datetime.time`, `Timestamp`, `Timedelta`, Excel gün kesri (0,375 → 09:00) veya dört farklı metin biçiminden gelebilir; saniye artığı varsa yarışmanın yuvarlama yönüyle tutarlı olacak biçimde bir üst **dakikaya** yuvarlanır. Desi hücresi sayıya çevrilir, en yakın tam sayıya yuvarlanır ve negatifler sıfırlanır.

Çözümlenemeyen satırlar **sessizce silinmez**: dört ayrı sayaç tutulur (geçersiz tarih, geçersiz saat, geçersiz desi, hat matrisinde olmayan çıkış/varış) ve her biri insan-okur bir not olarak konsola basılır. Referans girdide 4.046 satırın tamamı geçmiş, hiçbir satır atlanmamıştır.

### 7.3 Ufkun türetilmesi

Bölüm 7 kodda gömülü takvim tarihi yasaklar. Ufuk yalnızca girdinin `Tarih` kolonundan türetilir: en küçük ve en büyük tarih arasındaki **tüm günler kesintisiz** döner (arada talebi olmayan bir gün varsa bile listede yer alır, çünkü boru hattı "bir sonraki dalga = ertesi gün" zincirini varsayar). Aralık 31 günü aşarsa yalnızca **uyarı** basılır ve çalışma sürer — aykırı tek bir tarih hücresi yüzünden koşu düşürülmez.

Bir test aynı haftayı 2019, 2026 ve 2031 yıllarına taşıyıp sonucun kaymadığını doğrular.

### 7.4 Talep kimliği eşlemesi

Girdideki talep kimlikleri kanonik `D00001` biçiminde olmayabilir (`REQ_1`, `TALEP-7`...). Boru hattının iç doğrulayıcıları ve hakem simülatörü kanonik biçime dayandığı için iki yönlü bir eşleme yapılır: girdi satırları `(tarih, çıkış, varış, slot)` anahtarıyla kararlı biçimde sıralanıp `D00001...` kimlikleri atanır, plan yazılmadan hemen önce kimlikler **özgün hâllerine** geri çevrilir ve bölünmüş parça soneki korunur. Böylece çıktı, jürinin verdiği talep tablosuyla birebir eşleşir (Q&A HititRoute Soru 2: *"Talep ID exceli ile Taşıma planı exceli içindeki talep ID'lerin birebir eşleşmesi gerekmektedir."*).

Sıralama anahtarı, tahmin modülünün kimlik atama anahtarıyla **birebir aynı** seçilmiştir. Bunun ölçülebilir sonucu şudur: girdi bu projenin kendi tahmin çıktısıysa eşleme **özdeşliktir** ve boru hattı bit-birebir aynı planı üretir. Referans dosyada 4.046 satırın tamamında kanonik kimlik özgün kimlikle aynıdır.

### 7.5 Çıktı sözleşmesi ve atomik yazım

Plan beş adımda yazılır:

1. Şema doğrulaması **yazımdan önce** çalışır; en ufak hatada dosyaya hiç dokunulmaz.
2. Kimlikler özgün hâllerine çevrilir ve 16 kolon şablon sırasına sabitlenir.
3. Hedef dizinde **gizli önekli geçici bir dosyaya** yazılır ve `Taşınan Desi` kolonuna resmî şablonun `0.000` sayı biçimi uygulanır.
4. Geçici dosya diskten **geri okunur**: kolon listesi birebir eşleşmeli, satır sayısı korunmuş olmalıdır; uymazsa hata.
5. `os.replace` ile **atomik** olarak yerine konur.

Sonuç değişmez bir garantidir: diskteki dosya her an ya yoktur ya da şemaya birebir uyan, geçerli bir plandır. Yarım yazılmış dosya asla görünmez.

Hücre değerleri de karşılaştırılır. Excel hücreleri yaklaşık 17 anlamlı basamak sakladığı için 3347,8859374999997 değeri diskten 3347,8859375 olarak döner; bu **veri bozulması değil**, dosya biçiminin doğal hassasiyetidir ve bağıl toleransla tolere edilir. Toleransın ötesindeki farklar uyarı olarak basılır ama yayını engellemez — çünkü Bölüm 10'a göre çıktısız kalmak bir uyarıdan çok daha ağır bir sonuçtur.

### 7.6 Kademeli yayın ve sert süre sınırı

Bölüm 10 iki ayrı hata durumu tanımlar ve ikisi için de ayrı bir mekanizma vardır.

**"Beklenen çıktı dosyası üretilmez" için: kademeli yayın (progressive publishing).** Geçerli ilk plan — yani Stage 0 temel planı — elde edilir edilmez `out/Tasima-plani.xlsx` yazılır; kabul edilen her aşama dosyayı atomik olarak günceller. Beklenmedik bir hata hâlinde diskte her zaman geçerli bir taşıma planı bulunur. Bu ölçülmüştür: süreç Stage 2'nin ortasında **zorla öldürüldüğünde** bile diskte 3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru bir plan bulundu.

**"Zaman aşımı" için: sert süre sınırı.** Arama aşamaları kendi içlerinde bölünemediği için sınır dışarıdan konur: her aşama ayrı bir arka plan iş parçacığında, kalan bütçeyle sınırlı olarak çalıştırılır. Sınır dolarsa aşama **terk edilir**, o ana kadarki en iyi plan korunur ve süreç normal biçimde sonlanır. Bütçe varsayılan olarak **100 dakikadır** (Bölüm 10 ile aynı); bunun %90'ı aramaya, kalan %10'u çıktının yazılmasına ayrılır.

Ölçülmüş davranış (bütçe 36 saniyeye indirilerek):

```
[Stage 1 aynı-hat onarım] kabul edildi; tasarruf 1.800.774,93 TL (13,4 sn)
    -> çıktı güncellendi (Stage 1)
[Stage 2 milk-run] süre sınırında terk edildi (11,4 sn); önceki plan korunuyor
[Stage 3 rota-ortası yük alma] atlandı: arama bütçesi tükendi
Toplam süre: 32,4 sn -> çıkış kodu 0, geçerli plan diskte (0 ihlal)
```

Ek olarak her aşama istisna yakalamasıyla sarmalanmıştır; bir aşama çökerse tam hata izi basılır ve önceki aşamanın planı korunur. `main()` daima 0 döner. Tek bilinçli istisna, hiç yayın yapılamamış olmasıdır — o durumda hata bilinçli olarak yükseltilir, çünkü sessizce yanlış bir çıktı bırakmaktansa hatanın görünmesi yeğdir.

### 7.7 Değişiklik kapsamı (Bölüm 8)

Bölüm 8 değişikliklerin yalnız entegrasyon amaçlı olmasını ister. Teslim paketinde:

- `main.py` ve `src/contract.py` **tamamen yenidir** ve tek bir optimizasyon kararı içermez.
- **Değiştirilen dosya sayısı: iki.** `src/data.py`'ye opsiyonel `with_demand` bayrağı eklendi (varsayılan davranış değişmedi); `src/schemas.py`'de talep kimliği düzenli ifadesi `D\d{5}` yerine `D\d{5,}` olacak biçimde **genişletildi** (99.999 satırdan fazla girdi için, Bölüm 7 gereği).
- Algoritma, hakem ve çizelgeleme modüllerinin **hiçbiri değişmedi**.

Kanıt niteliksel değil sayısaldır: aynı talep tablosuyla çalıştırıldığında `main.py`, önceki aşamada teslim edilen plan dosyasıyla **hücre hücre birebir aynı** dosyayı üretir — 5.523 satır x 16 kolon, **0 farklı hücre**, 11.232.476,731944446 TL, 0 hakem ihlali.

---

## 8. Ölçülmüş Sonuçlar

### 8.1 Maliyet merdiveni

| Aşama | Araç maliyeti (TL) | SLA cezası (TL) | Toplam (TL) | Aşama tasarrufu (TL) | İhlal |
|---|---:|---:|---:|---:|---:|
| Stage 0 | 15.460.592,57 | 1.020.367,20 | 16.480.959,77 | — | 0 |
| Stage 1 | 12.510.401,25 | 2.169.783,60 | 14.680.184,85 | 1.800.774,93 | 0 |
| Stage 2 | 8.752.512,29 | 2.560.826,00 | 11.313.338,29 | 3.366.846,56 | 0 |
| Stage 3 | 8.616.944,73 | 2.615.532,00 | 11.232.476,73 | 80.861,55 | 0 |

Kümülatif: **−5.248.483,04 TL (−%31,84)**. Araç maliyetinden 6.843.647,84 TL kazanılıp 1.595.164,80 TL SLA cezası ödenmiştir.

### 8.2 Araç sayısı ve zincir dağılımı

| Aşama | Segment | Fiziksel araç | Tek bacak | 2 durak | 3 durak | 4 durak | Kiralık rota | Spot rota | Plan satırı |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stage 0 | 1.269 | 1.269 | 1.269 | — | — | — | 126 | 1.143 | 3.167 |
| Stage 1 | 1.092 | 1.092 | 1.092 | — | — | — | 126 | 966 | 3.167 |
| Stage 2 | 1.092 | 693 | 466 | 127 | 28 | 72 | 126 | 567 | 5.510 |
| Stage 3 | 1.064 | 665 | 438 | 127 | 28 | 72 | 126 | 539 | 5.523 |

Kimlik denklemleri: Stage 2 için `1.092 − (626 − 227) = 693`; Stage 3 için `693 − 28 = 665` ve `1.092 − 28 = 1.064`.

### 8.3 Doluluk

| Aşama | Ortalama spot doluluk | %30 altındaki spot araç |
|---|---:|---:|
| Stage 0 | %48,02 | 480 / 1.143 (%42) |
| Stage 1 | %56,82 | 296 / 966 (%31) |
| Stage 2 | %76,96 | 46 / 567 (%8) |
| **Stage 3** | **%79,03** | **30 / 539 (%6)** |

Stage 0'daki dağılım araç türüne göre çarpıcıdır: Kamyonet bacaklarının ortalama doluluğu %40,15, Kamyon %85,96, Hafif Kamyon %94,66, Tır %79,54. Yani düşük doluluk tek bir yerde toplanmıştır ve merdivenin hedeflediği tam olarak orasıdır.

### 8.4 Araç türü karması

| Araç türü | Stage 0 | Stage 1 | Stage 2 | Stage 3 |
|---|---:|---:|---:|---:|
| Kamyonet (5.600 desi) | 950 | 773 | 259 | **233** |
| Hafif Kamyon (7.200) | 24 | 24 | 29 | 29 |
| Kamyon (12.000) | 196 | 196 | 306 | **304** |
| Tır (22.400) | 99 | 99 | 99 | 99 |

Karma küçükten büyüğe kayar: yarı boş Kamyonet'ler birleşip daha az sayıda ama daha dolu Kamyon'a biner. Tır sayısı dört aşamada da sabittir — tır kapasitesi kıt bir kaynaktır (yedi merkezde sıfır) ve bilinçli olarak zorlanmamıştır.

### 8.5 Arama uzayı özeti

| Aşama | Taranan birim | Değerlendirilen aday | Kabul |
|---|---|---:|---:|
| Stage 0 | 1.751 hat-gün | 39.598 karma (6.847 fiyatlandı) | 1.269 bacak |
| Stage 1 | 1.134 verici | 4.035 çift, 239 geçerli aday | 177 hamle |
| Stage 2 | 93 grup | 5.426 ikili + 96.369 çoklu alt küme, 1.908.972 varyant | 227 zincir |
| Stage 3 | 227 hedef x 340 verici | 135.660 çift, 56 kârlı aday | 28 yük alma |

### 8.6 Kapasite kullanımı

Hiçbir defter aşılmamıştır. En yüksek doluluk oranları: Karaman 02.07 %95,9 (42.022 / 43.830), İstanbul 01.07 %92,7 (365.807 / 394.786), Zonguldak 02.07 %88,2, Yalova 01.07 %85,4. Tır tarafında en yoğun nokta İstanbul'da 9 / 10 ziyarettir. Kapasitesi sıfır olan yedi merkeze hiç tır ziyareti yazılmamıştır.

> **Fizikî sınır — bilinçli not.** Ağın elleçleme kapasitesi referans hafta için zaten neredeyse tamamen doludur: İstanbul, 01.07.2026 — o günün yükleme + indirme talebi 395.825 desi, günlük kapasite 394.786 desi. Yani hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme kısıtı **hiçbir plan tarafından** sağlanamaz; bu bir kod kusuru değil, veri setinin fizikî olarak çözümsüz olmasıdır.

### 8.7 Farklı hafta, hacim ve biçim senaryoları

Bölüm 7 için sentetik girdiler üretildi (tarih kaydırma, hacim ölçekleme, ufuk kısaltma, kimlik ve saat biçimi değiştirme) ve üretilen plan her seferinde diskten geri okunup bağımsız olarak hakemden geçirildi.

| Senaryo | Ufuk | Talep satırı | Desi | Süre | İhlal | Kazanç |
|---|---|---:|---:|---:|---:|---:|
| Referans (teslim edilen) | 29.06.2026 – 05.07.2026 (7 gün) | 4.046 | 4.977.975 | 150 sn | 0 | −%31,8 |
| Farklı yıl, 4 günlük ufuk, `REQ_` kimlikler, `HH:MM` | 25.05.2025 – 28.05.2025 | 1.808 | 1.214.316 | 171 sn | 0 | −%45,8 |
| Farklı hafta, %125 hacim, `HH:MM:SS` | 02.09.2026 – 08.09.2026 | 2.925 | 6.222.428 | 143 sn | 0 | −%28,0 |

Her üç senaryoda da çıkış kodu 0, şema birebir, beyan edilen toplam maliyet ile hakem toplamı arasındaki fark **0,0000 TL**.

**%250 hacimli sınır senaryosu:** Stage 0 planı 69 elleçleme kapasitesi ihlaliyle üretildi. İhlallerin tamamı, o gün o merkezde talebin kapasiteyi aşmasından kaynaklanıyor (örnek: Erzincan 80.160 desi, kapasite 58.673). Stage 1 adayı bu nedenle doğru biçimde reddedildi, temel plan korundu, kod çökmedi ve şemaya birebir uyan bir plan yazdı.

### 8.8 Çalışma süresi ve testler

| Ölçüm | Değer |
|---|---|
| Uçtan uca çalışma süresi (referans veri) | yaklaşık 150 sn (tavan 100 dakika) |
| Ölçülen aşama süreleri | Stage 0: 0,46 sn · Stage 1: 12,6–13,4 sn · Stage 2: yaklaşık 72 sn |
| Regresyon testi | **592** (528 mevcut + 64 yeni entegrasyon testi), tamamı geçiyor |
| Temiz sanal ortam doğrulaması | pandas 2.3.3 / numpy 2.4.6 / openpyxl 3.1.5 ile uçtan uca çalıştı, çıktı referansla birebir aynı |
| Çıktı | 5.523 satır x 16 kolon, tek sayfa, 665 benzersiz araç kimliği, 35 boş kiralık satırı |

---

## 9. Ölçülmüş Çıkmaz Sokaklar

Bu bölüm, denenip **ölçülerek reddedilen** fikirleri ve sayılarını içerir. Amacı, çözümün seçilmiş değil **aranmış** olduğunu göstermektir: aşağıdaki her kalem için kod yazıldı, çalıştırıldı ve sonuç hakemden geçirildi.

### 9.1 Düşük dolulukta aynı-hat birleştirme — 0 TL

Stage 2 sonrasında hâlâ 46 spot araç %30'un altında dolulukla çalışıyordu. Doğal ilk fikir bunları aynı hatta birleştirmekti. Ölçüm sonucu net: **46 aracın 46'sı da** o gün o hattın **tek aracıydı**, yani birleşecek eş yoktu. Aynı-hat sezgisiyle kazanılabilecek tutar tam olarak **0 TL**'dir.

Bu ölçüm Stage 3'ün varlık sebebidir: aynı hatta eş aramak yerine yükü **oradan geçen** bir zincire bindirmek. Sonuç, %30 altındaki araç sayısını 46'dan 30'a indirdi.

### 9.2 Tır'ı zincire katmak — 18.100 TL daha kötü

Kural engeli **yoktur**; `uğrama` yasağı yalnız kiralık araçlara yöneliktir, hiçbir araç **tipine** değil. Tır'ı zincire almak kapasite tavanını 12.000'den 22.400 desiye çıkarırdı ve teorik olarak daha büyük birleşmeler mümkün olurdu.

Ölçüldü: tam yama **+18.100 TL daha kötü** sonuç verdi; minimal yama ise bit-bazında aynı sonucu üretti. İki neden vardır. Birincisi, **Kamyon aynı 12.000 desi bandında Tır'ı her koşulda ezer** (318,25 TL/saat karşısında 487,50 TL/saat, 21 TL/km karşısında 25 TL/km, üstelik 306 hattın 306'sında daha hızlı). İkincisi, kârlı Tır adaylarının **%93,6'sı** kapasitesi sıfır olan yedi merkez yüzünden zaten uygulanamıyor.

### 9.3 Tahmin bias düzeltmesi — hedef sahte çıktı

Ay sonu haftası backtest penceresinde ölçülen **+%28,3 bias** ilk bakışta tahmin tarafındaki en değerli açık kalem gibi görünüyordu. Dört düzeltme adayı denendi: slot bazlı çarpanlar, ay sonundan iki gün sonrası için ek rol, toparlanma kalibrasyonu ve taban kalibrasyonu.

Sonuç: **hedefin kendisi sahte çıktı.** +%28,3 bias, 29 Mart kesim tarihinde "ayın ilk günü" çarpanının yalnızca iki örnekle uydurulmasının artefaktıdır. Birini-dışarıda-bırak (leave-one-out) yöntemiyle ölçüldüğünde teslim edilen modelin bias'ı **−0,0573**'tür. Dört adayın dördü de dışsal örneklemde başarısız oldu ve hiçbiri uygulanmadı.

### 9.4 Açgözlü yerine tam eşleme (max-weight matching) — 47.796 TL

Stage 2'nin çakışan adaylar arasındaki seçimi açgözlüdür (en çok kazandıran önce). Bunun yerine tam bir maksimum ağırlıklı eşleme (max-weight matching) kurulup ölçüldü: **47.795,99 TL**.

Ancak bu, çok duraklı geçişin **alternatifidir, toplamı değil**: aynı ikili aday kümesi üzerinde çalışır. Uygulanan çok duraklı milk-run geçişi aynı kaynakları yaklaşık 476 bin TL farkla aşmaktadır, dolayısıyla tam eşleme uygulanmamıştır.

### 9.5 Beş duraklı zincir — uygulanabilir değil

k = 5'e çıkmanın kural engeli yoktur ve teorik kazancı vardır. Ölçüm: aktif gruplar C(n,5) = **254.992** alt küme barındırır; bunların farklı varışlı olanları **190.966**'ya, 12.000 desi kapasite süzgecinden geçenler **41.425**'e (%21,7) iner. Geçen her alt küme 120 durak sırası x 3 araç tipi ile fiyatlanmalıdır, yani yaklaşık **14.913.000 varyant**. Deneme yapıldı: **13,5 dakika CPU ve 1,3 GB bellek** sonrasında sonuç vermedi.

Ulaşmak için dal-sınır ve kapasite öncelikli budama gerekir. Bilinçli olarak kapsam dışı bırakılmıştır ve kabul raporunda böyle kaydedilmiştir.

### 9.6 En kötü talepleri hedefleyerek SLA azaltma — uzun kuyruk

SLA cezasının büyük kısmının birkaç büyük talepte toplandığı varsayımı test edildi. Ölçüm: **en kötü 20 talep toplam cezanın yalnız yaklaşık %15'ini** oluşturuyor. Ceza uzun kuyrukludur; hedefli müdahaleyle anlamlı kazanç elde edilemez.

### 9.7 Ölçülmüş ama bilinçle uygulanmayan parametre değişiklikleri

İki Stage 0 parametresinin gevşetilmesi ölçüldü ve ikisi de daha ucuz sonuç verdi:

| Değişiklik | Stage 0 toplamı | Fark |
|---|---:|---:|
| Erteleme tavanı 5.600 → 12.000 desi | 16.177.786,20 TL | −303.173,57 TL |
| Erteleme marjinal bedeli 0,12 → 0,30 TL/desi | 16.411.674,58 TL | −69.285,19 TL |

Bunlar **uygulanmamıştır** ve gerekçesi üç katmanlıdır. Birincisi, ölçüm yalnız Stage 0 içindir; dört aşamalı boru hattının **sonucu** üzerindeki etkisi ölçülmemiştir. İkincisi, 12.000 seçimi "ertelenen yük yarın tek Kamyonet'e sığar" değişmezini bozar ve erteleme fiyatlama modelinin dayandığı varsayımı geçersiz kılar. Üçüncüsü ve belirleyicisi, **Teknik Gereksinimler Bölüm 8** bu aşamada algoritma iyileştirmesini açıkça yasaklar — final teslimi yalnız entegrasyon değişikliği içerebilir.

### 9.8 Ölçülmüş karşı-olgular

Bazı tasarım kararlarının doğruluğu, kaldırıldığında ne olduğu ölçülerek gösterilmiştir:

| Karar | Kaldırıldığında ölçülen sonuç |
|---|---|
| Kiralık tırların bütçeden ön rezervasyonu | 12 tır kapasitesi ihlali |
| Boşaltma gününde kiralık tırların erken kalkmaması | 2 tır kapasitesi ihlali (Balıkesir ve Tekirdağ, 06.07) |
| Erteleme mekanizması | Toplam 16.480.959,77 TL yerine 24.954.608,68 TL (+8.473.648,91 TL) |
| Stage 1'in düzeltilmiş taban üzerinde çalışması | 535 denemenin 535'i reddedilir, 0 hamle |

---

## 10. Bilinen Sınırlar ve Gelecek İş

Bu bölüm dürüst olmak için vardır. Aşağıdakiler kural ihlali değildir; hiçbiri planı geçersiz kılmaz. Hepsi, çözümün **daha az** tasarruf etmesine yol açan bilinçli muhafazakârlıklar ya da açıkça ölçülmemiş alanlardır.

### 10.1 Aramanın optimal olmadığı yerler

- **Açgözlü küme paketleme.** Stage 2'de k ≤ 4 için alt küme numaralandırması **tamdır** ve seçilen bir alt küme için bulunan çözüm o alt kümenin en iyisidir. Optimal olmayan kısım, **çakışan adaylar arasındaki seçimdir**: adaylar tasarrufa göre sıralanıp açgözlü işlenir, tam küme-bölümleme (set-partitioning) çözümü yapılmaz.
- **Stage 0 budaması.** İki budama kuralından ikincisi ("en küçük aracı çıkarmak yükü hâlâ karşılıyorsa aday domine") araç maliyeti üzerinde kesin baskındır ama SLA cezası teorik olarak farklılaşabilir. Elenen adayın alt kümesi ayrı bir kombinasyon olarak zaten numaralandırıldığı için arama kör kalmaz, ama bu kural tam ispatlı değildir.
- **Stage 0 tır bütçesi muhafazakârlığı.** Bir hatta ikinci ve üçüncü tır tahsis edilirken aynı merkez gereğinden fazla rezerve edilir. Bu **asla yetersiz rezerve etmez**, yani ihlal üretemez; yalnız bazı fırsatları kaçırabilir. Bu veri setinde hiç etkisi olmamıştır — tahsis edilen dokuz tırın dokuzu da farklı hat-günlerde ve ilk seviyededir.
- **Stage 3 tek yük alma kısıtı.** Hedef rota başına en fazla bir yük alma yapılır. Bu bir tasarruf tavanıdır; kademeli (iteratif) bir varyant mümkündür ama fiyatlama tabanının geçerliliğini korumak için bu teslimde kapsam dışı bırakılmıştır.

### 10.2 Ölçülmemiş açık alanlar

- **Tier B rota-ortası yük alma.** Rotayı bir durak uzatan varyant. Bağımsız bir ölçüm Tier A + Tier B için yaklaşık 146 bin TL görmüştür (yani ek yaklaşık 66 bin TL), ancak 5 duraklı rota üretir ve zincir uzunluğu sözleşmesini değiştirir.
- **Beş duraklı zincir.** Kaba kuvvetle uygulanabilir değil; budama gerektirir (Bölüm 9.5).
- **Hub konsolidasyonu.** Yükü ara bir merkezde indirip başka araca aktarma senaryosu hiç kullanılmamıştır. Jüri bunu serbest bırakır ama iki kez elleçleme ve SLA baskısı getirir; milk-run zaten aynı kazancı çok daha ucuza sağladığı için öncelik verilmemiştir.
- **Parametre taraması.** Erteleme tavanı, erteleme marjinal bedeli ve tır eşiği gibi sabitler tekil olarak ölçülmüş ama boru hattı sonucu üzerinde sistematik taranmamıştır (Bölüm 9.7).

### 10.3 Modelleme sınırları

- **Elleçleme kapasitesi ileriye dönük modellenmez.** Stage 0, araç karmasını seçerken elleçleme darboğazını **öngörmez**; kısıt sonradan, çizelgeleme katmanında kaydırmayla düzeltilir. Kaydırma araç maliyetini değiştirmez, yalnız SLA cezası ekler. Çok daha dar kapasiteli bir veri setinde bu, çözümü optimalden uzaklaştırabilir — **ihlal üretmez, pahalılaşır**.
- **Bekleme yapılmaz.** Model hiçbir yerde aracı bilerek bekletmez; bekleme süresi de araç maliyetine dahil olduğu için (Q&A Soru 12) beklemeyi açmak arama uzayını sürekli bir zaman değişkeniyle genişletirdi. Bu bir muhafazakârlıktır ve bazı fırsatları kaçırabilir.
- **Tahmin tarafında slot ayrımı yoktur.** Takvim çarpanları küreseldir; 17:00 slotu toplam desinin yaklaşık %91'ini taşıdığı hâlde slot bazlı çarpan denenmiş ve dışsal örneklemde başarısız olmuştur (Bölüm 9.3).

### 10.4 Yorum riski olarak izlenen konular

Aşağıdaki üç konuda jüri metni tek bir okumaya kapatmıyor; her birinde **muhafazakâr** tarafı seçtik ve bunu açıkça beyan ediyoruz:

1. **Kiralık araç kimliklerinin günler arası kalıcılığı.** Gün bazlı benzersiz kimlik kullanıyoruz; kimliklerin günler arası sabit olması gerekiyorsa da çözüm bundan etkilenmez, yalnız kimlik üretimi değişir.
2. **Puanlamanın kaynağı.** Jürinin beyan edilen maliyet kolonlarını mı yoksa bağımsız yeniden hesabı mı puanladığı bilinmiyor. İkisi de tutarlı olacak biçimde yazıyoruz ve fark 0,0000 TL'dir; hangisi puanlanırsa puanlansın aynı sonucu verir.
3. **Sıfır desili satırlar.** Jüri OpAI Soru 5'te "Sunulmalı" demiştir ve biz tam gridi sıfırlarla teslim ediyoruz. Pozitif bir taban (her satıra en az 1 desi) gerekseydi, hazır bir yedek çözüm mevcuttur.

### 10.5 Öncelik sırası

| Öncelik | Konu | Beklenen etki |
|---|---|---|
| 1 | Tier B rota-ortası yük alma | Ölçülen bağımsız gösterge: ek yaklaşık 66 bin TL |
| 2 | Beş duraklı zincir (budamalı) | Ölçülmemiş; k=3→4 geçişi 205.902 TL kazandırmıştı |
| 3 | Stage 2 için tam küme-bölümleme | Ölçülmemiş; açgözlü seçimin kaybını kapatır |
| 4 | Elleçleme darboğazını karmaya öngörülü katmak | Dar kapasiteli veri setlerinde değer üretir |
| 5 | Parametre taraması (erteleme tavanı ve bedeli) | Stage 0'da 303.174 TL ölçüldü; boru hattı etkisi bilinmiyor |

---

## 11. Kapanış

Teslim edilen çözüm, bir haftalık 4.046 satırlık ve 4.977.975 desilik talebi **11.232.476,73 TL** toplam maliyetle, **sıfır kural ihlaliyle** taşıyan bir sevkiyat planı üretir. Bu, temel plana göre **%31,84** daha ucuzdur; fiziksel araç sayısı 1.269'dan 665'e, ortalama spot doluluk %48,02'den %79,03'e taşınmıştır.

Kazancın kaynağı tek bir mühendislik fikridir — **aracı ortadan kaldır, yükü zaten yola çıkacak olana bindir** — ve bu fikir üç farklı eksende (aynı hat, aynı çıkış anı, rota ortası) uygulanmıştır. Sonucun güvenilirliği ise tek bir yöntem kararına dayanır: **planlayıcı asla kendi hesabını onaylamaz.** Her aşama, kuralları sıfırdan yeniden uygulayan bağımsız bir hakem simülatöründen geçer; aramanın iddia ettiği tasarruf ile hakemin ölçtüğü fark kuruşun milyonda birine kadar uyuşmak zorundadır. Stage 3 prototipindeki en sinsi dört hatanın üçü yalnız bu kapıda yakalanmıştır — o üçünü başka hiçbir kontrol fark etmiyordu.

Final teslimi Bölüm 8'e uyar: algoritma, model ve çözüm mantığı değişmemiştir. Kanıt sayısaldır — aynı girdiyle üretilen çıktı, önceki teslimle **0 farklı hücredir**.
