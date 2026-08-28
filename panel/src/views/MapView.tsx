import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ViewProps } from '../App'
import {
  BOX,
  D,
  DATES,
  NAME,
  RENTED_KEYS,
  VT_ORDER,
  XY,
  laneOf,
  useSlice,
  vehicleLegs,
} from '../store'
import type { Leg, Vehicle } from '../types.ext'
import { LABEL, LAND, arc, arcAt, chainPath } from '../lib/geo'
import { C, Icon, KIND_COLOR, Legend, Seg, Switch, TipKV, VT_COLOR, useTip } from '../lib/ui'
import { M, TL, clock, compact, dur, n0, pct, shortDate, stamp } from '../lib/fmt'
import { Meter } from '../lib/charts'

/* ══════════════════════════════════════════════════════════════════════
   Sevkiyat haritası — panonun kalbi.
   Üç karar türü aynı coğrafya üzerinde üst üste görünür:
     · zorunlu kiralık rotalar (değiştiremediğimiz taban)
     · spot atamalar (tek bacaklı, serbestçe kurduğumuz seferler)
     · konsolidasyon zincirleri (milk-run + yol üstü yük alma)
   "Zaman" kipinde plan dakika dakika oynatılır; hareket eden her jeton
   o anda gerçekten yolda olan bir araçtır.
   ══════════════════════════════════════════════════════════════════════ */

type LayerKey = 'kiralik' | 'spot' | 'zincir' | 'pickup'

/* Katman ipuçlarındaki sayılar veriden türetilir — eskiden elle yazılıydı ve
   veri değişince sessizce yanlışa dönerdi. */
const RENT_ROUTES = D.rented.length
const RENT_PER_DAY = D.rented.reduce((a, r) => a + r.n, 0)
const MAX_STOPS = D.stages.meta.max_chain_stops

const LAYERS: { k: LayerKey; label: string; color: string; hint: string }[] = [
  {
    k: 'kiralik',
    label: 'Kiralık rotalar',
    color: C.warn,
    hint: `zorunlu ${RENT_ROUTES} rota · ${RENT_PER_DAY} araç/gün`,
  },
  { k: 'spot', label: 'Spot atamalar', color: C.blue, hint: 'tek bacaklı spot seferler' },
  {
    k: 'zincir',
    label: 'Konsolidasyon zincirleri',
    color: C.brand,
    hint: `milk-run · 2–${MAX_STOPS} durak`,
  },
  { k: 'pickup', label: 'Yol üstü yük alma', color: C.pink, hint: 'ara durakta yük alan zincirler' },
]

/** Bir bacağın hangi karar katmanına ait olduğu. */
function layerOf(l: Leg, v: Vehicle): LayerKey {
  if (l.kind === 'Kiralık') return 'kiralik'
  if (v.pickup) return 'pickup'
  if (v.stops > 1) return 'zincir'
  return 'spot'
}

const VIEW0 = { x: 0, y: 0, w: BOX.w, h: BOX.h }
const CAP_MAX = 22400

export default function MapView({ filter, setFilter, go }: ViewProps) {
  const tip = useTip()
  const slice = useSlice(filter)

  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    kiralik: true,
    spot: true,
    zincir: true,
    pickup: true,
  })
  const [mode, setMode] = useState<'akis' | 'zaman'>('akis')
  const [focus, setFocus] = useState<number | null>(null)
  const [pick, setPick] = useState<Vehicle | null>(null)

  /* ── zaman kipi ────────────────────────────────────────────── */
  const span = useMemo(() => D.legs.reduce((a, l) => Math.max(a, l.t1), 0), [])
  const [t, setT] = useState(0)
  const [play, setPlay] = useState(false)
  const [speed, setSpeed] = useState(6)

  useEffect(() => {
    if (!play || mode !== 'zaman') return
    let raf = 0
    let last = performance.now()
    const step = (now: number) => {
      const dt = now - last
      last = now
      setT((p) => {
        const n = p + (dt / 1000) * speed * 60
        return n >= span ? 0 : n
      })
      raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [play, speed, span, mode])

  useEffect(() => {
    if (mode === 'akis') setPlay(false)
  }, [mode])

  /* ── görünür bacaklar ──────────────────────────────────────── */
  const vis = useMemo(() => {
    const byId = new Map(slice.vehicles.map((v) => [v.id, v]))
    const out: { l: Leg; v: Vehicle; k: LayerKey }[] = []
    for (const l of slice.legs) {
      const v = byId.get(l.v)
      if (!v) continue
      const k = layerOf(l, v)
      if (!layers[k]) continue
      if (focus !== null && l.a !== focus && l.b !== focus) continue
      out.push({ l, v, k })
    }
    return out
  }, [slice, layers, focus])

  /** Katman sayaçları — süzgeç içinde, katman anahtarından bağımsız. */
  const counts = useMemo(() => {
    const byId = new Map(D.vehicles.map((v) => [v.id, v]))
    const c: Record<LayerKey, number> = { kiralik: 0, spot: 0, zincir: 0, pickup: 0 }
    for (const l of slice.legs) {
      const v = byId.get(l.v)
      if (v) c[layerOf(l, v)]++
    }
    return c
  }, [slice])

  const flying = useMemo(() => {
    if (mode !== 'zaman') return []
    const out: { l: Leg; k: LayerKey; x: number; y: number }[] = []
    for (const { l, k } of vis) {
      if (t < l.t0 || t > l.t1) continue
      const p = arcAt(XY[l.a], XY[l.b], (t - l.t0) / Math.max(1, l.t1 - l.t0))
      out.push({ l, k, x: p.x, y: p.y })
    }
    return out
  }, [vis, t, mode])

  /** Nokta büyüklüğü: o merkeze değen yük. */
  const hubFlow = useMemo(() => {
    const out = new Array(18).fill(0)
    for (const { l } of vis) {
      out[l.a] += l.desi
      out[l.b] += l.desi
    }
    return out
  }, [vis])
  const hubMax = Math.max(1, ...hubFlow)

  /* ── yakınlaştırma / kaydırma ──────────────────────────────── */
  const [vb, setVb] = useState(VIEW0)
  const svgRef = useRef<SVGSVGElement>(null)
  const drag = useRef<{ cx: number; cy: number; vx: number; vy: number; s: number } | null>(null)
  const [grabbing, setGrabbing] = useState(false)

  const clampX = (x: number, w: number) => Math.max(-60, Math.min(BOX.w - w + 60, x))
  const clampY = (y: number, h: number) => Math.max(-60, Math.min(BOX.h - h + 60, y))

  const zoom = useCallback(
    (f: number, ax?: number, ay?: number) =>
      setVb((p) => {
        const w = Math.min(BOX.w, Math.max(BOX.w * 0.16, p.w * f))
        const h = (w / p.w) * p.h
        const cx = ax ?? p.x + p.w / 2
        const cy = ay ?? p.y + p.h / 2
        return {
          w,
          h,
          x: clampX(cx - ((cx - p.x) * w) / p.w, w),
          y: clampY(cy - ((cy - p.y) * h) / p.h, h),
        }
      }),
    [],
  )

  const local = (e: { clientX: number; clientY: number }) => {
    const r = svgRef.current!.getBoundingClientRect()
    return { x: vb.x + ((e.clientX - r.left) / r.width) * vb.w, y: vb.y + ((e.clientY - r.top) / r.height) * vb.h }
  }

  const onDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return
    const r = svgRef.current!.getBoundingClientRect()
    drag.current = { cx: e.clientX, cy: e.clientY, vx: vb.x, vy: vb.y, s: vb.w / r.width }
    setGrabbing(true)
  }
  const onMove = (e: React.MouseEvent) => {
    const g = drag.current
    if (!g) return
    setVb((p) => ({
      ...p,
      x: clampX(g.vx - (e.clientX - g.cx) * g.s, p.w),
      y: clampY(g.vy - (e.clientY - g.cy) * g.s, p.h),
    }))
  }
  const onUp = () => {
    drag.current = null
    setGrabbing(false)
  }

  const z = Math.max(1, Math.sqrt(BOX.w / vb.w))
  const pickPts = pick ? pick.path.map((i) => XY[i]) : []

  const dateOpts = useMemo(() => ['', ...DATES], [])

  return (
    <div className="map">
      {/* ══════════════ sol ray: katmanlar ve süzgeçler ══════════════ */}
      <div className="mrail l">
        <div className="ch3">Karar katmanları</div>
        {LAYERS.map((L) => (
          <Switch
            key={L.k}
            on={layers[L.k]}
            color={L.color}
            onChange={(v) => setLayers((q) => ({ ...q, [L.k]: v }))}
            label={L.label}
            count={n0(counts[L.k])}
          />
        ))}

        <div style={{ borderTop: '1px solid var(--line)', margin: '12px 0 10px' }} />
        <div className="ch3">Çıkış tarihi</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {dateOpts.map((d) => (
            <button
              key={d || 'all'}
              type="button"
              className={'chip' + (filter.date === d ? ' on' : '')}
              style={{ cursor: 'pointer', padding: '5px 8px', fontSize: 10.5 }}
              onClick={() => setFilter((q) => ({ ...q, date: d }))}
            >
              {d ? d.slice(0, 5) : 'tüm ufuk'}
            </button>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--line)', margin: '12px 0 10px' }} />
        <div className="ch3">Araç türü</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          <button
            type="button"
            className={'chip' + (filter.vt === 'all' ? ' on' : '')}
            style={{ cursor: 'pointer', padding: '5px 8px', fontSize: 10.5 }}
            onClick={() => setFilter((q) => ({ ...q, vt: 'all' }))}
          >
            tümü
          </button>
          {VT_ORDER.map((vt) => (
            <button
              key={vt}
              type="button"
              className={'chip' + (filter.vt === vt ? ' on' : '')}
              style={{
                cursor: 'pointer',
                padding: '5px 8px',
                fontSize: 10.5,
                ...(filter.vt === vt
                  ? { borderColor: VT_COLOR[vt] + '88', color: VT_COLOR[vt], background: VT_COLOR[vt] + '1a' }
                  : {}),
              }}
              onClick={() => setFilter((q) => ({ ...q, vt: q.vt === vt ? 'all' : vt }))}
            >
              {vt}
            </button>
          ))}
        </div>

        {(focus !== null || filter.date !== '' || filter.vt !== 'all' || pick) && (
          <button
            type="button"
            className="btn"
            style={{ marginTop: 12, width: '100%', justifyContent: 'center' }}
            onClick={() => {
              setFocus(null)
              setPick(null)
              setFilter((q) => ({ ...q, date: '', vt: 'all' }))
            }}
          >
            {Icon.reset} Seçimi temizle
          </button>
        )}

        <p className="note" style={{ marginTop: 14, fontSize: 11 }}>
          Bir <b>merkeze</b> tıklayın: yalnız oraya değen bacaklar kalır. Bir <b>rotaya</b> tıklayın:
          o aracın tüm zinciri açılır. Tekerlekle yakınlaştırın, sürükleyerek kaydırın.
        </p>
      </div>

      {/* ══════════════ harita alanı ══════════════ */}
      <div className="marea" style={{ background: 'radial-gradient(900px 520px at 50% 40%, #0a121d, #070a0f 74%)' }}>
      <svg
        ref={svgRef}
        viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
        preserveAspectRatio="xMidYMid meet"
        onWheel={(e) => {
          const p = local(e)
          zoom(e.deltaY > 0 ? 1.18 : 0.85, p.x, p.y)
        }}
        onMouseDown={onDown}
        onMouseMove={onMove}
        onMouseUp={onUp}
        onMouseLeave={onUp}
        style={{ cursor: grabbing ? 'grabbing' : 'grab' }}
      >
        <defs>
          <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="3.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {LAND.map((d, i) => (
          <path key={i} className="land" d={d} />
        ))}

        {/* ── bacaklar ─────────────────────────────────────── */}
        <g>
          {vis.map(({ l, v, k }, i) => {
            const col = LAYERS.find((x) => x.k === k)!.color
            const faded = pick ? pick.id !== l.v : false
            const wgt = (0.5 + 2.4 * Math.sqrt(l.desi / CAP_MAX)) / z
            const animate = mode === 'akis' && i < 420
            return (
              <path
                key={l.v + '-' + i}
                className={'arc' + (animate ? ' draw' : '')}
                pathLength={1}
                d={arc(XY[l.a], XY[l.b])}
                stroke={col}
                strokeWidth={wgt}
                opacity={faded ? 0.05 : mode === 'zaman' ? 0.13 : 0.42}
                style={{ cursor: 'pointer', ...(animate ? { animationDelay: (i % 140) * 7 + 'ms' } : {}) }}
                onMouseMove={(e) =>
                  tip.show(
                    e,
                    <>
                      <span className="h">
                        {l.v} · {l.vt} · {l.kind}
                      </span>
                      <b>
                        {NAME[l.a]} → {NAME[l.b]}
                      </b>
                      <TipKV
                        rows={[
                          ['kalkış', stamp(l.t0, D.meta.start)],
                          ['varış', stamp(l.t1, D.meta.start)],
                          ['taşınan', n0(l.desi) + ' / ' + n0(l.cap) + ' desi'],
                          ['doluluk', pct(l.fill)],
                          ['mesafe', n0(l.km) + ' km'],
                          ['maliyet', TL(l.cost, 0)],
                          ...(v.stops > 1
                            ? ([['zincir', v.stops + ' bacak · ' + v.id]] as [string, string][])
                            : []),
                        ]}
                      />
                    </>,
                  )
                }
                onMouseLeave={tip.hide}
                onClick={() => setPick(v)}
              />
            )
          })}
        </g>

        {/* ── seçili aracın zinciri ────────────────────────── */}
        {pick && pickPts.length > 1 && (
          <g filter="url(#glow)">
            <path className="arc" d={chainPath(pickPts)} stroke={C.brand} strokeWidth={2.6 / z} opacity={0.95} />
            {pickPts.map((p, i) => (
              <g key={i} transform={`translate(${p.x},${p.y})`}>
                <circle r={9 / z} fill="rgba(255,96,0,.22)" />
                <circle r={6 / z} fill="#ff8a3d" stroke="#0a0f18" strokeWidth={1.3 / z} />
                <text
                  y={2.7 / z}
                  textAnchor="middle"
                  fontSize={8 / z}
                  fontWeight={700}
                  fill="#0a0f18"
                  fontFamily='"Cascadia Mono",Consolas,monospace'
                >
                  {i + 1}
                </text>
              </g>
            ))}
          </g>
        )}

        {/* ── merkezler ────────────────────────────────────── */}
        {D.centres.map((c, i) => {
          const p = XY[i]
          const lb = LABEL[c.n] ?? [11, 4, 'start']
          const r = (3 + 7 * Math.sqrt((hubFlow[i] || 0) / hubMax)) / Math.sqrt(z)
          const on = focus === i
          return (
            <g
              key={c.n}
              className={'hub' + (on ? ' on' : '')}
              transform={`translate(${p.x},${p.y})`}
              onClick={(e) => {
                e.stopPropagation()
                setFocus(on ? null : i)
                setPick(null)
              }}
              onMouseMove={(e) =>
                tip.show(
                  e,
                  <>
                    <span className="h">Transfer merkezi</span>
                    <b>{c.n}</b>
                    <TipKV
                      rows={[
                        ['elleçleme kotası', n0(c.hand) + ' desi/gün'],
                        ['tır kotası', c.tir === 0 ? 'yok — tır giremez' : c.tir + ' ziyaret/gün'],
                        ['çıkan bacak', n0(slice.out[i])],
                        ['gelen bacak', n0(slice.in[i])],
                        ['değen yük', compact(hubFlow[i] || 0) + ' desi'],
                      ]}
                    />
                  </>,
                )
              }
              onMouseLeave={tip.hide}
            >
              {on && <circle className="pulse" r={r + 9} fill={C.brand} />}
              {c.tir === 0 && (
                <circle r={r + 4 / Math.sqrt(z)} fill="none" stroke="rgba(255,96,0,.6)" strokeWidth={1.2 / z} strokeDasharray="2 3" />
              )}
              <circle className="core" r={r} fill={on ? C.brand : c.tir === 0 ? '#ff8a3d' : C.blue} />
              <text x={lb[0] / Math.sqrt(z)} y={lb[1] / Math.sqrt(z)} textAnchor={lb[2] as 'start'} fontSize={10 / Math.sqrt(z)}>
                {c.n}
              </text>
            </g>
          )
        })}

        {/* ── o an yolda olanlar ───────────────────────────── */}
        {flying.map(({ l, k, x, y }, i) => {
          const col = LAYERS.find((q) => q.k === k)!.color
          const rr = (2.1 + 3.4 * Math.sqrt(l.desi / CAP_MAX)) / z
          return (
            <g key={l.v + '-' + i} transform={`translate(${x.toFixed(1)},${y.toFixed(1)})`}>
              <circle r={rr * 2.4} fill={col} opacity={0.15} />
              <circle r={rr} fill={col} stroke="#070a0f" strokeWidth={0.6 / z} />
            </g>
          )
        })}
      </svg>

      {/* ══════════════ kip / zaman ══════════════ */}
      <div className="mbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Seg
            value={mode}
            onChange={setMode}
            options={[
              { v: 'akis' as const, l: 'Akış' },
              { v: 'zaman' as const, l: 'Zaman' },
            ]}
          />
          {mode === 'zaman' ? (
            <>
              <button type="button" className="btn on" onClick={() => setPlay((p) => !p)}>
                {play ? Icon.pause : Icon.play}
                {play ? 'Duraklat' : 'Oynat'}
              </button>
              <Seg
                value={speed}
                onChange={setSpeed}
                options={[
                  { v: 2, l: '×2' },
                  { v: 6, l: '×6' },
                  { v: 16, l: '×16' },
                  { v: 40, l: '×40' },
                ]}
              />
              <div className="num" style={{ color: C.brand2, fontWeight: 700, fontSize: 15, minWidth: 120 }}>
                {stamp(Math.round(t), D.meta.start)}
              </div>
              <div className="num c-dim" style={{ fontSize: 11 }}>
                {n0(flying.length)} araç yolda
              </div>
            </>
          ) : (
            <Legend
              dot
              items={LAYERS.filter((L) => layers[L.k]).map((L) => [L.color, `${L.label} · ${n0(counts[L.k])}`])}
            />
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            <button type="button" className="btn" onClick={() => zoom(0.78)} title="Yakınlaştır">
              +
            </button>
            <button type="button" className="btn" onClick={() => zoom(1.28)} title="Uzaklaştır">
              −
            </button>
            <button type="button" className="btn" onClick={() => setVb(VIEW0)} title="Haritayı sıfırla">
              {Icon.reset}
            </button>
          </div>
        </div>
        {mode === 'zaman' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
            <span className="num c-dim" style={{ fontSize: 10.5, width: 78 }}>
              {DATES[0]?.slice(0, 5)} 00:00
            </span>
            <input
              className="rng"
              type="range"
              min={0}
              max={span}
              step={5}
              value={Math.round(t)}
              onChange={(e) => {
                setPlay(false)
                setT(+e.target.value)
              }}
              style={{ flex: 1 }}
              aria-label="Plan zamanı"
            />
            <span className="num c-dim" style={{ fontSize: 10.5, width: 78, textAlign: 'right' }}>
              {stamp(span, D.meta.start)}
            </span>
          </div>
        )}
      </div>

      </div>

      {/* ══════════════ sağ ray: seçime göre detay ══════════════ */}
      {pick ? (
        <VehicleCard v={pick} onClose={() => setPick(null)} go={go} />
      ) : focus !== null ? (
        <CentreCard i={focus} onClose={() => setFocus(null)} slice={slice} hub={hubFlow[focus]} />
      ) : (
        <SummaryCard slice={slice} counts={counts} date={filter.date} />
      )}
    </div>
  )
}

/* ══════════════════════ sağ panel içerikleri ══════════════════════ */

function Head({ kicker, title, onClose }: { kicker: string; title: string; onClose?: () => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p className="kicker" style={{ margin: '0 0 5px' }}>
          {kicker}
        </p>
        <div style={{ font: '700 17px/1.2 var(--sans)', letterSpacing: '-.02em' }}>{title}</div>
      </div>
      {onClose && (
        <button type="button" className="btn" style={{ padding: '5px 7px', flex: '0 0 auto' }} onClick={onClose} title="Kapat">
          {Icon.close}
        </button>
      )}
    </div>
  )
}

function Row({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: 12,
        padding: '5px 0',
        borderBottom: '1px solid rgba(28,38,52,.66)',
      }}
    >
      <span style={{ font: '500 11.5px/1.4 var(--sans)', color: 'var(--muted)' }}>{k}</span>
      <span className="num" style={{ fontSize: 12, fontWeight: 600, color: tone || 'var(--ink)' }}>
        {v}
      </span>
    </div>
  )
}

function SummaryCard({
  slice,
  counts,
  date,
}: {
  slice: ReturnType<typeof useSlice>
  counts: Record<LayerKey, number>
  date: string
}) {
  return (
    <div className="mrail r">
      <Head kicker={date ? shortDate(date) : `Tüm ufuk · ${D.meta.horizon[0]} – ${D.meta.horizon[1]}`} title="Seçili kesit" />
      <Row k="Fiziksel araç" v={n0(slice.vehicles.length)} />
      <Row k="Bacak" v={n0(slice.legs.length)} />
      <Row k="Taşınan desi" v={compact(slice.desi)} />
      <Row k="Toplam mesafe" v={n0(slice.km) + ' km'} />
      <Row k="Maliyet" v={M(slice.cost)} tone={C.brand2} />
      <Row k="SLA cezası" v={TL(slice.sla, 0)} tone={slice.sla > 0 ? C.warn : C.ok} />
      <Row k="Ortalama spot doluluk" v={pct(slice.avgFill)} tone={C.ok} />

      <div className="ch3" style={{ margin: '14px 0 9px' }}>
        Karar dağılımı
      </div>
      {LAYERS.map((L) => (
        <div key={L.k} style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ font: '500 11px/1.3 var(--sans)', color: 'var(--muted)' }}>{L.label}</span>
            <span className="num" style={{ fontSize: 11, color: L.color }}>
              {n0(counts[L.k])}
            </span>
          </div>
          <Meter v={counts[L.k]} max={Math.max(1, slice.legs.length)} color={L.color} warnAt={2} />
          <div style={{ font: '500 9.5px/1.35 var(--mono)', color: 'var(--faint)', marginTop: 3 }}>{L.hint}</div>
        </div>
      ))}

      <p className="note" style={{ marginTop: 12, fontSize: 11.5 }}>
        Bir <b>merkeze</b> tıklayın: yalnız oraya değen bacaklar kalır. Bir <b>rotaya</b> tıklayın: o
        aracın tüm zinciri açılır. Tekerlekle yakınlaştırın, sürükleyerek kaydırın.
      </p>
    </div>
  )
}

function CentreCard({
  i,
  onClose,
  slice,
  hub,
}: {
  i: number
  onClose: () => void
  slice: ReturnType<typeof useSlice>
  hub: number
}) {
  const c = D.centres[i]
  const day = D.loadgrid[i]
  const peak = Math.max(...day)
  const rOut = D.rented.filter((r) => r.a === i)
  const rIn = D.rented.filter((r) => r.b === i)
  return (
    <div className="mrail r">
      <Head kicker="Transfer merkezi" title={c.n} onClose={onClose} />
      <Row k="Elleçleme kotası" v={n0(c.hand) + ' desi/gün'} />
      <Row k="Tır ziyaret kotası" v={c.tir === 0 ? 'yok' : c.tir + ' / gün'} tone={c.tir === 0 ? C.brand2 : undefined} />
      <Row k="Çıkan bacak" v={n0(slice.out[i])} />
      <Row k="Gelen bacak" v={n0(slice.in[i])} />
      <Row k="Değen yük" v={compact(hub) + ' desi'} />

      <div className="ch3" style={{ margin: '14px 0 9px' }}>
        Günlük elleçleme kotası kullanımı
      </div>
      {day.map((v, d) => (
        <div key={d} style={{ marginBottom: 7 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
            <span className="num" style={{ fontSize: 10, color: 'var(--dim)' }}>
              {D.daily[d] ? D.daily[d].d.slice(0, 5) : 'ufuk sonrası'}
            </span>
            <span className="num" style={{ fontSize: 10, color: v / c.hand > 0.85 ? C.warn : 'var(--muted)' }}>
              {pct((100 * v) / c.hand)}
            </span>
          </div>
          <Meter v={v} max={c.hand} color={C.blue} />
        </div>
      ))}
      <p className="note hl" style={{ marginTop: 10, fontSize: 11.5 }}>
        Tepe kullanım <b>{pct((100 * peak) / c.hand)}</b>. Kota gün bazlıdır ve 00:00'da sıfırlanır;
        gece yarısını aşan elleçleme iki güne <b>oransal</b> bölünür.
      </p>

      {(rOut.length > 0 || rIn.length > 0) && (
        <>
          <div className="ch3" style={{ margin: '14px 0 7px' }}>
            Zorunlu kiralık rotalar
          </div>
          {rOut.map((r, k) => (
            <Row key={'o' + k} k={'→ ' + NAME[r.b]} v={`${r.n} × ${r.t}`} tone={C.warn} />
          ))}
          {rIn.map((r, k) => (
            <Row key={'i' + k} k={'← ' + NAME[r.a]} v={`${r.n} × ${r.t}`} tone={C.warn} />
          ))}
        </>
      )}
    </div>
  )
}

function VehicleCard({ v, onClose, go }: { v: Vehicle; onClose: () => void; go: ViewProps['go'] }) {
  const ls = vehicleLegs(v)
  const lane = laneOf(ls[0].a, ls[0].b)
  /** durak listesi: çıkış + her bacağın varışı */
  const stops = [{ n: NAME[ls[0].a], t: ls[0].t0, leg: ls[0], origin: true }].concat(
    ls.map((l) => ({ n: NAME[l.b], t: l.t1, leg: l, origin: false })),
  )
  return (
    <div className="mrail r">
      <Head
        kicker={v.stops > 1 ? (v.pickup ? 'Zincir · yol üstü yük alma' : 'Konsolidasyon zinciri') : `${v.kind} sefer`}
        title={`${v.id} · ${v.vt}`}
        onClose={onClose}
      />
      <div className="chips" style={{ marginBottom: 11 }}>
        <span className="chip" style={{ borderColor: KIND_COLOR[v.kind] + '77', color: KIND_COLOR[v.kind] }}>
          {v.kind}
        </span>
        <span className="chip" style={{ borderColor: VT_COLOR[v.vt] + '77', color: VT_COLOR[v.vt] }}>
          {n0(v.cap)} desi kapasite
        </span>
        <span className="chip">{v.stops} bacak</span>
        {v.pickup === 1 && <span className="chip on">{v.picked} yol üstü parça</span>}
        {v.kind === 'Kiralık' && RENTED_KEYS.has(ls[0].a * 100 + ls[0].b) && <span className="chip ok">zorunlu rota</span>}
      </div>

      <Row k="Tepe yük" v={`${n0(v.desi)} / ${n0(v.cap)} desi`} />
      <div style={{ margin: '8px 0 11px' }}>
        <Meter v={v.desi} max={v.cap} color={v.fill > 90 ? C.ok : C.blue} warnAt={2} />
        <div className="num" style={{ fontSize: 11, color: C.ok, marginTop: 4, textAlign: 'right' }}>
          {pct(v.fill)} doluluk
        </div>
      </div>
      <Row k="Kullanım süresi" v={dur(v.use)} />
      <Row k="Toplam mesafe" v={n0(v.km) + ' km'} />
      <Row k="Talep parçası" v={n0(v.parts)} />
      <Row k="SLA cezası" v={TL(v.sla, 0)} tone={v.sla > 0 ? C.warn : C.ok} />
      <Row k="Toplam maliyet" v={TL(v.cost, 0)} tone={C.brand2} />

      <div className="ch3" style={{ margin: '15px 0 10px' }}>
        Rota{lane && <span className="sub">SLA {lane.sla} gün</span>}
      </div>
      <div style={{ position: 'relative', paddingLeft: 21 }}>
        <div
          style={{
            position: 'absolute',
            left: 6,
            top: 8,
            bottom: 14,
            width: 2,
            background: 'linear-gradient(180deg,#ff6000,rgba(255,96,0,.16))',
          }}
        />
        {stops.map((s, i) => {
          /* plandaki gerçek indirme miktarı — fark hesabı yük almada yanılır */
          const drop = s.origin ? 0 : s.leg.drop
          return (
            <div key={i} style={{ position: 'relative', marginBottom: 13 }}>
              <div
                style={{
                  position: 'absolute',
                  left: -21,
                  top: 2,
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  background: s.origin ? C.brand : '#ff8a3d',
                  border: '2px solid #0a0f18',
                  font: '700 8px/10px var(--mono)',
                  color: '#0a0f18',
                  textAlign: 'center',
                }}
              >
                {i + 1}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                <span style={{ font: '600 12.5px/1.3 var(--sans)' }}>{s.n}</span>
                <span className="num" style={{ fontSize: 11.5, color: C.brand2 }}>
                  {clock(s.t)}
                </span>
              </div>
              <div className="num" style={{ fontSize: 10.5, color: 'var(--dim)', marginTop: 2, lineHeight: 1.45 }}>
                {s.origin
                  ? `${n0(s.leg.load)} desi yüklendi · ${s.leg.parts} parça · elleçleme ${s.leg.hld} dk`
                  : `${n0(drop)} desi bırakıldı · ${n0(s.leg.km)} km yol · elleçleme ${s.leg.hun} dk`}
              </div>
            </div>
          )
        })}
      </div>

      {v.stops > 1 && (
        <p className="note hl" style={{ marginTop: 10, fontSize: 11.5 }}>
          Milk-run olmasaydı bu <b>{v.stops} ayrı araç</b> demekti. Zincir yeni bacak yaratmaz — aynı
          sayıda segmenti tek fiziksel araca bindirir.
        </p>
      )}

      <button type="button" className="btn" style={{ marginTop: 12, width: '100%', justifyContent: 'center' }} onClick={() => go('filo')}>
        {Icon.truck} Filo tablosunda aç
      </button>
    </div>
  )
}
