# Stage 3 — Rota Ortasında Yük Alma (Tier A) · Kabul Raporu

> Tarih: **26 Temmuz 2026** · Branch: `feature/stage2-milkrun-ve-gorsel-readme`
> Plan: [`docs/superpowers/plans/2026-07-26-stage3-midroute-pickup.md`](../plans/2026-07-26-stage3-midroute-pickup.md)
> Prototip: [`docs/superpowers/prototypes/stage3-pickup-proto.py`](../prototypes/stage3-pickup-proto.py)

---

## 0. Özet

| | Değer |
|---|---:|
| Stage 2 taban (yayındaydı) | 11.313.338,286111113 TL |
| **Stage 3 (yayında)** | **11.232.476,731944447 TL** |
| **Tasarruf** | **80.861,554166666 TL** |
| Stage 0'a göre kümülatif | **−5.248.483,04 TL (−%31,84)** |
| Hakem ihlali | **0** — her aşamada |
| Test | **528 / 528** (258,81 sn) |
| `python run.py` | **104,7 sn**, tüm kapılar geçti |

Devralma dokümanındaki hedef 11.233.363,25 TL (−79.975,04 TL) idi. Üretim kodu bunu
**886,52 TL aşıyor**; nedeni §2.4'te.

---

## 1. Ne yapıldı

Stage 2'ye kadar milk-run zincirleri yalnız **yük indiriyordu**. Jüri Q&A Soru 6
bunun tersini de açıkça serbest bırakıyor:

> *"…Aynı şekilde bir araçtan **x kadar yük indirilip y kadar yük yüklenirse**
> kapasiteden x+y kadar yük düşülür."*

Yasak yalnız kiralıkta: *"Kiralık araçlarla uğrama yapılmaz."*

**Tier A:** alınan yükün varışı, rotanın **zaten uğradığı** bir durak olmalı. Rota
topolojisi hiç değişmez — zincir uzamaz, `MAX_CHAIN_STOPS` ve K1 sözleşmesi aynı
kalır. Kazanç, o yükü ayrı taşıyan aracın tamamen ortadan kalkmasından gelir.

Tier B (rotayı bir durak uzatan, 5 duraklı rota üreten varyant) **kapsam dışı**;
ayrı bir karar konusu olarak `PLAN.md` §5'te duruyor.

### 1.1 Verilen kararlar

| Karar | Gerekçe |
|---|---|
| Ayrı modül `src/pickup.py` + ayrı Stage 3 aşaması | Stage 2'nin bit-bazında sonucu ve `run.py`'deki 20 `STAGE2_*` sabiti **değişmedi** |
| Ekonomi/beyan sözleşmesi `src/milkrun.py`'den **import** edilir | İki aşama bir fiziksel rotayı tek kod yolundan fiyatlamalı; kopyalanmış bir formül sessizce ayrışırdı |
| `run_pickup_stage(baseline, forecast_df, data)` | Plan `stage2_decision` yazıyordu; `run_same_lane_stage` / `run_milk_run_stage` ile simetri ve modülün `MilkRunDecision`'a bağımlı olmaması için `PlanEvaluation` alıyor. `run.py` yine `stage2.selected`'ı geçiriyor, kimlik kontrolü aynı |
| `_build_pickup_candidates` `_PickupSearch` döner | Plan yalnız aday listesi diyordu; arama istatistikleri (`pairs_examined` vb.) tek geçişte gözlemlenebilsin diye küçük bir frozen kayıt döner |
| Stage 3 kabul tabanı **50.000 TL** | 1,00 TL çok gevşek: arama tek kazara yük almaya çökse bile geçerdi |

---

## 2. Bulunan hatalar ve regresyon testleri

Planın §3'ünde üç hata vardı. Üretim kodunu yazarken **dördüncüsü** çıktı.

### 2.1 Kiralık rotaları hedef almak (kural ihlali)

Kiralık rotalar yük alma hedefi olamaz; ayrıca maliyetleri `rental_hourly` /
`rental_per_km` ile hesaplanır, spot tarifesiyle fiyatlamak sessiz bir hata olur.

**Muhafız:** `_build_pickup_candidates` `kind != "Spot"` rotaları atlar
(`rented_routes_skipped`), **ve** `_route_total_tl` kiralık bir rota verilirse
`ValueError` fırlatır — yani yanlış tarife hiç uygulanamaz.

**Testler:** `test_rented_target_route_is_skipped_and_yields_no_candidates`,
`test_route_total_refuses_to_price_a_rented_route_at_spot_rates`,
`test_rented_donor_is_not_eligible`, ve plan seviyesinde
`test_stage3_result_rejects_a_rented_route_taking_cargo_mid_route`.

### 2.2 Yük alınan durakta SLA zaman damgası (prototipte 5.108,80 TL fazla beyan)

Bir yük alma durağında **iki ayrı zaman damgası** vardır:

```python
unload_end   = arr + handling(inen desi)        # SLA BU ana göre
depart_after = unload_end + handling(alınan)    # sonraki segment BUNDAN
```

İnen kargo indirmesi bittiği anda teslim edilmiştir; sonrasında başlayan yükleme
aracı geciktirir, teslimatı geciktirmez.

**Test:** `test_pickup_stop_sla_stamp_excludes_the_loading_that_follows` — B'ye inen
600 desinin teslim süresi tam 09:16'da doluyor; doğru damgada ceza `Decimal("0")`,
yükleme sonrası damgada olsaydı `Decimal("240.0")` olurdu. Ayrıca
`test_pickup_stop_departure_waits_for_the_loading_to_finish` hakemin türeteceği
`dep − handling(yeni desi)` yükleme başlangıcının önceki indirmenin bitişine **tam
eşit** olduğunu doğruluyor (bir dakika erken olsa hakem ihlal yazardı).

### 2.3 Alınan yükün hedefini geçmesi (prototipte 274,00 TL)

Alınan kargo yalnız `pickup_at < i ≤ drop_at` aralığında taşınmalı.

**Test:** `test_picked_up_cargo_never_rides_past_its_own_stop` — 4 segmentli rotada
2. durakta alınıp 3. durakta inen yükün segment maskesi tam olarak
`[False, False, True, False]`.

### 2.4 (YENİ) Ara durakta yanlış indirme kümesi

Prototipin `rebuild()` fonksiyonu, bir durakta neyin indiğini **pickup öncesi**
`segments[i+1].items` listesinden türetiyordu. Alınan parçalar o listede hiç
bulunmadığı için, `pickup_at` ile `drop_at` arasındaki **her ara durakta** yalnızca
geçmekte olan yük "burada indi" sayılıyordu. Sonuç: `handling(drop_desi)` şişiyor,
sonraki bütün segmentler geriye kayıyor.

Bu hata **kendi içinde tutarlıydı** — prototip aynı yanlış zamanlarla fiyatladığı
için beyan = hakem kapısı geçti ve hakem 0 ihlal yazdı. Yalnızca gereğinden pahalı
bir plan üretti.

Üretim kodu indirme kümesini **yeni** yük listelerinden türetiyor
(`_dropped_here`). Kazandığımız fark: **886,52 TL**.

**Test:** `test_carried_pickup_is_not_unloaded_at_an_intermediate_stop` — 3 duraklı
rotada 1. durakta alınıp 3. durakta inen 6.000 desi için ara durağın indirme süresi
`handling(300)` = 3 dk olmak zorunda, `handling(6300)` = 63 dk değil.

---

## 3. Kanıt

### 3.1 Test paketi

```
528 passed in 258.81s (0:04:18)
```

Önceki durum 471 test. Yeni 57 testin dağılımı: `tests/test_pickup.py` 28 test
(yukarıdaki dört regresyon, bağımsız Decimal fiyatlaması, her segmentte kapasite,
hub'da hazır olma, elleçleme defteri reddi, **biriken** muhafız, determinizm, tam
ufuk), `tests/test_optimize.py` +27 Stage 3 kapı testi ve genişletilen boru hattı
testleri.

Kritik iki test:

- `test_guard_accumulates_across_accepted_pickups` — iki yük alma tek başına
  geçerli, birlikte C merkezinin 30 Haziran elleçleme kapasitesini aşıyor. Muhafız
  **kabul edilen her hamleyi taşıyarak** doğrulamasaydı ikisi de kabul edilir ve
  plan ihlalli çıkardı. Ölçüm: `pickups_accepted == 1`, `rejected_by_ledger == 1`.
- `test_stage3_entry_requires_local_saving_to_reconcile_with_referee` — aramanın
  analitik toplamı ile hakemin ölçtüğü fark `0,000001 TL` içinde aynı olmalı.

### 3.2 `python run.py`

```
[Stage 3 candidate]
    Araç maliyeti :   8,616,944.73 TL
    SLA cezası    :   2,615,532.00 TL
    TOPLAM        :  11,232,476.73 TL
    Ham TOPLAM    : 11232476.731944447 TL
    Segment       : 1064
    Fiziksel rota : 665 (126 kiralık, 539 Spot)
    Araç karması  : Hafif Kamyon: 29, Kamyon: 304, Kamyonet: 233, Tır: 99
    Spot doluluk  : 79.03% (2862383/3622080)
    Spot <%30     : 30
    İhlal         : 0
[Stage 3 rota-ortası yük alma (Tier A)]
    Hedef rota    : 227 (126 kiralık atlandı)
    Donör havuzu  : 340
    İncelenen çift: 135660
    Kârlı aday    : 56
    Kabul yük alma: 28
    Defter reddi  : 0
    Silinen araç  : 28
    Parça/desi    : 82/65754
    Hedef karması : Kamyon: 11, Kamyonet: 17
    Yerel tasarruf: 80861.55416666666605766666666 TL
    Ham tasarruf  : 80861.554166666 TL
    Kabul         : True
[Kümülatif]
    Stage 0 -> 3  : 5248483.040277787 TL
    Süre          : 93.1 sn
Yayın tamamlandı; toplam 104.7 sn
```

`İncelenen çift: 135.660` sayısı prototiple **birebir aynı** — arama uzayı
değişmedi, yalnız fiyatlama düzeldi.

### 3.3 Bağımsız yeniden inşa ve şema kontrolü

Ayrı bir süreçte Stage 0/1/2/3 sıfırdan kuruldu ve yayınlanan `out/*.xlsx`
optimizer durumuna hiç bakılmadan yeniden hakemlendi. Tüm kontroller geçti:

**Yeniden inşa.** Stage 0/1/2/3 toplamları sabitlerle birebir; Stage 3'te 0 ihlal;
Stage 2 bacakları Stage 3 tarafından **değiştirilmedi**; kaynak bacaklar ve
in-memory tahmin çerçevesi mutasyona uğramadı; `run.py` Stage 3 kapıları kabul etti.

**Envanter korunumu.** Yüklenen ve teslim edilen (talep → desi) çoklu kümeleri Stage
2 ile Stage 3 arasında **aynı**; yüklenen = teslim edilen; toplam **4.977.975 desi**.

**Topoloji (Tier A değişmezleri).** 0 hata: her çok duraklı rota tek `chain_id`, tek
araç türü, Spot, asla Tır, `2 ≤ uzunluk ≤ 4`, ardışık bacaklar bağlı, varış tekrarı
yok; rota-ortası yükleme yalnız Spot rotalarda ve tam **28** adet; inen her parçanın
indiği durak kendi nihai varışı; `analyze_leg_flows` fiziksel sürekliliği doğruladı;
zincir sayısı 227'de sabit; 126 kiralık rota korundu; son kargo teslim tarihi
**geç değil** (iki planda da `2026-07-06 21:04`).

**Determinizm.** `pickup_improve` aynı ve karıştırılmış girdide birebir aynı plan ve
birebir aynı `PickupMetrics`.

**Yayınlanan artifact.** `PLAN_COLS` birebir · 5.523 satır · `validate_plan` boş ·
`validate_forecast_grid` boş · tahmin ve plan parmak izleri eşit · bağımsız
`simulate()` **0 ihlal**, toplam `11232476.731944447` · `require_plan_total`
uzlaşıyor · 665 benzersiz `Araç ID` · `verify_plan_artifact` geçti.

**Yalnız çalışma kitabından denetim** (optimizer durumu okunmadan, satırlar `Araç
ID`'ye göre gruplanıp kalkış anına göre sıralanarak): bacak sayısına göre araç
dağılımı `{1: 438, 2: 127, 3: 28, 4: 72}` = 665; **28** rota-ortası yükleme; 0 hata.

**Hakem canlı.** Tek bir `Yolculuk süresi` hücresine bir dakika eklendiğinde
`simulate()` ihlal yazıyor.

---

## 4. `run.py` kapıları

Stage 3 için **23 çivili sabit** eklendi; Stage 2'nin 20 sabiti **dokunulmadı**.

`_require_stage3_entry`: kimlik (`baseline is stage2.selected`), kabul, adayın
seçilmiş olması, taban ve adayda 0 ihlal, beyan edilen tasarrufun hakem farkına
eşitliği, tasarruf **≥ 50.000 TL**, ve yerel/hakem tasarruf **uzlaşması**
(`≤ 0,000001 TL`).

`_require_stage3_result`: maliyetler, segment/rota/satır sayıları, her
`PickupMetrics` alanı, zincir şekli ve **yük almanın şekli** — rota ortasında yük
yalnız Spot rotada alınabilir, inen her parçanın durağı kendi nihai varışı olmalı,
ve rota-ortası yükleme yapan segment sayısı tam `STAGE3_PICKUPS_ACCEPTED`.

`_stage_and_publish`: artık `Stage2-baseline.xlsx` → `Tasima-plani.xlsx` sırasıyla
sahneliyor; artifact seviyesindeki tasarruf da **50.000 TL** tabanına tabi.

---

## 5. Hakem kapısı (codex review)

`codex exec --sandbox read-only` ile `src/pickup.py`, `run.py` kapıları ve
testler yedi soru üzerinden incelendi. **Üç bulgu geldi; üçü de kabul edildi ve
düzeltildi.** Kapasite, biriken muhafız, sıralamanın tam-sıra oluşu ve
deepcopy/`id()` sınırı için "defect yok" raporlandı.

### 5.1 `_rebuild_route`, girdisinin yalnız-indiren bir rota olduğunu varsayıyordu

`loaded_desi` yalnız segment 0 ve yük alınan segment için hesaplanıyor, diğer
segmentlerde 0 kabul ediliyordu. Rotada **zaten** bir ara yükleme varsa
(`extra_loads`), o segmentin `load_start`'ı `dep`'e eşitleniyordu; oysa hakem
`dep − handling(yeni yüklenen desi)` türetir. Bugünkü üretim yolunda erişilemez
(Stage 2 rotaları yalnız indirir, rota başına tek yük alma), ama
`test_capacity_is_checked_on_every_segment_the_pickup_rides` fikstürü tam olarak
bu girdiyi üretiyor — yani yardımcı fonksiyonun belgelenmemiş bir ön koşulu vardı.

**Düzeltme:** `_loaded_here()` — yeni yüklenen yük, hakemin tanımıyla birebir
aynı şekilde yük sürekliliğinden türetiliyor; kalkış saati de genelleştirildi
(`loading_at(index + 1)`). Üretim sonucu **bit-bazında değişmedi**.

**Test:** `test_rebuild_reproduces_the_referee_load_start_on_every_segment` —
ara yüklemesi olan bir rotada her segment için `load_start == dep −
handling(yeni desi)` ve `load_start >= önceki unload_end`.

### 5.2 `_build_pickup_candidates` çağıranın verdiği donörün tipini doğrulamıyordu

Üretimde `pickup_improve` donörleri `_donor_eligible`'dan geçiriyor, dolayısıyla
yayınlanan yol güvenliydi. Ama doğrudan verilen bir `Kiralık` donör
`_scheduled_direct_total_tl` üzerinden **spot tarifesiyle** fiyatlanabilirdi.

**Düzeltme:** donör döngüsünde `kind != "Spot"` muhafızı.
**Test:** `test_rented_donor_is_never_priced_even_if_handed_in_directly`.

### 5.3 Şekil kapısı Tier A topolojisini gerçekten kanıtlamıyordu

Çivili sayımlar tek başına, bir rotanın durak kazanıp bir başkasının kaybettiği
bir durumu geçirebilirdi.

**Düzeltme:** `_require_stage3_result` artık zincir uzunluklarının **çoklu
kümesini** Stage 2 ile doğrudan karşılaştırıyor ve araç sayısındaki düşüşün tam
olarak silinen donör sayısına eşit olmasını (`stage3_vehicles_removed`) istiyor.
Şekil kapısının docstring'i de düzeltildi: kontrol bellekteki bacaklar üzerinde
çalışır; bunların diske giden satırlar olduğu ayrıca plan parmak izi ve
`verify_plan_artifact` ile kanıtlanır.

**Testler:** `test_stage3_result_rejects_a_changed_chain_topology`,
`test_stage3_result_rejects_a_wrong_vehicle_reduction`.

Düzeltmelerden sonra `python run.py` **bit-bazında aynı** sonucu üretti
(11.232.476,731944447 TL, 0 ihlal) ve bağımsız yeniden inşa denetimi yine tüm
kontrollerden geçti.

---

## 6. Değişen dosyalar

| Dosya | Değişiklik |
|---|---|
| `src/pickup.py` | **yeni** — Tier A arama, yeniden zamanlama, biriken muhafız, aşama sınırı |
| `tests/test_pickup.py` | **yeni** — 28 test |
| `run.py` | 23 `STAGE3_*` sabiti, iki kapı, şekil + topoloji denetimi, metrik bloğu, yayın yeniden bağlandı |
| `tests/test_optimize.py` | +27 Stage 3 kapı testi; boru hattı testleri dört aşamaya genişletildi |
| `docs/figures/extract_chart_data.py` · `make_figures.py` | Stage 3 verisi + 18 figür tazelendi (F1/F7/F8/F9 dört aşamalı) |
| `README.md` · `PLAN.md` | sonuçlar, yeni §2.3 bölümü, kapı açıklamaları, yol haritası |

**Değişmeyen:** `src/milkrun.py`, `src/repair.py`, `src/optimize.py`,
`src/simulator.py`, `src/schedule.py`, `src/chain.py`, `src/export.py`,
`src/schemas.py` ve `run.py`'deki bütün `STAGE0_*` / `STAGE1_*` / `STAGE2_*`
sabitleri.
