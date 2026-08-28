import { useState, type ReactNode } from 'react'
import { D, S, STAGES, STAGE_LABEL } from '../store'
import { Bars, C, Card, Kpi, Legend, VT_COLOR } from '../lib/ui'
import { Chart, Columns, Donut, Funnel, Txt } from '../lib/charts'
import { DOW, M, TL, dM, dPct, dTL, n0, nf, pct, pct01 } from '../lib/fmt'
import type { ViewProps } from '../App'

/* App'teki görünüm kimliğini yeniden yazmadan almanın yolu — ViewId'yi
   ayrıca import etmemek için go'nun imzasından türetiyoruz. */
type VId = Parameters<ViewProps['go']>[0]

/* ══════════════════════════════════════════════════════════════════════
   Görünüm 6 — Model ve boru hattı
   Jürinin "bu çözüm nasıl çalışıyor" sorusunun tek ekranlık cevabı:
   akış şeması → seçili adımın detayı → reddedilen denemeler.
   ══════════════════════════════════════════════════════════════════════ */

const CL = D.stages.cleaning
const MR = D.stages.milkrun
const PU = D.stages.pickup
const RP = D.stages.repair
const CAL = D.stages.calendar
const BT = D.stages.backtest

/** Şartname sabitleri (panel.json'da sayı olarak tutulmuyor). */
const K_LAST = 4
const EXPORT_COLS = 16
const REG_TESTS = 592
/** "Düşük doluluk" eşiği — stages.spot_below_30 alanının tanımıyla aynı sayı. */
const FILL_LOW = 30
/** Tır kotası olmayan merkez = kota sıfır. */
const NO_TIR = 0

/* ── hakem kural listesi ─────────────────────────────────────── */
const G = {
  yapi: ['yapı', C.blue],
  zaman: ['zaman', C.purple],
  kap: ['kapasite', C.warn],
  but: ['bütünlük', C.ok],
  mal: ['maliyet', C.brand2],
  kir: ['kiralık', C.teal],
} as const

const RULES: [string, keyof typeof G][] = [
  ['Bacak zinciri sürekliliği — her bacak öncekinin bittiği merkezden başlar', 'yapi'],
  ['Aynı bacakta tekrarlı talep kimliği yok', 'but'],
  ['Araç kapasitesi aşılmıyor (desi)', 'kap'],
  ['Hat matrisinde bulunmayan bir çıkış–varış kullanılmamış', 'yapi'],
  ['Zincir boyunca araç tipi tutarlı — araç yolda tür değiştirmiyor', 'yapi'],
  ['Önceki işlem bitmeden yükleme yapılmıyor', 'zaman'],
  ['Talep hazır olmadan yükleme yapılmıyor', 'zaman'],
  ['Rota, talebin tahmindeki çıkış merkezinden başlıyor', 'yapi'],
  ['Aktarma zamanlaması — indirilen yük, sonraki bacağa ancak elleçlendikten sonra biniyor', 'zaman'],
  ['Teslim bütünlüğü — talebin toplam desisi eksiksiz taşınmış', 'but'],
  ['SLA cezası hesabı, şartname formülüyle birebir', 'mal'],
  ['Kiralık araç tanımlı rotasının dışına çıkamaz', 'kir'],
  ['Kiralık araç günde en fazla bir bacak koşar', 'kir'],
  ['Zorunlu kiralık çıkış sayısı her gün tam olarak tutuyor', 'kir'],
  ['Elleçleme kapasitesi — gece yarısını aşan işlem güne bölünerek sayılıyor', 'kap'],
  ['Tır ziyaret kapasitesi merkez bazında aşılmıyor', 'kap'],
  ['Plandaki her talep kimliği tahmin tablosunda var', 'but'],
]

/* ── hakem sonuçları: iddia edilen "sıfır ihlal" veriden okunur ── */
const VIOL = (k: string) => Number(S(k).violations)
const VIOL_TOTAL = STAGES.reduce((a, k) => a + VIOL(k), 0)
const STAGES_CLEAN = STAGES.filter((k) => VIOL(k) === 0).length

/* ── evreler ─────────────────────────────────────────────────── */
const PHASE = {
  veri: { c: C.dim, l: 'VERİ' },
  tahmin: { c: C.blue, l: 'TAHMİN' },
  plan: { c: C.brand, l: 'OPTİMİZASYON' },
  dogru: { c: C.ok, l: 'DOĞRULAMA' },
  yayin: { c: C.warn, l: 'YAYIN' },
} as const
type Ph = keyof typeof PHASE

interface Step {
  id: string
  ph: Ph
  name: string
  desc: string
  val: string
  head: string
  lead: string
  link?: { v: VId; l: string }
}

const ROUTES = (k: string) => Number(S(k).routes)
const SEGS = (k: string) => Number(S(k).segments)

const STEPS: Step[] = [
  {
    id: 'hist',
    ph: 'veri',
    name: 'Geçmiş talep',
    desc: 'ham sipariş',
    val: n0(CL.raw_rows) + ' satır',
    head: 'Geçmiş talep · veri hazırlığı',
    lead: 'Ham sipariş kütüğünden eğitim ızgarasına giden yol. Hangi satırın neden düştüğü tek tek sayılır.',
  },
  {
    id: 'model',
    ph: 'tahmin',
    name: 'Tahmin modeli',
    desc: 'iki katman',
    val: 'DOW × takvim',
    head: 'Tahmin modeli · iki katman',
    lead: 'Kara kutu yok: iki çarpandan oluşan, elle denetlenebilir bir tahmin. Karmaşıklık değil, sızıntısızlık hedeflendi.',
  },
  {
    id: 'fc',
    ph: 'tahmin',
    name: 'Talep tahmini',
    desc: '7 günlük ufuk',
    val: n0(D.forecast.rows) + ' satır',
    head: '7 günlük talep tahmini · optimizatörün tek girdisi',
    lead: 'Planlayıcı gerçek talebi hiç görmez; yalnız bu tabloyu görür. Hakem de plandaki her talep kimliğini bu tabloda arar.',
    link: { v: 'talep', l: 'TALEP GÖRÜNÜMÜ' },
  },
  {
    id: 's0',
    ph: 'plan',
    name: 'Stage 0',
    desc: STAGE_LABEL['Stage 0'],
    val: n0(ROUTES('Stage 0')) + ' rota',
    head: 'Stage 0 · temel plan',
    lead: 'Sıra burada her şeydir: zorunlu kısıtlar önce kapatılır, seçim serbestliği en sona bırakılır.',
    link: { v: 'kisit', l: 'KISIT GÖRÜNÜMÜ' },
  },
  {
    id: 's1',
    ph: 'plan',
    name: 'Stage 1',
    desc: STAGE_LABEL['Stage 1'],
    val: n0(ROUTES('Stage 1')) + ' rota',
    head: 'Stage 1 · aynı-hat onarımı',
    lead: 'Tek kurallı, kanıtı kolay bir sadeleştirme: aynı gün aynı hatta iki spot araçtan birini tamamen boşalt ve sil.',
  },
  {
    id: 's2',
    ph: 'plan',
    name: 'Stage 2',
    desc: STAGE_LABEL['Stage 2'],
    val: n0(ROUTES('Stage 2')) + ' rota',
    head: 'Stage 2 · milk-run konsolidasyonu',
    lead: 'Asıl kazanç burada. Aynı araç birden çok durağa uğrar; segment sayısı değişmez, araç sayısı düşer.',
    link: { v: 'harita', l: 'ZİNCİRLERİ HARİTADA GÖR' },
  },
  {
    id: 's3',
    ph: 'plan',
    name: 'Stage 3',
    desc: STAGE_LABEL['Stage 3'],
    val: n0(ROUTES('Stage 3')) + ' rota',
    head: 'Stage 3 · rota ortasında yük alma (Tier A)',
    lead: 'Var olan bir rotaya, topolojisini hiç bozmadan yolcu yükü bindirmek. Dar ama temiz bir kazanç.',
    link: { v: 'filo', l: 'FİLO GEZGİNİ' },
  },
  {
    id: 'ref',
    ph: 'dogru',
    name: 'Hakem',
    desc: 'simülatör',
    val: n0(RULES.length) + ' kural',
    head: 'Hakem simülatörü · bağımsız doğrulama',
    lead: 'Planlayıcıdan ayrı yazıldı, optimizatörün iç durumunu hiç görmez. Yalnız yazılmış planı ve şartnameyi okur.',
  },
  {
    id: 'pub',
    ph: 'yayin',
    name: 'Yayın',
    desc: 'Excel çıktı',
    val: n0(EXPORT_COLS) + ' kolon',
    head: 'Yayın · kademeli ve geri okunarak doğrulanan çıktı',
    lead: 'Süre dolsa bile elde geçerli bir plan kalmalı. Bu yüzden yayın bir son adım değil, sürekli bir davranış.',
  },
]

/* Palette'te karşılığı olmayan iki yüzey rengi: seçili kutunun dolgusu ve
   huninin en geniş (ham aday) dilimi. */
const BOX_ON = '#16202e'
const FUNNEL_TOP = '#20304a'

/* ── akış şeması geometrisi ──────────────────────────────────── */
const BW = 118
const BG = 18
const BX0 = 12
const BY = 52
const BH = 74
const FW = BX0 * 2 + STEPS.length * BW + (STEPS.length - 1) * BG
const FH = 220
const MID = BY + BH / 2
const bx = (i: number) => BX0 + i * (BW + BG)
const cx = (i: number) => bx(i) + BW / 2

const GROUPS: [number, number, Ph][] = [
  [0, 0, 'veri'],
  [1, 2, 'tahmin'],
  [3, 6, 'plan'],
  [7, 7, 'dogru'],
  [8, 8, 'yayin'],
]

/* ── reddedilen denemeler ────────────────────────────────────── */
const TIR0 = D.centres.filter((c) => c.tir === NO_TIR).length
const KAMYON = D.vtypes.find((v) => v.n === 'Kamyon')!
const TIR = D.vtypes.find((v) => v.n === 'Tır')!

/** Reddedilen denemelerin ölçüm sonuçları — bunlar plan çıktısı değil, deney
    kütüğünden gelen sabitler; panel.json bu koşuları taşımıyor. */
const LAB = {
  /** düşük dolulukta aynı-hat birleştirme */
  lowfill_saving_tl: 0,
  lowfill_candidates: 46,
  /** tır'ı milk-run zincirine katma */
  tir_chain_delta_tl: 18100,
  tir_artifact_share: 93.6,
  /** kaba kuvvet zincir arama */
  bruteforce_stops: 5,
  bruteforce_cpu_min: 13.5,
  bruteforce_mem_gb: 1.3,
  /** tam eşleşme alternatifi */
  matching_saving_tl: 47796,
  /** tahmin bias'ı */
  bias_claimed_pct: 28.3,
  bias_sample_n: 2,
  bias_loo: -0.0573,
  /** en kötü talepleri hedefleme */
  sla_worst_n: 20,
  sla_worst_share: 15,
} as const

/* LAB ve REG_TESTS panel.json'da taşınmayan deney/koşu ölçümleridir. Panonun
   "elle yazılmış sayı yok" ilkesini korumak için kaynakları ekranda açıkça
   yazılır; B planında kanit.json'a bağlanacaklar. */
const LAB_KAYNAK = 'deney kütüğü · Stage 1–3 kabul raporları'
const TEST_KAYNAK = 'pytest koşusu · final-teslim/tests'

const TRIED: { t: string; m: ReactNode; r: string; tone: string; note: string }[] = [
  {
    t: 'Düşük dolulukta aynı-hat birleştirme',
    m: (
      <>
        {TL(LAB.lowfill_saving_tl, 0)} kazanç — {n0(LAB.lowfill_candidates)} adayın{' '}
        {n0(LAB.lowfill_candidates)}&apos;sı da o gün o hattın tek aracıydı
      </>
    ),
    r: 'Duvar',
    tone: 'c-warn',
    note: 'Stage 3 aynı boşluğa farklı yönden girdi',
  },
  {
    t: 'Tır’ı milk-run zincirine katmak',
    m: (
      <>
        {dTL(LAB.tir_chain_delta_tl, 0)} <b>daha kötü</b> — Kamyon aynı {n0(KAMYON.cap)} desiyi {TL(KAMYON.spot_h)}/sa
        ile taşırken Tır {TL(TIR.spot_h)}/sa istiyor; kârlı görünen Tır adaylarının {pct(LAB.tir_artifact_share)}
        &apos;sı tır kapasitesi {n0(NO_TIR)} olan {n0(TIR0)} merkez yüzünden oluşuyordu
      </>
    ),
    r: 'Reddedildi',
    tone: 'c-bad',
    note: 'kârlılık gerçek değil, kısıt artefaktıydı',
  },
  {
    t: n0(LAB.bruteforce_stops) + ' duraklı zincir (kaba kuvvet arama)',
    m: (
      <>
        {nf(LAB.bruteforce_cpu_min, 1)} dk CPU ve {nf(LAB.bruteforce_mem_gb, 1)} GB bellekten sonra hâlâ sonuç yok
      </>
    ),
    r: 'Budama gerekir',
    tone: 'c-warn',
    note: 'zincir üst sınırı ' + n0(D.stages.meta.max_chain_stops) + ' durakta bırakıldı',
  },
  {
    t: 'Greedy yerine tam eşleşme (max-weight matching)',
    m: (
      <>
        {TL(LAB.matching_saving_tl, 0)} kazanç — ama bu çok duraklı geçişin <b>alternatifi</b>, toplamı değil
      </>
    ),
    r: 'Üstü kapatıldı',
    tone: 'c-dim',
    note: 'milk-run zaten daha fazlasını alıyor',
  },
  {
    t: 'Tahmin bias’ını düzeltme (4 ayrı yaklaşım)',
    m: (
      <>
        Hedefin kendisi sahte: {dPct(LAB.bias_claimed_pct)} bias, n={n0(LAB.bias_sample_n)} gözlemle uydurulan bir
        çarpanın artefaktı; LOO ile ölçünce teslim modelinin bias&apos;ı {nf(LAB.bias_loo, 4)}
      </>
    ),
    r: 'Reddedildi',
    tone: 'c-bad',
    note: 'düzeltilecek bir hata yoktu',
  },
  {
    t: 'En kötü talepleri hedefleyerek SLA azaltma',
    m: (
      <>
        Ceza uzun kuyruklu: en kötü {n0(LAB.sla_worst_n)} talep toplam cezanın yalnız {pct(LAB.sla_worst_share, 0)}
        &apos;i
      </>
    ),
    r: 'Verimsiz',
    tone: 'c-dim',
    note: 'nokta atışı yerine yapısal kazanç arandı',
  },
]

/* ══════════════ küçük yardımcılar ══════════════ */

function KvTable({ rows }: { rows: [ReactNode, ReactNode, string?][] }) {
  return (
    <table className="t">
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="c-muted">{r[0]}</td>
            <td className={'n ' + (r[2] ?? 'c-blue')}>{r[1]}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Grafik bileşenleri esnek yükseklikli — kart içinde çökmesin diye sabitliyoruz. */
function Box({ h, children }: { h: number; children: ReactNode }) {
  return <div style={{ height: h, display: 'flex', minWidth: 0 }}>{children}</div>
}

function StageHead({ k }: { k: string }) {
  const s = S(k)
  const i = (STAGES as readonly string[]).indexOf(k)
  const p = i > 0 ? S(STAGES[i - 1]) : null
  const dc = p ? s.total_cost - p.total_cost : 0
  return (
    <div className="g5">
      <Kpi
        sm
        tone="brand"
        v={M(s.total_cost)}
        l="toplam maliyet"
        d={p ? <span className={dc < 0 ? 'c-ok' : 'c-bad'}>{dM(dc)} önceki aşamaya göre</span> : undefined}
      />
      <Kpi sm v={M(s.vehicle_cost)} l="araç maliyeti" />
      <Kpi sm v={M(s.sla_penalty)} l="SLA cezası" tone="warn" />
      <Kpi sm v={n0(ROUTES(k))} l={'fiziksel rota · ' + n0(SEGS(k)) + ' segment'} />
      <Kpi sm tone="ok" v={pct(s.avg_fill)} l="ortalama spot doluluk" />
    </div>
  )
}

function vehicleBars(k: string) {
  const mix = S(k).vehicle_mix
  return Object.entries(mix)
    .sort((a, b) => b[1] - a[1])
    .map(([n, v]) => ({ n, v, q: n0(v), col: VT_COLOR[n], key: n }))
}

/* ══════════════ adım detayları ══════════════ */

function detailFor(id: string): ReactNode {
  if (id === 'hist')
    return (
      <div className="rowf">
        <div className="grow stack">
          <p className="note">
            Ham kütükte <b>{n0(CL.raw_rows)}</b> sipariş satırı var. Bunlar önce merkez–merkez–gün ızgarasına
            yayılıyor: geçmişte görülen <b>{n0(CL.od_in_history)}</b> çıkış–varış çifti, hat matrisindeki{' '}
            <b>{n0(CL.od_in_lane_matrix)}</b> çiftin bir alt kümesi — yani tahmin, matriste karşılığı olmayan bir hat
            uydurmuyor.
          </p>
          <p className="note hl">
            <b>{n0(CL.excluded_dates)}</b> tarih anormal davrandığı için eğitim tabanından çıkarıldı (ay sonu
            çöküşleri ve resmî tatiller). Bu, <b>{n0(CL.excluded_grid_rows)}</b> ızgara satırı demek; geriye{' '}
            <b>{n0(CL.training_grid_rows)}</b> satırlık temiz taban kalıyor. Dışlanan günler yok sayılmıyor — takvim
            çarpanı tam olarak onlardan ölçülüyor.
          </p>
          <Bars
            nw={168}
            qw={86}
            rows={[
              { n: 'geçmiş ızgara satırı', v: CL.history_grid_rows, q: n0(CL.history_grid_rows), key: 'h' },
              { n: 'eğitim tabanı', v: CL.training_grid_rows, q: n0(CL.training_grid_rows), cls: 'hi', key: 't' },
              { n: 'dışlanan (anormal gün)', v: CL.excluded_grid_rows, q: n0(CL.excluded_grid_rows), cls: 'z', key: 'e' },
            ]}
          />
        </div>
        <div style={{ width: 320, flex: '0 0 auto' }}>
          <KvTable
            rows={[
              ['ham sipariş satırı', n0(CL.raw_rows)],
              ['geçmiş gün sayısı', n0(CL.history_days)],
              ['aktarma merkezi', n0(CL.transfer_centres)],
              ['geçmişte görülen O–D', n0(CL.od_in_history)],
              ['hat matrisindeki O–D', n0(CL.od_in_lane_matrix)],
              ['ızgara satırı', n0(CL.history_grid_rows)],
              ['dışlanan tarih', n0(CL.excluded_dates), 'c-warn'],
              ['eğitim satırı', n0(CL.training_grid_rows), 'c-ok'],
            ]}
          />
        </div>
      </div>
    )

  if (id === 'model')
    return (
      <div className="rowf">
        <div className="grow stack">
          <p className="def">
            <b>tahmin(hat, gün)</b> = <em>DOW medyan tabanı</em> × <em>takvim çarpanı</em>
            <br />
            Taban: o hattın aynı hafta gününe ait <em>son k={n0(K_LAST)}</em> gözleminin medyanı — ortalama değil
            medyan, çünkü tek bir kampanya günü hattı yıllarca yukarı çekiyordu. Hat seyrekse taban merkez, o da
            seyrekse genel medyana düşüyor.
          </p>
          <p className="note">
            <b>Katman 2 — takvim çarpanı.</b> Ay sonu rejimi bu veri kümesinin en sert yapısal etkisi ve bir hafta
            günü etkisi değil. Çarpanlar uydurulmadı, dışlanan günlerin kendi oranlarından ölçüldü:
          </p>
          <Bars
            nw={196}
            qw={64}
            max={Math.max(...Object.values(CAL))}
            rows={[
              { n: 'normal gün', v: CAL.normal, q: nf(CAL.normal, 3) + '×', key: 'n' },
              {
                n: 'ay sonundan önceki gün',
                v: CAL.day_before_month_end,
                q: nf(CAL.day_before_month_end, 3) + '×',
                cls: 'z',
                key: 'b',
              },
              { n: 'ay sonu', v: CAL.month_end, q: nf(CAL.month_end, 3) + '×', cls: 'z', key: 'm' },
              {
                n: 'ay sonu ertesi ilk gün',
                v: CAL.first_day_after_month_end,
                q: nf(CAL.first_day_after_month_end, 3) + '×',
                cls: 'hi',
                key: 'a',
              },
            ]}
          />
          <p className="note hl">
            <b>Üç sızıntı koruması.</b> (1) Çarpan yalnızca tahmin edilen günden <b>önceki</b> gözlemlerden ölçülür;
            ufuk içindeki hiçbir gün modele girmez. (2) Geri-test rolling-origin: her hafta yalnız kendinden önceki
            veriyle tahmin edilir, tek bir global uydurma yapılmaz. (3) Anormal günler tabandan çıkarılır ama çarpan
            ölçümünde kalır — böylece rejim bilgisi taban medyanına sızmaz.
          </p>
        </div>
        <div style={{ width: 340, flex: '0 0 auto' }} className="stack">
          <p className="note c-dim">
            Geri-test hatası (WAPE, düşük olan iyi). Aynı hafta, üç ayrı tahminciyle:
          </p>
          {Object.entries(BT).map(([k, v]) => (
            <div key={k}>
              <p className="note" style={{ marginBottom: 6 }}>
                <b>{k}</b>
              </p>
              <Bars
                nw={104}
                qw={58}
                max={Math.max(v.naive, v.dow_median, v.ours)}
                rows={[
                  { n: 'naif (dünkü)', v: v.naive, q: pct01(v.naive), cls: 'z', key: 'n' },
                  { n: 'DOW medyanı', v: v.dow_median, q: pct01(v.dow_median), key: 'd' },
                  { n: 'bizim model', v: v.ours, q: pct01(v.ours), cls: 'hi', key: 'o' },
                ]}
              />
            </div>
          ))}
          <p className="note c-dim">
            Normal haftada takvim çarpanı 1&apos;dir — model kasten DOW medyanına eşitlenir. Fark yalnız ay sonu
            haftasında ortaya çıkar; iddia da zaten orada.
          </p>
        </div>
      </div>
    )

  if (id === 'fc')
    return (
      <div className="rowf">
        <div className="grow stack">
          <Box h={244}>
            <Columns
              vw={560}
              vh={244}
              labels={D.forecast.daily.map((r) => r.d)}
              sub={(i) => DOW[D.forecast.daily[i].dow]}
              series={[{ key: 'desi', label: 'desi', color: C.blue, values: D.forecast.daily.map((r) => r.desi) }]}
              fmtY={(t) => n0((t * Math.max(...D.forecast.daily.map((r) => r.desi)) * 1.12) / 1000) + ' B'}
              fmtV={(v) => n0(v / 1000) + ' B'}
            />
          </Box>
          <p className="note hl">
            30.06 ay sonu: tahmin <b>{n0(D.forecast.daily[1].desi)}</b> desiye düşüyor, ertesi gün{' '}
            <b>{n0(D.forecast.daily[2].desi)}</b> desiye fırlıyor. Bu çukur ve sıçrama elle konmadı, takvim
            çarpanından geldi — ve filo planı bunu bildiği için ay sonunda araç tutmuyor.
          </p>
        </div>
        <div style={{ width: 320, flex: '0 0 auto' }}>
          <KvTable
            rows={[
              ['tahmin satırı', n0(D.forecast.rows)],
              ['sıfır talepli satır', n0(D.forecast.zero), 'c-dim'],
              ['toplam tahmin desisi', n0(D.forecast.total), 'c-ok'],
              ['hazır olma slotu 09:00', n0(D.forecast.slot['9'])],
              ['hazır olma slotu 17:00', n0(D.forecast.slot['17'])],
              ['ufuk', D.meta.horizon[0] + ' → ' + D.meta.horizon[1], 'c-muted'],
              ['plandaki gerçekleşen desi', n0(D.meta.desi), 'c-brand'],
            ]}
          />
          <p className="note c-dim" style={{ marginTop: 10 }}>
            Sıfır talepli satırlar da yazılır: hakem, plandaki her kimliği bu tabloda arar; tablo eksikse plan
            reddedilir.
          </p>
        </div>
      </div>
    )

  if (id === 's0') {
    const k = 'Stage 0'
    const s = S(k)
    return (
      <div className="stack">
        <StageHead k={k} />
        <div className="rowf">
          <div className="grow stack">
            <p className="note">
              <b>Sıra önemli.</b> Stage 0 dört adımı bu sırayla koşar; sıra bozulursa sonraki adımın arama uzayı
              geçersiz oluyor:
            </p>
            <ol className="note" style={{ margin: 0, paddingLeft: 20, lineHeight: 1.75 }}>
              <li>
                <b>Zorunlu kiralık filo.</b> {n0(D.rented.length)} tanımlı rota, ufuk boyunca{' '}
                <b>{n0(Number(s.rented_routes))}</b> rota-günü olarak önce yerleştirilir — bunlar seçim değil, veri.
              </li>
              <li>
                <b>Tır ziyaret bütçesi.</b> Merkez başına tır kotası paylaştırılır; kotası olmayan{' '}
                {n0(TIR0)} merkez baştan tır adayı listesinden düşer.
              </li>
              <li>
                <b>Hat-gün araç karması tam numaralandırma.</b> Her hat-gün için olası araç türü kombinasyonları
                eksiksiz denenir — bu ölçekte kaba kuvvet hâlâ mümkün, sezgisele gerek yok.
              </li>
              <li>
                <b>Erteleme kararı.</b> En sonda: bir talebi bugün yarım araçla mı göndermeli, yoksa SLA cezasını
                göze alıp yarın dolu araca mı bindirmeli.
              </li>
            </ol>
            <p className="note c-dim">
              Sonuç ham ve kasten iyimser değil: {n0(Number(s.spot_below_30))} spot araç {pct(FILL_LOW, 0)} dolulukun
              altında çıkıyor. Sonraki üç aşamanın tek işi bu boşluğu kapatmak.
            </p>
          </div>
          <div style={{ width: 340, flex: '0 0 auto' }} className="stack">
            <p className="note c-dim">Araç türü karması — Stage 0</p>
            <Bars nw={112} qw={62} rows={vehicleBars('Stage 0')} />
            <KvTable
              rows={[
                ['segment', n0(SEGS('Stage 0'))],
                ['kiralık rota-günü', n0(Number(s.rented_routes)), 'c-warn'],
                ['spot rota', n0(Number(s.spot_routes))],
                [pct(FILL_LOW, 0) + ' altı spot araç', n0(Number(s.spot_below_30)), 'c-bad'],
                ['plan satırı', n0(s.plan_rows)],
                ['hakem ihlali', n0(VIOL(k)), 'c-ok'],
              ]}
            />
          </div>
        </div>
      </div>
    )
  }

  if (id === 's1') {
    const k = 'Stage 1'
    const s = S(k)
    const p = S('Stage 0')
    return (
      <div className="stack">
        <StageHead k={k} />
        <div className="rowf">
          <div className="grow stack">
            <p className="def">
              <b>Tek kural:</b> aynı gün, aynı hatta koşan iki spot araçtan birinin <em>tüm</em> yükü diğerinin boş
              kapasitesine sığıyorsa, yükü aktar ve boşalan aracı sil.
            </p>
            <p className="note">
              Rota geometrisi değişmiyor, süre değişmiyor, aktarma yok — yalnız bir araç kalemi düşüyor. Bu yüzden
              hakem doğrulaması burada neredeyse bedava: kontrol edilecek tek şey kapasite ve talep bütünlüğü.
            </p>
            <p className="note hl">
              Ancak bu adım maliyeti tek yönlü düşürmüyor: araç maliyeti{' '}
              <b className="c-ok">{dM(s.vehicle_cost - p.vehicle_cost)}</b> gerilerken SLA cezası{' '}
              <b className="c-bad">{dM(s.sla_penalty - p.sla_penalty)}</b> artıyor. Net{' '}
              <b className="c-ok">{dM(s.total_cost - p.total_cost)}</b> — kabul kararı her zaman toplam üzerinden
              veriliyor, kalem bazında değil.
            </p>
          </div>
          <div style={{ width: 360, flex: '0 0 auto' }} className="stack">
            <Box h={172}>
              <Funnel
                vw={360}
                vh={172}
                showPct
                rows={[
                  { label: 'değerlendirilen donör', v: RP.donors_considered, color: C.blueD },
                  { label: 'kabul edilen aktarım', v: RP.moves_accepted, color: C.blue },
                  { label: 'silinen araç', v: RP.vehicles_removed, color: C.ok },
                ]}
              />
            </Box>
            <KvTable
              rows={[
                ['rota', n0(ROUTES('Stage 1')) + ' ← ' + n0(ROUTES('Stage 0'))],
                ['segment (değişmedi)', n0(SEGS('Stage 1')), 'c-dim'],
                [pct(FILL_LOW, 0) + ' altı spot araç', n0(Number(s.spot_below_30)) + ' ← ' + n0(Number(p.spot_below_30)), 'c-ok'],
                ['ortalama doluluk', pct(s.avg_fill) + ' ← ' + pct(p.avg_fill), 'c-ok'],
                ['hakem ihlali', n0(VIOL(k)), 'c-ok'],
              ]}
            />
          </div>
        </div>
      </div>
    )
  }

  if (id === 's2') {
    const k = 'Stage 2'
    const s = S(k)
    const p = S('Stage 1')
    const mix = MR.chain_size_mix
    const cols = [C.blue, C.purple, C.brand]
    return (
      <div className="stack">
        <StageHead k={k} />
        <div className="rowf">
          <div className="grow stack">
            <Box h={224}>
              <Funnel
                vw={430}
                vh={224}
                rows={[
                  { label: 'denenen üçlü', v: MR.triples_evaluated, color: FUNNEL_TOP },
                  { label: 'denenen ikili', v: MR.pairs_evaluated, color: C.blueD },
                  { label: 'ele alınan küme', v: MR.groups_considered, color: C.blue },
                  { label: 'kabul edilen zincir', v: MR.chains_accepted, color: C.brand },
                ]}
              />
            </Box>
            <p className="note c-dim">
              Huni tepesindeki {n0(MR.triples_evaluated)} üçlü, {n0(MR.groups_considered)} aday küme içinde
              üretilip puanlandı; kabul edilen {n0(MR.chains_accepted)} zincir bu aramanın çıktısı.
            </p>
          </div>
          <div className="grow stack">
            <Box h={224}>
              <Donut
                vw={430}
                vh={224}
                cx={112}
                r={80}
                ri={50}
                center={n0(MR.chains_accepted)}
                centerSub="zincir"
                items={Object.entries(mix).map(([k, v], i) => ({
                  label: k + ' duraklı',
                  v,
                  color: cols[i % cols.length],
                }))}
              />
            </Box>
            <Bars nw={112} qw={62} rows={Object.entries(MR.chain_type_mix).sort((a, b) => b[1] - a[1]).map(([n, v]) => ({ n, v, q: n0(v), col: VT_COLOR[n], key: n }))} />
          </div>
        </div>
        <p className="note hl">
          <b>Zincir yeni bacak yaratmaz.</b> Stage 1&apos;de {n0(SEGS('Stage 1'))} segment vardı, Stage 2&apos;de
          yine <b>{n0(SEGS('Stage 2'))}</b> segment var — değişen tek şey, bu segmentlerin{' '}
          {n0(ROUTES('Stage 1'))} yerine <b>{n0(ROUTES('Stage 2'))}</b> fiziksel rotaya paketlenmesi.{' '}
          {n0(MR.source_vehicles_replaced)} kaynak araç {n0(MR.chains_accepted)} zincire kapandı;{' '}
          {n0(MR.parts_consolidated)} parça ve {n0(MR.desi_consolidated)} desi birleştirildi. Ortalama doluluk{' '}
          {pct(p.avg_fill)} → <b className="c-ok">{pct(s.avg_fill)}</b>, yerel kazanç{' '}
          <b className="c-ok">{M(MR.local_saving_tl)}</b>.
        </p>
      </div>
    )
  }

  if (id === 's3') {
    const k = 'Stage 3'
    return (
      <div className="stack">
        <StageHead k={k} />
        <div className="rowf">
          <div className="grow stack">
            <p className="def">
              <b>Tier A kısıtı:</b> yol üstünde alınan yükün varış merkezi, rotanın <em>zaten uğradığı</em> bir durak
              olmak zorunda. Böylece rota topolojisi hiç değişmez — yeni bacak, yeni km, yeni süre yok; yalnız var
              olan bir bacağın boş kapasitesi dolar.
            </p>
            <p className="note">
              Kiralık rotalar bu aramanın tamamen dışında: {n0(PU.rented_routes_skipped)} kiralık rota baştan
              atlanıyor, çünkü kiralık araç tanımlı rotasının dışına çıkamaz ve günde birden fazla bacak koşamaz.
            </p>
            <p className="note hl">
              <b>İki zaman damgası aynı şey değil.</b>
              <br />
              <span className="chip blue mono">unload_end</span> — yükün indirilmesinin bittiği an;{' '}
              <b>SLA saati burada durur</b>.
              <br />
              <span className="chip on mono">depart_after</span> — aracın o duraktan kalkabileceği en erken an; yolda
              yük alındıysa bu, unload_end&apos;den sonradır.
              <br />
              Prototipte bu ikisi tek alanda birleştirilmişti; hakem simülatörü aktarma zamanlaması kuralında
              yakaladı. Ayrıştırıldıktan sonra kabul edilen alım sayısı düştü ama plan geçerli hâle geldi.
            </p>
          </div>
          <div style={{ width: 360, flex: '0 0 auto' }} className="stack">
            <Box h={172}>
              <Funnel
                vw={360}
                vh={172}
                showPct
                rows={[
                  { label: 'incelenen rota×donör', v: PU.pairs_examined, color: FUNNEL_TOP },
                  { label: 'kârlı aday', v: PU.profitable_candidates, color: C.blue },
                  { label: 'kabul edilen alım', v: PU.pickups_accepted, color: C.ok },
                ]}
              />
            </Box>
            <KvTable
              rows={[
                ['aday rota', n0(PU.routes_considered)],
                ['atlanan kiralık rota', n0(PU.rented_routes_skipped), 'c-warn'],
                ['uygun donör araç', n0(PU.donors_available)],
                ['muhasebe kapısında reddedilen', n0(PU.rejected_by_ledger), 'c-ok'],
                ['kaldırılan donör araç', n0(PU.donor_vehicles_removed), 'c-ok'],
                ['alınan parça', n0(PU.parts_picked_up)],
                ['alınan desi', n0(PU.desi_picked_up)],
                ['yerel kazanç', TL(PU.local_saving_tl), 'c-ok'],
                ['hakem ihlali', n0(VIOL(k)), 'c-ok'],
              ]}
            />
          </div>
        </div>
      </div>
    )
  }

  if (id === 'ref')
    return (
      <div className="stack">
        <div className="rowf">
          <div className="grow stack">
            <p className="note hl">
              <b>Bağımsızlık.</b> Hakem simülatörü planlayıcıdan ayrı yazıldı ve optimizatörün iç durumunu hiç
              görmez: elindeki tek girdi diske yazılmış {n0(EXPORT_COLS)} kolonluk plan, tahmin tablosu ve şartname
              sabitleri. Optimizatörün &quot;bu geçerli&quot; demesi hakem için hiçbir anlam taşımaz.
            </p>
            <p className="note">
              <b>Uzlaşma kapısı.</b> Optimizatörün kendi maliyet defteri ile hakemin bağımsız hesabı, kuruşun
              milyonda birine kadar aynı sayıyı vermek zorunda. Aradaki en küçük fark bile bir modelleme hatasının
              işaretidir; plan o farkla yayınlanmaz.
            </p>
            <p className="note">
              <b>Determinizm.</b> Aynı girdi, aynı sürüm, aynı çıktı — sözlük sıralaması ve eşitlik bozma kuralları
              sabitlendi; rastgelelik kaynağı yok. Her aşama sonunda plan yeniden doğrulanıyor, yalnız sonda değil.
            </p>
            <div className="chips">
              <span className="chip ok" title={`kaynak: ${TEST_KAYNAK}`}>
                {n0(REG_TESTS)} regresyon testi
              </span>
              <span className="chip ok">{n0(RULES.length)} hakem kuralı</span>
              <span className="chip ok">
                {n0(STAGES.length)} aşamanın {n0(STAGES_CLEAN)}&apos;inde de {n0(VIOL_TOTAL)} ihlal
              </span>
              <span className="chip blue">artifact geri okuma</span>
              <span className="chip blue">determinist çıktı</span>
            </div>
          </div>
          <div style={{ width: 300, flex: '0 0 auto' }}>
            <KvTable
              rows={STAGES.map((k): [ReactNode, ReactNode, string] => [
                k + ' · ' + STAGE_LABEL[k],
                n0(VIOL(k)) + ' ihlal',
                'c-ok',
              ])}
            />
            <p className="note c-dim" style={{ marginTop: 10 }}>
              Her aşama hakemden geçmeden bir sonrakine girdi olamaz. Reddedilen bir aşama sessizce atlanır ve bir
              önceki kabul edilmiş plan korunur.
            </p>
          </div>
        </div>
        <div>
          <p className="note c-dim" style={{ marginBottom: 8 }}>
            Hakemin uyguladığı {n0(RULES.length)} kural — hepsi plandan tek başına doğrulanabilir:
          </p>
          <div className="g3" style={{ gap: '0 20px' }}>
            {RULES.map(([t, g], i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 9,
                  alignItems: 'baseline',
                  padding: '6px 0',
                  borderBottom: '1px solid var(--line)',
                }}
              >
                <span className="mono" style={{ fontSize: 10, color: C.faint, flex: '0 0 auto' }}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span style={{ fontSize: 12, lineHeight: 1.45, color: C.ink2 }}>{t}</span>
                <span
                  className="mono"
                  style={{ marginLeft: 'auto', fontSize: 9, color: G[g][1], flex: '0 0 auto', paddingLeft: 6 }}
                >
                  {G[g][0]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )

  return (
    <div className="rowf">
      <div className="grow stack">
        <p className="note hl">
          <b>Kademeli yayın.</b> İlk geçerli plan üretilir üretilmez diske yazılır. Sonrasında kabul edilen her aşama
          dosyayı atomik olarak günceller (geçici dosyaya yaz → yerine taşı), böylece süreç herhangi bir anda
          kesilse bile elde her zaman geçerli ve tam bir plan kalır. Yarım yazılmış dosya diye bir durum yok.
        </p>
        <p className="note">
          <b>Sert süre sınırı.</b> Her aşama kendi daemon thread&apos;inde, kalan süre bütçesiyle çağrılır. Bütçe
          biterse aşama iptal edilir ve bir önceki kabul edilmiş plan korunur — hiçbir aşama tüm koşuyu rehin
          alamaz. Aşamalar arasındaki kazanç sırası da buna göre kuruldu: en büyük kazanç ({M(MR.local_saving_tl)})
          erken alınır.
        </p>
        <p className="note">
          <b>Artifact doğrulama.</b> Yazılan Excel geri okunur; {n0(EXPORT_COLS)} kolonun adı, sırası, veri tipi ve
          boşluk durumu şemayla karşılaştırılır. Ardından hakem simülatörü <em>diskteki dosya</em> üzerinden yeniden
          koşturulur — jürinin göreceği dosya, bizim doğruladığımız dosyanın ta kendisi.
        </p>
      </div>
      <div style={{ width: 340, flex: '0 0 auto' }}>
        <KvTable
          rows={[
            ['plan satırı', n0(D.meta.plan_rows)],
            ['bacak', n0(D.meta.legs)],
            ['fiziksel araç', n0(D.meta.vehicles)],
            ['kiralık / spot', n0(D.meta.rent_vehicles) + ' / ' + n0(D.meta.spot_vehicles)],
            ['çıktı kolonu', n0(EXPORT_COLS)],
            ['toplam maliyet', M(D.meta.total_cost), 'c-brand'],
            ['SLA cezası', M(D.meta.sla_cost), 'c-warn'],
            ['hakem ihlali', n0(VIOL_TOTAL), 'c-ok'],
          ]}
        />
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════ */

export default function Pipeline({ go }: ViewProps) {
  const [sel, setSel] = useState(5) // varsayılan: Stage 2
  const [hov, setHov] = useState(-1)
  const cur = STEPS[sel]

  return (
    <div className="stack">
      <p className="lead in in-1">
        Burada çözümün kendisine değil, <b>çözümü üreten makineye</b> bakıyoruz. Soldan sağa: ham talep geçmişi iki
        katmanlı bir tahmine, tahmin dört aşamalı bir plana, plan da bağımsız hakem simülatöründen geçtikten sonra
        Excel çıktısına dönüşüyor. Herhangi bir kutuya tıklayın — altındaki panel o adımın iç işleyişine ve gerçek
        sayılarına geçer.
      </p>

      {/* ── a) akış şeması ── */}
      <Card
        className="in in-1"
        title="Uçtan uca boru hattı"
        sub={'kutuya tıkla → detay panelinde aç · şu an: ' + cur.name}
      >
        <Chart vw={FW} vh={FH} style={{ minHeight: 238 }}>
          {/* evre çerçeveleri */}
          {GROUPS.map(([a, b, ph]) => {
            const x1 = bx(a) + 2
            const x2 = bx(b) + BW - 2
            return (
              <g key={ph}>
                <path
                  d={`M${x1},${38} V${31} H${x2} V${38}`}
                  fill="none"
                  stroke={PHASE[ph].c}
                  strokeWidth={1}
                  opacity={0.34}
                />
                <Txt x={(x1 + x2) / 2} y={24} anchor="middle" size={9} weight={700} fill={PHASE[ph].c} op={0.85}>
                  {PHASE[ph].l}
                </Txt>
              </g>
            )
          })}

          {/* akış hattı + akan jeton (kutuların ALTINDA çizilir, boşluklarda görünür) */}
          <line x1={BX0} y1={MID} x2={FW - BX0} y2={MID} stroke={C.line} strokeWidth={2} />
          <line
            x1={BX0}
            y1={MID}
            x2={FW - BX0}
            y2={MID}
            stroke={C.brand}
            strokeWidth={2}
            strokeDasharray="6 10"
            opacity={0.5}
          >
            <animate attributeName="stroke-dashoffset" from="32" to="0" dur="1.4s" repeatCount="indefinite" />
          </line>
          {[0, 3.6].map((b) => (
            <g key={b}>
              <circle cx={BX0} cy={MID} r={11} fill={C.brand} opacity={0.16}>
                <animate
                  attributeName="cx"
                  from={BX0}
                  to={FW - BX0}
                  dur="7.2s"
                  begin={b + 's'}
                  repeatCount="indefinite"
                />
              </circle>
              <circle cx={BX0} cy={MID} r={4.5} fill={C.brand2}>
                <animate
                  attributeName="cx"
                  from={BX0}
                  to={FW - BX0}
                  dur="7.2s"
                  begin={b + 's'}
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          ))}
          {STEPS.slice(0, -1).map((_, i) => {
            const gx = bx(i) + BW + BG / 2
            return (
              <path
                key={i}
                d={`M${gx - 3.5},${MID - 4.5} L${gx + 2.5},${MID} L${gx - 3.5},${MID + 4.5}`}
                fill="none"
                stroke={C.dim}
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )
          })}

          {/* hakemden aşamalara geri dönen doğrulama okları */}
          {[3, 4, 5, 6].map((j, k) => {
            const hx = cx(7)
            const sx = cx(j)
            const dep = 152 + (3 - k) * 11
            return (
              <g key={j}>
                <path
                  d={`M${hx},${BY + BH + 2} C${hx},${dep} ${sx},${dep} ${sx},${BY + BH + 11}`}
                  fill="none"
                  stroke={C.ok}
                  strokeWidth={1.1}
                  strokeDasharray="4 6"
                  opacity={sel === j || sel === 7 ? 0.95 : 0.42}
                >
                  <animate attributeName="stroke-dashoffset" from="20" to="0" dur="1.1s" repeatCount="indefinite" />
                </path>
                <path
                  d={`M${sx - 4},${BY + BH + 12} L${sx},${BY + BH + 3.5} L${sx + 4},${BY + BH + 12} Z`}
                  fill={C.ok}
                  opacity={sel === j || sel === 7 ? 0.95 : 0.5}
                />
              </g>
            )
          })}
          <circle cx={cx(7)} cy={BY + BH + 2} r={2.6} fill={C.ok} />
          <Txt x={FW / 2} y={FH - 6} anchor="middle" size={9.5} fill={C.dim}>
            her aşama hakem simülatöründen geçmeden kabul edilmiyor — reddedilirse bir önceki plan korunur
          </Txt>

          {/* adım kutuları */}
          {STEPS.map((st, i) => {
            const on = i === sel
            const hi = on || i === hov
            const ph = PHASE[st.ph]
            const x = bx(i)
            const c = cx(i)
            return (
              <g
                key={st.id}
                role="button"
                tabIndex={0}
                aria-label={st.name + ' adımının detayını aç'}
                aria-pressed={on}
                onClick={() => setSel(i)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    setSel(i)
                  }
                }}
                onMouseEnter={() => setHov(i)}
                onMouseLeave={() => setHov(-1)}
                style={{ cursor: 'pointer' }}
              >
                {on && (
                  <rect
                    x={x - 5}
                    y={BY - 5}
                    width={BW + 10}
                    height={BH + 10}
                    rx={14}
                    fill="none"
                    stroke={ph.c}
                    strokeWidth={1}
                    opacity={0.38}
                  />
                )}
                <rect
                  x={x}
                  y={BY}
                  width={BW}
                  height={BH}
                  rx={10}
                  fill={on ? BOX_ON : C.panel}
                  stroke={hi ? ph.c : ph.c + '55'}
                  strokeWidth={on ? 1.8 : 1}
                />
                <path d={`M${x + 10},${BY} H${x + BW - 10}`} stroke={ph.c} strokeWidth={3} opacity={on ? 1 : 0.42} />
                <Txt x={x + 10} y={BY + 17} size={8.5} fill={C.faint}>
                  {String(i + 1).padStart(2, '0')}
                </Txt>
                <Txt x={c} y={BY + 36} anchor="middle" size={12.5} weight={700} fill={hi ? '#fff' : C.ink2} sans>
                  {st.name}
                </Txt>
                <Txt x={c} y={BY + 50} anchor="middle" size={9.5} fill={C.dim}>
                  {st.desc}
                </Txt>
                <Txt x={c} y={BY + 65} anchor="middle" size={10} weight={700} fill={hi ? ph.c : C.muted}>
                  {st.val}
                </Txt>
              </g>
            )
          })}
        </Chart>
        <Legend
          dot
          items={[
            [PHASE.veri.c, 'veri hazırlığı'],
            [PHASE.tahmin.c, 'tahmin'],
            [PHASE.plan.c, 'optimizasyon — dört aşama, her biri bir önceki planı girdi alır'],
            [PHASE.dogru.c, 'bağımsız doğrulama'],
            [PHASE.yayin.c, 'yayın'],
          ]}
        />
      </Card>

      {/* ── b) seçili adımın detayı ── */}
      <Card
        className="in in-2"
        title={'Adım ' + String(sel + 1).padStart(2, '0') + ' · ' + cur.head}
        sub={PHASE[cur.ph].l}
      >
        <p className="note" style={{ marginBottom: 14 }}>
          {cur.lead}
        </p>
        {detailFor(cur.id)}
        <div className="rowf" style={{ marginTop: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn" type="button" onClick={() => setSel((s) => (s + STEPS.length - 1) % STEPS.length)}>
            ← ÖNCEKİ ADIM
          </button>
          <button className="btn" type="button" onClick={() => setSel((s) => (s + 1) % STEPS.length)}>
            SONRAKİ ADIM →
          </button>
          {cur.link && (
            <button className="btn on" type="button" onClick={() => go(cur.link!.v)}>
              {cur.link.l} →
            </button>
          )}
          <div className="grow" />
          <span className="mono c-dim" style={{ fontSize: 10.5 }}>
            {STEPS.map((s) => s.name).join(' · ')}
          </span>
        </div>
      </Card>

      {/* ── c) reddedilen denemeler ── */}
      <Card
        className="in in-3"
        title="Denedik, ölçtük, reddettik"
        sub="her satır çalıştırıldı ve sayıyla kapatıldı"
      >
        <table className="t">
          <thead>
            <tr>
              <th style={{ width: 28 }}>#</th>
              <th style={{ width: '26%' }}>Denenen fikir</th>
              <th>Ölçüm</th>
              <th style={{ width: 132 }}>Sonuç</th>
            </tr>
          </thead>
          <tbody>
            {TRIED.map((r, i) => (
              <tr key={i}>
                <td className="n c-dim" style={{ paddingRight: 0 }}>
                  {String(i + 1).padStart(2, '0')}
                </td>
                <td style={{ color: 'var(--ink2)', fontWeight: 600 }}>{r.t}</td>
                <td className="c-muted">
                  {r.m}
                  <div className="mono c-dim" style={{ fontSize: 10.5, marginTop: 3 }}>
                    → {r.note}
                  </div>
                </td>
                <td>
                  <span className={'mono ' + r.tone} style={{ fontSize: 11.5, fontWeight: 700 }}>
                    {r.r}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note hl" style={{ marginTop: 12 }}>
          Bu bir başarısızlık listesi değil, <b>arama yaptığımızın kanıtı</b>. Her satır tahmin edilip atlanmadı;
          kodlandı, koşturuldu, ölçüldü ve ölçüm kötü çıktığı için bırakıldı. Kabul edilen dört aşama, bu elemenin
          geride kalanı.
        </p>
        <p className="fine c-dim" style={{ marginTop: 8 }}>
          Kaynak: bu tablodaki ölçümler plan çıktısından değil, {LAB_KAYNAK}'ndan gelir.
        </p>
      </Card>
    </div>
  )
}
