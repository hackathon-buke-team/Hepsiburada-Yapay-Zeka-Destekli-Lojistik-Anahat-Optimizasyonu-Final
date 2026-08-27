import { useMemo } from 'react'
import { D, S, STAGES, STAGE_LABEL, DATES, VT_ORDER } from '../store'
import { Bars, C, Card, KIND_COLOR, Kpi, Legend, TipKV, VT_COLOR } from '../lib/ui'
import { Columns, Donut, Spark } from '../lib/charts'
import { DOW, M, TL, compact, dM, dPct, n0, nf, pct, shortDate } from '../lib/fmt'
import type { ViewProps } from '../App'

/* Gün grafiğinin ölçüleri sabit: tıklanan sütunu bulmak için aynı sayılar
   hem çizimde hem de tıklama matematiğinde kullanılıyor. */
const DVW = 600
const DVH = 250
const DPAD = { l: 46, r: 12, t: 14, b: 34 }

const ST0 = S('Stage 0')
const ST3 = S('Stage 3')

/* Zincir uzunluğu ekseni şartnamedeki üst sınırdan türetilir. */
const CHAIN_SIZES = Array.from({ length: D.stages.meta.max_chain_stops }, (_, i) => String(i + 1))
const CHAIN_COLOR = [C.dim, C.blue, C.brand2, C.brand]

/* Doluluk histogramı: %0–100 aralığı eşit dilimlere bölünür. */
const FILL_STEP = 10
const FILL_BINS = 100 / FILL_STEP

/** Kpi.d varsayılan olarak yeşil; her fark iyi haber değil, rengi ezebilelim. */
function Delta({ t, c }: { t: string; c: string }) {
  return <span style={{ color: c }}>{t}</span>
}

/** Yüzde puan farkı; işaret fmt'teki delta biçimleriyle aynı. */
const dPts = (v: number) => (v < 0 ? '−' : '+') + nf(Math.abs(v), 1)

export default function Overview({ filter, setFilter, go }: ViewProps) {
  /* ── gün gün plan ───────────────────────────────────────── */
  const day = useMemo(() => {
    const desi = D.daily.map((r) => r.desi)
    const veh = D.daily.map((r) => r.vehicles)
    return { desi, veh, max: Math.max(...desi) * 1.12, peak: Math.max(...veh) }
  }, [])

  /* ── maliyet merdiveni ──────────────────────────────────── */
  const ladder = useMemo(
    () =>
      STAGES.map((k, i) => {
        const r = S(k)
        const p = i ? S(STAGES[i - 1]) : null
        return {
          k,
          r,
          gain: p ? r.total_cost - p.total_cost : 0,
          drop: p ? (r.total_cost / p.total_cost - 1) * 100 : 0,
        }
      }),
    [],
  )
  const ladderMax = Math.max(...ladder.map((s) => s.r.total_cost)) * 1.14
  const violations = ladder.reduce((a, s) => a + Number(s.r.violations), 0)

  /* ── filo karması ───────────────────────────────────────── */
  const mix = useMemo(() => {
    let rn = 0
    let sn = 0
    let rc = 0
    let sc = 0
    const fill = new Array(FILL_BINS).fill(0) as number[]
    for (const v of D.vehicles) {
      if (v.kind === 'Kiralık') {
        rn++
        rc += v.cost
      } else {
        sn++
        sc += v.cost
        fill[Math.min(FILL_BINS - 1, Math.floor(v.fill / FILL_STEP))]++
      }
    }
    return { rn, sn, rc, sc, fill }
  }, [])

  const hi = DATES.indexOf(filter.date)

  /* Aşama anlatısı — her cümle ölçülmüş bir sayıya dayanır. */
  const story = [
    <>
      Tahminden çıkan her sipariş grubu kendi aracına bindi: <b>{n0(ST0.routes)}</b> rota, ortalama
      doluluk <b>{pct(ST0.avg_fill)}</b>, <b>{n0(Number(ST0.spot_below_30))}</b> araç %30'un altında.
    </>,
    <>
      Aynı hattaki düşük dolulukların yükü komşu araca taşındı:{' '}
      <b>{n0(D.stages.repair.donors_considered)}</b> verici incelendi,{' '}
      <b>{n0(D.stages.repair.moves_accepted)}</b> taşıma kabul edildi ve{' '}
      <b>{n0(D.stages.repair.vehicles_removed)}</b> araç filodan çıktı.
    </>,
    <>
      Farklı hatlar tek zincire bağlandı: <b>{n0(D.stages.milkrun.pairs_evaluated)}</b> ikili ve{' '}
      <b>{n0(D.stages.milkrun.triples_evaluated)}</b> üçlü denendi,{' '}
      <b>{n0(D.stages.milkrun.chains_accepted)}</b> zincir{' '}
      <b>{n0(D.stages.milkrun.source_vehicles_replaced)}</b> aracın yerine geçti.
    </>,
    <>
      Zincirler yol üstündeki merkezden ek yük aldı:{' '}
      <b>{n0(D.stages.pickup.pairs_examined)}</b> çift tarandı,{' '}
      <b>{n0(D.stages.pickup.profitable_candidates)}</b> kârlı aday çıktı,{' '}
      <b>{n0(D.stages.pickup.pickups_accepted)}</b> yükleme kabul edildi.
    </>,
  ]

  return (
    <div className="stack">
      <p className="lead in">
        Yayınlanan nihai planın tamamı tek ekranda: <b>{D.meta.horizon[0]}</b> –{' '}
        <b>{D.meta.horizon[1]}</b> ufkunda <b>{n0(D.meta.plan_rows)}</b> plan satırı,{' '}
        <b>{n0(D.meta.vehicles)}</b> fiziksel araç ve <b>{n0(D.meta.legs)}</b> bacak. Her sayı
        yayınlanan plan dosyasından üretildi; fark rozetleri temel planla (Stage 0) karşılaştırır.
      </p>

      {/* ══════════ a) KPI şeridi ══════════ */}
      <div className="g6 in in-1">
        <Kpi
          v={M(D.meta.total_cost)}
          l="Toplam maliyet"
          tone="brand"
          d={<Delta t={`${dM(D.meta.total_cost - ST0.total_cost)} · ${dPct(ladderCumDrop(ladder))}`} c={C.ok} />}
          onClick={() => go('model')}
        />
        <Kpi
          v={pct((D.meta.sla_cost / D.meta.total_cost) * 100)}
          l="SLA cezasının maliyet içindeki payı"
          tone="warn"
          d={<Delta t={dM(D.meta.sla_cost - ST0.sla_penalty)} c={C.warn} />}
          onClick={() => go('kisit')}
        />
        <Kpi
          v={n0(D.meta.vehicles)}
          l="Fiziksel araç"
          d={<Delta t={dPct((D.meta.vehicles / ST0.routes - 1) * 100)} c={C.ok} />}
          onClick={() => go('filo')}
        />
        <Kpi
          v={n0(D.meta.legs)}
          l="Bacak (araç hareketi)"
          d={<Delta t={dPct((D.meta.legs / Number(ST0.segments) - 1) * 100)} c={C.ok} />}
          onClick={() => go('filo')}
        />
        <Kpi
          v={pct(D.meta.avg_fill)}
          l="Ortalama spot doluluk"
          tone="ok"
          d={<Delta t={`${dPts(D.meta.avg_fill - ST0.avg_fill)} puan`} c={C.ok} />}
          onClick={() => go('filo')}
        />
        <Kpi
          v={n0(D.meta.km)}
          l="Toplam km"
          unit="km"
          d={<Delta t={`${nf(D.meta.km / D.meta.legs, 0)} km / bacak`} c={C.dim} />}
          onClick={() => go('harita')}
        />
      </div>

      {/* ══════════ b) maliyet merdiveni ══════════ */}
      <Card
        title="Maliyet merdiveni"
        sub="yığılmış ₺ · araç maliyeti + SLA cezası"
        className="in in-2"
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0,1.5fr) minmax(0,1fr)',
            gap: 20,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', height: 316 }}>
              <Columns
                vw={760}
                vh={300}
                stacked
                pad={{ l: 62, r: 12, t: 16, b: 38 }}
                max={ladderMax}
                labels={ladder.map((s, i) => `S${i} · ${STAGE_LABEL[s.k]}`)}
                series={[
                  {
                    key: 'veh',
                    label: 'araç maliyeti',
                    color: C.brand,
                    values: ladder.map((s) => s.r.vehicle_cost),
                  },
                  {
                    key: 'sla',
                    label: 'SLA cezası',
                    color: C.warn,
                    values: ladder.map((s) => s.r.sla_penalty),
                  },
                ]}
                fmtY={(t) => compact(ladderMax * t)}
                fmtV={(v) => M(v)}
                sub={(i) => (i ? dPct(ladder[i].drop) : 'başlangıç')}
                tip={(i) => {
                  const s = ladder[i]
                  const rows: [string, string][] = [
                    ['araç maliyeti', TL(s.r.vehicle_cost, 0)],
                    ['SLA cezası', TL(s.r.sla_penalty, 0)],
                    ['toplam', TL(s.r.total_cost, 0)],
                    ['rota', n0(s.r.routes)],
                    ['ort. doluluk', pct(s.r.avg_fill)],
                    ['hakem ihlali', n0(Number(s.r.violations))],
                  ]
                  if (i) rows.push(['önceki aşamaya göre', dM(s.gain)])
                  return (
                    <>
                      <span className="h">
                        {s.k} · {STAGE_LABEL[s.k]}
                      </span>
                      <TipKV rows={rows} />
                    </>
                  )
                }}
              />
            </div>
            <Legend
              items={[
                [C.brand, 'araç maliyeti'],
                [C.warn, 'SLA cezası'],
              ]}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 11, minWidth: 0 }}>
            <p className="note c-dim" style={{ margin: 0 }}>
              Her aşama bir öncekinin planını girdi alır; kabul edilen tek hamle, toplam maliyeti
              düşürüp hiçbir kısıtı bozmayandır.
            </p>
            {ladder.map((s, i) => (
              <div key={s.k}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 9 }}>
                  <span className={i ? 'chip on' : 'chip'}>S{i}</span>
                  <b style={{ fontSize: 12.5, color: C.ink2 }}>{STAGE_LABEL[s.k]}</b>
                  <span style={{ flex: 1 }} />
                  <span className="num" style={{ fontSize: 12, color: i ? C.ok : C.dim }}>
                    {i ? dM(s.gain) : M(s.r.total_cost)}
                  </span>
                </div>
                <p className="note" style={{ marginTop: 5 }}>
                  {story[i]}
                </p>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ══════════ c) gün gün plan + araç türü karması ══════════ */}
      <div className="g2 in in-3">
        <Card
          title="Gün gün plan"
          sub={`${D.meta.horizon[0]} – ${D.meta.horizon[1]}`}
        >
          <div
            role="button"
            aria-label="Bir günü seçip haritada aç"
            title="Sütuna tıkla: o günü süz ve haritada aç"
            style={{ display: 'flex', flexDirection: 'column', height: 250, cursor: 'pointer' }}
            onClick={(e) => {
              const svg = e.currentTarget.querySelector('svg')
              if (!svg) return
              /* preserveAspectRatio=meet: içerik ortalanır, küçük eksene göre ölçeklenir. */
              const r = svg.getBoundingClientRect()
              const sc = Math.min(r.width / DVW, r.height / DVH)
              const vx = (e.clientX - r.left - (r.width - DVW * sc) / 2) / sc
              const i = Math.floor(((vx - DPAD.l) / (DVW - DPAD.l - DPAD.r)) * DATES.length)
              if (i < 0 || i >= DATES.length) return
              setFilter((f) => ({ ...f, date: DATES[i] }))
              go('harita')
            }}
          >
            <Columns
              vw={DVW}
              vh={DVH}
              pad={DPAD}
              max={day.max}
              highlight={hi}
              labels={D.daily.map((r) => r.d.slice(0, 5))}
              series={[{ key: 'desi', label: 'desi', color: C.blue, values: day.desi }]}
              fmtY={(t) => compact(day.max * t)}
              fmtV={(v) => compact(v)}
              sub={(i) => DOW[D.daily[i].dow]}
              tip={(i) => {
                const r = D.daily[i]
                return (
                  <>
                    <span className="h">{shortDate(r.d)}</span>
                    <TipKV
                      rows={[
                        ['desi', n0(r.desi)],
                        ['araç', n0(r.vehicles)],
                        ['bacak', n0(r.legs)],
                        ['kiralık / spot', `${n0(r.rent)} / ${n0(r.spot)}`],
                        ['maliyet', TL(r.cost, 0)],
                        ['SLA cezası', TL(r.sla, 0)],
                        ['km', n0(r.km)],
                      ]}
                    />
                  </>
                )
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginTop: 4 }}>
            <span className="note c-dim" style={{ whiteSpace: 'nowrap' }}>
              araç / gün
            </span>
            <Spark values={day.veh} w={168} h={26} color={C.brand} fill />
            <span className="num c-brand" style={{ fontSize: 11.5 }}>
              {n0(day.peak)}
            </span>
            <span className="note c-dim" style={{ whiteSpace: 'nowrap' }}>
              en yoğun gün
            </span>
          </div>
          <div className="chips" style={{ marginTop: 9 }}>
            {filter.date ? (
              <>
                <span className="chip on">{shortDate(filter.date)}</span>
                <button
                  type="button"
                  className="chip"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setFilter((f) => ({ ...f, date: '' }))}
                >
                  tüm ufuk
                </button>
              </>
            ) : (
              <span className="chip">sütuna tıkla → günü haritada aç</span>
            )}
          </div>
        </Card>

        <Card title="Araç türü karması" sub={`${n0(D.meta.vehicles)} fiziksel araç`}>
          <div style={{ display: 'flex', flexDirection: 'column', height: 250 }}>
            <Donut
              vw={480}
              vh={250}
              cx={126}
              center={n0(D.meta.vehicles)}
              centerSub="araç"
              items={VT_ORDER.map((t) => ({
                label: t,
                v: ST3.vehicle_mix[t] ?? 0,
                color: VT_COLOR[t],
              }))}
              onPick={(t) => {
                setFilter((f) => ({ ...f, vt: t }))
                go('filo')
              }}
            />
          </div>
          <p className="note" style={{ marginTop: 4 }}>
            Temel planda filonun <b>{n0(ST0.vehicle_mix['Kamyonet'])}</b> aracı kamyonetti; zincirler
            küçük yükleri birleştirince bu sayı <b>{n0(ST3.vehicle_mix['Kamyonet'])}</b>'e indi,
            kamyon <b>{n0(ST0.vehicle_mix['Kamyon'])}</b> → <b>{n0(ST3.vehicle_mix['Kamyon'])}</b>{' '}
            çıktı. Tır sayısı <b>{n0(ST3.vehicle_mix['Tır'])}</b> ile sabit: zorunlu kiralık rotalar.
            Bir dilime tıkla, filo gezginini o türle aç.
          </p>
        </Card>
      </div>

      {/* ══════════ d) kiralık/spot · zincir · doluluk ══════════ */}
      <div className="g3 in in-4">
        <Card title="Kiralık ve spot" sub="araç sayısı ve maliyet">
          <Bars
            nw={64}
            qw={82}
            rows={[
              {
                n: 'Kiralık',
                v: mix.rn,
                q: n0(mix.rn) + ' araç',
                col: KIND_COLOR['Kiralık'],
              },
              { n: 'Spot', v: mix.sn, q: n0(mix.sn) + ' araç', col: KIND_COLOR['Spot'] },
            ]}
          />
          <p className="note c-dim" style={{ margin: '13px 0 7px' }}>
            maliyet
          </p>
          <Bars
            nw={64}
            qw={82}
            rows={[
              { n: 'Kiralık', v: mix.rc, q: M(mix.rc), col: KIND_COLOR['Kiralık'] },
              { n: 'Spot', v: mix.sc, q: M(mix.sc), col: KIND_COLOR['Spot'] },
            ]}
          />
          <p className="note" style={{ marginTop: 13 }}>
            Kiralık taraf sözleşme gereği sabit: <b>{n0(D.rented.length)}</b> zorunlu rota tanımı,{' '}
            <b>{n0(mix.rn)}</b> araç. Optimizasyonun dokunabildiği kısım maliyetin{' '}
            <b>{pct((mix.sc / (mix.sc + mix.rc)) * 100)}</b>'ini oluşturan spot filo.
          </p>
        </Card>

        <Card
          title="Zincir uzunluğu"
          sub={`${n0(D.meta.chains)} çok duraklı zincir`}
        >
          <Bars
            nw={64}
            qw={86}
            rows={CHAIN_SIZES.map((k, i) => {
              const v = ST3.chain_size_counts[k] ?? 0
              return {
                n: k + ' durak',
                v,
                q: n0(v) + ' araç',
                col: CHAIN_COLOR[Math.min(i, CHAIN_COLOR.length - 1)],
              }
            })}
          />
          <p className="note" style={{ marginTop: 13 }}>
            Temel planda her araç tek duraklıydı ({n0(ST0.chain_size_counts['1'])} rota). Şimdi{' '}
            <b>{n0(D.meta.chains)}</b> araç birden çok merkeze uğruyor; şartnamenin izin verdiği en
            uzun zincir <b>{n0(D.stages.meta.max_chain_stops)}</b> durak ve o sınıra{' '}
            <b>{n0(ST3.chain_size_counts['4'])}</b> zincir dayandı.
          </p>
        </Card>

        <Card title="Doluluk dağılımı" sub={`${n0(mix.sn)} spot araç`}>
          <Bars
            nw={62}
            qw={52}
            rows={mix.fill.map((v, i) => ({
              n: `%${i * FILL_STEP}–${(i + 1) * FILL_STEP}`,
              v,
              q: n0(v),
              col: i < 3 ? C.bad : i < 6 ? C.warn : i < 8 ? C.blue : C.ok,
            }))}
          />
          <p className="note" style={{ marginTop: 13 }}>
            Ağırlık sağ uca kaydı: %30'un altında kalan spot araç{' '}
            <b>{n0(Number(ST0.spot_below_30))}</b> iken <b>{n0(Number(ST3.spot_below_30))}</b> oldu,
            ortalama doluluk <b>{pct(ST0.avg_fill)}</b> → <b>{pct(D.meta.avg_fill)}</b>.
          </p>
        </Card>
      </div>

      {/* ══════════ e) nihai planın özeti ══════════ */}
      <Card title="Nihai planın özeti" sub="beş madde, beş ölçüm" className="in in-5">
        <div className="g2" style={{ alignItems: 'start' }}>
          <div className="stack" style={{ gap: 10 }}>
            <p className="note hl">
              <b>Konsolidasyon zincirleri.</b> {n0(D.stages.milkrun.chains_accepted)} zincir,{' '}
              {n0(D.stages.milkrun.source_vehicles_replaced)} tekil aracın yerine geçti;{' '}
              {n0(D.stages.milkrun.parts_consolidated)} sipariş parçası ve{' '}
              {compact(D.stages.milkrun.desi_consolidated)} desi aynı araca bindi. Zincirlerin{' '}
              {n0(ST3.chain_size_counts['2'])}'si iki, {n0(ST3.chain_size_counts['3'])}'ü üç,{' '}
              {n0(ST3.chain_size_counts['4'])}'si dört duraklı.
            </p>
            <p className="note hl">
              <b>Yol üstü yük alma.</b> {n0(D.stages.pickup.pairs_examined)} çift tarandı,{' '}
              {n0(D.stages.pickup.profitable_candidates)} kârlı aday çıktı,{' '}
              {n0(D.stages.pickup.pickups_accepted)} tanesi kabul edildi:{' '}
              {n0(D.stages.pickup.parts_picked_up)} parça ve{' '}
              {n0(D.stages.pickup.desi_picked_up)} desi ayrı araç açılmadan taşındı,{' '}
              {n0(D.stages.pickup.donor_vehicles_removed)} verici araç filodan düştü.
            </p>
            <p className="note hl">
              <b>Sıfır ihlal.</b> Dört aşamanın dördünde de hakem ihlali {n0(violations)}: kapasite,
              elleçleme kotası, tır ziyaret kotası ve zaman kısıtları{' '}
              {n0(D.meta.plan_rows)} plan satırının tamamında sağlandı.
            </p>
          </div>
          <div className="stack" style={{ gap: 10 }}>
            <p className="note hl">
              <b>Doluluk.</b> Ortalama spot doluluk {pct(ST0.avg_fill)} → {pct(D.meta.avg_fill)};
              %30 altında kalan araç {n0(Number(ST0.spot_below_30))} → {n0(Number(ST3.spot_below_30))}.
              Bacak bazında ağırlıklı doluluk {pct(D.meta.avg_fill_leg)} — zincirlerin ilk bacağı
              dolu çıkıp yol üstünde boşalıyor.
            </p>
            <p className="note hl">
              <b>Takas bilinçli.</b> SLA cezası {M(ST0.sla_penalty)} → {M(D.meta.sla_cost)} yükseldi;
              buna karşılık araç maliyeti {M(ST0.vehicle_cost)} → {M(ST3.vehicle_cost)} düştü. Net
              sonuç {dM(D.meta.total_cost - ST0.total_cost)} ({dPct(ladderCumDrop(ladder))}): birkaç
              siparişi bir gün geç teslim etmek, yarı boş araç kaldırmaktan ucuz.
            </p>
            <p className="note hl">
              <b>Ölçek.</b> {D.meta.horizon[0]} – {D.meta.horizon[1]} ufkunda{' '}
              {n0(D.meta.vehicles)} araç, {n0(D.meta.legs)} bacak, {n0(D.meta.km)} km ve{' '}
              {compact(D.meta.desi)} desi; günlük en yoğun nokta {n0(day.peak)} araç.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

/** Stage 0 → Stage 3 toplam düşüş yüzdesi. */
function ladderCumDrop(l: { r: { total_cost: number } }[]): number {
  return (l[l.length - 1].r.total_cost / l[0].r.total_cost - 1) * 100
}
