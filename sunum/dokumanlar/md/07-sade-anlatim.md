# Modelimiz ve Algoritmamız — Sade Anlatım

TEKNOFEST 2026 · Hepsiburada · Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · Takım Büke

Bu belge, teknik raporlarda anlatılan tahmin modelimizi ve optimizasyon algoritmamızı **jargonsuz** anlatır. Amaç, konuya uzak bir okuyucunun bile "ne yaptık, neden yaptık, nasıl ölçtük" sorularının cevabını baştan sona takip edebilmesidir.

Her terim ilk geçtiği yerde tanımlanır. Belgedeki tüm sayılar teslim paketindeki koddan veya ölçülmüş koşum çıktılarından gelir; hiçbiri tahminî değildir. Terimlerin toplu listesi belgenin sonundaki sözlüktedir.

---

## 1. Bir Cümlede Ne Yaptık

Yarışma bizden **iki ayrı iş** istiyor ve biz de iki ayrı program yazdık:

| Sıra | İş | Girdi | Çıktı |
|---|---|---|---|
| 1 | **Talep tahmini** | 179 günlük geçmiş sipariş verisi | Gelecek haftanın hangi hatta, hangi gün, hangi saatte kaç desi yük çıkacağı |
| 2 | **Taşıma planı optimizasyonu** | O tahmin tablosu | Hangi yükün hangi araca bineceği, aracın ne zaman kalkacağı, toplam maliyetin ne olacağı |

Birinci program **geleceği tahmin eder**, ikinci program **o geleceğe en ucuz cevabı üretir**. İkisi birbirinden tamamen ayrıdır: final değerlendirmesinde jüri bize kendi talep tablosunu verecek ve yalnız ikinci program çalışacaktır.

Ölçülmüş sonuç: baştaki akla gelen ilk geçerli plan **16.480.960 TL** tutuyordu. Teslim ettiğimiz plan **11.232.477 TL**. Fark **5.248.483 TL**, yani **yüzde 31,84 tasarruf**. Aradaki her adımı bu belgede tek tek açıyoruz.

---

## 2. Birinci İş — Talep Tahmini

### 2.1 Tam olarak neyi tahmin ediyoruz

Türkiye'de **18 transfer merkezi** var. Bir merkezden bir başkasına giden yola **hat** diyoruz. Geçmiş veride fiilen yük görülen **289 hat** var.

Her gün **iki kez** talep toplanıyor: saat **09:00** ve saat **17:00**. Bunlara **slot** diyoruz.

Tahmin ettiğimiz en küçük birim bu üçlünün kesişimi:

```
bir hücre = (hangi gün, hangi hat, hangi slot)
```

Bir haftalık ufuk için toplam hücre sayısı:

```
289 hat  x  7 gün  x  2 slot  =  4.046 hücre
```

Teslim ettiğimiz tahmin dosyası tam olarak bu 4.046 satırdır. Her satırda tek bir sayı vardır: **o hücrede kaç desi yük oluşacak**. Desi, hacim ölçüsüdür.

### 2.2 Bu, tek bir zaman serisi değil

Yaygın hata şudur: "günlük toplam hacmi tahmin et, sonra hatlara dağıt". Biz bunu yapmadık, çünkü hatlar birbirine benzemiyor.

```
289 hat  x  2 slot  =  578 ayrı zaman serisi
```

Her hat kendi hikâyesini yaşıyor. Üstelik iki slotun ölçeği bile farklı: **17:00 slotu toplam desinin yüzde 91,24'ünü**, 09:00 slotu yalnız **yüzde 8,76'sını** taşıyor. Bu yüzden tahmin, 578 serinin **her biri için ayrı ayrı** yapılır.

### 2.3 Verinin gerçek zorluğu: seyreklik

Elimizdeki geçmiş 66.024 satır, 179 gün. Ama 179 günü 289 hat ve 2 slotla çarparsak:

```
289  x  179  x  2  =  103.462 hücre
```

Yani veri satırlarının çoğu **yok**. Bu bir eksiklik değil, bilginin kendisidir: veride görünmeyen hücre, **o gün o hatta o saatte hiç yük çıkmadı** demektir. Biz de tam gridi kurup boş hücrelere sıfır yazdık.

Bunu yapmasaydık model, yük çıkmayan günleri hiç görmeyecek ve her hücreyi olduğundan büyük tahmin edecekti.

### 2.4 DOW medyan nedir

**DOW**, İngilizce *day of week* kısaltmasıdır: haftanın günü. Modelimizin temel katmanı tek bir cümlede özetlenir:

> Bir salı gününü tahmin etmek için, **aynı hattın, aynı slotunun, geçmişteki son 4 salısına** bak ve o dört sayının **ortancasını** al.

Somut örnek. 2 Temmuz salı günü, Yalova - Balıkesir hattı, 17:00 slotu tahmin edilecek olsun. Model geçmişte aynı hücrenin son dört salısına bakar:

| Geçmiş salı | Gerçekleşen desi |
|---|---|
| 4 hafta önce | 11.800 |
| 3 hafta önce | 12.400 |
| 2 hafta önce | 12.050 |
| 1 hafta önce | 12.200 |

Bu dördünün ortancası **12.125** desidir ve taban tahmin budur.

Dört tasarım kararı var, dördü de gerekçeli:

**Neden aynı hat?** Her hattın ölçeği farklı. İstanbul çıkışlı bir hat ile Karaman çıkışlı bir hattın sayılarını karıştırmak ikisini de bozar.

**Neden aynı slot?** 17:00 slotu 09:00'un on katından fazla yük taşıyor. İkisini birleştirmek her ikisini de yanlış tahmin etmek demektir.

**Neden aynı haftagünü?** Sipariş davranışı haftanın gününe güçlü biçimde bağlı. Salıyı pazarla aynı kefeye koymak sistematik hata üretir.

**Neden ortalama değil ortanca (medyan)?** Ortalama tek bir uç değerden bozulur, ortanca bozulmaz. Örnek:

| Ölçüm | Dört salının değerleri | Sonuç |
|---|---|---|
| Ortalama | 100, 110, 105, 900 | 303,75 |
| Ortanca | 100, 110, 105, 900 | 107,50 |

Dördüncü salıda bir kampanya olmuş olsun. Ortalama tahmini **üç katına** çıkarır ve model haftalarca bu hatayı taşır. Ortanca aynı veriyle 107,5 der, yani olağan salı davranışını korur. Lojistik verisi tam da böyle ani sıçramalar içerdiği için ortanca seçtik.

**Neden son 4?** Dört hafta iki şeyi birden dengeler: ortanca alabilmek için yeterli örnek, ve mevsimsel kaymadan etkilenmeyecek kadar güncel bir pencere. Beş ay öncesinin salısı bugünün salısı hakkında az şey söyler.

### 2.5 Takvim çarpanı nedir

DOW medyan tek başına şunu varsayar: her salı diğer salılara benzer. Veri bunun **doğru olmadığı** günler olduğunu gösteriyor.

Aşağıdaki tablo, geçmiş verideki her ay sonunu ve komşu günlerini ham desi olarak gösteriyor. Hiçbir model yok, sadece gerçekleşen toplamlar:

| Ay | İki gün önce | Bir gün önce | Ayın son günü | Ertesi gün |
|---|---|---|---|---|
| Ocak | 780.635 | 529.434 | **7.852** | 122.493 |
| Şubat | 884.554 | 678.251 | **14.843** | 101.882 |
| Mart | 82.097 | 1.147.893 | **24.059** | 1.091.999 |
| Nisan | 925.820 | 667.562 | **8.622** | 86.753 |
| Mayıs | 3.077 | 42.971 | **2.010** | 2.637.199 |

Desen tartışmasız: **ayın son günü sistem neredeyse duruyor.** Muhtemel sebebi ay sonu muhasebe kapanışıdır, ama sebebini bilmemize gerek yok. Ölçmemiz yeterli.

DOW medyan bu günü göremez, çünkü geçen dört salının arasında bir tanesi ay sonuysa ortanca onu zaten dışlar. İşte **takvim çarpanı** bu boşluğu kapatan ikinci katmandır.

Modelimiz her günü dört **role** ayırır ve her role bir çarpan verir:

| Rol | Ne demek | Ölçülen çarpan |
|---|---|---|
| Ayın son günü | Ay kapanışı | **x 0,0198** |
| Sondan bir önceki gün | Kapanışa hazırlık | **x 0,6752** |
| Ayın ilk günü | Ertelenen talebin telafisi | **x 1,2072** |
| Normal gün | Diğer tüm günler | **x 1,0000** |

Okunuşu şöyle: ayın son gününde, o hattın olağan seviyesinin yalnız **yüzde 2'si** kadar yük bekleriz. Sondan bir önceki gün olağanın **üçte ikisi**. Ayın ilk günü ise olağanın **yüzde 21 üstü**, çünkü ay sonunda ertelenen talep kaybolmuyor, ertesi güne kayıyor.

**Bu çarpanları biz seçmedik, veriden ölçtük.** Yöntem şudur: geçmişteki her ay sonu günü için, sanki o günü hiç görmemiş gibi bir DOW medyan tabanı hesaplarız; sonra o günün gerçekleşen toplamını bu tabana böleriz. Elde edilen oranların **ortancası** o rolün çarpanı olur.

Üç koruma var:

- **Taban hesabına olay günleri girmez.** Ay sonlarını ve resmî tatilleri geçmiş verisinden çıkarırız (toplam 23 gün), yoksa olağan tanımı kirlenir.
- **Sızıntı yasağı.** Bir çarpan hesaplanırken yalnız hedef günden **önceki** gözlemler kullanılır. Geleceği bilerek geçmişi açıklamak, gerçekte olmayan bir başarı üretirdi.
- **En az iki örnek kuralı.** Bir rol için elde iki sonlu oran yoksa çarpan **1,0** kalır, yani model karışmaz. Tek bir örnekten çarpan üretmek, gürültüyü kural sanmaktır.

### 2.6 Tahmin formülü tek satırda

```
tahmin = DOW medyan tabanı  x  o günün takvim çarpanı
```

Sonuç negatifse sıfıra çekilir ve en yakın tam sayıya yuvarlanır. Modelin tamamı budur: iki katman, dört çarpan, bir pencere uzunluğu (k = 4).

Ufuktaki 4.046 hücrenin **1.121'ine sıfır** tahmini verdik ve bu doğru davranıştır: o hücrelerde geçmişin dört aynı gününde de yük çıkmamış.

### 2.7 Naive ne anlamda kullanılıyor

**Naive** burada aptal anlamında değil, istatistikteki teknik anlamıyla kullanılır: **karşılaştırma çıtası**, yani *benchmark*.

Naive modelimiz şudur:

> Gelecek salıya ne kadar yük çıkacak? Geçen salı ne çıktıysa o.

Kod düzeyinde: aynı hücrenin **7 gün önceki** değerini kopyala. Hepsi bu.

Bu model neden var? Çünkü her karmaşık modelin ispat borcu vardır. Bir model, "geçen hafta ne olduysa aynısı olur" demekten daha iyi değilse, kurduğunuz tüm yapı boşunadır. Naive, bizim modelimizin gerçekten bir katkı sağlayıp sağlamadığını ölçtüğümüz sıfır noktasıdır.

### 2.8 wMAPE nedir

**wMAPE**, İngilizce *weighted Mean Absolute Percentage Error* kısaltmasıdır: **ağırlıklı ortalama mutlak yüzde hata**. Tahminin ne kadar isabetli olduğunu tek bir yüzdeyle söyler. Formülü:

```
wMAPE  =  toplam |gerçek - tahmin|  /  toplam gerçek
```

Yani bütün hücrelerdeki hataların mutlak büyüklüğünü desi cinsinden toplarız, sonra gerçekleşen toplam desiye böleriz. Küçük olması iyidir; sıfır mükemmel demektir.

Üç hücrelik bir örnek:

| Hücre | Gerçek | Tahmin | Mutlak hata |
|---|---|---|---|
| A | 10.000 | 9.000 | 1.000 |
| B | 5.000 | 6.000 | 1.000 |
| C | 100 | 150 | 50 |
| **Toplam** | **15.100** | **15.150** | **2.050** |

```
wMAPE = 2.050 / 15.100 = 0,1358  ->  yüzde 13,58
```

**Neden düz MAPE değil?** Klasik MAPE her hücrenin kendi yüzde hatasını alıp ortalar. Bizim problemimizde bu iki nedenle çöker:

1. **Sıfıra bölme.** Ufkun 1.121 hücresinde gerçek değer sıfırdır. Sıfıra bölemezsiniz; o hücreleri atmak da onları görmezden gelmek olur.
2. **Küçük hücrelerin haksız ağırlığı.** Yukarıdaki C hücresinde 50 desilik hata MAPE'de yüzde 50 sayılır ve A hücresindeki 1.000 desilik hatayla (yüzde 10) aynı ağırlıkta ortalamaya girer. Oysa şirketin kamyonunu 1.000 desilik hata doldurur, 50 desilik hata değil.

wMAPE hataları **desi cinsinden** topladığı için her hücre gerçek büyüklüğü kadar söz sahibi olur. Bu yüzden lojistik ve perakende talep tahmininde standart ölçüttür.

### 2.9 Ölçülmüş sonuçlar

İki farklı hafta üzerinde geriye dönük test (backtest) yaptık. Testin kuralı şu: model o haftayı tahmin ederken **yalnız o haftadan önceki** veriyi görür.

| Test haftası | Naive | Yalnız DOW medyan | Bizim modelimiz |
|---|---|---|---|
| Normal hafta (15-21 Haziran) | yüzde 25,92 | yüzde 21,74 | **yüzde 21,74** |
| Ay sonu haftası (30 Mart - 5 Nisan) | yüzde 69,72 | yüzde 53,28 | **yüzde 44,64** |

Tablodan okunacak üç şey var:

**Birincisi**, DOW medyan katmanı normal haftada naive'e göre hatayı **4,2 puan** düşürüyor. Yani "geçen hafta ne olduysa o" demek yerine "son dört aynı günün ortancası" demek gerçekten kazandırıyor.

**İkincisi**, normal haftada bizim modelimiz ile yalnız DOW medyan **birebir aynı**. Bu bir eksiklik değil, tasarımın kanıtı: o haftada ay sonu ya da ayın ilk günü yok, dolayısıyla takvim çarpanı **1,0** ile devreye girip hiçbir şeyi bozmuyor. Model gereksiz yere karışmıyor.

**Üçüncüsü**, takvim katmanının bedelini ödediği yer ay sonu haftası: hata **yüzde 53,28'den yüzde 44,64'e** iniyor, yani **8,6 puanlık** düşüş. Naive ile aramızdaki fark ise **25 puan**.

### 2.10 Sızıntı koruması

**Sızıntı** (İngilizcesi *leakage*), modelin tahmin ederken görmemesi gereken bilgiyi kazara görmesidir. Bir modele geleceği gösterirseniz testte mükemmel görünür, sahada çuvallar.

Üç ayrı kilit koyduk:

- Tahmin fonksiyonu, geçmiş tablosunda **ufuk içi bir satır görürse çalışmayı reddeder** ve hata verir. Yani sızıntı bir uyarı değil, programın durma sebebidir.
- DOW medyan her hücre için yalnız **hedef tarihten kesinlikle önceki** gözlemleri kullanır.
- Takvim çarpanları da aynı kurala tabidir ve taban hesabından olay günleri dışlanır.

---

## 3. İkinci İş — Taşıma Planı Optimizasyonu

### 3.1 Ödediğimiz üç kalem

Optimizasyonun neyi küçültmeye çalıştığını bilmek için önce faturayı bilmek gerekir. Şartnamede **yalnız üç** maliyet kalemi vardır, dördüncüsü yoktur:

| Kalem | Formül | Örnek sefer |
|---|---|---|
| Araç süresi | saatlik kira x kullanım süresi | 318,25 TL/sa x 6,97 sa = 2.217,14 TL |
| Araç mesafesi | km başı ücret x mesafe | 21 TL/km x 207 km = 4.347,00 TL |
| SLA cezası | geciken desi x gecikilen saat x 0,40 TL | gecikme yok, 0,00 TL |

Örnekteki sefer nihai planımızdan gerçek bir kayıttır (Yalova - Balıkesir, tam dolu kamyon): toplam **6.564,14 TL**.

Sabit çağırma ücreti, boş dönüş bedeli, günlük taban ücret veya bekleme ücreti **yoktur**. Bu, optimizasyonun neyi hedefleyeceğini tek başına belirler: **daha az araç, daha kısa süre, daha az gecikme.**

Kritik tanım: **kullanım süresi**, aracın ilk yükleme başlangıcından son indirme bitişine kadar geçen **tek, kesintisiz** penceredir. Araç yolda mı, merkezde bekliyor mu, elleçleniyor mu fark etmez; pencerenin içindeki her dakika ödenir. Bu yüzden aracı doldurmak için beklemek bedavaya gelmez.

Elleçleme (yükleme veya indirme) desi başına **0,01 dakika** sürer ve yükleme ile indirme ayrı ayrı hesaplanır. Tüm süreler bir üst tam dakikaya yuvarlanır.

### 3.2 Uymak zorunda olduğumuz kısıtlar

| Kısıt | Ne diyor |
|---|---|
| Elleçleme kapasitesi | Her merkezin günlük işlem limiti var; gece yarısını aşan bir elleçleme iki güne bölünür |
| Tır ziyaret kapasitesi | Bazı merkezler günde sınırlı sayıda tır kabul eder, yedi merkez ise hiç kabul etmez |
| Kiralık filo | Her gün çıkmak zorunda, kendi hattı dışına çıkamaz, uğrama yapamaz, günde en fazla bir bacak |
| Araç kapasitesi | Kamyonet 5.600, Hafif Kamyon 7.200, Kamyon 12.000, Tır 22.400 desi |
| Zaman tutarlılığı | Bir araç önceki işini bitirmeden yeni yük alamaz; yük hazır olmadan yüklenemez |

### 3.3 Algoritma: dört aşamalı merdiven

Optimizasyonumuz tek bir dev denklem çözmez. Bunun yerine **geçerli bir plandan başlar ve onu adım adım ucuzlatır.** Her adım kendi başına çalışır ve her adımın çıktısı bağımsız bir denetimden geçer.

**Aşama 0 — Temel plan.** Kısıtları sağlayan ilk geçerli planı üretir. Sırayla: kiralık araçları kendi hatlarının yüküyle doldurur (zaten ödenmiş, marjinal maliyeti neredeyse sıfır), kıt tır ziyaretlerini en çok kazandıracak hatlara dağıtır, sonra her hat ve gün için **araç karmasını sayarak dener**. Yani "1 kamyon mu, 2 kamyonet mi, 1 kamyon artı 1 kamyonet mi" seçeneklerinin hepsini fiyatlar ve en ucuzunu seçer. Ayrıca "bu yükü bugün taşımayıp yarınki dalgaya bırakmak daha mı ucuz" sorusunu da fiyatlayıp cevaplar.

Sonuç: **1.269 araç, 16.480.960 TL, 0 ihlal.**

**Aşama 1 — Aynı-hat onarımı.** Aynı gün aynı hatta çıkan yarı boş araçlara bakar ve birinin yükünü diğerine aktarabiliyorsa aktarır; boşalan aracı plandan siler. 1.003 aday incelendi, **177 araç silindi.**

Sonuç: **1.092 araç, 14.680.185 TL.**

**Aşama 2 — Milk-run, yani uğramalı zincir.** Buradan sonrası asıl kazancın geldiği yer. Kural şu: bir **spot** araç tek seferde **birden fazla merkeze uğrayıp** sırayla yük bırakabilir. Kiralık araç bunu yapamaz.

Somut örnek: A merkezinden B'ye giden yarı dolu bir araç ve A'dan C'ye giden bir başka yarı dolu araç varsa, tek araca ikisinin yükünü koyup A, B, C sırasını yürütmek genellikle daha ucuzdur. İki araç yerine bir araç ödersiniz; karşılığında ek mesafe ve ek elleçleme ödersiniz. Algoritma bu iki tarafı da hesaplar ve **yalnız net kazanç varsa** kabul eder.

En fazla **4 duraklı** zincirlere kadar aradık. 5 duraklı zinciri de denedik ama kaba kuvvetle çözülemedi: aday altküme sayısı 254.992'ye, her biri 120 durak sırasına çıkıyor ve 13,5 dakika CPU ile 1,3 GB bellekten sonra sonuç alınamıyor. Bu sınır bizim kararımızdır, şartnamede yoktur.

93 grup incelendi, 5.426 ikili ve 96.369 üçlü fiyatlandı, **227 zincir kabul edildi** ve **626 araç** plandan çıktı.

Sonuç: **693 araç, 11.313.338 TL.**

**Aşama 3 — Rota ortasında yük alma.** Aşama 2'deki zincirler yalnız yük **bırakır**. Jüri soru-cevabı bunun tersini de açıkça serbest bırakıyor: bir araçtan yük indirilip yeni yük **yüklenebilir**.

Bu aşamada, zaten yoldan geçen bir araca ara duraktan yük bindiririz. Ama tek bir koşulla: **alınan yükün varış merkezi, rotanın zaten uğradığı bir durak olmalı.** Böylece rota hiç uzamaz, sadece dolar. Yükü tamamen devredilen araç plandan silinir.

227 rota tarandı, 135.660 ikili incelendi, **28 yük alma kabul edildi** ve 28 araç daha çıktı.

Sonuç: **665 araç, 11.232.477 TL.**

### 3.4 Merdivenin tamamı

| Aşama | Araç | Toplam maliyet | Ortalama doluluk |
|---|---|---|---|
| Aşama 0 | 1.269 | 16.480.960 TL | yüzde 48,0 |
| Aşama 1 | 1.092 | 14.680.185 TL | yüzde 56,8 |
| Aşama 2 | 693 | 11.313.338 TL | yüzde 77,0 |
| Aşama 3 | **665** | **11.232.477 TL** | **yüzde 79,0** |

Araç sayısı **yüzde 47,6 azaldı**, ortalama doluluk **yüzde 48'den 79'a** çıktı, toplam maliyet **yüzde 31,84 düştü**. Yarıdan az dolu spot araç sayısı da 480'den **30'a** indi.

### 3.5 Kabul kuralı: daha az araç değil, daha ucuz

Her aşamanın sonunda tek bir soru sorulur:

> Bu aday plan, önceki plandan **en az 1 TL daha ucuz mu** ve **sıfır ihlal** veriyor mu?

Cevap hayırsa aday **atılır** ve önceki plan korunur. Bu ayrım önemlidir: araç sayısını azaltmak her zaman ucuzlatmaz. Bir aracı zincire katmak mesafeyi uzatabilir, elleçlemeyi artırabilir, SLA cezası doğurabilir. Bu yüzden ölçüt araç sayısı değil, **hakemin hesapladığı toplam maliyettir.**

Nitekim aşama aşama SLA cezası artıyor (1,02 milyondan 2,62 milyona), ama araç maliyeti çok daha fazla düşüyor (15,46 milyondan 8,62 milyona). Toplam kazandığı için kabul ediliyor.

---

## 4. Bu İşin Neresinde Yapay Zekâ Var

Bu soruyu dürüstçe cevaplamak istiyoruz, çünkü cevabı hem hayır hem evet içeriyor.

### 4.1 Hazır bir makine öğrenmesi kütüphanesi kullanmadık

Çalışma zamanı bağımlılıklarımız yalnız iki pakettir: **pandas** ve **openpyxl**. Yani veri okuma ve Excel yazma. Ortada scikit-learn, XGBoost, LightGBM, Prophet ya da bir sinir ağı yok.

### 4.2 Ama parametreleri veriden öğrenen bir model var

Modelimizin hiçbir sayısı elle girilmemiştir. Dört takvim çarpanının dördü de geçmiş veriden, sızıntısız bir prosedürle **ölçülmüştür**. DOW medyan tabanı da her hücre için veriden hesaplanır. Bu, dar anlamıyla bir **istatistiksel öğrenme** modelidir: veriden parametre çıkarır, o parametrelerle geleceği tahmin eder, ve başarısı geriye dönük testle ölçülür.

Fark şudur: modelin **her adımı açıklanabilir**. "Neden bu hücreye 12.125 desi dedin" sorusunun cevabı tek satırdır. Bir gradyan artırma modelinde bu cevabı vermek çok daha zordur.

### 4.3 Neden daha ağır bir model kurmadık

Denemedik değil, **denedik ve ölçtük**. Karar gerekçeleri:

**Örnek sayısı yetersiz.** Elimizde beş aylık veri var, yani ay sonu rolü için **beş örnek**, bazı roller için **iki örnek**. İki örnekle bir ağaç modeli eğitmek öğrenmek değil, ezberlemektir.

**Sızıntı riski.** Karmaşık öznitelik mühendisliği, gelecek bilgisini kazara geçmişe taşımanın en kolay yoludur. Bunu kabul edilemez bulduk ve modeli, sızıntının yapısal olarak imkânsız olduğu kadar sade tuttuk.

**Determinizm zorunluluğu.** Jüri kodu kendi makinesinde çalıştıracak. Rastgele başlatmalı bir model aynı girdiyle farklı çıktı verebilir. Bizim planımız karıştırılmış girdiyle bile **birebir aynı** çıkıyor ve bunu ayrıca test ediyoruz.

**Süre bütçesi.** Şartname 100 dakikalık tavan koyuyor ve internet erişimi yok. Ölçülen uçtan uca süremiz **150 saniye**, yani tavanın yüzde 2,5'i. Bu payı model eğitmeye değil, optimizasyon aramasına harcamayı tercih ettik. Kazancın geldiği yer orası.

**Ölçtük, tutmadı.** Tahmin sapmasını (bias) düzeltmek için **dört ayrı yaklaşım** denedik. Hedefin kendisi sahte çıktı: görünen yüzde 28,3'lük sapma, iki örnekle uydurulan bir çarpanın artefaktıydı. Doğru yöntemle ölçünce teslim ettiğimiz modelin sapması **eksi 0,0573**, yani neredeyse sıfır. Dört adayın dördü de dışsal örneklemde başarısız oldu ve dördünü de reddettik.

### 4.4 Asıl zorluk zaten tahmin tarafında değil

Bu problemde toplam maliyetin belirleyicisi, tahminin son yüzde birlik isabeti değil **planın kalitesidir**. Nitekim kazancın tamamı optimizasyon tarafından geldi: 16,48 milyondan 11,23 milyona. Mühendislik emeğini oraya yönlendirdik.

---

## 5. Kendi Kendimizi Nasıl Denetliyoruz

Bir optimizasyon kodu **kendi hesabına göre daima haklıdır.** Planı üreten ve maliyeti hesaplayan kod aynı varsayımı paylaşıyorsa, ikisi de yanlışken hiçbir test bunu göremez.

Bu yüzden **hakem simülatörü** adını verdiğimiz ikinci bir program yazdık. Hakem, planlayıcıdan tamamen ayrı yazılmıştır ve optimizatörün iç durumunu **hiç görmez**: yalnız diske yazılan Excel dosyasını ve şartnamenin ham veri dosyalarını okur, maliyeti ve **17 kuralı sıfırdan yeniden hesaplar**.

Dolayısıyla optimizatör ile hakem arasındaki bir anlaşmazlık **gerçek bir hatadır** ve teslimden önce yakalanır.

Ölçülen sonuç: teslim edilen planda **17 kuralın 17'si de geçiyor, 0 ihlal var**, ve bizim beyan ettiğimiz maliyet ile hakemin bağımsız hesabı arasındaki fark **0,0000 TL**.

Hakem sıralamayı da belirledi: onu **optimizatörden önce** yazdık. Optimizatör daha yazılmamışken bile iki optimizatör-sınıfı hata yakaladı.

---

## 6. Sözlük

| Terim | İngilizcesi | Anlamı |
|---|---|---|
| Hücre | cell | Tahminin en küçük birimi: gün, hat ve slot üçlüsü |
| Hat | lane | İki transfer merkezi arasındaki yön; 289 aktif hat var |
| Slot | slot | Talep tamamlanma saati; 09:00 veya 17:00 |
| Desi | - | Hacim ölçüsü; tahmin ve kapasite bu birimdedir |
| DOW | day of week | Haftanın günü |
| Medyan | median | Ortanca; sıralanmış değerlerin tam ortasındaki değer |
| Naive | naive forecast | Karşılaştırma çıtası; geçen hafta aynı günün değerini kopyalar |
| wMAPE | weighted MAPE | Ağırlıklı ortalama mutlak yüzde hata; küçük olması iyidir |
| Bias | bias | Sistematik sapma; modelin sürekli yüksek veya düşük tahmin etmesi |
| Backtest | backtest | Geçmiş bir dönemi, o dönemi görmemiş gibi tahmin edip hatayı ölçme |
| Sızıntı | leakage | Modelin görmemesi gereken gelecek bilgisini kazara görmesi |
| Ufuk | horizon | Tahmin edilen gelecek dönem; burada 7 gün |
| Grid | grid | Tüm olası hücrelerin tam listesi; boş olanlar sıfır kabul edilir |
| Milk-run | milk run | Bir aracın tek seferde birden çok merkeze uğrayıp yük bırakması |
| Bacak | leg | Bir aracın iki merkez arasındaki tek gidişi |
| Spot araç | spot vehicle | İhtiyaç anında kiralanan, uğrama yapabilen araç |
| Kiralık araç | rented vehicle | Sabit sözleşmeli, her gün çıkmak zorunda olan, uğrama yapamayan araç |
| Elleçleme | handling | Yükleme veya indirme işlemi; desi başına 0,01 dakika |
| SLA | service level agreement | Teslim süresi taahhüdü; aşılırsa desi-saat başına 0,40 TL ceza |
| Determinizm | determinism | Aynı girdiyle her zaman birebir aynı çıktıyı üretme özelliği |
