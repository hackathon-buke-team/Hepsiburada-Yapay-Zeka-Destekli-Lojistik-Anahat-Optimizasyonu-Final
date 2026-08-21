# Sunum materyalleri

TEKNOFEST 2026 · Hepsiburada · Takım Büke · Final aşaması jüri sunumu.

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| [`v2.html`](v2.html) | **Ana sunum.** 17 slayt, 15 gömülü SVG grafik. Tek dosya, dış bağımlılık yok — çift tıklayıp tarayıcıda açın. |
| [`index.html`](index.html) | Anahat sevkiyat panosu (önceki aşamadan, interaktif veri panosu). |
| `dokumanlar/` | Jüri için hazırlanan Word dökümanları (`.docx`) ve markdown kaynakları. |
| `kaynak/` | Sunumu ve dökümanları yeniden üreten betikler. |

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
