# Anahat Sevkiyat Panosu

TEKNOFEST 2026 · Hepsiburada · Takım Büke — nihai sevkiyat planının **harita tabanlı
interaktif kontrol panosu**.

Pano iki biçimde çalışır ve ikisi de aynı koddan üretilir:

| Biçim | Dosya | Nasıl açılır |
|---|---|---|
| **Masaüstü** | `dist-exe/Anahat-Sevkiyat-Panosu.exe` | Çift tıklayın. Kurulum, internet ve tarayıcı ayarı gerekmez (~15 MB). |
| **Web** | `dist/` | Herhangi bir statik sunucuda ya da Vercel'de yayımlanır. |

Panoda dış harita servisi, CDN, font sunucusu ya da API çağrısı **yoktur** — Türkiye
haritası, tüm grafikler ve veri tek bir pakete gömülüdür.

---

## Panoda ne var

| Görünüm | Ne gösterir |
|---|---|
| **Özet** | Nihai planın tamamı tek ekranda: maliyet merdiveni (Stage 0→3), gün gün plan, araç türü karması, doluluk dağılımı. |
| **Harita** | Ana görünüm. 18 transfer merkezi ve planın 1.064 bacağı; dört karar katmanı ayrı ayrı açılıp kapanır: <br>· **kiralık rotalar** — zorunlu 12 rota, değiştiremediğimiz taban<br>· **spot atamalar** — tek bacaklı seferler<br>· **konsolidasyon zincirleri** — 2–4 duraklı milk-run<br>· **yol üstü yük alma** — ara durakta yük alan zincirler |
| **Filo** | 665 fiziksel aracın tamamı: arama, sıralama, doluluk ölçeri; seçilen aracın rotası harita ve durak durak zaman çizelgesi olarak açılır. |
| **Kısıt** | Elleçleme kotası ve tır ziyaret kotasının merkez-gün ısı haritaları — "0 ihlal" iddiasının görsel kanıtı. |
| **Talep** | 179 günlük geçmiş (takvim ısı haritası + çizgi), 23 dışlanan tarihin gerekçeleri, ölçülmüş takvim çarpanları, dondurulmuş geri-test, 7 günlük tahminimiz. |
| **Model** | Uçtan uca boru hattı: ham talep → tahmin → Stage 0-3 → hakem simülatörü → Excel çıktısı. Her kutu tıklanabilir. |

### Haritayı kullanma

- **Merkeze tıklayın** — yalnız oraya değen bacaklar kalır, merkezin günlük kota kullanımı açılır.
- **Rotaya tıklayın** — o aracın tüm zinciri, durak durak yük dökümüyle açılır.
- **Zaman kipi** — plan dakika dakika oynatılır; hareket eden her jeton o anda gerçekten yolda olan bir araçtır. Hız ×2 – ×40.
- Tekerlekle yakınlaştırın, sürükleyerek kaydırın; `1`–`6` tuşları görünümler arasında geçer.

---

## Veri

Panodaki **her sayı** teslim ettiğimiz çıktılardan ve şartnamenin veri setlerinden
üretilir; elle yazılmış tek bir değer yoktur.

```bash
python kaynak/build_panel_data.py     # -> src/data/panel.json
```

Betik şu kaynakları okur:

| Kaynak | Ne verir |
|---|---|
| `stage-2-step-3/out/Tasima-plani.xlsx` | Nihai plan — 5.523 satır, 1.064 bacak, 665 araç |
| `stage-2-step-3/out/Talep-tahmini.xlsx` | 7 günlük talep tahminimiz — 4.046 satır |
| `stage-2-step-3/datas/*.xlsx` | Şartname verisi: mesafe/SLA matrisi, elleçleme ve tır kapasiteleri, kiralık rotalar, araç maliyetleri, 179 günlük geçmiş |
| `sunum/kaynak/deck_data.json` | Stage 0–3 aşama ölçümleri |

Betik sonunda tutarlılık kapılarından geçer — 18 merkez, 306 hat, 289'unda talep,
7 merkezde tır kotası sıfır, 12 kiralık rota / 14 araç, ve toplam maliyetin aşama
verisiyle **kuruşu kuruşuna** eşleşmesi. Bunlardan biri tutmazsa betik hata verir.

---

## Derleme

```bash
npm install

npm run dev          # geliştirme sunucusu
npm run build        # -> dist/       (web, Vercel)
npm run build:tek    # -> dist-tek/   (tek dosyalık HTML, .exe içine gömülür)
npm run build:exe    # -> dist-exe/Anahat-Sevkiyat-Panosu.exe
```

`build:exe`, önce `build:tek` çalıştırılmış olmasını bekler.

### Yayımlama

```bash
npx vercel --prod        # panel/ klasöründe; vercel.json hazır
```

---

## Teknoloji

| Katman | Seçim | Neden |
|---|---|---|
| Arayüz | React 18 + TypeScript + Vite | Tip güvenliği; `strict` + `noUnusedLocals` açık |
| Grafikler | Elle yazılmış SVG (`src/lib/charts.tsx`) | Grafik kütüphanesi yok — tam kontrol, çevrimdışı çalışma, tek tipografi |
| Harita | Elle yazılmış izdüşüm (`src/lib/geo.ts`) | Eş dikdörtgen izdüşüm, 39° enleminde boylam düzeltmesi. GeoJSON dosyası, tile sunucusu ya da harita kütüphanesi yok |
| Stil | Tek `styles.css`, CSS değişkenli tasarım belirteçleri | CSS çerçevesi yok |
| Masaüstü | pywebview + PyInstaller | Windows'un yerleşik WebView2 motorunu kullanır; Electron'un ~150 MB'ı yerine ~15 MB |

Toplam çalışma zamanı bağımlılığı: `react` ve `react-dom`.

---

## Klasörler

```
panel/
├── kaynak/build_panel_data.py    veri üreteci (tek gerçeğin kaynağı)
├── src/
│   ├── data/panel.json           üretilen veri
│   ├── lib/                      fmt · geo · ui · charts
│   ├── views/                    Overview · MapView · Fleet · Constraints · Demand · Pipeline
│   ├── store.ts                  veri erişimi ve süzgeç
│   ├── types.ts                  panel.json şeması
│   └── styles.css                tasarım dili
├── desktop/                      pywebview kabuğu + .exe derleyici
└── vercel.json
```
