/* Türkiye izdüşümü ve harita geometrisi.
   Eş dikdörtgen izdüşüm, 39° enleminde boylam düzeltmesi — dış harita
   servisi ya da GeoJSON dosyası yok, pano tamamen çevrimdışı çalışır. */

export const GB = {
  lo0: 25.8,
  lo1: 45.2,
  la0: 35.6,
  la1: 42.3,
  W: 1000,
  H: 0,
}
GB.H = Math.round((GB.W * (GB.la1 - GB.la0)) / ((GB.lo1 - GB.lo0) * Math.cos((39 * Math.PI) / 180)))

export const gx = (lon: number) => ((lon - GB.lo0) / (GB.lo1 - GB.lo0)) * GB.W
export const gy = (lat: number) => ((GB.la1 - lat) / (GB.la1 - GB.la0)) * GB.H

/* Basitleştirilmiş kıyı ve sınır noktaları — "boylam,enlem". */
const TR_ANATOLIA = `29.12,41.20 29.60,41.18 30.30,41.13 31.12,41.09 31.42,41.28 31.80,41.49 32.38,41.75 33.00,41.90
33.76,41.98 34.30,41.96 34.75,41.97 35.15,42.03 35.28,41.70 35.60,41.62 36.15,41.30 36.42,41.38
36.78,41.42 37.30,41.10 37.90,41.02 38.40,40.93 39.10,40.98 39.72,40.98 40.30,41.02 41.02,41.30
41.55,41.52 42.60,41.58 43.05,41.25 43.45,41.10 43.60,40.55 43.55,40.10 44.10,40.03 44.80,39.72
44.42,39.40 44.30,38.90 44.42,38.35 44.10,37.90 44.60,37.55 44.80,37.32 44.10,37.30 43.30,37.36
42.80,37.32 42.35,37.12 41.50,37.10 40.70,37.10 39.80,36.85 38.80,36.72 37.90,36.68 37.10,36.68
36.75,36.82 36.62,36.35 36.30,36.00 36.10,35.85 35.92,36.06 36.10,36.45 35.90,36.56 35.55,36.62
35.05,36.72 34.62,36.78 34.20,36.60 34.05,36.30 33.55,36.16 33.20,36.08 32.80,36.30 32.30,36.22
31.60,36.53 31.10,36.75 30.75,36.88 30.60,36.60 30.45,36.30 30.10,36.30 29.70,36.18 29.30,36.30
29.10,36.55 28.85,36.68 28.45,36.75 28.10,36.65 27.42,36.72 27.90,37.02 27.28,37.05 27.55,37.35
27.28,37.62 27.20,37.95 26.90,38.20 26.35,38.32 26.75,38.70 26.72,39.05 26.68,39.30 26.06,39.48
26.20,39.75 26.15,39.98 26.40,40.00 26.70,40.28 27.30,40.42 27.95,40.36 28.50,40.38 29.10,40.43
28.88,40.52 29.28,40.68 29.62,40.70 29.86,40.76 29.72,40.79 29.42,40.79 29.20,40.88 29.10,40.99
29.12,41.06`

const TR_THRACE = `26.05,41.75 26.55,41.85 27.20,42.06 27.55,42.00 28.03,41.98 28.30,41.55 28.75,41.35 29.08,41.22
29.01,40.97 28.72,40.94 28.28,40.99 27.95,40.96 27.51,40.92 27.25,40.83 27.15,40.60 26.70,40.55
26.30,40.28 26.18,40.05 26.30,40.18 26.72,40.55 26.55,40.66 26.08,40.73 26.32,41.15 26.55,41.60
26.30,41.72`

const path = (s: string) =>
  'M' +
  s
    .trim()
    .split(/\s+/)
    .map((p) => {
      const [lo, la] = p.split(',').map(Number)
      return gx(lo).toFixed(1) + ',' + gy(la).toFixed(1)
    })
    .join('L') +
  'Z'

export const LAND: string[] = [path(TR_ANATOLIA), path(TR_THRACE)]

/** Merkez adı -> etiket kaçırma [dx, dy, text-anchor] */
export const LABEL: Record<string, [number, number, string]> = {
  İstanbul: [0, -13, 'middle'],
  Tekirdağ: [-11, 4, 'end'],
  Kocaeli: [12, 3, 'start'],
  Yalova: [-11, 7, 'end'],
  Zonguldak: [11, 4, 'start'],
  Bilecik: [11, 5, 'start'],
  Eskişehir: [11, 6, 'start'],
  Kütahya: [-11, 4, 'end'],
  Balıkesir: [-11, 4, 'end'],
  Manisa: [-11, 4, 'end'],
  Denizli: [-11, 4, 'end'],
  Isparta: [11, 4, 'start'],
  Karaman: [0, 19, 'middle'],
  Mersin: [11, 7, 'start'],
  Sivas: [0, -13, 'middle'],
  Erzincan: [0, -13, 'middle'],
  Şanlıurfa: [0, 19, 'middle'],
  Mardin: [11, 6, 'start'],
}

export interface XY { x: number; y: number }

/** İki merkez arasında hafifçe bükülmüş yay — gidiş/dönüş ayırt edilsin diye. */
export function arc(a: XY, b: XY, bend = 0.11): string {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const cx = (a.x + b.x) / 2 - dy * bend
  const cy = (a.y + b.y) / 2 + dx * bend
  return `M${a.x.toFixed(1)},${a.y.toFixed(1)}Q${cx.toFixed(1)},${cy.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`
}

/** Yayın t ∈ [0,1] parametresindeki noktası (kuadratik Bézier). */
export function arcAt(a: XY, b: XY, t: number, bend = 0.11): XY {
  const dx = b.x - a.x
  const dy = b.y - a.y
  const cx = (a.x + b.x) / 2 - dy * bend
  const cy = (a.y + b.y) / 2 + dx * bend
  const u = 1 - t
  return {
    x: u * u * a.x + 2 * u * t * cx + t * t * b.x,
    y: u * u * a.y + 2 * u * t * cy + t * t * b.y,
  }
}

/** Çok duraklı zincir için tek bir sürekli yol. */
export function chainPath(pts: XY[], bend = 0.12): string {
  if (pts.length < 2) return ''
  let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1]
    const b = pts[i]
    const dx = b.x - a.x
    const dy = b.y - a.y
    const cx = (a.x + b.x) / 2 - dy * bend
    const cy = (a.y + b.y) / 2 + dx * bend
    d += `Q${cx.toFixed(1)},${cy.toFixed(1)} ${b.x.toFixed(1)},${b.y.toFixed(1)}`
  }
  return d
}
