# Teslim Öncesi Kontrol Listesi (Bölüm 11)

*Final Backtest — Teknik Gereksinimler* dokümanının 11. bölümündeki liste,
madde madde ve nasıl doğrulandığıyla birlikte.

| ✔ | Madde | Doğrulama |
|---|---|---|
| ✅ | `main.py` kök dizinde ve argümansız çalışıyor | `python main.py` → çıkış kodu 0, ~150 sn (temiz sanal ortamda da doğrulandı) |
| ✅ | `main.py` sadece optimizasyon adımını çalıştırıyor (tahmin modülü çağrılmıyor) | `main.py`'nin import grafiği taranarak `src.forecast`, `src.backtest`, `src.frozen_backtest` modüllerine **hiçbir yoldan ulaşılamadığı** doğrulandı |
| ✅ | Girdi, Bölüm 4'teki format/şema/erişim yöntemleriyle okunabiliyor | Her iki yöntem de destekleniyor ve testlerle kapsanıyor: `TEKNOFEST_INPUT_FILE` (öncelikli) ve `data/one_week_backtest.xlsx` (yedek) |
| ✅ | Çıktı, Bölüm 5'teki format/şema/konumla yazılıyor | `out/Tasima-plani.xlsx`, tek sayfa, 16 kolon ad ve sıra birebir; yazımdan sonra diskten geri okunup şema yeniden doğrulanıyor, ardından atomik `os.replace` yapılıyor |
| ✅ | Kod, sabit tarih/hacim varsayımı içermiyor (Bölüm 7) — farklı bir hafta/hacimle test edildi | Ufuk `Tarih` kolonundan türetiliyor. Test edilenler: 25–28.05.2025 (farklı yıl, 4 günlük ufuk, %35 hacim, `REQ_` kimlikler, `HH:MM`) ve 02–08.09.2026 (%125 hacim, `HH:MM:SS`) — her ikisinde de çıkış kodu 0 ve 0 hakem ihlali |
| ✅ | `requirements.txt` güncel ve eksiksiz | `pandas>=2.0,<3.0`, `openpyxl>=3.1,<4.0` — başka çalışma zamanı bağımlılığı yok |
| ✅ | `teknofest_manifest.json` dolduruldu ve kök dizine eklendi | ⚠️ **`takim_id` alanına başvuru numaranızı yazın** (bkz. aşağıdaki not) |
| ✅ | Çalışma anında internet erişimi veya kullanıcı etkileşimi gerektiren kod yok | Statik tarama: `input()`, `urllib`, `requests`, `socket`, `subprocess`, `pip install`, `tkinter`, `get_ipython`, `google.colab` — hiçbiri yok |
| ✅ | Değişiklikler sadece entegrasyon amaçlı, algoritma/model/çözüm mantığına dokunmuyor (Bölüm 8) | Değişen dosya sayısı: **2** (`src/data.py`, `src/schemas.py` — ikisi de yalnızca davranış genişleten). Kanıt: aynı girdiyle üretilen çıktı, önceki teslimle **0 farklı hücre**. Ayrıntı: [`DEGISIKLIKLER.md`](DEGISIKLIKLER.md) |
| ✅ | `python main.py`, temiz bir sanal ortamda (sadece `requirements.txt`) baştan sona test edildi | `python -m venv` ile kurulan izole ortam (pandas 2.3.3 / numpy 2.4.6 / openpyxl 3.1.5): çıkış kodu 0, çıktı referans teslimle birebir aynı |

---

## ⚠️ Teslimden önce yapılması gereken tek işlem

`teknofest_manifest.json` içindeki `takim_id` alanı şu an yer tutucudur:

```json
"takim_id": "BASVURU_NUMARANIZI_YAZIN",
"takim_adi": "Büke",
```

Başvuru numaranızı yazın; `takim_adi` alanını da doğru yazıldığından emin
olmak için kontrol edin. Bu iki alan dışında paket teslime hazırdır.

---

## Ek doğrulamalar (dokümanda istenmiyor, kendi kontrolümüz)

| Kontrol | Sonuç |
|---|---|
| Regresyon testleri | 592/592 geçti (528 mevcut + 64 yeni entegrasyon testi) |
| Bağımsız hakem denetimi (`tools/verify_output.py`) | Çıktı diskten geri okunup yeniden fiyatlandırıldı: 0 ihlal, beyan/hakem farkı 0,0000 TL |
| Sert süre sınırı davranışı | `TEKNOFEST_TIME_BUDGET_MIN=0.6` ile Stage 2 terk edildi; geçerli plan yayınlandı, çıkış kodu 0 |
| Kademeli yayın | Stage 0 planı elde edilir edilmez diske yazılıyor; her kabul edilen aşama atomik olarak güncelliyor |
| Çalışma dizininden bağımsızlık | Farklı bir dizinden `python /mutlak/yol/main.py` çalıştırıldı: girdi, `datas/` ve `out/` yolları betiğe göre çözüldü, çıkış kodu 0 |
| Fizikî olarak çözümsüz veri seti (%250 hacim) | Çökme yok: Stage 0 planı üretilip yayınlandı; 69 elleçleme ihlalinin tamamı, o gün o merkezde talebin kapasiteyi aşmasından kaynaklanıyor (hiçbir planla sağlanamaz) |
| Zorla sonlandırma testi | Süreç Stage 2 ortasında öldürüldü; diskte 3.710 satırlık, şemaya birebir uyan geçerli bir plan kaldı |
