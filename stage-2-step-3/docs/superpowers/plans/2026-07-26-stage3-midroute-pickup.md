# Stage 3 — Rota Ortasında Yük Alma (Mid-Route Pickup)

> **Durum: UYGULANDI ve YAYINDA.** Bu doküman tarihsel kayıt olarak duruyor.
> Üretim kodu `src/pickup.py`; ölçülen sonuç **11.232.476,73 TL** (−80.861,55 TL),
> yani aşağıdaki prototip hedefinden **886,52 TL daha iyi** — nedeni prototipte
> sonradan bulunan dördüncü hata (§3.4 yok, kabul raporunda §2.4).
> Kabul kanıtı: [`../reports/2026-07-26-stage3-midroute-pickup-acceptance.md`](../reports/2026-07-26-stage3-midroute-pickup-acceptance.md)
> Tarih: 26 Temmuz 2026 · Branch: `feature/stage2-milkrun-ve-gorsel-readme`

---

## 1. Neden yapıyoruz

Mevcut milk-run zincirleri yalnız **yük indiriyor**: araç çıkışta her şeyi yükler,
her durakta bir kısmını bırakır. Bir ara durakta **yeni yük almıyor**.

Jüri buna açıkça izin veriyor:

> **Q&A Soru 6:** *"…Aynı şekilde bir araçtan **x kadar yük indirilip y kadar yük
> yüklenirse** kapasiteden x+y kadar yük düşülür."*

Bu cümle tam olarak bir aracın bir merkezde indirip yüklemesini tarif ediyor ve
elleçleme aritmetiğini veriyor. Yasak yalnız kiralık araçlarda:
*"Kiralık araçlarla uğrama yapılmaz."*

**Hakemimiz bunu zaten kabul ediyor.** `src/simulator.py`'deki çıkış kontrolü
**parça bazlı**, araç bazlı değil:

```python
for tid, moves in part_moves.items():
    first_origin = moves[0][3]
    if first_origin != rec0["origin"]:      # her parçanın KENDİ tahmin çıkışı
```

Hub'da alınan talebin kendi tahmin çıkışı o hub olduğu için kontrol sağlanır;
K1 sözleşmesi (bölünme eki yalnız tahmin çıkışında doğar) ihlal edilmez.

**Bonus:** boşalt+yükle durağı `TirLedger`'da **1** tır ziyareti tüketir, 2 değil
(`simulator.py` bacak *i*'nin varışını ve bacak *i+1*'in kalkışını aynı
`visit_id` altına yazar).

---

## 2. Ölçülen sonuç (Tier A)

`Tier A` = alınan yükün varışı, rotanın **zaten uğradığı** bir durak. Rota
topolojisi hiç değişmez.

| | Stage 2 (yayında) | **Stage 3 prototip** |
|---|---:|---:|
| Araç maliyeti | 8.752.512,286111115 | 8.629.612,050000004 |
| SLA cezası | 2.560.825,9999999986 | 2.603.751,1999999993 |
| **TOPLAM** | **11.313.338,286111113** | **11.233.363,250000004** |
| **Tasarruf** | — | **79.975,036111109 TL** |
| Segment | 1.092 | 1.065 |
| Fiziksel araç | 693 | 666 |
| **İhlal** | 0 | **0** |

Analitik tahmin (`79.975,03611111111056…`) hakem sonucuyla **son basamağa kadar**
tuttu; `require_plan_total` uzlaşma kapısı geçti.

Arama istatistiği: 693 rotanın 126'sı kiralık olduğu için atlandı; 135.660
(rota-durak, donör) çifti incelendi; 55 kârlı aday; çakışmasız 27 kabul.

**Tier B** (rotayı bir durak uzatmak) ölçülmedi bu prototipte. Bağımsız bir ajan
A+B için 145.764,47 TL ölçtü — yani Tier B ek ~66 bin TL. Ama Tier B **5 duraklı
rotalar** üretiyor, yani `MAX_CHAIN_STOPS` ve K1 dokümantasyonu değişir. Ayrı
karar konusu.

---

## 3. Prototipte bulunan ÜÇ HATA — her biri için regresyon testi şart

Üçünü de "beyan ettiğim toplam ≠ hakemin hesapladığı toplam" kapısı yakaladı.
Tek uygulama olsaydı üçü de sessizce yanlış plan üretirdi.

### 3.1 Kiralık rotaları hedef almak (KURAL İHLALİ)
Kiralık rotalar yük alma hedefi olamaz. Ayrıca maliyetleri `rental_hourly` /
`rental_per_km` ile hesaplanır; `_vehicle_cost_tl` spot tarifesi kullandığı için
sessizce yanlış fiyatlanıyordu.
**Muhafız:** `route[0].kind != "Spot"` ise hedef değil.
**Test:** kiralık rota içeren bir fikstürde 0 aday üretilmeli.

### 3.2 Yük alınan durakta SLA zaman damgası (5.108,80 TL fazla beyan)
`unload_end` **indirmenin bittiği** an olmalı — SLA bu ana göre hesaplanır.
Sonrasında başlayan **yükleme** işlemi SLA'yı geciktirmez ama aracın **kalkışını**
geciktirir. İki ayrı zaman damgası gerekiyor:

```python
unload_end   = arr + handling(drop_desi)          # SLA bu damgadan
depart_after = unload_end + handling(pickup_desi) # sonraki segment bundan
```

**Test:** yük alınan durakta inen kargonun SLA'sı, yükleme süresi kadar
gecikmemeli (kesin Decimal karşılaştırması).

### 3.3 Alınan yükün hedefini geçmesi (274,00 TL)
Alınan kargo YALNIZ `pickup_at < i <= drop_at` aralığındaki segmentlerde
taşınmalı. Tüm sonraki segmentlere bindirmek hem SLA'yı hem kapasiteyi bozar.
**Test:** 4 duraklı bir rotanın 2. durağında alınan, 3. durakta inen yük 4.
segmentte bulunmamalı.

---

## 4. Üretim planı (TDD)

### Görev 1 — `src/pickup.py`
- `_PickupCandidate` frozen dataclass: `route_index`, `pickup_at`, `drop_at`,
  `donor_token`, `segments`, `delta_tl`
- `_rebuild_route(segments, data, *, pickup_at, drop_at, pickup_items)` —
  zaman çizelgesini baştan kurar, §3.2 ve §3.3'e uyar, beyan kolonlarını
  (`cost` yalnız segment 0'da, `penalty` durak başına) `milkrun.py` ile **aynı**
  sözleşmeyle doldurur
- `_build_pickup_candidates(routes, donors, data)` — Tier A adayları
- `pickup_improve(legs, data) -> (legs, PickupMetrics)` — deterministik greedy,
  her kabulde `_trial_candidate_valid` ile **biriken** doğrulama
- `run_pickup_stage(stage2_decision, forecast_df, data) -> PickupDecision`

**Kritik:** muhafız birden çok yük almayı **biriktirerek** doğrulamalı. Bağımsız
ajanın ölçümünde 3 ihlal tam olarak bu eksiklikten çıktı.

**Determinizm:** sıralama anahtarı `(delta_tl, route_key, pickup_at, donor_key)`
— `_leg_key` üzerinden semantik, nesne kimliği kullanılmadan.

### Görev 2 — Testler (`tests/test_pickup.py`)
- §3.1, §3.2, §3.3 için birer regresyon testi (yukarıdaki tarifler)
- bağımsız Decimal yeniden hesaplama ile bir tam aday fiyatlaması
- kapasite: pickup sonrası her segment ayrı ayrı kontrol
- elleçleme defteri reddi
- determinizm: aynı ve karıştırılmış girdide birebir aynı plan
- gerçek ufuk: `test_full_horizon_pickup_stage_accepts_stage2_baseline`

### Görev 3 — `run.py` Stage 3 entegrasyonu
- `STAGE3_*` sabitleri (Stage 2 kalıbıyla, ~20 sabit) + `_require_stage3_result`
  → maliyetler, sayımlar, her `PickupMetrics` alanı, ve **yük alma şekli**
  (hedef rota Spot, alınan yük yalnız kendi aralığında)
- `_require_stage3_entry` → kimlik, 0 ihlal, tasarruf ≥ 1,00 TL
- `_print_pipeline_metrics`'e Stage 3 bloğu
- `_stage_and_publish` → `Stage2-baseline.xlsx` sonra `Tasima-plani.xlsx`
- **Stage 2'nin 20 çivili sabiti DEĞİŞMEZ** — bu yüzden ayrı modül/aşama seçildi

### Görev 4 — Kabul ve doküman
- tam paket (471 + yeni testler), `python run.py`, şema + bağımsız yeniden inşa
- `docs/figures/extract_chart_data.py` + `make_figures.py` → grafikler tazelenir
- README / PLAN.md / kabul raporu güncellenir, push

---

## 5. Prototip nerede

```
docs/superpowers/prototypes/stage3-pickup-proto.py
```

Çalışan, hakemden geçmiş Tier A prototipi. Depo kökünden çalıştırılır:

```bash
python docs/superpowers/prototypes/stage3-pickup-proto.py
```

Prototip **repoya hiç dokunmadı**. Üretim kodu sıfırdan TDD ile yazılacak;
prototip yalnız referans ve ölçüm kaynağı.

---

## 6. Devralma anındaki durum

- Depo: **471/471 test**, `python run.py` 110 sn, **11.313.338,286111113 TL**, 0 ihlal
- Branch `feature/stage2-milkrun-ve-gorsel-readme` push'lu, commit `ae8e96d`
- Stage 2 sabitleri (`run.py` `STAGE2_*`, 20 adet) geçerli ve çivili
- `MAX_CHAIN_STOPS = 4`

## 7. Reddedilen alternatifler (tekrar denenmemeli)

| Fikir | Ölçüm |
|---|---|
| Tahmin bias'ı düzeltme (slot-bazlı, +2. gün, toparlanma, taban kalibrasyonu) | Hedef sahte: +%28,3 bias, 29 Mart cutoff'unda `first_day` çarpanının n=2 ile 2,0679 uydurulmasının artefaktı. LOO ile teslim modelinin bias'ı **−0,0573** (eksik tahmin). Dört adayın hepsi dışsal örneklemde başarısız |
| Tır'ı zincire katmak | Tam yama **+18.100 TL DAHA KÖTÜ**; minimal yama bit-bazında aynı; Kamyon aynı 12.000 kapasitede Tır'ı her koşulda eziyor (318,25 vs 487,50 TL/sa). Kârlı Tır adaylarının %93,6'sı kapasitesi-0 yedi merkez yüzünden ölüyor |
| Düşük dolulukta aynı-hat birleştirme | **0 TL** — 46 aracın 46'sı o gün o hattın tek aracı |
| Greedy yerine tam eşleme | 47.796 TL, ama çoklu-durak geçişinin alternatifi; mevcut çözüm ~476k TL ile aşıyor |
| 5 duraklı zincir (kaba kuvvet) | 13,5 dk CPU + 1,3 GB, sonuç yok. Budama gerekir |
