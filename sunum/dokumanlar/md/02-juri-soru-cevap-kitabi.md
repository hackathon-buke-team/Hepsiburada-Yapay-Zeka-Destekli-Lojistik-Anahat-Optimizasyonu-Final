# Jüri Soru-Cevap Hazırlık Kitabı

Takım Büke · TEKNOFEST 2026 · Hepsiburada Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · Final Backtest Aşaması

Bu kitap, sunum sonrası soru-cevap oturumu için hazırlanmış referans belgedir. Amacı tek: takımın hiçbir soruya hazırlıksız yakalanmaması. Her cevap ölçülmüş bir sayıya, bir dosya/fonksiyon adına veya jüri Soru-Cevap dokümanındaki bir cevaba dayanır. Bilmediğimiz veya ölçmediğimiz hiçbir şey burada bir iddia olarak yazılmadı; bilinen sınırlar ayrı ayrı işaretlendi.

---

## 1. Bu Kitap Nasıl Kullanılır

Sorular dokuz bölüme ayrıldı: (A) problem ve maliyet modeli, (B) talep tahmini, (C) Stage 0 temel plan, (D) Stage 1-2-3 iyileştirme aşamaları, (E) doğrulama ve güvenilirlik, (F) kurallara uyum, (G) final backtest teknik gereksinimleri, (H) zor ve sıkıştırıcı sorular, (I) soruyu karşılama taktikleri.

Her soru dört parçadan oluşur:

- **Kısa cevap** — mikrofonun başında söylenecek bir-iki cümle. Jüri çoğu zaman bununla yetinir.
- **Detay** — takip sorusu gelirse açılacak teknik gövde.
- **Kanıt** — dosya, fonksiyon, ölçülmüş sayı veya jüri Q&A referansı.
- **Tuzak** — yalnız gerektiğinde. Bu soruda nereye dikkat edilmeli, hangi cevap yanlış olurdu.

Bir kural: **sayıyı hatırlamıyorsak yuvarlarız, uydurmayız.** "Yaklaşık 11,2 milyon TL" doğrudur; yanlış bir ondalık ise belgeye olan güveni tümden yıkar.

---

## 2. Çekirdek Sayı Tablosu

Aşağıdaki tablo bu kitabın omurgasıdır. Oturum öncesi son 10 dakikada yalnız bu bölüm okunsa bile soruların büyük çoğunluğu karşılanır.

### 2.1 Optimizasyon merdiveni

| Aşama | Araç maliyeti (TL) | SLA cezası (TL) | Toplam (TL) | İhlal | Fiziksel araç |
|---|---|---|---|---|---|
| Stage 0 — temel plan | 15.460.592,57 | 1.020.367,20 | 16.480.959,77 | 0 | 1.269 |
| Stage 1 — aynı-hat onarım | 12.510.401,25 | 2.169.783,60 | 14.680.184,85 | 0 | 1.092 |
| Stage 2 — milk-run (≤4 durak) | 8.752.512,29 | 2.560.826,00 | 11.313.338,29 | 0 | 693 |
| Stage 3 — rota-ortası yük alma | 8.616.944,73 | 2.615.532,00 | 11.232.476,73 | 0 | 665 |

Toplam iyileşme **−%31,84**. Araç maliyetinden **6.843.647,84 TL** kazanıldı, karşılığında **1.595.164,80 TL** ek SLA cezası ödendi.

### 2.2 Doluluk ve filo karması

| Ölçü | Stage 0 | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|---|
| Spot araç doluluğu (ortalama) | %48,02 | %56,82 | %76,96 | %79,03 |
| Doluluğu %30 altındaki spot araç | 480 / 1.143 | 296 / 966 | 46 / 567 | 30 / 539 |
| Kamyonet (5.600 desi) | 950 | 773 | 259 | 233 |
| Hafif Kamyon (7.200 desi) | 24 | 24 | 29 | 29 |
| Kamyon (12.000 desi) | 196 | 196 | 306 | 304 |
| Tır (22.400 desi) | 99 | 99 | 99 | 99 |
| Plan satırı | 3.167 | 3.167 | 5.510 | 5.523 |

### 2.3 Talep tahmini

| Ölçü | Değer |
|---|---|
| Geçmiş veri | 66.024 satır · 179 gün · 289 aktif hat · 18 transfer merkezi |
| Tahmin çıktısı | 4.046 satır · 4.977.975 desi · 1.121 satır sıfır |
| Takvim çarpanları | ay sonu ×0,0198 · ay sonundan bir önceki gün ×0,6752 · ayın ilk günü ×1,2072 · normal ×1,0000 |
| WMAPE, normal hafta (15-21 Haz) | naive 0,2592 · DOW medyanı 0,2174 · bizim model 0,2174 |
| WMAPE, ay sonu haftası (30 Mar - 5 Nis) | naive 0,6972 · DOW medyanı 0,5328 · bizim model 0,4464 |

### 2.4 Final paket

| Ölçü | Değer |
|---|---|
| Çıktı | `out/Tasima-plani.xlsx` · 5.523 satır × 16 kolon · tek sayfa |
| Önceki teslimle fark | 0 farklı hücre |
| Uçtan uca süre | ~150 saniye (zaman aşımı sınırı 100 dakika) |
| Test | 592 (528 mevcut + 64 yeni entegrasyon testi) |
| Hakem ihlali | 0 |
| Beyan edilen maliyet ile hakem maliyeti farkı | 0,0000 TL |

---

## 3. A Bölümü — Problem ve Maliyet Modeli

### S1. Toplam maliyeti hangi formülle hesaplıyorsunuz?

**Kısa cevap:** Toplam Maliyet = Araç Maliyeti + SLA Cezası; Araç Maliyeti = Saatlik Kira × Kullanım Süresi + Kat Edilen Mesafe × Km Başı Maliyet; SLA Cezası = Geciken Desi × yukarı yuvarlanmış Gecikme Saati × 0,40 TL.

**Detay:** Formül şartnamedeki hâliyle uygulanır, ek bir terim veya katsayı yoktur. Mesafe kuş uçuşu değil, `sehirler_arasi_lojistik.xlsx` matrisindeki km değeridir; seyir süresi de aynı matristen, araç tipine göre okunur. Saatlik ücret Spot mu Kiralık mı olduğuna göre seçilir: örneğin Tır için spot 487,50 TL/saat ve 25 TL/km, kiralık 291,67 TL/saat ve 13 TL/km. Kullanım süresi saate yuvarlanmaz, kesirli saat olarak çarpılır.

**Kanıt:** Şartname Bölüm 2 ve Bölüm 5; `src/simulator.py` içindeki `trace_vehicle` maliyet yeniden hesabı; ücretler `datas/Araç_Kapasite_Maliyet_Saat.xlsx`.

### S2. "Kullanım süresi" tam olarak ne zaman başlar, ne zaman biter?

**Kısa cevap:** İlk yükleme elleçlemesinin başladığı andan son indirme elleçlemesinin bittiği ana kadar geçen kesintisiz penceredir; bekleme ve ara durak elleçlemeleri dâhildir.

**Detay:** Jürinin işlenmiş örneği kodda birebir üretilir: 10.000 desilik yük, 5 saatlik hat, spot Tır → 100 dakika çıkış elleçlemesi + 300 dakika yol + 100 dakika varış elleçlemesi = 500 dakika. Ayrı bir örnek olan İstanbul-Yalova seferi (10.000 desi, 0,92 saat seyir → 100 + 56 + 100 = 256 dakika, 60 km) de testle çivilenmiştir: 487,50 × 256/60 + 25 × 60 = 3.580 TL. Çok duraklı bir milk-run zincirinde pencere yine tektir: ilk yüklemeden son indirmeye kadar her şey içeridedir ve fiziksel araç yalnız **bir kez** ücretlendirilir.

**Kanıt:** Jüri Q&A — OptiVision Soru 3, HititRoute Soru 12, Budapeşte Soru 5, HİB LOGİ Soru 9. `src/simulator.py` `usage_hours` hesabı; `tests/test_simulator_cost.py`.

**Tuzak:** "Sadece seyir süresi" demek doğrudan yanlış cevaptır ve jürinin en çok tekrarladığı netleştirmedir.

### S3. Elleçleme süresini nasıl hesaplıyorsunuz? Yükleme ve indirme ayrı mı?

**Kısa cevap:** Desi × 0,01 dakika, yukarı tam dakikaya yuvarlanır; yükleme ve indirme **ayrı ayrı** uygulanır.

**Detay:** Tam yüklü bir Tır için ⌈22.400 × 0,01⌉ = 224 dakika, 10.000 desi için 100 dakika, 5.000 desi için 50 dakika. Zaman çizelgesi bacağın **toplam** desisi üzerinden tek bir toplu işlemle kurulur; plan dosyasındaki satır bazlı "Çıkış Elleçleme süresi" ve "Varış elleçleme süresi" kolonları ise o tek işlemin talep bazlı beyanıdır. Hakem simülatörü tam olarak bu satır bazlı değeri bekler, dolayısıyla beyan ile denetim aynı tanımı kullanır.

**Kanıt:** Şartname EK KISIT 1; `src/timeutil.py` `HANDLING_MIN_PER_DESI = 0,01` ve `handling_minutes`; `src/simulator.py` satır bazlı elleçleme denetimi.

**Tuzak:** Satır bazlı elleçleme kolonlarını toplayıp bacağın süresini bulmaya çalışan bir jüri üyesi çıkarsa fark oluşur (örneğin 1 + 6 desilik iki kalem: bacak ⌈0,07⌉ = 1 dakika, satırlar 1 + 1 = 2 dakika). Bu tutarsızlık değil, şartnamenin "Yarışmacılar aynı araç içerisindeki desiyi bölerek bir kısmını daha erken elleçlenmiş kabul edemezler" kuralının doğrudan sonucudur; ve hakem de aynı iki tanımı ayrı ayrı kullanır.

### S4. Aynı araçtaki farklı talepler farklı zamanlarda mı elleçleniyor?

**Kısa cevap:** Hayır. Bir araçtaki tüm gönderiler için elleçleme aynı anda başlar, aynı anda biter; o durakta inen her yük aynı varış zamanını alır.

**Detay:** Bir durakta inen kümenin toplam desisinden tek bir süre hesaplanır ve o kümedeki her parça aynı `unload_end` anını paylaşır; SLA cezaları da bu tek ana göre hesaplanır. Milk-run zincirlerinde gemide kalıp devam eden yük ara merkezde **hiç** elleçlenmez — yalnız o durakta inen desi elleçlenir.

**Kanıt:** Şartname EK KISIT 1; `src/milkrun.py` durak zaman çizelgesi; `src/chain.py` `analyze_leg_flows` yüklenen/taşınan/indirilen ayrımı.

### S5. SLA saati nerede başlar, nerede durur?

**Kısa cevap:** Orijinal çıkış merkezindeki talep tamamlanma anında (09:00 veya 17:00) başlar; orijinal varış merkezindeki **indirme elleçlemesinin bitiş anında** durur.

**Detay:** Vade `ready + 24 × sla_days` saattir; veri setindeki 306 hattın 204'ü 1 günlük, 102'si 2 günlük SLA'ya sahiptir. Ara merkezdeki indirme, bekleme ve yeniden yükleme sürelerinin hepsi saat işlerken geçer — jüri bunu açıkça söylemiştir. Bu yüzden ceza yalnız `leg.dest == part.dest` olan, yani nihai varıştaki indirmede yazılır; konsolidasyon veya milk-run ara durağında ceza yazılmaz.

**Kanıt:** Şartname EK KISIT 2; jüri Q&A — OptiVision Soru 2, HititRoute Soru 14, ROTAI Soru 1. `src/schedule.py` ceza koşulu; `src/simulator.py` teslim bütünlüğü ve SLA hesabı.

### S6. Gecikme yuvarlaması nasıl yapılıyor? 1 dakikalık gecikme ne kadar ceza?

**Kısa cevap:** Gecikme bir üst tam saate yuvarlanır; 1 dakikalık gecikme tam 1 saatlik ceza doğurur.

**Detay:** Jürinin verdiği iki örnek de kodda birebir üretilir: 2 saat 20 dakika gecikme 3 saat sayılır; SLA vadesi 09:00 olan bir yükün elleçlemesi 09:01'de biterse 1 saatlik ceza uygulanır. Şartnamenin 6.000 desi × 1 saat × 0,40 = 2.400 TL örneği bir birim testiyle sabitlenmiştir.

**Kanıt:** Şartname EK KISIT 2; jüri Q&A — Astra Bölüm 3 yuvarlama hassasiyeti. `src/timeutil.py` `late_hours`; `tests/test_simulator_full.py` SLA örnek testi.

### S7. Süre yuvarlamalarını nerede yapıyorsunuz? Kayan nokta hatası riski var mı?

**Kısa cevap:** Tüm yuvarlama tek bir modülden geçer ve kayan nokta artefaktına karşı korumalıdır.

**Detay:** `_ceil_guarded(x) = math.ceil(round(x, 6))` — önce 6 haneye yuvarlanır, sonra yukarı alınır. Tehlike, çarpımın tam sayının hemen **üstüne** taşmasıdır: hat matrisindeki Mersin→Denizli ve Denizli→Mersin Kamyonet bacakları 8,05 saattir ve Python'da `8.05 * 60` tam 483 değil **483,00000000000006** verir; korumasız `math.ceil` bunu 484 dakikaya çıkarır, koruma ile 483 kalır. Veri setinde bu durumdaki hat-araç çifti tam olarak 2 tanedir. Jürinin verdiği İstanbul-Yalova örneği (0,92 saat = 55,2 dakika → 56 dakika) doğrudan bu fonksiyondan çıkar. Planlayıcı, çizelgeleyici ve hakem simülatörü aynı kaynağı kullanır; hiçbir yerde ikinci bir yuvarlama aritmetiği yoktur.

**Kanıt:** `src/timeutil.py` `travel_minutes`, `handling_minutes`, `late_hours`; jüri ek mesajı madde 4; `tests/test_timeutil.py`.

### S8. Gece yarısını aşan elleçlemeyi hangi günün kapasitesinden düşüyorsunuz?

**Kısa cevap:** Süreye orantılı olarak iki güne bölüyoruz — jürinin verdiği 3.000 / 7.000 örneği birebir çıkıyor.

**Detay:** Elleçleme defteri, işlemi gece yarısı sınırlarında dilimler ve her güne `desi × o gündeki dakika / toplam dakika` kadar yazar. 29.06 saat 23:30'da başlayan 10.000 desilik işlem 100 dakika sürer; 30 dakikası 29.06'ya (3.000 desi), 70 dakikası 30.06'ya (7.000 desi) düşer ve işlem 30.06 saat 01:10'da biter. Bu davranış bir birim testiyle çivilenmiştir.

**Kanıt:** Jüri Q&A — Astra Bölüm 2, ByteSis; jüri ek mesajı madde 5. `src/ledger.py` `HandlingLedger.add`; `tests/test_ledger.py`.

### S9. Mesafeleri kuş uçuşu mu hesaplıyorsunuz?

**Kısa cevap:** Hayır. Km ve seyir süresi doğrudan hat matrisinden okunuyor.

**Detay:** Şartname bunu açıkça söylüyor: "Bu aşamada kuş uçuşu ile kilometre hesabı yapmanızı beklemiyoruz. Kilometreyi direkt bu exceldeki bilgilere uygun kullanacaksınız." Matris tam doludur: 18 merkez × 17 = 306 yönlü hat, hepsi mevcut. Veri yükleyici hat sayısının tam 306 ve merkez sayısının tam 18 olmasını zorunlu kılar; sapma hâlinde süreç hata ile durur.

**Kanıt:** Şartname Bölüm 5; `src/data.py` `_load_lanes` doğrulaması.

---

## 4. B Bölümü — Talep Tahmini

### S10. Tahmin modeliniz tek cümleyle nedir?

**Kısa cevap:** Haftagünü medyan tabanı çarpı geçmişten kalibre edilmiş takvim çarpanı.

**Detay:** Her (çıkış, varış, saat dilimi, haftagünü) hücresi için hedef tarihten **kesin önceki** son 4 aynı-haftagünü gözlemin medyanı taban olur; bu taban günün takvim rolüne (ay sonu / ay sonundan bir önceki gün / ayın ilk günü / normal) karşılık gelen çarpanla çarpılır. Çıktı 4.046 satır ve 4.977.975 desidir. Model iki güçlü olguyu hedefler: haftagünü mevsimselliği ve ay sonu çöküşü.

**Kanıt:** `src/backtest.py` `dow_median`; `src/forecast.py` `calendar_multipliers` ve `forecast_horizon`.

### S11. Neden makine öğrenmesi kullanmadınız?

**Kısa cevap:** Veri, tek bir güçlü mevsimsellik (haftagünü) ve tek bir takvim olayı (ay sonu) tarafından yönetiliyor; robust medyan bu ikisini yakalıyor ve backtest'te daha karmaşık bir modele ihtiyaç göstermiyor.

**Detay:** Bilerek yapmadıklarımız: aykırı değer temizleme, log dönüşümü, ölçekleme, yumuşatma, interpolasyon, trend/mevsim ayrıştırma ve harici ML kütüphanesi (sklearn, statsmodels, Prophet, ARIMA yok). Gerekçe ölçülebilir: normal haftada model düz haftagünü medyanıyla **birebir aynı** WMAPE veriyor (0,2174), yani fazladan karmaşıklık için yer yok; ay sonu haftasında ise kazanç tamamen takvim katmanından geliyor (0,5328 → 0,4464). Doğrulanamayan karmaşıklık eklemektense doğrulanabilir bir modeli savunuyoruz. Ayrıca final aşamasında bu modül hiç çalıştırılmıyor, dolayısıyla çalışma süresi bütçesinden de hiç harcamıyor.

**Kanıt:** stage-2-step-3 README Bölüm 1.1 "kasıtlı olarak yapmadıklarımız"; frozen backtest WMAPE tablosu; TEKNIK_GEREKSINIMLER Bölüm 2.

**Tuzak:** "ML denemedik" demek yerine "ML'e ihtiyaç olmadığını ölçtük" demek gerekiyor. Ölçüm, normal haftadaki birebir eşitlik.

### S12. Takvim çarpanlarını nereden ölçtünüz?

**Kısa cevap:** Geçmişteki her takvim olayı günü için "o günün gerçekleşen toplamı / aynı hücrelerin sızıntısız taban toplamı" oranını hesaplayıp rol başına bu oranların medyanını aldık.

**Detay:** Tabana bölmek, ay sonu etkisini haftagünü etkisinden ayırır — 30 Haziran bir salıdır ve taban zaten salı hacmini yakalar, çarpan yalnız "ay sonu olması"nı ekler. Geçmişte 16 olay günü taranır; geçmişi boş olduğu için 1 Ocak atlanır, rol başına beşer oran kalır. Rol başına en az iki geçerli oran yoksa güvenli 1,0 değerine düşülür, yani tek gözlemden çarpan üretilmez.

**Kanıt:** `src/forecast.py` `calendar_multipliers`, `MIN_CALENDAR_SAMPLES = 2`; ölçülen çarpanlar `docs/figures/chart_data.json`.

### S13. Ay sonu çarpanı 0,0198 — bu tek bir aykırı günden mi geliyor?

**Kısa cevap:** Hayır, beş bağımsız ay sonundan ve medyanla geliyor; beş oranın hepsi 0,0088 ile 0,0254 arasında.

**Detay:** Ölçülen ham oranlar 31.01 için 0,019766, 28.02 için 0,025397, 31.03 için 0,019441, 30.04 için 0,008835 ve 31.05 için 0,021036; medyan 0,019766. Yani sinyal aykırı değil, sistematik: ayın son günü beş ayın beşinde de normal bir günün yaklaşık %2'sine iniyor, en düşük gözlem 2.010 desi. 30 Haziran tahmin ufkunun içinde olduğu için bu tek gün tahmin puanını domine edebilecek büyüklükte — o günü normal bir salı sayan bir model tek başına yaklaşık 1,1 milyon desi hata üretirdi.

**Kanıt:** `docs/figures/chart_data.json` `history_daily` ve `calendar_multipliers` blokları; stage-2-step-3 README Bölüm 1.2.

### S14. Neden medyan, neden ortalama değil?

**Kısa cevap:** Ortalama tek bir aykırı günden kalıcı olarak bozuluyor; medyan bozulmuyor ve farkı ölçtük.

**Detay:** "Ayın ilk günü" rolünün ham oranları 2,928668 (1 Şubat), 1,207219 (1 Mart), 1,056397 (1 Nisan), 0,089875 (1 Mayıs — resmî tatil) ve 1,573929 (1 Haziran). Ortalaması 1,371, medyanı 1,207. Ortalama hem 2,93'lük zıplamadan hem 0,09'luk tatil çöküşünden aynı anda bozulurken medyan ikisini de dışarıda bırakıyor. Aynı ilke taban modelde de geçerli: son dört aynı-haftagünü gözlemin medyanı alınıyor, ortalaması değil.

**Kanıt:** `src/forecast.py` çarpan döngüsü; `src/backtest.py` `dow_median`.

### S15. Sızıntı (leakage) olmadığını nasıl kanıtlıyorsunuz?

**Kısa cevap:** Üç ayrı katmanda yapısal olarak engelledik; biri sızıntı görürse çalışmayı hata ile durduruyor.

**Detay:** Birincisi, `forecast_horizon` girdide tahmin başlangıcı veya sonrasına ait tek bir gözlem bile bulursa `ValueError` fırlatıyor — sessizce devam etmiyor. İkincisi, takvim çarpanı kalibrasyonunda her olay günü için taban yalnız `tarih < hedef` verisiyle hesaplanıyor ve bu davranış, taban fonksiyonu bir "sızıntı bekçisi" ile değiştirilerek test ediliyor. Üçüncüsü, raporlanan WMAPE değerleri dondurulmuş (frozen) backtest ile üretiliyor: eğitim verisi tek bir kesim tarihinde kesiliyor, ufuk içinde yeniden eğitim yapılmıyor ve modele gerçekleşen etiketin bulunmadığı bir hedef tablosu veriliyor.

**Kanıt:** `src/forecast.py` cutoff kontrolü ve sızıntısız kalibrasyon döngüsü; `src/frozen_backtest.py` `run_frozen`; `tests/test_forecast.py` sızıntı bekçisi testi.

### S16. WMAPE sonuçlarınız ne? Referans modele göre ne kadar iyisiniz?

**Kısa cevap:** Normal haftada 0,2174, ay sonu haftasında 0,4464. Naive "geçen hafta" modeline göre sırasıyla %16,1 ve %36,0 daha iyi.

**Detay:** Normal haftada (15-21 Haziran) naive 0,2592, düz haftagünü medyanı 0,2174, bizim model 0,2174. İki değerin birebir aynı olması tesadüf değil: o pencerede takvim rolü olan gün yok, çarpan 1,0 ve model **gereksiz yere müdahale etmiyor**. Ay sonu haftasında (30 Mart - 5 Nisan) naive 0,6972, düz medyan 0,5328, bizim model 0,4464 — takvim katmanı hatayı %16,2 azaltıyor. Yani katman zarar vermeden, yalnız gerektiğinde kazandırıyor.

**Kanıt:** `docs/figures/chart_data.json` `backtest` bloğu; `src/frozen_backtest.py`.

### S17. Ay sonu haftasında bias +%28,3 diyorsunuz. Bu bir kusur değil mi?

**Kısa cevap:** Açık bir kalem olarak kendimiz raporladık; ama araştırdığımızda hedefin sahte olduğunu ölçtük — teslim modelinin dışsal örneklemde bias'ı −0,0573.

**Detay:** +%28,3, 29 Mart kesim tarihinde "ayın ilk günü" çarpanının yalnız iki örnekle uydurulmasının artefaktı. Bu bias'ı hedefleyen dört ayrı düzeltme adayını denedik (saat dilimi bazlı çarpanlar, ikinci gün çarpanı, toparlanma kalibrasyonu, taban kalibrasyonu) ve **dördü de dışsal örneklemde başarısız oldu**. Bir çıkarma-bir (leave-one-out) değerlendirmesinde teslim modelinin bias'ı −0,0573, yani neredeyse sıfır. Bu yüzden düzeltme yapmadık; sahte bir hedefe göre modeli eğmek gerçek performansı kötüleştirirdi.

**Kanıt:** stage-2-step-3 README Bölüm 7, "ölçülmüş çıkmaz sokaklar" tablosu.

**Tuzak:** Bu soruyu savunmacı karşılamak yanlış olur. Doğru tavır: "biz kendimiz açık kalem olarak yazdık, sonra araştırdık, sonuç şu."

### S18. Tahmin edilen desi 0 çıkan 1.121 satırı neden dosyada tutuyorsunuz?

**Kısa cevap:** Doğrudan jüri kuralı gereği — "0,5'in altındaki satırlar da sunulmalı".

**Detay:** Çıktı, aktif hat × gün × iki saat dilimi gridinin tamamını kapsar: 289 × 7 × 2 = 4.046 satır. Bunların 1.121'i (%27,7) sıfırdır ve silinmez. Grid tamlığı ayrı bir doğrulayıcı tarafından denetlenir: eksik veya fazla hücre bulunursa şema hatası verilir. Sıfır satırlar tahmin dosyasında kalır ama optimizasyona girmez — sıfır desi için araç çıkarılmaz.

**Kanıt:** Jüri Q&A — OpAI Soru 5. `src/forecast.py` `to_forecast_frame`; `src/schemas.py` `validate_forecast_grid`.

### S19. Geçmişte hiç görülmemiş bir hat için tahmin üretiyor musunuz?

**Kısa cevap:** Hayır. Hat evreni yalnız geçmiş veriden türetiliyor — 289 aktif çift.

**Detay:** Jüri iki ayrı takıma aynı cevabı verdi: "veride hiç talep görülmemiş bir merkez ikilisi için talep tahmin etmemelisiniz." Kodda hat listesi geçmiş talepten çıkarılır; dondurulmuş backtest'te ise evren yalnız kesim tarihi öncesi eğitim geçmişinden türetilir, yani ufukta ilk kez görünen bir hat çifti evrene giremez. Bu davranış ayrı bir testle sabitlenmiştir. Not: matriste 306 hat var, veride 289 aktif hat var; fark Kocaeli'nin hiç varış merkezi olmamasından kaynaklanıyor.

**Kanıt:** Jüri Q&A — HititRoute Soru 3, Budapeşte Soru 6. `src/forecast.py` hat evreni türetimi; `src/frozen_backtest.py`.

### S20. Final aşamasında tahmin modülünüz çalışıyor mu?

**Kısa cevap:** Hayır, hiç çağrılmıyor — TEKNIK_GEREKSINIMLER Bölüm 2 bunu istemiyor ve biz de import grafiğinden ulaşılamaz hâle getirdik.

**Detay:** `main.py`'nin import listesinde `src.forecast`, `src.backtest` ve `src.frozen_backtest` yoktur ve bu modüllere hiçbir yoldan ulaşılamaz. İkinci bir davranışsal kanıt: statik veri yükleyici `with_demand=False` ile çağrılıyor, yani tahminin geçmiş veri kaynağı olan 66.024 satırlık tablo hiç açılmıyor. Bunun ölçülen etkisi 8,20 saniyeden 0,08 saniyeye düşen bir yükleme süresidir. Ayrıca `Talep-tahmini.xlsx` yazılmıyor; tek çıktı taşıma planıdır.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 2; `final-teslim/main.py` import listesi; `DEGISIKLIKLER.md` fark #1 ve #8; `KONTROL_LISTESI.md` import grafiği taraması.

---

## 5. C Bölümü — Stage 0 Temel Plan

### S21. Stage 0 planı hangi sırayla kuruyor?

**Kısa cevap:** Önce tır ziyaret bütçesini rezerve ediyor, sonra her gün için kiralık filoyu dolduruyor, ardından spot araç karmasını tam sayımla seçiyor, en sonda kalan yükü iki boşaltma gününde sıfırlıyor.

**Detay:** Sıra kritiktir. Kiralık araçlar her gün nasılsa yola çıkacağı için önce onlar doldurulur — marjinal desi maliyetleri çok düşüktür. Sonra kalan yük için her (hat, gün) çifti değerlendirilir. Ufuk bitince eklenen iki boşaltma gününde havuzda kalan her şey ertelemesiz taşınır ve `assert leftover == 0` ile havuzun tamamen boşaldığı doğrulanır. Sonuç: 1.269 bacak (126 kiralık + 1.143 spot), 3.167 plan satırı, 16.480.959,77 TL, 0 ihlal.

**Kanıt:** `src/optimize.py` `build_plan`; `tests/test_optimize.py` altın değer testi.

### S22. Kiralık araçları neden boşken bile çıkarıyorsunuz? Bedeli ne?

**Kısa cevap:** Şartname zorunlu kılıyor; ölçülen bedel 104.545,11 TL.

**Detay:** 9 günün her birinde tam 14 kiralık bacak çıkarılır, toplam 126 bacak; bunların 35'i boştur (28'i iki boşaltma gününde, 7'si ufuk günlerinde). Boş bacaklar plan dosyasında Talep ID hücresi boş ve Taşınan Desi 0 olarak yazılır; şema doğrulayıcı bu istisnayı yalnız Araç Tipi "Kiralık" iken kabul eder, boş bir Spot bacağı reddeder. Kiralık filo bir yük değil bir kaldıraçtır: 126 bacak toplam 459.936,67 TL'ye — nihai planın 8.616.944,73 TL'lik araç maliyetinin %5,34'ü, Stage 0 temel planının araç maliyetinin ise %2,97'si — 867.524 desi, yani toplam hacmin %17,4'ünü taşır.

**Kanıt:** Şartname Bölüm 3; jüri ek mesajı. `src/optimize.py` `_fill_rented`; `src/schemas.py` boş kiralık istisnası.

### S23. Kiralık araçları neden her zaman spottan önce dolduruyorsunuz?

**Kısa cevap:** Kiralık aracın km ve seyir maliyeti batıktır; yalnız elleçleme süresi yükle değişir, dolayısıyla marjinal desi maliyeti 0,07-0,10 TL aralığındadır.

**Detay:** Ölçülen marjinal maliyetler kiralık Tır için 0,09722 TL/desi, kiralık Kamyon için 0,06944 TL/desi. Aynı desiyi spotta taşımak en ucuz hâlinde (Kamyonet) 0,06597 TL/desi marjinal **artı** aracın sabit maliyeti demektir. Bu yüzden kiralığı doldurmak her koşulda kazançlıdır ve algoritma hattın havuzunu aciliyet sırasına (vade, hazır olma anı, kimlik) dizip kiralık araçları önce doldurur.

**Kanıt:** `src/optimize.py` `_fill_rented` ve modül başlığındaki marjinal maliyet notu; `datas/Araç_Kapasite_Maliyet_Saat.xlsx`.

### S24. Balıkesir ve Tekirdağ'ın tır kapasitesi zorunlu kiralık tırlara ancak yetiyor. Nasıl aşmıyorsunuz?

**Kısa cevap:** Kiralık tırları planlamaya başlamadan **önce** bütçeden düşerek. Bu rezervasyonu kaldırdığımızda plan 12 tır kapasitesi ihlali veriyor.

**Detay:** Planlama başlamadan tüm günler için her kiralık Tır'ın hem çıkış hem varış ziyareti bütçeden düşülür; kalkış anı gerçek yüke değil **tam kapasiteye** göre sabitlenir, böylece varış günü de yükten bağımsız olur ve rezervasyon doğru güne yazılır. Ölçülen sonuç: Balıkesir kapasite 1 → kalan 0; Tekirdağ kapasite 2 → kalan 0; Yalova kapasite 4 → kalan 1; İstanbul kapasite 10 → kalan 2. Karşı-olgu ölçümü nettir: rezervasyon kaldırılırsa Balıkesir 2>1, Tekirdağ 4>2, Manisa 5>4 dâhil 12 ihlal doğar.

**Kanıt:** `src/optimize.py` `_seed_context`; `datas/tir_kapasiteleri v2.xlsx` (Balıkesir 0→1, Tekirdağ 1→2 güncellemesi jüriden gelmiştir).

**Tuzak:** Bu soru aslında jürinin kendi çelişki sorusudur (OptiVision Soru 1, ROTAI Soru 3, Budapeşte Soru 2, OpAI Soru 2). Cevap "v2 dosyasını kullanıyoruz **ve** kiralık tırları önceden rezerve ediyoruz" olmalı; ikisinden biri eksik kalırsa çelişki çözülmez.

### S25. Bir (hat, gün) için kaç aday üretiyorsunuz? Bu tam sayım mı?

**Kısa cevap:** Tam sayım. Ufuk boyunca 39.598 araç karması numaralandırıldı, budamadan sonra 6.847'si (%17,3) kesin fiyatlandırıldı; tüm arama 0,46 saniye sürüyor.

**Detay:** Dört iç içe döngü tüm araç sayısı karmalarını tarar. Üst sınırlar kapasiteden türetilir: Tır = ⌈desi/22.400⌉+1 (en fazla 3), Kamyon = ⌈desi/12.000⌉+1, Hafif Kamyon 2, Kamyonet 1. Ölçülen uçlar: en yoğun hat-gün olan 43.854 desi için 143 aday, küçük bir hat-gün için 17 aday, ortalama 21,0. Kabul kriteri araç maliyeti + SLA cezası + erteleme maliyetidir ve yeni aday ancak **kesin** olarak daha ucuzsa kazanır; beraberlikte en düşük sayımlı karma korunur, bu da determinizmi garanti eder.

**Kanıt:** `src/candidates.py` `plan_lane_day`, `_count_bounds`; ölçülen çağrı sayıları 1.886 `plan_lane_day` ve 9.007 `plan_vehicle`.

### S26. Spot Tır eşiği 12.000 desi. Bu keyfi bir sayı mı?

**Kısa cevap:** Hayır, Kamyon kapasitesine eşit ve ölçerek doğrulanmış: eşiğin altında tek Tır hiçbir hatta tek Kamyondan ucuz çıkmıyor.

**Detay:** 306 hattın tamamında ve desi ∈ {1, 1.000, 5.600, 7.200, 12.000} için karşılaştırma yaptık: 1.530 kontrolün hiçbirinde Tır ucuz çıkmadı. Sebep üç katlı — Tır km başına daha pahalı (25 TL vs 21 TL), saatlik daha pahalı (487,50 TL vs 318,25 TL) ve 306 hattın 306'sında Kamyondan yavaş. Eşiğin üstünde ise 12.000-22.400 desi aralığında tek Tır iki Kamyondan 1.224 kontrolün 1.220'sinde ucuz. Yani eşik arama uzayını küçültüyor ama optimalliği bozmuyor.

**Kanıt:** `src/optimize.py` `TIR_MIN_DESI = 12000`; ölçüm stage-2-step-3 kabul raporları.

### S27. Tır ziyaretlerini hatlara nasıl paylaştırıyorsunuz? İlk gelen mi alıyor?

**Kısa cevap:** Hayır — azalan getiriyle. Her turda tüm hatlar taranır, bir tır daha eklemenin kazancı hesaplanır ve tur içindeki **en yüksek kazançlı tek hat** kabul edilir.

**Detay:** Kabul edilmeden önce o tırın hem çıkış hem varış merkezindeki bütçesi kesin tarihlerle kontrol edilir. Ölçüm: 7 gün boyunca 1.751 hat-gün tarandı, 45'i tır-uygun bulundu, 28'inde ilk tırın getirisi pozitifti (en yüksek 02.07 İstanbul-Mersin 10.058,50 TL), ancak bütçe kısıtı nedeniyle yalnız 9 tır tahsis edildi. Reddedilenler tipik olarak kapasitesi 0 olan merkezlere veya kiralıklarca tüketilmiş merkezlere gidiyordu.

**Kanıt:** `src/optimize.py` `_allocate_tir`.

### S28. Yükü ertelemek (carry-over) gerçekten kazandırıyor mu?

**Kısa cevap:** Evet, net 8.473.648,91 TL. Aynı boru hattını erteleme kapalıyken çalıştırıp ölçtük.

**Detay:** Erteleme tamamen kapatıldığında Stage 0 çıktısı 1.943 bacak ve 24.954.608,68 TL (SLA cezası 0). Açıkken 1.269 bacak ve 16.480.959,77 TL. Yani 1.020.367,20 TL SLA cezası ödeyerek 9.494.016,11 TL araç maliyeti tasarruf ediliyor; net kazanç −%33,96. Her iki koşuda da ihlal sayısı 0. Erteleme keyfî değil, üç sert kuralla sınırlı: hat-gün başına en fazla 5.600 desi (bir Kamyonet kapasitesi), boşaltma gününde yasak, ve bir parça en fazla **bir kez** ertelenebilir. Ertelemenin bedeli de aday değerlendirmesinin içinde fiyatlanır — yarınki gerçek SLA cezası artı yarınki taşıma bedeli.

**Kanıt:** `src/candidates.py` `_carry_cost`, `MAX_CARRY_DESI = 5600`; şartname EK KISIT 2 "gönderileri bekletebilirsiniz".

### S29. Boşaltma günleri (flush days) neden var?

**Kısa cevap:** Jüri "5 Temmuz'da tahminlenen talepleri 7 Temmuz'da teslim edebilirsiniz" dediği için; ufka iki gün ekliyoruz.

**Detay:** Ufuk bittikten sonraki iki günde kiralık filo yine çıkar, kalan yük gün başından itibaren ertelemesiz taşınır ve doğan SLA cezası tam olarak fiyatlandırılır. Ölçülen davranış: 06.07 ve 07.07'de 14'er kiralık bacak çıktı, hepsi boş, hiç spot bacak gerekmedi — kiralıklar 05.07'den sarkan yükü zaten yutmuştu.

**Kanıt:** Jüri Q&A — HititRoute Soru 4, ROTAI Soru 5, Budapeşte Soru 1, OpAI Soru 6. `src/optimize.py` `flush_days = 2`, `_flush_day`.

### S30. Elleçleme kapasitesini Stage 0'da nerede kontrol ediyorsunuz?

**Kısa cevap:** Stage 0 modellemiyor; kısıt çizelgeleme katmanında uygulanıyor ve nihai denetim hakem simülatöründe.

**Detay:** Bu bilinçli bir katman ayrımıdır. Çizelgeleyici, aşan (merkez, gün) çiftlerinde aşımı besleyen **en küçük** spot yükü bütün olarak ertesi günün 00:00'ına kaydırır; kullanım süresi korunduğu için araç maliyeti değişmez, yalnız SLA cezası doğar. Bu, şartnamenin "kapasiteyi aşma durumunda yükleri bekletip ertesi gün göndermeniz beklenmektedir" kuralının birebir karşılığıdır. Ölçülen etki: 11 kaydırma, hepsi Denizli'de (kapasite 36.868,61 — 18 merkezin en küçüğü); araç maliyeti değişmedi, SLA cezası 1.017.967,60 TL'den 1.020.367,20 TL'ye çıktı, yani **+2.399,60 TL**. Düzeltme kapatıldığında hakem 1 elleçleme ihlali yazar (Denizli 02.07.2026: 38.449 > 36.869); açıkken **sıfır** ihlal vardır.

**Kanıt:** Şartname Bölüm 4; `src/schedule.py` `_fix_handling`; `src/ledger.py` `HandlingLedger`.

---

## 6. D Bölümü — Stage 1, 2 ve 3

### S31. Stage 1 "aynı-hat onarımı" tam olarak ne yapıyor?

**Kısa cevap:** Aynı hat üzerindeki düşük dolulukta bir spot aracın **tüm** yükünü aynı hattaki mevcut bir araca taşıyor ve o aracı plandan siliyor.

**Detay:** Hiçbir aracın hattı değişmez, hiçbir yeni araç yaratılmaz, hiçbir talep bölünmez. Vericiler doluluk oranına göre artan sırada denenir — en boş araç, yani km ücretini en verimsiz kullanan araç ilk elden çıkarılmaya çalışılır. Ölçülen sonuç: 1.003 verici değerlendirildi, 177 hamle kabul edildi, 394 kalem ve 59.852 desi taşındı, 177 spot araç silindi. Plan 1.269 bacaktan 1.092 bacağa indi ve toplam maliyet 1.800.774,93 TL düştü. Süre 12,6-13,4 saniye.

**Kanıt:** `src/repair.py` `repair_same_lane`, `run_same_lane_stage`.

### S32. Stage 1'de aday üretimi kapsamlı mı, yoksa ilk uyanı mı alıyorsunuz?

**Kısa cevap:** İlk uyanı almıyoruz. Her verici için aynı hattaki **tüm** uygun alıcılar taranıyor ve en çok tasarruf ettiren seçiliyor.

**Detay:** 1.003 verici için toplam 4.035 (verici, alıcı) çifti incelendi — verici başına ortalama 4,02 aday. Bunların 3.792'si (%94,0) maliyet, kapasite veya kiralık-gün kapılarında düştü; 243'ü tam defter denemesine geldi, 4'ü orada reddedildi, 239 geçerli aday kaldı ve 177'si uygulandı. Kabul için üç kapı var: yerel maliyet farkı **kesin negatif** olmalı, hamle uygulanmış planın tamamı elleçleme ve tır defterlerine karşı yeniden doğrulanmalı, ve aşama sonunda hakem simülatörü ile ölçülen küresel tasarruf en az 1,00 TL olmalı.

**Kanıt:** `src/repair.py` `_receiver_proposal`, `_trial_ledgers_valid`; kabul raporu 2026-07-24.

### S33. Bir hamlenin plandaki uzak bir transfer merkezini taşırmadığını nasıl garanti ediyorsunuz?

**Kısa cevap:** Her aday için hamle uygulanmış planın **tamamı** için defterleri sıfırdan yeniden kuruyoruz — yalnız değişen iki bacağı değil.

**Detay:** Kapasiteler (merkez, gün) düzeyinde küresel kaynaklardır; yerel bir hamle uzaktaki bir merkezi taşırabilir. Bunun gerçekten çalıştığının sert kanıtı şudur: onarımı ham, yani elleçleme düzeltmesinden geçmemiş bir plana uyguladığımızda 535 denemenin 535'i de reddedildi ve 0 hamle üretildi. Düzeltilmiş temel planla aynı kod 177 hamle üretiyor.

**Kanıt:** `src/repair.py` `_trial_ledgers_valid`; `tests/test_same_lane_repair.py` ilgisiz bacak testleri.

### S34. Milk-run neden en fazla 4 durak? Şartnamede böyle bir sınır var mı?

**Kısa cevap:** Şartnamede ve Q&A'da durak sayısına **hiçbir** sınır yok. 4, ölçülmüş bir mühendislik takasıdır.

**Detay:** Jüri, çok duraklı uğramaya spot araçlar için açıkça izin veriyor ve üst sınır sorulduğunda "kısıtlamalar dikkate alınarak sınırsız sefer yapabilirsiniz" diyor. Bizim sınırımızın gerekçesi ölçüm: en fazla 3 durakla toplam 11.519.240,35 TL, 4 durakla 11.313.338,29 TL — 205.902,07 TL fark. 5 durak ise bu kaba-kuvvet sayıcıyla uygulanabilir değil: 14.913.000 varyant demek, denedik ve yaklaşık 13,5 dakika CPU ile 1,3 GB bellek sonrasında sonuç alamadık. Bağlayıcı fiziksel sınır zaten kapasite: zincirler Tır kullanmadığı için bir rota en fazla 12.000 desi taşıyabilir ve uygun bir kaynak bacak ortalama 4.128 desi. Bu yüzden dörtlü kombinasyonların yalnız %32'si sığıyor.

**Kanıt:** Jüri Q&A — OpAI Soru 11.1, NEURON-LOG Soru 3, şartname Bölüm ÇÖZÜM. `src/milkrun.py` `MAX_CHAIN_STOPS = 4` ve satır içi gerekçe.

### S35. Milk-run zincirlerinde neden Tır yok?

**Kısa cevap:** Tır ziyaret kapasitesi kıt bir kaynak — 18 merkezin 7'sinde sıfır — ve çok duraklı bir tır her durakta ayrı ziyaret tüketirdi. Üstelik ölçtük: Tır'ı zincire katmak 18.100 TL daha kötü sonuç veriyor.

**Detay:** Kural engeli yok; yasak yalnız kiralıkta. Ama Kamyon aynı 12.000 desi kapasitede Tır'ı her koşulda eziyor (318,25 TL/saat vs 487,50 TL/saat). Yapılan tam yama ölçümünde kârlı Tır adaylarının %93,6'sı kapasitesi sıfır olan yedi merkez yüzünden zaten ölüyordu; net sonuç +18.100 TL daha kötüydü. Bu yüzden zincir araç tipleri Kamyonet, Hafif Kamyon ve Kamyon ile sınırlandırıldı.

**Kanıt:** Jüri Q&A — HititRoute Soru 10, Budapeşte Soru 3, HİB LOGİ Soru 7. `src/milkrun.py` `ROUTE_TYPES`; stage-2-step-3 README "ölçülmüş çıkmaz sokaklar".

### S36. Milk-run'da ara merkezde yük indirip yeniden yüklüyor musunuz?

**Kısa cevap:** Hayır. Stage 2 konsolidasyon değil, milk-run yapıyor: yük çıkışta bir kez yüklenir, her durakta yalnız o durağa ait desi iner, gemide kalan yük ara merkezde hiç elleçlenmez.

**Detay:** Bu ayrım maliyet açısından belirleyici. Jüri, konsolidasyonda elleçlemenin iki kez yapıldığını ve bunun hem süre hem kapasite olarak sayıldığını söylüyor; "gerçek operasyonda da zamanla bir yarış olmaktadır, bu nedenle bazı durumlarda konsolidasyon tercih edilememektedir" diye de ekliyor. Biz bu maliyeti hiç doğurmuyoruz. Ölçülebilir kanıt: zincirin ilk segmentinde tüm yük yüklenir, sonraki segmentlerde yüklenen kalem sayısı sıfırdır ve her segmentte yalnız o durağın kalemi iner.

**Kanıt:** Jüri Q&A — HititRoute Soru 9, HİB LOGİ Soru 6, OptiVision Soru 2. `src/chain.py` `analyze_leg_flows`; `tests/test_milkrun.py` üç duraklı akış testi.

### S37. Fiziksel araç sayısı 1.092'den 693'e nasıl düştü? Bu sayılar tutuyor mu?

**Kısa cevap:** Segment sayısı 1.092'de sabit kalıyor; değişen, bu segmentlerin tek fiziksel araca bağlanması. Kimlik kontrolü: 1.092 − (626 − 227) = 693.

**Detay:** 227 zincir kabul edildi; boyut dağılımı 127 adet 2 duraklı, 28 adet 3 duraklı, 72 adet 4 duraklı. 127×2 + 28×3 + 72×4 = 626 kaynak aracın yerini 626 segment aldı ve bunlar 227 fiziksel araca bağlandı. Araç tipi karması da tutarlı: Hafif Kamyon 11 + Kamyon 120 + Kamyonet 96 = 227. Stage 3 ise zincirlerin **şeklini hiç değiştirmeden** 28 tek-bacaklı aracın yükünü mevcut zincirlere bindirip o araçları siliyor: 693 − 28 = 665, segment 1.092 − 28 = 1.064. Bu özdeşlik yayınlanan Excel üzerinden bağımsız olarak yeniden hesaplanıp doğrulanmıştır.

**Kanıt:** `docs/figures/chart_data.json` `milkrun_metrics` ve `stages` blokları; `tests/test_milkrun.py` tam ufuk testi.

### S38. Stage 3'teki "Tier A" ne demek? Neden Tier B yok?

**Kısa cevap:** Tier A, alınan yükün varışının rotanın **zaten uğradığı** bir durak olması demek — böylece rota topolojisi hiç değişmiyor. Tier B rotayı bir durak uzatırdı ve kapsam dışı bıraktık.

**Detay:** Tier A'da zincir uzamaz, durak sayısı sınırı ve talep bölme sözleşmesi aynı kalır; kazanç, o yükü ayrı taşıyan aracın tamamen ortadan kalkmasından gelir. Tier B'yi ölçmedik değil: bağımsız bir ölçüm A+B için yaklaşık 146 bin TL gördü, yani ek yaklaşık 66 bin TL. Ama Tier B 5 duraklı rota üretiyor, en fazla 4 durak sınırını ve dokümantasyonu değiştiriyor; bu ayrı bir karar konusu olduğu için bu teslimde kapsam dışı bırakıldı ve kabul raporuna böyle kaydedildi.

**Kanıt:** Jüri Q&A — HİB LOGİ Soru 6 ("x indirilip y yüklenirse kapasiteden x+y düşülür"). `src/pickup.py`; kabul raporu 2026-07-26.

### S39. Stage 3'ün arama uzayı ne kadar? Kabul oranınız neden bu kadar düşük?

**Kısa cevap:** 135.660 çift incelendi, 56'sı kârlı çıktı, 28'i kabul edildi. Düşük oran bir kusur değil, katı fizibilite kapılarının sonucu.

**Detay:** Aritmetik açık ve doğrulanabilir: 227 çok duraklı Spot zincir hedef, 126 kiralık rota atlandı, kalan 340 tek bacaklı Spot rotanın tamamı donör havuzuna girdi. 227 zincirin toplam (uzunluk−1) değeri 399'dur ve 399 × 340 = 135.660. Bir aday ancak şu koşulları birlikte geçerse kabul edilir: yük hub'da araç indirmeyi bitirdiğinde hazır olmalı, pencerede geçtiği **her** segmentte kapasite yetmeli, varışı rotada bulunmalı, maliyet farkı kesin negatif olmalı ve birikmiş plan defterleri geçerli kalmalı. Kabul edilen 28 hamle 28 aracı sildi, 82 parça ve 65.754 desi taşıdı, 80.861,55 TL kazandırdı ve hiçbiri defter kapısında reddedilmedi.

**Kanıt:** `docs/figures/chart_data.json` `pickup_metrics`; `src/pickup.py` `_build_pickup_candidates`.

### S40. Stage 3'te bir rotaya neden yalnızca bir yük alma yapıyorsunuz?

**Kısa cevap:** Bilinçli bir muhafazakârlık — ve bunu açıkça bir tasarruf tavanı olarak kabul ediyoruz.

**Detay:** Her adayın maliyet farkı, o adayın **değişmemiş** rota üzerinde yeniden zamanlanmasıyla hesaplanır. Aynı rotaya ikinci bir yük alma kabul edilseydi, ikinci adayın fiyatı artık geçerli olmayan bir taban üzerinden hesaplanmış olurdu ve aramanın iddiası ile hakemin ölçtüğü fark arasındaki 0,000001 TL'lik uzlaşma kapısı kırılırdı. Kademeli (iteratif) bir varyant mümkündür ama bu teslimde kapsam dışıdır.

**Kanıt:** `src/pickup.py` kabul döngüsü; `run.py` `STAGE3_SAVING_TOLERANCE = 0,000001`.

### S41. Üç aşama da açgözlü. Girdi sırası değişirse sonuç değişir mi?

**Kısa cevap:** Hayır, çıktı bit-birebir aynı. Bunu karıştırılmış girdilerle test ettik.

**Detay:** Determinizm dört yerde zorlanır: giriş listesi anlamsal bir kanonik anahtarla sıralanır (bu anahtar maliyet, ceza, araç kimliği gibi türev alanları içermez), aday sıralaması tamamen anlamsal çok bileşenli anahtarlarla yapılır, tüm para aritmetiği `Decimal` üzerinden gider ve çıktı yine kanonik sıraya dizilir. Testler: Stage 1'de dört bacaklı bir planın **24 permütasyonunun tamamı** aynı imzayı ve aynı metrikleri veriyor; Stage 2'de aynı test 24 girdi permütasyonunda 11 metrik alanının tamamını karşılaştırıyor; Stage 3'te 6 farklı karıştırma tohumu birebir aynı planı üretiyor.

**Kanıt:** `tests/test_same_lane_repair.py`, `tests/test_milkrun.py`, `tests/test_pickup.py` determinizm testleri.

### S42. Bir aşama kabul edilmezse ne oluyor?

**Kısa cevap:** Önceki aşamanın planı korunuyor. Bir aşama planı asla kötüleştiremez.

**Detay:** Kabul kuralı üç koşulun hepsini ister: temel planda 0 ihlal, aday planda 0 ihlal ve hakem toplamlarından hesaplanan tasarrufun en az 1,00 TL olması. Herhangi biri sağlanmazsa seçilen plan temel plan olur. Bu mekanizmanın gerçekten çalıştığının ölçülmüş kanıtı %250 hacimli sentetik veri setidir: orada temel plan 69 elleçleme kapasitesi ihlaliyle üretildi ve Stage 1 adayı **doğru biçimde reddedildi**, temel plan korundu, kod çökmedi ve şemaya birebir uyan bir plan yazıldı.

**Kanıt:** `src/evaluation.py` `accepts_candidate`; `final-teslim/README.md` Bölüm 7 stres senaryosu.

### S43. Aşama kabul eşiği neden 1,00 TL? Bu çok gevşek değil mi?

**Kısa cevap:** Modül içi eşik gerçekten 1,00 TL, ama yayınlanan koşuda Stage 3 için 50.000 TL'lik çok daha sıkı bir kapı ve 0,000001 TL'lik bir uzlaşma toleransı var.

**Detay:** 1,00 TL eşiği yalnız "aday mı yoksa değişmemiş taban mı seçilsin" sorusunu yanıtlar; gürültü seviyesindeki farkları eler. Yayın kapıları ise şunu sorar: aramanın kendi aritmetiğiyle iddia ettiği tasarruf ile hakemin bağımsız olarak ölçtüğü fark kuruşun milyonda birine kadar aynı sayı mı? Kabul raporunda gerekçesi açıkça yazılı: 1,00 TL çok gevşek, arama tek kazara yük almaya çökse bile geçerdi.

**Kanıt:** `src/evaluation.py` `accepts_candidate`; `run.py` `STAGE3_MIN_SAVING_TL = 50000` ve `STAGE3_SAVING_TOLERANCE = 0,000001`.

### S44. Milk-run yükü geciktirir. Teslim ufkunuz uzuyor mu?

**Kısa cevap:** Hayır. Hiçbir zincir, temel plandaki yüklü bacakların en geç indirme tarihini geçemez — bu bir kod kısıtıdır ve testle sabitlenmiştir.

**Detay:** SLA cezası artıyor, evet: Stage 1'den Stage 2'ye geçişte araç maliyeti 3.757.888,96 TL düşerken SLA cezası 391.042,40 TL yükseliyor; net kazanç 3.366.846,56 TL ve ihlal sayısı 0 kalıyor. Ama teslim ufku uzamıyor; gecikme ufuk içinde, fiyatlanmış bir takas olarak oluşuyor.

**Kanıt:** `src/milkrun.py` ufuk koruması; `tests/test_milkrun.py` "zincir Stage 1 son kargo tarihini uzatamaz" testi.

---

## 7. E Bölümü — Doğrulama ve Güvenilirlik

### S45. Maliyeti kendi hesabınıza göre mi raporluyorsunuz?

**Kısa cevap:** Hayır. `src/simulator.py` bağımsız bir ikinci uygulamadır; optimizerin iç durumunu hiç görmez, yalnız çıktı tablolarını ve statik referans veriyi okur.

**Detay:** Hakem, araç zaman çizelgesini, maliyeti ve SLA'yı sıfırdan yeniden kurar. Bu izolasyon sayesinde optimizer ile hakem arasındaki her uyuşmazlık gerçek bir hatadır ve teslim öncesi yakalanır. Nitekim hakem, optimizer daha yazılmamışken bile iki optimizer-sınıfı hatayı yakalamıştır: yanlış çıkış merkezinden alınan yükün teslim edilmiş sayılması ve karışık araç tipli bir zincirin kapasite ile tır defterini atlatması.

**Kanıt:** `src/simulator.py`; ARCHITECTURE.md Bölüm 9.

### S46. Hakem kaç kural denetliyor?

**Kısa cevap:** Belgelenmiş fiziksel kural tablosu 17 satır; kodun bugünkü hâli toplam 33 farklı ihlal mesajı üretim noktası içeriyor.

**Detay:** 17 satırlık tablo zincir sürekliliği, tekrarlı kimlik, kapasite aşımı, hat varlığı, tip tutarlılığı, çakışan elleçleme, hazır olmadan yükleme, rota kökeni, aktarma zamanlaması, teslim bütünlüğü, SLA, kiralık rota/gün/sayı, elleçleme kapasitesi, tır kapasitesi ve tahminde olmayan talep kontrollerini kapsar. Sonradan eklenen 16 kontrol ise **beyan denetimleridir**: yolculuk süresi, çıkış ve varış elleçleme süreleri, SLA cezası hücresi, araç maliyeti payı, iz düzeyi maliyet uzlaşması, boş kiralık iz üç şartı ve beyan varışın matris varışıyla karşılaştırılması. Dürüst tespit: mimari doküman tablosu bu eklemelerle güncellenmemiştir; kodun kendisi kaynaktır.

**Kanıt:** ARCHITECTURE.md Bölüm 9 tablosu; `src/simulator.py` (29 nokta — 27 `violations.append` + 2 `leg_violations.append`) ve `src/ledger.py` (4 nokta).

### S47. Beyan ettiğiniz maliyet ile hakem maliyeti uyuşuyor mu?

**Kısa cevap:** Evet, ölçülen fark 0,0000 TL. Ve bu bir kontrol değil, bir kapı: uyuşmazsa boru hattı çalışmayı durduruyor.

**Detay:** İki katmanlı bir mutabakat var. Satır düzeyinde: bir fiziksel izin tüm satırlarındaki (Toplam maliyet − SLA cezası) toplamı, hakemin yeniden hesapladığı araç maliyetine 0,01 TL içinde eşit olmalı; bu, zincirin ikinci bacağına maliyet kopyalamayı yapısal olarak imkânsız kılar. Plan düzeyinde: "Toplam maliyet" kolonunun `Decimal` toplamı hakem toplamına 0,01 TL içinde eşit olmalı. Teslim edilen dosyada kolon toplamı 11.232.476,731944446 TL ve SLA kolonu toplamı 2.615.532,00 TL; verilen doğrulanmış değerlerle birebir aynı.

**Kanıt:** `src/simulator.py` iz uzlaşması; `src/export.py` `require_plan_total`; `tools/verify_output.py` çıktısı.

### S48. "Uzlaşma kapısı" nedir? Ne yakaladı?

**Kısa cevap:** Aramanın kendi aritmetiğiyle iddia ettiği tasarruf ile hakemin ölçtüğü farkın kuruşun milyonda birine kadar aynı olması şartı. Stage 3 prototipindeki dört hatanın üçünü bu kapı yakaladı; dördüncüsü bu kapıyı da geçti ve üretim kodu yazılırken ortaya çıktı.

**Detay:** Dört hata şunlardı: (1) kiralık bir rotayı yük alma hedefi almak — kural ihlali, ayrıca spot tarifesiyle fiyatlama; (2) yük alınan durakta SLA damgasını indirmeden sonra başlayan yüklemenin bitişine koymak (5.108,80 TL fazla beyan); (3) alınan yükün kendi varış durağını geçip devam etmesi (274,00 TL); (4) ara durakta indirme kümesinin yanlış türetilmesi — yalnız geçmekte olan yükün orada inmiş sayılması, elleçlemeyi şişirip sonraki bütün segmentleri kaydırıyordu (886,52 TL fazla maliyet). İlk üçünü uzlaşma kapısı yakaladı ve başka hiçbir kontrol fark etmiyordu. Dördüncüsü özellikle öğreticiydi: **kendi içinde tutarlıydı**, yani prototip aynı yanlış zamanlarla hem planlayıp hem fiyatladığı için beyan ile hakem birbirine uyuyor ve hakem 0 ihlal yazıyordu; sadece gereğinden pahalı bir plan üretiyordu. Üretim kodu indirme kümesini yük alma **sonrası** yük listelerinden türetince o fark da kazanıldı.

**Kanıt:** Kabul raporu 2026-07-26 Bölüm 2.1-2.4; `run.py` `STAGE3_SAVING_TOLERANCE`.

### S49. 592 test neyi kapsıyor?

**Kısa cevap:** 528'i önceki teslimden değişmeden geliyor, 64'ü final entegrasyon katmanı için eklendi. Hepsi geçiyor.

**Detay:** Dağılım toplamı 592'yi tam verir: Stage 0 ve kapılar için 88 test, Stage 1 için 42 + zincir doğrulaması için 14, Stage 2 için 75, Stage 3 için 28, hakem katmanı (simülatör, defterler, zaman, değerlendirme) için 107, girdi/çıktı sözleşmesi için 64, şema ve Excel yazımı için 102, veri yükleme ve çizelgeleme için 45, tahmin katmanı için 27. Testler yalnız birim davranışı değil, gerçek 4.046 satırlık ufku uçtan uca çalıştırıp toplam maliyetleri kuruşuna kadar sabitleyen altın değer testlerini de içeriyor. Bir sabiti değiştirmek bu testlerden en az birini kırar.

**Kanıt:** `final-teslim/tests/`; `python -m pytest -q` → 592 geçti.

### S50. Diske yazılan dosyanın bozulmadığını nasıl biliyorsunuz?

**Kısa cevap:** Yazdıktan sonra dosyayı **geri okuyup** yeniden doğruluyoruz; ancak ondan sonra atomik olarak yerine koyuyoruz.

**Detay:** Sıra şudur: şema doğrulaması → hedef klasördeki geçici dosyaya yazım → geçici dosyayı diskten geri okuma → kolon listesi ve satır sayısı kontrolü → hücre değerlerinin toleranslı karşılaştırılması → `os.replace` ile atomik taşıma. Şema hatası ölümcüldür ve hedef dosyaya hiç dokunulmaz; hücre değeri farkı ise uyarı basar ama yayını engellemez, çünkü Excel'in yaklaşık 17 anlamlı basamaklık hassasiyeti doğal farklar üretir (3347,8859374999997 → 3347,8859375) ve çıktısız kalmak çok daha ağır bir sonuçtur. Ayrıca ayrı bir araç, yayınlanan planı diskten okuyup bağımsız olarak hakemden geçiriyor: 0 ihlal, fark 0,0000 TL.

**Kanıt:** `src/contract.py` `write_final_plan`, `_roundtrip_differences`; `tools/verify_output.py`.

### S51. Geliştirme deposundaki sabit sonuç kapıları neden final pakette yok?

**Kısa cevap:** Çünkü onlar tek bir veri setinin ölçülmüş sonucuna çivilenmişti; bilinmeyen bir veri setinde tanım gereği hata verirlerdi ve bu, hatalı çalıştırma sayılırdı.

**Detay:** Geliştirme hattında Stage 0'dan Stage 3'e kadar her aşama, kabul edilmiş sonucuna birebir sabitlerle bağlıdır — Stage 2 için 20, Stage 3 için 23 sabit; maliyetler, sayımlar, her metrik alanı ve zincirlerin şekli. Bu kapılar geliştirme sırasında gerçekten devreye girdi (örneğin 4 duraklı geçişte). Ama final koşusunda tarih ve hacim önceden bildirilmediği için bu sabitler anlamsızdır. Kaldırılan **yalnız** bu sabit sonuç kapılarıdır; aşamaların kendi kabul kuralı — 0 ihlal ve daha düşük maliyet — değişmeden korunmuştur.

**Kanıt:** `DEGISIKLIKLER.md` fark #3; TEKNIK_GEREKSINIMLER Bölüm 10.

### S52. Determinizmi neden bu kadar önemsiyorsunuz?

**Kısa cevap:** Çünkü "ilk hatasız çalıştırma resmî sonuçtur". Tekrarlanamayan bir sonuç savunulamaz bir sonuçtur.

**Detay:** Hiçbir yerde rastgelelik, zaman damgası veya sözlük sırası bağımlılığı yok. Aynı girdi her koşuda birebir aynı 1.269 bacağı, aynı 227 zinciri ve aynı 28 yük almayı üretiyor. Bunun en güçlü kanıtı final paketinin kendisi: aynı talep tablosuyla çalıştırıldığında önceki teslimle **0 farklı hücre** üretiyor — 5.523 satır × 16 kolon.

**Kanıt:** `DEGISIKLIKLER.md` Bölüm 4 doğrulama tablosu; determinizm testleri.

---

## 8. F Bölümü — Kurallara Uyum

### S53. Kiralık araçlarla uğrama yapmadığınızı nasıl kanıtlıyorsunuz?

**Kısa cevap:** Dört bağımsız katmanla — kiralık bir bacak ne zincire girebilir, ne yük alma hedefi olabilir, ne de silinebilir.

**Detay:** (1) Zincir kaynakları yalnız Spot bacaklardır ve üretilen her segment Spot olarak kurulur. (2) Stage 3'te kiralık rotalar hedef taramasında atlanır — ölçüm: 126 kiralık rotanın tamamı. (3) Kiralık bir rota yanlışlıkla fiyatlanmaya çalışılsa fonksiyon hata fırlatır, yani yanlış tarife hiç uygulanamaz. (4) Yayın kapısı, yayınlanacak plan üzerinde rota-ortası yüklemenin yalnız Spot rotalarda olduğunu ve bu tür segmentlerin sayısının tam 28 olduğunu doğrular. Kiralık bacaklar her zaman tek bacaklıdır ve kendi rotasından sapmaz.

**Kanıt:** Şartname Bölüm 3; jüri Q&A — HititRoute Soru 11, OpAI Soru 11.1. `src/milkrun.py`, `src/pickup.py`, `src/repair.py` filtreleri.

### S54. Kiralık araçlar tır kapasitesini tüketiyor mu?

**Kısa cevap:** Evet, tüketiyor. Jüri bunu açıkça söyledi ve biz kiralık tırları planlamadan önce bütçeden düşüyoruz.

**Detay:** Hakem defterinde araç tipi ayrımı yapılmaz; Kiralık Tır de Spot Tır da aynı deftere yazılır. Kiralık filoda 10 Tır ve 4 Kamyon var, günde toplam 14 araç 12 rotada. Kiralık tırların rezervasyonu kaldırıldığında plan 12 tır kapasitesi ihlali veriyor; rezervasyonla ihlal 0.

**Kanıt:** Jüri Q&A — HititRoute Soru 11, Astra Bölüm 1, Budapeşte Soru 3. `src/optimize.py` `_seed_context`; `src/simulator.py` tır defteri beslemesi.

### S55. Tır kapasitesi hangi araç tiplerini kapsıyor?

**Kısa cevap:** Yalnız "Tır" araç tipini. Kamyon, Hafif Kamyon ve Kamyonet için hiçbir yanaşma limiti uygulanmıyor.

**Detay:** Jüri bunu üç ayrı takıma tekrarladı. Kodda hakem yalnız araç türü Tır olan izleri deftere yazar. Bu ayrım stratejik olarak da önemli: tır kapasitesi 18 merkezin 7'sinde sıfır (Kütahya, Isparta, Bilecik, Zonguldak, Sivas, Karaman, Denizli). Toplam ziyaret kapasitesi 69: Kocaeli 12, Mersin 11, Eskişehir 10, İstanbul 10, Erzincan 5, Mardin 5, Şanlıurfa 5, Manisa 4, Yalova 4, Tekirdağ 2, Balıkesir 1.

**Kanıt:** Jüri Q&A — HititRoute Soru 10, HİB LOGİ Soru 7. `datas/tir_kapasiteleri v2.xlsx`; `src/simulator.py`.

### S56. Aynı araç bir merkezde boşalıp yeniden yüklenirse kaç tır sayılır?

**Kısa cevap:** Bir. Ama araç gidip geri dönerse iki.

**Detay:** Jürinin netleştirmesi şudur: "Bu kural gün içinde tekrar kullanılması durumunda değil, aracın **hareket etmeden** boşaltılıp tekrar yüklenmesi durumunda geçerlidir." Kodda tır defteri (araç, ziyaret numarası) çiftlerini bir kümede tutar; bir bacağın varışı ile bir sonraki bacağın kalkışı aynı ziyaret numarasını paylaştığı için hareketsiz boşalt-yükle tek eleman olur. Araç gidip döndüğünde bacak indeksi ilerlediği için ziyaret farklı olur ve ayrı sayılır. Her iki durum da birim testleriyle sabitlenmiştir.

**Kanıt:** Şartname ÇÖZÜM Soru 7; jüri Q&A — Astra Bölüm 2, HititRoute Soru 13. `src/ledger.py` `TirLedger`; `tests/test_ledger.py`.

### S57. Gün aşırı taşımada kapasite hangi günün kotasından düşüyor?

**Kısa cevap:** Çıkış günü için çıkış merkezinin, varış günü için varış merkezinin kotasından — jürinin verdiği örnekle aynı.

**Detay:** Elleçleme defterine çıkış olayı yükleme başlangıcı anıyla, varış olayı gerçek varış anıyla yazılır; günler bu anlardan türer ve gece yarısını aşan işlemler oransal bölünür. Tır defterine ise çıkış için kalkış tarihi, varış için varış tarihi yazılır. Kapasiteler 00:00'da sıfırlanır.

**Kanıt:** Jüri Q&A — HititRoute Soru 6; şartname ÇÖZÜM Soru 5 ve 6. `src/ledger.py`; `src/simulator.py`.

### S58. Bir merkezde x indirip y yüklerseniz kapasiteden ne düşüyor?

**Kısa cevap:** x + y. İndirme ve yükleme iki ayrı elleçleme olayı olarak deftere yazılıyor.

**Detay:** Bu, Stage 3'ün varlık sebebi olan cümledir; jüri aynı yanıtta konsolidasyon için 2x kuralını da veriyor. Kodda araç izinin her yükleme ve indirme işlemi ayrı bir olay olarak üretilir ve tek bir merkez-gün kotasından ikisi birlikte düşer. Milk-run zincirlerinde ise gemide kalıp geçen yük hiç sayılmaz — bu da aynı kuralın diğer yüzüdür.

**Kanıt:** Jüri Q&A — HİB LOGİ Soru 6, HititRoute Soru 8 ve 9. `src/chain.py` yüklenen/taşınan/indirilen ayrımı; `src/ledger.py`.

### S59. Talebi bölüyor musunuz? Kimlik formatı ne?

**Kısa cevap:** Evet, Stage 0'da bölünme olabiliyor; kimlik `D00001-1`, `D00001-2` biçiminde. Stage 1, 2 ve 3 hiç yeni bölme üretmiyor.

**Detay:** Bölünme fiziksel olarak yeni bir parça nesnesi üretir; çıktı kimliklerini çizelgeleyici, parçaların ilk fiziksel görünme sırasına göre deterministik biçimde atar. Teslim edilen dosyada 525 tireli satır var ve sonekler 1'den 5'e kadar gidiyor. Şema doğrulayıcı jürinin izin verdiği çok düzeyli biçimi (`D00001-1-1`) de kabul eder; mevcut boru hattı tek düzeyli sonek üretiyor. İyileştirme aşamaları yükü yalnız tam parça olarak taşır — bunu, bölme fonksiyonunu hata fırlatacak şekilde değiştirip testlerin yine geçmesiyle kanıtlıyoruz.

**Kanıt:** Şartname ÇÖZÜM Soru 1; jüri Q&A — Astra Bölüm 4. `src/schedule.py` kimlik atama; `src/schemas.py` `SPLIT_ID_RE`.

### S60. Boş spot araç döndürüyor musunuz?

**Kısa cevap:** Hayır. Boş bacak yalnız zorunlu kiralık seferler için yazılıyor.

**Detay:** Jüri ek mesajında "Boş araçları döndürmeyiniz" diyor. Optimizer boş dönüş bacağı üretmiyor; şema doğrulayıcı boş Talep ID'yi yalnız Araç Tipi "Kiralık" iken kabul ediyor ve o satırda desinin 0 olmasını zorunlu kılıyor. Hakem ayrıca boş bir fiziksel iz için üç şart arıyor: iz kiralık olmalı, tam bir boş beyan satırı bulunmalı ve tek bacaklı olup kiralık rota listesinde eşleşmeli. Teslim edilen dosyada 35 boş kimlikli satır var ve hepsi kiralık.

**Kanıt:** Jüri ek mesajı madde 1; `src/schemas.py` `validate_plan`; `src/simulator.py` boş iz denetimi.

### S61. Minimum doluluk kuralı var mı? %48'lik Stage 0 doluluğu ihlal değil mi?

**Kısa cevap:** Bu aşamada minimum doluluk kuralı yok — jüri açıkça kaldırdığını söyledi. Ve zaten teslim ettiğimiz plan Stage 3, doluluk %79,03.

**Detay:** Jürinin cevabı şu: "Bu aşamada böyle bir kural bulunmamaktadır, gönderiler gecikirse SLA cezası ödenmesi gerekmektedir." Kodun hiçbir yerinde doluluk alt sınırı yok; doluluk yalnız Stage 1'de verici sıralaması için bir sezgisel olarak kullanılıyor, bir kısıt olarak değil. Stage 0 kasten "doğru ama saf" bir taban plandır; asıl teslim Stage 3'tür ve orada doluluğu %30'un altında olan spot araç sayısı 480 / 1.143'ten 30 / 539'a inmiştir.

**Kanıt:** Jüri Q&A — Budapeşte Soru 4. `docs/figures/chart_data.json` doluluk dağılımları.

### S62. Yükü hazır olmadan araca yüklüyor musunuz?

**Kısa cevap:** Hayır ve bunu üç ayrı yerde zorluyoruz; hakem ayrıca bağımsız olarak denetliyor.

**Detay:** Kontrol edilen şey kalkış saati değil, **yükleme başlangıcıdır**. Örnek: talep 09:00'da hazır, kalkış 09:30, 10.000 desi — yükleme 07:50'de başlaması gerekirdi, dolayısıyla bu bir ihlaldir ve hakem yazar. Planlayıcıda yükleme başlangıcı her zaman en geç hazır olma anına çıpalanır; Stage 3'te ise araç hub'da bekletilmez, yük araç indirmeyi bitirdiğinde hazır değilse aday hiç üretilmez.

**Kanıt:** Jüri Q&A — HititRoute Soru 7, ROTAI Soru 1. `src/candidates.py` `plan_vehicle`; `src/simulator.py` hazır olma kontrolü.

### S63. Tır kapasitesi 0 olan merkezlere tır gönderiyor musunuz?

**Kısa cevap:** Hayır, tek bir ziyaret bile yok. Aksi hâlde defter kesin eşitsizlikle anında ihlal üretirdi.

**Detay:** Yedi merkezin kapasitesi sıfır. Planda en yoğun tır noktası İstanbul'da 01.07 ve 02.07 tarihlerinde 9/10 ziyarettir. Elleçleme tarafında da hiçbir defter aşılmıyor; en yüksek doluluk oranları Karaman 02.07'de %95,9 (42.022 / 43.830) ve İstanbul 01.07'de %92,7 (365.807 / 394.786). Bu sayılar teslim edilen dosya üzerinde defterler yeniden kurularak ölçülmüştür.

**Kanıt:** `datas/tir_kapasiteleri v2.xlsx`; `src/ledger.py` `TirLedger.violations`; teslim edilen `out/Tasima-plani.xlsx` üzerinden ölçüm.

### S64. "Yolculuk süresi" kolonunu desi payına bölüyor musunuz?

**Kısa cevap:** Hayır. Yolculuk süresi bacağa aittir ve her satıra tam yazılır; elleçleme ve maliyet ise satır bazlıdır.

**Detay:** Üçünün fiziksel anlamı farklıdır. Araç 60 dakika yol gider; 100 desilik kalem için 20, 200 desilik için 40 dakika gitmez. Elleçleme ise şartnamede desi başına tanımlıdır, dolayısıyla satır bazlı yazılır. Maliyet de bölünebilir, çünkü toplam korunur ve bu korunum hakem tarafından ayrıca denetlenir. Hakem her satırda yolculuk süresinin hat matrisiyle **birebir** eşleşmesini arar; tolerans yoktur.

**Kanıt:** Jüri ek mesajı madde 4 (0,92 saat = 56 dakika örneği bacak düzeyindedir); `src/schedule.py` beyan kolonları; `src/simulator.py` satır denetimi.

---

## 9. G Bölümü — Final Backtest Teknik Gereksinimleri

### S65. `python main.py` argümansız çalışıyor mu?

**Kısa cevap:** Evet. Hiçbir argüman, ortam kurulumu veya kullanıcı etkileşimi gerekmiyor; referans veri setinde uçtan uca yaklaşık 150 saniye.

**Detay:** `main.py` kök dizinde ve ince bir orkestratördür — optimizasyona ait tek bir karar vermez, yalnız aşamaları sırayla çağırır ve kabul bayrağını okur. Kodda `input()`, dosya seçici, IDE veya not defteri bağımlılığı yok; statik tarama ile `urllib`, `requests`, `socket`, `subprocess`, `pip install`, `tkinter`, `get_ipython`, `google.colab` aranmış ve hiçbiri bulunmamıştır. Yollar betiğin kendi konumundan çözüldüğü için farklı bir çalışma dizininden mutlak yolla çağrıldığında da çıkış kodu 0 verir.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 3; `final-teslim/main.py`; `KONTROL_LISTESI.md`.

### S66. Girdi dosyasını nasıl buluyorsunuz?

**Kısa cevap:** Bölüm 4'ün iki erişim yönteminin **ikisini de** destekliyoruz: önce `TEKNOFEST_INPUT_FILE` ortam değişkeni, sonra `data/one_week_backtest.xlsx`.

**Detay:** Ortam değişkeninin değeri kırpılır ve çevresindeki tırnaklar soyulur; göreli verilmişse betiğin dizinine göre çözülür. Ortam değişkeni tanımlı ama gösterdiği dosya yoksa sessizce yedek yola düşülür — bu davranış testle sabitlenmiştir. İkisi de yoksa denenen tüm yolları listeleyen açık bir hata verilir. Yedek yoldaki dosya, ekibin kendi tahmin modülünün ürettiği 29.06-05.07.2026 talep tablosudur.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 4; `src/contract.py` `resolve_input_path`; `teknofest_manifest.json`.

### S67. Girdi biçimi beklediğinizden biraz farklı gelirse ne oluyor?

**Kısa cevap:** Geniş bir tolerans katmanı var, ama toleransların hiçbiri sessiz değil — uygulanan her tolerans ve atlanan her satır konsola not olarak basılıyor.

**Detay:** Kolon adları Unicode normalizasyonu, boşluk ve büyük/küçük harf toleransıyla eşleştirilir; ad eşlemesi tamamlanamazsa ve tabloda tam 6 kolon varsa şartnamenin "ad ve sıra birebir" garantisine dayanarak konum eşlemesine düşülür. Saat hücreleri altı ayrı tipten (saat nesnesi, metin, Excel gün kesri, zaman damgası, süre, sayı) kanonik `SS:DD` biçimine çevrilir; tarih hücreleri altı ayrı metin biçiminden ve Excel seri numarasından çözülür; desi hücreleri sayıya çevrilip yuvarlanır ve negatifler sıfırlanır. Çözümlenemeyen satırlar dört ayrı sayaçla (geçersiz tarih, geçersiz saat, geçersiz desi, matriste olmayan hat) raporlanır. Referans girdide 4.046 satırın tamamı geçti, 0 satır atlandı.

**Kanıt:** `src/contract.py` `read_demand_table`, `_to_date`, `_to_hhmm`, `_to_desi`; `tests/test_contract.py` (64 test).

### S68. Ufku nereden türetiyorsunuz? Kodda gömülü tarih var mı?

**Kısa cevap:** Yok. Ufuk yalnız girdinin Tarih kolonundan, en küçük ve en büyük tarih arasındaki kesintisiz gün listesi olarak türetiliyor.

**Detay:** Geliştirme hattındaki sabit başlangıç ve bitiş tarihleri final pakete taşınmadı. Aynı haftayı 2019, 2026 ve 2031 yıllarına taşıyıp sonucun kaymadığını test ettik. Aralık 31 günü aşarsa yalnız uyarı basılır ve çalışma sürer — aykırı tek bir tarih hücresi yüzünden koşu düşürülmez.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 7; `src/contract.py` `horizon_days`; `DEGISIKLIKLER.md` fark #2.

### S69. Çıktı şemasına birebir uyduğunuzu nasıl garanti ediyorsunuz?

**Kısa cevap:** Üç kat doğrulama: yazımdan önce şema, yazımdan sonra diskten geri okuma, sonra atomik yerine koyma.

**Detay:** Şema hatası ölümcüldür; en ufak sapmada dosyaya hiç dokunulmaz. Denetlenen kurallar arasında 16 kolonun ad ve sırası, araç kimliği biçimi, araç tipi ve türü, merkez ve hat tanınırlığı, iki tarihin gerçek takvim tarihi olması (31.06 reddedilir), iki saatin gerçek `SS:DD` olması (24:00 ve 23:60 reddedilir), talep kimliği biçimi, altı sayısal kolonun sonlu ve negatif olmaması ve bacak içinde araç tipi/türü tutarlılığı var. Şablonun bilinen tuzakları da doğrulayıcıda açıkça ele alınmıştır: "Araç Tipi" ile "Araç türü" ayrımı ve "Varış elleçleme" ile "Çıkış Elleçleme" arasındaki büyük harf farkı.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 5 ve Bölüm 10; `src/schemas.py` `validate_plan`; `src/contract.py` `write_final_plan`.

**Tuzak:** Şartname "bu formata uymayan takımların sonuçları kesinlikle değerlendirmeye alınmayacaktır" diyor. Bu soruya "kolonları doğru yazıyoruz" demek yetersiz; **iki yönlü** doğrulamayı anlatmak gerekiyor.

### S70. Çıktıdaki talep kimlikleri girdiyle birebir eşleşiyor mu?

**Kısa cevap:** Evet. İç boru hattı kanonik kimliklerle çalışır, yazımdan hemen önce girdideki özgün kimlikler geri yazılır.

**Detay:** Girdi kimlikleri kanonik olmasa bile (`REQ_1`, `TALEP-7`) iç doğrulayıcıların ve hakemin kimlik sözleşmesi bozulmaz. Kanonik kimlik atamanın sıralama anahtarı, projenin kendi tahmin modülünün anahtarıyla **birebir aynıdır**; bu yüzden girdi bizim kendi tahmin çıktımız olduğunda eşleme özdeşliktir ve boru hattı bit-birebir aynı planı üretir. Bölünmüş parça soneki çeviride korunur; haritada bulunmayan bir kimlik hiç değiştirilmez.

**Kanıt:** Jüri Q&A — HititRoute Soru 2; `src/contract.py` `read_demand_table`, `restore_demand_ids`.

### S71. 100 dakikayı aşmayacağınızı nasıl garanti ediyorsunuz?

**Kısa cevap:** Her arama aşaması, kalan bütçeyle sınırlı ayrı bir iş parçacığında çalışıyor. Süre dolarsa aşama terk ediliyor, önceki plan korunuyor ve süreç çıkış kodu 0 ile bitiyor.

**Detay:** Varsayılan bütçe 100 dakika, yani Bölüm 10 ile aynı; bunun %90'ı aramaya, kalan %10'u çıktının yazılmasına ayrılır. Ölçülmüş davranış: bütçe 36 saniyeye indirildiğinde Stage 1 kabul edilip yayınlandı, Stage 2 11,4 saniyede terk edildi, Stage 3 hiç başlatılmadı, süreç 32,4 saniyede çıkış kodu 0 ile bitti ve diskte 0 ihlalli geçerli bir plan kaldı. Dürüst sınır: süreç açılışı, girdi okuma ve Stage 0 bütçeden düşülür ama **kesilemez** — ayrı bir iş parçacığına sarılmadıkları için sınır dolsa bile tamamlanmak zorundadırlar. Ölçülen maliyetleri yaklaşık 2,2 saniyedir, yani ~150 saniyelik toplam koşunun %1,5'i; dolayısıyla pratikte risk oluşturmuyor.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 10; `main.py` `_call_with_deadline`, `_run_stage`; `README.md` süre sınırı ölçümü.

### S72. Çıktı dosyası hiç üretilmezse? Süreç çökerse?

**Kısa cevap:** Geçerli ilk plan elde edilir edilmez dosya yazılıyor. Sonraki her kabul edilen aşama atomik olarak güncelliyor.

**Detay:** Buna kademeli yayın diyoruz. Stage 0 planı diske yazıldıktan sonra beklenmedik her durumda diskte geçerli bir taşıma planı bulunur. Ölçülmüş kanıt: %250 hacimli stres senaryosunda süreç Stage 2'nin ortasında zorla öldürüldüğünde bile diskte 3.710 satırlık, tek sayfalı, 16 kolonu birebir doğru bir dosya kaldı. Ayrıca her aşama ayrı ayrı `try/except` ile sarmalanır; hata hâlinde tam iz basılır ve önceki plan korunur, süreç çıkış kodu 0 ile biter.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 10; `main.py` `Publisher`; `DEGISIKLIKLER.md` fark #5 ve #7.

### S73. `teknofest_manifest.json` ne diyor?

**Kısa cevap:** Python 3.11, kurulum `pip install -r requirements.txt`, çalıştırma `python main.py`, çıktı klasörü `out/`, beklenen çıktı `Tasima-plani.xlsx`.

**Detay:** Manifest ayrıca her iki girdi erişim yönteminin de desteklendiğini, ufkun girdiden dinamik türetildiğini, statik referans verilerin `datas/` klasöründe teslim paketindeki hâliyle kullanıldığını ve geliştirme veri setiyle ölçülen sürenin yaklaşık 2,5 dakika olduğunu belirtir. Çalışma zamanı bağımlılıkları yalnız iki paket: `pandas>=2.0,<3.0` ve `openpyxl>=3.1,<4.0`. Değerlendirme ortamında internet olmadığı için çalışma anında hiçbir kurulum yapılmaz.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 6 ve Bölüm 9; `teknofest_manifest.json`; `requirements.txt`.

### S74. Bölüm 8 — değişiklikleriniz gerçekten sadece entegrasyon amaçlı mı?

**Kısa cevap:** Evet ve bunun ölçülebilir kanıtı var: aynı girdiyle üretilen çıktı önceki teslimle **0 farklı hücre**.

**Detay:** On üç algoritma ve hakem modülü tek karakter dahi değişmedi. Eklenen iki dosya (`main.py` ve `src/contract.py`) yalnız Bölüm 3-7 gereksinimlerini karşılar ve içlerinde tek bir optimizasyon kararı yoktur. Değiştirilen yalnız iki modül var, ikisi de davranış genişletiyor: veri yükleyiciye final koşusunda gereksiz olan 66 bin satırlık geçmiş tabloyu atlayan opsiyonel bir bayrak eklendi (8,20 saniyeden 0,08 saniyeye), ve talep kimliği düzenli ifadesi 99.999 satırdan sonra doğal olarak 6 haneye çıkan kimlikleri şema hatası saymasın diye genişletildi. Her iki değişiklik de mevcut davranışı değiştirmiyor; 528 mevcut test değişmeden geçiyor.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 8; `DEGISIKLIKLER.md` Bölüm 1 ve 3.

---

## 10. H Bölümü — Zor ve Sıkıştırıcı Sorular

### S75. SLA cezanız bilerek artıyor. Bu müşteriye zarar değil mi?

**Kısa cevap:** Şartnamedeki amaç fonksiyonu saf toplam maliyet ve jüri gizli bir SLA tavanı koymadı; gecikmeyi 0,40 TL/desi/saat ile **fiyatladı**. Biz o fiyatı kabul edip daha ucuz olduğu yerde satın alıyoruz.

**Detay:** Rakamlar açık: araç maliyetinden 6.843.647,84 TL kazanıp 1.595.164,80 TL ek ceza ödüyoruz; net kazanç 5.248.483,04 TL. Jürinin ilgili cevabı şudur: "Bu aşamada böyle bir kural bulunmamaktadır, gönderiler gecikirse SLA cezası ödenmesi gerekmektedir." Ayrıca SLA gecikmesi hakem simülatöründe bir **ihlal** değil, fiyatlanmış bir maliyet kalemidir — ihlal listesine hiç girmez. Gerçek operasyonda bir servis seviyesi tavanı istenirse bu, amaç fonksiyonuna eklenecek tek bir kısıttır; algoritmanın yapısı değişmez.

**Kanıt:** Jüri Q&A — Budapeşte Soru 4; şartname EK KISIT 2; `src/simulator.py` ihlal listesi ile ceza ayrımı.

**Tuzak:** "SLA'yı umursamıyoruz" demek felaket olur. Doğru çerçeve: "SLA'yı jürinin belirlediği fiyattan satın alıyoruz ve bu bilinçli, ölçülmüş bir takas."

### S76. Neden ticari çözücü (Gurobi/CPLEX) veya OR-Tools CP-SAT kullanmadınız?

**Kısa cevap:** Problem tek bir MILP'e sığmıyor: kısıtların bir bölümü zaman-sürekli, defter tabanlı ve gece yarısında oransal bölünen türden. Buna karşılık bizim yaklaşımımız öngörülebilir, hızlı ve dış bağımlılıksız.

**Detay:** Üç gerekçe var. Birincisi modelleme: elleçleme kapasitesi bir günlük kova değil, gece yarısında süreye orantılı bölünen bir defter; tır ziyareti (araç, ziyaret) küme kardinalitesi; SLA yukarı yuvarlanmış saat üzerinden ceza. Bunları doğrusal bir modele gömmek doğrusallaştırma katmanları gerektirir ve her katman şartnameden sapma riskidir. İkincisi doğrulanabilirlik: bizim her aşamamız bağımsız bir hakem simülatörüyle kural-birebir denetleniyor ve beyan ile hakem 0,0000 TL farkla uzlaşıyor; bir çözücünün iç modeli bu denetimi sağlamaz. Üçüncüsü pratiklik: değerlendirme ortamında internet yok ve bağımlılık listemiz iki paketten ibaret; 7 günlük ufuk için Stage 0 araması 0,46 saniye, tüm boru hattı yaklaşık 150 saniye sürüyor.

**Kanıt:** `requirements.txt`; `src/ledger.py` oransal bölme; `src/simulator.py` bağımsız denetim.

**Tuzak:** "Çözücü kullanmayı bilmiyoruz" izlenimi verilmemeli. Doğru çerçeve: "modelin doğrulanabilirliğini çözücü rahatlığına tercih ettik ve maliyetini ölçtük."

### S77. Çözümünüz optimal mi? Optimalite boşluğunu (gap) biliyor musunuz?

**Kısa cevap:** Hayır, küresel optimal olduğunu iddia etmiyoruz ve bir alt sınır hesaplamadık. Ama iyileştirmenin nereden geldiğini ve nerede durduğunu ölçtük.

**Detay:** Neyin optimal olduğunu net söyleyebiliriz: bir (hat, gün) için araç karması seçimi **tam sayımdır**; bir milk-run alt kümesi seçildiğinde o alt küme için bulunan durak sırası ve araç tipi kombinasyonu o alt kümenin en iyisidir (k ≤ 4 için tüm alt kümeler ve tüm sıralar taranır). Optimal olmayan kısım, çakışan adaylar arasındaki seçimdir: adaylar tasarrufa göre sıralanıp açgözlü işlenir, tam bir küme-bölümleme çözülmez. Bunun etkisini de ölçtük: alternatif olarak denenen tam eşleme (maksimum ağırlıklı eşleme) 47.796 TL kazandırıyor, ama o, çok duraklı geçişin **alternatifi**, toplamı değil — mevcut çözüm o hattı yaklaşık 476 bin TL ile aşıyor. Dürüst özet: alt sınırımız yok, ama her aşamanın marjinal katkısı ve her denenen alternatifin sonucu kayıtlı.

**Kanıt:** `src/candidates.py` tam sayım; `src/milkrun.py` alt küme ve permütasyon sayımı; stage-2-step-3 README "ölçülmüş çıkmaz sokaklar".

**Tuzak:** Bu soruda blöf yapılmamalı. "Optimal" kelimesini yalnız tam sayım yaptığımız yerlerde kullanın.

### S78. Açgözlü / sezgisel yaklaşım bilimsel mi?

**Kısa cevap:** Bilimselliği yöntemin adı değil, doğrulanabilirliği belirler. Bizim her adımımız deterministik, bağımsız olarak yeniden hesaplanmış ve karşı-olgu ölçümleriyle desteklenmiş.

**Detay:** Somut olarak: sonuç girdi sırasından bağımsız (24 permütasyon testi), her kabul edilen hamle plandaki tüm defterlere karşı yeniden doğrulanıyor, her aşama bağımsız bir hakemden geçiyor ve her tasarım kararının karşı-olgusu ölçülüyor. Örnekler: erteleme kapatılınca maliyet 24.954.608,68 TL'ye çıkıyor; kiralık tır rezervasyonu kaldırılınca 12 ihlal doğuyor; boşaltma gününde kiralık tırlar erken kalkarsa 2 ihlal doğuyor; en fazla 3 durakla toplam 205.902,07 TL daha kötü. Bunlar "denedik, oldu" değil, kontrollü ölçümlerdir.

**Kanıt:** Determinizm ve karşı-olgu ölçümleri; 592 test.

### S79. Yapay zekâ nerede? Bu klasik optimizasyon değil mi?

**Kısa cevap:** Yarışmanın iki bileşeni var: veriden öğrenen bir tahmin katmanı ve o tahmini taşıyan bir optimizasyon katmanı. Öğrenme tahmin tarafında, veriden kalibre edilen takvim çarpanlarında.

**Detay:** Takvim çarpanları elle konmuş sabitler değil; geçmişin tamamından, sızıntısız biçimde, rol başına beş oranın medyanı olarak **ölçülmüştür** ve yeterli örnek yoksa güvenli 1,0'a düşer. Etkisi de ölçülmüştür: ay sonu haftasında WMAPE 0,5328'den 0,4464'e iniyor. Optimizasyon tarafında ise problem türü gereği doğru araç kombinatoryal aramadır; oraya sinir ağı koymak sonucu iyileştirmez, yalnız doğrulanabilirliği azaltırdı. Final aşamasında zaten yalnız optimizasyon puanlanıyor ve tahmin modülü çalıştırılmıyor.

**Kanıt:** `src/forecast.py` kalibrasyon; frozen backtest WMAPE tablosu; TEKNIK_GEREKSINIMLER Bölüm 2.

### S80. Farklı bir hafta verilirse çözümünüz çalışır mı? Nasıl emin olabiliriz?

**Kısa cevap:** Test ettik. Farklı yıl, farklı ufuk uzunluğu, farklı hacim, farklı kimlik ve saat biçimleriyle üç senaryo çalıştırıldı; hepsinde çıkış kodu 0 ve 0 hakem ihlali.

**Detay:** Ölçülen senaryolar: referans hafta (29.06-05.07.2026, 4.046 satır, 4.977.975 desi, 150 sn, −%31,8); farklı yıl ve 4 günlük ufuk (25-28.05.2025, 1.808 satır, 1.214.316 desi, `REQ_` kimlikler, `SS:DD` saat biçimi, 171 sn, −%45,8); farklı hafta ve %125 hacim (02-08.09.2026, 2.925 satır, 6.222.428 desi, `SS:DD:ss` saat biçimi, 143 sn, −%28,0). Her üçünde de beyan edilen maliyet ile hakem toplamı arasındaki fark 0,0000 TL. Senaryoları üreten ve çıktıyı bağımsız denetleyen araçlar da pakette.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 7; `final-teslim/README.md` Bölüm 2; `tools/make_test_input.py`, `tools/verify_output.py`.

### S81. %250 hacimde ihlal verdiniz. Bu bir kusur değil mi?

**Kısa cevap:** Hayır — o veri seti fizikî olarak çözümsüz. İhlallerin tamamı, o gün o merkezde **talebin kendisinin** günlük elleçleme kapasitesini aşmasından kaynaklanıyor.

**Detay:** Ağın elleçleme kapasitesi referans hafta için zaten neredeyse doludur: İstanbul 01.07.2026'da o günün yükleme + indirme talebi 395.825 desi, günlük kapasite 394.786 desi. Hacim bu seviyenin belirgin biçimde üzerine çıkarsa elleçleme kısıtı **hiçbir plan tarafından** sağlanamaz. %250 senaryosunda ölçülen 69 ihlalin somut örneği: Erzincan'da o gün 80.160 desi talep var, kapasite 58.673. Önemli olan davranış: kod çökmedi, Stage 1 adayı kural gereği doğru biçimde reddedildi, temel plan korundu ve Bölüm 5 şemasına birebir uyan bir plan yazıldı.

**Kanıt:** `final-teslim/README.md` "fizikî sınır" notu; `DEGISIKLIKLER.md` Bölüm 4 doğrulama tablosu.

**Tuzak:** Bu soruyu "bizim hatamız" diye kabul etmek yanlış olur; ama "sorun yok" demek de yanlış. Doğru cevap: fizikî çözümsüzlüğü göster, sonra kodun bu koşulda nasıl davrandığını anlat.

### S82. 100 dakikada bitmezse ne olur?

**Kısa cevap:** Bitmeme durumu için kod tasarlandı: sınır dolan aşama terk edilir, o ana kadarki en iyi plan diskte kalır ve süreç normal biçimde biter.

**Detay:** Referans veri setinde toplam süre ~150 saniye, yani sınırın %2,5'i. Buna rağmen mekanizmayı gerçekten test ettik: bütçe 36 saniyeye indirildiğinde Stage 2 terk edildi, Stage 1 planı yayınlandı, süreç 32,4 saniyede çıkış kodu 0 ile bitti ve plan 0 ihlalliydi. Süre sınırında terk edilmiş bir iş parçacığı hâlâ CPU tüketiyor olabileceği için süreç, çıktıyı atomik olarak yazdıktan sonra doğrudan sonlandırılır.

**Kanıt:** `main.py` `_seconds_left`, `_call_with_deadline`; `README.md` Bölüm 10 güvenlikleri.

### S83. Kademeli yayın yarım veya tutarsız bir dosya bırakabilir mi?

**Kısa cevap:** Hayır. Yazım hedef klasördeki geçici bir dosyaya yapılır ve ancak tüm doğrulamalar geçtikten sonra atomik olarak yerine konur.

**Detay:** Diskteki dosya her an ya yoktur ya da şemaya birebir uyan geçerli bir plandır; ara bir hâl yoktur. Yazım hatası olursa geçici dosya silinir ve bir önceki geçerli plan diskte kalır. Zorla sonlandırma testinde bulunan 3.710 satırlık dosya tam olarak bu garantiyi gösterir: kesilmiş bir dosya değil, o ana kadarki tam ve geçerli bir plandı.

**Kanıt:** `src/contract.py` `write_final_plan` (geçici dosya + `os.replace`); `KONTROL_LISTESI.md` zorla sonlandırma testi.

### S84. Kiralık araç kimlikleri günler arasında değişiyor. Bu doğru mu?

**Kısa cevap:** Bilerek gün-bazlı benzersiz kimlik kullanıyoruz. Bu, kuralın daha muhafazakâr yorumu ve bunu açık yorum riski olarak kendimiz kaydettik.

**Detay:** Şartname kiralık araçları rota ve adet olarak tanımlıyor; kimliklerin günler arasında kalıcı olması gerektiğine dair bir kural yok. Hakem kendi denetiminde her kiralık aracın gün başına en fazla bir bacak yapmasını ve gün başına benzersiz kimlik kullanmasını arıyor. Kalıcı kimlik istenirse bu, kimlik atama fonksiyonunda tek satırlık bir değişikliktir ve maliyeti değiştirmez — çünkü kimlik atama maliyet hesabına hiç girmez.

**Kanıt:** stage-2-step-3 README Bölüm 4 "açık yorum riski olarak izlediğimiz konular"; `src/simulator.py` kiralık kimlik denetimi.

### S85. Tahmininiz kötüyse optimizasyonunuz da kötüdür, değil mi?

**Kısa cevap:** Final aşamasında bu bağ kopuk: tahmin modülümüz hiç çalışmıyor, optimizasyon jürinin verdiği talep tablosuyla değerlendiriliyor.

**Detay:** TEKNIK_GEREKSINIMLER Bölüm 2 bunu açıkça söylüyor: "Tahmin modülünüzün doğruluğu (WAPE/WMAPE vb.) final puanlamasını etkilemez." Gelişmiş Çözüm aşamasında ise jüri iki bileşeni **ayrı ayrı** puanladığını söylemişti: tahmin gerçek verilerle karşılaştırılıyor, optimizasyon başarısı ise takımın kendi tahminlediği talepler üzerinden ölçülüyor. Dolayısıyla iki bileşen birbirinin puanını taşımıyor. Ayrıca optimizasyon tarafımız hacme duyarlı değil: %35'ten %125'e kadar farklı hacimlerde 0 ihlalle çalıştı.

**Kanıt:** TEKNIK_GEREKSINIMLER Bölüm 2; jüri Q&A — HİB LOGİ Soru 3; Bölüm 7 senaryo ölçümleri.

### S86. Neden konsolidasyon veya hub kullanmadınız?

**Kısa cevap:** Kullanmamayı seçtik ve gerekçesi jürinin kendi cevabında: konsolidasyonda elleçleme iki kez yapılır, SLA saati işlemeye devam eder ve bu, 1 günlük SLA'lı hatlarda konsolidasyonu uygulanamaz hâle getirir.

**Detay:** Jüri şunu söylüyor: "Gerçek operasyonda da zamanla bir yarış olmaktadır bu nedenle bazı durumlarda konsolidasyon tercih edilememektedir. Konsolidasyon yapmak bir zorunluluk değildir." Biz aynı kazancı çift elleçleme maliyeti ödemeden alan bir yol seçtik: milk-run. Yük çıkışta bir kez yüklenir, ara merkezde hiç elleçlenmez ve yalnız kendi durağında iner. Ölçülen sonuç, konsolidasyonsuz olarak fiziksel araç sayısını 1.269'dan 665'e, doluluğu %48,02'den %79,03'e taşıdı. Hub konsolidasyonu, sıradaki iyileştirme başlıklarından biri olarak kayıtlı — ama tercih edilmemiş bir seçenek, kaçırılmış bir seçenek değil.

**Kanıt:** Jüri Q&A — OptiVision Soru 2, HititRoute Soru 9. stage-2-step-3 README Bölüm 7.

### S87. Bu çözümü gerçek operasyona nasıl taşırsınız?

**Kısa cevap:** Üç şey zaten hazır: deterministik çıktı, bağımsız kural denetleyicisi ve dakika çözünürlüklü izlenebilir plan. Eksik olan, canlı veri beslemesi ve operasyonel geri besleme döngüsü.

**Detay:** Plan, her fiziksel araç için tek bir kimlik, her talep parçası için izlenebilir bir kimlik ve dakika hassasiyetinde kalkış/varış zamanları içeriyor — yani doğrudan bir sevkiyat listesine dönüştürülebilir. Hakem simülatörü canlı ortamda bir "plan denetleyici" olarak yeniden kullanılabilir: herhangi bir manuel müdahaleden sonra planı yeniden fiyatlandırır ve kural ihlali varsa gösterir. Gerçek operasyona geçişte eklenecek başlıklar bellidir: sürücü çalışma süresi ve dinlenme kısıtları, araç bulunabilirliği takvimi, gerçek zamanlı gecikme geri beslemesi ve bir servis seviyesi tavanı. Bunların hiçbiri mimariyi değiştirmez; hepsi mevcut kabul kapısına eklenecek yeni kısıtlardır.

**Kanıt:** `src/schedule.py` kimlik atama; `src/simulator.py` bağımsız denetim; stage-2-step-3 README Bölüm 7.

### S88. Mimari dokümanınızda CP-SAT yazıyor ama kodda yok. Hangisi doğru?

**Kısa cevap:** Kod doğru. `ARCHITECTURE.md` erken bir planlama belgesidir ve o satırlar hâlâ "yapılacak" olarak işaretlidir; o tasarım hayata geçirilmedi.

**Detay:** Teslim edilen çözüm dış çözücü kullanmaz; araç karmalarını tam sayımla tarar ve tır ziyaretlerini azalan getirili bir döngüyle dağıtır. Bunu saklamıyoruz, tersine avantajını söylüyoruz: öngörülebilirlik ve hız. Dış bağımlılık yok, 7 günlük ufuk 0,46 saniyede tamamlanıyor ve sonuç bit-birebir tekrarlanabilir. `requirements.txt` içinde de OR-Tools yok.

**Kanıt:** `stage-2-step-3/ARCHITECTURE.md` Bölüm 7 (TODO işaretli); `final-teslim/src/candidates.py`; `requirements.txt`.

**Tuzak:** Bu soru gelirse savunmaya geçmeyin. Dokümanın eski olduğunu kabul edip kodun ne yaptığını net anlatın; tutarsızlığı kendiniz adlandırmak güven verir.

### S89. Aday budamanız optimal çözümü kaçırıyor olabilir mi?

**Kısa cevap:** Küçük bir teorik risk var ve bunu biliyoruz. Ama elenen adayın alt kümesi zaten ayrı bir kombinasyon olarak numaralandırıldığı için arama kör kalmıyor.

**Detay:** İki budama kuralı var. Birincisi kesin doğrudur: kapasite, toplamın erteleme sınırından fazlasını açıkta bırakıyorsa aday nasılsa elenecekti. İkincisi — "en küçük aracı çıkarmak yükü hâlâ tamamen karşılıyorsa aday domine" — araç maliyeti üzerinde kesin baskındır, ama SLA cezası teorik olarak farklılaşabilir: daha çok araç, yükü bölerek elleçleme süresini kısaltıp cezayı düşürebilir. Pratik etkisi ölçülmüştür: 39.598 adayın 6.847'si fiyatlandı ve sonuç 0 ihlalle 16.480.959,77 TL oldu; bu değer sonraki üç aşama tarafından ayrıca %31,84 iyileştirildi.

**Kanıt:** `src/candidates.py` budama kuralları ve ölçülen aday sayıları.

### S90. Tır sayınız dört aşamada hiç değişmemiş. Tır'ı optimize etmiyor musunuz?

**Kısa cevap:** Tır sayısı Stage 0'da zaten bütçeye göre optimize ediliyor ve sonraki aşamalar Tır'a dokunmuyor — çünkü dokunmanın kazandırmadığını ölçtük.

**Detay:** Stage 0'da 45 tır-uygun hat-gün taranıyor, 28'inde ilk tırın getirisi pozitif çıkıyor, ama bütçe kısıtı nedeniyle yalnız 9 spot tır tahsis ediliyor; geri kalan 90 tır zorunlu kiralık filodan geliyor. Stage 1'de spot Tır verici olamıyor (tır bütçesi kıt ve tır zaten verimli araç), Stage 2 ve 3'te ise zincirler Tır kullanmıyor. Tır'ı zincire katma denemesi ölçüldü: sonuç 18.100 TL daha kötü, çünkü kârlı Tır adaylarının %93,6'sı kapasitesi sıfır olan yedi merkez yüzünden ölüyor.

**Kanıt:** `src/optimize.py` `_allocate_tir`; stage-2-step-3 README "ölçülmüş çıkmaz sokaklar".

### S91. Milk-run gerçek hayatta uygulanabilir mi? Sürücü ve mevzuat kısıtları?

**Kısa cevap:** Kural tarafı açık — jüri spot araçlar için çok duraklı uğramaya açıkça izin veriyor ve sefer sayısına üst sınır koymuyor. Sürücü çalışma süresi kısıtı şartnamede yok, dolayısıyla modellemedik.

**Detay:** Zincirlerimizin şekli operasyonel olarak da makul: en fazla 4 durak, tüm duraklar farklı, ardışık bacaklar bağlı, çıkışa dönüş yok ve gemide kalan yük ara merkezde elleçlenmiyor. Zincir teslim ufkunu uzatmıyor. Sürücü dinlenme kuralı eklenmesi istenirse bu, zincirin zaman çizelgesine eklenecek bir alt sınırdır ve mevcut kabul kapısıyla doğrulanabilir; ama şartnamede olmayan bir kısıtı varsayarak maliyeti şişirmek de doğru olmazdı.

**Kanıt:** Jüri Q&A — OpAI Soru 11.1, NEURON-LOG Soru 3; `src/chain.py` topoloji doğrulaması (665 araçta 0 topoloji hatası).

### S92. Arama uzayınızın çoğu boşa gidiyor: 135.660 çiftten 28 kabul. Verimsiz değil mi?

**Kısa cevap:** Sayım ucuz, doğrulama pahalı. Biz tam sayımı ucuz kapılarla filtreliyoruz ve pahalı doğrulamayı yalnız hayatta kalanlara uyguluyoruz.

**Detay:** Stage 3'te 135.660 çift incelendi ama pahalı tam-plan defter doğrulaması yalnız kârlı çıkan adaylar için çalıştı. Stage 1'de de aynı örüntü var: 4.035 çiftin %94'ü ucuz maliyet ve kapasite kapılarında düştü, tam defter denemesi yalnız 243 kez çalıştı. Stage 0'da 39.598 adayın %17,3'ü fiyatlandı. Sonuç ölçülebilir: toplam koşu ~150 saniye, yani zaman aşımı sınırının %2,5'i. Düşük kabul oranı verimsizlik değil, seçiciliktir — kabul edilen 28 hamle 80.861,55 TL kazandırdı ve hiçbiri defter kapısında reddedilmedi.

**Kanıt:** Ölçülen arama metrikleri (`chart_data.json`); kabul raporları.

### S93. Sonuçlarınızı tek bir veri setinde ölçtünüz. Aşırı uyum (overfitting) yok mu?

**Kısa cevap:** Bu risk gerçek ve iki farklı yerde ayrı ayrı ele aldık: tahmin tarafında dondurulmuş backtest, optimizasyon tarafında farklı hafta ve hacim senaryoları.

**Detay:** Tahmin tarafında raporlanan WMAPE değerleri rolling değil, tek atışlık (frozen) değerlendirmeden gelir — eğitim penceresi hedeften önce kesilir ve ufuk içinde yeniden eğitim yapılmaz, yani gerçek yarışma koşulunun aynısıdır. Ayrıca bias düzeltmesi için denenen dört adayın dördü de dışsal örneklemde başarısız oldu ve bu yüzden **hiçbiri teslime alınmadı** — bu, aşırı uyuma karşı verilmiş bilinçli bir karardır. Optimizasyon tarafında ise kodda tek bir takvim tarihi yok ve üç farklı senaryo ölçüldü. Dürüst sınır: sabitlerimizin (12.000 desi eşiği, en fazla 4 durak, 5.600 desi erteleme tavanı) etkisi bu veri setinde ölçüldü; bunların tamamı kapasite değerlerinden türetilmiştir ve veri değişse de türetme kuralı geçerli kalır.

**Kanıt:** `src/frozen_backtest.py`; stage-2-step-3 README "ölçülmüş çıkmaz sokaklar"; Bölüm 7 senaryo tablosu.

### S94. Kodunuzdaki sabitler (12.000, 5.600, 4, 3) gizli parametre ayarı değil mi?

**Kısa cevap:** Üçü kapasiteden türetilmiş, biri ölçülmüş bir mühendislik takası. Hiçbiri deneme-yanılmayla ayarlanmış değil.

**Detay:** 12.000 Kamyon kapasitesidir ve altında Tır'ın hiçbir hatta ucuz olmadığını 1.530 kontrolle doğruladık. 5.600 Kamyonet kapasitesidir ve ertelenen yükün yarın tek küçük araca sığacağını garanti eder. Milk-run'daki 12.000 tavanı en büyük Tır-olmayan aracın kapasitesidir ve asıl kapasite kontrolü zaten veriden okunarak her araç tipi için ayrıca uygulanır. En fazla 4 durak ise açıkça kural değil tercih olarak belgelenmiştir ve gerekçesi ölçümdür: 3 durakla 205.902,07 TL daha kötü, 5 durak kaba kuvvetle uygulanabilir değil. Dürüstlük payı: erteleme tavanını 12.000'e çıkarmanın Stage 0'da 303.173,57 TL kazandırdığını ölçtük, ama bu ölçüm yalnız Stage 0 içindir, dört aşamalı boru hattının sonucu üzerindeki etkisini ölçmedik ve "tek Kamyonet" değişmezini bozduğu için değiştirmedik.

**Kanıt:** `src/candidates.py` ve `src/optimize.py` sabit gerekçeleri; `src/milkrun.py` satır içi ölçüm notu.

### S95. Elleçleme kapasitesi neredeyse dolu diyorsunuz. Planınız kırılgan değil mi?

**Kısa cevap:** Plan kırılgan değil, **veri seti** sınırda. Kapasite dolduğunda kodun davranışı belirlidir: yükü ertesi güne kaydırır ve SLA cezasını öder.

**Detay:** Referans haftada İstanbul 01.07'de %92,7 (365.807 / 394.786) ve Karaman 02.07'de %95,9 doluluğa ulaşıyor, ama hiçbir defter aşılmıyor. Düzeltme katmanı ölçeklenir: en fazla 500 tur döner ve her turda aşımı yaratan en küçük spot yükü ertesi güne kaydırır; kaydırma araç maliyetini değiştirmez, yalnız SLA cezası ekler. Bu, "kapasite ihlali kabul edilemez, gecikme kabul edilebilir" şeklindeki şartname mantığının birebir karşılığıdır. Referans haftada ölçülen etki 11 kaydırma ve +2.399,60 TL cezadır. Dürüst sınır: bu katman elleçleme darboğazını **öngörerek** araç karması seçmez; çok daha dar kapasiteli bir veri setinde çözüm optimalden uzaklaşabilir — ihlal vermez, pahalılaşır.

**Kanıt:** `src/schedule.py` `_fix_handling`; teslim edilen plan üzerinden defter ölçümleri.

### S96. Neden daha da iyileştirmediniz? Masada para bıraktınız mı?

**Kısa cevap:** Evet, bıraktık ve nerede bıraktığımızı sayıyla biliyoruz. Kalan başlıkların her biri kayıtlı, gerekçeli ve ölçülü.

**Detay:** Bilinen açık başlıklar: rota-ortası yük almanın Tier B varyantı (bağımsız bir ölçüm A+B için yaklaşık 146 bin TL gördü, yani ek yaklaşık 66 bin TL — ama 5 duraklı rota üretiyor ve durak sınırı sözleşmesini değiştiriyor); 5 duraklı zincir (kaba kuvvetle uygulanamaz, dal-sınır budaması gerekir); hub konsolidasyonu ve parametre taraması. Buna karşılık kapalı başlıklar da ölçülü: aynı-hat birleştirmenin Stage 2 sonrası getirisi tam olarak **0 TL** (kalan 46 aracın 46'sı da o gün o hattın tek aracı, birleşecek eş yok) ve Tır'ı zincire katmak 18.100 TL daha kötü. Ayrıca final aşamasının kural çerçevesi burada belirleyici: TEKNIK_GEREKSINIMLER Bölüm 8, bu aşamada algoritma iyileştirmesini açıkça kapsam dışı bırakıyor.

**Kanıt:** stage-2-step-3 README Bölüm 7; TEKNIK_GEREKSINIMLER Bölüm 8.

**Tuzak:** "Her şeyi yaptık" demek hem yanlış hem inandırıcılığı düşürür. Açık kalemleri sayıyla söylemek, kontrol sahibi olduğumuzu gösterir.

---

## 11. I Bölümü — Soruyu Karşılama Taktikleri

### 11.1 Ezberlenecek altı sayı

Oturumda başka hiçbir şey hatırlanmasa bile bu altısı hatırlanmalı. Diğer her sayı bunlardan türetilebilir veya "ölçtük, raporda var" denerek ertelenebilir.

| # | Sayı | Ne olduğu |
|---|---|---|
| 1 | **11.232.476,73 TL** | Nihai toplam maliyet |
| 2 | **−%31,84** | Temel plana göre iyileşme |
| 3 | **0** | Hakem ihlali — dört aşamanın hepsinde |
| 4 | **1.269 → 665** | Fiziksel araç sayısı |
| 5 | **%48,02 → %79,03** | Spot araç doluluğu |
| 6 | **592 test · ~150 saniye** | Doğrulama ve uçtan uca süre |

Yardımcı ikinci sıra (gelirse iyi olur, gelmezse sorun değil): 4.046 satır ve 4.977.975 desilik tahmin; 227 milk-run zinciri; 28 rota-ortası yük alma; 0 farklı hücre.

### 11.2 Bilmediğimiz bir soru gelirse

Şu üç adımı sırayla uygulayın:

1. **Soruyu net biçimde kabul edin.** "Bunu bu şekilde ölçmedik." Kaçamak cevap, yanlış cevaptan daha çok zarar verir.
2. **En yakın ölçülmüş şeyi verin.** "Şunu ölçtük ve şu çıktı; sorduğunuz varyantı ölçmedik." Bu, konuya hâkim olduğumuzu gösterir.
3. **Nasıl ölçüleceğini söyleyin.** "Bunu ölçmek için şu senaryoyu üretip hakem simülatöründen geçirmek gerekir." Yöntemi bilmek, sonucu bilmekten çoğu zaman daha değerlidir.

Asla yapılmayacak şey: sayı uydurmak. Bir yanlış sayı, doğru söylenmiş kırk sayının değerini düşürür.

### 11.3 Sayıları hatırlama düzeni

Sayılar tek tek değil, **hikâye olarak** hatırlanır. Merdiven şöyle okunur:

- Stage 0 doğru ama saf bir plandır: her talep taşınır, hiçbir kural çiğnenmez, ama araçların yarısı yarı boştur. 16,48 milyon TL.
- Stage 1 aynı hattaki gereksiz araçları siler. 14,68 milyon TL.
- Stage 2 farklı hatlara giden araçları tek fiziksel araca zincirler. Buradaki sıçrama en büyüğüdür. 11,31 milyon TL.
- Stage 3 zincirlerin boş kapasitesine yol üstündeki yükleri bindirir ve o araçları siler. 11,23 milyon TL.

Aynı hikâye doluluk üzerinden de anlatılabilir: %48 → %57 → %77 → %79. Araç sayısı üzerinden: 1.269 → 1.092 → 693 → 665.

### 11.4 Zor soruda tavır

- **Sıkıştıran soruyu düşman saymayın.** Jürinin sorduğu her sert soru, cevabı hazırsa lehimize dönen bir soru. Özellikle SLA artışı, açgözlü yöntem ve optimalite soruları bizim en güçlü ölçümlerimizin bulunduğu alanlar.
- **Açık kalemi önce siz söyleyin.** Ay sonu bias'ı, Tier B, 5 duraklı zincir ve alt sınır hesabının olmaması zaten belgelenmiş. Bunları jüri bulup çıkarmadan önce söylemek, geri kalan her iddianın güvenilirliğini yükseltir.
- **Kural sorusuna kural cevabı verin.** "Şartname Bölüm X" veya "jüri Q&A'da şu takıma verilen cevap" diye başlayıp sonra koddaki karşılığını gösterin. Sıra bu olmalı: önce kural, sonra uygulama, sonra ölçüm.
- **Karşı-olgu kullanın.** "Bunu kaldırdığımızda şu oluyor" cümlesi, "biz bunu yaptık" cümlesinden çok daha ikna edicidir. Elimizde hazır karşı-olgular var: kiralık tır rezervasyonu kaldırılırsa 12 ihlal; erteleme kapatılırsa 24,95 milyon TL; en fazla 3 durakla 205.902,07 TL daha kötü.
- **Uzunluk kontrolü.** İlk cevap iki cümle olsun. Jüri derinleşmek isterse zaten sorar; istemiyorsa uzun cevap zaman kaybettirir ve konuyu dağıtır.

### 11.5 Kaçınılacak cümleler

| Söylemeyin | Yerine söyleyin |
|---|---|
| "Optimal çözümü buluyoruz." | "Araç karması seçimi tam sayım; aşamalar arası seçim açgözlü, alt sınır hesaplamadık." |
| "SLA'yı önemsemiyoruz." | "SLA'yı jürinin belirlediği 0,40 TL/desi/saat fiyatından satın alıyoruz; net kazanç 5,25 milyon TL." |
| "Yaklaşık şu kadardı sanırım." | "Kesin değeri raporda var; büyüklük mertebesi şu." |
| "Bu bizim hatamız değil." | "Bu, veri setinin fizikî sınırı; kodun bu koşuldaki davranışı şu." |
| "Test etmedik ama çalışır." | "Bunu ölçmedik; ölçmek için şu senaryo gerekir." |

### 11.6 Son kontrol

Oturumdan hemen önce şu dört şey elinizde olsun: çekirdek sayı tablosu (Bölüm 2), altı sayılık ezber listesi (11.1), açık kalemler listesi (ay sonu bias'ı, Tier B, 5 duraklı zincir, alt sınır yokluğu) ve karşı-olgu üçlüsü (kiralık tır rezervasyonu, erteleme, durak sayısı). Bu dört başlık, bu kitaptaki 96 sorunun neredeyse tamamının cevabını taşır.
