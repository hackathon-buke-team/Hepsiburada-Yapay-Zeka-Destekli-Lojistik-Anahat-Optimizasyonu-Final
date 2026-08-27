import { Fragment, type ReactNode } from 'react'
import { C, useSize, useTip } from './ui'

/* ══════════════════════════════════════════════════════════════════════
   Elle yazılmış SVG grafik ailesi.
   Dış grafik kütüphanesi yok: pano çevrimdışı çalışır, her grafik aynı
   ızgara / tipografi / renk kurallarına uyar.
   ══════════════════════════════════════════════════════════════════════ */

export const AX = { size: 10, fill: C.dim, font: '"Cascadia Mono",Consolas,monospace' }

export function Txt({
  x,
  y,
  children,
  size = 11,
  fill = C.muted,
  weight = 500,
  anchor = 'start',
  sans,
  rot,
  op,
}: {
  x: number
  y: number
  children: ReactNode
  size?: number
  fill?: string
  weight?: number
  anchor?: 'start' | 'middle' | 'end'
  sans?: boolean
  rot?: number
  op?: number
}) {
  return (
    <text
      x={x}
      y={y}
      fill={fill}
      fontSize={size}
      fontWeight={weight}
      textAnchor={anchor}
      opacity={op}
      fontFamily={sans ? '"Inter","Segoe UI",sans-serif' : AX.font}
      style={{ fontVariantNumeric: 'tabular-nums' }}
      transform={rot ? `rotate(${rot} ${x} ${y})` : undefined}
    >
      {children}
    </text>
  )
}

/** Yatay ızgara çizgileri + sol eksen etiketleri. */
export function Grid({
  x,
  y,
  w,
  h,
  n = 4,
  fmt,
  vertical,
}: {
  x: number
  y: number
  w: number
  h: number
  n?: number
  fmt?: (t: number) => string
  vertical?: number
}) {
  const out: ReactNode[] = []
  for (let i = 0; i <= n; i++) {
    const yy = y + h - (h * i) / n
    out.push(<line key={'h' + i} x1={x} y1={yy} x2={x + w} y2={yy} stroke={C.line} strokeWidth={1} />)
    if (fmt)
      out.push(
        <Txt key={'l' + i} x={x - 8} y={yy + 3.5} anchor="end" size={9.5} fill={C.faint}>
          {fmt(i / n)}
        </Txt>,
      )
  }
  if (vertical)
    for (let i = 1; i <= vertical; i++) {
      const xx = x + (w * i) / vertical
      out.push(<line key={'v' + i} x1={xx} y1={y} x2={xx} y2={y + h} stroke={C.line} strokeWidth={1} />)
    }
  return <>{out}</>
}

/** Yuvarlatılmış sütun; h<0.6 ise ince bir çizgi olarak görünür. */
export function Bar({
  x,
  y,
  w,
  h,
  fill,
  r = 4,
  op,
  onEnter,
  onLeave,
}: {
  x: number
  y: number
  w: number
  h: number
  fill: string
  r?: number
  op?: number
  onEnter?: (e: React.MouseEvent) => void
  onLeave?: () => void
}) {
  const hh = Math.max(h, 0.6)
  return (
    <rect
      x={x}
      y={y + h - hh}
      width={w}
      height={hh}
      rx={Math.min(r, w / 2, hh / 2)}
      fill={fill}
      opacity={op}
      onMouseMove={onEnter}
      onMouseLeave={onLeave}
      style={onEnter ? { cursor: 'default' } : undefined}
    />
  )
}

/* ══════════════ ölçekli kapsayıcı ══════════════ */
/** Kart içine oturan, en-boy oranını koruyan responsive SVG. */
export function Chart({
  vw,
  vh,
  children,
  style,
}: {
  vw: number
  vh: number
  children: ReactNode
  style?: React.CSSProperties
}) {
  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', ...style }}>
      <svg
        viewBox={`0 0 ${vw} ${vh}`}
        preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', height: '100%', display: 'block', overflow: 'visible' }}
      >
        {children}
      </svg>
    </div>
  )
}

/* ══════════════ sütun grafiği ══════════════ */
export interface ColSeries {
  key: string
  label: string
  color: string
  values: number[]
}

export function Columns({
  labels,
  series,
  vw = 440,
  vh = 260,
  stacked,
  max,
  fmtY,
  fmtV,
  sub,
  highlight = -1,
  pad = { l: 46, r: 12, t: 14, b: 34 },
  tip,
}: {
  labels: string[]
  series: ColSeries[]
  vw?: number
  vh?: number
  stacked?: boolean
  max?: number
  fmtY?: (t: number) => string
  fmtV?: (v: number, i: number) => string
  sub?: (i: number) => string | undefined
  highlight?: number
  pad?: { l: number; r: number; t: number; b: number }
  tip?: (i: number) => ReactNode
}) {
  const t = useTip()
  const x0 = pad.l
  const y0 = pad.t
  const w = vw - pad.l - pad.r
  const h = vh - pad.t - pad.b
  const n = labels.length
  const totals = labels.map((_, i) =>
    stacked ? series.reduce((a, s) => a + (s.values[i] || 0), 0) : Math.max(...series.map((s) => s.values[i] || 0)),
  )
  const mx = max ?? Math.max(1, ...totals) * 1.12
  const g = w / n
  const bw = stacked ? g * 0.44 : Math.min(g * 0.7, g * 0.68) / series.length

  return (
    <Chart vw={vw} vh={vh}>
      <Grid x={x0} y={y0} w={w} h={h} n={4} fmt={fmtY} />
      {labels.map((lb, i) => {
        const cx = x0 + g * i + g / 2
        const on = i === highlight
        const hover = tip
          ? {
              onEnter: (e: React.MouseEvent) => t.show(e, tip(i)),
              onLeave: t.hide,
            }
          : {}
        let acc = 0
        return (
          <Fragment key={lb + i}>
            {series.map((s, j) => {
              const v = s.values[i] || 0
              const bh = (h * v) / mx
              const bx = stacked ? cx - bw / 2 : cx - (series.length * bw) / 2 + j * bw + 1
              const by = stacked ? y0 + h - acc - bh : y0 + h - bh
              acc += bh
              return (
                <Bar
                  key={s.key}
                  x={bx}
                  y={by}
                  w={stacked ? bw : bw - 2}
                  h={bh}
                  fill={s.color}
                  op={on || highlight < 0 ? 1 : 0.42}
                  r={stacked && j < series.length - 1 ? 0 : 4}
                  {...hover}
                />
              )
            })}
            {fmtV && (
              <Txt x={cx} y={y0 + h - acc - 7} anchor="middle" size={11.5} weight={700} fill={on ? C.brand2 : C.ink2}>
                {fmtV(totals[i], i)}
              </Txt>
            )}
            <Txt x={cx} y={y0 + h + 15} anchor="middle" size={10} fill={on ? C.brand2 : C.dim} weight={on ? 700 : 500}>
              {lb}
            </Txt>
            {sub?.(i) && (
              <Txt x={cx} y={y0 + h + 28} anchor="middle" size={9} fill={C.faint}>
                {sub(i)}
              </Txt>
            )}
          </Fragment>
        )
      })}
    </Chart>
  )
}

/* ══════════════ çizgi + alan ══════════════ */
export function Area({
  values,
  vw = 440,
  vh = 180,
  color = C.blue,
  fmtY,
  marks,
  pad = { l: 44, r: 10, t: 12, b: 24 },
  labels,
  tip,
  max,
  id = 'ar',
}: {
  values: number[]
  vw?: number
  vh?: number
  color?: string
  fmtY?: (t: number) => string
  marks?: { i: number; color: string; label?: string }[]
  pad?: { l: number; r: number; t: number; b: number }
  labels?: [string, string]
  tip?: (i: number) => ReactNode
  max?: number
  id?: string
}) {
  const t = useTip()
  const x0 = pad.l
  const y0 = pad.t
  const w = vw - pad.l - pad.r
  const h = vh - pad.t - pad.b
  const n = values.length
  const mx = max ?? Math.max(1, ...values)
  const px = (i: number) => x0 + (w * i) / Math.max(1, n - 1)
  const py = (v: number) => y0 + h - (h * v) / mx
  const pts = values.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(' ')

  return (
    <Chart vw={vw} vh={vh}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity=".5" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <Grid x={x0} y={y0} w={w} h={h} n={4} fmt={fmtY} />
      <polygon points={`${x0},${y0 + h} ${pts} ${x0 + w},${y0 + h}`} fill={`url(#${id})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
      {marks?.map((m) => (
        <Fragment key={m.i}>
          <line x1={px(m.i)} y1={y0} x2={px(m.i)} y2={y0 + h} stroke={m.color} strokeWidth={1} strokeDasharray="3 3" opacity=".5" />
          <circle cx={px(m.i)} cy={py(values[m.i])} r={4} fill={m.color} stroke="#070a0f" strokeWidth={1.6} />
          {m.label && (
            <Txt x={px(m.i)} y={y0 + h + 15} anchor="middle" size={9} fill={m.color}>
              {m.label}
            </Txt>
          )}
        </Fragment>
      ))}
      {tip && (
        <rect
          x={x0}
          y={y0}
          width={w}
          height={h}
          fill="transparent"
          onMouseMove={(e) => {
            const r = (e.currentTarget as SVGRectElement).getBoundingClientRect()
            const i = Math.round(((e.clientX - r.left) / r.width) * (n - 1))
            if (i >= 0 && i < n) t.show(e, tip(i))
          }}
          onMouseLeave={t.hide}
        />
      )}
      {labels && (
        <>
          <Txt x={x0} y={y0 + h + 17} size={9.5} fill={C.faint}>
            {labels[0]}
          </Txt>
          <Txt x={x0 + w} y={y0 + h + 17} anchor="end" size={9.5} fill={C.faint}>
            {labels[1]}
          </Txt>
        </>
      )}
    </Chart>
  )
}

/* ══════════════ halka ══════════════ */
export function Donut({
  items,
  vw = 430,
  vh = 250,
  center,
  centerSub,
  r = 88,
  ri = 54,
  cx = 120,
  onPick,
}: {
  items: { label: string; v: number; color: string }[]
  vw?: number
  vh?: number
  center?: ReactNode
  centerSub?: string
  r?: number
  ri?: number
  cx?: number
  onPick?: (label: string) => void
}) {
  const cy = vh / 2
  const tot = items.reduce((a, b) => a + b.v, 0) || 1
  let a0 = -Math.PI / 2
  const arcs = items.map((it) => {
    const a1 = a0 + (2 * Math.PI * it.v) / tot
    const big = a1 - a0 > Math.PI ? 1 : 0
    const p = (rr: number, a: number) => [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]
    const [x1, y1] = p(r, a0)
    const [x2, y2] = p(r, a1)
    const [x3, y3] = p(ri, a1)
    const [x4, y4] = p(ri, a0)
    a0 = a1
    return { ...it, d: `M${x1},${y1} A${r},${r} 0 ${big} 1 ${x2},${y2} L${x3},${y3} A${ri},${ri} 0 ${big} 0 ${x4},${y4} Z` }
  })
  const lx = cx + r + 42
  return (
    <Chart vw={vw} vh={vh}>
      {arcs.map((a) => (
        <path
          key={a.label}
          d={a.d}
          fill={a.color}
          stroke="#070a0f"
          strokeWidth={2}
          onClick={onPick ? () => onPick(a.label) : undefined}
          style={onPick ? { cursor: 'pointer' } : undefined}
        />
      ))}
      {center !== undefined && (
        <Txt x={cx} y={cy - 1} anchor="middle" size={24} weight={700} fill="#fff">
          {center}
        </Txt>
      )}
      {centerSub && (
        <Txt x={cx} y={cy + 17} anchor="middle" size={10} fill={C.dim}>
          {centerSub}
        </Txt>
      )}
      {items.map((it, i) => {
        const y = cy - ((items.length - 1) * 30) / 2 + i * 30
        return (
          <Fragment key={it.label}>
            <rect x={lx} y={y - 9} width={11} height={11} rx={3} fill={it.color} />
            <Txt x={lx + 19} y={y} size={11.5} fill={C.muted}>
              {it.label}
            </Txt>
            <Txt x={vw - 8} y={y} anchor="end" size={12.5} weight={700} fill={it.color}>
              {it.v.toLocaleString('tr-TR')}
            </Txt>
          </Fragment>
        )
      })}
    </Chart>
  )
}

/* ══════════════ arama hunisi ══════════════ */
export function Funnel({
  rows,
  vw = 430,
  vh = 220,
  showPct,
}: {
  rows: { label: string; v: number; color?: string }[]
  vw?: number
  vh?: number
  showPct?: boolean
}) {
  const pctW = showPct ? 52 : 6
  const x0 = 6
  const gapY = 12
  const w = vw - 12 - pctW
  const bh = Math.min(44, (vh - 6) / rows.length - gapY)
  const mx = Math.max(...rows.map((r) => r.v))
  return (
    <Chart vw={vw} vh={vh}>
      {rows.map((r, i) => {
        const y = 4 + i * (bh + gapY)
        const val = r.v.toLocaleString('tr-TR')
        const lw = r.label.length * 7.8
        const vwid = val.length * 8.7
        const raw = Math.min(w, w * Math.pow(r.v / mx, 0.3))
        const inside = raw >= 14 + lw + 18 + vwid + 14
        const bw = Math.max(26, inside ? raw : Math.max(14 + lw + 14, Math.min(raw, w - vwid - 22)))
        const col = r.color || C.brand
        return (
          <Fragment key={r.label}>
            <rect x={x0} y={y} width={bw} height={bh} rx={6} fill={col} />
            <Txt x={x0 + 13} y={y + bh / 2 + 4.5} size={12} weight={600} fill="#eef3fa">
              {r.label}
            </Txt>
            {inside ? (
              <Txt x={x0 + bw - 13} y={y + bh / 2 + 5} anchor="end" size={13.5} weight={700} fill="#fff">
                {val}
              </Txt>
            ) : (
              <Txt x={x0 + bw + 10} y={y + bh / 2 + 5} size={13.5} weight={700} fill={col === C.brand ? C.brand2 : C.ink2}>
                {val}
              </Txt>
            )}
            {showPct && i > 0 && (
              <Txt x={vw - 5} y={y + bh / 2 + 4} anchor="end" size={10} fill={C.faint}>
                {'%' + (100 * r.v / rows[i - 1].v).toLocaleString('tr-TR', { maximumFractionDigits: 100 * r.v / rows[i - 1].v < 1 ? 3 : 1 })}
              </Txt>
            )}
          </Fragment>
        )
      })}
    </Chart>
  )
}

/* ══════════════ matris ısı haritası ══════════════ */
export function Matrix({
  rows,
  cols,
  value,
  color,
  cell = 30,
  rowW = 92,
  headH = 22,
  tip,
  onCell,
  gap = 3,
}: {
  rows: string[]
  cols: string[]
  value: (r: number, c: number) => number
  /** 0-1 arası yoğunluk -> renk */
  color: (t: number, r: number, c: number) => string
  cell?: number
  rowW?: number
  headH?: number
  gap?: number
  tip?: (r: number, c: number) => ReactNode
  onCell?: (r: number, c: number) => void
}) {
  const t = useTip()
  const vw = rowW + cols.length * (cell + gap)
  const vh = headH + rows.length * (cell + gap)
  let mx = 0
  for (let r = 0; r < rows.length; r++) for (let c = 0; c < cols.length; c++) mx = Math.max(mx, value(r, c))
  return (
    <Chart vw={vw} vh={vh} style={{ minHeight: rows.length * (cell + gap) + headH }}>
      {cols.map((cl, c) => (
        <Txt key={cl + c} x={rowW + c * (cell + gap) + cell / 2} y={headH - 9} anchor="middle" size={9.5} fill={C.dim}>
          {cl}
        </Txt>
      ))}
      {rows.map((rw, r) => (
        <Fragment key={rw}>
          <Txt x={rowW - 9} y={headH + r * (cell + gap) + cell * 0.66} anchor="end" size={10} fill={C.muted}>
            {rw}
          </Txt>
          {cols.map((_, c) => {
            const v = value(r, c)
            return (
              <rect
                key={c}
                x={rowW + c * (cell + gap)}
                y={headH + r * (cell + gap)}
                width={cell}
                height={cell}
                rx={4}
                fill={color(mx ? v / mx : 0, r, c)}
                onMouseMove={tip ? (e) => t.show(e, tip(r, c)) : undefined}
                onMouseLeave={tip ? t.hide : undefined}
                onClick={onCell ? () => onCell(r, c) : undefined}
                style={{ cursor: onCell ? 'pointer' : tip ? 'default' : undefined }}
              />
            )
          })}
        </Fragment>
      ))}
    </Chart>
  )
}

/* ══════════════ takvim ısı haritası ══════════════ */
export function CalendarHeat({
  start,
  dow0,
  days,
  flag,
  median,
  vw = 900,
  cell = 15,
  gap = 3,
  tip,
}: {
  start: string
  dow0: number
  days: number[]
  flag: number[]
  median: number
  vw?: number
  cell?: number
  gap?: number
  tip?: (i: number) => ReactNode
}) {
  const t = useTip()
  const weeks = Math.ceil((dow0 + days.length) / 7)
  const pad = 26
  const vh = pad + 7 * (cell + gap) + 8
  const DOW = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
  const AY = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
  const x0 = 30
  const scale = Math.min(1, (vw - x0 - 6) / (weeks * (cell + gap)))
  const cw = (cell + gap) * scale
  let month = -1
  const monthLabels: [number, string][] = []
  const base = new Date(start + 'T00:00:00')
  return (
    <Chart vw={vw} vh={vh} style={{ minHeight: vh }}>
      {DOW.map((d, i) =>
        i % 2 === 0 ? (
          <Txt key={d} x={x0 - 7} y={pad + i * (cell + gap) + cell * 0.72} anchor="end" size={9} fill={C.faint}>
            {d}
          </Txt>
        ) : null,
      )}
      {days.map((v, i) => {
        const p = dow0 + i
        const wk = Math.floor(p / 7)
        const dw = p % 7
        const x = x0 + wk * cw
        const y = pad + dw * (cell + gap)
        const f = flag[i]
        const k = Math.min(v / (median * 1.6), 1)
        const fill = f ? (f === 2 ? C.brand : C.warn) : `rgba(87,166,255,${(0.1 + 0.85 * k).toFixed(3)})`
        const d = new Date(base)
        d.setDate(d.getDate() + i)
        if (d.getMonth() !== month) {
          month = d.getMonth()
          monthLabels.push([x, AY[month]])
        }
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={cell * scale}
            height={cell}
            rx={3}
            fill={fill}
            opacity={f ? 0.92 : 1}
            onMouseMove={tip ? (e) => t.show(e, tip(i)) : undefined}
            onMouseLeave={tip ? t.hide : undefined}
            style={{ cursor: tip ? 'default' : undefined }}
          />
        )
      })}
      {monthLabels.map(([x, m], i) => (
        <Txt key={i} x={x} y={pad - 8} size={9.5} weight={700} fill={C.muted}>
          {m}
        </Txt>
      ))}
    </Chart>
  )
}

/* ══════════════ mini çizgi (sparkline) ══════════════ */
export function Spark({
  values,
  w = 110,
  h = 26,
  color = C.blue,
  fill,
}: {
  values: number[]
  w?: number
  h?: number
  color?: string
  fill?: boolean
}) {
  const mx = Math.max(1, ...values)
  const mn = Math.min(...values)
  const rng = mx - mn || 1
  const pts = values.map((v, i) => `${(w * i) / (values.length - 1)},${h - 2 - ((h - 4) * (v - mn)) / rng}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
      {fill && <polygon points={`0,${h} ${pts} ${w},${h}`} fill={color} opacity=".14" />}
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.4} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

/* ══════════════ yatay ölçer ══════════════ */
export function Meter({
  v,
  max,
  color = C.blue,
  h = 8,
  warnAt = 0.85,
}: {
  v: number
  max: number
  color?: string
  h?: number
  warnAt?: number
}) {
  const t = Math.min(1, max ? v / max : 0)
  const col = t >= 1 ? C.bad : t >= warnAt ? C.warn : color
  return (
    <div style={{ height: h, borderRadius: h / 2, background: 'rgba(255,255,255,.06)', overflow: 'hidden' }}>
      <div
        style={{
          height: '100%',
          width: (t * 100).toFixed(2) + '%',
          borderRadius: h / 2,
          background: col,
          transition: 'width .5s cubic-bezier(.2,.85,.3,1), background .3s',
        }}
      />
    </div>
  )
}

/** Kart içinde kendi genişliğine göre ölçeklenen sarmalayıcı. */
export function Fit({ children, ratio = 0.42 }: { children: (w: number, h: number) => ReactNode; ratio?: number }) {
  const [ref, s] = useSize<HTMLDivElement>()
  return (
    <div ref={ref} style={{ flex: 1, minHeight: 0, width: '100%' }}>
      {s.w > 0 && children(s.w, s.h || Math.round(s.w * ratio))}
    </div>
  )
}
