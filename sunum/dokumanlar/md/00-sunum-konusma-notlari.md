# Sunum Konuşma Notları

Bu belge `sunum/v2.html` dosyasındaki 17 slayttan **otomatik olarak** üretilmiştir; sunumdaki her slaytın konuşma metni ve kullanım notu birebir aynıdır. Sunum sırasında **N** tuşuyla aynı metni ekranda da görebilirsiniz, **O** tuşu slayt haritasını açar.

---

## Slayt haritası ve süre planı

| # | Slayt | Hedef süre | Kümülatif |
|---|---|---:|---:|
| 1 | Kapak | 37 sn | 0:37 |
| 2 | Problem | 56 sn | 1:33 |
| 3 | Maliyet modeli | 43 sn | 2:16 |
| 4 | Veri | 53 sn | 3:09 |
| 5 | Tahmin modeli | 53 sn | 4:02 |
| 6 | Backtest | 51 sn | 4:53 |
| 7 | Merdiven | 57 sn | 5:50 |
| 8 | Stage 0 | 56 sn | 6:46 |
| 9 | Stage 1 | 46 sn | 7:32 |
| 10 | Stage 2 | 61 sn | 8:33 |
| 11 | Stage 3 | 61 sn | 9:34 |
| 12 | Filo | 47 sn | 10:21 |
| 13 | Hakem | 52 sn | 11:13 |
| 14 | Final uyumu | 69 sn | 12:22 |
| 15 | Genelleştirilebilirlik | 61 sn | 13:23 |
| 16 | Çıkmaz sokaklar | 60 sn | 14:23 |
| 17 | Kapanış | 52 sn | 15:15 |

**Toplam konuşma süresi:** yaklaşık **15 dakika 15 saniye** (dakikada 135 kelime temposuyla). Slayt geçişleri ve nefes payıyla birlikte **18 dakika** planlayın. 15 dakikalık bir slot için aşağıdaki “süre aşarsak” önceliğini kullanın.

---

## Süre aşarsak — atlama önceliği

Sırayla feda edin; her adım yaklaşık kaç saniye kazandırdığı yanında yazıyor.

1. **Slayt 16 — Ölçülmüş çıkmaz sokaklar.** Ekranda gösterin, okumayın. “Altı fikri ölçtük ve reddettik, detayı raporda var” deyip geçin. (~60 sn)
2. **Slayt 9 — Stage 1.** En basit aşama; “aynı hatta ikinci aracı sildik, 1,8 milyon” tek cümlesiyle özetlenebilir. (~45 sn)
3. **Slayt 15 — Genelleştirilebilirlik.** Tabloyu gösterip “üç farklı hafta ve hacimde sıfır ihlal” demek yeter. (~50 sn)
4. **Slayt 3 — Maliyet modeli.** Sadece alttaki formül satırını okuyun. (~40 sn)

**Asla atlanmayacak slaytlar:** 7 (maliyet merdiveni), 10 (milk-run), 13 (hakem simülatörü), 14 (final backtest uyumu). Bu dördü çözümün savunmasının tamamıdır.

---

## Ezberlenecek sayılar

| Sayı | Ne | Nerede söylenecek |
|---|---|---|
| **11.232.476,73 ₺** | Yayınlanan planın toplam maliyeti | Slayt 1, 11, 17 |
| **−%31,84** | Temel plana göre iyileşme | Slayt 1, 7, 17 |
| **0** | Hakem ihlali — her aşamada | Slayt 1, 7, 13, 17 |
| **1.269 → 665** | Fiziksel araç sayısı | Slayt 1, 12 |
| **%48,02 → %79,03** | Ortalama spot araç doluluğu | Slayt 1, 12 |
| **×0,0198** | Ayın son günü takvim çarpanı | Slayt 5 |
| **0,5328 → 0,4464** | Ay sonu haftası WMAPE (DOW medyanı → bizim model) | Slayt 6 |
| **227 zincir / 96.369 kombinasyon** | Stage 2 arama ve kabul | Slayt 10 |
| **~150 sn / 100 dk** | Çalışma süremiz ve tavan | Slayt 14 |
| **592/592** | Regresyon testi | Slayt 13, 17 |

---

## Slayt slayt konuşma metni

### Slayt 1 — Kapak  (~37 sn)

**Kullanım notu:** **Kullan:** Açılış. Dört KPI kartını tek tek gösterin, ekranda 20 saniyeden fazla kalmayın. **Ezberlenecek:** 11,23 M₺ · −%31,84 · 0 ihlal · 665 araç.

**Konuşma metni:**

Merhaba, ben ... Takım Büke adına anlatacağım.

Bize verilen problem şu: bir haftalık talebi, onlarca operasyonel kısıta uyarak en düşük toplam maliyetle taşıyan bir sevkiyat planı üretmek. Sadece hangi aracın hangi hatta çalışacağını değil, hangi dakikada çıkacağını da planlıyoruz.

Sonucu baştan söyleyeyim: temel plandan yüzde 31,84 daha ucuz bir plan ürettik — 11 milyon 232 bin lira. Ve bunu tek bir kural ihlali olmadan yaptık. Araç sayısını neredeyse yarıya indirdik, araç doluluğunu yüzde 48'den yüzde 79'a çıkardık.

Şimdi bu dört sayının nasıl çıktığını anlatacağım.

---

### Slayt 2 — Problem  (~56 sn)

**Kullanım notu:** **Kullan:** Kısıt/serbestlik ikilisini yan yana gösterin — sağdaki liste ilerideki Stage 2 ve Stage 3'ün kural dayanağı. **Vurgula:** "durak sayısına kural sınırı yok" ve "gizli SLA tavanı yok".

**Konuşma metni:**

Ağ 18 transfer merkezi ve 306 yönlü hattan oluşuyor. Geçmiş veride bunların 289'unda gerçekten talep görülmüş.

Sol tarafta bizi sıkıştıran kısıtlar var. En sert olanı iki tanesi: elleçleme kapasitesi — her merkezin günlük bir işlem limiti var ve gece yarısını aşan bir elleçleme oransal olarak iki güne bölünüyor. İkincisi tır kapasitesi — yedi merkezde sıfır, yani oralara tır hiç giremiyor, ve zorunlu kiralık tırlar bu kotayı zaten tüketiyor.

Sağ taraf ise fırsat tarafı. Jüri soru-cevabında net olarak şunu söyledi: spot araçlarla sınırsız sefer ve uğrama yapabilirsiniz, durak sayısında bir üst sınır yok. Çözümümüzün en büyük kazancı tam olarak buradan geliyor.

Ve kritik bir nokta: gizli bir SLA tavanı yok. Yani ceza ödemek yasak değil, sadece pahalı. Bu bir maliyet takası ve biz bunu bilinçli kullanıyoruz.

---

### Slayt 3 — Maliyet modeli  (~43 sn)

**Kullanım notu:** **Kullan:** Akış şemasını soldan sağa parmakla takip edin. **Vurgula:** "kullanım süresi = tek sürekli pencere". **Ezberlenecek:** 55,2 → 56 · 3.000/7.000 · 2.400 ₺.

**Konuşma metni:**

Maliyet iki parçadan oluşuyor: araç maliyeti ve SLA cezası.

Araç maliyetindeki kritik tanım "kullanım süresi". Jüri bunu üç ayrı soruda netleştirdi: kullanım süresi ilk yükleme başlangıcından son indirme bitişine kadar tek sürekli pencere. Bekleme de elleçleme de dâhil. Yani bir aracı yolda tutmak kadar, onu merkezde bekletmek de para.

SLA saati talebin tamamlanma anında — dokuzda veya on yedide — başlıyor, nihai varış merkezindeki elleçleme bittiğinde duruyor. Aradaki her şey sayılıyor.

Alttaki üç kutu jürinin verdiği birebir sayısal örnekler. Bunların üçünü de birer regresyon testi olarak koda çiviledik; şartnamedeki beş çalışılmış örneğin hepsi testlerimizde aynen var.

---

### Slayt 4 — Veri  (~53 sn)

**Kullanım notu:** **Kullan:** Ay sonu noktalarını turuncu daire olarak gösterin, beşini tek tek sayın. **Vurgula:** "beş ayda beş kez, istisnasız". **Ezberlenecek:** 66.024 satır · 179 gün · 23 dışlanan tarih.

**Konuşma metni:**

Elimizdeki geçmiş veri 66 bin satır, 1 Ocak – 28 Haziran arası 179 gün.

Grafikte hemen göze çarpan şey şu: ayın son günü, her ay, normal bir günün yaklaşık yüzde ikisine iniyor. Beş ayda beş kez, istisnasız. En düşük gözlem 2.010 desi.

Bu bizim için kritik, çünkü 30 Haziran tam olarak tahmin ufkumuzun içinde. 30 Haziran'ı normal bir salı sayan bir model, tek başına o günde bir milyon 100 bin desi hata üretir — bu tek gözlem WMAPE puanını domine eder.

Sağda veri temizleme var. Eğitim verisinden 23 tarihi dışlıyoruz: 15 resmî tatil ve Ocak–Mayıs'ın son iki günü. Dikkat: dışlama sadece eğitime uygulanıyor, hedef günlere değil. Haziran bilerek dışlama listesinde yok, çünkü 29 ve 30 Haziran zaten tahmin edeceğimiz günler.

---

### Slayt 5 — Tahmin modeli  (~53 sn)

**Kullanım notu:** **Kullan:** Önce formül satırı, sonra soldaki çarpanlar, sonra sağdaki karşılaştırma. **Vurgula:** "çarpanlar ölçüldü, seçilmedi". **Ezberlenecek:** ×0,0198 · 24.040 desi vs 1.110.177.

**Konuşma metni:**

Model iki katmanlı ve kasten sade.

Taban katman: her çıkış-varış-saat-haftagünü kombinasyonu için, hedef tarihten kesin önceki son dört gözlemin medyanı. Medyan, çünkü ortalama tek bir sıçramadan bozuluyor.

İkinci katman takvim çarpanı. Solda gördüğünüz üç sayı uydurma değil, geçmiş ay sonlarından ölçüldü: ay sonundan bir önceki gün 0,68; ayın son günü 0,0198; ayın ilk günü 1,21. Her çarpan beş ay sonundan alınan beş oranın medyanı — o günün gerçekleşeni bölü aynı hücrelerin DOW taban toplamı. Tabana bölmek ay sonu etkisini haftagünü etkisinden ayırıyor.

Sağdaki grafik katmanın nerede devreye girdiğini gösteriyor. 30 Haziran'da tahminimiz 24 bin desi, sıradan bir salı ortalaması 1 milyon 110 bin. Kalan dört gün ise düz ortalamaya çok yakın — yani model sadece gerekli yerde müdahale ediyor.

---

### Slayt 6 — Backtest  (~51 sn)

**Kullanım notu:** **Kullan:** Normal hafta ile ay sonu haftasını yan yana okuyun. **Vurgula:** "aynı sayı olması bir kusur değil, kanıt". **Ezberlenecek:** 0,5328 → 0,4464. **Dürüstlük notu:** sorulursa ay sonu haftasındaki bias +%28,3 açık kalemimiz.

**Konuşma metni:**

Modelin işe yaradığını iddia etmek yetmez, ölçmek gerekir.

Normal bir haftada — 15-21 Haziran — bizim model ile DOW medyanı birebir aynı: 0,2174. Bu tesadüf değil, o pencerede takvim etkisi olan bir gün yok, yani katman hiç devreye girmiyor. Zarar vermiyor.

Ay sonu haftasında ise — 30 Mart, 5 Nisan — DOW medyanı 0,5328'den bizim model 0,4464'e iniyor. Naive yaklaşım 0,6972. Yani katman sadece gerektiğinde, ama ciddi biçimde kazandırıyor.

Bu bir frozen backtest: eğitim penceresi hedeften önce kesiliyor ve ufuk içinde yeniden eğitim yok. Gerçek yarışma koşulunun aynısı.

Sağda üç sızıntı koruması var. Üçüncüsü özellikle önemli: fonksiyon, ufuk içi veri görürse çalışmayı reddediyor. Yani gerçekleşen değerin modele sızması kazayla bile mümkün değil, yapısal olarak engellenmiş.

---

### Slayt 7 — Merdiven  (~57 sn)

**Kullanım notu:** **Kullan:** Ana grafik. Barları soldan sağa gösterin, altındaki yüzde düşüşleri okuyun. **Vurgula:** SLA'nın bilerek arttığı — bu soruyu jüri kesin soracak, önce siz söyleyin. **Ezberlenecek:** 16,48 → 14,68 → 11,31 → 11,23 M₺.

**Konuşma metni:**

Bu sunumun kalbi burası.

Planı tek hamlede kurmuyoruz. Dört aşama var ve her aşama bir öncekinin çıktısını girdi olarak alıyor, kendi iyileştirmesini deniyor.

Kabul kuralı tek ve değişmez: hem taban plan hem aday plan hakem simülatöründen sıfır ihlalle geçecek, ve tasarruf pozitif olacak. Bu iki koşuldan biri sağlanmazsa aday çöpe gidiyor, resmî çıktı hiç değişmiyor.

Sonuç: 16 milyon 481 binden 11 milyon 232 bine. Yüzde 31,84 düşüş.

Turuncu bar araç maliyeti, sarı bar SLA cezası. Dikkatinizi çekmek istediğim şey şu: SLA cezası bilerek artıyor. Araç maliyetinden 6 milyon 844 bin lira kazanıp 1 milyon 595 bin lira ceza ödüyoruz. Net kazanç 5 milyon 248 bin. Gizli bir SLA tavanı olmadığı için doğru hedef saf toplam maliyet — bir aracı yola çıkarmak, küçük bir gecikme cezasından pahalıysa cezayı satın alıyoruz.

---

### Slayt 8 — Stage 0  (~56 sn)

**Kullanım notu:** **Kullan:** Dört adımı sırayla okuyun, "sıra önemli" deyin. **Vurgula:** sağ alttaki "neden greedy" kutusu — MILP sorusunun ön cevabı. **Ezberlenecek:** 1.269 araç · 16,48 M₺.

**Konuşma metni:**

Stage 0 kısıtları sağlayan ilk geçerli planı kuruyor.

Sıra önemli. Önce zorunlu kiralık filo, çünkü onlar zaten çıkacak — günde 42 bin lira batık maliyet. O trunk'ları boş göndermek saf israf, o yüzden önce onları dolduruyoruz.

Sonra tır ziyaret bütçesi. Yedi merkezde tır kapasitesi sıfır, bazılarında kiralık tırlar kotayı zaten tüketiyor. Kalan kotayı hesaplayıp bütçe olarak koyuyoruz.

Sonra her hat-gün için araç tipi kombinasyonlarını numaralandırıp kesin maliyet modeliyle en ucuzunu seçiyoruz.

Sonuç: 1.269 araç, 16 milyon 481 bin lira, sıfır ihlal. Bu bizim tabanımız.

Bize sıklıkla "neden MILP solver kullanmadınız" diye soruluyor. Cevabı şu: hat-gün başına karar uzayı zaten küçük ve maliyet modeli kesin — numaralandırma bu ölçekte optimali garanti ediyor. Gerçek zorluk araç kombinasyonunda değil, hangi yüklerin hangi araçta birleşeceğinde. Onu sonraki üç aşama çözüyor.

---

### Slayt 9 — Stage 1  (~46 sn)

**Kullanım notu:** **Kullan:** Kısa tutun, 45 saniye. Bu aşama basit — asıl hikâye Stage 2. **Ezberlenecek:** 177 araç silindi · −1,80 M₺.

**Konuşma metni:**

Stage 1 en basit fikir: aynı gün, aynı hatta çalışan iki araçtan birinin yükü diğerine sığıyorsa, o aracı tamamen sil.

Bin üç donör adayına baktık, 177'si kabul edildi. 177 spot araç plandan tamamen kayboldu.

Kazanç 1 milyon 800 bin lira, yüzde 10,9. Araç sayısı 1.269'dan 1.092'ye indi, doluluk yüzde 48'den 57'ye çıktı.

Bu aşamanın önemli özelliği şu: yeni bacak yaratmıyor. Sadece var olan bir aracın yükünü başka bir araca taşıyıp aracı siliyor. Kimlikler korunuyor, desi korunuyor. O yüzden hem hızlı hem güvenli.

Ama bir duvara toslıyor: aynı hatta birleşecek eş bulamadığınızda yapabileceğiniz bir şey kalmıyor. Sonraki aşama bu duvarı farklı bir yönden aşıyor.

---

### Slayt 10 — Stage 2  (~61 sn)

**Kullanım notu:** **Kullan:** Hunide 96.369 → 227 kontrastını vurgulayın. Donut'ta 4 duraklı 72 zinciri gösterin. **Vurgula:** "segment sabit, araç düşüyor" ve jüri alıntısı. **Ezberlenecek:** 227 zincir · −3,37 M₺ · 693 araç.

**Konuşma metni:**

Stage 2 en büyük kazancı getiren aşama.

Fikir şu: aynı merkezden aynı anda kalkan 2 ile 4 araç varsa, bunları tek bir fiziksel araca zincirleyip sırayla uğratabilir miyiz?

93 aday grup, 5.426 ikili ve 96 bin 369 çoklu kombinasyon denedik. 227 zincir kabul edildi.

Kritik nokta şu: segment sayısı 1.092'de sabit kalıyor. Zincir yeni bacak yaratmıyor — k ayrı aracın işini tek araca bindiriyor. Araç sayısı 1.092'den 693'e düşüyor. Kimlik kontrolü basit: 1.092 eksi 626 artı 227 eşittir 693.

Kazanç 3 milyon 367 bin lira, yüzde 22,9.

Bunun kural dayanağı jüri soru-cevabında açık: "Spot araçlar için birden fazla merkeze uğrama mümkündür" ve "kısıtlamalar dikkate alınarak sınırsız sefer yapabilirsiniz". Yani durak sayısına kural sınırı yok. Dört durak sınırı bizim mühendislik tercihimiz; gerçek sınır kapasite — zincirler tırsız spot tipleri kullandığı için bir rota en fazla 12 bin desi taşıyabiliyor.

---

### Slayt 11 — Stage 3  (~61 sn)

**Kullanım notu:** **Kullan:** Jüri alıntısını (x+y) sesli okuyun — bu aşamanın meşruiyeti oradan geliyor. Kod kutusunu gösterin. **Ezberlenecek:** 135.660 çift → 28 kabul · −80.862 ₺.

**Konuşma metni:**

Stage 2'ye kadar zincirlerimiz sadece indiriyordu: araç çıkışta her şeyi yükler, her durakta bir kısmını bırakır, ara durakta yeni yük almaz.

Jüri bunun tersini de açıkça serbest bırakıyor. Altıncı soruda şöyle diyor: "bir araçtan x kadar yük indirilip y kadar yük yüklenirse kapasiteden x artı y kadar yük düşülür." Bu cümle hem işlemi tarif ediyor hem elleçleme aritmetiğini veriyor.

Biz bunu Tier A biçiminde uyguladık: alınan yükün varışı, rotanın zaten uğradığı bir durak olmak zorunda. Böylece rota hiç uzamıyor, topoloji değişmiyor.

227 hedef rota, 340 donör, 135 bin 660 çift inceledik. 56'sı kârlı çıktı, çakışma çözümünden sonra 28'i kabul edildi. 28 araç daha plandan silindi.

Soldaki kod kutusu önemli. Bir yük alma durağında iki ayrı zaman damgası var: indirme bitişi ve kalkış anı. Bunları karıştırmak sessiz bir hata olurdu. Prototipimizde tam olarak bu hatayı yaptık; hakem simülatörü yakaladı.

---

### Slayt 12 — Filo  (~47 sn)

**Kullanım notu:** **Kullan:** Üç grafiği tek cümlede bağlayın: "daha az araç, daha dolu araç, daha doğru araç". **Ezberlenecek:** 480 → 30 · %48 → %79 · Tır 99 sabit.

**Konuşma metni:**

Üç grafik, tek hikâye.

Solda araç sayısı: 1.269'dan 665'e, yüzde 47,6 düşüş.

Ortada doluluk dağılımı. Eğri ne kadar sağdaysa o kadar iyi. Stage 0'da spot araçların yüzde 42'si yarıdan az doluydu — 1.143 aracın 480'i yüzde 30'un altında. Stage 3'te bu sayı 30'a indi. Ortalama doluluk yüzde 48'den 79'a çıktı.

Sağda araç türü karması. Karma küçükten büyüğe kayıyor: yarı boş kamyonetler birleşip daha az sayıda ama daha dolu kamyona biniyor. Kamyonet 950'den 233'e, kamyon 196'dan 304'e.

Tır sayısı 99'da sabit — bilinçli. Tır kapasitesi kıt bir kaynak, yedi merkezde sıfır. Onu zorlamıyoruz. Zaten ölçtük: tırı zincire katmak 18 bin 100 lira daha kötü sonuç veriyor.

---

### Slayt 13 — Hakem  (~52 sn)

**Kullanım notu:** **Kullan:** "İç durumunu hiç görmez" cümlesini vurgulayın — bağımsızlık iddiasının özü bu. **Ezberlenecek:** 17 kural · 592 test · kuruşun milyonda biri.

**Konuşma metni:**

Bu projede tek bir sayıya bile "hesapladım, doğrudur" demiyoruz.

Hakem simülatörü planlayıcıdan tamamen ayrı yazılmış ikinci bir uygulama. Optimizatörün iç durumunu hiç görmüyor — sadece çıktı Excel'ini ve ham veriyi okuyup maliyeti ve 17 kuralı sıfırdan yeniden hesaplıyor. Dolayısıyla optimizatör ile hakem arasındaki bir anlaşmazlık gerçek bir hatadır, ve teslimden önce yakalanır.

Optimizatör daha yazılmamışken bile iki optimizatör-sınıfı hatayı yakaladı.

İkinci kapı uzlaşma kapısı: aramanın kendi hesabıyla bulduğu tasarruf ile hakemin ölçtüğü fark, kuruşun milyonda birine kadar aynı sayı olmak zorunda. Stage 3 prototipindeki üç hatanın üçünü de bu kapı yakaladı — başka hiçbir kontrol fark etmiyordu.

Bunun üstüne 592 regresyon testi, determinizm kontrolü ve artifact doğrulaması var: yayından önce Excel geri okunuyor, şema doğrulanıyor, hakem yeniden çalıştırılıyor.

---

### Slayt 14 — Final uyumu  (~69 sn)

**Kullanım notu:** **Kullan:** Tabloyu tek tek okumayın, sadece 2 / 5 / 8 / 10 satırlarını gösterin. **Vurgula:** "süreci bilerek öldürdük". **Ezberlenecek:** ~150 sn vs 100 dk · 0 farklı hücre.

**Konuşma metni:**

Final aşamasında kodumuz bize önceden bildirilmeyen bir haftalık veri setiyle çalıştırılacak. Teknik gereksinimler dokümanı 11 bölüm ve her bölüm test edilebilir bir gereksinim tanımlıyor.

Solda hepsinin karşılığı var. Birkaçını vurgulayayım: Bölüm 2 tahmin modülünün çağrılmamasını istiyor — main.py'nin import grafiğini taradık, forecast modülüne hiçbir yoldan ulaşılamıyor. Bölüm 5 kolon şemasına birebir uyum istiyor — dosyayı yazdıktan sonra diskten geri okuyup şemayı yeniden doğruluyor, ancak ondan sonra atomik olarak yerine koyuyoruz.

Sağdaki iki güvenlik Bölüm 10 için. Bölüm 10 üç şeyi hatalı çalıştırma sayıyor: sıfırdan farklı çıkış kodu, 100 dakikayı aşmak, çıktı üretmemek.

Birincisi kademeli yayın: geçerli ilk plan elde edilir edilmez dosya yazılıyor. Süreci Stage 2'nin ortasında bilerek öldürdük — diskte 3.710 satırlık, şemaya birebir uyan geçerli bir plan vardı.

İkincisi sert süre sınırı: her arama aşaması ayrı bir daemon thread'de kalan bütçeyle çalışıyor. Sınır dolarsa aşama terk ediliyor ve süreç normal biçimde bitiyor.

Referans veri setinde uçtan uca süremiz 150 saniye — tavanın kırkta biri.

---

### Slayt 15 — Genelleştirilebilirlik  (~61 sn)

**Kullanım notu:** **Kullan:** Tabloyu gösterin, %250 kutusunu dürüstlük anı olarak sunun — jüri sorarsa hazırlıksız yakalanmayın. **Ezberlenecek:** 395.825 vs 394.786 desi.

**Konuşma metni:**

Bölüm 7 kodun herhangi bir takvim haftası için çalışmasını istiyor. Bunu iddia etmek yetmez, kendimiz test ettik.

Üç senaryo ölçtük. Referansın yanı sıra: farklı bir yıl, 4 günlük kısaltılmış ufuk, yüzde 35 hacim, REQ_ önekli kimlikler ve HH:MM saat biçimi. Ve ayrı olarak farklı bir hafta, yüzde 125 hacim, HH:MM:SS biçimi. Üçünde de çıkış kodu sıfır, sıfır ihlal, ve beyan ettiğimiz maliyet ile hakemin hesabı arasındaki fark sıfır virgül sıfır lira.

Alttaki kutu dürüst bir not. Yüzde 250 hacimli sentetik bir veri setinde 69 elleçleme ihlali gördük. Ama bu bir kod kusuru değil: İstanbul'un 1 Temmuz'daki elleçleme talebi 395.825 desi, günlük kapasitesi 394.786. Ağ zaten neredeyse dolu. Hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme kısıtı hiçbir plan tarafından sağlanamaz.

Önemli olan şu: kod çökmedi, geçerli plan üretti ve yayınladı, ve Stage 1 adayını doğru biçimde reddetti.

---

### Slayt 16 — Çıkmaz sokaklar  (~60 sn)

**Kullanım notu:** **Kullan:** En fazla iki satırı sesli anlatın (0 ₺ ve +18.100 ₺), gerisi ekranda kalsın. **Vurgula:** "arama yaptığımızın kanıtı". **Ezberlenecek:** 0 ₺ · +18.100 ₺ · 318,25 vs 487,50 ₺/sa.

**Konuşma metni:**

Bu slaytı özellikle koydum, çünkü bir optimizasyon çözümünün kalitesi sadece kabul ettiği fikirlerle değil, reddettikleriyle de ölçülür.

Altı fikri denedik, ölçtük ve reddettik.

En ilginç ikisi şunlar. Birincisi: düşük dolulukta aynı-hat birleştirme. Stage 2'den sonra kalan 46 yarı boş aracı birleştirmeyi denedik — kazanç tam olarak sıfır lira. Çünkü 46'sının 46'sı da o gün o hattın tek aracıydı; birleşecek eş yok. Stage 3 bu duvarı farklı bir yönden aştı: aynı hatta eş aramak yerine yükü oradan geçen bir zincire bindirdi.

İkincisi: tırı zincire katmak. Kural engeli yok, kapasite tavanını 22 bin 400'e çıkarırdı. Ama ölçtük: 18 bin 100 lira daha kötü. Çünkü kamyon aynı 12 bin kapasitede tırı her koşulda eziyor — saatlik 318 lira karşı 487 — ve kârlı tır adaylarının yüzde 93,6'sı kapasitesi sıfır olan yedi merkez yüzünden ölüyor.

Hiçbiri sezgiyle elenmedi. Hepsi ölçüldü.

---

### Slayt 17 — Kapanış  (~52 sn)

**Kullanım notu:** **Kullan:** KPI şeridini tekrar gösterin — açılıştaki dört sayıyla simetri kurun. **Bitiriş cümlesi:** "iki cümle, 3,45 milyon lira". Soru-cevaba geçin.

**Konuşma metni:**

Toparlayayım.

11 milyon 232 bin liralık bir plan ürettik — temel plandan yüzde 31,84 daha ucuz. Sıfır kural ihlali, 592 test, 150 saniye çalışma süresi.

Bu çözümü ayıran üç şey var.

Birincisi bağımsız hakem: hiçbir sayıya güvenmiyoruz, her şey ikinci bir uygulamayla sıfırdan yeniden hesaplanıyor.

İkincisi kural okuma disiplini. Kazancımızın büyük kısmı jürinin soru-cevapta açıkça serbest bıraktığı iki cümleden geldi: "spot araçlarla sınırsız sefer ve uğrama yapabilirsiniz" ve "bir araçtan x indirilip y yüklenirse kapasiteden x artı y düşülür". Bu iki cümle 3 milyon 447 bin liralık kazancın kapısıydı.

Üçüncüsü ölçülmüş reddetme: altı fikri sezgiyle değil, sayıyla eledik.

Açık kalemlerimiz de var ve saklamıyoruz: tahmin bias'ı, Tier B yük alma, beş duraklı zincir.

Teşekkürler, sorularınızı bekliyoruz.

---

## Sunum öncesi 10 dakikalık hazırlık listesi

1. `sunum/v2.html` dosyasını tarayıcıda açın, **F11** ile tam ekran yapın.
2. **O** tuşuyla slayt haritasını açıp kapatın — akışın aklınızda olduğundan emin olun.
3. Slayt 7 (maliyet merdiveni) ve slayt 10 (milk-run) üzerinde birer kez prova yapın; sunumun ağırlık merkezi bu ikisi.
4. Yukarıdaki on sayıyı sesli tekrarlayın.
5. Demo yapacaksanız terminali hazırlayın: `cd final-teslim && python main.py`. Referans veri setinde ~150 saniye sürer ve her aşamada maliyeti ekrana basar — sunum sırasında başlatıp konuşmaya devam edin, kapanışta çıktıyı gösterin.
6. Yedek: internet veya projeksiyon sorunu olursa sunum tek bir HTML dosyasıdır, dış bağımlılığı yoktur; tarayıcının **yazdır** menüsünden PDF de alınabilir.

## Soru-cevap taktikleri

- **Bilmediğiniz bir soru gelirse:** “Bunu ölçmedik” demek, tahmin yürütmekten iyidir. Ardından ölçtüğünüz en yakın şeyi söyleyin.
- **Sayı sorulursa** yuvarlayın ama kaynağını söyleyin: “yaklaşık 11,2 milyon; kesin değer hakem simülatörünün yeniden hesabından geliyor”.
- **“Neden X yapmadınız?”** sorularının çoğunun cevabı slayt 16'dadır — “denedik, ölçtük, şu kadar kötüydü”.
- **SLA cezası** sorusunu jüri sormadan siz açın (slayt 7). Savunmada kalmayın.
- **Açık kalemlerinizi saklamayın:** tahmin bias'ı, Tier B, beş duraklı zincir. Bilinen sınırı söylemek, bilinmeyen sınırdan iyidir.
