import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'

/* ══════════════ renk paleti (styles.css ile birebir) ══════════════ */
export const C = {
  brand: '#ff6000',
  brand2: '#ffa14a',
  brandD: '#b34400',
  blue: '#57a6ff',
  blueD: '#2b6db8',
  ok: '#3dd68c',
  warn: '#ffc53d',
  bad: '#ff4d6d',
  purple: '#b18cff',
  pink: '#ff6b9d',
  teal: '#35d7d0',
  ink: '#e9eff7',
  ink2: '#b9c6d8',
  muted: '#7f8da2',
  dim: '#56637a',
  faint: '#38445a',
  line: '#1c2634',
  panel: '#0d131c',
} as const

/** Araç türü -> renk (panonun her yerinde aynı). */
export const VT_COLOR: Record<string, string> = {
  Tır: '#8d9cb5',
  Kamyon: C.blue,
  'Hafif Kamyon': C.purple,
  Kamyonet: C.brand,
}
/** Araç tipi (kiralık / spot) -> renk. */
export const KIND_COLOR: Record<string, string> = {
  Kiralık: C.warn,
  Spot: C.blue,
}

/* ══════════════ kart ══════════════ */
export function Card({
  title,
  sub,
  children,
  className = '',
  onClick,
  style,
}: {
  title?: ReactNode
  sub?: ReactNode
  children?: ReactNode
  className?: string
  onClick?: () => void
  style?: React.CSSProperties
}) {
  return (
    <div
      className={'card' + (onClick ? ' click' : '') + (className ? ' ' + className : '')}
      onClick={onClick}
      style={style}
    >
      {title !== undefined && (
        <h3>
          {title}
          {sub !== undefined && <span className="sub">{sub}</span>}
        </h3>
      )}
      {children}
    </div>
  )
}

/* ══════════════ KPI ══════════════ */
export function Kpi({
  v,
  l,
  d,
  tone,
  sm,
  unit,
  onClick,
}: {
  v: ReactNode
  l: ReactNode
  d?: ReactNode
  tone?: 'brand' | 'ok' | 'blue' | 'warn' | 'bad'
  sm?: boolean
  unit?: string
  onClick?: () => void
}) {
  return (
    <div className={'card tight kpi' + (onClick ? ' click' : '')} onClick={onClick}>
      <div className={'v' + (sm ? ' sm' : '') + (tone ? ' c-' + tone : '')}>
        {v}
        {unit && <span className="u">{unit}</span>}
      </div>
      <div className="l">{l}</div>
      {d !== undefined && <div className="d c-ok">{d}</div>}
    </div>
  )
}

/* ══════════════ yatay bar listesi ══════════════ */
export interface BarRow {
  n: ReactNode
  v: number
  q: ReactNode
  cls?: '' | 'hi' | 'z'
  col?: string
  key?: string
}

export function Bars({
  rows,
  nw = 96,
  qw = 74,
  max,
}: {
  rows: BarRow[]
  nw?: number
  qw?: number
  max?: number
}) {
  const mx = max ?? Math.max(1, ...rows.map((r) => r.v))
  return (
    <div className="bars" style={{ ['--nw' as string]: nw + 'px', ['--qw' as string]: qw + 'px' }}>
      {rows.map((r, i) => (
        <div className={'r ' + (r.cls || '')} key={r.key ?? i}>
          <div className="n">{r.n}</div>
          <div className="t">
            <i
              style={{
                ['--w' as string]: Math.max((r.v / mx) * 100, r.v > 0 ? 1.6 : 0) + '%',
                animationDelay: i * 22 + 'ms',
                ...(r.col ? { background: r.col } : {}),
              }}
            />
          </div>
          <div className="q">{r.q}</div>
        </div>
      ))}
    </div>
  )
}

/* ══════════════ segment seçici ══════════════ */
export function Seg<T extends string | number>({
  value,
  onChange,
  options,
}: {
  value: T
  onChange: (v: T) => void
  options: { v: T; l: ReactNode; disabled?: boolean }[]
}) {
  return (
    <div className="seg">
      {options.map((o) => (
        <button
          key={String(o.v)}
          className={o.v === value ? 'on' : ''}
          disabled={o.disabled}
          onClick={() => onChange(o.v)}
          type="button"
        >
          {o.l}
        </button>
      ))}
    </div>
  )
}

/* ══════════════ anahtar ══════════════ */
export function Switch({
  on,
  onChange,
  label,
  count,
  color,
}: {
  on: boolean
  onChange: (v: boolean) => void
  label: ReactNode
  count?: ReactNode
  color?: string
}) {
  return (
    <div
      className={'sw' + (on ? ' on' : '')}
      onClick={() => onChange(!on)}
      role="switch"
      aria-checked={on}
    >
      <i style={on && color ? { background: color + '30', borderColor: color + '99' } : undefined}>
        {on && color && (
          <span
            style={{
              position: 'absolute',
              left: 2,
              top: 1.5,
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: color,
              transform: 'translateX(13px)',
            }}
          />
        )}
      </i>
      <span>{label}</span>
      {count !== undefined && <span className="n">{count}</span>}
    </div>
  )
}

/* ══════════════ efsane ══════════════ */
export function Legend({
  items,
  dot,
}: {
  items: [string, ReactNode][]
  dot?: boolean
}) {
  return (
    <div className="leg">
      {items.map(([c, l], i) => (
        <span key={i}>
          <i className={dot ? 'd' : ''} style={{ background: c }} />
          {l}
        </span>
      ))}
    </div>
  )
}

/* ══════════════ modal ══════════════ */
export function Modal({
  title,
  kicker,
  onClose,
  children,
  width,
}: {
  title: ReactNode
  kicker?: ReactNode
  onClose: () => void
  children: ReactNode
  width?: number
}) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    addEventListener('keydown', h)
    document.body.style.overflow = 'hidden'
    return () => {
      removeEventListener('keydown', h)
      document.body.style.overflow = ''
    }
  }, [onClose])
  return (
    <div className="modal" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bd" onMouseDown={onClose} />
      <div className="win" style={width ? { width: `min(${width}px, 95vw)` } : undefined}>
        <button className="x" onClick={onClose} title="Kapat (Esc)" type="button">
          ✕
        </button>
        {kicker && <p className="kicker">{kicker}</p>}
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  )
}

/* ══════════════ ipucu (tooltip) ══════════════ */
interface TipState {
  x: number
  y: number
  node: ReactNode
}
const TipCtx = createContext<{
  show: (e: { clientX: number; clientY: number }, node: ReactNode) => void
  hide: () => void
}>({ show: () => {}, hide: () => {} })

export function TipProvider({ children }: { children: ReactNode }) {
  const [tip, setTip] = useState<TipState | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  const show = useCallback(
    (e: { clientX: number; clientY: number }, node: ReactNode) =>
      setTip({ x: e.clientX, y: e.clientY, node }),
    [],
  )
  const hide = useCallback(() => setTip(null), [])
  useLayoutEffect(() => {
    const el = ref.current
    if (!el || !tip) return
    const r = el.getBoundingClientRect()
    let x = tip.x + 15
    let y = tip.y + 15
    if (x + r.width > innerWidth - 10) x = tip.x - r.width - 15
    if (y + r.height > innerHeight - 10) y = tip.y - r.height - 15
    el.style.left = Math.max(8, x) + 'px'
    el.style.top = Math.max(8, y) + 'px'
  }, [tip])
  return (
    <TipCtx.Provider value={{ show, hide }}>
      {children}
      {tip && (
        <div className="tip" ref={ref} style={{ left: tip.x + 15, top: tip.y + 15 }}>
          {tip.node}
        </div>
      )}
    </TipCtx.Provider>
  )
}
export const useTip = () => useContext(TipCtx)

/** İpucu içinde anahtar/değer satırları. */
export function TipKV({ rows }: { rows: [ReactNode, ReactNode][] }) {
  return (
    <div className="kv">
      {rows.map(([k, v], i) => (
        <span key={i} style={{ display: 'contents' }}>
          <i>{k}</i>
          <b>{v}</b>
        </span>
      ))}
    </div>
  )
}

/* ══════════════ simgeler (tek çizgi, 24×24) ══════════════ */
const P = (d: string) => (
  <svg viewBox="0 0 24 24" aria-hidden>
    <path d={d} />
  </svg>
)
export const Icon = {
  grid: P('M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z'),
  map: P('M9 4 3 6.5v13L9 17l6 2.5 6-2.5v-13L15 7 9 4zM9 4v13M15 7v12.5'),
  truck: P('M3 7h11v8H3zM14 10h4l3 3v2h-7zM7 18.5a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2zM17.5 18.5a1.6 1.6 0 1 0 0-3.2 1.6 1.6 0 0 0 0 3.2z'),
  gauge: P('M12 20a8 8 0 1 1 8-8M12 12l4.5-3.2'),
  chart: P('M4 20V9M10 20V4M16 20v-7M22 20H2'),
  layers: P('M12 3 3 7.5l9 4.5 9-4.5L12 3zM3 12.5 12 17l9-4.5M3 17 12 21.5 21 17'),
  flow: P('M6 4v5a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v5M6 4a2 2 0 1 0 0-.1M18 20a2 2 0 1 0 0 .1M12 12h.01'),
  shield: P('M12 3 5 6v6c0 4.4 3 8.2 7 9 4-.8 7-4.6 7-9V6l-7-3zM9 12l2 2 4-4'),
  clock: P('M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3.5 2'),
  play: P('M7 4.5v15l12-7.5-12-7.5z'),
  pause: P('M8 5h3v14H8zM13 5h3v14h-3z'),
  reset: P('M4 5v5h5M4.5 10a8 8 0 1 1 .5 5.5'),
  info: P('M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 7.5h.01'),
  search: P('M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4'),
  down: P('M6 9l6 6 6-6'),
  right: P('M9 6l6 6-6 6'),
  close: P('M6 6l12 12M18 6L6 18'),
  book: P('M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15zM4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5A2.5 2.5 0 0 1 4 20.5z'),
}

/* ══════════════ sayı animasyonu ══════════════ */
export function useCountUp(target: number, ms = 700) {
  const [v, setV] = useState(0)
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setV(target)
      return
    }
    let raf = 0
    const t0 = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms)
      setV(target * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return v
}

/* ══════════════ boyut ölçer ══════════════ */
export function useSize<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [s, setS] = useState({ w: 0, h: 0 })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => {
      const r = e.contentRect
      setS({ w: Math.round(r.width), h: Math.round(r.height) })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, s] as const
}
