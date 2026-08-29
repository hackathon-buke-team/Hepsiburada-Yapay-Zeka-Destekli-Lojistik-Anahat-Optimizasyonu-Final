/* Panonun TÜM durumu tek yerde ve URL'ye serileştirilebilir.

   Görünümler bu durumu okur; kendi yerel kopyalarını tutmazlar. Böylece
   sekme değişiminde hiçbir şey kaybolmaz, her ekran paylaşılabilir bir
   adrese sahip olur, seçili araç görünümler arasında taşınır ve Esc tek
   tuşta bilinen bir zemine döner.

   Eskiden durum üç ayrı yerdeydi (App.filter, MapView'ın yerel
   pick/focus/zoom/mode/t'si, Fleet'in yerel selId/q'su) ve URL'de yalnız
   sekme adı tutuluyordu. */
import type { Filter } from './store'

export const VIEW_IDS = ['ozet', 'harita', 'filo', 'kisit', 'talep', 'model'] as const
export const LAYER_KEYS = ['kiralik', 'spot', 'zincir', 'pickup'] as const

export interface PanoState {
  view: string
  /** '' = tüm ufuk */
  date: string
  kind: 'all' | 'Kiralık' | 'Spot'
  vt: string
  chainsOnly: boolean
  pickupOnly: boolean
  /** seçili araç kimliği, '' = seçim yok */
  sel: string
  /** odaklı merkez indeksi, -1 = odak yok */
  focus: number
  mode: 'akis' | 'zaman'
  /** zaman kipinde ufuk başlangıcından dakika */
  t: number
  speed: number
  /** harita viewBox'ı; vw = 0 "varsayılan görünüm" demektir (yükseklik
      en-boy oranı sabit olduğu için genişlikten türetilir) */
  vx: number
  vy: number
  vw: number
  layers: Record<string, boolean>
  /** filo arama kutusu */
  q: string
}

export const PANO0: PanoState = {
  view: 'ozet',
  date: '',
  kind: 'all',
  vt: 'all',
  chainsOnly: false,
  pickupOnly: false,
  sel: '',
  focus: -1,
  mode: 'akis',
  t: 0,
  speed: 6,
  vx: 0,
  vy: 0,
  vw: 0,
  layers: { kiralik: true, spot: true, zincir: true, pickup: true },
  q: '',
}

/** Kısa URL anahtarları — hash gözle okunabilir kalsın diye tek/iki harfli. */
const STR: [keyof PanoState, string][] = [
  ['date', 'd'],
  ['kind', 'k'],
  ['vt', 'vt'],
  ['sel', 'v'],
  ['q', 'q'],
]
const NUM: [keyof PanoState, string][] = [
  ['focus', 'f'],
  ['t', 't'],
  ['speed', 's'],
  ['vx', 'vx'],
  ['vy', 'vy'],
  ['vw', 'vw'],
]
const BOOL: [keyof PanoState, string][] = [
  ['chainsOnly', 'c'],
  ['pickupOnly', 'p'],
]

const hepsiAcik = (l: Record<string, boolean>) => LAYER_KEYS.every((k) => l[k])

export function toHash(s: PanoState): string {
  const q = new URLSearchParams()
  for (const [key, sh] of STR) {
    const v = s[key] as string
    if (v !== (PANO0[key] as string)) q.set(sh, v)
  }
  for (const [key, sh] of NUM) {
    const v = s[key] as number
    if (v !== (PANO0[key] as number)) q.set(sh, String(v))
  }
  for (const [key, sh] of BOOL) {
    if (s[key] !== PANO0[key]) q.set(sh, '1')
  }
  if (s.mode !== PANO0.mode) q.set('m', s.mode)
  if (!hepsiAcik(s.layers)) q.set('l', LAYER_KEYS.filter((k) => s.layers[k]).join(','))
  const qs = q.toString()
  return '#' + s.view + (qs ? '?' + qs : '')
}

export function fromHash(h: string): PanoState {
  const raw = h.startsWith('#') ? h.slice(1) : h
  const [viewPart, queryPart] = raw.split('?')
  const s: PanoState = { ...PANO0, layers: { ...PANO0.layers } }
  if (viewPart && (VIEW_IDS as readonly string[]).includes(viewPart)) s.view = viewPart
  if (queryPart === undefined) return s

  const q = new URLSearchParams(queryPart)
  for (const [key, sh] of STR) {
    const v = q.get(sh)
    if (v !== null) (s[key] as string) = v
  }
  for (const [key, sh] of NUM) {
    const v = q.get(sh)
    if (v === null) continue
    const n = Number(v)
    if (v.trim() !== '' && Number.isFinite(n)) (s[key] as number) = n
  }
  for (const [key, sh] of BOOL) {
    if (q.get(sh) === '1') (s[key] as boolean) = true
  }
  const m = q.get('m')
  if (m === 'akis' || m === 'zaman') s.mode = m
  const l = q.get('l')
  if (l !== null) {
    const acik = new Set(l.split(',').filter(Boolean))
    for (const k of LAYER_KEYS) s.layers[k] = acik.has(k)
  }
  if (s.kind !== 'Kiralık' && s.kind !== 'Spot') s.kind = 'all'
  return s
}

/** Mevcut görünümlerin beklediği süzgeç biçimi. */
export function toFilter(s: PanoState): Filter {
  return {
    date: s.date,
    kind: s.kind,
    vt: s.vt,
    chainsOnly: s.chainsOnly,
    pickupOnly: s.pickupOnly,
  }
}
