import { useMemo, useState } from 'react'
import type { ViewProps } from '../App'
import { D, HAND_TOTAL, NAME, TIR_TOTAL, laneOf } from '../store'
import { C, Card, Icon, Kpi, Legend, Seg, TipKV } from '../lib/ui'
import { Matrix, Meter } from '../lib/charts'
import { M, TL, n0, pct01, shortDate } from '../lib/fmt'

/* ══════════════════════════════════════════════════════════════════════
   Kısıt kullanımı — "0 ihlal" iddiasının görsel kanıtı.
   İki sert kısıt aynı ızgarada okunur: merkez-gün elleçleme kotası ve
   merkez-gün tır ziyaret kotası. Elleçleme için iki defter tutuyoruz:
     · hakem defteri  — yalnız o merkezde yüklenen/indirilen desi
     · üst sınır      — panel.json loadgrid: bacağın tüm desisi iki uca da
                        yazılır (aktarmadan geçen yük iki kez sayılır)
   Hakem simülatörü birincisini sayar; ikincisini kötümser sınır olarak
   gösteriyoruz ki tablo abartılı görünmesin, saklanmasın da.
   ══════════════════════════════════════════════════════════════════════ */

type Mode = 'defter' | 'ust'

const ND = D.loadgrid[0].length
const NC = D.centres.length

/** Kotanın bağlayıcı sayıldığı doluluk eşiği (Meter'ın warnAt'i ile aynı). */
const WARN_AT = 0.85
/** Kayan nokta toleransı — yalnız bunun üstü gerçek ihlaldir. */
const OVER_AT = 1.0005

const pad2 = (n: number) => String(n).padStart(2, '0')

/** "29.06.2026" -> "29.06" (ızgara sütun başlığı) */
const ddmm = (dmy: string) => dmy.split('.').slice(0, 2).join('.')

/** Izgara sütunları: ufuk günleri + son varışların taştığı ufuk sonrası gün. */
const DAY = Array.from({ length: ND }, (_, c) => {
  if (c < D.daily.length) return { d: D.daily[c].d, post: false }
  const dt = new Date(D.meta.start + 'T00:00:00')
  dt.setDate(dt.getDate() + c)
  return { d: `${pad2(dt.getDate())}.${pad2(dt.getMonth() + 1)}.${dt.getFullYear()}`, post: true }
})

/* Her iki defter de kaynak/build_panel_data.py'de üretilir: gece yarısını
   aşan elleçleme, işlem süresiyle orantılı olarak iki güne bölünür. */
const LEDGER = D.loadgrid

/** '#57a6ff' -> '87,166,255'. Isı haritası paletle aynı kaynaktan beslenir. */
const rgb = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)).join(',')

const RGB = { blue: rgb(C.blue), warn: rgb(C.warn), bad: rgb(C.bad) }

/** Süzgeç etkinken seçili gün dışındaki sütunların sönümü. */
const FADE = 0.28
const dim = (faded: boolean) => (faded ? FADE : 1)

/** İşlemsiz hücre ve ihlal hücresi — açıklama şeridiyle birebir aynı dolgu. */
const emptyFill = (k: number) => `rgba(255,255,255,${(0.04 * k).toFixed(3)})`
const overFill = (k: number) => `rgba(${RGB.bad},${(0.92 * k).toFixed(3)})`

/** 0–1 doluluk -> renk. Süzgeç etkinken seçili gün dışındaki sütunlar soluk. */
const heat = (t: number, faded: boolean) => {
  const k = dim(faded)
  if (t <= 0) return emptyFill(k)
  if (t > OVER_AT) return overFill(k)
  if (t >= WARN_AT) return `rgba(${RGB.warn},${(0.9 * k).toFixed(3)})`
  return `rgba(${RGB.blue},${((0.13 + 0.72 * Math.min(1, t / WARN_AT)) * k).toFixed(3)})`
}

const CELL = 34
const ROWW = 116

export default function Constraints({ filter, setFilter, go }: ViewProps) {
  const [mode, setMode] = useState<Mode>('defter')
  const grid = mode === 'ust' ? D.loadgrid_ust : LEDGER

  /* ── elleçleme defteri özeti ───────────────────────────────── */
  const hand = useMemo(() => {
    const cells: { r: number; c: number; v: number; cap: number; t: number }[] = []
    for (let r = 0; r < NC; r++)
      for (let c = 0; c < ND; c++) {
        const v = grid[r][c]
        if (v > 0) cells.push({ r, c, v, cap: D.centres[r].hand, t: v / D.centres[r].hand })
      }
    cells.sort((a, b) => b.t - a.t)
    return {
      top: cells.slice(0, 10),
      active: cells.length,
      over: cells.filter((x) => x.t > OVER_AT).length,
      peak: cells[0],
    }
  }, [grid])

  /* ── tır ziyaret defteri özeti ─────────────────────────────── */
  const tir = useMemo(() => {
    let visits = 0
    let full = 0
    let over = 0
    for (let r = 0; r < NC; r++)
      for (let c = 0; c < ND; c++) {
        const v = D.tirgrid[r][c]
        const q = D.centres[r].tir
        visits += v
        if (q > 0 && v === q) full++
        if (v > q) over++
      }
    return { visits, full, over, zero: D.centres.map((_, i) => i).filter((i) => D.centres[i].tir === 0) }
  }, [])

  /* ── zorunlu kiralıkların peşinen yediği tır ziyareti ──────── */
  const rentVisit = useMemo(() => {
    const v = new Array<number>(NC).fill(0)
    for (const r of D.rented)
      if (r.t === 'Tır') {
        v[r.a] += r.n
        v[r.b] += r.n
      }
    return v
  }, [])

  /* ── zincirlerin ara durakları: tır kotası sıfır olan merkezler ── */
  const midZero = useMemo(() => {
    const cnt = new Array<number>(NC).fill(0)
    for (const v of D.vehicles)
      if (v.stops > 1) for (let i = 1; i < v.path.length - 1; i++) cnt[v.path[i]]++
    return {
      stops: tir.zero.reduce((a, i) => a + cnt[i], 0),
      top: tir.zero
        .slice()
        .sort((a, b) => cnt[b] - cnt[a])
        .slice(0, 3)
        .map((i) => NAME[i]),
    }
  }, [tir.zero])

  const late = useMemo(() => D.legs.filter((l) => l.sla > 0).sort((a, b) => b.sla - a.sla), [])

  const selC = DAY.findIndex((d) => d.d === filter.date)
  const cols = DAY.map((d) => ddmm(d.d) + (d.post ? '*' : ''))
  const pickDay = (c: number) => {
    if (DAY[c].post) return
    setFilter((p) => ({ ...p, date: p.date === DAY[c].d ? '' : DAY[c].d }))
  }

  const rentTir = D.rented.reduce((a, r) => a + (r.t === 'Tır' ? r.n : 0), 0)
  const rentAll = D.rented.reduce((a, r) => a + r.n, 0)

  return (
    <div className="stack">
      <div className="in in-1">
        <p className="lead">
          Planın operasyonel kısıtları ne kadar zorladığına bakıyoruz. İki sert kısıt var: merkez
          başına <b>günlük elleçleme kotası</b> ve merkez başına <b>günlük tır ziyaret kotası</b>.
          Aşağıdaki iki ısı haritası {n0(NC)} merkezin {n0(ND)} günlük kota kullanımının tamamıdır —
          hakem simülatörünün saydığı defterin birebir aynısı. Bir hücreye tıklayınca o gün tüm
          panoda süzülür.
        </p>
        <div className="def">
          <b>Elleçleme kotası</b> merkez başına <em>günlüktür</em> ve 00:00'da sıfırlanır; gece
          yarısını aşan bir elleçleme işlemi iki güne süresiyle orantılı bölünür — gece kalkışları
          bu yüzden kotayı iki güne yayar. {n0(NC)} merkezin toplamı {n0(HAND_TOTAL)} desi/gün.{' '}
          <b>Tır kotası</b> ise gün içindeki <em>ziyaret</em> sayısıdır: aynı seferin çıkışı ve
          varışı ayrı ayrı sayılır, {n0(tir.zero.length)} merkezde kota sıfırdır ve zorunlu kiralık
          seferler de bu kotadan yer. Ülke toplamı {n0(TIR_TOTAL)} ziyaret/gün.
        </div>
      </div>

      <div className="g4 in in-2">
        <Kpi
          v={n0(tir.over)}
          l="tır ziyaret kotası ihlali"
          tone="ok"
          d={`${n0(tir.visits)} ziyaretin tamamı kota içinde`}
        />
        <Kpi
          v={n0(tir.full)}
          l="tır kotasının tamamen dolduğu merkez-gün"
          tone="warn"
          d={<span className="c-warn">kotanın bağlayıcı olduğu hücreler</span>}
        />
        <Kpi
          v={n0(hand.over)}
          l="elleçleme kotası aşımı (merkez-gün)"
          tone={hand.over ? 'bad' : 'ok'}
          d={
            <span className={hand.over ? 'c-bad' : 'c-ok'}>
              {mode === 'defter' ? 'hakem defteri' : 'üst sınır kipi'} · {n0(hand.active)} etkin
              merkez-gün
            </span>
          }
        />
        <Kpi
          v={hand.peak ? pct01(hand.peak.t) : '—'}
          l="en yüksek elleçleme doluluğu"
          tone={hand.peak && hand.peak.t > OVER_AT ? 'bad' : 'ok'}
          d={hand.peak ? `${NAME[hand.peak.r]} · ${shortDate(DAY[hand.peak.c].d)}` : ''}
        />
      </div>

      <div className="g2 in in-3">
        {/* ── elleçleme ısı haritası ─────────────────────────── */}
        <Card
          title="Elleçleme kotası kullanımı"
          sub={
            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {filter.date && (
                <button
                  type="button"
                  className="btn on"
                  onClick={() => setFilter((p) => ({ ...p, date: '' }))}
                  title="Gün süzgecini kaldır"
                >
                  {Icon.close}
                  {filter.date}
                </button>
              )}
              <Seg<Mode>
                value={mode}
                onChange={setMode}
                options={[
                  { v: 'defter', l: 'hakem defteri' },
                  { v: 'ust', l: 'üst sınır' },
                ]}
              />
            </span>
          }
        >
          <Matrix
            rows={NAME}
            cols={cols}
            cell={CELL}
            rowW={ROWW}
            value={(r, c) => grid[r][c] / D.centres[r].hand}
            color={(_t, r, c) => heat(grid[r][c] / D.centres[r].hand, selC >= 0 && c !== selC)}
            onCell={(_r, c) => pickDay(c)}
            tip={(r, c) => {
              const v = grid[r][c]
              const cap = D.centres[r].hand
              const t = v / cap
              return (
                <>
                  <span className="h">
                    {NAME[r]} · {shortDate(DAY[c].d)}
                  </span>
                  <TipKV
                    rows={[
                      ['kullanılan', v > 0 ? n0(Math.round(v)) + ' desi' : 'işlem yok'],
                      ['günlük kota', n0(cap) + ' desi'],
                      [
                        'doluluk',
                        <span className={t > OVER_AT ? 'c-bad' : t >= WARN_AT ? 'c-warn' : 'c-blue'}>
                          {pct01(t)}
                        </span>,
                      ],
                    ]}
                  />
                </>
              )
            }}
          />
          <Legend
            items={[
              [`rgba(${RGB.blue},.85)`, `${pct01(WARN_AT, 0)} altı`],
              [`rgba(${RGB.warn},.9)`, `${pct01(WARN_AT, 0)} – %100`],
              [overFill(1), '%100 üstü (ihlal)'],
              [emptyFill(1), 'işlem yok'],
            ]}
          />
          <p className="note" style={{ marginTop: 9 }}>
            {mode === 'defter' ? (
              <>
                <b>Hakem defteri.</b> Bir merkezde yalnız orada <b>yüklenen ya da indirilen</b> desi
                elleçlenir; aktarmadan geçip araçta kalan yük sayılmaz. Bu defterde {n0(ND)} günün
                tamamında {hand.over === 0 ? 'hiçbir merkez-gün' : n0(hand.over) + ' merkez-gün'}{' '}
                kotayı {hand.over === 0 ? 'aşmıyor' : 'aşıyor'}, tepe doluluk{' '}
                {hand.peak ? pct01(hand.peak.t) : '—'}. Elleçleme bizim için darboğaz değil;
                darboğaz tır kotası.
              </>
            ) : (
              <>
                <b>Üst sınır.</b> Her bacağın <b>tüm desisi</b> hem çıkış hem varış merkezine
                yazılır; zincirde aktarmadan geçen yük iki kez sayıldığı için {n0(hand.over)}{' '}
                merkez-gün kotanın üstünde görünür. Bu kötümser sınırdır — hakemin saydığı defter
                için soldaki kipe geç.
              </>
            )}
          </p>
        </Card>

        {/* ── tır ziyaret ısı haritası ───────────────────────── */}
        <Card
          title="Tır ziyaret kotası"
          sub={`${n0(tir.visits)} ziyaret · ${n0(tir.full)} hücre tam kotada`}
        >
          <Matrix
            rows={D.centres.map((c) => `${c.n} · ${c.tir}`)}
            cols={cols}
            cell={CELL}
            rowW={ROWW}
            value={(r, c) => (D.centres[r].tir ? D.tirgrid[r][c] / D.centres[r].tir : 0)}
            color={(_t, r, c) => {
              const q = D.centres[r].tir
              const v = D.tirgrid[r][c]
              const faded = selC >= 0 && c !== selC
              /* Kotası sıfır olan merkezde tek bir ziyaret bile ihlaldir. */
              if (q === 0) return v > 0 ? overFill(dim(faded)) : emptyFill(dim(faded))
              return heat(v / q, faded)
            }}
            onCell={(_r, c) => pickDay(c)}
            tip={(r, c) => {
              const q = D.centres[r].tir
              const v = D.tirgrid[r][c]
              return (
                <>
                  <span className="h">
                    {NAME[r]} · {shortDate(DAY[c].d)}
                  </span>
                  <TipKV
                    rows={[
                      ['ziyaret', n0(v)],
                      ['günlük kota', q === 0 ? 'yok — tır giremez' : n0(q)],
                      [
                        'doluluk',
                        q === 0 ? (
                          <span className={v > 0 ? 'c-bad' : 'c-dim'}>{v > 0 ? 'ihlal' : '—'}</span>
                        ) : (
                          <span className={v > q ? 'c-bad' : v === q ? 'c-warn' : 'c-blue'}>
                            {pct01(v / q)}
                          </span>
                        ),
                      ],
                      ['bunun kiralığı', n0(Math.min(rentVisit[r], v))],
                    ]}
                  />
                </>
              )
            }}
          />
          <Legend
            items={[
              [`rgba(${RGB.blue},.85)`, 'kota içinde'],
              [`rgba(${RGB.warn},.9)`, 'kota tam dolu'],
              [overFill(1), 'kota aşımı'],
              [emptyFill(1), 'ziyaret yok'],
            ]}
          />
          <div style={{ marginTop: 9 }}>
            <p className="note" style={{ marginBottom: 7 }}>
              Satır etiketindeki sayı o merkezin günlük kotasıdır. Kotası <b>sıfır</b> olan{' '}
              {n0(tir.zero.length)} merkeze plan boyunca tek bir tır sokulmadı — bu satırlar
              tamamen boş:
            </p>
            <div className="chips">
              {tir.zero.map((i) => (
                <span className="chip" key={i}>
                  {NAME[i]} · 0
                </span>
              ))}
            </div>
            <p className="note" style={{ marginTop: 8 }}>
              * {ddmm(DAY[ND - 1].d)} ufuk sonrası gün: {ddmm(DAY[D.daily.length - 1].d)}{' '}
              gecesi kalkan zorunlu kiralık tırlar gece yarısından sonra vardığı için varış
              ziyaretleri ertesi güne yazılır.
            </p>
          </div>
        </Card>
      </div>

      <div className="g2 in in-4">
        {/* ── en çok zorlanan merkez-günler ──────────────────── */}
        <Card
          title="En çok zorlanan 10 merkez-gün"
          sub={mode === 'defter' ? 'hakem defteri' : 'üst sınır kipi'}
        >
          <table className="t">
            <thead>
              <tr>
                <th>Merkez</th>
                <th>Gün</th>
                <th className="n">Kullanılan</th>
                <th className="n">Kota</th>
                <th className="n">Doluluk</th>
                <th style={{ width: 96 }} />
              </tr>
            </thead>
            <tbody>
              {hand.top.map((s) => (
                <tr
                  key={s.r + '-' + s.c}
                  className={'click' + (selC === s.c ? ' sel' : '')}
                  onClick={() => pickDay(s.c)}
                >
                  <td>{NAME[s.r]}</td>
                  <td className="mono c-dim">{shortDate(DAY[s.c].d)}</td>
                  <td className="n">{n0(Math.round(s.v))}</td>
                  <td className="n c-dim">{n0(s.cap)}</td>
                  <td className={'n ' + (s.t > OVER_AT ? 'c-bad' : s.t >= WARN_AT ? 'c-warn' : 'c-blue')}>
                    {pct01(s.t)}
                  </td>
                  <td>
                    <Meter v={s.v} max={s.cap} color={C.blue} h={6} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* ── SLA ────────────────────────────────────────────── */}
        <Card title="SLA" sub="bilinçli satın alınan gecikme">
          <div className="rowf" style={{ gap: 26, marginBottom: 12, flexWrap: 'wrap' }}>
            <div>
              <div className="num c-warn" style={{ font: '700 21px/1 var(--mono)' }}>
                {n0(late.length)}
                <span className="c-dim" style={{ fontSize: 14 }}> / {n0(D.legs.length)}</span>
              </div>
              <div className="c-dim" style={{ font: '500 11px/1.3 var(--sans)', marginTop: 6 }}>
                gecikmeli bacak · {pct01(late.length / D.legs.length)}
              </div>
            </div>
            <div>
              <div className="num c-warn" style={{ font: '700 21px/1 var(--mono)' }}>
                {M(D.meta.sla_cost)}
              </div>
              <div className="c-dim" style={{ font: '500 11px/1.3 var(--sans)', marginTop: 6 }}>
                toplam SLA cezası · toplam maliyetin{' '}
                {pct01(D.meta.sla_cost / D.meta.total_cost)}'i
              </div>
            </div>
          </div>
          <p className="note hl" style={{ marginBottom: 11 }}>
            Gecikme cezası bir kaza değil, bir <b>karar</b>: küçük artık yükler için adanmış araç
            açmanın maliyeti, cezayı satın almaktan pahalıya geliyorsa ceza tercih ediliyor. Kural
            motoru cezayı hakemle birebir aynı formülle sayıyor.
          </p>
          <table className="t">
            <thead>
              <tr>
                <th>Araç</th>
                <th>Hat</th>
                <th className="n">Desi</th>
                <th className="n">Ceza</th>
              </tr>
            </thead>
            <tbody>
              {late.slice(0, 8).map((l, i) => (
                <tr
                  key={l.v + '-' + i}
                  className="click"
                  onClick={() => {
                    setFilter((p) => ({ ...p, date: l.dd }))
                    go('filo')
                  }}
                >
                  <td className="mono">{l.v}</td>
                  <td>
                    {NAME[l.a]} <span className="c-dim">→</span> {NAME[l.b]}
                  </td>
                  <td className="n">{n0(l.desi)}</td>
                  <td className="n c-warn">{TL(l.sla, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {/* ── kiralık filo ─────────────────────────────────────── */}
      <Card
        className="in in-5"
        title="Kiralık filo — kotayı peşinen yiyen taban"
        sub={`${n0(D.rented.length)} zorunlu rota · ${n0(rentAll)} araç/gün`}
      >
        <p className="note" style={{ marginBottom: 11 }}>
          Bu {n0(D.rented.length)} rota her gün aynı saatte kalkmak zorunda; planın optimize
          edebildiği kısım bunların üstünde başlıyor. {n0(rentTir)} tanesi tır olduğu için günde{' '}
          {n0(rentTir * 2)} tır ziyareti (çıkış + varış) kotadan peşinen düşüyor. Stratejimiz önce
          bu araçları doldurmak: batık maliyet zaten ödeniyor.
        </p>
        <div className="g2">
          <table className="t">
            <thead>
              <tr>
                <th>Çıkış</th>
                <th>Varış</th>
                <th>Tür</th>
                <th className="n">Araç/gün</th>
                <th className="n">km</th>
                <th className="n">Tır ziy./gün</th>
              </tr>
            </thead>
            <tbody>
              {D.rented.map((r, i) => {
                const ln = laneOf(r.a, r.b)
                return (
                  <tr key={i}>
                    <td>{NAME[r.a]}</td>
                    <td>{NAME[r.b]}</td>
                    <td className={r.t === 'Tır' ? 'c-muted' : 'c-blue'}>{r.t}</td>
                    <td className="n">{n0(r.n)}</td>
                    <td className="n c-dim">{ln ? n0(ln.km) : '—'}</td>
                    <td className="n">
                      {r.t === 'Tır' ? (
                        <span className="c-warn">{n0(r.n * 2)}</span>
                      ) : (
                        <span className="c-dim">0</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <div>
            <p className="kicker" style={{ marginBottom: 10 }}>
              Kiralığın yediği tır kotası
            </p>
            <table className="t">
              <thead>
                <tr>
                  <th>Merkez</th>
                  <th className="n">Kiralık</th>
                  <th className="n">Kota</th>
                  <th style={{ width: 110 }} />
                  <th className="n">Kalan</th>
                </tr>
              </thead>
              <tbody>
                {D.centres
                  .map((c, i) => ({ i, n: c.n, q: c.tir, u: rentVisit[i] }))
                  .filter((x) => x.u > 0 && x.q > 0)
                  .sort((a, b) => b.u / b.q - a.u / a.q)
                  .map((x) => (
                    <tr key={x.i}>
                      <td>{x.n}</td>
                      <td className="n c-warn">{n0(x.u)}</td>
                      <td className="n c-dim">{n0(x.q)}</td>
                      <td>
                        <Meter v={x.u} max={x.q} color={C.warn} h={6} />
                      </td>
                      <td className={'n ' + (x.u >= x.q ? 'c-bad' : 'c-ok')}>{n0(x.q - x.u)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
            <p className="note" style={{ marginTop: 10 }}>
              Kalan sütunu sıfır olan merkezlerde kotanın <b>tamamını</b> zorunlu kiralıklar
              tüketiyor: oralara plan boyunca ek bir tır sokulamaz, gelen yük ancak araç
              merdiveniyle ya da aktarmayla taşınabilir. Kotası zaten sıfır olan{' '}
              {n0(tir.zero.length)} merkez ise zincirlerin en sık uğradığı ara duraklar —{' '}
              {midZero.top.join(', ')} başta olmak üzere {n0(midZero.stops)} ara durağın tamamına
              tır yerine kamyon/kamyonet ile giriliyor.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
