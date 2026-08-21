# Sunum Akışı ve Konuşma Metni

Takım Büke — TEKNOFEST 2026 · Hepsiburada Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · Final (Backtest) aşaması

Bu belge sunumu **ezberlemeden**, akışı takip ederek anlatabilmek için hazırlanmıştır. Her slayt için dört blok vardır: slaytta ne olacağı, birinci ağızdan söylenecek metin, o slaytta mutlaka telaffuz edilecek sayılar ve jürinin o noktada sorabileceği tipik soru ile tek cümlelik cevabı.

Konuşma metinlerini kelimesi kelimesine okumak zorunda değilsiniz; **vurgu sayıları** ve **olası ara soru** blokları asıl taşıyıcıdır. Bir cümleyi unutursanız o slaydın vurgu sayılarını söyleyip devam edin.

> **Süre varsayımı.** Aşağıdaki süreler dakikada yaklaşık 150 kelimelik bir konuşma temposuna göre hesaplanmıştır. Toplam konuşma 21 slaytta **15 dakika 15 saniye** tutar. Slayt geçişleri ve nefes payıyla birlikte **17-18 dakikalık** bir slot planlayın; 15 dakikalık bir slotta "Süre aşarsak" bölümündeki atlama önceliğini uygulayın.

---

## 1. Slayt haritası ve süre planı

| # | Slayt | Süre | Kümülatif |
|---|---|---|---|
| 1 | Açılış — dört sayı | 40 sn | 0:40 |
| 2 | Problem, kısıtlar ve serbestlikler | 50 sn | 1:30 |
| 3 | Veri: ne aldık, ne temizledik | 35 sn | 2:05 |
| 4 | Keşif: ay sonu çöküşü | 45 sn | 2:50 |
| 5 | Tahmin modeli: DOW medyan tabanı | 45 sn | 3:35 |
| 6 | Takvim katmanı ve sızıntı koruması | 45 sn | 4:20 |
| 7 | Backtest: model gerçekten iyi mi | 45 sn | 5:05 |
| 8 | Maliyet modeli ve yuvarlama kuralları | 45 sn | 5:50 |
| 9 | Kabul kuralı: her aşama aynı kapıdan geçer | 35 sn | 6:25 |
| 10 | Optimizasyon merdiveni — genel bakış | 40 sn | 7:05 |
| 11 | Stage 0 — temel plan | 50 sn | 7:55 |
| 12 | Stage 1 — aynı-hat onarımı | 35 sn | 8:30 |
| 13 | Stage 2 — milk-run zincirleri | 55 sn | 9:25 |
| 14 | Stage 3 — rota ortasında yük alma | 55 sn | 10:20 |
| 15 | Hakem simülatörü | 45 sn | 11:05 |
| 16 | Kalite kapıları ve determinizm | 35 sn | 11:40 |
| 17 | Final backtest uyumu — main.py ve sözleşmeler | 50 sn | 12:30 |
| 18 | Bölüm 10 güvenlikleri ve genelleştirilebilirlik | 45 sn | 13:15 |
| 19 | Sonuçlar: filo, doluluk, araç karması | 45 sn | 14:00 |
| 20 | Ölçülmüş çıkmaz sokaklar | 35 sn | 14:35 |
| 21 | Kapanış ve gelecek iş | 40 sn | 15:15 |

---

## 2. Slayt slayt akış ve konuşma metni

### Slayt 1 — Açılış: dört sayı  (~40 sn)

**Slaytta ne var:**
- Takım adı, yarışma başlığı, aşama: Final backtest
- Dört büyük sayı kartı: **11.232.476,73 TL** toplam maliyet · **−%31,84** iyileşme · **0** hakem ihlali · **1.269 → 665** fiziksel araç
- Alt şerit: 592/592 regresyon testi, uçtan uca yaklaşık 150 saniye

**Konuşma metni:**

Merhaba, Takım Büke adına anlatıyorum. Bize verilen problem şu: bir haftalık talebi, elleçleme kapasitesi, tır kapasitesi ve teslim süresi kısıtlarına uyarak en düşük toplam maliyetle taşıyan bir sevkiyat planı üretmek. Sadece hangi aracın hangi hatta çalışacağını değil, hangi dakikada yükleneceğini de planlıyoruz.

Sonucu baştan söyleyeyim. Kendi temel planımıza göre yüzde 31,84 daha ucuz, 11 milyon 232 bin liralık bir plan ürettik. Bunu tek bir kural ihlali olmadan yaptık. Fiziksel araç sayısı 1.269'dan 665'e indi, ortalama spot araç doluluğu yüzde 48'den yüzde 79'a çıktı.

Şimdi bu dört sayının nasıl çıktığını anlatacağım. Peşinen bir not: hiçbir sayıya "hesapladım, doğrudur" demiyoruz; her aşamayı bağımsız yazılmış bir hakem simülatörü yeniden fiyatlandırıyor.

**Vurgu sayıları:** 11.232.476,73 TL · −%31,84 · 0 ihlal

**Olası ara soru:** *"Yüzde 31,84 neye göre?"* — Kendi ürettiğimiz Stage 0 temel planına göre; dört aşamanın mutlak değerleri `final-teslim/README.md` içindeki aşama tablosunda ve teslim edilen `out/Tasima-plani.xlsx` üzerinde doğrulanabilir.

---

### Slayt 2 — Problem, kısıtlar ve serbestlikler  (~50 sn)

**Slaytta ne var:**
- Ağ şeması: 18 transfer merkezi, 306 yönlü hat, geçmişte talep görülen 289 aktif OD çifti
- Sol sütun "Kısıtlar": elleçleme kapasitesi (gece yarısını aşan işlem oransal bölünür), tır kapasitesi (7 merkezde sıfır), zorunlu kiralık filo (günde 14 araç), SLA 24/48 saat
- Sağ sütun "Serbestlikler": spot araçla sınırsız sefer, uğrama serbest, minimum doluluk kuralı yok, gizli SLA tavanı yok

**Konuşma metni:**

Ağ 18 transfer merkezi ve 306 yönlü hattan oluşuyor; geçmiş veride bunların 289'unda gerçekten talep görülmüş, sadece o 289 hat için tahmin üretiyoruz — jüri bunu açıkça istedi: geçmiş veride bulunmayan bir merkez ikilisi için tahmin üretilmemeli.

Sol taraf bizi sıkıştıran kısıtlar. En sert ikisi: elleçleme kapasitesi, çünkü her merkezin günlük bir işlem limiti var ve gece yarısını aşan bir elleçleme oransal olarak iki güne bölünüyor; ve tır kapasitesi, çünkü yedi merkezde sıfır ve zorunlu kiralık tırlar kalan kotayı zaten tüketiyor.

Sağ taraf ise fırsat tarafı, ve çözümümüzün büyük kazancı oradan geliyor. Jüri soru-cevabında spot araçlar için uğramanın mümkün olduğunu, sefer sayısında üst sınır bulunmadığını, bu aşamada minimum doluluk kuralı olmadığını söyledi. Ve gizli bir SLA tavanı yok: gecikme yasak değil, sadece fiyatlı.

**Vurgu sayıları:** 18 merkez · 306 hat · 289 aktif OD

**Olası ara soru:** *"SLA cezasını bilerek mi ödüyorsunuz?"* — Evet; jüri Q&A'da "bu aşamada böyle bir kural bulunmamaktadır, gönderiler gecikirse SLA cezası ödenmesi gerekmektedir" dediği için doğru hedef saf toplam maliyettir ve gecikme cezası aracın sabit maliyetinden ucuz olduğunda cezayı satın alıyoruz.

---

### Slayt 3 — Veri: ne aldık, ne temizledik  (~35 sn)

**Slaytta ne var:**
- Ham veri künyesi: 66.024 talep satırı, 1 Ocak – 28 Haziran 2026, 179 gün
- İki seviyeli huni grafiği: eğitim geçmişi 103.462 grid hücresi → 90.168 kullanıldı, 13.294'ü (%12,8) elendi; tahmin dosyası 4.046 satır → 2.925'i optimizasyona girdi, 1.121'i (%27,7) sıfır desi
- "Kasıtlı olarak yapmadıklarımız" kutusu: outlier temizleme, log dönüşümü, smoothing, harici makine öğrenmesi kütüphanesi yok

**Konuşma metni:**

Elimizdeki geçmiş 66 bin talep satırı, 179 gün. İlk yaptığımız şey veriyi **tam grid**'e çevirmek oldu: her aktif hat, her gün, iki saat dilimi. Veride görünmeyen bir hücre eksik veri değil, sıfır talep demek. Bunu yapmazsanız sıfırları hiç modellemezsiniz ve tahmin sistematik olarak yukarı sapar.

İkinci adım eğitim filtresi: 23 tarihi eğitimden çıkardık — 15 resmî tatil ve Ocak-Mayıs aylarının son iki günü. Dikkat: bu dışlama **yalnız eğitim verisine** uygulanıyor, hedef günler asla elenmiyor; zaten 29 ve 30 Haziran tahmin ufkumuzun içinde.

Bilerek yapmadıklarımızı da söyleyeyim: outlier temizleme, log dönüşümü, smoothing, Prophet, ARIMA, sklearn — hiçbiri yok. Veri tam ve düzenli; iki güçlü sinyal var, robust medyan ikisini de yakalıyor. Fazlası doğrulanamayan karmaşıklık olurdu.

**Vurgu sayıları:** 66.024 satır · 23 dışlanan tarih · 1.121 sıfır satır korundu

**Olası ara soru:** *"Sıfır satırları neden silmiyorsunuz?"* — Jüri "ayrı satırlarda olmasını bekliyoruz" dedi ve düşük tahminli satırların da sunulması gerektiğini belirtti; sıfır satırlar tahmin dosyasında kalır, sadece optimizasyona girmez — sıfır desi için araç çıkarılmaz.

---

### Slayt 4 — Keşif: ay sonu çöküşü  (~45 sn)

**Slaytta ne var:**
- Ocak-Haziran 2026 günlük desi grafiği; ayın son günleri işaretli
- Beş ay sonunun hepsi taban çizgide; en düşük gözlem 2.010 desi
- Kırmızı uyarı kutusu: "30 Haziran'ı normal bir salı sayan model o gün tek başına yaklaşık 1,1 milyon desi hata üretir"

**Konuşma metni:**

Bu grafiği gördüğümüz an modelin şekli belli oldu. Ayın son günü **her ay** normal bir günün yaklaşık yüzde ikisine iniyor — beş ay boyunca istisnasız. En düşük gözlem 2.010 desi.

Bunun neden hayati olduğunu söyleyeyim: tahmin ufkumuzun ikinci günü 30 Haziran, yani bir ay sonu. Haftagünü ortalamasına bakan bir model o gün için yaklaşık 1 milyon 110 bin desi tahmin ederdi. Bizim tahminimiz 24.040 desi. Tek bir günde bir milyondan fazla desilik fark var ve bu fark WMAPE'yi tek başına domine edecek büyüklükte.

Aynı olgunun iki komşusu da var: ay sonundan bir önceki gün bastırılmış, ayın ilk günü ise toparlanmış geliyor. Yani bu bir gürültü değil, tekrarlayan bir takvim olayı — ve tekrarlayan bir olay ölçülebilir demektir.

**Vurgu sayıları:** ayın son günü ≈ normalin %2'si · en düşük gözlem 2.010 desi · 30 Haziran tahmini 24.040 desi

**Olası ara soru:** *"Bu ay sonu etkisi bir veri hatası olamaz mı?"* — Beş ayın beşinde de aynı yönde ve aynı büyüklükte tekrarlıyor; tek bir aya özgü olsaydı aykırı değer derdik, beş aya yayıldığı için yapısal bir takvim olayı olarak modelledik.

---

### Slayt 5 — Tahmin modeli: DOW medyan tabanı  (~45 sn)

**Slaytta ne var:**
- Tek satırlık model formülü: `tahmin = DOW_medyan_tabanı(k=4) × takvim_çarpanı(gün)`
- Taban modelin tanımı: (çıkış, varış, saat dilimi, haftagünü) bazında, hedef tarihten kesin önceki son 4 gözlemin medyanı
- Çıktı künyesi: 4.046 satır, 4.977.975 desi, `D00001…` kimlikleri, tam grid

**Konuşma metni:**

Model tek satır: haftagünü medyan tabanı, çarpı takvim çarpanı.

Taban şöyle çalışıyor: her hat, her saat dilimi ve her haftagünü için, hedef tarihten **kesin önce** gelen son dört gözlemin **medyanını** alıyoruz. Ortalama değil medyan, çünkü ortalama tek bir kampanya gününden kalıcı olarak bozulur. Dört gözlem, çünkü mevsimsel kayma ile örneklem gürültüsü arasındaki denge orada.

Çıktı 4.046 satır ve toplam 4 milyon 978 bin desi. Kimlikler `D00001`'den başlayarak, tarih-çıkış-varış-saat sırasına göre kararlı biçimde atanıyor; bu sıralama anahtarı ileride final entegrasyonunda tekrar karşımıza çıkacak, çünkü dışarıdan gelen bir talep tablosunu tam olarak aynı anahtarla kanonik hâle getiriyoruz.

Model bu kadar basit olduğu için de savunulabilir: bir jüri sorusuna "şu satırda şu medyan alındı" diye cevap verebiliyoruz.

**Vurgu sayıları:** k = 4 · 4.046 satır · 4.977.975 desi

**Olası ara soru:** *"Neden gradyan artırma veya derin öğrenme değil?"* — Denemedik demiyoruz, gerekmedi diyoruz: veri tek bir güçlü mevsimsellikle bir takvim olayından oluşuyor ve backtest'te medyan tabanı naive modeli zaten geçiyor; doğrulanamayan model karmaşıklığı bu veri setinde risk, kazanç değil.

---

### Slayt 6 — Takvim katmanı ve sızıntı koruması  (~45 sn)

**Slaytta ne var:**
- Dört çarpanlı tablo: ay sonundan bir önceki gün ×0,6752 · ayın son günü ×0,0198 · ayın ilk günü ×1,2072 · normal gün ×1,0000
- Çarpanların nasıl ölçüldüğü: her rol için geçmiş beş olay gününün oranlarının **medyanı**
- Üç sızıntı koruması kutusu

**Konuşma metni:**

Takvim katmanı üç global çarpandan ibaret ve üçü de veriden ölçüldü, elle konmadı. Ayın son günü çarpanı 0,0198; ayın ilk günü 1,2072; ay sonundan bir önceki gün 0,6752. Her çarpan, geçmişteki beş olay gününde gerçekleşen toplamın, aynı hücreler için hesaplanan medyan tabanının toplamına oranının **medyanı**. Medyan seçmemiz önemli: ayın ilk günü oranlarından biri 1 Mayıs, yani resmî tatil, ve 0,09 çıkıyor; medyan onu dışarıda bırakıyor, ortalama alsaydık çarpan bozulurdu.

Sızıntıya karşı üç ayrı korumamız var. Bir: çarpan uydurulurken yalnızca hedeften önceki veri kullanılıyor. İki: taban hesabından olay günlerinin kendisi dışlanıyor. Üç: tahmin fonksiyonu, ufuk içi bir satır içeren veri alırsa doğrudan **hata fırlatıyor** — yani gerçekleşen değerin modele sızması yapısal olarak imkânsız, iyi niyete bırakılmamış.

**Vurgu sayıları:** ×0,0198 · ×1,2072 · ×0,6752

**Olası ara soru:** *"Bir rol için yeterli örnek yoksa ne oluyor?"* — Rol başına en az iki sonlu oran yoksa çarpan güvenli 1,0 değerine düşüyor; yani model o rolde müdahale etmeyip düz medyan tabanı gibi davranıyor.

---

### Slayt 7 — Backtest: model gerçekten iyi mi  (~45 sn)

**Slaytta ne var:**
- İki pencereli WMAPE tablosu

| Pencere | Naive (geçen hafta) | DOW medyanı | Bizim model |
|---|---|---|---|
| Normal hafta · 15-21 Haz | 0,2592 | 0,2174 | 0,2174 |
| Ay sonu haftası · 30 Mar - 5 Nis | 0,6972 | 0,5328 | 0,4464 |

- "Frozen backtest" rozeti: eğitim penceresi hedeften önce kesiliyor, ufuk içinde yeniden eğitim yok
- Açık kalem etiketi: ay sonu haftasında bias **+%28,3**

**Konuşma metni:**

Modeli iddia ederek değil, ölçerek savunuyoruz. Bu **dondurulmuş** bir backtest: eğitim penceresi hedef tarihten önce kesiliyor ve ufuk içinde yeniden eğitim yapılmıyor — gerçek yarışma koşulunun aynısı.

Normal haftada iki değer birebir aynı: 0,2174 ve 0,2174. Bu bir tesadüf değil, tasarım. O pencerede takvim etkisi olan gün yok, çarpan 1,0, katman hiç devreye girmiyor. Yani model gereksiz yere müdahale etmiyor.

Ay sonu haftasında ise fark açılıyor: naive model 0,6972, düz haftagünü medyanı 0,5328, bizim model 0,4464. Katman hatayı yüzde 16 azaltıyor, naive'e göre ise yüzde 36 iyileştiriyor.

Açık kalemi de söyleyeyim, çünkü saklamıyoruz: ay sonu haftasında pozitif bir bias'ımız var, ölçülen değer artı yüzde 28,3. Tahmin tarafında bildiğimiz en yüksek değerli iyileştirme alanı bu ve dört farklı düzeltme adayını ölçüp reddettik — sonuncu slaytta ona döneceğim.

**Vurgu sayıları:** 0,5328 → 0,4464 · normal haftada birebir aynı

**Olası ara soru:** *"Neden sadece iki pencere?"* — İkisi bilerek seçildi: biri katmanın hiç devreye girmediği pencere, diğeri tam olarak devreye girdiği pencere; amaç ortalamayı güzelleştirmek değil, katmanın zarar vermediğini ve yalnız gerektiğinde kazandırdığını göstermek.

---

### Slayt 8 — Maliyet modeli ve yuvarlama kuralları  (~45 sn)

**Slaytta ne var:**
- Formül bloğu: Toplam Maliyet = Araç Maliyeti + SLA Cezası; Araç Maliyeti = Saatlik Kira × Kullanım Süresi + Mesafe × Km Başı Maliyet; SLA Cezası = Geciken Desi × ⌈Gecikme Saati⌉ × 0,40 TL
- Zaman çizgisi: yükleme elleçlemesi → seyir → indirme elleçlemesi, hepsi **tek sürekli pencere**
- Üç jüri kuralı kartı: 0,92 saat = 55,2 dk → 56 dk · 23:30'da 10.000 desi → 3.000 / 7.000 · 6.000 desi 1 saat geç → 2.400 TL

**Konuşma metni:**

Maliyet modeli tartışmaya açık değil, şartnamede yazıyor: araç maliyeti saatlik kira çarpı kullanım süresi, artı mesafe çarpı kilometre başı maliyet. Kritik nokta kullanım süresinin tanımı. Jüri Q&A'da açıkça "kullanım süresi bekleme, elleçleme ve seyir süresinin toplamıdır" dedi ve uğramalı bir rotada ara duraktaki elleçlemenin de dahil olduğunu ayrıca teyit etti. Biz de kullanım süresini ilk yükleme başlangıcından son indirmenin bitişine kadar **tek sürekli pencere** olarak sayıyoruz.

Üç yuvarlama kuralı var ve üçü de tek bir modülde toplanmış durumda: süreler en yakın büyük tam dakikaya yuvarlanıyor — jürinin verdiği örnekte 0,92 saat 55,2 dakika, biz 56 yazıyoruz. Gece yarısını aşan elleçleme süreye orantılı bölünüyor — jürinin örneğinde 23:30'da başlayan 10.000 desilik işlem 3.000 ve 7.000 olarak iki güne düşüyor. Ve SLA gecikmesi bir üst tam saate yuvarlanıyor: bir dakikalık gecikme bile bir saat sayılıyor.

**Vurgu sayıları:** 55,2 dk → 56 dk · 3.000 / 7.000 · 0,40 TL/desi/saat

**Olası ara soru:** *"Bu yuvarlamaları planlayıcı ile hakem farklı mı yapıyor?"* — Hayır, ikisi de aynı zaman modülünden okuyor; ayrıca float artefaktına karşı yukarı yuvarlamadan önce altı haneye sabitleme koruması var: 8,05 saatlik bir bacakta `8,05 × 60` çarpımı 483,00000000000006 verir ve koruma olmasa 484 dakikaya yuvarlanırdı.

---

### Slayt 9 — Kabul kuralı: her aşama aynı kapıdan geçer  (~35 sn)

**Slaytta ne var:**
- Tek şema: aday plan → çizelgele → şema doğrula → hakem simülatörü → kabul kapısı
- Kabul kapısının üç şartı yan yana: temel planda 0 ihlal · adayda 0 ihlal · tasarruf ≥ 1,00 TL
- "Reddedilen aday resmî çıktıyı değiştirmez" rozeti

**Konuşma metni:**

Bir sonraki dört slayt boyunca aşamaları anlatacağım, ama önce hepsinin ortak kuralını söyleyeyim, çünkü aynı kapı dört kez kullanılıyor.

Bir aşama bir aday plan üretir. O aday önce dakika dakika çizelgelenir, sonra çıktı şemasına göre doğrulanır, sonra bağımsız hakem simülatöründen geçirilir. Kabul için üç şart birden gerekir: temel planda sıfır ihlal, adayda sıfır ihlal ve ölçülen tasarrufun en az bir lira olması. Üçünden biri tutmazsa aday tamamen atılır ve bir önceki aşamanın planı korunur.

Bunun pratik sonucu şu: kötü bir aşama planı bozamaz. Fizikî olarak çözümsüz bir veri setinde bunu ölçtük — yüzde 250 hacimli sentetik veride temel plan ihlalli çıktı, Stage 1 adayı doğru biçimde reddedildi, kod çökmedi ve şemaya birebir uyan bir plan yazdı.

**Vurgu sayıları:** 0 ihlal + 0 ihlal + ≥ 1,00 TL

**Olası ara soru:** *"Bir aşama planı bozarsa fark eder misiniz?"* — Kabul kapısı hakem simülatörünün toplamına bakıyor, aşamanın kendi hesabına değil; ayrıca yayınlanan koşuda aramanın iddia ettiği tasarrufla hakemin ölçtüğü fark 0,000001 TL'den fazla ayrışırsa çalıştırma reddediliyor.

---

### Slayt 10 — Optimizasyon merdiveni: genel bakış  (~40 sn)

**Slaytta ne var:**
- Dört basamaklı maliyet merdiveni grafiği (araç maliyeti + SLA cezası yığılmış)

| Aşama | Araç maliyeti | SLA cezası | Toplam | İhlal |
|---|---|---|---|---|
| Stage 0 — temel plan | 15.460.592,57 | 1.020.367,20 | 16.480.959,77 | 0 |
| Stage 1 — aynı-hat onarım | 12.510.401,25 | 2.169.783,60 | 14.680.184,85 | 0 |
| Stage 2 — milk-run | 8.752.512,29 | 2.560.826,00 | 11.313.338,29 | 0 |
| Stage 3 — rota-ortası yük alma | 8.616.944,73 | 2.615.532,00 | 11.232.476,73 | 0 |

- Sağ altta kutu: araç maliyetinden 6.843.648 TL kazanç, 1.595.165 TL ek ceza

**Konuşma metni:**

Planı tek hamlede kurmuyoruz, dört basamakta kuruyoruz. Her aşama bir öncekini girdi alıyor.

Temel plan 16 milyon 481 bin lira. Aynı-hat onarımı 14 milyon 680 bine indiriyor. Milk-run zincirleri 11 milyon 313 bine. Rota ortasında yük alma da 11 milyon 232 bine. Her satırda ihlal sıfır.

Bu tabloda gözden kaçırılmaması gereken bir şey var: **SLA cezası bilerek artıyor.** Araç maliyetinden 6 milyon 844 bin lira kazanıyoruz, karşılığında 1 milyon 595 bin lira ceza ödüyoruz. Yani gecikmeyi satın alıyoruz. Bu bir ihmal değil, bilinçli bir takas; ve daha önce söylediğim gibi jürinin gizli bir SLA tavanı koymamış olması bunu meşru kılıyor. Bir aracı yola çıkarmak, küçük bir gecikme cezasından pahalıysa aracı çıkarmıyoruz.

**Vurgu sayıları:** 16.480.959,77 → 11.232.476,73 TL · araç maliyetinde −6.843.648 TL · SLA'da +1.595.165 TL

**Olası ara soru:** *"Ceza artışını jüri nasıl değerlendirir?"* — Puanlanan büyüklük toplam maliyet olduğu için net etki 5,25 milyon liralık iyileşmedir; ayrıca SLA gecikmesi hakem simülatöründe bir ihlal değil, fiyatlanmış bir maliyet kalemi olarak görünür.

---

### Slayt 11 — Stage 0: temel plan  (~50 sn)

**Slaytta ne var:**
- Günlük akış şeması: zorunlu kiralık filoyu doldur → tır ziyaret bütçesini rezerve et → hat-gün araç karmasını tam sayımla seç → kalanı ertele → iki boşaltma günü
- Sonuç künyesi: 1.269 fiziksel araç (126 kiralık + 1.143 spot), 3.167 plan satırı, 16.480.959,77 TL, 0 ihlal
- İki kritik karar kutusu: kiralık tırlar önceden rezerve ediliyor · erteleme mekanizması

**Konuşma metni:**

Stage 0 "doğru ama saf" bir taban plan. Günlük döngüsü şu: önce zorunlu kiralık filo doldurulur, sonra kıt tır ziyaret bütçesi dağıtılır, sonra her hat-gün için araç karması tam sayımla seçilir, sığmayan yük ertelenir, ufuk bitince kalan yük iki boşaltma gününde sıfırlanır.

İki karar kritik. Birincisi: kiralık tırların hem çıkış hem varış ziyaretini, planlama başlamadan **önce** bütçeden düşüyoruz. Bunu ölçtük — rezervasyonu kaldırırsanız plan 12 tır kapasitesi ihlali veriyor. Rezervasyonla ihlal sıfır.

İkincisi erteleme. Şartname düşük talepte gönderiyi bekletmeye izin veriyor. Erteleme mekanizmasını tamamen kapattığımızda Stage 0 toplamı 16 milyon 481 binden 24 milyon 955 bine çıkıyor. Yani tek başına erteleme 8,5 milyon lira kazandırıyor. Ama bu bir keyfî bekletme değil: ertelemenin bedeli aday değerlendirmesinin içinde birebir fiyatlanıyor ve üç sert kuralla sınırlanıyor.

**Vurgu sayıları:** 1.269 araç · 16.480.959,77 TL · erteleme kapalıyken 24.954.608,68 TL

**Olası ara soru:** *"Erteleme sadece cezayı ileriye mi atıyor?"* — Hayır, ölçtük: 1.020.367,20 TL SLA cezası ödeyip 9.494.016,11 TL araç maliyeti tasarruf ediyoruz, net kazanç 8.473.648,91 TL ve her iki koşumda da ihlal sıfır.

---

### Slayt 12 — Stage 1: aynı-hat onarımı  (~35 sn)

**Slaytta ne var:**
- Önce/sonra minyatürü: aynı hatta aynı gün iki yarı boş spot araç → tek araç
- Sayaçlar: 1.003 verici değerlendirildi, 177 hamle kabul, 394 parça / 59.852 desi taşındı, 177 spot araç silindi
- Sonuç: 1.269 → 1.092 araç, 14.680.184,85 TL, tasarruf 1.800.774,93 TL

**Konuşma metni:**

Stage 1 en basit aşama ve tam da bu yüzden en güvenli. Yaptığı tek şey şu: aynı hat üzerinde, düşük dolulukta bir spot aracın **tüm** yükünü aynı hattaki mevcut bir araca taşımak ve o aracı plandan silmek. Hiçbir talep bölünmüyor, hiçbir yeni araç yaratılmıyor, hiçbir aracın hattı değişmiyor.

Vericiler doluluk oranına göre en boştan başlayarak deneniyor. Bin üç verici değerlendirildi, 177 hamle kabul edildi; 394 yük parçası, toplam 59.852 desi başka araçlara taşındı ve tam 177 spot araç silindi. Toplam 1 milyon 801 bin lira tasarruf.

Bir noktayı açıkça söyleyeyim: burada SLA cezası iki katına çıkıyor, 1 milyondan 2,17 milyona. Ama araç maliyeti 15,5 milyondan 12,5 milyona iniyor. Net etki 1,8 milyon liralık iyileşme ve ihlal yine sıfır.

**Vurgu sayıları:** 177 hamle · 177 araç silindi · −1.800.774,93 TL

**Olası ara soru:** *"Kiralık araçları da siliyor musunuz?"* — Hayır; kiralık bacak asla verici olamaz, çünkü şartname talep olmasa bile kiralık araçların her gün çıkmasını zorunlu kılıyor — boş çıkan 35 kiralık bacak plana dokunulmadan kalıyor.

---

### Slayt 13 — Stage 2: milk-run zincirleri  (~55 sn)

**Slaytta ne var:**
- Zincir görseli: aynı merkezden aynı dakikada kalkan 4 ayrı araç → tek fiziksel araç, dört durakta sırayla bırakma
- Arama künyesi: 93 grup, 5.426 ikili, 96.369 çoklu alt küme, 227 zincir kabul, 626 kaynak araç birleşti
- Sonuç: 1.092 → 693 araç, 11.313.338,29 TL, tasarruf 3.366.846,56 TL
- Jüri alıntısı kutusu: "Spot araçlar için evet mümkündür fakat kiralık araçlar için uğrama mümkün değildir."

**Konuşma metni:**

En büyük kazanç burada, 3 milyon 367 bin lira. Fikir şu: aynı çıkış merkezinden **tam olarak aynı dakikada** yüklenen iki ile dört ayrı aracı tek bir fiziksel araca zincirliyoruz. Araç çıkışta her şeyi yüklüyor, her durakta yalnız o durağa ait yükü indiriyor, gemide kalan yük ara merkezde hiç elleçlenmiyor.

Kural dayanağı jüri soru-cevabında net: "Spot araçlar için evet mümkündür fakat kiralık araçlar için uğrama mümkün değildir." Ve sefer sayısı üst sınırı sorusuna verilen cevap "kısıtlamalar dikkate alınarak sınırsız sefer yapabilirsiniz."

Arama tam sayım, örnekleme yok: 93 grupta 5.426 ikili ve 96.369 çoklu alt küme fiyatlandı, her alt küme için tüm durak sıraları ve sığan tüm araç tipleri denendi. 227 zincir kabul edildi ve 626 ayrı araç birleşti.

Kritik ayrım: **segment sayısı değişmiyor**, 1.092'de kalıyor. Zincir yeni bacak yaratmıyor; dört ayrı aracın işini tek araca bindiriyor. Araç sayısı 1.092'den 693'e iniyor.

**Vurgu sayıları:** 96.369 alt küme denendi · 227 zincir kabul · −3.366.846,56 TL

**Olası ara soru:** *"Neden en fazla dört durak? Şartnamede sınır var mı?"* — Şartnamede ve Q&A'da durak sayısına hiçbir sınır yok; dört bizim mühendislik tercihimiz: üç durakla toplam 11.519.240,35 TL, dört durakla 11.313.338,29 TL çıkıyor, beş durak ise kaba kuvvetle uygulanabilir değil — yaklaşık 13,5 dakika işlemci ve 1,3 GB bellekten sonra sonuç vermedi. Gerçek sınır kapasite: zincirler tır kullanmadığı için bir rota en çok 12.000 desi taşıyabiliyor.

---

### Slayt 14 — Stage 3: rota ortasında yük alma  (~55 sn)

**Slaytta ne var:**
- Şema: zincir bir ara durakta yalnız indirmesin, oradan kalkacak yükü de alsın; o yükü tek başına taşıyan araç plandan silinsin
- İki zaman damgası kutusu: `unload_end = varış + inen desinin elleçlemesi` (SLA bundan hesaplanır) · `kalkış = unload_end + alınan yükün elleçlemesi` (yalnız aracı geciktirir)
- Arama künyesi: 227 hedef rotanın 399 ara durağı × 340 verici = 135.660 (rota-durak, verici) çifti, 56 kârlı aday, 28 kabul, 28 araç silindi
- Jüri alıntısı: "bir araçtan x kadar yük indirilip y kadar yük yüklenirse kapasiteden x+y kadar yük düşülür."

**Konuşma metni:**

Stage 2'ye kadar zincirlerimiz yalnız indiriyordu. Jüri bunun tersini de açıkça serbest bırakmış: bir araçtan x kadar yük indirilip y kadar yük yüklenirse kapasiteden x artı y düşülür. Bu cümle hem izni hem elleçleme aritmetiğini birlikte veriyor.

Biz bunu **Tier A** biçiminde uyguluyoruz: alınan yükün varışı, rotanın **zaten uğradığı** bir durak olmak zorunda. Böylece rota topolojisi hiç değişmiyor, zincir uzamıyor, dört durak sınırı ve talep bölme sözleşmesi aynı kalıyor. Kazanç tamamen o yükü ayrı taşıyan aracın ortadan kalkmasından geliyor.

Arama tam sayım: 227 hedef rotanın 399 ara durağı ile 340 vericinin hepsi eşleştirildi, yani 135.660 çift incelendi. 56'sı kesin kâr etti, 28'i kabul edildi ve 28 araç silindi.

Burada sessiz bir hata kaynağı var, onu vurgulayayım: yük alma durağında **iki ayrı zaman damgası** var. İnen kargonun SLA'sı indirmenin bittiği anda durur; ondan sonra başlayan yükleme aracı geciktirir ama teslimatı geciktirmez. Prototipte bu ikisini karıştırmak 5.108,80 liralık fazla beyana yol açmıştı; şimdi ikisi de birer regresyon testiyle çivili.

**Vurgu sayıları:** 135.660 çift · 28 araç silindi · −80.861,55 TL

**Olası ara soru:** *"Kiralık bir aracı da yolda doldurabilir misiniz?"* — Hayır, dört bağımsız katmanda engellendi: kiralık rotalar hedef taramasında atlanıyor (ölçülen 126 rota), kiralık rota spot tarifesiyle fiyatlanmaya çalışılırsa kod hata fırlatıyor, verici filtresi de yayın öncesi şekil kontrolü de yalnız spot kabul ediyor.

---

### Slayt 15 — Hakem simülatörü  (~45 sn)

**Slaytta ne var:**
- İki kutu yan yana: "Planlayıcı" ve "Hakem" — aralarında yalnız iki DataFrame okuyla bağlantı
- Hakemin yeniden hesapladıkları: araç zaman çizelgesi, kullanım süresi, maliyet, SLA, elleçleme defteri, tır ziyaret defteri
- Ölçüm: teslim edilen dosyada 0 ihlal, beyan edilen toplam ile hakem toplamı arasındaki fark 0,0000 TL

**Konuşma metni:**

Bu projede tek bir sayıya bile "hesapladım, doğrudur" demiyoruz. Hakem simülatörü, planlayıcıdan tamamen ayrı yazılmış ikinci bir uygulama. Optimizerin iç durumunu, nesnelerini, maliyet önbelleğini **hiç görmüyor**; yalnızca 16 kolonluk plan tablosunu, altı kolonluk talep tablosunu ve statik referans verisini okuyor. Araç zaman çizelgesini, maliyeti ve SLA'yı sıfırdan yeniden kuruyor.

Bunun anlamı şu: planlayıcı ile hakem arasındaki her uyuşmazlık gerçek bir hatadır ve teslim öncesi yakalanır. Hakem daha optimizer yazılmadan önce bile iki optimizer-sınıfı hata yakaladı.

Denetim de yalnız fizikî kurallarla sınırlı değil. Plandaki her satırın beyan ettiği yolculuk süresi, elleçleme süresi, SLA cezası ve maliyet payı tek tek denetleniyor; bir fiziksel aracın tüm satırlarının maliyet toplamı, hakemin yeniden hesabıyla bir kuruş toleransında uzlaşmak zorunda. Teslim edilen dosyada ölçülen fark sıfır virgül sıfır sıfır sıfır sıfır lira.

**Vurgu sayıları:** 0 ihlal · beyan-hakem farkı 0,0000 TL

**Olası ara soru:** *"Hakem gerçekten bağımsız mı, aynı kodu mu çağırıyor?"* — Paylaşılan tek şey yuvarlama kurallarını tutan zaman modülü; maliyet, çizelge ve kural denetimi baştan aşağı ayrı yazıldı ve hakem, plan dosyasını diskten geri okuyup yeniden çalıştırıldığında da aynı sonucu veriyor.

---

### Slayt 16 — Kalite kapıları ve determinizm  (~35 sn)

**Slaytta ne var:**
- Dört kapı kartı: aşama kapıları · uzlaşma kapısı (0,000001 TL) · determinizm · artifact doğrulama
- Rozet: 592/592 test
- Kutu: "Rota-ortası yük alma prototipindeki üç hatanın üçünü de uzlaşma kapısı yakaladı"

**Konuşma metni:**

Hakemin üstünde dört kapı daha var.

Birincisi aşama kapıları: her aşamanın kabul edilmiş sonucu birebir sabitlerle çivili — maliyetler, sayımlar ve zincirlerin şekli. Arama algoritmasında sessizce kazanç kaybettiren bir değişiklik olursa boru hattı yayını reddediyor.

İkincisi uzlaşma kapısı: aramanın kendi aritmetiğiyle iddia ettiği tasarruf ile hakemin ölçtüğü fark, kuruşun milyonda birine kadar aynı olmak zorunda. Rota-ortası yük alma prototipindeki üç hatanın — kiralık rotayı hedef almak, yanlış SLA zaman damgası, yükün hedefini geçmesi — **üçünü de** bu kapı yakaladı; başka hiçbir kontrol fark etmiyordu.

Üçüncüsü determinizm: aşamalar karıştırılmış girdiyle de çalıştırıldı, plan birebir aynı çıktı.

Dördüncüsü artifact doğrulama: Excel yazıldıktan sonra diskten geri okunuyor, şeması yeniden doğrulanıyor ve hakem yeniden çalıştırılıyor.

**Vurgu sayıları:** 0,000001 TL tolerans · 592/592 test

**Olası ara soru:** *"Aynı kodu iki kez çalıştırsak aynı planı mı alırız?"* — Evet; hiçbir yerde rastgelelik, zaman damgası veya sözlük sırası bağımlılığı yok, adaylar tamamen anlamsal anahtarlarla sıralanıyor ve bu 24 farklı girdi permütasyonu üzerinde testle çivilenmiş durumda. Bir netleştirme: bu dört kapı geliştirme ve yayın hattında — `run.py` ve 592 testlik pakette — çalışır; final koşusundaki `main.py` bunlardan yalnız çıktının diskten geri okunup şemasının yeniden doğrulanmasını taşır, çünkü sabit sonuç kapıları bilinmeyen bir veri setinde tanım gereği hata verir ve Bölüm 10'a göre hatalı çalıştırma sayılırdı; bağımsız hakem denetimi final pakette `tools/verify_output.py` ile istendiği an tekrar çalıştırılabiliyor.

---

### Slayt 17 — Final backtest uyumu: main.py ve sözleşmeler  (~50 sn)

**Slaytta ne var:**
- Bölüm-gereksinim eşleme tablosu (kısa): Bölüm 3 tek giriş noktası · Bölüm 2 tahmin çağrılmaz · Bölüm 4 girdi sözleşmesi · Bölüm 5 çıktı sözleşmesi · Bölüm 6 manifest · Bölüm 9 bağımlılıklar
- Kanıt kutusu: aynı girdiyle üretilen dosya önceki teslimle **0 farklı hücre** (5.523 satır × 16 kolon)
- Değişen dosya sayısı: 2

**Konuşma metni:**

Final aşaması için ne değiştirdiğimizi tek cümleyle söyleyeyim: algoritmaya dokunmadık.

Kök dizinde argümansız çalışan bir `main.py` var; aşamaları sırayla çağıran ince bir orkestratör, içinde tek bir optimizasyon kararı yok. Tahmin modülü çağrılmıyor — import grafiğinde tahmin modüllerine hiçbir yoldan ulaşılamıyor. Girdi ve çıktı sözleşmesinin tamamı ayrı bir modülde toplandı: kolon adlarını Unicode ve büyük-küçük harf toleransıyla eşliyor, tarih ve saat hücrelerinin bütün makul Excel tiplerini kanonik biçime çeviriyor, ufku girdinin Tarih kolonundan türetiyor.

Kanıtı da şu: aynı talep tablosuyla çalıştırıldığında `main.py`, önceki aşamada teslim ettiğimiz dosyayla **hücre hücre birebir aynı** çıktıyı üretiyor — 5.523 satır, 16 kolon, sıfır farklı hücre. Algoritma dosyalarından hiçbiri değişmedi; değişen dosya sayısı iki ve ikisi de yalnızca davranış genişletiyor.

**Vurgu sayıları:** 0 farklı hücre · 5.523 satır × 16 kolon · değişen dosya: 2

**Olası ara soru:** *"Talep kimlikleri kanonik biçimde gelmezse ne oluyor?"* — Girdideki kimlikler iç boru hattının kullandığı kanonik biçime eşleniyor, çıktıda ise özgün kimlikler geri yazılıyor; sıralama anahtarı kendi tahmin modülümüzle birebir aynı olduğu için girdi bizim tahmin çıktımızsa eşleme özdeşlik oluyor ve plan bit-birebir aynı kalıyor.

---

### Slayt 18 — Bölüm 10 güvenlikleri ve genelleştirilebilirlik  (~45 sn)

**Slaytta ne var:**
- İki güvenlik kartı: kademeli yayın · sert süre sınırı
- Bölüm 7 senaryo tablosu

| Senaryo | Ufuk | Talep | Süre | İhlal |
|---|---|---|---|---|
| Referans | 29.06.2026 - 05.07.2026 | 4.046 | 150 sn | 0 |
| Farklı yıl, 4 günlük ufuk, %35 hacim, REQ_ kimlikler | 25.05.2025 - 28.05.2025 | 1.808 | 171 sn | 0 |
| Farklı hafta, %125 hacim, HH:MM:SS | 02.09.2026 - 08.09.2026 | 2.925 | 143 sn | 0 |

- Kutu: zorla sonlandırma testinde diskte 3.710 satırlık geçerli plan bulundu

**Konuşma metni:**

Bölüm 10 dört durumu hatalı çalıştırma sayıyor: sıfırdan farklı çıkış kodu, yüz dakikayı aşmak, çıktı üretmemek ve şemadan sapmak. Dördü için de bir güvenliğimiz var.

Birincisi kademeli yayın: geçerli ilk plan elde edilir edilmez çıktı dosyası yazılıyor, kabul edilen her aşama dosyayı atomik olarak güncelliyor. Bunu zorla test ettik — süreci Stage 2'nin ortasında öldürdüğümüzde diskte 3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru bir plan kaldı.

İkincisi sert süre sınırı: her arama aşaması ayrı bir iş parçacığında, kalan bütçeyle sınırlı çalışıyor. Sınır dolarsa aşama terk ediliyor, önceki plan korunuyor ve süreç çıkış kodu sıfırla bitiyor. Bunu 36 saniyelik bütçeyle ölçtük: Stage 2 terk edildi, Stage 1 planı yayınlandı, toplam 32,4 saniye, sıfır ihlal.

Genelleştirilebilirlik tarafında da kodda gömülü takvim tarihi yok; farklı yıl, farklı ufuk uzunluğu, farklı hacim ve farklı kimlik biçimleriyle test edildi — üçünde de çıkış kodu sıfır ve sıfır ihlal.

**Vurgu sayıları:** ~150 sn / 100 dk tavan · 3.710 satır · 3 farklı senaryoda 0 ihlal

**Olası ara soru:** *"Hacim çok daha büyük gelirse ne olur?"* — Dürüst cevap: ağın elleçleme kapasitesi referans hafta için zaten neredeyse dolu; İstanbul'da 1 Temmuz'da günlük talep 395.825 desi, kapasite 394.786 desi. Hacim belirgin biçimde artarsa kısıt hiçbir plan tarafından sağlanamaz; bu bir kod kusuru değil, veri setinin fizikî olarak çözümsüz olmasıdır ve o durumda bile kod çökmeden geçerli bir plan yazıyor.

---

### Slayt 19 — Sonuçlar: filo, doluluk, araç karması  (~45 sn)

**Slaytta ne var:**
- Araç sayısı merdiveni: 1.269 → 1.092 → 693 → 665; Stage 3'te 438 tek bacak + 127 iki duraklı + 28 üç duraklı + 72 dört duraklı
- Doluluk tablosu: ortalama %48,02 → %56,82 → %76,96 → %79,03; %30 altındaki spot araç 480 → 296 → 46 → 30
- Araç türü karması: Kamyonet 950 → 233, Kamyon 196 → 304, Tır 99 sabit

**Konuşma metni:**

Sonuç üç grafikte özetleniyor.

Fiziksel araç sayısı 1.269'dan 665'e indi. Bugün planın 227 aracı çok duraklı: 127'si iki, 28'i üç, 72'si dört duraklı.

Doluluk yüzde 48'den yüzde 79'a çıktı. Daha anlamlı olan sayı şu: doluluğu yüzde 30'un altında kalan spot araç sayısı 480'den 30'a indi. Yarı boş araç neredeyse kalmadı.

Araç türü karması da küçükten büyüğe kaydı: Kamyonet sayısı 950'den 233'e düşerken Kamyon 196'dan 304'e çıktı. Yani yarı boş küçük araçlar birleşip daha az sayıda ama daha dolu büyük araca bindi.

Tır sayısı 99'da sabit ve bu bilinçli. Tır kapasitesi kıt bir kaynak, yedi merkezde sıfır; onu zorlamıyoruz. Zaten ölçtük — tırı zincirlere katmak sonucu 18.100 lira **kötüleştiriyor**.

**Vurgu sayıları:** 665 araç · %79,03 doluluk · %30 altı: 480 → 30

**Olası ara soru:** *"Kalan 30 düşük dolulu aracı da birleştiremez misiniz?"* — Stage 2 sonrası kalan 46 aracı aynı hatta birleştirmeyi ölçtük: kazanç tam olarak 0 TL, çünkü 46'sının 46'sı da o gün o hattın tek aracı; Stage 3 bu duvarı farklı yönden aştı ve sayıyı 30'a indirdi.

---

### Slayt 20 — Ölçülmüş çıkmaz sokaklar  (~35 sn)

**Slaytta ne var:**
- Tablo: fikir → ölçüm

| Fikir | Ölçüm |
|---|---|
| Düşük dolulukta aynı-hat birleştirme | 0 TL — 46 aracın 46'sı o gün o hattın tek aracı |
| Tır'ı zincire katmak | 18.100 TL daha kötü |
| Beş duraklı zincir | Kaba kuvvetle uygulanamaz: 13,5 dk işlemci, 1,3 GB, sonuç yok |
| Tahmin bias'ını düzeltmek (4 aday) | Hedef sahte çıktı — LOO ile teslim modelinin bias'ı −0,0573; dördü de dışsal örneklemde başarısız |
| Açgözlü yerine tam eşleme | 47.796 TL, ama çoklu-durak geçişinin alternatifi, toplamı değil; bugünkü çözüm bunu ~476.000 TL ile aşıyor |
| En kötü talepleri hedefleyerek SLA azaltma | Uzun kuyruk — en kötü 20 talep cezanın yalnız %15'i |

**Konuşma metni:**

Bu slayt bilerek burada. Denemediklerimizi değil, **deneyip ölçerek reddettiklerimizi** gösteriyor; çünkü bir mühendislik kararının değeri, reddedilen alternatifin sayısıyla ölçülür.

Altı fikri ölçtük. Aynı-hat birleştirmenin kazancı tam olarak sıfır lira çıktı. Tırı zincire katmak sonucu on sekiz bin lira kötüleştirdi — Kamyon aynı kapasitede tırı her koşulda eziyor. Beş duraklı zincir kaba kuvvetle uygulanabilir değil. Tahmin bias'ını düzeltmek için dört ayrı aday denedik, dördü de dışsal örneklemde başarısız oldu — hedefin kendisi bir kalibrasyon artefaktı çıktı.

Bunları belgede satır satır tuttuk; sorularınız olursa detayına girebiliriz.

**Vurgu sayıları:** 6 fikir ölçüldü ve reddedildi · tır zinciri +18.100 TL kötü · aynı-hat birleştirme 0 TL

**Olası ara soru:** *"Bunları neden sunuma koydunuz?"* — Çünkü her biri bir jüri sorusunun peşin cevabı: "şunu neden denemediniz" sorusunun karşılığı "denedik, şu kadar ölçtük, şu yüzden reddettik" olduğunda tartışma kanıt üzerinden yürüyor.

---

### Slayt 21 — Kapanış ve gelecek iş  (~40 sn)

**Slaytta ne var:**
- Üç kapanış sayısı tekrar: 11.232.476,73 TL · −%31,84 · 0 ihlal
- Üç maddelik gelecek iş listesi: ay sonu haftası tahmin bias'ı · Tier B rota uzatma · beş duraklı zincir için dal-sınır budaması
- Kapanış cümlesi ve teşekkür

**Konuşma metni:**

Toparlayayım. Bir haftalık talebi 11 milyon 232 bin liraya taşıyan bir plan ürettik; kendi temel planımıza göre yüzde 31,84 daha ucuz ve dört aşamanın hiçbirinde tek bir kural ihlali yok. Uçtan uca çalışma yaklaşık iki buçuk dakika, tavan yüz dakika. 592 regresyon testinin tamamı geçiyor.

Ve tekrar altını çizeyim: bu sayıların hiçbirini kendimiz onaylamadık. Bağımsız hakem simülatörü, uzlaşma kapısı ve diskten geri okuyan artifact doğrulaması hepsini yeniden hesaplıyor.

Sırada üç iş var. Birincisi tahmin tarafında ay sonu haftasındaki bias — en yüksek değerli açık kalemimiz. İkincisi rota ortasında yük almanın rotayı bir durak uzatan Tier B varyantı; bağımsız bir ölçüm ek altmış altı bin lira gördü ama zincir sözleşmemizi değiştiriyor, ayrı bir karar konusu. Üçüncüsü beş duraklı zincirleri budama ile ulaşılabilir kılmak.

Dinlediğiniz için teşekkür ederim; sorularınızı almaktan memnuniyet duyarım.

**Vurgu sayıları:** 11.232.476,73 TL · −%31,84 · 0 ihlal · 592/592 test

**Olası ara soru:** *"Bir cümleyle en güçlü yanınız nedir?"* — Kazancın kaynağı tek bir zekice fikir değil, dört bağımsız iyileştirmenin üst üste binmesi ve her birinin ancak bağımsız bir hakemden sıfır ihlalle geçtiğinde kabul edilmesi.

---

## 3. Ezberlenecek 8 sayı

Sunumda başka hiçbir şey hatırlamasanız bu sekiz sayıyı hatırlayın. Her biri en az bir slaytta mutlaka telaffuz edilmeli.

| # | Sayı | Ne olduğu | Nerede söylenecek |
|---|---|---|---|
| 1 | 11.232.476,73 TL | Yayınlanan planın toplam maliyeti | Slayt 1, 10, 21 |
| 2 | −%31,84 | Stage 0 temel planına göre iyileşme | Slayt 1, 21 |
| 3 | 0 | Hakem ihlali — dört aşamanın hepsinde | Slayt 1, 9, 15, 21 |
| 4 | 1.269 → 665 | Fiziksel araç sayısı | Slayt 1, 19 |
| 5 | %48,02 → %79,03 | Ortalama spot araç doluluğu | Slayt 1, 19 |
| 6 | ×0,0198 | Ayın son gününün takvim çarpanı | Slayt 4, 6 |
| 7 | 0,5328 → 0,4464 | Ay sonu haftası WMAPE — düz medyandan bizim modele | Slayt 7 |
| 8 | 0 farklı hücre | Final paketi ile önceki teslim arasındaki fark | Slayt 17 |

Yedek sayılar (sorulursa lazım olur): 96.369 milk-run alt kümesi · 135.660 yük alma çifti · 592/592 test · ~150 sn / 100 dk · 4.046 satır ve 4.977.975 desi.

---

## 4. Süre aşarsak — atlanacak slaytlar önceliği

Sırayla feda edin. Her adımın yanında yaklaşık kaç saniye kazandırdığı yazılı.

1. **Slayt 20 — Ölçülmüş çıkmaz sokaklar (~35 sn).** Ekranda gösterin, okumayın. "Altı fikri ölçüp reddettik, detayı belgede var" deyip geçin.
2. **Slayt 12 — Stage 1 (~35 sn).** En basit aşama. Tek cümleyle özetlenebilir: "Aynı hatta gereksiz ikinci aracı sildik, 177 araç, 1,8 milyon lira."
3. **Slayt 16 — Kalite kapıları (~35 sn).** Slayt 15'te hakemi anlattıktan sonra "üstünde dört kapı daha var, en kritiği kuruşun milyonda birine kadar uzlaşma kapısı" demek yeter.
4. **Slayt 3 — Veri temizleme (~35 sn).** Sadece "tam grid ve 23 dışlanan tarih" cümlesini söyleyin, huni grafiğini geçin.
5. **Slayt 6 — Takvim katmanı (~45 sn).** Slayt 4'te çöküşü gösterdiyseniz üç çarpanı okuyup sızıntı korumasını tek cümleye indirin.

**Asla atlanmayacak beş slayt:** 10 (maliyet merdiveni), 13 (milk-run), 14 (rota-ortası yük alma), 15 (hakem simülatörü), 17 (final backtest uyumu). Bu beş slayt çözümün savunmasının tamamıdır: ilk üçü kazancın kaynağını, son ikisi sonucun ve teslimin geçerliliğini anlatır.

**Tersine, süre kalırsa:** Slayt 11'de erteleme karşı-olgusunu (16,48 milyon yerine 24,95 milyon) ve Slayt 13'te üç durak/dört durak karşılaştırmasını açın; ikisi de "bu sayıyı nasıl bildiniz" sorusunu peşinen cevaplar.

---

## 5. Demo yaparsak — `python main.py`

Demo zorunlu değil ve **canlı tam koşu önerilmez**: referans veri setinde uçtan uca süre yaklaşık **150 saniye**, yani iki buçuk dakika. On beş dakikalık bir sunumda bu sürenin altıda birini bir terminale bakarak geçirmek pahalıdır.

### Önerilen yol: önceden kaydedilmiş çıktı

Koşuyu sunumdan **önce** yapın, terminal çıktısını bir metin dosyasına alın ve slayt üzerinde gösterin:

```
python main.py > kosu-kaydi.txt 2>&1
```

Konsol çıktısının yapısı şudur (sayı biçimi Python'un varsayılanıdır, yani binlik ayracı virgüldür):

```
Girdi talep tablosu : ...\final-teslim\data\one_week_backtest.xlsx
    - Talep kimlikleri kanonik biçimde; eşleme özdeşlik
Talep satırı        : 4046  |  toplam desi: 4,977,975
Ufuk (girdiden)     : 29.06.2026 - 05.07.2026 (7 gün)
Stage 0 bacak       : 1269  (2.2 sn)
[Stage 0 temel plan]
    Araç maliyeti :    15,460,592.57 TL
    SLA cezası    :     1,020,367.20 TL
    TOPLAM        :    16,480,959.77 TL
    Segment       : 1269
    Fiziksel rota : 1269 (126 kiralık, 1143 Spot)
    Plan satırı   : 3167
    İhlal         : 0
    → çıktı güncellendi (Stage 0)
[Stage 1 aynı-hat onarım] kabul edildi; tasarruf 1,800,774.93 TL (...)
    → çıktı güncellendi (Stage 1)
[Stage 2 milk-run] kabul edildi; tasarruf 3,366,846.56 TL (...)
    → çıktı güncellendi (Stage 2 milk-run)
[Stage 3 rota-ortası yük alma] kabul edildi; tasarruf 80,861.55 TL (...)
    → çıktı güncellendi (Stage 3 rota-ortası yük alma)
[Yayınlanan plan]
    ...
    TOPLAM        :    11,232,476.73 TL
    İhlal         : 0
Optimizasyon süresi : ... sn
Toplam süre         : ... sn
Çıktı               : ...\final-teslim\out\Tasima-plani.xlsx
```

### Demoda gösterilecek üç şey

1. **Ufuk satırı.** "Ufuk (girdiden)" satırını parmakla gösterin: tarih aralığı girdi dosyasından türetiliyor, kodda gömülü takvim tarihi yok — Bölüm 7'nin kanıtı tek satırda.
2. **Dört tasarruf satırı.** Aşamaların kabul satırları maliyet merdiveninin canlı hâlidir: 1.800.774,93 + 3.366.846,56 + 80.861,55 TL.
3. **Son iki satır.** Toplam 11.232.476,73 TL ve İhlal 0.

### Canlı koşu yapılacaksa

- Koşuyu **sunumun başında** arka planda başlatın, sonuca kapanış slaytında dönün. Program çıktısını her aşamada anında bastığı için ekranda ölü bekleme olmaz.
- Kısa demo istenirse süre bütçesini düşürün: `TEKNOFEST_TIME_BUDGET_MIN=0.6` ile koşu 32,4 saniyede biter, Stage 2 terk edilir, Stage 1 planı yayınlanır, çıkış kodu 0 ve ihlal 0 olur. Bu aynı zamanda Bölüm 10 güvenliğinin canlı gösterimidir — ama **sonucun 11,23 milyon olmayacağını** önceden söyleyin, yoksa yanlış anlaşılır.
- Çıktının bağımsız denetimini göstermek isterseniz `python tools/verify_output.py` planı diskten geri okuyup hakem simülatöründen geçirir ve beyan-hakem farkını basar; referans koşuda bu fark 0,0000 TL'dir.

---

## 6. Sunum öncesi 10 dakikalık hazırlık listesi

Sahneye çıkmadan önce sırayla uygulanacak liste. Toplam süresi yaklaşık on dakikadır.

**Dakika 0-2 — Dosya ve ortam**

1. `final-teslim/out/Tasima-plani.xlsx` dosyasının yerinde olduğunu ve 5.523 satır içerdiğini doğrulayın.
2. Önceden alınmış koşu kaydını (`kosu-kaydi.txt`) ve yedek ekran görüntülerini açık bir klasörde hazır tutun — canlı demo çökerse tek tıkla geçilebilsin.
3. Sunumu tam ekran açın, ikinci ekranda bu belge açık dursun.

**Dakika 2-4 — Sekiz sayı**

4. "Ezberlenecek 8 sayı" tablosunu yüksek sesle bir kez okuyun. Özellikle üçünü şaşırmadan söyleyebildiğinizden emin olun: **11.232.476,73** — **−%31,84** — **0 ihlal**.
5. Yedek sayıları da bir kez gözden geçirin: 96.369, 135.660, 592/592, ~150 sn.

**Dakika 4-6 — Üç zor sorunun cevabı**

6. *"SLA cezanız neden artıyor?"* → Araç maliyetinden 6.843.648 TL kazanıp 1.595.165 TL ceza ödüyoruz; jüri gizli SLA tavanı koymadı, doğru hedef toplam maliyet.
7. *"Durak sayısını neden dört ile sınırladınız?"* → Kural sınırı yok, mühendislik tercihi; üç durakla 11.519.240,35 TL, dört durakla 11.313.338,29 TL, beş durak kaba kuvvetle uygulanamaz.
8. *"Algoritmayı final için değiştirdiniz mi?"* → Hayır; aynı girdiyle çıktı önceki teslimle 0 farklı hücre, değişen dosya sayısı 2 ve ikisi de yalnızca davranış genişletiyor.

**Dakika 6-8 — Akış provası**

9. Slayt haritasını başparmakla takip ederek on iki blok başlığını sırayla söyleyin: açılış, problem, veri, ay sonu, tahmin, backtest, maliyet modeli, merdiven, hakem, final uyumu, sonuçlar, kapanış. Metni değil, **sırayı** ezberleyin.
10. Atlama önceliğini gözden geçirin: 20, 12, 16, 3, 6 — bu sırayla feda edilecek. Asla atlanmayacaklar: 10, 13, 14, 15, 17.

**Dakika 8-10 — Son kontrol**

11. Kapanış cümlesini bir kez sesli tekrar edin; sunumun en çok hatırlanan cümlesi odur.
12. Su alın, telefonu susturun, saatinizi görebileceğiniz bir yere koyun. Yedinci slayta 5 dakikayı geçmeden ulaşmayı hedefleyin; geçtiyseniz atlama önceliğini uygulamaya slayt 12'den başlayın.
