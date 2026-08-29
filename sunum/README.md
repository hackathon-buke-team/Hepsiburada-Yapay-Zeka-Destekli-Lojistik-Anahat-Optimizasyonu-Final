# Sunum materyalleri

TEKNOFEST 2026 · Hepsiburada · Takım Büke · Final aşaması jüri sunumu.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| [`v2.html`](v2.html) | **Ana sunum.** 15 slayt (1. slayt takım tanıtımı, son slayt soru-cevap), 15 gömülü SVG grafik, **28 interaktif pop-up**. Tek dosya, dış bağımlılık yok — çift tıklayıp tarayıcıda açın. |
| [`../panel/`](../panel/README.md) | **Anahat Sevkiyat Panosu** — nihai planın harita tabanlı kontrol panosu. Hem web hem tek dosyalık `.exe` olarak çalışır. |
| [`index.html`](index.html) | Önceki aşamadan kalan eski veri panosu (yerini `panel/` aldı). |
| `dokumanlar/` | Jüri için hazırlanan Word dökümanları (`.docx`) ve markdown kaynakları. |
| `kaynak/` | Sunumu ve dökümanları yeniden üreten betikler. |

## Word dökümanları — ne hangisinde

| Belge | Ne işe yarar | Uzunluk |
|---|---|---:|
| **00 — Sunum Konuşma Notları** | `v2.html`'deki 17 içerik slaydından otomatik üretildi; sonradan eklenen 1. slayt (takım tanıtımı) bu belgede yoktur, konuşma metni sunumun kendi `N` panelindedir. Süre planı (toplam 15:15), "süre aşarsak" atlama önceliği, ezberlenecek 10 sayı, slayt slayt metin, 10 dakikalık hazırlık listesi. | ~3.400 kelime |
| **01 — Algoritma ve Teknik Rapor** | Uçtan uca teknik anlatım: maliyet modeli ve zaman aritmetiği, veri katmanı, tahmin modeli, Stage 0–3 optimizasyon merdiveni, hakem simülatörü, final entegrasyon katmanı, ölçülmüş sonuçlar, ölçülmüş çıkmaz sokaklar, bilinen sınırlar. | ~12.800 kelime · 26 tablo |
| **02 — Jüri Soru-Cevap Hazırlık Kitabı** | **96 soru**, dokuz kategoride (problem/maliyet, tahmin, Stage 0, Stage 1-2-3, doğrulama, kural uyumu, final backtest gereksinimleri, zor sorular, karşılama taktikleri). Her soru için kısa cevap + detay + kanıt + tuzak notu. | ~12.400 kelime |
| **03 — Teknik Gereksinim Uyum Matrisi** | Final Backtest dokümanının Bölüm 1–11'i madde madde: jüri ne istedi → biz ne yaptık → kanıt → risk. Bölüm 11 kontrol listesi, şartname uyumu, jüri Q&A eşlemesi, çıktı şema tuzakları, genelleştirilebilirlik kanıtı. | ~11.400 kelime · 21 tablo |
| **04 — Sunum Akışı ve Konuşma Metni** | 21 slaytlık genişletilmiş akış: slaytta ne var, konuşma metni, vurgu sayıları, olası ara soru. Demo senaryosu ve hazırlık listesi dahil. | ~6.900 kelime |

| **06 — Ön Yazı** | Jüriye iletilecek ön yazı: çalışmanın ve sunumun kısa özeti, ekteki dosyaların dökümü, açık kalemler. | ~1.100 kelime |

> Belgelerdeki her sayısal iddia bağımsız bir doğrulama turundan geçirildi; ölçülemeyen
> veya kaynağı bulunamayan değerler düzeltildi. Doğrulama sırasında bulunup düzeltilen
> hatalar arasında SLA düzeltme katmanının etkisi (+14.391,60 TL → **+2.399,60 TL**),
> kayan nokta artefaktı örneği (CPython'da `4.6*60` tam 276'dır; gerçek örnek
> `8.05*60 = 483,00000000000006`), hakem ihlal mesajı sayısı (36 → **33**) ve
> 5 Temmuz oranının yuvarlanması (0,67 → **0,66**) vardır.

## v2.html — kullanım

| Tuş | İşlev |
|---|---|
| `→` `Space` `PageDown` | Sonraki slayt |
| `←` `PageUp` | Önceki slayt |
| `Home` / `End` | İlk / son slayt |
| **`N`** | **Konuşma metnini aç/kapat** — o slaytta ne söyleneceği ve hangi sayının vurgulanacağı |
| **`O`** | **Slayt haritası** — 15 slaytın listesi, tıklayınca o slayta gider |

> `N` ve `O` ekranda **hiçbir ipucu göstermez** — jüri ekranı temiz kalsın diye
> rozetler kaldırıldı. Tuşlar çalışmaya devam eder; prova sırasında kullanın.
| `Esc` | Açık paneli / pop-up'ı kapat |
| `F11` | Tam ekran |

### İnteraktif pop-up'lar — 26 adet

Slaytların çoğunda kartlar ve grafikler tıklanabilir; her biri o kavramı önce tek
cümlelik bir **tanımla** açan, sonra ölçülmüş veriyle detaylandıran bir pop-up açar.
Başlıkta `grafiklere tıklayın` gibi bir rozet varsa o slaytta tıklanabilir öğe vardır.

| Slayt | Tıklanabilir | Pop-up'ta ne var |
|---|---|---|
| 3 · Problem | 3 sayaç + 9 madde | Ağ yapısı, dört kısıt, beş serbestlik — harita ve tablolarla |
| 5 · Veri | 5 kart | 179 günlük hacim (çizgi + rejim şeridi + takvim), veri eleme, veri setleri, **23 dışlanan tarihin her birinin gerekçesi**, metodoloji |
| 10 · Stage 2 | Arama + zincir dağılımı | Huninin neden önce genişlediği, kabul kuralı, kimlik kontrolü (1.092 − 626 + 227 = 693), gerçek bir milk-run zinciri |
| 11 · Stage 3 | Arama | Tier A'nın rotayı neden uzatmadığı, iki zaman damgası ayrımı, Tier B'nin neden dışarıda bırakıldığı |
| 12 · Filo | 3 grafiğin üçü de | Fiziksel araç ≠ segment, kümülatif doluluk eğrisi nasıl okunur, karma neden değişti / tır neden sabit |
| 13 · Hakem | 17 kural kartı | Hakem simülatörü nedir, neden yazıldı, beş kapı, yakaladığı üç hata |

### Detay — 3. ve 5. slayt

3. slaytta ("Ne çözüyoruz") **üç sayaç kartı ve on madde**, 5. slaytta ("Veri") **beş kart**
tıklanabilir; her biri o
kavramı ölçülmüş veriyle açan bir pop-up açar. Pop-up dışına tıklamak, `Esc` ya da
sağ üstteki `✕` kapatır — kapanırken slayt değişmez. Pop-up açıkken ok tuşları ve
`N` / `O` panelleri kilitlidir, yani sunum sırasında yanlışlıkla ilerlenmez.

| Tıklanan | Pop-up'ta ne var |
|---|---|
| **18** transfer merkezi | Türkiye haritası; nokta büyüklüğü elleçleme kapasitesi, kırmızı halka tır kotası sıfır olan 7 merkez |
| **306** yönlü hat | 306 hat animasyonla çizilir, SLA 1 gün (yeşil) / 2 gün (turuncu) ayrımıyla |
| **289** hat | 289 hat soluk, hiç talep görülmemiş 17 hat kırmızı — hepsinin Kocaeli varışlı olduğu görülür |
| Kısıt maddeleri (4) | Elleçleme kapasitesi (18 merkezin bar dağılımı), tır kotası, 12 kiralık rota tablosu, SLA'nın mesafe eşiği |
| Serbestlik maddeleri (5) | Sefer/doluluk sayıları, **nihai plandan gerçek bir milk-run zinciri** (V0225: Mersin → Şanlıurfa → Mardin → Erzincan → Sivas, harita üzerinde animasyonlu), karışık yükleme, dakika çözünürlüğü, SLA maliyet takası |

5. slayttaki beş kart:

| Tıklanan | Pop-up'ta ne var |
|---|---|
| Günlük desi grafiği | **179 günlük takvim ısı haritası** — ay sonu (turuncu) ve resmî tatiller (sarı) tek bakışta |
| Veri işleme ve eleme | Izgara (grid) kavramı, 103.462 hücrenin nasıl 90.168'e indiği, ne yapılmadığı |
| **179** gün geçmiş veri | 8 veri setinin tablosu — hangisi girdi, hangisi bizim çıktımız |
| **23** dışlanan tarih | 23 tarihin **tamamı adıyla**, her birinin normal güne oranı animasyonlu barlarla |
| Kritik nokta | Sızıntı tanımı, yapılan/yapılmayan ön işleme adımları ve gerekçeleri |

Her pop-up, kavramın **kısa tanımıyla** başlar (SLA nedir, elleçleme nedir, milk-run
nedir, ızgara nedir, sızıntı nedir…) — jüri terimi sormadan önce cevaplanmış olur.
Pop-up'lardaki tüm sayılar `kaynak/net_data.json` ve `kaynak/deck_data.json` üzerinden
ölçülmüş veriden gelir.

### Animasyonlu anlatımlar

| Nerede | Ne anlatıyor |
|---|---|
| 4. slayt — maliyet akışı | Nihai planımızdan **gerçek bir sefer** (V0187, tam dolu kamyon, Yalova → Balıkesir) zaman ekseninde canlanır: 17:00 talep hazır → 120 dk elleçleme → 178 dk yolculuk → 120 dk elleçleme → 23:58 teslim. Kullanım süresinin **tek sürekli pencere** olduğu görsel olarak kanıtlanır; alttaki maliyet satırı plandaki 6.564,14 ₺ ile kuruşu kuruşuna aynıdır. |
| 3. slayt — 18 / 306 / 289 | Türkiye haritası üzerinde merkezler, hatlar ve talep görülmeyen 17 hat sırayla çizilir |
| 3. slayt — milk-run | Gerçek bir uğramalı zincir (V0225) harita üzerinde döngüsel olarak dolaşır |
| 3. slayt — dakika çözünürlüğü | Planımızdaki 1.064 seferin saat ve dakika dağılımı — gece 129 sefer, 60 dakika değerinin 60'ı da dolu |
| 5. slayt — takvim / dışlanan tarih | Isı haritası ve 23 tarihin barları sırayla belirir |

Slaydın **dışındaki** alana tıklamak sayfayı çevirir — sol yarısı geri, sağ yarısı
ileri. Slaydın içine tıklamak sayfayı değiştirmez, böylece anlatırken içeriği
gösterirken yanlışlıkla ilerlenmez (3. slayttaki pop-up tetikleyicileri bunun
istisnasıdır). Ekranın **sol ve sağ ortasında** birer gezinme oku vardır: fare hareket
edince belirir, iki saniye hareketsizlikte kaybolur; ilk ve son slaytta ilgili ok
gizlenir. Sağ alttaki sayaç o an kaçıncı slaytta olduğunuzu gösterir.

Hepsiburada logosu kapak slaydında başlığın üstünde, kalan on dört slaytta ise sağ üst
köşede küçük bir işaret olarak durur (`kaynak/foto/hepsiburada.png`, derlemede gömülür).

Tarayıcının **Yazdır** menüsünden PDF alınabilir (her slayt ayrı sayfa olur).

Adres çubuğundaki `#7` gibi bir çapa doğrudan o slayta açar; prova sırasında
tek bir slayta hızlı dönmek için kullanışlıdır.

## Grafikler

Sunumdaki 15 grafiğin tamamı **ölçülmüş gerçek veriden** üretilir; hiçbiri elle
çizilmiş veya temsilî değildir. Kaynak:
`../stage-2-step-3/docs/figures/chart_data.json` → `kaynak/deck_data.json`.

Maliyet merdiveni · 179 günlük geçmiş hacim (ay sonu işaretli) · veri eleme ·
takvim çarpanları · tahmin vs haftagünü ortalaması ·
milk-run arama hunisi · zincir dağılımı · yük alma hunisi ve durak şeması ·
filo sayısı · doluluk kümülatif dağılımı · araç türü karması · 17 hakem kuralı ·
maliyet akış şeması.

## Yeniden üretme

```bash
# Ağ verisini şartname Excel'lerinden yeniden üret (kaynak/net_data.json)
python kaynak/build_net.py

# Sunumu yeniden derle (şablon + veri + fotoğraflar -> v2.html) ve headless doğrula
python kaynak/build_deck.py

# Bir markdown dökümanını Word'e çevir
python kaynak/md2docx.py dokumanlar/md/<dosya>.md "dokumanlar/<Ad>.docx" "Alt başlık"
```

`build_deck.py`, derlemeden sonra 15 grafiği ve 12 pop-up gövdesini Node ile başsız
(headless) çalıştırıp çıktıda `NaN` / `undefined` olup olmadığını, her slaytın konuşma
metninin dolu olup olmadığını, tanımsız grafik ya da pop-up referansı bulunup
bulunmadığını ve ağ verisinin 18 / 306 / 289 sayılarını tutturup tutturmadığını denetler.

`kaynak/` içindekiler: `v2_template.html` (şablon), `deck_data.json` (grafik verisi),
`net_data.json` (ağ verisi — `build_net.py` üretir), `foto/` (takım fotoğrafları,
derlemede base64 olarak gömülür).

## Word dökümanları

`.docx` dosyaları kapak sayfası, otomatik içindekiler tablosu, üstbilgi/altbilgi ve
sayfa numarası içerir. Word'de ilk açılışta içindekiler tablosu kendini günceller;
güncellemezse tabloya sağ tıklayıp **Alanı Güncelleştir** deyin (veya `Ctrl+A`, `F9`).


---

## Bu turda değişenler

| Ne | Değişiklik |
|---|---|
| **Animasyon** | 6. slayttan sonrası da canlı: her slayta girişte kartlar, liste satırları, tablo satırları ve çipler sırayla belirir; grafikler `replay()` ile yeniden kurulduğu için SVG animasyonları her dönüşte baştan çalışır. |
| **4 · Maliyet modeli** | Yeniden kurgulandı. Üstte renk kodlu **formül kartı** (üç terim + toplam), altında yalnız *kullanım süresi*ni anlatan temiz zaman ekseni. Formül ile eksen aynı renkleri kullanır. |
| **5 · Geçmiş veri pop-up'ı** | Takvim ısı haritası tek anlatım olmaktan çıktı. Artık önce **179 günlük çizgi grafiği** (rejim şeridi + medyan çizgisi + ay sonu işaretleri), sonra **rejim karşılaştırması** (normal / tatil / ay sonu −1 / ay sonu), en sonda takvim düzeni. |
| **5 · Dışlanan tarihler** | "15 + 10 ama 23 tarih" karışıklığı giderildi: **15 + 10 − 2 = 23** aritmetiği grafiğin başlığında yazılı, çakışan iki tarih (30–31 Mayıs) mor işaretli, ve her satırda **neden dışlandığı** yazıyor. |
| **11 · Stage 2** | Huninin her satırına ne olduğu yazıldı; kimlik kontrolü (1.092 − 626 + 227 = 693) slayta çıktı; iki grafik tıklanabilir. |
| **12 · Stage 3** | Durak şeması animasyonlu (rota çizilir, duraklar sırayla belirir, yük alma yayı en son çizilir); arama kartı tıklanabilir. |
| **13 · Filo** | Üç grafiğin üçü de tıklanabilir; her biri "bu grafik neyi ifade ediyor" sorusunu cevaplayan bir pop-up açar. |
| **14 · Hakem** | Slayta "neden ikinci bir uygulama" kutusu eklendi; pop-up nedir / neden / ne yakaladı sorularını beş kapı ve üç somut hatayla cevaplıyor. |
| **15 · Final uyumu** | Slaytın başına "Final Backtest nedir" kutusu eklendi; tablo satır satır beliriyor; pop-up 11 bölümü ve Bölüm 10'un iki güvenliğini açıyor. |
| **16 · Bölüm 7** | Başına "Bölüm 7 ne istiyor" kutusu eklendi; tablo animasyonlu; pop-up sentetik girdi üretecini ve %250 senaryosunu açıyor. |
| **17 · Çıkmaz sokaklar** | Altı satır sırayla beliriyor. |
| **18 · Kapanış** | "Sırada ne var" ve "bu çözümü ayıran üç şey" kaldırıldı (diğer takımlar hakkındaki ifade dâhil). Yerine **özet**: çözümün yapısı, ölçülen sonuç tablosu, doğrulama rozetleri. |
| **19 · Sorularınız** | Yeni kapanış slaydı — soru-cevap boyunca ekranda kalır. |
