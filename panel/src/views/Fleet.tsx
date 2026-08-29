import { Fragment, useEffect, useMemo, useState } from 'react'
import {
  D,
  NAME,
  XY,
  BOX,
  RENTED_KEYS,
  laneOf,
  VT_ORDER,
  useSlice,
  vehicleLegs,
} from '../store'
import type { ViewProps } from '../App'
import type { Leg, Vehicle } from '../types.ext'
import { Card, Kpi, Seg, Switch, Icon, C, VT_COLOR, KIND_COLOR, useTip, TipKV } from '../lib/ui'
import { Chart, Meter } from '../lib/charts'
import { n0, M, TL, pct, dur, clock, shortDate, compact } from '../lib/fmt'
import { LAND, chainPath } from '../lib/geo'

/** Tabloda en fazla bu kadar satır çizilir — kalanı gizlenmez, sayısı yazılır. */
const CAP = 400

/** Yüzde ölçeğinin tepesi. */
const FULL = 100
/** Meter tam 100'de "aşım" sayıp kırmızıya döner; doluluk içinse 100 iyi bir değerdir. */
const FILL_CLAMP = 99.9
/** Erişilemez uyarı eşiği: doluluk ölçerinde sarı uyarı hiç tetiklenmesin. */
const FILL_NO_WARN = 2

const COLS = [
  { k: 'id', l: 'Araç', w: 66, n: false },
  { k: 'kind', l: 'Tip', w: 62, n: false },
  { k: 'vt', l: 'Tür', w: 88, n: false },
  { k: 'dd', l: 'Çıkış', w: 84, n: false },
  { k: 'stops', l: 'Bacak', w: 46, n: true },
  { k: 'desi', l: 'Desi', w: 62, n: true },
  { k: 'fill', l: 'Doluluk', w: 96, n: true },
  { k: 'use', l: 'Kullanım', w: 78, n: true },
  { k: 'km', l: 'Km', w: 54, n: true },
  { k: 'sla', l: 'SLA cezası', w: 84, n: true },
  { k: 'cost', l: 'Maliyet', w: 88, n: true },
] as const

type SortKey = (typeof COLS)[number]['k']

/** Sıralama anahtarı -> karşılaştırılabilir değer. Tarih için ufuk dakikası kullanılır. */
const sval = (v: Vehicle, k: SortKey): number | string => (k === 'dd' ? v.t0 : v[k])

/** Doluluk yüzdesine göre renk — yüksek doluluk iyidir. */
const fillCol = (f: number) => (f >= 80 ? C.ok : f >= 50 ? C.blue : f >= 25 ? C.warn : C.bad)

/** Doluluk ölçeri — tabloda ve bacak listesinde aynı kırpma/eşik kuralıyla çizilir. */
const FillMeter = ({ fill }: { fill: number }) => (
  <Meter v={Math.min(fill, FILL_CLAMP)} max={FULL} warnAt={FILL_NO_WARN} color={fillCol(fill)} h={6} />
)

const lc = (s: string) => s.toLocaleLowerCase('tr')

export default function Fleet({ st, set, filter, setFilter, go }: ViewProps) {
  const slice = useSlice(filter)
  const tip = useTip()

  /* Tek süzgeç sistemi. Eskiden Fleet'in kendi kind/vt/onlyChains/onlyPickup
     state'i vardı ve global süzgecin ÜSTÜNE biniyordu: ÖZET donut'undan gelen
     tür süzgeci listeyi daraltıyor ama buradaki çipler "tümü" görünüyordu.
     Artık ikisi aynı durumu okuyup yazıyor; süzme işini useSlice yapıyor. */
  const q = st.q
  const setQ = (v: string) => set({ q: v })
  const kind = filter.kind
  const setKind = (v: 'all' | 'Kiralık' | 'Spot') => setFilter((f) => ({ ...f, kind: v }))
  const vt = filter.vt
  const setVt = (v: string) => setFilter((f) => ({ ...f, vt: v }))
  const onlyChains = filter.chainsOnly
  const setOnlyChains = (v: boolean) => setFilter((f) => ({ ...f, chainsOnly: v }))
  const onlyPickup = filter.pickupOnly
  const setOnlyPickup = (v: boolean) => setFilter((f) => ({ ...f, pickupOnly: v }))
  const [sort, setSort] = useState<SortKey>('cost')
  const [asc, setAsc] = useState(false)
  const selId = st.sel
  const setSelId = (v: string) => set({ sel: v })

  const globalOn =
    !!filter.date || filter.kind !== 'all' || filter.vt !== 'all' || filter.chainsOnly || filter.pickupOnly

  /* ── süzülen küme + toplamları ─────────────────────────────── */
  const { base, tot } = useMemo(() => {
    const needle = lc(q.trim())
    // kind/vt/zincir/yük-alma süzgeçlerini useSlice zaten uyguladı; burada
    // yalnız serbest metin araması kalır.
    const arr = slice.vehicles.filter((v) => {
      if (needle) {
        const hit = lc(v.id).includes(needle) || v.path.some((i) => lc(NAME[i]).includes(needle))
        if (!hit) return false
      }
      return true
    })
    let legs = 0
    let desi = 0
    let km = 0
    let cost = 0
    let sla = 0
    let chains = 0
    let picks = 0
    for (const v of arr) {
      legs += v.stops
      km += v.km
      cost += v.cost
      sla += v.sla
      if (v.stops > 1) chains++
      if (v.pickup) picks++
      for (const l of vehicleLegs(v)) desi += l.desi
    }
    return { base: arr, tot: { legs, desi, km, cost, sla, chains, picks } }
  }, [slice.vehicles, q])

  /* ── sıralama ──────────────────────────────────────────────── */
  const rows = useMemo(() => {
    const dir = asc ? 1 : -1
    return base.slice().sort((a, b) => {
      const x = sval(a, sort)
      const y = sval(b, sort)
      if (typeof x === 'string' || typeof y === 'string')
        return dir * String(x).localeCompare(String(y), 'tr')
      return dir * (x - y)
    })
  }, [base, sort, asc])

  const shown = rows.slice(0, CAP)

  /* Harita ya da Kısıt görünümünden bir araçla gelindiğinde tabloda ona
     kaydır — eskiden seçim taşınmadığı için kullanıcı aracı elle arıyordu. */
  useEffect(() => {
    if (!selId) return
    document.getElementById('arac-' + selId)?.scrollIntoView({ block: 'center' })
  }, [selId])

  // Süzgeç seçili aracı dışarıda bırakırsa detay paneli de kapanır.
  const sel = useMemo(() => base.find((v) => v.id === selId) ?? null, [base, selId])
  const selLegs = useMemo(() => (sel ? vehicleLegs(sel) : []), [sel])

  /* ── seçim yokken: öne çıkan üç araç ───────────────────────── */
  const highlights = useMemo(() => {
    if (!base.length) return []
    const best = (f: (v: Vehicle) => number) => base.reduce((a, v) => (f(v) > f(a) ? v : a), base[0])
    const priciest = best((v) => v.cost)
    const fullest = best((v) => v.fill)
    const longest = best((v) => v.stops * 1e6 + v.cost)
    const out: { v: Vehicle; t: string; q: string; c: string }[] = [
      { v: priciest, t: 'En pahalı araç', q: TL(priciest.cost, 0), c: C.brand },
      { v: fullest, t: 'En dolu araç', q: pct(fullest.fill), c: C.ok },
      { v: longest, t: 'En uzun zincir', q: n0(longest.stops) + ' bacak', c: C.blue },
    ]
    return out
  }, [base])

  const head = (c: (typeof COLS)[number]) => (
    <th
      key={c.k}
      className={'s' + (sort === c.k ? ' on' : '') + (c.n ? ' n' : '')}
      style={{ width: c.w }}
      onClick={() => {
        if (sort === c.k) setAsc((p) => !p)
        else {
          setSort(c.k)
          setAsc(!c.n)
        }
      }}
      title="Sırala"
    >
      {c.l}
      {sort === c.k && <span style={{ marginLeft: 4 }}>{asc ? '▲' : '▼'}</span>}
    </th>
  )

  return (
    <div className="stack">
      <p className="lead in in-1">
        Burada <b>tek tek araçlara</b> bakıyoruz: planın ürettiği {n0(D.meta.vehicles)} fiziksel aracın
        her biri aranabilir, sıralanabilir ve rotası bacak bacak açılabilir. Soldaki tabloda bir satıra
        tıklayın — sağda o aracın haritadaki yolu ve zaman çizelgesi belirir.
      </p>

      {/* ── (d) süzülen kümenin toplamları ─────────────────────── */}
      <div className="g6 in in-1">
        <Kpi sm v={n0(base.length)} l="araç" tone="brand" d={`${n0(tot.chains)} zincir · ${n0(tot.picks)} yük alma`} />
        <Kpi sm v={n0(tot.legs)} l="bacak" />
        <Kpi sm v={compact(tot.desi)} l="taşınan desi (bacak toplamı)" />
        <Kpi sm v={n0(tot.km)} l="km" />
        <Kpi sm v={M(tot.sla)} l="SLA cezası" tone={tot.sla > 0 ? 'warn' : 'ok'} />
        <Kpi sm v={M(tot.cost)} l="maliyet" tone="brand" />
      </div>

      {/* ── (a) arama çubuğu ───────────────────────────────────── */}
      <Card className="tight in in-2">
        <div className="rowf" style={{ flexWrap: 'wrap', alignItems: 'center', gap: 14 }}>
          <input
            className="inp"
            style={{ flex: '0 0 232px' }}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="araç kodu ya da merkez ara…"
            aria-label="Araç kodu ya da merkez adı ara"
          />
          <Seg
            value={kind}
            onChange={setKind}
            options={[
              { v: 'all', l: 'tümü' },
              { v: 'Kiralık', l: 'Kiralık' },
              { v: 'Spot', l: 'Spot' },
            ]}
          />
          <Seg
            value={vt}
            onChange={setVt}
            options={[{ v: 'all', l: 'tür' }, ...VT_ORDER.map((t) => ({ v: t as string, l: t }))]}
          />
          <Switch
            on={onlyChains}
            onChange={setOnlyChains}
            label="yalnızca zincirler"
            count={n0(tot.chains)}
          />
          <Switch
            on={onlyPickup}
            onChange={setOnlyPickup}
            label="yalnızca yol üstü yük alanlar"
            count={n0(tot.picks)}
          />
          <div className="grow" />
          {globalOn && (
            <button
              type="button"
              className="btn on"
              onClick={() =>
                setFilter((f) => ({ ...f, date: '', kind: 'all', vt: 'all', chainsOnly: false, pickupOnly: false }))
              }
              title="Haritadan gelen genel süzgeci kaldır"
            >
              genel süzgeç etkin ✕
            </button>
          )}
        </div>
      </Card>

      {/* ── (b) tablo + (c) detay ──────────────────────────────── */}
      <div className="rowf in in-3">
        <Card
          className="grow"
          title="Araç listesi"
          sub={
            rows.length > CAP
              ? `${n0(rows.length)} araçtan ilk ${n0(CAP)}'ü`
              : `${n0(rows.length)} araç · başlığa tıklayıp sıralayın`
          }
        >
          <div
            style={{
              overflow: 'auto',
              flex: 1,
              minHeight: 380,
              maxHeight: 'calc(100vh - 402px)',
              margin: '0 -6px',
              padding: '0 6px',
            }}
          >
            <table className="t">
              <thead>
                <tr>{COLS.map(head)}</tr>
              </thead>
              <tbody>
                {shown.map((v) => (
                  <tr
                    key={v.id}
                    id={'arac-' + v.id}
                    className={'click' + (v.id === selId ? ' sel' : '')}
                    onClick={() => setSelId(v.id === selId ? '' : v.id)}
                  >
                    <td className="mono" style={{ color: C.ink }}>
                      {v.id}
                    </td>
                    <td style={{ color: KIND_COLOR[v.kind] }}>{v.kind}</td>
                    <td>
                      <span
                        style={{
                          display: 'inline-block',
                          width: 7,
                          height: 7,
                          borderRadius: 2,
                          background: VT_COLOR[v.vt],
                          marginRight: 7,
                        }}
                      />
                      {v.vt}
                    </td>
                    <td className="mono" style={{ color: C.muted, fontSize: 11.5 }}>
                      {shortDate(v.dd)}
                    </td>
                    <td className="n">
                      {v.stops > 1 ? <b className="c-brand">{v.stops}</b> : v.stops}
                      {v.pickup ? <span className="c-ok"> ↑</span> : ''}
                    </td>
                    <td className="n">{n0(v.desi)}</td>
                    <td className="n">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                        <div style={{ width: 34 }}>
                          <FillMeter fill={v.fill} />
                        </div>
                        <span style={{ color: fillCol(v.fill) }}>{pct(v.fill, 0)}</span>
                      </div>
                    </td>
                    <td className="n" style={{ color: C.muted }}>
                      {dur(v.use)}
                    </td>
                    <td className="n">{n0(v.km)}</td>
                    <td className={'n' + (v.sla > 0 ? ' c-warn' : ' c-dim')}>
                      {v.sla > 0 ? TL(v.sla, 0) : '—'}
                    </td>
                    <td className="n" style={{ color: C.ink, fontWeight: 600 }}>
                      {TL(v.cost, 0)}
                    </td>
                  </tr>
                ))}
                {!shown.length && (
                  <tr>
                    <td colSpan={COLS.length} style={{ padding: '28px 0', textAlign: 'center' }}>
                      <span className="c-dim">Bu süzgeçle eşleşen araç yok.</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <div style={{ flex: '0 0 430px', minWidth: 0 }}>
          {sel ? (
            <Detail
              v={sel}
              legs={selLegs}
              onClose={() => setSelId('')}
              onMap={() => {
                setFilter((f) => ({ ...f, date: sel.dd }))
                go('harita')
              }}
              tip={tip}
            />
          ) : (
            <Card title="Öne çıkan araçlar" sub="tablodan bir satır seçin">
              <p className="note" style={{ marginBottom: 12 }}>
                Süzülen {n0(base.length)} araç içinde uç örnekler. Birine tıklayın; rotası ve bacak bacak
                zaman çizelgesi burada açılır.
              </p>
              <div className="stack">
                {highlights.map((p) => (
                  <button
                    key={p.t}
                    type="button"
                    className="card tight click"
                    style={{ textAlign: 'left', cursor: 'pointer' }}
                    onClick={() => setSelId(p.v.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 9 }}>
                      <span className="mono" style={{ color: p.c, fontWeight: 700, fontSize: 15 }}>
                        {p.q}
                      </span>
                      <span className="c-muted" style={{ fontSize: 12 }}>
                        {p.t}
                      </span>
                    </div>
                    <div className="mono c-dim" style={{ fontSize: 11, marginTop: 6 }}>
                      {p.v.id} · {p.v.kind} {p.v.vt} · {shortDate(p.v.dd)} ·{' '}
                      {p.v.path.map((i) => NAME[i]).join(' → ')}
                    </div>
                  </button>
                ))}
                {!highlights.length && <p className="note c-dim">Süzgeçle eşleşen araç yok.</p>}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

/* ══════════════ seçili aracın detayı ══════════════ */
function Detail({
  v,
  legs,
  onClose,
  onMap,
  tip,
}: {
  v: Vehicle
  legs: Leg[]
  onClose: () => void
  onMap: () => void
  tip: ReturnType<typeof useTip>
}) {
  const pts = v.path.map((i) => XY[i])
  return (
    <Card
      title={<span className="mono">{v.id}</span>}
      sub={`${v.kind} · ${v.vt} · ${n0(v.cap)} desi kapasite`}
      style={{ maxHeight: 'calc(100vh - 402px)', minHeight: 380, overflow: 'auto' }}
    >
      {/* rozetler */}
      <div className="chips" style={{ marginBottom: 11 }}>
        <span className="chip" style={{ color: KIND_COLOR[v.kind] }}>
          {v.kind}
        </span>
        <span className="chip" style={{ color: VT_COLOR[v.vt] }}>
          {v.vt}
        </span>
        <span className="chip">{shortDate(v.dd)}</span>
        <span className="chip">{dur(v.use)} kullanım</span>
        {v.stops > 1 && <span className="chip on">{v.stops} bacaklı zincir</span>}
        {v.pickup === 1 && <span className="chip ok">yol üstünde yük aldı · {n0(v.picked)} parça</span>}
      </div>

      {v.stops > 1 && (
        <p className="note hl" style={{ marginBottom: 11 }}>
          <b>{n0(v.stops)} ayrı aracın işi tek araca bindirildi.</b> Zincir {v.path.map((i) => NAME[i]).join(' → ')}{' '}
          sırasıyla koşuyor; tek bir kiralama/spot ücreti ödeniyor.
        </p>
      )}

      {/* mini harita */}
      <div style={{ display: 'flex', height: 176, margin: '0 -4px 4px' }}>
        <Chart vw={BOX.w} vh={BOX.h}>
          {LAND.map((d, i) => (
            <path key={i} className="land" d={d} />
          ))}
          {XY.map((p, i) =>
            v.path.includes(i) ? null : <circle key={i} cx={p.x} cy={p.y} r={4} fill={C.faint} opacity={0.55} />,
          )}
          <path
            className="arc draw"
            d={chainPath(pts)}
            pathLength={1}
            stroke={C.brand}
            strokeWidth={3.6}
            opacity={0.92}
          />
          {v.path.map((ci, i) => (
            <Fragment key={i}>
              <circle
                cx={XY[ci].x}
                cy={XY[ci].y}
                r={13}
                fill="#070a0f"
                stroke={i === 0 ? C.brand2 : C.brand}
                strokeWidth={2.6}
                onMouseMove={(e) =>
                  tip.show(
                    e,
                    <>
                      <span className="h">{i === 0 ? 'çıkış' : i === v.path.length - 1 ? 'son varış' : 'ara durak'}</span>
                      <b>{NAME[ci]}</b>
                      <TipKV
                        rows={[
                          ['durak', `${i + 1} / ${v.path.length}`],
                          ['saat', clock(i === 0 ? legs[0].t0 : legs[i - 1].t1)],
                        ]}
                      />
                    </>,
                  )
                }
                onMouseLeave={tip.hide}
                style={{ cursor: 'default' }}
              />
              <text
                x={XY[ci].x}
                y={XY[ci].y + 5}
                textAnchor="middle"
                fontSize={14}
                fontWeight={700}
                fill={C.brand2}
                fontFamily='"Cascadia Mono",Consolas,monospace'
                style={{ pointerEvents: 'none' }}
              >
                {i + 1}
              </text>
              <text
                x={XY[ci].x}
                y={XY[ci].y - 21}
                textAnchor="middle"
                fontSize={17}
                fontWeight={600}
                fill={C.ink2}
                fontFamily='"Cascadia Mono",Consolas,monospace'
                stroke="#070a0f"
                strokeWidth={4}
                style={{ paintOrder: 'stroke', pointerEvents: 'none' }}
              >
                {NAME[ci]}
              </text>
            </Fragment>
          ))}
        </Chart>
      </div>

      {/* bacak bacak zaman çizelgesi */}
      <h3 className="ch3" style={{ marginTop: 6 }}>
        Zaman çizelgesi
        <span className="sub">{n0(legs.length)} bacak · toplam {dur(v.use)}</span>
      </h3>

      <div className="stack" style={{ gap: 9 }}>
        {legs.map((l, i) => {
          const lane = laneOf(l.a, l.b)
          const rented = RENTED_KEYS.has(l.a * 100 + l.b)
          const carried = i > 0 && legs[i - 1].ids.some((x) => l.ids.includes(x))
          return (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '20px 1fr', gap: 10 }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span
                  className="mono"
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: 6,
                    display: 'grid',
                    placeItems: 'center',
                    fontSize: 10.5,
                    fontWeight: 700,
                    color: C.brand2,
                    background: 'rgba(255,96,0,.12)',
                    border: '1px solid rgba(255,96,0,.34)',
                  }}
                >
                  {i + 1}
                </span>
                {i < legs.length - 1 && (
                  <span style={{ flex: 1, width: 1, background: C.line, marginTop: 3 }} />
                )}
              </div>

              <div style={{ paddingBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span style={{ color: C.ink, fontWeight: 600, fontSize: 12.5 }}>
                    {NAME[l.a]} <span className="c-dim">→</span> {NAME[l.b]}
                  </span>
                  <span className="grow" />
                  <span className="mono" style={{ color: C.muted, fontSize: 11.5 }}>
                    {clock(l.t0)}–{clock(l.t1)}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '6px 0 5px' }}>
                  <div style={{ flex: 1 }}>
                    <FillMeter fill={l.fill} />
                  </div>
                  <span className="mono" style={{ fontSize: 11, color: fillCol(l.fill), width: 46, textAlign: 'right' }}>
                    {pct(l.fill, 0)}
                  </span>
                  <span className="mono c-dim" style={{ fontSize: 11, width: 78, textAlign: 'right' }}>
                    {n0(l.desi)} desi
                  </span>
                </div>

                <div className="mono c-dim" style={{ fontSize: 10.5, display: 'flex', flexWrap: 'wrap', gap: '2px 12px' }}>
                  <span>{n0(l.km)} km</span>
                  <span>yol {dur(l.trav)}</span>
                  <span>elleçleme {dur(l.hun + l.hld)}</span>
                  <span>{n0(l.parts)} parça</span>
                  <span style={{ color: C.ink2 }}>{TL(l.cost, 0)}</span>
                  {l.sla > 0 && <span className="c-warn">SLA {TL(l.sla, 0)}</span>}
                </div>

                <div className="chips" style={{ marginTop: 6, gap: 5 }}>
                  {carried && <span className="chip blue">önceki bacaktan devreden yük</span>}
                  {rented && <span className="chip">zorunlu kiralık hat</span>}
                  {lane && <span className="chip">hat SLA hedefi {n0(lane.sla)} gün</span>}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="rowf" style={{ gap: 8, marginTop: 12 }}>
        <button type="button" className="btn" onClick={onMap} title="Bu aracın gününü haritada aç">
          {Icon.map}
          haritada aç
        </button>
        <button type="button" className="btn" onClick={onClose}>
          seçimi bırak
        </button>
      </div>
    </Card>
  )
}
