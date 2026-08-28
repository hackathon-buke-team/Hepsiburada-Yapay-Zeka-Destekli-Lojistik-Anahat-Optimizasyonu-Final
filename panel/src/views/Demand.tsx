import { useMemo } from 'react'
import { D, NAME } from '../store'
import type { ViewProps } from '../App'
import { Bars, C, Card, Kpi, Legend, TipKV, useCountUp } from '../lib/ui'
import { Area, CalendarHeat, Columns } from '../lib/charts'
import { AY, DOW, DOW_LONG, compact, dPct, n0, nf, pct01, shortDate } from '../lib/fmt'

/* ══════════════════════════════════════════════════════════════════════
   GÖRÜNÜM 5 — Talep ve tahmin
   Modelin girdisi (179 günlük geçmiş) ve çıktısı (7 günlük tahmin).
   ══════════════════════════════════════════════════════════════════════ */

const H = D.history
const CL = D.stages.cleaning
const CAL = D.stages.calendar
const FVD = D.stages.forecast_vs_dow
const BT = D.stages.backtest
const FC = D.forecast

const p2 = (v: number) => String(v).padStart(2, '0')

/** Geçmişin i. günü. Yerel saat kullanılır — toISOString gün kaydırabilir. */
const dayAt = (i: number) => {
  const d = new Date(H.start + 'T00:00:00')
  d.setDate(d.getDate() + i)
  return d
}
const dmy = (d: Date) => `${p2(d.getDate())}.${p2(d.getMonth() + 1)}.${d.getFullYear()}`
const isoOf = (d: Date) => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`

/* takvim ısı haritası kendi doğal genişliğinde çizilsin (ölü boşluk olmasın) */
const CELL = 15
const GAP = 3
/* CalendarHeat içindeki sol eksen payı (30) + sağ nefes payı (8) ile aynı olmalı */
const CAL_X0 = 30
const CAL_PAD_R = 8
const WEEK = 7
const CAL_VW = CAL_X0 + Math.ceil((H.dow0 + H.days.length) / WEEK) * (CELL + GAP) + CAL_PAD_R

/** listede gösterilen en yoğun hat sayısı */
const TOP_LANES = 12

export default function Demand({ go }: ViewProps) {
  const daily = FC.daily
  const cu = useCountUp(FC.total)

  const hmax = useMemo(() => Math.max(...H.days) * 1.06, [])
  const exMap = useMemo(() => new Map(H.excluded.map((e) => [e.iso, e])), [])

  /** takvimdeki bayrak sayıları: 0 normal · 1 resmî tatil · 2 ay sonu */
  const flagN = useMemo(() => {
    const c = [0, 0, 0]
    for (const f of H.flag) c[f]++
    return c
  }, [])

  /** ay sonu rejimi kaç gün sürüyor — bayrak dizisindeki 2'li serinin uzunluğu */
  const meSpan = useMemo(() => {
    let best = 0
    let run = 0
    for (const f of H.flag) {
      run = f === 2 ? run + 1 : 0
      if (run > best) best = run
    }
    return best
  }, [])

  /** ay sonu çiftinin ikinci günü = ayın son günü; çizgide bunu işaretliyoruz */
  const marks = useMemo(
    () =>
      H.flag
        .map((f, i) => (f === 2 && H.flag[i + 1] !== 2 ? i : -1))
        .filter((i) => i >= 0)
        .map((i) => {
          const d = dayAt(i)
          return { i, color: C.brand, label: `${p2(d.getDate())} ${AY[d.getMonth()]}` }
        }),
    [],
  )

  /* ── takvim + çizgi ortak ipucu ────────────────────────────── */
  const dayTip = (i: number) => {
    const d = dayAt(i)
    const ex = exMap.get(isoOf(d))
    const v = H.days[i]
    const rows: Parameters<typeof TipKV>[0]['rows'] = [
      ['desi', n0(v)],
      ['normal güne oran', pct01(v / H.median)],
    ]
    if (ex?.h) rows.push(['tatil', ex.h])
    if (ex?.me) rows.push(['ay sonu', `son ${n0(meSpan)} gün`])
    return (
      <>
        <span className="h">{shortDate(dmy(d))}</span>
        <TipKV rows={rows} />
        {ex && (
          <div className="c-brand mono" style={{ marginTop: 7, fontSize: 10.5 }}>
            eğitim setinden çıkarıldı
          </div>
        )}
      </>
    )
  }

  /* ── dışlanan tarihler ─────────────────────────────────────── */
  const holN = H.excluded.filter((e) => e.h).length
  const meN = H.excluded.filter((e) => e.me === 1).length
  /** hem resmî tatil hem ay sonu olan tarihler — iki etiket, tek satır */
  const bothDays = H.excluded.filter((e) => e.h && e.me === 1).map((e) => e.d)
  const bothList =
    bothDays.length > 1
      ? bothDays.slice(0, -1).join(', ') + ' ve ' + bothDays[bothDays.length - 1]
      : bothDays.join('')
  const deepest = useMemo(() => H.excluded.reduce((a, b) => (b.r < a.r ? b : a)), [])

  const exRows: Parameters<typeof Bars>[0]['rows'] = useMemo(
    () =>
      H.excluded.map((e) => {
        const both = !!e.h && e.me === 1
        return {
          key: e.iso,
          n: (
            <span>
              <span className="mono c-dim">{e.d}</span>
              {' · '}
              {e.h || 'ay sonu'}
              {both && <span className="c-brand"> + ay sonu</span>}
            </span>
          ),
          v: e.r,
          q: pct01(e.r),
          cls: e.me === 1 ? 'hi' : 'z',
          col: both
            ? `linear-gradient(90deg, ${C.warn}, ${C.brand})`
            : e.me === 1
              ? C.brand
              : C.warn,
        }
      }),
    [],
  )

  /* ── takvim çarpanları ─────────────────────────────────────── */
  const calRows: Parameters<typeof Bars>[0]['rows'] = [
    { key: 'b1', n: 'ay sonu −1 gün', v: CAL.day_before_month_end, q: '×' + nf(CAL.day_before_month_end), cls: 'z', col: C.warn },
    { key: 'me', n: 'ayın son günü', v: CAL.month_end, q: '×' + nf(CAL.month_end), cls: 'hi', col: C.brand },
    { key: 'a1', n: 'ayın ilk günü', v: CAL.first_day_after_month_end, q: '×' + nf(CAL.first_day_after_month_end), cls: '', col: C.ok },
    { key: 'no', n: 'normal gün', v: CAL.normal, q: '×' + nf(CAL.normal), cls: '', col: C.dim },
  ]

  /* ── geri-test ─────────────────────────────────────────────── */
  const btKeys = Object.keys(BT)
  const btMax = Math.max(...btKeys.flatMap((k) => [BT[k].naive, BT[k].dow_median, BT[k].ours])) * 1.2
  const btSame = btKeys.filter((k) => BT[k].ours === BT[k].dow_median)
  const btWin = btKeys.filter((k) => BT[k].ours < BT[k].dow_median)

  /* ── tahmin ufku ───────────────────────────────────────────── */
  /** ufuk içinde ay değişimi: ay sonu günü (planın kritik günü) */
  const meIdx = daily.findIndex(
    (x, i) => i + 1 < daily.length && x.iso.slice(5, 7) !== daily[i + 1].iso.slice(5, 7),
  )
  const firstMonth = daily.filter((x) => x.iso.slice(0, 7) === daily[0].iso.slice(0, 7))
  const fMax = Math.max(...daily.map((x) => x.desi)) * 1.16
  const fvdMax = Math.max(...FVD.forecast, ...FVD.dow_mean) * 1.16

  const slotKeys = Object.keys(FC.slot).sort((a, b) => Number(a) - Number(b))
  const slotTot = slotKeys.reduce((a, k) => a + FC.slot[k], 0)

  const top = FC.lane.slice(0, TOP_LANES)
  const topSum = top.reduce((a, l) => a + l.desi, 0)
  const laneRows: Parameters<typeof Bars>[0]['rows'] = useMemo(
    () =>
      top.map((l, i) => ({
        key: l.a + '-' + l.b,
        n: (
          <span>
            <span className="mono c-dim">{p2(i + 1)}</span> {NAME[l.a]} → {NAME[l.b]}
          </span>
        ),
        v: l.desi,
        q: compact(l.desi),
        cls: i < 3 ? ('hi' as const) : ('' as const),
      })),
    [],
  )

  return (
    <div className="stack">
      <p className="lead">
        Modelin <b>girdisi</b> ve <b>çıktısı</b> aynı ekranda: {n0(H.days.length)} günlük geçmiş talep
        ve ondan ürettiğimiz {n0(daily.length)} günlük tahmin. Ayrıca hangi günleri eğitim setinden
        çıkardığımızı, <b>neden</b> çıkardığımızı ve bu kararın dondurulmuş bir geri-testte ne
        kazandırdığını gösteriyoruz.
      </p>

      {/* ── a) KPI şeridi ───────────────────────────────────── */}
      <div className="g4 in in-1">
        <Kpi
          v={n0(CL.raw_rows)}
          l="ham geçmiş talep satırı"
          d={`${n0(CL.od_in_history)} farklı çıkış-varış çifti`}
        />
        <Kpi
          v={n0(H.days.length)}
          unit="gün"
          l="geçmiş gözlem penceresi"
          d={`${dmy(dayAt(0))} → ${dmy(dayAt(H.days.length - 1))}`}
        />
        <Kpi
          v={n0(FC.rows)}
          l="tahmin satırı — hat × gün × saat dilimi"
          d={`${n0(FC.zero)} satırda sıfır tahmin`}
        />
        <Kpi
          v={compact(cu)}
          tone="brand"
          l="tahmin edilen toplam desi"
          d={`${n0(daily.length)} gün · ${n0(CL.od_in_history)} aktif hat`}
        />
      </div>

      {/* ── b) geçmiş hacim: takvim + çizgi ─────────────────── */}
      <div className="g2 in in-2">
        <Card title={`${n0(H.days.length)} günlük geçmiş hacim`} sub="günlük toplam desi">
          <CalendarHeat
            start={H.start}
            dow0={H.dow0}
            days={H.days}
            flag={H.flag}
            median={H.median}
            vw={CAL_VW}
            cell={CELL}
            gap={GAP}
            tip={dayTip}
          />
          <Legend
            items={[
              [C.blue, 'normal gün — koyu az, açık çok desi'],
              [C.warn, `resmî tatil · ${n0(flagN[1])} gün (yalnız tatil)`],
              [C.brand, `ay sonu · ${n0(flagN[2])} gün`],
            ]}
          />
        </Card>

        <Card title="Aynı veri, çizgi hâli" sub="ayın son günleri işaretli">
          <div style={{ display: 'flex', minHeight: 170 }}>
            <Area
              values={H.days}
              vw={560}
              vh={206}
              color={C.blue}
              max={hmax}
              fmtY={(t) => compact(t * hmax)}
              marks={marks}
              labels={[dmy(dayAt(0)), dmy(dayAt(H.days.length - 1))]}
              tip={dayTip}
              id="hist"
            />
          </div>
          <p className="note">
            Her ay sonunda talep neredeyse sıfıra iniyor, ertesi gün normalin üstüne çıkarak geri
            dönüyor. Bu düzensiz bir sıçrama değil, <b>tekrar eden bir rejim</b>: ortalamayla
            bastırılırsa arka arkaya iki gün birden yanlış tahmin edilir.
          </p>
        </Card>
      </div>

      {/* ── c) dışlama + d) çarpanlar + f) geri-test ────────── */}
      <div className="g2 in in-3">
        <Card
          title={`Neden ${n0(H.excluded.length)} tarih dışlandı`}
          sub={`${n0(CL.excluded_grid_rows)} ızgara satırı eğitim dışı`}
        >
          <p className="def">
            Dışlama <em>yalnız eğitim verisine</em> uygulanır; hedef günler asla elenmez. Bu günler
            gürültü değil <em>başka bir rejim</em>: bayram ve ay sonu davranışı normal gün
            davranışının üstüne ortalanırsa iki rejim de bozulur.
            <br />
            <b>{n0(holN)}</b> resmî tatil + <b>{n0(meN)}</b> ay sonu günü = {n0(holN + meN)} etiket;
            ancak <b>{bothList}</b> ikisine birden giriyor → <b>{n0(H.excluded.length)}</b> ayrı
            tarih. Listede bu {n0(bothDays.length)} gün <em>+ ay sonu</em> ile ayrıca işaretli.
            <br />
            Ufkun ilk ayı bilerek listede yok: <b>{firstMonth.map((x) => x.d).join(' ve ')}</b> tahmin
            ufkunun <em>içinde</em> — eğitimden atılacak değil, tahmin edilecek gün.
          </p>
          <Bars rows={exRows} nw={214} qw={58} />
          <p className="note" style={{ marginTop: 11 }}>
            Oran = o günün desisi ÷ {n0(H.days.length)} günün medyanı ({n0(H.median)} desi). En dip
            gün <b>{deepest.d}</b> · {deepest.h} · {pct01(deepest.r, 2)}.
          </p>
        </Card>

        <div className="stack">
          <Card title="Takvim çarpanları" sub={`${n0(H.days.length)} günden ölçüldü`}>
            <Bars rows={calRows} nw={122} qw={52} />
            <p className="note" style={{ marginTop: 11 }}>
              Bu katsayılar <b>seçilmedi, ölçüldü</b>: geçmişteki ay sonu pencerelerinden doğrudan
              hesaplandı — ay ay elle ayarlanmış tek bir sayı yok. Ayın son gününde talebin{' '}
              {pct01(1 - CAL.month_end)} kadarı kayboluyor, ertesi gün normalin{' '}
              {dPct((CAL.first_day_after_month_end - 1) * 100)} üstüne çıkıyor.
            </p>
          </Card>

          <Card title="Dondurulmuş geri-test" sub="düşük iyi · WAPE">
            <div style={{ display: 'flex', minHeight: 180 }}>
              <Columns
                labels={btKeys}
                series={[
                  { key: 'naive', label: 'saf', color: C.dim, values: btKeys.map((k) => BT[k].naive) },
                  { key: 'dow', label: 'gün-türü medyanı', color: C.blue, values: btKeys.map((k) => BT[k].dow_median) },
                  { key: 'ours', label: 'bizim model', color: C.brand, values: btKeys.map((k) => BT[k].ours) },
                ]}
                vw={470}
                vh={218}
                max={btMax}
                fmtY={(t) => pct01(t * btMax, 0)}
                pad={{ l: 46, r: 10, t: 12, b: 30 }}
                tip={(i) => (
                  <>
                    <span className="h">{btKeys[i]}</span>
                    <TipKV
                      rows={[
                        ['saf (son hafta)', pct01(BT[btKeys[i]].naive)],
                        ['gün-türü medyanı', pct01(BT[btKeys[i]].dow_median)],
                        ['bizim model', pct01(BT[btKeys[i]].ours)],
                      ]}
                    />
                  </>
                )}
              />
            </div>
            <Legend
              items={[
                [C.dim, 'saf — geçen haftayı kopyala'],
                [C.blue, 'gün-türü medyanı'],
                [C.brand, 'bizim model'],
              ]}
            />
            <div style={{ marginTop: 10 }}>
              {btSame.map((k) => (
                <p className="note" key={k}>
                  <b>{k}:</b> bizim model gün-türü medyanının aynısı ({pct01(BT[k].ours)}) — takvim
                  katmanı devreye girmiyor, dolayısıyla zarar da vermiyor.
                </p>
              ))}
              {btWin.map((k) => (
                <p className="note hl" key={k}>
                  <b>{k}:</b> hata {pct01(BT[k].dow_median)} → {pct01(BT[k].ours)}; bağıl kazanç{' '}
                  <b className="c-ok">{pct01((BT[k].dow_median - BT[k].ours) / BT[k].dow_median)}</b>.
                </p>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* ── e) tahminimiz vs sıradan bir gün ────────────────── */}
      <Card
        className="in in-4"
        title="Tahminimiz vs sıradan bir gün"
        sub="aynı hafta, iki farklı yöntem"
      >
        <div style={{ display: 'flex', minHeight: 230 }}>
          <Columns
            labels={daily.map((x) => x.d)}
            sub={(i) => DOW[daily[i].dow]}
            series={[
              { key: 'ours', label: 'tahminimiz', color: C.brand, values: FVD.forecast },
              { key: 'dow', label: 'gün-türü ortalaması', color: C.blue, values: FVD.dow_mean },
            ]}
            highlight={meIdx}
            max={fvdMax}
            fmtY={(t) => compact(t * fvdMax)}
            vw={900}
            vh={252}
            pad={{ l: 54, r: 12, t: 14, b: 40 }}
            tip={(i) => (
              <>
                <span className="h">
                  {daily[i].d} · {DOW_LONG[daily[i].dow]}
                </span>
                <TipKV
                  rows={[
                    ['tahminimiz', n0(FVD.forecast[i])],
                    ['gün-türü ortalaması', n0(Math.round(FVD.dow_mean[i]))],
                    ['fark', dPct((FVD.forecast[i] / FVD.dow_mean[i] - 1) * 100)],
                  ]}
                />
              </>
            )}
          />
        </div>
        <Legend
          items={[
            [C.brand, 'tahminimiz — takvim katmanlı'],
            [C.blue, 'gün-türü ortalaması — takvimi görmeyen sıradan gün'],
          ]}
        />
        {meIdx >= 0 && (
          <p className="note hl" style={{ marginTop: 11 }}>
            Ay sonunda (<b>{daily[meIdx].d}</b>) sıradan bir gün-türü ortalaması{' '}
            {compact(FVD.dow_mean[meIdx])} desi yazardı; biz {compact(FVD.forecast[meIdx])} desi
            diyoruz — {pct01(1 - FVD.forecast[meIdx] / FVD.dow_mean[meIdx])} daha düşük.
            {meIdx + 1 < daily.length && (
              <>
                {' '}
                Ertesi gün (<b>{daily[meIdx + 1].d}</b>) ise ters yön:{' '}
                {dPct((FVD.forecast[meIdx + 1] / FVD.dow_mean[meIdx + 1] - 1) * 100)} daha yüksek.
              </>
            )}{' '}
            İki hareket de aynı ölçülmüş takvim katmanından geliyor; filo bu iki günün gerçek şekline
            göre boyutlanıyor.
          </p>
        )}
      </Card>

      {/* ── g) 7 günlük tahmin + en yoğun hatlar ────────────── */}
      <div className="g2 in in-5">
        <Card
          title={`${n0(daily.length)} günlük tahminimiz`}
          sub="çıkış günü bazında toplam desi"
        >
          <div style={{ display: 'flex', minHeight: 210 }}>
            <Columns
              labels={daily.map((x) => x.d)}
              sub={(i) => DOW[daily[i].dow]}
              series={[{ key: 'desi', label: 'desi', color: C.blue, values: daily.map((x) => x.desi) }]}
              max={fMax}
              fmtY={(t) => compact(t * fMax)}
              fmtV={(v) => compact(v)}
              vw={480}
              vh={246}
              pad={{ l: 48, r: 10, t: 16, b: 40 }}
              tip={(i) => (
                <>
                  <span className="h">
                    {daily[i].d} · {DOW_LONG[daily[i].dow]}
                  </span>
                  <TipKV
                    rows={[
                      ['desi', n0(daily[i].desi)],
                      ['gün-türü medyanı', n0(H.dowmed[String(daily[i].dow)])],
                      ['ufuktaki pay', pct01(daily[i].desi / FC.total)],
                    ]}
                  />
                </>
              )}
            />
          </div>
          <p className="note" style={{ marginTop: 9 }}>
            Teslim saati dilimine göre:{' '}
            {slotKeys.map((k, i) => (
              <span key={k}>
                {i > 0 && ' · '}
                <b>{p2(Number(k))}:00</b> {compact(FC.slot[k])} desi ({pct01(FC.slot[k] / slotTot)})
              </span>
            ))}
          </p>
        </Card>

        <Card
          title={`En yoğun ${n0(top.length)} hat`}
          sub={`${n0(CL.od_in_history)} aktif hattın en yoğun ${n0(FC.lane.length)}'ı içinden`}
        >
          <Bars rows={laneRows} nw={186} qw={62} />
          <p className="note" style={{ marginTop: 11 }}>
            Bu {n0(top.length)} hat, tahmin edilen desinin <b>{pct01(topSum / FC.total)}</b> kadarını
            taşıyor. Yoğunluk birkaç ana merkezde toplandığı için konsolidasyon (milk-run) burada
            anlamlı; kuyruktaki hatlar tek tek küçük ve dağınık.
          </p>
        </Card>
      </div>

      <div className="rowf in in-6" style={{ alignItems: 'center' }}>
        <p className="note grow">
          Bu tahmin, planlayıcının tek girdisidir: her satır bir (hat, gün, saat dilimi) için desi.
          Araç seçimi, konsolidasyon ve SLA kararlarının tamamı bu tablonun üstüne kuruluyor.
        </p>
        <button type="button" className="btn" onClick={() => go('model')}>
          Model ve boru hattı →
        </button>
      </div>
    </div>
  )
}
