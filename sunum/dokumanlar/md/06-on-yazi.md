# Ön Yazı

**TEKNOFEST 2026 · Hepsiburada — Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu**
**Takım Büke · Takım No 997307 · Final Aşaması**

---

## Sayın Jüri Üyeleri,

Ekte final sunumumuzu, sunuma eşlik eden interaktif kontrol panosunu ve teknik
dokümanlarımızı bulacaksınız. Bu ön yazı, hangi dosyanın neyi anlattığını ve
çalışmamızın nerede durduğunu kısaca özetlemek içindir.

---

## Neyi çözdük

Problem, bir haftalık talebi onlarca operasyonel kısıta uyarak **en düşük toplam
maliyetle** taşıyan bir sevkiyat planı üretmekti. Çözümümüz iki parçadan oluşuyor:

**Talep tahmini.** İki katmanlı ve kasten sade bir model: her çıkış–varış–saat–haftagünü
kombinasyonu için son dört gözlemin medyanı, üstüne geçmişten **ölçülmüş** bir takvim
çarpanı. Ay sonu ve resmî tatiller "aykırı değer" olarak temizlenmedi; ayrı birer rejim
olarak modellendi. Dondurulmuş bir geri-testte, ay sonu haftasında WMAPE 0,5328'den
**0,4464**'e indi; normal bir haftada ise basit taban modelle birebir aynı kaldı — yani
katman yalnız gerektiği yerde devreye giriyor, başka hiçbir yerde zarar vermiyor.

**Optimizasyon.** Planı tek hamlede kurmuyoruz. Dört aşamalı bir maliyet merdiveni var
ve her aşama bir öncekinin çıktısını girdi alıyor: zorunlu kiralık filoyu önce dolduran
temel plan, aynı hattaki düşük dolulukları birleştiren onarım, aynı merkezden aynı
dakikada kalkan araçları tek fiziksel araca bindiren **milk-run** zincirleri, ve
zincirlerin ara duraklarda yük de almasını sağlayan **yol üstü toplama**.

Sonuç: temel plandan **%31,84 daha ucuz** bir plan. 16.480.959,77 ₺ → **11.232.476,73 ₺**.
Fiziksel araç sayısı 1.269'dan **665**'e, ortalama spot doluluk %48,02'den **%79,03**'e.
Uçtan uca çalışma süresi referans veri setinde **~150 saniye** — şartnamedeki 100 dakikalık
tavanın kırkta biri.

---

## Neye güvenerek bu sayıları söylüyoruz

Bir optimizasyon kodu kendi hesabına göre daima haklıdır. Planı üreten ve maliyeti
hesaplayan kod aynı varsayımı paylaşıyorsa, ikisi de yanlışken hiçbir test bunu göremez.

Bu yüzden planlayıcıdan **tamamen ayrı** bir hakem simülatörü yazdık. Optimizatörün iç
durumunu hiç görmez; yalnızca diske yazılan Excel çıktısını ve şartnamenin ham veri
dosyalarını okuyup maliyeti ve 17 kuralı sıfırdan yeniden hesaplar. Bir aşama ancak hem
taban plan hem aday plan hakemden **sıfır ihlalle** geçerse kabul edilir; aksi hâlde aday
kârlı olsa bile atılır ve resmî çıktı hiç değişmez.

Bu kapı işe yaradı: Stage 3 prototipindeki üç hatanın üçünü de yalnız o yakaladı —
zorunlu kiralık bir rotayı yük alma hedefi seçmek, yanlış SLA zaman damgası kullanmak,
ve alınan yükün varış durağını geçmesi. Hiçbiri programı çökertmiyordu; üçü de sessizce
yanlış ama geçerli görünen bir plan üretiyordu.

Bunun üstünde 592 regresyon testi, determinizm kontrolü ve yayın öncesi artifact
doğrulaması var. Beyan ettiğimiz maliyet ile hakemin bağımsız hesabı arasındaki fark
**0,0000 ₺**.

---

## Ekteki dosyalar

| Dosya | Ne işe yarar |
|---|---|
| **Sunum (`v2.html`)** | 19 slaytlık jüri sunumu. Tek dosya, dış bağımlılık yok — çift tıklayıp tarayıcıda açın. |
| **Anahat Sevkiyat Panosu** | Nihai planın harita tabanlı interaktif kontrol panosu. Hem web adresinden hem de kurulum gerektirmeyen tek dosyalık `.exe` olarak çalışır. |
| **01 — Algoritma ve Teknik Rapor** | Maliyet modeli, veri katmanı, tahmin modeli, Stage 0–3 merdiveni, hakem simülatörü, ölçülmüş sonuçlar ve ölçülmüş çıkmaz sokaklar. |
| **02 — Jüri Soru-Cevap Hazırlık Kitabı** | Dokuz kategoride 96 soru; her biri için kısa cevap, detay ve kanıt. |
| **03 — Teknik Gereksinim Uyum Matrisi** | Final Backtest dokümanının Bölüm 1–11'i madde madde: ne istendi, ne yaptık, kanıt nerede. |
| **00 / 04 — Sunum akışı ve konuşma notları** | Slayt slayt anlatım metni ve süre planı. |

---

## Sunum nasıl kullanılıyor

Sunum akış olarak şu sırayı izliyor: takım tanıtımı ve sonuç, problemin yapısı, maliyet
modeli ve zaman aritmetiği, veri ve tahmin modeli, dört aşamalı optimizasyon merdiveni,
filoya etkisi, kalite kapıları, final gereksinimlerine uyum, ölçüp reddettiğimiz fikirler
ve özet.

Slaytlar salt metin değil: **kartların ve grafiklerin çoğu tıklanabilir**. Tıklanan her
öğe, o kavramı önce tek cümlelik bir tanımla açan, sonra ölçülmüş veriyle detaylandıran
bir pop-up açıyor — 18 transfer merkezinin haritası, planımızdan gerçek bir milk-run
zinciri, 23 dışlanan tarihin her birinin gerekçesi, hakem simülatörünün yakaladığı
hatalar, ve dahası. Amacımız, jürinin merak ettiği ayrıntıya sunumu bölmeden ulaşabilmesi.

Anlatım sırasında kullanılan kısayollar: `→` / `←` slayt geçişi, `N` konuşma metni,
`O` slayt haritası, `Esc` açık paneli kapatır, `F11` tam ekran.

---

## Kontrol panosu

Sunuma ek olarak, nihai planın tamamını gezilebilir kılan bir pano hazırladık. Türkiye
haritası üzerinde **zorunlu kiralık rotalar**, **spot atamalar**, **konsolidasyon
zincirleri** ve **yol üstü yük alma** hamleleri ayrı katmanlar olarak görülüyor; "Zaman"
kipinde plan dakika dakika oynatılabiliyor ve o anda gerçekten yolda olan araçlar harita
üzerinde hareket ediyor. Bir merkeze tıklandığında yalnız oraya değen seferler kalıyor,
bir rotaya tıklandığında o aracın zinciri durak durak açılıyor.

Panoda ayrıca 665 aracın tek tek arandığı bir filo gezgini, elleçleme ve tır kotalarının
merkez-gün bazında ne kadar zorlandığını gösteren ısı haritaları, geçmiş veri ile
tahminimizin karşılaştırması ve modelin uçtan uca boru hattının görselleştirmesi var.
Panodaki **her sayı**, teslim ettiğimiz plan ve tahmin dosyalarından üretilir; elle
yazılmış tek bir değer yoktur.

Pano tamamen çevrimdışı çalışır — dış harita servisi, CDN ya da internet bağlantısı
gerektirmez.

---

## Açık kalemlerimiz

Dürüst olmak gerekirse üç açık kalemimiz var ve bunları saklamıyoruz: ay sonu
haftasındaki tahmin sapması, rotayı bir durak uzatan Tier B yük alma (bağımsız ölçümümüz
ek ~66 bin ₺ gösterdi ama kalan sürede güvenle doğrulayamadık), ve budamalı arama
gerektiren beş duraklı zincirler. Üçü de sunumda ve teknik raporda açıkça yazılıdır.

Değerlendirmeniz için şimdiden teşekkür ederiz. Sorularınızı yanıtlamaktan memnuniyet
duyarız.

**Takım Büke**
Melih Ekizce · Mustafa Eren Işıktaşlı · Serhat Özdemir · Mert Arı
