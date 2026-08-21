# Sunum materyalleri

TEKNOFEST 2026 · Hepsiburada · Takım Büke · Final aşaması jüri sunumu.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| [`v2.html`](v2.html) | **Ana sunum.** 17 slayt, 15 gömülü SVG grafik. Tek dosya, dış bağımlılık yok — çift tıklayıp tarayıcıda açın. |
| [`index.html`](index.html) | Anahat sevkiyat panosu (önceki aşamadan, interaktif veri panosu). |
| `dokumanlar/` | Jüri için hazırlanan Word dökümanları (`.docx`) ve markdown kaynakları. |
| `kaynak/` | Sunumu ve dökümanları yeniden üreten betikler. |

## Word dökümanları — ne hangisinde

| Belge | Ne işe yarar | Uzunluk |
|---|---|---:|
| **00 — Sunum Konuşma Notları** | `v2.html`'deki 17 slayttan otomatik üretildi, birebir senkron. Süre planı (toplam 15:15), "süre aşarsak" atlama önceliği, ezberlenecek 10 sayı, slayt slayt metin, 10 dakikalık hazırlık listesi. | ~3.400 kelime |
| **01 — Algoritma ve Teknik Rapor** | Uçtan uca teknik anlatım: maliyet modeli ve zaman aritmetiği, veri katmanı, tahmin modeli, Stage 0–3 optimizasyon merdiveni, hakem simülatörü, final entegrasyon katmanı, ölçülmüş sonuçlar, ölçülmüş çıkmaz sokaklar, bilinen sınırlar. | ~12.800 kelime · 26 tablo |
| **02 — Jüri Soru-Cevap Hazırlık Kitabı** | **96 soru**, dokuz kategoride (problem/maliyet, tahmin, Stage 0, Stage 1-2-3, doğrulama, kural uyumu, final backtest gereksinimleri, zor sorular, karşılama taktikleri). Her soru için kısa cevap + detay + kanıt + tuzak notu. | ~12.400 kelime |
| **03 — Teknik Gereksinim Uyum Matrisi** | Final Backtest dokümanının Bölüm 1–11'i madde madde: jüri ne istedi → biz ne yaptık → kanıt → risk. Bölüm 11 kontrol listesi, şartname uyumu, jüri Q&A eşlemesi, çıktı şema tuzakları, genelleştirilebilirlik kanıtı. | ~11.400 kelime · 21 tablo |
| **04 — Sunum Akışı ve Konuşma Metni** | 21 slaytlık genişletilmiş akış: slaytta ne var, konuşma metni, vurgu sayıları, olası ara soru. Demo senaryosu ve hazırlık listesi dahil. | ~6.900 kelime |

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
| **`O`** | **Slayt haritası** — 17 slaytın listesi, tıklayınca o slayta gider |
| `Esc` | Açık paneli kapat |
| `F11` | Tam ekran |

Ekranın solundaki %28'lik alana tıklamak geri, kalanına tıklamak ileri gider —
uzaktan kumanda/klikır olmadan da sunulabilir.

Tarayıcının **Yazdır** menüsünden PDF alınabilir (her slayt ayrı sayfa olur).

Adres çubuğundaki `#7` gibi bir çapa doğrudan o slayta açar; prova sırasında
tek bir slayta hızlı dönmek için kullanışlıdır.

## Grafikler

Sunumdaki 15 grafiğin tamamı **ölçülmüş gerçek veriden** üretilir; hiçbiri elle
çizilmiş veya temsilî değildir. Kaynak:
`../stage-2-step-3/docs/figures/chart_data.json` → `kaynak/deck_data.json`.

Maliyet merdiveni · 179 günlük geçmiş hacim (ay sonu işaretli) · veri eleme ·
takvim çarpanları · tahmin vs haftagünü ortalaması · frozen backtest WMAPE ·
milk-run arama hunisi · zincir dağılımı · yük alma hunisi ve durak şeması ·
filo sayısı · doluluk kümülatif dağılımı · araç türü karması · 17 hakem kuralı ·
maliyet akış şeması.

## Yeniden üretme

```bash
# Sunumu yeniden derle (şablon + veri -> v2.html) ve grafikleri headless doğrula
python kaynak/build_deck.py

# Bir markdown dökümanını Word'e çevir
python kaynak/md2docx.py dokumanlar/md/<dosya>.md "dokumanlar/<Ad>.docx" "Alt başlık"
```

`build_deck.py`, derlemeden sonra 15 grafiği Node ile başsız (headless) çalıştırıp
çıktıda `NaN` / `undefined` olup olmadığını, her slaytın konuşma metninin dolu olup
olmadığını ve tanımsız grafik referansı bulunup bulunmadığını denetler.

## Word dökümanları

`.docx` dosyaları kapak sayfası, otomatik içindekiler tablosu, üstbilgi/altbilgi ve
sayfa numarası içerir. Word'de ilk açılışta içindekiler tablosu kendini günceller;
güncellemezse tabloya sağ tıklayıp **Alanı Güncelleştir** deyin (veya `Ctrl+A`, `F9`).
