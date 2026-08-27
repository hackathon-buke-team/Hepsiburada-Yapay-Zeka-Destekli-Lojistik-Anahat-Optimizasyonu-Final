import { useEffect, useMemo, useState } from 'react'
import { D, FILTER0, useSlice, type Filter } from './store'
import { Icon, TipProvider } from './lib/ui'
import { M, n0, pct } from './lib/fmt'
import Overview from './views/Overview'
import MapView from './views/MapView'
import Fleet from './views/Fleet'
import Constraints from './views/Constraints'
import Demand from './views/Demand'
import Pipeline from './views/Pipeline'

export type ViewId = 'ozet' | 'harita' | 'filo' | 'kisit' | 'talep' | 'model'

export interface ViewProps {
  filter: Filter
  setFilter: (f: Filter | ((p: Filter) => Filter)) => void
  go: (v: ViewId) => void
}

const VIEWS: {
  id: ViewId
  label: string
  title: string
  sub: string
  icon: JSX.Element
  flush?: boolean
}[] = [
  {
    id: 'ozet',
    label: 'ÖZET',
    title: 'Genel bakış',
    sub: 'nihai plan tek ekranda — maliyet, filo, doluluk',
    icon: Icon.grid,
  },
  {
    id: 'harita',
    label: 'HARİTA',
    title: 'Sevkiyat haritası',
    sub: 'kiralık rotalar · spot atamalar · konsolidasyon zincirleri',
    icon: Icon.map,
    flush: true,
  },
  {
    id: 'filo',
    label: 'FİLO',
    title: 'Filo gezgini',
    sub: '665 fiziksel araç · 1.064 bacak · her aracın rotası',
    icon: Icon.truck,
  },
  {
    id: 'kisit',
    label: 'KISIT',
    title: 'Kısıt kullanımı',
    sub: 'elleçleme kotası · tır ziyaret kotası · SLA',
    icon: Icon.gauge,
  },
  {
    id: 'talep',
    label: 'TALEP',
    title: 'Talep ve tahmin',
    sub: '179 günlük geçmiş · 7 günlük tahminimiz',
    icon: Icon.chart,
  },
  {
    id: 'model',
    label: 'MODEL',
    title: 'Model ve boru hattı',
    sub: 'tahmin → Stage 0-3 → hakem → yayın',
    icon: Icon.flow,
  },
]

export default function App() {
  const [view, setView] = useState<ViewId>(() => {
    const h = location.hash.slice(1) as ViewId
    return VIEWS.some((v) => v.id === h) ? h : 'ozet'
  })
  const [filter, setFilter] = useState<Filter>(FILTER0)
  const slice = useSlice(filter)

  useEffect(() => {
    location.hash = view
  }, [view])

  useEffect(() => {
    const h = () => {
      const id = location.hash.slice(1) as ViewId
      if (VIEWS.some((v) => v.id === id)) setView(id)
    }
    addEventListener('hashchange', h)
    return () => removeEventListener('hashchange', h)
  }, [])

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      const i = Number(e.key)
      if (i >= 1 && i <= VIEWS.length) setView(VIEWS[i - 1].id)
    }
    addEventListener('keydown', h)
    return () => removeEventListener('keydown', h)
  }, [])

  const cur = VIEWS.find((v) => v.id === view)!
  const filtered = filter.date || filter.kind !== 'all' || filter.vt !== 'all' || filter.chainsOnly || filter.pickupOnly

  const kpis = useMemo(
    () =>
      filtered
        ? [
            { v: M(slice.cost), l: 'süzülen maliyet', c: 'brand' },
            { v: n0(slice.vehicles.length), l: 'araç', c: '' },
            { v: n0(slice.legs.length), l: 'bacak', c: '' },
            { v: pct(slice.avgFill), l: 'spot doluluk', c: 'ok' },
          ]
        : [
            { v: M(D.meta.total_cost), l: 'toplam maliyet', c: 'brand' },
            { v: '0', l: 'hakem ihlali', c: 'ok' },
            { v: n0(D.meta.vehicles), l: 'fiziksel araç', c: '' },
            { v: pct(D.meta.avg_fill), l: 'spot doluluk', c: 'ok' },
          ],
    [filtered, slice],
  )

  const props: ViewProps = { filter, setFilter, go: setView }

  return (
    <TipProvider>
      <div className="app">
        <nav className="rail">
          <div className="mark" title="Takım Büke">
            B
          </div>
          {VIEWS.map((v, i) => (
            <button
              key={v.id}
              className={v.id === view ? 'on' : ''}
              onClick={() => setView(v.id)}
              title={`${v.title} (${i + 1})`}
              type="button"
            >
              {v.icon}
              {v.label}
            </button>
          ))}
          <div className="sp" />
          <div className="tag">997307</div>
        </nav>

        <div className="main">
          <header className="top">
            <div className="ttl">
              <h1>{cur.title}</h1>
              <p>
                {cur.sub}
                {filtered && <span className="c-brand"> · süzgeç etkin</span>}
              </p>
            </div>
            <div className="sp" />
            <div className="kstrip">
              {kpis.map((k, i) => (
                <div className={'k ' + k.c} key={i}>
                  <div className="v">{k.v}</div>
                  <div className="l">{k.l}</div>
                </div>
              ))}
            </div>
          </header>

          <main className={'view' + (cur.flush ? ' flush' : '')} key={view}>
            {view === 'ozet' && <Overview {...props} />}
            {view === 'harita' && <MapView {...props} />}
            {view === 'filo' && <Fleet {...props} />}
            {view === 'kisit' && <Constraints {...props} />}
            {view === 'talep' && <Demand {...props} />}
            {view === 'model' && <Pipeline {...props} />}
          </main>
        </div>
      </div>
    </TipProvider>
  )
}
