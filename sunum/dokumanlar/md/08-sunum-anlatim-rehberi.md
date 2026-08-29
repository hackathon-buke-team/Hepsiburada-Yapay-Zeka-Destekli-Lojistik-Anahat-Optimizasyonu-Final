# Sunum Anlatım Rehberi

Bu belge iki işe yarar. Birinci bölüm **teknik sözlük**: sunumda geçen her terimin
ne demek olduğu, neden onu seçtiğimiz ve teknik bir jüri üyesi derinleştirirse
nereye kadar gidebileceğiniz. İkinci bölüm **slayt slayt anlatım**: 15 slaydın
her biri için ekranda ne olduğu, ne söyleyeceğiniz, hangi sayıyı vurgulayacağınız
ve o slayttan çıkabilecek soru.

Buradaki her sayı `sunum/kaynak/deck_data.json` ve `final-teslim/src/` altındaki
koddan gelir. Sunumdaki grafiklerle birebir aynı kaynaktan beslenir.

---

## Bölüm 1 — Teknik sözlük

### Desi

Hacim ağırlık birimi. Taşımacılıkta bir kolinin kapladığı yerin ağırlığa
çevrilmiş hâli. Bizim için önemi şu: **kapasite de talep de desi cinsinden**,
yani araç seçimi ile yük miktarı doğrudan karşılaştırılabilir. Kamyonet 5.600
desi, hafif kamyon 7.200, kamyon 12.000, tır 22.400 desi taşır.

### Medyan — ve neden ortalama değil

Bir sayı dizisini küçükten büyüğe sıraladığınızda tam ortadaki değer. Ortalama
tüm değerleri toplayıp adede böler; medyan sadece sıralamaya bakar.

Farkı bir örnekle: `100, 110, 105, 95, 2.000` dizisinin ortalaması 482, medyanı
105. Son değer bir kampanya günü ya da veri hatasıysa, ortalama onun peşinden
sürüklenir, medyan yerinde durur.

**Neden bizde kritik:** Talep verisinde ay sonu çöküşleri ve tatil sıçramaları
var. Taban tahmini ortalamayla kursaydık, geçmişteki tek bir sıçrama o hücrenin
tüm tahminlerini yukarı çekerdi. Medyan bu tür aykırı değerlere karşı
**dayanıklıdır** (robust). Aynı gerekçeyle takvim çarpanlarını da beş oranın
medyanı olarak alıyoruz, ortalaması olarak değil.

> Teknik jüri sorarsa: medyanın kırılma noktası (breakdown point) %50'dir —
> verinin yarısı bozulmadan tahmin bozulmaz. Ortalamanınki 0'dır, tek bir
> uç değer yeter.

### DOW ve haftagünü medyanı

DOW = *day of week*, haftanın günü. Talep haftanın gününe güçlü bağlı:
salı ile pazar aynı davranmaz.

Taban tahminimiz şu: her **(çıkış merkezi, varış merkezi, saat slotu, haftagünü)**
kombinasyonu için, hedef tarihten **kesin önceki** son dört aynı-haftagünü
gözleminin medyanı. Kodda `dow_median(train, targets, k=4)`.

Yani "önümüzdeki salı 09:00 slotunda İzmir→Ankara ne gelir?" sorusuna,
"son dört salının aynı slotundaki değerlerin medyanı" diye cevap veriyoruz.

`k=4` seçimi bilinçli: dört hafta bir aylık mevsimselliği yakalar ama daha
eski, artık geçerli olmayan dönemleri içeri almaz.

### Takvim rolü ve takvim çarpanı

Her günün takvimden türetilen bir **rolü** var (kodda `_calendar_role`):

| Rol | Tanım |
|---|---|
| `month_end` | Ayın son günü |
| `day_before_month_end` | Ayın son gününden bir önceki gün |
| `first_day_after_month_end` | Ayın 1'i |
| `normal` | Diğer tüm günler |

Her role bir **çarpan** karşılık gelir ve nihai tahmin şudur:

```
tahmin = haftagünü medyanı  ×  takvim çarpanı
```

Ölçülmüş çarpanlar:

| Rol | Çarpan | Yorum |
|---|---:|---|
| Ay sonundan bir önceki gün | ×0,6752 | Hacim normalin %68'ine iner |
| Ayın son günü | **×0,0198** | Hacmin **%98'i kaybolur** |
| Ayın ilk günü | ×1,2072 | Telafi sıçraması, %21 fazlası |
| Normal gün | ×1,0000 | Dokunulmaz |

**Bu üç sayı seçilmedi, ölçüldü.** Yöntem (kodda `calendar_multipliers`):
geçmişteki her olay günü için o günün haftagünü tabanı hesaplanır, sonra
`oran = o günün gerçekleşeni ÷ taban` bulunur, ve aynı role ait tüm oranların
**medyanı** çarpan olur.

Üç tasarım kararı bunu savunulabilir kılıyor:

1. **Sızıntı yok.** Taban hesaplanırken yalnız o günden önceki veri kullanılır
   (`past = history[history["tarih"] < target_date]`).
2. **Ay sonu etkisi haftagünü etkisinden ayrılır.** Taban hesaplanırken ay sonu
   ve bir öncesi günler geçmişten dışlanır (`baseline_exclude`). Yoksa çöküş
   günleri tabanı da aşağı çeker, oran gerçek etkiyi küçük gösterirdi.
3. **Güvenlik freni.** Bir rol için en az iki gözlem yoksa çarpan `1.0`'a düşer
   (`MIN_CALENDAR_SAMPLES = 2`) — model veri yoksa uydurmaz, hiçbir şey yapmaz.

Veri 1 Ocak – 28 Haziran 2026 arası olduğu için her rolde **beş gözlem** var:
31 Ocak, 28 Şubat, 31 Mart, 30 Nisan, 31 Mayıs.

### Naive taban (kıyas çıtası)

Bir modelin "iyi" olduğunu söyleyebilmek için neyden iyi olduğunu söylemek
gerekir. Bizim çıtamız **naive**: "önümüzdeki salı, geçen salı ne olduysa odur"
— yani t−7 günü aynen kopyala (kodda `naive_lastweek`).

Bu, tahmin literatüründe standart bir referanstır. Naive'i yenemeyen bir model
karmaşıklığını hak etmiyor demektir.

### wMAPE — hata ölçütümüz

*Weighted Mean Absolute Percentage Error.* Formülü tek satır:

```
wMAPE  =  Σ |gerçekleşen − tahmin|  ÷  Σ gerçekleşen
```

Yani **toplam mutlak hatayı toplam gerçek hacme** bölüyoruz. Düşük olması iyi.
0,2174 demek "toplam hacmin %21,74'ü kadar hata yaptık" demek.

**Neden düz MAPE değil?** Klasik MAPE her satırın yüzde hatasını ayrı hesaplayıp
ortalar. Bunun iki kusuru var: talebin sıfır olduğu hücrelerde tanımsızlaşır
(sıfıra bölme), ve 3 desilik bir hattaki %100 hata ile 300.000 desilik bir
hattaki %100 hatayı eşit sayar. Bizim ağımızda 306 hat var ve hacimleri
arasında dört kat büyüklük farkı olabiliyor — wMAPE hataları hacimle
ağırlıklandırdığı için operasyonel gerçeğe daha yakın.

### Bias (yanlılık)

```
bias  =  Σ (tahmin − gerçekleşen)  ÷  Σ gerçekleşen
```

wMAPE hatanın **büyüklüğünü** ölçer, bias **yönünü**. Pozitif bias sistematik
fazla tahmin (gereksiz araç çıkarırsınız), negatif bias eksik tahmin
(SLA cezası ödersiniz) demektir.

### Frozen backtest — ve rolling'den farkı

Backtest, modeli geçmiş veriyle sınamaktır. İki türü var ve aradaki fark
dürüstlük açısından kritik:

**Rolling backtest:** Eğitim penceresi her hedef gün için yeniden kaydırılır ve
model her gün yeniden eğitilir. Daha iyimser sonuç verir, çünkü model ufkun
içinde ilerledikçe yeni gerçekleşenleri görür.

**Frozen backtest (bizim kullandığımız):** Eğitim verisi tek bir **cutoff**
tarihinde kesilir, model bir kez eğitilir, ve **ufkun tamamı tek atışta** tahmin
edilir. Ufuk içinde yeniden eğitim yoktur.

Neden bunu seçtik: **gerçek yarışma koşulunun aynısı.** Bize bir hafta ileriyi
tahmin ettirip planı istiyorlar; o hafta içinde kimse bize gün gün gerçekleşen
veriyi vermiyor. Rolling backtest bu koşulu taklit etmez ve modeli olduğundan
iyi gösterir.

Kod düzeyinde üç sızıntı koruması var (`src/frozen_backtest.py`, `run_frozen`):

1. **Eğitim kesiliyor:** `train = data[data["tarih"] <= cutoff]`.
2. **Cutoff ufuktan önce olmak zorunda:** `cutoff >= horizon_start` ise
   fonksiyon hata fırlatır.
3. **Model cevapları göremiyor:** hedef tablosundan gerçekleşen değer sütunu
   silinerek veriliyor —
   `target_metadata = actual_grid.drop(columns=["desi"])`.

Ayrıca `forecast_horizon`, ufuk içi gerçekleşen satır içeren bir talep tablosu
alırsa **hata fırlatır**. Yani sızıntı sessizce olamaz, koşum durur.

### Leakage (sızıntı)

Modelin, gerçek hayatta erişemeyeceği bilgiyi eğitim ya da değerlendirme
sırasında görmesi. Backtest sonucunu yapay olarak iyileştirir ve gerçek
performansı gizler. Yukarıdaki üç koruma tam olarak buna karşıdır.

### Kullanım süresi

Bir spot aracın faturalandığı süre: **ilk yükleme başlangıcından son indirme
bitişine kadar tek, kesintisiz bir pencere.** Parçalı değil — araç durakta
beklerken de sayaç işler.

İki ayrı saat var ve karıştırılmamalı:

- **SLA saati** talebin tamamlanma anında başlar (09:00 ya da 17:00).
- **Kullanım süresi saati** aracın o yükü fiilen yüklemeye başladığı anda başlar.

İkisi de son indirme bittiğinde durur. Elleçleme süresi desi başına 0,01 dakika
ve yükleme ile indirme ayrı ayrı hesaplanır. Tüm süreler bir üst tam dakikaya
yuvarlanır.

### Maliyet formülü — üç terim

```
Toplam maliyet  =  (Saatlik kira × Kullanım süresi)
                +  (Mesafe × Km başı maliyet)
                +  (Geciken desi × ceil(Saat) × 0,40 ₺)
```

Şartnamede dördüncü bir kalem yoktur: sabit çağırma ücreti, boş dönüş bedeli,
bekleme ücreti ya da ceza katsayısı yok. Bu, optimizasyonun neyi hedefleyeceğini
tek başına belirler.

### ceil() — yukarı yuvarlama

`ceil(x)`, x'ten büyük veya ona eşit en küçük tam sayı. `ceil(2,1) = 3`,
`ceil(3,0) = 3`.

SLA cezasında geciken saat **yukarı yuvarlanır**: 2 saat 1 dakika gecikme
3 saatlik ceza demektir. Bu yüzden gecikmeyi 2 saat 1 dakikadan 2 saat 0 dakikaya
çekmek bir tam saatlik ceza kazandırır — küçük zaman iyileştirmelerinin
maliyette basamak basamak karşılığı var.

### SLA cezası — neden yasak değil

Şartnamede "en fazla şu kadar gecikebilir" diye bir üst sınır yok. Ceza
doğrusal ve hesaplanabilir. Dolayısıyla bir aracı yola çıkarmak, küçük bir
gecikme cezasından pahalıysa **cezayı satın almak doğru karardır**.

Nihai planımızda bu bilinçli olarak yapıldı: SLA cezası Stage 0'daki
1.020.367 ₺'den 2.615.532 ₺'ye **çıktı**, ama araç maliyeti 15.460.593 ₺'den
8.616.945 ₺'ye düştü. Net kazanç 5,25 milyon ₺.

> Bu, sunumun en güçlü noktalarından biri. Jüri "cezayı neden artırdınız"
> derse cevap hazır: toplam maliyeti optimize ediyoruz, tek bir kalemi değil.

### Greedy (açgözlü) yaklaşım — ve neden MILP değil

Greedy, her adımda o an en iyi görünen hamleyi yapıp devam eden yöntemdir.
Global en iyiyi garanti etmez, ama büyük arama uzaylarında hızlıdır ve
sonucu ölçülebilir.

Bizim yapımız dört aşamalı bir **iyileştirme merdiveni**: her aşama bir
öncekinin çıktısını girdi alır, kendi hamlesini dener, ve kabul kuralından
geçerse benimser.

**Neden karma tam sayılı programlama (MILP) kurmadık:** problem boyutu.
Stage 2'de tek başına 96.369 çoklu kombinasyon değerlendirildi; zincir uzunluğu,
zaman pencereleri, elleçleme kapasitesi ve araç tipi seçimi birlikte
modellendiğinde değişken sayısı pratik çözücü sınırlarının üstüne çıkıyor.
Ölçülebilir ve kural-güvenli bir merdiveni, çözülemeyen bir tam modele tercih
ettik. Sağ alttaki "neden greedy" kutusu bu sorunun ön cevabıdır.

### Milk-run (uğramalı zincir)

Aynı merkezden aynı anda kalkan birden çok aracın işini **tek bir fiziksel
araca** bindirip sırayla uğratmak. Süt toplama kamyonunun çiftlik çiftlik
dolaşmasından geliyor.

Zincir uzunluğu en fazla **4 durak**. Nihai planda 227 zincir kabul edildi:
127 tanesi 2 duraklı, 28 tanesi 3 duraklı, 72 tanesi 4 duraklı.

### Rota ortasında yük alma (Tier A)

Stage 2'ye kadar zincirlerimiz sadece **indiriyordu**: araç çıkışta her şeyi
yükler, her durakta bir kısmını bırakır, ara durakta yeni yük almaz.

Şartname bunun tersini açıkça serbest bırakıyor: bir araçtan x kadar yük
indirilip y kadar yük alınabilir. Stage 3 tam olarak bunu kullanıyor —
rotanın ortasındaki bir durakta yeni yük alıp taşımak.

### Hakem simülatörü

Planlayıcıdan **tamamen ayrı yazılmış ikinci bir uygulama**. Optimizatörün iç
durumunu hiç görmez; sadece çıktı Excel'ini ve ham veriyi okuyup maliyeti ve
17 kuralı sıfırdan yeniden hesaplar.

Amacı: "hesapladım, doğrudur" demeyi ortadan kaldırmak. İki bağımsız uygulama
aynı sayıya varıyorsa sayı güvenilirdir. Ölçülen fark: **0,0000 ₺**.

Kabul kuralı tek ve değişmez: hem taban plan hem aday plan hakemden
**sıfır ihlalle** geçecek. Geçmezse hamle reddedilir.

---

## Bölüm 2 — Slayt slayt anlatım

### 1. Takım

**Ekranda:** Dört kişilik takım kartı, fotoğraflar.

**Anlatım:** Takım Büke dört kişiyiz ve dördümüz de Bilgisayar Mühendisliği
okuyoruz. Melih Ekizce — İzmir Yüksek Teknoloji Enstitüsü, yüksek lisans devam
ediyor. Mustafa Eren Işıktaşlı — Yıldız Teknik Üniversitesi, yüksek lisans devam
ediyor. Serhat Özdemir ve Mert — takım kartındaki sırayla.

**Süre:** 20 saniye. Burada oyalanmayın.

---

### 2. Kapak

**Ekranda:** Başlık ve Hepsiburada logosu.

**Anlatım:** Bize verilen problem şu: bir haftalık talebi, onlarca operasyonel
kısıta uyarak **en düşük toplam maliyetle** taşıyan bir sevkiyat planı üretmek.
Sadece hangi aracın hangi hatta çalışacağını değil, hangi dakikada çıkacağını da
belirlemek zorundayız.

**Vurgu:** "Plan dakika çözünürlüğünde." Bu, problemi bir atama probleminden
çizelgeleme problemine çıkarıyor.

---

### 3. Problem

**Ekranda:** Ağ yapısı ve kısıt kartları. **12 tıklanabilir pop-up** var.

**Anlatım:** Ağ 18 transfer merkezi ve 306 yönlü hattan oluşuyor — 18×17 tam
matris. Geçmiş veride bunların **289'unda** gerçekten talep görülmüş.

Bizi sıkıştıran kısıtların en serti iki tane:

- **Elleçleme kapasitesi:** her merkezin günlük bir işlem limiti var ve gece
  yarısını geçen operasyonlarda gün ataması dikkat istiyor.
- **Tır kapasitesi:** yedi merkezde tır kapasitesi **sıfır** — tır oraya hiç
  giremez. Bu, "tam dolu tır her zaman en ucuzdur" sezgisini kırıyor.

**Teknik derinlik:** Kiralık filo 12 zorunlu rotada her gün çıkar, 14 araç.
Seçim hakkımız yok — batık maliyet. Spot araçlar ise tamamen bizim
kontrolümüzde ve sınırsız sefer yapabilir.

---

### 4. Maliyet modeli

**Ekranda:** Formül animasyonu ve zaman ekseni. İki tıklanabilir kart.

**Anlatım:** Maliyet üç terimin toplamı: araç süre maliyeti, araç mesafe
maliyeti, ve varsa SLA gecikme cezası. Dördüncü kalem yok.

Kritik tanım **kullanım süresi**. Jüri bunu üç ayrı soruda netleştirdi ve tanım
her seferinde aynı çıktı: ilk yükleme başlangıcından son indirme bitişine kadar
**tek sürekli pencere**. Bekleme de elleçleme de bu pencerenin içinde.

**Vurgu:** Örnek seferde toplam 6.564,14 ₺ — süre terimi %33,8, mesafe terimi
%66,2. Bu sayı elle hesaplanmadı: teslim ettiğimiz Excel'in *Toplam maliyet*
hücresiyle birebir aynı.

**Beklenen soru:** "Bekleme süresi neden faturaya giriyor?" → Çünkü araç o
sürede sizde. Şartname kullanım süresini tek pencere olarak tanımlıyor,
parçalı değil.

---

### 5. Veri

**Ekranda:** 179 günlük hacim eğrisi ve veri eleme şeması.

**Anlatım:** Geçmiş veri **66.024 satır**, 1 Ocak – 28 Haziran arası **179 gün**,
kesintisiz.

Grafikte hemen göze çarpan şey: **ayın son günü, her ay, normal bir günün
yaklaşık %2'sine iniyor.** Beş ayda beş kez, istisnasız. En düşük gözlem
2.010 desi — normal gün medyanı 939.989 iken.

**Vurgu:** Bu bizim için kritik, çünkü tahmin ufkumuzun içinde 30 Haziran var
ve o da bir ay sonu. Bu günü normal bir salı sayan bir model tek başına orada
yaklaşık **1,1 milyon desi** hata yapar.

**Teknik derinlik:** Ham 66.024 satır, 103.462 satırlık bir ızgaraya açılıyor.
23 tarih eğitimden dışlandı (13.294 ızgara satırı), geriye **90.168 satırlık
eğitim ızgarası** kaldı. Her dışlanan tarihin gerekçesi tek tek yazılı —
pop-up'ta liste var.

---

### 6. Tahmin modeli

**Ekranda:** Takvim çarpanları grafiği ve tahmin-vs-haftagünü karşılaştırması.

**Anlatım:** Model iki katmanlı ve **kasten sade**.

Taban katman: her çıkış-varış-slot-haftagünü kombinasyonu için, hedef tarihten
kesin önceki **son dört gözlemin medyanı**. Medyan, çünkü ortalama tek bir
sıçramadan bozuluyor.

İkinci katman **takvim çarpanı**. Soldaki üç sayı uydurma değil, geçmiş ay
sonlarından ölçüldü: ay sonundan bir önceki gün ×0,6752; ayın son günü ×0,0198;
ayın ilk günü ×1,2072.

**Vurgu:** "Çarpanlar seçilmedi, ölçüldü." Her çarpan beş ay sonundan alınan
beş oranın medyanı — o günün gerçekleşeni bölü aynı hücrelerin taban toplamı.
Tabana bölmek, ay sonu etkisini haftagünü etkisinden ayırıyor.

**Beklenen soru:** "Neden derin öğrenme kullanmadınız?" → 179 günlük veri ve
haftalık bir ufuk için parametre sayısı veriden fazla olurdu. Ölçtük: iki
katmanlı model naive çıtayı da, tek katmanlı DOW medyanını da yeniyor.
Karmaşıklık ancak ölçülen bir kazanç getiriyorsa hak edilir.

---

### 7. Merdiven

**Ekranda:** Dört aşamalı maliyet merdiveni, yığılmış sütunlar.

**Anlatım:** **Bu sunumun kalbi burası.** Planı tek hamlede kurmuyoruz.
Dört aşama var; her aşama bir öncekinin çıktısını girdi olarak alıyor ve kendi
iyileştirmesini deniyor.

Kabul kuralı tek ve değişmez: hem taban plan hem aday plan hakem
simülatöründen **sıfır ihlalle** geçecek, ve toplam maliyet düşecek.
İkisinden biri sağlanmazsa hamle reddedilir.

| Aşama | Rota | Araç maliyeti | SLA cezası | Toplam | Kümülatif |
|---|---:|---:|---:|---:|---:|
| Stage 0 | 1.269 | 15.460.593 ₺ | 1.020.367 ₺ | 16.480.960 ₺ | — |
| Stage 1 | 1.092 | 12.510.401 ₺ | 2.169.784 ₺ | 14.680.185 ₺ | −%10,9 |
| Stage 2 | 693 | 8.752.512 ₺ | 2.560.826 ₺ | 11.313.338 ₺ | −%31,4 |
| Stage 3 | 665 | 8.616.945 ₺ | 2.615.532 ₺ | **11.232.477 ₺** | **−%31,8** |

**Vurgu:** SLA cezasının **arttığına** dikkat çekin ve nedenini hemen söyleyin —
araç maliyetinden çok daha fazlasını kazanıyoruz. Dört aşamanın dördünde de
ihlal sayısı sıfır.

---

### 8. Stage 0 — Temel plan

**Ekranda:** Aşama açıklaması.

**Anlatım:** Stage 0 kısıtları sağlayan **ilk geçerli planı** kuruyor.
Sıra önemli:

1. **Önce zorunlu kiralık filo.** Onlar zaten çıkacak — günde 42 bin lira
   batık maliyet. O trunk'ları boş göndermek saf israf, o yüzden önce
   onları dolduruyoruz.
2. **Sonra tır ziyaret bütçesi.** Yedi merkezde tır kapasitesi sıfır olduğu
   için tır rotaları sınırlı ve dikkatli dağıtılmalı.
3. **Sonra spot araçlar** kalan yükü alıyor.

**Çıktı:** 1.269 rota (126 kiralık + 1.143 spot), 16.480.960 ₺, 0 ihlal.
Ortalama doluluk %48,02 — spot araçların 480'i %30'un altında dolu.

**Vurgu:** Bu bir optimizasyon değil, **geçerli bir başlangıç**. Asıl kazanç
sonraki üç aşamada.

---

### 9. Stage 1 — Aynı-hat onarımı

**Ekranda:** Aşama açıklaması.

**Anlatım:** En basit fikir: aynı gün, aynı hatta çalışan iki araçtan birinin
yükü diğerine sığıyorsa, o aracı **tamamen sil**.

**1.003 donör adayına** baktık, **177'si** kabul edildi. 177 spot araç plandan
tamamen kayboldu.

**Kazanç:** 1,8 milyon ₺, %10,9. Doluluk %48,02'den %56,82'ye çıktı,
%30 altı araç sayısı 480'den 296'ya indi.

**Vurgu:** Buradaki kazanç tamamen **boşa giden kapasitenin** toplanmasından
geliyor. Yeni bir araç çıkarmıyoruz, var olanı dolduruyoruz.

---

### 10. Stage 2 — Milk-run

**Ekranda:** Arama hunisi ve zincir dağılımı grafikleri. İki pop-up.

**Anlatım:** **En büyük kazancı getiren aşama.** Fikir: aynı merkezden aynı
anda kalkan 2 ile 4 araç varsa, bunları tek bir fiziksel araca zincirleyip
sırayla uğratabilir miyiz?

**Arama hunisi:** 93 aday grup → 5.426 ikili kombinasyon → 96.369 çoklu
kombinasyon → **227 zincir kabul**.

Kabul edilen zincirlerin dağılımı: 127 tanesi 2 duraklı, 28 tanesi 3 duraklı,
72 tanesi 4 duraklı. Bu zincirler **626 kaynak aracın** yerine geçti,
2.110 yük parçasını birleştirdi, 1.675.453 desi taşıdı.

**Kazanç:** Toplam 11.313.338 ₺'ye iniş — kümülatif %31,4. Rota sayısı
1.092'den 693'e düştü. Doluluk %76,96.

**Vurgu:** "96 bin kombinasyon denedik, 227'sini kabul ettik." Kabul oranının
düşüklüğü kural disiplininin kanıtı — her aday hakemden sıfır ihlalle geçmek
zorundaydı.

---

### 11. Stage 3 — Rota ortasında yük alma

**Ekranda:** Yük alma hunisi ve durak şeması. Bir pop-up.

**Anlatım:** Stage 2'ye kadar zincirlerimiz sadece **indiriyordu**: araç çıkışta
her şeyi yükler, her durakta bir kısmını bırakır, ara durakta yeni yük almaz.

Jüri bunun tersini açıkça serbest bırakıyor. Altıncı soruda "bir araçtan x kadar
yük indirilip y kadar yük alınabilir" diyor. Stage 3 tam olarak bunu kullanıyor.

**Arama:** 227 rota incelendi (126 kiralık rota atlandı), 340 donör aday,
**135.660 çift** değerlendirildi, 56'sı kârlı çıktı, **28'i kabul edildi**.
28 donör araç plandan silindi, 82 yük parçası, 65.754 desi.

**Kazanç:** 80.862 ₺. Toplam 11.232.477 ₺ — kümülatif %31,8.

**Vurgu:** Kazanç küçük ama **meşruiyeti önemli**. Soldaki kod kutusunu gösterin:
bir yük alma durağında iki ayrı zaman damgası okunuyor — bu aşamanın kural
uyumu oradan geliyor. `rejected_by_ledger: 0` — defter tutarsızlığı nedeniyle
reddedilen hamle olmadı.

---

### 12. Filo

**Ekranda:** Üç grafik — araç sayısı, doluluk dağılımı, araç türü karması.

**Anlatım:** Üç grafik, tek hikâye.

**Solda araç sayısı:** 1.269'dan **665'e**, %47,6 düşüş.

**Ortada doluluk dağılımı** (kümülatif eğri — ne kadar sağdaysa o kadar iyi).
Stage 0'da spot araçların %42'si yarıdan az doluydu: 1.143 aracın 480'i
%30'un altında. Stage 3'te bu sayı **30'a** indi. Ortalama doluluk
%48,02 → **%79,03**.

**Sağda araç türü karması:**

| Tür | Stage 0 | Stage 3 |
|---|---:|---:|
| Kamyonet | 950 | 233 |
| Kamyon | 196 | 304 |
| Hafif Kamyon | 24 | 29 |
| Tır | 99 | 99 |

**Vurgu:** Kamyonet azaldı, kamyon arttı, tır **hiç değişmedi**. Sebep:
kapasite başına maliyet. Kamyon 12.000 desiyi 318,25 ₺/sa ile taşır; tır
22.400 desiyi 487,50 ₺/sa ile. Tır ancak **tam dolu** giderse desi başına öne
geçer — ve yedi merkezde tır kotası sıfır olduğu için tam dolu bir tır rotası
çoğu zaman kurulamaz.

---

### 13. Hakem

**Ekranda:** 17 kural tablosu, "0 ihlal" vurgu şeridi. Bir pop-up.

**Anlatım:** Bu projede tek bir sayıya bile "hesapladım, doğrudur" demiyoruz.

Hakem simülatörü planlayıcıdan **tamamen ayrı yazılmış ikinci bir uygulama**.
Optimizatörün iç durumunu hiç görmüyor — sadece çıktı Excel'ini ve ham veriyi
okuyup maliyeti ve 17 kuralı sıfırdan yeniden hesaplıyor.

**Sonuç:** 17 kuralın hepsinde **0 ihlal**. Bizim hesabımız ile hakemin farkı
**0,0000 ₺**.

**Vurgu:** Bu bir test değil, **bağımsız ikinci uygulama**. İki ayrı kod tabanı
aynı sayıya varıyorsa sayı güvenilirdir. Ayrıca merdivendeki her aşamanın kabul
kuralı buydu — hakemden geçmeyen hamle plana girmedi.

---

### 14. Özet

**Ekranda:** Dört katmanın özeti.

**Anlatım:** Toparlayayım. Çözüm dört katmandan oluşuyor:

1. **Talep tahmini** — iki katmanlı, kasten sade: haftagünü medyanı × ölçülmüş
   takvim çarpanı.
2. **Dört aşamalı maliyet merdiveni** — temel plan, aynı-hat onarımı, milk-run
   zincirleri, rota ortasında yük alma.
3. **Hakem simülatörü** — bağımsız doğrulama, her aşamada sıfır ihlal şartı.
4. **Final entegrasyon katmanı** — teslim formatı ve çapraz doğrulama.

**Kapanış sayıları:** Maliyet 16.480.960 ₺ → **11.232.477 ₺** (−%31,8).
Filo 1.269 → **665 araç** (−%47,6). Doluluk %48 → **%79**. İhlal: **0**.

---

### 15. Sorular

**Ekranda:** Teşekkür ve kapanış.

**Anlatım:** Teşekkür ederiz. Sorularınızı bekliyoruz.

**Hazır olduğumuz ama sunumda değinmediğimiz konular:**

- Arama uzayının nasıl budandığı
- Kural yorumlarımızın şartnamedeki dayanağı
- Ölçüp **reddettiğimiz** altı fikir
- Açık kalemlerimiz ve bilinen sınırlarımız

> "Denedik, ölçtük, reddettik" bölümünü açmaya hazır olun. Reddedilen fikirleri
> sayı ile anlatabilmek, kabul edilenleri anlatmak kadar güçlü bir sinyaldir.

---

## Ezberlenecek on sayı

| Sayı | Ne |
|---:|---|
| **66.024** | Geçmiş talep satırı, 179 gün |
| **18 / 306 / 289** | Merkez / yönlü hat / talep görülen hat |
| **×0,0198** | Ay sonu takvim çarpanı — hacmin %98'i kaybolur |
| **0,4464** | Ay sonu haftası wMAPE (DOW medyanı 0,5328) |
| **16,48 M ₺ → 11,23 M ₺** | Toplam maliyet, −%31,8 |
| **1.269 → 665** | Fiziksel araç, −%47,6 |
| **%48 → %79** | Ortalama doluluk |
| **227** | Kabul edilen milk-run zinciri (96.369 denemeden) |
| **28** | Kabul edilen rota ortası yük alma (135.660 çiftten) |
| **0 ihlal · 0,0000 ₺** | Hakem simülatörü sonucu |
