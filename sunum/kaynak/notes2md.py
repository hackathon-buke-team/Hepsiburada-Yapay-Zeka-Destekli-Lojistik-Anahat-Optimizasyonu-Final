#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sunum/v2.html slaytlarından konuşma metni markdown'ı üretir (birebir senkron)."""
import io, json, math, pathlib, re

SP = pathlib.Path(r"C:/Users/darkb/AppData/Local/Temp/claude/C--Users-darkb-Desktop-hb-final/e7189315-fed6-416f-988d-d776129e0973/scratchpad")
OUT = pathlib.Path(r"C:/Users/darkb/Desktop/hb-final/sunum/dokumanlar/md/00-sunum-konusma-notlari.md")

slides = json.loads((SP / "notes.json").read_text(encoding="utf-8"))

# konuşma hızı ~135 kelime/dk (Türkçe, sunum temposu)
WPM = 135.0


def strip_html(s: str) -> str:
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def secs(text: str) -> int:
    return int(round(len(text.split()) / WPM * 60))


total = sum(secs(s["notes"]) for s in slides)

L = []
w = L.append
w("# Sunum Konuşma Notları")
w("")
w("Bu belge `sunum/v2.html` dosyasındaki 17 slayttan **otomatik olarak** üretilmiştir; "
  "sunumdaki her slaytın konuşma metni ve kullanım notu birebir aynıdır. "
  "Sunum sırasında **N** tuşuyla aynı metni ekranda da görebilirsiniz, **O** tuşu slayt haritasını açar.")
w("")
w("---")
w("")
w("## Slayt haritası ve süre planı")
w("")
w("| # | Slayt | Hedef süre | Kümülatif |")
w("|---|---|---:|---:|")
acc = 0
for s in slides:
    t = secs(s["notes"])
    acc += t
    w(f"| {s['n']} | {s['title']} | {t} sn | {acc // 60}:{acc % 60:02d} |")
w("")
w(f"**Toplam konuşma süresi:** yaklaşık **{total // 60} dakika {total % 60} saniye** "
  f"(dakikada {int(WPM)} kelime temposuyla). Slayt geçişleri ve nefes payıyla birlikte "
  f"**{math.ceil((total * 1.18) / 60)} dakika** planlayın. 15 dakikalık bir slot için "
  "aşağıdaki “süre aşarsak” önceliğini kullanın.")
w("")
w("---")
w("")
w("## Süre aşarsak — atlama önceliği")
w("")
w("Sırayla feda edin; her adım yaklaşık kaç saniye kazandırdığı yanında yazıyor.")
w("")
w("1. **Slayt 16 — Ölçülmüş çıkmaz sokaklar.** Ekranda gösterin, okumayın. "
  "“Altı fikri ölçtük ve reddettik, detayı raporda var” deyip geçin. (~60 sn)")
w("2. **Slayt 9 — Stage 1.** En basit aşama; “aynı hatta ikinci aracı sildik, 1,8 milyon” "
  "tek cümlesiyle özetlenebilir. (~45 sn)")
w("3. **Slayt 15 — Genelleştirilebilirlik.** Tabloyu gösterip “üç farklı hafta ve hacimde "
  "sıfır ihlal” demek yeter. (~50 sn)")
w("4. **Slayt 3 — Maliyet modeli.** Sadece alttaki formül satırını okuyun. (~40 sn)")
w("")
w("**Asla atlanmayacak slaytlar:** 7 (maliyet merdiveni), 10 (milk-run), 13 (hakem simülatörü), "
  "14 (final backtest uyumu). Bu dördü çözümün savunmasının tamamıdır.")
w("")
w("---")
w("")
w("## Ezberlenecek sayılar")
w("")
w("| Sayı | Ne | Nerede söylenecek |")
w("|---|---|---|")
w("| **11.232.476,73 ₺** | Yayınlanan planın toplam maliyeti | Slayt 1, 11, 17 |")
w("| **−%31,84** | Temel plana göre iyileşme | Slayt 1, 7, 17 |")
w("| **0** | Hakem ihlali — her aşamada | Slayt 1, 7, 13, 17 |")
w("| **1.269 → 665** | Fiziksel araç sayısı | Slayt 1, 12 |")
w("| **%48,02 → %79,03** | Ortalama spot araç doluluğu | Slayt 1, 12 |")
w("| **×0,0198** | Ayın son günü takvim çarpanı | Slayt 5 |")
w("| **0,5328 → 0,4464** | Ay sonu haftası WMAPE (DOW medyanı → bizim model) | Slayt 6 |")
w("| **227 zincir / 96.369 kombinasyon** | Stage 2 arama ve kabul | Slayt 10 |")
w("| **~150 sn / 100 dk** | Çalışma süremiz ve tavan | Slayt 14 |")
w("| **592/592** | Regresyon testi | Slayt 13, 17 |")
w("")
w("---")
w("")
w("## Slayt slayt konuşma metni")
w("")

for s in slides:
    t = secs(s["notes"])
    w(f"### Slayt {s['n']} — {s['title']}  (~{t} sn)")
    w("")
    w(f"**Kullanım notu:** {strip_html(s['use'])}")
    w("")
    w("**Konuşma metni:**")
    w("")
    for para in [p.strip() for p in s["notes"].split("\n") if p.strip()]:
        w(para)
        w("")
    w("---")
    w("")

w("## Sunum öncesi 10 dakikalık hazırlık listesi")
w("")
w("1. `sunum/v2.html` dosyasını tarayıcıda açın, **F11** ile tam ekran yapın.")
w("2. **O** tuşuyla slayt haritasını açıp kapatın — akışın aklınızda olduğundan emin olun.")
w("3. Slayt 7 (maliyet merdiveni) ve slayt 10 (milk-run) üzerinde birer kez prova yapın; "
  "sunumun ağırlık merkezi bu ikisi.")
w("4. Yukarıdaki on sayıyı sesli tekrarlayın.")
w("5. Demo yapacaksanız terminali hazırlayın: `cd final-teslim && python main.py`. "
  "Referans veri setinde ~150 saniye sürer ve her aşamada maliyeti ekrana basar — "
  "sunum sırasında başlatıp konuşmaya devam edin, kapanışta çıktıyı gösterin.")
w("6. Yedek: internet veya projeksiyon sorunu olursa sunum tek bir HTML dosyasıdır, "
  "dış bağımlılığı yoktur; tarayıcının **yazdır** menüsünden PDF de alınabilir.")
w("")
w("## Soru-cevap taktikleri")
w("")
w("- **Bilmediğiniz bir soru gelirse:** “Bunu ölçmedik” demek, tahmin yürütmekten iyidir. "
  "Ardından ölçtüğünüz en yakın şeyi söyleyin.")
w("- **Sayı sorulursa** yuvarlayın ama kaynağını söyleyin: “yaklaşık 11,2 milyon; "
  "kesin değer hakem simülatörünün yeniden hesabından geliyor”.")
w("- **“Neden X yapmadınız?”** sorularının çoğunun cevabı slayt 16'dadır — "
  "“denedik, ölçtük, şu kadar kötüydü”.")
w("- **SLA cezası** sorusunu jüri sormadan siz açın (slayt 7). Savunmada kalmayın.")
w("- **Açık kalemlerinizi saklamayın:** tahmin bias'ı, Tier B, beş duraklı zincir. "
  "Bilinen sınırı söylemek, bilinmeyen sınırdan iyidir.")
w("")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L), encoding="utf-8")
print(f"yazıldı: {OUT}  ·  {len(' '.join(L).split())} kelime  ·  toplam konuşma {total//60}:{total%60:02d}")
