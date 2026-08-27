# Talep Tahmini — Teknik Rapor

TEKNOFEST 2026 · Hepsiburada · Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · Takım Büke

Bu belge yalnız **talep tahmini** tarafını anlatır: bizden tam olarak neyi tahmin etmemiz istendiğini, ham veriye uyguladığımız ön işleme (preprocessing) adımlarının tamamını, uygulamadığımız işlemleri ve **neden** uygulamadığımızı, kurduğumuz modelin matematiğini ve modelde kullandığımız her girdi ile her hiperparametreyi kapsar. Taşıma planı optimizasyonu bu belgenin konusu değildir; o taraf ayrı belgede anlatılmıştır.

Belgedeki her sayı ya teslim paketindeki bir dosyadan ya kaynak kodun ilgili satırından ya da yeniden üretilebilir bir ölçümden gelir. Teknik terimlerin Türkçesi kullanılmış, ilk geçtiği yerde İngilizcesi parantez içinde verilmiştir.

---

## 1. Bizden Ne Tahmin Etmemiz İsteniyor

### 1.1 Tek cümlede hedef

Gelecek bir haftalık ufukta, **her aktif transfer merkezi çifti için, her gün, iki talep tamamlanma saatinin her birinde oluşacak desi miktarını** tahmin etmemiz isteniyor.

### 1.2 Tahmin biriminin tanımı

Modelin tahmin ettiği en küçük birim bir **hücredir** ve bir hücre üç anahtarla tanımlanır:

| Anahtar | Anlamı | Değer kümesi |
|---|---|---|
| Tarih | Talebin oluştuğu gün | Ufuktaki 7 gün |
| OD çifti | Çıkış ve varış transfer merkezi | 289 aktif çift |
| Slot | Talep tamamlanma saati | 09:00 veya 17:00 |

Tahmin edilen büyüklük **desi** cinsindendir; hacimsel bir yük ölçüsüdür ve tam sayı olarak raporlanır. Yani problem bir sınıflandırma değil, **kesikli değerli bir regresyon (tahmin) problemidir**.

Bu üç anahtarın kartezyen çarpımı bir tahmin ufkunu tamamen doldurur:

```
289 OD çifti  x  7 gün  x  2 slot  =  4.046 hücre
```

Teslim edilen tahmin dosyası da tam olarak bu 4.046 satırdır.

### 1.3 Bu bir tek zaman serisi değil, 578 paralel zaman serisidir

Problemi "günlük toplam hacmi tahmin et" diye okumak yanlış olurdu. Her (OD, slot) ikilisi kendi başına bir zaman serisidir ve birbirinden bağımsız davranır:

```
289 OD çifti  x  2 slot  =  578 paralel zaman serisi
```

İki slotun ölçeği bile birbirinden çok farklıdır: ölçülen paylara göre **17:00 slotu toplam desinin %91,24'ünü**, 09:00 slotu ise yalnız **%8,76'sını** taşır. Bu yüzden tahmin, tek bir toplam seri üzerinden değil, 578 serinin her biri üzerinde ayrı ayrı yapılmalıdır.

### 1.4 Çıktı biçimi

Yarışma çıktı şablonunu birebir sabitlemiştir. Ürettiğimiz `Talep-tahmini.xlsx` dosyası tek sayfa ve altı kolondur:

| Kolon | İçerik |
|---|---|
| Talep ID | `D00001` biçiminde kanonik kimlik |
| Tarih | `GG.AA.YYYY` |
| Talep Tamamlama Saati | `09:00` veya `17:00` |
| Çıkış Transfer Merkezi | Merkez adı |
| Varış Transfer Merkezi | Merkez adı |
| Tahmin Edilen Desi | Tam sayı, negatif olamaz |

### 1.5 Başarı ölçütü: WMAPE

Değerlendirme ölçütü **WMAPE** (weighted mean absolute percentage error — hacim ağırlıklı mutlak yüzde hata):

```
WMAPE = toplam |gerçek - tahmin|  /  toplam gerçek
```

Bu ölçütün seçimi modelleme kararlarımızı doğrudan belirlemiştir. WMAPE hatayı **desi ağırlıklı** ölçer: 78.420 desilik bir hücrede yapılan %10 hata, 17 desilik bir hücrede yapılan %100 hatadan yüzlerce kat daha pahalıdır. Dolayısıyla model, küçük hücrelerde yüzde hatasını kovalamak yerine **büyük hacimleri doğru bilmeye** odaklanmalıdır. Bölüm 4'teki "neden aykırı değer temizlemedik" kararının arkasında da bu ölçüt vardır.

Ayrıca bir yan ölçüt olarak **yanlılığı (bias)** izliyoruz:

```
bias = toplam (tahmin - gerçek)  /  toplam gerçek
```

WMAPE hatanın büyüklüğünü, bias ise hatanın **yönünü** söyler. Sistematik olarak yukarı sapan bir tahmin, sonraki adımda gereksiz araç çıkarılmasına yol açacağı için ayrıca izlenmesi gerekir.

---

## 2. Elimizdeki Ham Veri

### 2.1 Kaynak dosya

Tahmin modelinin gördüğü tek geçmiş veri kaynağı `datas/teknofest26_gelismis.xlsx` dosyasıdır. Altı kolonu vardır: `tarih`, `cikis`, `varis`, `talep_id`, `toplam_desi`, `talep_tamamlanma_saati`.

| Özellik | Ölçülen değer |
|---|---|
| Satır sayısı | 66.024 |
| Tarih aralığı | 1 Ocak 2026 – 28 Haziran 2026 |
| Gün sayısı | 179 (kesintisiz) |
| Aktif OD çifti | 289 |
| Transfer merkezi | 18 (çıkış olarak 18, varış olarak 17) |
| Slot | 2 (`9:00` ve `17:00`) |
| Toplam desi | 145.763.108 |
| En küçük gözlem | 17 desi |
| En büyük gözlem | 78.420 desi |

### 2.2 Ölçülmüş veri kalitesi

Ön işleme kararlarını anlatmadan önce, verinin fiilen ne durumda olduğunu ölçtük. Aşağıdaki tablo, ham dosya üzerinde doğrudan çalıştırılan denetimlerin sonucudur:

| Denetim | Sonuç |
|---|---|
| Boş (null) hücre | 6 kolonun 6'sında da **0** |
| Tamamen tekrar eden satır | **0** |
| Tekrar eden `talep_id` | **0** (66.024 kimliğin 66.024'ü benzersiz) |
| Tekrar eden (tarih, çıkış, varış, slot) anahtarı | **0** |
| Negatif desi | **0** |
| Sıfır desi | **0** |
| Beklenmeyen slot değeri | **0** (yalnız iki değer var) |
| Tarih boşluğu | **0** (179 günün 179'u dolu) |
| Tip tutarsızlığı | `toplam_desi` kolonunun tamamı tam sayı |

Bu tablo, Bölüm 4'ün tamamının dayanağıdır. **Veriyi temizlemedik, çünkü ölçtüğümüzde temizlenecek bir şey bulamadık.** Bu bir varsayım değil, çalıştırılmış bir denetimin çıktısıdır.

### 2.3 Verinin tek gerçek zorluğu: seyreklik

Veride bozukluk yok; ama bir **seyreklik (sparsity)** özelliği var ve bu, atlanması hâlinde modeli sistematik olarak bozacak tek yapısal özelliktir.

```
Tam grid   = 289 OD  x  179 gün  x  2 slot  =  103.462 hücre
Ham veride görünen                          =   66.024 hücre  (%63,81)
Ham veride hiç görünmeyen                   =   37.438 hücre  (%36,19)
```

Yani olası hücrelerin **%36,19'u dosyada satır olarak hiç yok**. Bu satırların anlamı "veri eksik" değil, "o gün o hatta o slotta talep oluşmadı", yani **desi = 0** demektir. Ham dosyada en küçük gözlemin 17 desi ve sıfır gözlem sayısının 0 olması bunu doğrular: sıfırlar satır olarak yazılmamış, yokluk olarak ifade edilmiştir.

Bu ayrım tahmin için kritiktir ve Bölüm 3.5'te ele alınmıştır.

---

## 3. Ön İşleme (Preprocessing) — Yaptığımız Her Şey

Uyguladığımız işlemlerin tamamı yedi adımdır. Aşağıdaki tablo tam listedir; bu tabloda olmayan hiçbir dönüşüm veriye uygulanmamıştır.

| # | Adım | Ne yapıyor | Nerede |
|---|---|---|---|
| 1 | Dosya adı çözümü | Türkçe karakterli dosya adlarını Unicode biçiminden bağımsız bulur | `src/data.py` |
| 2 | Şema doğrulaması | Anahtar benzersizliği, sayısal geçerlilik, beklenen slot kümesi | `src/data.py` |
| 3 | Normalizasyon | `tarih` -> datetime, `9:00` -> `09:00`, `toplam_desi` -> int64 | `src/data.py` |
| 4 | Tam grid kurulumu | Kartezyen çarpım; görünmeyen hücreyi desi = 0 ile doldurur | `src/backtest.py` |
| 5 | Eğitim takvim filtresi | 23 özel tarihi **yalnız eğitim geçmişinden** dışlar | `src/backtest.py` |
| 6 | Kararlı sıralama | (tarih, çıkış, varış, slot) anahtarıyla deterministik sıra ve kimlik | `src/forecast.py` |
| 7 | Çıktı sanitizasyonu | Negatif kırpma, sonsuz/NaN koruması, tam sayıya yuvarlama | `src/forecast.py` |

### 3.1 Adım 1 — Dosya adı çözümü

Windows dosya sisteminde Türkçe karakterli adlar bazen ayrıştırılmış (NFD) biçimde saklanır; kodun aradığı ad ise birleşik (NFC) biçimdedir. Bu, "dosya orada olduğu hâlde bulunamıyor" hatasına yol açar. Yükleyici önce birebir adı dener, bulamazsa dizindeki tüm adları NFC'ye normalize ederek karşılaştırır. Bu bir veri dönüşümü değil, bir taşınabilirlik önlemidir; jürinin farklı bir makinede çalıştırması hâlinde sessiz başarısızlığı önler.

### 3.2 Adım 2 — Şema doğrulaması (fail-fast)

Veriyi düzeltmek yerine **doğrulamayı** seçtik. Yükleyici şu koşulların herhangi biri sağlanmazsa çalışmayı durdurur ve hangi satırların sorunlu olduğunu yazan bir hata fırlatır:

- `talep_id` benzersiz değilse
- (tarih, çıkış, varış, slot) anahtarı tekrar ediyorsa
- Slot kümesi `{09:00, 17:00}` dışında bir değer içeriyorsa
- Sayısal alanlarda sonlu olmayan (NaN, sonsuz) bir değer varsa

Bu tasarım kararı bilinçlidir ve Bölüm 4.1'in ikinci yarısıdır: **sessizce düzelten bir boru hattı, bozuk veriyi bozuk sonuca çevirir ve kimse fark etmez.** Duran bir boru hattı ise sorunu insana gösterir. Referans veri setinde bu doğrulamaların hiçbiri tetiklenmez; ama farklı bir veriyle çalıştırılırsa koruma yerindedir.

### 3.3 Adım 3 — Normalizasyon

Üç dönüşüm uygulanır ve üçü de **biçimsel**dir, yani hiçbir değeri değiştirmez:

- `tarih` kolonu metinden `datetime` tipine çevrilir ve gün başına normalize edilir.
- Slot metni kırpılır ve `9:00` değeri `09:00`'a çevrilir. Ham dosyada slot değeri `9:00` biçiminde yazılıdır; çıktı şablonu ise `09:00` bekler. Bu tek karakterlik fark, düzeltilmezse grid birleştirmesinin sessizce boş dönmesine yol açar.
- `toplam_desi` kolonu `int64` tipine sabitlenir; desi zaten tam sayıdır, bu adım kayan noktalı aritmetikten gelebilecek `4999,9999` türü artıkları baştan engeller.

### 3.4 Adım 4 — Tam grid kurulumu (en kritik adım)

Bu, ön işlemenin tahmin doğruluğunu en çok etkileyen adımıdır.

Ham veri seyrektir (Bölüm 2.3). Model doğrudan bu 66.024 satır üzerinde eğitilseydi, **sıfırları hiç görmezdi** — çünkü sıfırlar dosyada satır olarak yok. Örneğin bir OD çiftinin pazar günü 09:00 slotunda geçmiş 4 haftanın 3'ünde talep oluşmamışsa, seyrek veri üzerinde medyan yalnız o tek dolu gözlemden hesaplanır ve tahmin gerçek değerin dört katına çıkar.

`build_grid` bunu şöyle çözer:

```
grid = OD çiftleri  x  {09:00, 17:00}  x  [başlangıç .. bitiş] günleri
grid = grid  SOL BİRLEŞTİRME  gerçekleşen talep
grid[desi] = eşleşmeyen hücrelerde 0
```

Sonuç: model artık 66.024 pozitif gözlemi değil, **103.462 hücrenin tamamını** görür ve sıfırlar birer gözlem olarak medyan hesabına girer.

Bu adımın gerekliliğini gösteren somut bir ölçüm: ham veride (OD, slot, haftagünü) üçlüsünün **3.862** farklı kombinasyonu görünür; tam grid üzerinde ise **4.046** kombinasyon vardır. Aradaki **184 kombinasyon**, altı ay boyunca bir kez bile talep oluşmamış hücrelerdir. Grid kurulmasaydı bu 184 grup için model bir taban bulamayacak, tanımsız kalacaktı.

### 3.5 Adım 5 — Eğitim takvim filtresi

Eğitim geçmişinden **23 tarih** dışlanır:

| Grup | Tarihler | Sayı |
|---|---|---|
| Resmî tatil ve bayramlar | 1 Ocak; 19–22 Mart; 23 Nisan; 1 Mayıs; 19 Mayıs; 25–31 Mayıs | 15 |
| Ocak–Mayıs aylarının son iki günü | 30–31 Ocak; 27–28 Şubat; 30–31 Mart; 29–30 Nisan; 30–31 Mayıs | 10 |
| İki listenin kesişimi (30–31 Mayıs) | – | −2 |
| **Toplam benzersiz tarih** | | **23** |

Sayısal etkisi:

| Seviye | Toplam | Eğitimde kullanılan | Dışlanan |
|---|---:|---:|---:|
| Grid hücresi | 103.462 | 90.168 | 13.294 (%12,8) |
| Gün | 179 | 156 | 23 |

Bu filtrenin amacı, taban modelin "normal bir gün nasıl görünür" sorusunu **anormal günlerin bulaşması olmadan** cevaplamasıdır. Ay sonu çöküşü ve bayram günleri tabanın içinde kalsaydı, medyan aşağı çekilir ve normal günler sistematik olarak düşük tahmin edilirdi. Anormal günler ise silinmez, **ayrı bir katmanda modellenir** (Bölüm 5.3).

Filtreyle ilgili iki nokta özellikle önemlidir ve Bölüm 4.2'de tekrar ele alınacaktır:

- Dışlama **yalnız eğitim geçmişine** uygulanır. Hedef günler asla dışlanmaz.
- Bu yüzden dışlama listesi bilerek yalnız **Ocak–Mayıs**'ı kapsar. Haziran'ın son iki günü (29–30 Haziran) tahmin ufkunun **içindedir**; onları dışlamak, tahmin edilmesi istenen günü tahmin etmemek olurdu.

### 3.6 Adım 6 — Kararlı sıralama ve kimlik ataması

Çıktı satırları `(tarih, çıkış, varış, slot)` anahtarına göre **kararlı (stable) sıralama** ile sıralanır ve ardından `D00001`, `D00002`, ... biçiminde kimlik atanır. Kararlı sıralama, girdi dosyasındaki satır sırası değişse bile aynı kimlik dizisinin üretilmesini garanti eder — yani çıktı tekrarlanabilirdir (reproducible). 99.999 satırdan fazla girdi gelirse sessiz kimlik çakışması yerine açık bir hata fırlatılır.

### 3.7 Adım 7 — Çıktı sanitizasyonu

Son adımda üç koruma uygulanır:

- Sonsuz (`inf`) ve tanımsız (`NaN`) değerler sıfıra çevrilir.
- Negatif değerler sıfıra kırpılır — negatif desi fiziksel olarak anlamsızdır.
- Değer `round()` ile tam sayıya yuvarlanır. Python'un `round()` fonksiyonu "yarımı çift sayıya yuvarla" davranışı gösterir; bu, 4.046 satır boyunca tek yönlü sistematik bir sapmanın birikmesini önler (hep yukarı yuvarlama binlerce satırda görünür bir yanlılık üretirdi).

---

## 4. Yapmadıklarımız ve Nedenleri

Bu bölüm belgenin merkezidir. Aşağıdaki tekniklerin hiçbiri uygulanmamıştır ve her biri için gerekçe **ölçüme dayalıdır**, tercihe değil.

### 4.1 Veri temizleme yapmadık — çünkü temizlenecek veri yoktu

Klasik bir veri temizleme adımı şunları arar: eksik değerler, tekrar eden kayıtlar, tip tutarsızlıkları, imkânsız değerler, aykırı biçimler. Bunların hepsini **ölçtük** ve sonuç Bölüm 2.2'deki tablodur: her denetimde sıfır bulgu.

Bu durumda bir temizleme adımı yazmak iki şekilde zarar verirdi:

1. **Yanlış güvenlik hissi.** "Eksik değerleri doldur" gibi bir adım, veride eksik değer olmadığı hâlde kodda durursa, gelecekte gerçekten eksik değer geldiğinde onu sessizce doldurur ve sorun hiç fark edilmez.
2. **Doğrulanamayan karmaşıklık.** Etkisi sıfır olan bir adımın doğru çalıştığı test edilemez; çünkü tetiklenmez.

Bunun yerine **doğrulama (validation)** yazdık: veri beklenen biçimde değilse boru hattı düzeltmez, **durur ve söyler** (Bölüm 3.2). Kısacası kararımız "temizleme yok" değil, "**sessiz düzeltme yerine gürültülü doğrulama**"dır.

### 4.2 Satır silme yapmadık — üç ayrı silme sorusu var, üçünün de cevabı hayır

"Silme yapmadık" ifadesi üç farklı soruyu kapsar ve üçünü ayrı ayrı cevaplamak gerekir.

**(a) Eğitim verisinden aykırı değer (outlier) silmedik.**

Bu, kararların en önemlisidir. Ayın son günü, veride **beş ayın beşinde de istisnasız**, normal bir günün yaklaşık **%2'sine** iner; ölçülen en düşük günlük gözlem **2.010 desidir**. Standart bir aykırı değer testi (3 sigma, IQR, winsorize — hangisi olursa) bu günleri anında aykırı işaretler ve siler.

Silmek felaket olurdu: **bu veri setindeki en büyük "aykırı" değerler, tam olarak modellemek istediğimiz sinyalin kendisidir.** Onları temizlemek, öğrenilecek olguyu silmek demektir. Sayısal karşılığı şudur: tahmin ufkunun tam ortasındaki 30 Haziran'ı sıradan bir salı sayan bir model, o tek günde yaklaşık **1,1 milyon desi** hata üretir — ve WMAPE hacim ağırlıklı olduğu için bu tek gün toplam puanı domine eder.

Bunun yerine, aykırı görünen bu günleri **silmedik, isimlendirdik**: her birine bir takvim rolü atadık ve rolün etkisini veriden ölçtük (Bölüm 5.3). Aykırı değer bir gürültü değil, bir **özellikti (feature)**.

**(b) Eğitim filtresi bir silme değildir.**

Bölüm 3.5'teki 23 tarihlik dışlama, satır silmekle karıştırılmamalıdır. Farklar şunlardır:

| | Aykırı değer silme | Bizim eğitim filtremiz |
|---|---|---|
| Kapsam | Tüm veri | Yalnız taban modelin eğitim geçmişi |
| Kalıcılık | Satır veri setinden çıkar | Satır veri setinde durur, yalnız bir hesaba girmez |
| Bilginin akıbeti | Bilgi kaybolur | Bilgi **ikinci katmanda kullanılır** (çarpan kalibrasyonu tam olarak bu günlerden hesaplanır) |
| Hedef günlere etkisi | Hedef gün de elenebilir | Hedef gün **asla** elenmez |

Yani dışlanan 23 tarih, çöpe atılan veri değil, **iki farklı katmana ayrıştırılan** veridir: normal günler tabanı, anormal günler çarpanı besler.

**(c) Çıktı dosyasından sıfır satırları silmedik.**

Teslim edilen 4.046 satırın **1.121'i (%27,7) sıfır desidir.** Bunları dosyadan çıkarmak dosyayı küçültürdü; yapmadık, üç nedenle:

1. **Jüri açıkça cevapladı.** Soru–Cevap oturumunda "tahmin edilen desi çok düşükse o satır çıkarılabilir mi?" sorusuna verilen cevap **"Sunulmalı"** olmuştur.
2. **Grid tamlığı bir sözleşmedir.** Çıktı, ufkun tam kartezyen çarpımıdır. Sıfır satırın olmaması ile "o hücre unutuldu" durumu birbirinden ayırt edilemez hâle gelir; eksiksiz grid bu belirsizliği ortadan kaldırır.
3. **Sonraki adım bu dosyayı anahtar olarak kullanır.** Taşıma planını doğrulayan hakem simülatörünün kurallarından biri, plandaki her talep kimliğinin tahmin dosyasında bulunmasını şart koşar. Satır silmek bu doğrulama zincirini kırar.

Sıfır satırların optimizasyona maliyeti yoktur: sıfır desi için araç çıkarılmaz, dolayısıyla 4.046 satırın 2.925'i plana girer, 1.121'i doğal olarak dışarıda kalır. Yani satırı **dosyada tutmak** ile **plana sokmak** ayrı kararlardır; biz birincisini yaptık, ikincisini yapmadık.

### 4.3 Logaritmik dönüşüm yapmadık

Log dönüşümü, çarpık dağılımlı ve çarpımsal hatalı verilerde hata metriğini dengelemek için kullanılır. Burada iki nedenle uygulanmadı:

- Değerlendirme ölçütü **WMAPE**, yani **doğrusal ölçekte hacim ağırlıklı** bir hatadır. Log uzayında optimize etmek, doğrusal uzayda ölçülen puanla uyumsuz bir hedefi optimize etmek olur — küçük hücrelerdeki yüzde hatalar aşırı ağırlık kazanır, büyük hücreler ihmal edilir. Bu, doğrudan puan kaybıdır.
- Veride **sıfır değerler yapısal olarak vardır** (%36,19 örtük sıfır, çıktıda %27,7 sıfır). `log(0)` tanımsızdır; kaçınmak için `log(1+x)` gibi bir kaydırma gerekir ve bu kaydırma, sıfırın anlamını ("talep yok") bulanıklaştırır.

### 4.4 Ölçekleme ve normalizasyon yapmadık

Ölçekleme (standardizasyon, min-max) mesafeye veya gradyana dayalı öğrenicilerin gereksinimidir: özellikler farklı birimlerdeyse biri diğerini ezer. Bizim modelimizde:

- Öğrenilen büyüklük bir **medyandır**; medyan monoton dönüşümlere karşı zaten dayanıklıdır ve ölçekten etkilenmez.
- Karşılaştırılan tek şey aynı hücrenin **kendi geçmişidir**; farklı birimli özelliklerin bir arada toplandığı bir aşama yoktur.
- Çıktının **desi biriminde** kalması gerekir; ölçekleyip geri dönüştürmek, hiçbir kazanç sağlamayan ekstra bir yuvarlama hatası kaynağı olurdu.

### 4.5 Yumuşatma (smoothing) ve ara değerleme (interpolation) yapmadık

Ara değerleme, veri boşluklarını doldurmak içindir. Bizde **veri boşluğu yoktur**: 179 günün 179'u doludur ve "görünmeyen hücre" bir boşluk değil, bilgi taşıyan bir sıfırdır (Bölüm 3.4). Boşluk olmayan yerde ara değerleme, olmayan bir gözlemi uydurmak anlamına gelir.

Yumuşatma (hareketli ortalama, üstel yumuşatma) ise uç değerleri törpüler. Bizim veri setimizde uç değerler sinyalin kendisidir (Bölüm 4.2-a); yumuşatma, ay sonu çöküşünü komşu günlere yayarak hem çöküşü hem de komşu günleri bozardı. Zaten taban modelde kullandığımız **medyan**, gürültüye karşı yumuşatmanın sağladığı korumayı **sinyali bozmadan** sağlar.

### 4.6 Trend ve mevsim ayrıştırma (decomposition) yapmadık

Klasik ayrıştırma (STL, klasik toplamsal/çarpımsal ayrıştırma) seriyi trend + mevsim + artık bileşenlerine böler. Burada uygulanmamasının nedenleri:

- Veri **179 gün**, yani yaklaşık altı aydır. Yıllık mevsimselliği tahmin etmek için bir tam çevrim bile yoktur; ayrıştırma bu ufukta yıllık bileşeni **uyduracaktır**.
- Serideki baskın mevsimsellik **haftalıktır** ve taban modelimiz zaten doğrudan haftagünü bazında çalışır, yani haftalık mevsimselliği ayrıştırmaya gerek kalmadan modelin yapısına gömer.
- Geriye kalan tek güçlü sistematik etki **takvim olayıdır** (ay sonu) ve bu, düzenli bir mevsimsel bileşen değil, ayrık bir olaydır; ayrıştırma bunu yakalayamaz, ikinci katmanımız yakalar.

### 4.7 Harici makine öğrenmesi kütüphanesi kullanmadık

Projede **scikit-learn, statsmodels, Prophet, ARIMA, XGBoost, LightGBM veya herhangi bir derin öğrenme çerçevesi yoktur.** `requirements.txt` yalnız iki paket içerir: `pandas` ve `openpyxl`.

Gerekçe üç maddedir:

1. **Veri yapısı, kompleks bir öğreniciyi haklı çıkarmıyor.** Seri, tek bir güçlü mevsimsellik (haftagünü) ve tek bir takvim olayı (ay sonu) tarafından yönetiliyor. Bu iki olguyu robust medyan ve ölçülmüş bir çarpan zaten yakalıyor.
2. **Örneklem, öğrenilecek parametre sayısını sınırlıyor.** Her (OD, slot, haftagünü) hücresi için altı ayda yaklaşık 25 gözlem vardır. Bu miktarda gözlemle bir gradyan artırma (gradient boosting) modeli veya mevsimsel ARIMA uydurmak, doğrulanamayan parametre tahmini demektir; frozen backtest'te aşırı uydurma (overfitting) olarak geri döner.
3. **Ölçüm bunu doğruladı.** Modelimiz iki referansa karşı ölçüldü (Bölüm 6.3). Normal haftada düz haftagünü medyanıyla **birebir aynı**, ay sonu haftasında ondan **belirgin biçimde daha iyi** sonuç veriyor. Yani eklediğimiz tek karmaşıklık katmanı ölçülebilir bir kazanç sağlıyor; daha fazlası için elimizde kanıt yoktu ve kanıtsız karmaşıklık eklemedik.

Ek bir pratik fayda: bağımlılık yüzeyinin iki pakete indirilmiş olması, jürinin çalıştırma ortamında sürüm çatışması riskini pratikte sıfırlar.

### 4.8 Özet tablo

| Teknik | Uygulandı mı | Gerekçe |
|---|---|---|
| Eksik değer doldurma | Hayır | Veride 0 eksik değer var; yerine fail-fast doğrulama yazıldı |
| Tekrar eden kayıt temizleme | Hayır | Veride 0 tekrar var; yerine benzersizlik doğrulaması yazıldı |
| Aykırı değer temizleme / winsorize | Hayır | En büyük aykırılar modellenmek istenen sinyalin kendisi |
| Çıktıdan sıfır satır silme | Hayır | Jüri "Sunulmalı" dedi; grid tamlığı ve hakem doğrulaması gerektiriyor |
| Logaritmik dönüşüm | Hayır | Ölçüt doğrusal ölçekte WMAPE; veride yapısal sıfırlar var |
| Ölçekleme / normalizasyon | Hayır | Medyan tabanlı, ölçekten bağımsız model; çıktı desi biriminde olmalı |
| Yumuşatma / ara değerleme | Hayır | Veride boşluk yok; yumuşatma takvim sinyalini bozar |
| Trend / mevsim ayrıştırma | Hayır | 179 gün yıllık bileşen için yetersiz; haftalık mevsimsellik zaten modelin yapısında |
| Harici ML kütüphanesi | Hayır | Örneklem karmaşık öğreniciyi taşımıyor; ölçülen kazanç yok |
| Tam grid kurulumu | **Evet** | Örtük sıfırlar modellenmezse tahmin sistematik olarak yukarı sapar |
| Eğitim takvim filtresi | **Evet** | Anormal günler tabanı kirletmesin; ayrı katmanda modellensin |
| Şema doğrulaması | **Evet** | Bozuk veriyi sessizce işlemek yerine durdurmak |

---

## 5. Modelimiz

### 5.1 Model tek satırda

```
tahmin(hücre) = DOW_medyan_tabanı(OD, slot, haftagünü; k = 4)  x  takvim_çarpanı(gün rolü)
```

İki katmanlı, **çarpımsal** bir modeldir. Birinci katman "bu hücre normal bir X gününde kaç desi taşır" sorusunu, ikinci katman "bu belirli gün normalden ne kadar sapar" sorusunu cevaplar.

### 5.2 Katman 1 — Haftagünü medyan tabanı

Her hedef hücre için taban şöyle hesaplanır:

1. Hedefin anahtarı alınır: `(çıkış, varış, slot, haftagünü)`.
2. Eğitim geçmişinde aynı anahtara sahip, **hedef tarihten kesin önce** gelen gözlemler bulunur.
3. Bunların **son 4 tanesi** alınır (k = 4, yani son dört hafta).
4. Bu dört değerin **medyanı** taban tahmindir.
5. Hiç geçmiş gözlem yoksa taban 0'dır.

**Neden haftagünü bazında?** Lojistik talebi güçlü bir haftalık ritim taşır: pazar günü hacmi hafta içinin çok altındadır. Modeli haftagünü bazında kurmak, bu mevsimselliği ayrı bir bileşen olarak tahmin etmek yerine **doğrudan modelin yapısına gömer** — tahmin edilecek ek parametre üretmez.

**Neden medyan, ortalama değil?** Ortalama tek bir uç gözleme karşı savunmasızdır. Dört haftanın birinde bir kampanya veya bayram varsa, ortalama kalıcı olarak yukarı kayar; medyan bu tek gözlemi **görmezden gelir ama silmez**. Aykırı değere karşı dayanıklılığı, veriyi silmeden elde etmenin yolu budur.

**Neden k = 4?** İki hata kaynağı arasındaki dengedir:

| k değeri | Risk |
|---|---|
| Çok küçük (k = 1–2) | Örneklem gürültüsü; tek bir sıra dışı hafta tahmini domine eder |
| Çok büyük (k = 8+) | Mevsimsel kayma; aylar önceki hacim seviyesi bugüne taşınır |

k = 4, yaklaşık son bir aylık davranışı temsil eder — hacim seviyesindeki yavaş kaymayı takip edecek kadar kısa, tek haftalık gürültüyü bastıracak kadar uzun.

Bu katmanın önemli bir özelliği **parametrik olmamasıdır (non-parametric)**: uydurulan bir katsayı yoktur, taban her hedef için geçmiş gözlemlerden doğrudan okunur. Tam grid üzerinde toplam **4.046 farklı (OD, slot, haftagünü) grubu** için ayrı bir taban hesaplanır.

### 5.3 Katman 2 — Takvim çarpanları

Taban, "normal bir salı" sorusunu cevaplar. Ama 30 Haziran normal bir salı değildir. İkinci katman bunu düzeltir.

**Rol atama.** Her gün, takvim aritmetiğiyle dört rolden birine atanır. Kodda gömülü tek bir tarih yoktur; rol, ayın uzunluğundan hesaplanır — yani model başka bir yıla veya aya taşındığında da çalışır:

| Rol | Tanım |
|---|---|
| `month_end` | Ayın son günü |
| `day_before_month_end` | Ayın son gününden bir önceki gün |
| `first_day_after_month_end` | Ayın ilk günü |
| `normal` | Diğer tüm günler |

**Çarpan kalibrasyonu.** Her rol için çarpan, geçmişteki olay günlerinden **ölçülür**:

```
oran(olay günü) = o günün gerçekleşen toplam hacmi
                  --------------------------------------------------
                  aynı hücreler için hesaplanan DOW-medyan tabanının toplamı

çarpan(rol) = o role ait tüm oranların MEDYANI
```

Tabana bölmek kritik bir ayrıştırma yapar: **ay sonu etkisini haftagünü etkisinden ayırır.** 30 Haziran bir salıdır; taban zaten salı hacmini yakalar, çarpan yalnızca "ay sonu olma" bilgisini ekler. Bölmeseydik, çarpan içinde hangi haftagününe denk geldiği de karışırdı.

**Ölçülen üç çarpan:**

| Takvim rolü | Çarpan | Geçmiş beş aydan ham oranlar |
|---|---:|---|
| Ay sonundan bir önceki gün | 0,6752 | 0,879 / 0,766 / 0,648 / 0,675 / 0,059 |
| **Ayın son günü** | **0,0198** | 0,0198 / 0,0254 / 0,0194 / 0,0088 / 0,0210 |
| Ayın ilk günü (toparlanma) | 1,2072 | 2,929 / 1,207 / 1,056 / 0,090 / 1,574 |
| Normal gün | 1,0000 | Tanım gereği |

Ayın son günü satırındaki tutarlılık dikkat çekicidir: beş ayın beşinde de oran 0,009–0,026 bandındadır. Bu, tesadüfi bir dalgalanma değil, **operasyonel bir düzenliliktir**.

**Burada da medyan kullandık, ortalama değil.** Etkisi "ayın ilk günü" satırında görülür: ham oranlar arasında 1 Şubat'ın 2,929'u ve resmî tatile denk gelen 1 Mayıs'ın 0,090'ı vardır. Medyan ikisini de dışarıda bırakıp **1,2072** verir; ortalama alınsaydı çarpan **1,371** çıkardı — yani ayın ilk günü sistematik olarak %14 fazla tahmin edilirdi.

**Güvenli geri düşüş.** Bir rol için en az **iki** geçerli oran yoksa çarpan **1,0**'a düşer. Yani tek bir gözlemden çarpan uydurulmaz; model emin olmadığı yerde müdahale etmemeyi seçer.

### 5.4 Neden çarpımsal, toplamsal değil

İki katmanı toplayabilirdik (`taban + düzeltme`). Çarpmayı seçtik, çünkü ay sonu etkisi **hacme oranlı** bir etkidir: büyük bir hattaki çöküş binlerce desi, küçük bir hattaki aynı çöküş onlarca desidir. Sabit bir toplamsal düzeltme, küçük hücrelerde negatif tahmin üretir (kırpılması gerekir, bilgi kaybolur), büyük hücrelerde ise yetersiz kalır. Çarpımsal yapı bu ölçeklenmeyi doğal olarak sağlar ve negatif değer üretmesi yapısal olarak imkânsızdır.

### 5.5 Bu bir makine öğrenmesi modeli midir?

Evet — ve tam olarak hangi anlamda olduğunu açıkça yazmak gerekir. Model, **örnek tabanlı (instance-based), parametrik olmayan (non-parametric) bir tahmin modelidir** ve makine öğrenmesinin tanımlayıcı unsurlarının hepsini taşır:

| Unsur | Bu modeldeki karşılığı |
|---|---|
| Eğitim verisi | 1 Ocak – 28 Haziran 2026 geçmişi, tam grid üzerinde 90.168 hücre |
| Öğrenilen büyüklükler | 4.046 hücre grubu için taban medyanları + 3 global takvim çarpanı |
| Özellikler (features) | Çıkış, varış, slot, haftagünü, takvim rolü, gecikmeli hacim geçmişi |
| Hiperparametreler | k = 4, medyan toplayıcı, rol başına minimum 2 örnek, dışlama listesi |
| Eğitim/test ayrımı | Dondurulmuş (frozen) kesim tarihi; ufuk içinde yeniden eğitim yok |
| Sızıntı koruması | Üç bağımsız katman (Bölüm 6.2) |
| Doğrulama | Frozen backtest, iki referans modele karşı WMAPE (Bölüm 6.3) |

Modeli "basit" yapan şey kullanılan matematiğin ilkelliği değil, **problemin gerçekten basit olması** ve bunu ölçerek göstermiş olmamızdır. Karmaşık bir model, kazanç sağlamadığını ölçtüğümüz için değil, kazanç sağladığını ölçemediğimiz için kullanılmamıştır.

---

## 6. ML Modelinde Kullandıklarımız

### 6.1 Girdi özellikleri (features)

Model altı bilgiden başka hiçbir girdi kullanmaz:

| # | Özellik | Tipi | Modeldeki rolü |
|---|---|---|---|
| 1 | Çıkış transfer merkezi | Kategorik (18 değer) | Hücre anahtarının parçası |
| 2 | Varış transfer merkezi | Kategorik (17 değer) | Hücre anahtarının parçası |
| 3 | Slot (09:00 / 17:00) | Kategorik (2 değer) | Hücre anahtarının parçası |
| 4 | Haftagünü | Kategorik (7 değer) | Haftalık mevsimselliği taşır |
| 5 | Gecikmeli hacim geçmişi | Sayısal (son k = 4 gözlem) | Taban tahmininin kaynağı |
| 6 | Takvim rolü | Kategorik (4 değer) | İkinci katmanın çarpanını seçer |

Kategorik özellikler kodlanmaz (one-hot, target encoding vb. yoktur); doğrudan **gruplama anahtarı** olarak kullanılırlar. Bu, kategorik değişken kodlamasının getireceği tüm aşırı uydurma risklerini yapısal olarak ortadan kaldırır.

### 6.2 Hiperparametreler

Modelin ayarlanabilir tüm büyüklükleri aşağıdadır. Toplam **dört** hiperparametre vardır:

| Hiperparametre | Değer | Gerekçe |
|---|---|---|
| `k` — geriye bakış penceresi | 4 hafta | Mevsimsel kayma ile örneklem gürültüsü dengesi |
| Toplayıcı (aggregator) | Medyan | Aykırı değere dayanıklılık, veri silmeden |
| `MIN_CALENDAR_SAMPLES` | 2 | Tek gözlemden çarpan uydurmayı engeller; altındaysa 1,0'a düşer |
| Eğitim dışlama listesi | 23 tarih | Anormal günler tabanı kirletmesin |

Bu sayının küçüklüğü bilinçlidir: her hiperparametre, backtest üzerinde ayarlanabilecek bir serbestlik derecesidir ve serbestlik dereceleri arttıkça test setine aşırı uydurma riski büyür. Dört parametreyle bu risk pratikte yok denecek düzeydedir.

### 6.3 Öğrenilen parametreler

| Parametre grubu | Sayı | Nasıl elde edildi |
|---|---:|---|
| Hücre tabanı (OD x slot x haftagünü medyanı) | 4.046 | Doğrudan geçmiş gözlemlerden, uydurma yok |
| Global takvim çarpanı | 3 | Geçmiş beş ay sonu olayının oran medyanı |

Yani **veriden uydurulan (fit edilen) toplam katsayı sayısı üçtür.** Geri kalan her şey doğrudan geçmiş gözlemlerin okunmasıdır. Aşırı uydurma riskinin bu kadar düşük olmasının nedeni budur.

### 6.4 Kullanılan yazılım araçları

| Araç | Sürüm kısıtı | Kullanım |
|---|---|---|
| Python | 3.11 | Çalışma ortamı |
| pandas | `requirements.txt` | Veri çerçevesi, gruplama, birleştirme, medyan |
| openpyxl | `requirements.txt` | Excel okuma/yazma |
| pytest | Yalnız geliştirme | Regresyon testleri |

Üretim bağımlılığı **iki pakettir**. `src/forecast.py` dosyasının import ettiği her şey: `calendar`, `math`, `datetime`, `typing` (Python standart kütüphanesi) ve `pandas`.

### 6.5 Kullanmadığımız ve kullanamayacağımız özellikler

Tahmin doğruluğunu artırabilecek bazı özellikler, **veri sağlanmadığı için** kullanılamamıştır. Bunları eksiklik olarak değil, veri sınırı olarak kaydediyoruz:

| Özellik | Neden kullanılmadı |
|---|---|
| Kampanya / indirim takvimi | Veri setinde yok |
| Ürün kategorisi kırılımı | Veri setinde yok; talep yalnız toplam desi olarak veriliyor |
| Hava durumu | Veri setinde yok |
| Fiyat, stok, sipariş adedi | Veri setinde yok |
| Merkez bazlı kapasite geri beslemesi | Tahmin ile optimizasyon arasında tek yönlü akış var |

---

## 7. Eğitim ve Doğrulama Protokolü

### 7.1 Frozen (dondurulmuş) backtest

Raporlanan tüm başarım rakamları **tek atışlık** bir çerçeveyle üretilir:

- Eğitim verisi tek bir **kesim tarihinde** kesilir.
- Ufuk içinde **yeniden eğitim yoktur** — 7 günün tamamı tek bir modelle tahmin edilir.
- OD evreni bile yalnız eğitim geçmişinden türetilir; ufukta ilk kez görünen bir OD çifti evrene giremez.

Bu, gerçek yarışma koşulunun aynısıdır. Yaygın bir hata olan "yuvarlanan başlangıçlı (rolling-origin) backtest'i tek atışlık koşul sanmak" burada bilinçle önlenmiştir.

### 7.2 Üç sızıntı (leakage) koruması

Bir tahmin modelinin bozulacağı en kolay yer, gelecekteki gerçekleşen değerin modele sızmasıdır. Üç bağımsız koruma vardır:

1. **Çarpan kalibrasyonunda:** her olay günü için taban, yalnız `tarih < hedef gün` verisiyle hesaplanır. Bir test, taban fonksiyonunu bir "sızıntı bekçisi" ile değiştirip her çağrıda bu koşulu doğrular.
2. **Tabanda:** olay günlerinin kendisi taban hesabından dışlanır, yani anormal gün kendi tabanını belirlemez.
3. **Yapısal olarak:** tahmin fonksiyonu, kendisine verilen geçmiş veride tahmin başlangıcına veya sonrasına ait **tek bir satır** bulursa çalışmayı reddeder ve hata fırlatır. Sessizce sızıntı yapması mümkün değildir.

Üçüncüsü özellikle önemlidir: sızıntı bir uyarı değil, **çalışmayı durduran bir hatadır**.

### 7.3 Ölçülen sonuçlar

İki referans modele karşı ölçüldü. Naive model "geçen hafta aynı gün ne olduysa o olur" der; DOW medyanı ise takvim katmanı olmayan hâlimizdir, yani ikinci katmanın **saf katkısını** izole eder.

| Pencere | Naive (geçen hafta) | DOW medyanı | **Bizim model** |
|---|---:|---:|---:|
| Normal hafta · 15–21 Haziran | 0,2592 | 0,2174 | **0,2174** |
| Ay sonu haftası · 30 Mart – 5 Nisan | 0,6972 | 0,5328 | **0,4464** |

Tablonun okunuşu iki cümledir:

- **Normal haftada bizim model ile düz DOW medyanı birebir aynıdır.** Çünkü o pencerede takvim rolü olan gün yoktur ve çarpan 1,0'dır. Yani eklediğimiz katman, gerekmediği yerde **hiç müdahale etmez** — bu, bir katmandan istenebilecek en iyi davranıştır.
- **Ay sonu haftasında hata 0,5328'den 0,4464'e iner.** Takvim katmanı hatayı **%16,2**, naive referansa göre ise **%36,0** azaltır.

### 7.4 Açık kalem: bias ve neden düzeltilmedi

Ay sonu haftası penceresinde ölçülen **+%28,3 bias** ilk bakışta en değerli iyileştirme alanı gibi göründü. Dört düzeltme adayı denendi: slot bazlı çarpanlar, ay sonundan iki gün sonrası için ek rol, toparlanma kalibrasyonu ve taban kalibrasyonu.

Sonuç: **hedefin kendisi sahte çıktı.** +%28,3 bias, 29 Mart kesim tarihinde "ayın ilk günü" çarpanının yalnızca iki örnekle kalibre edilmesinin bir artefaktıdır. Birini-dışarıda-bırak (leave-one-out) yöntemiyle ölçüldüğünde teslim edilen modelin bias'ı **−0,0573**'tür, yani pratikte yansızdır. Dört adayın dördü de dışsal örneklemde başarısız oldu ve **hiçbiri uygulanmadı.**

Bunu raporda tutuyoruz, çünkü ölçüm yapmadan "iyileştirme" uygulamanın nasıl bir tuzak olduğunu gösteren en net örnektir.

---

## 8. Üretilen Çıktı

### 8.1 Toplamlar

| Büyüklük | Değer |
|---|---:|
| Satır sayısı | 4.046 |
| Toplam tahmin edilen desi | 4.977.975 |
| Sıfır desili satır | 1.121 (%27,7) |
| Optimizasyona giren satır | 2.925 |

### 8.2 Günlük dağılım — takvim katmanının imzası

Aşağıdaki tablo, modelin ne yaptığını tek bakışta gösterir. "Aynı haftagünü ortalaması", takvim katmanı olmayan bir modelin vereceği yanıta yakın bir referanstır:

| Gün | Bizim tahmin (desi) | Aynı haftagünü ortalaması | Oran |
|---|---:|---:|---:|
| 29 Haziran (Pazartesi) | 1.161.736 | 1.622.264 | 0,72 |
| **30 Haziran (Salı)** | **24.040** | 1.110.177 | **0,02** |
| 1 Temmuz (Çarşamba) | 1.305.721 | 1.016.846 | 1,28 |
| 2 Temmuz (Perşembe) | 978.038 | 953.021 | 1,03 |
| 3 Temmuz (Cuma) | 859.444 | 897.773 | 0,96 |
| 4 Temmuz (Cumartesi) | 591.542 | 619.547 | 0,96 |
| 5 Temmuz (Pazar) | 57.454 | 86.435 | 0,66 |

Fark üç günde toplanır: 29 Haziran bastırılmış, 30 Haziran çökmüş, 1 Temmuz toparlanmıştır. Kalan dört günde çarpan 1,0'dır ve oranlar 0,96–1,03 bandındadır — yani model **yalnız gerekli yerde** müdahale eder.

Bu tablo aynı zamanda Bölüm 4.2'deki kararın somut karşılığıdır: 30 Haziran'ı aykırı sayıp silseydik, o gün için 1,1 milyon desi civarında bir tahmin üretecektik; gerçek ise onun yaklaşık %2'sidir.

---

## 9. Bilinen Sınırlar

Dürüst bir teknik rapor, modelin nerede zayıf olduğunu da yazar:

- **Slot ayrımı yoktur.** Takvim çarpanları geneldir; 17:00 slotu toplam desinin %91,24'ünü taşıdığı hâlde slot bazlı ayrı çarpan denenmiş ve dışsal örneklemde başarısız olmuştur (Bölüm 7.4).
- **Çarpanlar yalnız beş olaydan kalibre edilmiştir.** Veri altı ay olduğu için rol başına en fazla beş gözlem vardır. Daha uzun geçmişle çarpanların güven aralığı daralır.
- **Yıllık mevsimsellik modellenmemiştir.** 179 günlük veri bir yıllık çevrimi kapsamaz; bayram dönemleri, yılbaşı veya okul dönemleri gibi yıllık etkiler bu modelde yoktur.
- **Yeni OD çiftleri sıfır tahmin alır.** Eğitim geçmişinde hiç görünmemiş bir hat için taban 0'dır. Referans veri setinde böyle bir durum yoktur, ama yeni bir hat açılırsa model onu göremez.
- **Trend bileşeni yoktur.** Hacimde kalıcı bir büyüme olursa, k = 4 penceresi bunu ancak dört hafta gecikmeyle takip eder.

---

## 10. Özet

Üç soru, üç cevap:

**Bizden ne isteniyor?** Bir haftalık ufukta, 289 aktif OD çiftinin her biri için, 7 günün her birinde, 09:00 ve 17:00 slotlarının her birinde oluşacak desi miktarı — toplam 4.046 hücre. Ölçüt hacim ağırlıklı mutlak yüzde hata (WMAPE).

**Ne ön işleme yaptık?** Yedi adım: dosya adı çözümü, şema doğrulaması, biçim normalizasyonu, **tam grid kurulumu** (örtük sıfırların modellenmesi), eğitim takvim filtresi, kararlı sıralama ve çıktı sanitizasyonu. Veri temizleme yapmadık, çünkü ölçtüğümüzde veride 0 eksik değer, 0 tekrar, 0 negatif ve 0 tip hatası bulduk; sessizce düzelten bir adım yerine bozuk veride **duran** bir doğrulama katmanı yazdık. Satır silmedik, çünkü bu veri setindeki en uç değerler modellemek istediğimiz sinyalin kendisidir ve çıktıdaki sıfır satırlar jürinin açık talebiyle dosyada kalmalıdır.

**Modelimiz ne?** İki katmanlı çarpımsal bir tahmin modeli: her (çıkış, varış, slot, haftagünü) hücresi için son dört gözlemin medyanından oluşan bir taban, çarpı geçmiş ay sonlarından ölçülmüş bir takvim çarpanı. Dört hiperparametre, üç uydurulan katsayı, iki üretim bağımlılığı. Frozen backtest'te normal haftada referansla birebir aynı, ay sonu haftasında referanstan **%16,2** daha iyi — yani eklediğimiz tek karmaşıklık katmanı, ölçülmüş bir kazanç karşılığında eklenmiştir.
