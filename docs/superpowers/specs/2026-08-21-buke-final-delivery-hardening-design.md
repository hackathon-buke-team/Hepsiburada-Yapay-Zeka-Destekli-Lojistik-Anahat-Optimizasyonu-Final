# Büke Final Teslim Sertleştirme Tasarımı

Tarih: 2026-08-21  
Durum: Kullanıcı tarafından bölüm bölüm onaylandı  
Takım ID: `997307`  
Takım adı: `Büke`

## 1. Amaç

Bu çalışmanın amacı mevcut optimizasyon algoritmasını yeniden tasarlamak veya iyileştirmek değil; tamamlanmış projeyi `TEKNIK_GEREKSINIMLER.pdf` içindeki final backtest sözleşmesine uygun, tekrarlanabilir ve jüriye sunulabilir bir teslim paketine dönüştürmektir.

Başarılı sonuç aşağıdaki üç çıktıdan oluşur:

1. Portalın 10 MB sınırına uyan `Buke_997307_Final_Teslim.zip`.
2. Optimizasyon öncelikli 14 ana slayt ve ayrı soru-cevap eklerinden oluşan jüri sunumu.
3. Kod, sunum ve doküman iddialarını aynı doğrulama kanıtlarına bağlayan güncel belgeler.

## 2. Değişmezler ve kapsam sınırı

"Sürpriz yok" ilkesi aşağıdaki değişmezlerle uygulanır:

- Araç karması, rota seçimi, Stage 0, aynı-hat onarımı, milk-run, pickup, maliyet ve SLA karar mantığı değiştirilmez.
- `candidates.py`, `optimize.py`, `repair.py`, `milkrun.py`, `pickup.py`, `schedule.py` ve maliyet/zaman kuralları davranışsal olarak aynı kalır.
- Kapsam; manifest, girdi/çıktı sözleşmesi, hata görünürlüğü, paketleme, uçtan uca test, sunum ve doküman üretilebilirliğiyle sınırlıdır.
- Kök dizindeki mevcut `Tasima-plani.xlsx` referans çıktı kabul edilir. Uygulama başında SHA-256 değeri kaydedilir.
- Referans veriyle yeni çıktının 5.523 satır, 16 kolon, 0 ihlal, 11.232.476,73 TL ve 0 hücre farkı sonuçlarını koruması zorunludur.
- Bu değişmezlerden biri bozulursa final ZIP oluşturulmaz.

## 3. Nihai teslim paketi

Nihai dosya yolu:

`C:\Users\darkb\Desktop\hb-final\Buke_997307_Final_Teslim.zip`

ZIP açıldığında arşiv kökü doğrudan çalıştırma kökü olur:

```text
main.py
teknofest_manifest.json
requirements.txt
README.md
DEGISIKLIKLER.md
src/
datas/
data/
  one_week_backtest.xlsx
```

Arşivde `final-teslim/` üst klasörü bulunmaz. Aşağıdaki içerikler arşive alınmaz:

- `out/Tasima-plani.xlsx` veya başka bir önceden üretilmiş çıktı
- `tests/`, `tools/`, `run.py` ve geliştirme yardımcıları
- sunum ve jüri dokümanları
- `__pycache__`, `.pytest_cache`, sanal ortam, log ve geçici dosyalar
- placeholder veya makineye özgü mutlak yol içeren dosyalar

Arşiv boyutu portal sınırında yorum farkı oluşmaması için 10.000.000 bayttan küçük olmalıdır.

## 4. Manifest

Manifest geçerli UTF-8 JSON olur ve PDF'deki on alanı birebir içerir. Kimlik alanları:

```json
{
  "takim_id": "997307",
  "takim_adi": "Büke",
  "python_surumu": "3.11"
}
```

Diğer alanlar gerçek davranışla uyumlu olur:

- Kurulum: `python -m pip install -r requirements.txt`
- Çalıştırma: `python main.py`
- Birincil girdi: `TEKNOFEST_INPUT_FILE`
- Yedek girdi: `data/one_week_backtest.xlsx`
- Çıktı klasörü: `out/`
- Beklenen tek çıktı: `Tasima-plani.xlsx`

Paketleme komutu eksik/yer tutucu takım kimliğinde başarısız olur. Kontrol listesi, manifest gerçekten geçerli olmadıkça bu maddeyi tamamlanmış göstermez.

## 5. Girdi veri akışı

### 5.1 Yol seçimi

1. `TEKNOFEST_INPUT_FILE` tanımlıysa değer mutlak `.xlsx` dosya yolu olmalı ve dosya bulunmalıdır.
2. Ortam değişkeni tanımlı fakat yol hatalıysa yedek haftaya sessiz geçiş yapılmaz; program açık hata ve sıfırdan farklı kodla sonlanır.
3. Ortam değişkeni hiç tanımlı değilse `data/one_week_backtest.xlsx` kullanılır.

### 5.2 Excel sözleşmesi

Girdi:

- Tek sayfa içerir ve sayfa adı tam olarak `Sheet1` olur.
- Tam olarak altı kolon içerir; ad ve sıra PDF ile birebir aynı olur.
- Boş veya tekrarlı `Talep ID` içermez.
- Tarih, saat, transfer merkezi ve hat bilgileri geçerli olur.
- Desi sayısal, sonlu, negatif olmayan ve matematiksel olarak tam sayı olur.

Yanlış kolon adını pozisyona göre tahmin etme, geçersiz satırı atlama, negatif desiyi sıfıra çekme ve kesirli desiyi yuvarlama kaldırılır. Herhangi bir ihlal tüm dosyayı okunabilir hata mesajıyla reddeder.

PDF, desi tipini "sayı" olarak tanımlarken mevcut resmî algoritma tam sayı desi kullanır. Algoritma davranışını değiştirmemek için kesirli desi desteklenmez; sessiz yuvarlama yerine açık sözleşme hatası verilir. Bu karar README ve teknik uyum belgesinde açık risk olarak yazılır.

### 5.3 Talep kimlikleri

Optimizasyon içeride kanonik `D00001` biçimini kullanmaya devam eder. Çıktıda girdideki özgün kimlik geri yazılır. Tire içeren kimliklerde önce tam özgün kimlik eşleşmesi aranır; yalnız algoritmanın eklediği en sağdaki parça soneki ayrılır. Bu değişiklik rota veya maliyet kararına değil, yalnız entegrasyon kimlik eşlemesine uygulanır.

## 6. Çalıştırma, hata ve çıktı davranışı

- `main.py` başlarken kendi hedefindeki eski `out/Tasima-plani.xlsx` dosyasını kaldırır. Başarısız koşu eski dosyayı yeni sonuç gibi bırakamaz.
- Tahmin modülü import edilmez veya çalıştırılmaz.
- Zaman bütçesi ve geçerli önceki aşamaya dönme davranışı korunur; ancak fallback yalnız daha önce bağımsız simülasyonda sıfır ihlal aldığı kanıtlanmış plan için kullanılır.
- Normal aşama hataları kaydedilir. `KeyboardInterrupt`, `SystemExit` ve benzeri kritik süreç sinyalleri başarılı fallback gibi yutulmaz.
- Çıktı atomik olarak `out/Tasima-plani.xlsx` yoluna yazılır.
- Yazılan dosya tekrar açılır; tek sayfa, tam 16 kolon, hücre koruması, maliyet uzlaşması ve sıfır ihlal yeniden denetlenir.
- Program yalnız bu son kontrol geçerse `0` döndürür. Kontrol başarısızsa yeni çıktı kaldırılır ve sıfırdan farklı kod döner.

## 7. Sunum tasarımı

Ana sunum 15 dakikalık, 14 slaytlık optimizasyon anlatısı olur:

1. Ana iddia: 4,98M desi, 0 ihlal, 11,23M TL
2. Operasyon problemi ve bağlayıcı kısıtlar
3. Jürinin verdiği girdi ve final sözleşmesi
4. Maliyet modeli ve zaman aritmetiği
5. Stage 0 geçerli temel plan
6. Stage 1 aynı-hat onarımı
7. Stage 2 milk-run
8. Stage 3 rota-ortası pickup
9. Tek talebin girdiden nihai araca uçtan uca rota vakası
10. Düzeltilmiş maliyet merdiveni
11. Bağımsız hakem ve kanıt izi
12. Genelleştirilebilirlik: %35, %100 ve %125
13. Teknik uyum: ID 997307 ve temiz teslim paketi
14. Kapanış: ilk koşuda denetlenebilir plan

Tahmin/WMAPE, %250 fiziksel sınır, reddedilen fikirler, ayrıntılı 17 hakem kuralı ve teknik tablolar soru-cevap eklerine taşınır. Ana akış "Sırada ne var" açık iş listesiyle bitmez.

Görsel kurallar:

- Ana gövde yazısı en az 20 px olur.
- Her slaytta bir ana grafik ve en fazla üç kanıt sayısı kullanılır.
- Her KPI; kaynak dosya, test komutu/tarihi veya doğrulama etiketiyle izlenebilir olur.
- Mevcut slayt 4 taşması ve slayt 7 SVG kırpılması yeniden yerleşimle giderilir.
- "AI destekli" yerine "açıklanabilir karar zekâsı" kullanılır.
- "Enumeration optimum" ifadesi "sabit hat-gün yükü için koşullu yerel optimum" olarak daraltılır.
- Eski `sunum/index.html` ana sunum olarak kullanılmaz.

## 8. Doküman ve üretilebilirlik

- `v2_template.html` ve `deck_data.json` sunumun tek kaynak çifti olur.
- `build_deck.py`, `notes2md.py` ve `build_docs.py` yalnız repo-relative yollar kullanır.
- Claude geçici dizinlerine ve kullanıcı bilgisayarına sabitlenmiş yollar kaldırılır.
- Sunum notları, teknik rapor, soru-cevap kitabı, uyum matrisi ve genişletilmiş sunum aynı doğrulanmış metriklerden üretilir.
- Manifest, ZIP kökü, test sayısı, maliyet ve kapsam hakkındaki eski veya yanıltıcı beyanlar düzeltilir.
- DOCX dosyaları yeniden üretilir; tüm sayfalar PNG/PDF render ile taşma, kırpılma, tablo bölünmesi ve okunabilirlik açısından incelenir.

## 9. Doğrulama ve paketleme kapısı

Doğrulama sırası:

1. Referans dosyaların hash ve metriklerini kaydet.
2. Girdi sözleşmesi, env/fallback, tireli ID, kesirli desi reddi, eski çıktı temizliği ve final yayın davranışı için testleri ekle.
3. Tam pytest paketini önbelleksiz çalıştır.
4. Referans girdiyle `python main.py` koşusunu tamamla.
5. Çıktıyı bağımsız hakemle tekrar fiyatlandır ve sıfır ihlali doğrula.
6. Referans çıktıyla hücre hücre karşılaştır.
7. Sunumun 14 ana slaydını 1600x900 masaüstü viewport'ta render edip tek tek incele; konsol hatalarını kontrol et.
8. DOCX belgelerinin tüm sayfalarını render edip incele.
9. Allowlist ile geçici bir yayın kökü ve ZIP oluştur.
10. ZIP'i yeni geçici dizine aç; arşiv kökünden hem env hem fallback yöntemiyle gerçek `python main.py` koşusu yap.
11. ZIP içeriğini placeholder, mutlak yol, cache, eski çıktı, dosya adı ve boyut açısından denetle.
12. Nihai ZIP'in SHA-256 değerini raporla.

Herhangi bir kapı başarısızsa `Buke_997307_Final_Teslim.zip` final artefaktı olarak bırakılmaz.

## 10. Bağımlılıklar ve offline koşulu

`requirements.txt`, doğrulanan Python 3.11 ortamındaki pandas ve openpyxl sürümlerine sabitlenir. Program çalışma anında ağ çağrısı veya otomatik kurulum yapmaz.

Portalın 10 MB sınırı pandas wheel paketlerini teslim ZIP'ine koymayı pratik olarak engeller. Bu nedenle teslim, PDF'de tarif edilen `requirements.txt` kurulum modelini kullanır; değerlendirme ortamının bağımlılıkları kurulum aşamasında sağlayacağı varsayılır. Bu varsayım README'de açık yazılır.

## 11. Kabul kriterleri

Çalışma ancak aşağıdaki maddelerin tamamı sağlandığında tamamlanmış sayılır:

- Takım kimliği `997307`, takım adı `Büke`.
- ZIP 10.000.000 bayttan küçük ve kök yapısı doğru.
- ZIP'te eski çıktı, placeholder, cache veya makineye özgü yol yok.
- `python main.py` argümansız ve kullanıcı etkileşimsiz çalışıyor.
- Env ve fallback girdi yolları ayrı ayrı doğrulanmış.
- Çıktı `out/Tasima-plani.xlsx`, tek sayfa ve tam 16 kolon.
- Bağımsız hakem 0 ihlal ve beyan-hakem maliyet farkı 0 veriyor.
- Referans maliyet, satır sayısı ve hücreler değişmiyor.
- Tam test paketi geçiyor.
- 14 ana sunum slaydında görsel kusur ve yanlış uyum iddiası yok.
- DOCX belgeleri sayfa bazında görsel kontrolden geçiyor.
- Kullanıcıya yüklenmesi gereken tek dosyanın tıklanabilir yolu, boyutu ve SHA-256 değeri veriliyor.
