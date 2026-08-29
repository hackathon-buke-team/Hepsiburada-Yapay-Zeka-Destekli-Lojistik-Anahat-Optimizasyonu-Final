import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { D, S, STAGES, useSlice, type Filter } from './store'
import { PANO0, fromHash, toFilter, toHash, type PanoState } from './pano'
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
  /** Panonun tüm durumu — görünümler kendi yerel kopyalarını tutmaz. */
  st: PanoState
  /** Kısmi güncelleme; önceki duruma bağlı hesaplar için güncelleyici biçim. */
  set: (p: Partial<PanoState> | ((s: PanoState) => Partial<PanoState>)) => void
  filter: Filter
  /** Uyumluluk sarmalayıcısı: Filter'ın beş alanı PanoState'te aynı adlarla
      bulunduğu için doğrudan yayılabiliyor. */
  setFilter: (f: Filter | ((p: Filter) => Filter)) => void
  go: (v: ViewId) => void
}

/** Görünmeyen görünümleri DONDURUR: React aynı eleman referansını görünce o
    alt ağacı yeniden render etmez. Böylece altı görünüm birden bağlı kalabilir
    (durum korunur) ama haritayı sürüklerken diğer beşi yeniden çizilmez. */
function Donduran({
  acik,
  className,
  children,
}: {
  acik: boolean
  className: string
  children: ReactNode
}) {
  const son = useRef<ReactNode>(children)
  if (acik) son.current = children
  return (
    <div className={className} hidden={!acik}>
      {son.current}
    </div>
  )
}

/** Hakem simülatörünün her aşamada bulduğu ihlal sayısı — veriden okunur.
    Eskiden bu sayı ekranda düz bir '0' dizesiydi; panonun en büyük iddiası
    kendi verisinden doğrulanmıyordu. */
const VIOL_TOTAL = STAGES.reduce((a, k) => a + Number(S(k).violations), 0)

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
    sub: `${n0(D.meta.vehicles)} fiziksel araç · ${n0(D.meta.legs)} bacak · her aracın rotası`,
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
    sub: `${n0(D.history.days.length)} günlük geçmiş · ${n0(D.forecast.daily.length)} günlük tahminimiz`,
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
  const [st, setSt] = useState<PanoState>(() => fromHash(location.hash))
  const set = useCallback(
    (p: Partial<PanoState> | ((s: PanoState) => Partial<PanoState>)) =>
      setSt((s) => ({ ...s, ...(typeof p === 'function' ? p(s) : p) })),
    [],
  )
  const go = useCallback((v: ViewId) => set({ view: v }), [set])
  const setFilter = useCallback(
    (f: Filter | ((p: Filter) => Filter)) =>
      setSt((s) => ({ ...s, ...(typeof f === 'function' ? f(toFilter(s)) : f) })),
    [],
  )
  const filter = useMemo(() => toFilter(st), [st])
  const slice = useSlice(filter)

  /* Durum <-> adres. replaceState kullanıyoruz: her süzgeç değişimi tarayıcı
     geçmişine bir giriş eklemesin, ama ekran paylaşılabilir/geri yüklenebilir
     kalsın. */
  useEffect(() => {
    // Geciktirilmiş: zaman kipi her karede t'yi ilerletiyor; her kare için
    // replaceState çağırmak tarayıcı sınırlarına takılır.
    const id = setTimeout(() => {
      const h = toHash(st)
      if (location.hash !== h) history.replaceState(null, '', h)
    }, 400)
    return () => clearTimeout(id)
  }, [st])

  useEffect(() => {
    const h = () => setSt(fromHash(location.hash))
    addEventListener('hashchange', h)
    return () => removeEventListener('hashchange', h)
  }, [])

  useEffect(() => {
    const yaziyor = (t: EventTarget | null) =>
      t instanceof HTMLInputElement ||
      t instanceof HTMLTextAreaElement ||
      (t instanceof HTMLElement && t.isContentEditable)

    const h = (e: KeyboardEvent) => {
      if (yaziyor(e.target)) return
      if (e.key === 'Escape') {
        // panik tuşu: süzgeç, seçim, odak, katman, zoom, kip — hepsi bilinen zemine
        setSt((s) => ({ ...PANO0, layers: { ...PANO0.layers }, view: s.view }))
        return
      }
      const i = Number(e.key)
      if (i >= 1 && i <= VIEWS.length) setSt((s) => ({ ...s, view: VIEWS[i - 1].id }))
    }
    addEventListener('keydown', h)
    return () => removeEventListener('keydown', h)
  }, [])

  const view = st.view as ViewId
  const cur = VIEWS.find((v) => v.id === view) ?? VIEWS[0]
  const filtered = filter.date || filter.kind !== 'all' || filter.vt !== 'all' || filter.chainsOnly || filter.pickupOnly

  const kpis = useMemo(
    () =>
      filtered
        ? [
            { v: M(slice.cost), l: 'süzülen maliyet', c: 'brand' },
            { v: n0(slice.vehicles.length), l: 'araç', c: '' },
            { v: n0(slice.legs.length), l: 'bacak', c: '' },
            { v: pct(slice.avgFill), l: 'tepe spot doluluk', c: 'ok' },
          ]
        : [
            { v: M(D.meta.total_cost), l: 'toplam maliyet', c: 'brand' },
            { v: n0(VIOL_TOTAL), l: 'hakem ihlali', c: VIOL_TOTAL === 0 ? 'ok' : 'bad' },
            { v: n0(D.meta.vehicles), l: 'fiziksel araç', c: '' },
            { v: pct(D.meta.avg_fill), l: 'tepe spot doluluk', c: 'ok' },
          ],
    [filtered, slice],
  )

  const props: ViewProps = { st, set, filter, setFilter, go }
  /* Bir görünüm ilk kez açıldığında bağlanır ve bir daha sökülmez; böylece
     harita kipi/zoomu, filo araması ve seçimler sekme değişiminde korunur.
     Hiç açılmamış görünüm hiç bağlanmaz — açılış maliyeti artmaz. */
  const acildi = useRef<Set<string>>(new Set([view]))
  acildi.current.add(view)

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
              onClick={() => go(v.id)}
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

          <main className="viewhost">
            {VIEWS.filter((v) => acildi.current.has(v.id)).map((v) => (
              <Donduran
                key={v.id}
                acik={v.id === view}
                className={'view' + (v.flush ? ' flush' : '')}
              >
                {v.id === 'ozet' && <Overview {...props} />}
                {v.id === 'harita' && <MapView {...props} />}
                {v.id === 'filo' && <Fleet {...props} />}
                {v.id === 'kisit' && <Constraints {...props} />}
                {v.id === 'talep' && <Demand {...props} />}
                {v.id === 'model' && <Pipeline {...props} />}
              </Donduran>
            ))}
          </main>
          <div className="hint-esc">Esc: sıfırla · 1–6: görünüm</div>
        </div>
      </div>
    </TipProvider>
  )
}
