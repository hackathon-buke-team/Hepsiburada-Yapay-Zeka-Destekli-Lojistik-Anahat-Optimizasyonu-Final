/* Türkçe sayı / süre biçimleyicileri. Panodaki her sayı buradan geçer. */

const cache = new Map<number, Intl.NumberFormat>()
const fmt = (d: number) => {
  let f = cache.get(d)
  if (!f) {
    f = new Intl.NumberFormat('tr-TR', { minimumFractionDigits: d, maximumFractionDigits: d })
    cache.set(d, f)
  }
  return f
}

/** 1234567 -> "1.234.567" */
export const n0 = (v: number) => fmt(0).format(v)
/** 12,34 basamaklı */
export const nf = (v: number, d = 2) => fmt(d).format(v)
/** 11232476.73 -> "11,23 M₺" */
export const M = (v: number, d = 2) => fmt(d).format(v / 1e6) + ' M₺'
/** 11232476.73 -> "11.232.476,73 ₺" */
export const TL = (v: number, d = 2) => fmt(d).format(v) + ' ₺'
/** 0.7903 girmez — 79.03 girer -> "%79,0" */
export const pct = (v: number, d = 1) => '%' + fmt(d).format(v)
/** 0.3184 -> "%31,8" */
export const pct01 = (v: number, d = 1) => '%' + fmt(d).format(v * 100)
/** işaretli fark: -1800774.92 -> "−1,80 M₺" */
export const dM = (v: number, d = 2) => (v < 0 ? '−' : '+') + fmt(d).format(Math.abs(v) / 1e6) + ' M₺'
export const dTL = (v: number, d = 2) => (v < 0 ? '−' : '+') + fmt(d).format(Math.abs(v)) + ' ₺'
export const dPct = (v: number, d = 1) => (v < 0 ? '−' : '+') + '%' + fmt(d).format(Math.abs(v))

/** 4977975 -> "4,98 M" (birimsiz büyük sayı) */
export const compact = (v: number) => {
  const a = Math.abs(v)
  if (a >= 1e6) return fmt(2).format(v / 1e6) + ' M'
  if (a >= 1e4) return fmt(0).format(v / 1e3) + ' B'
  return fmt(0).format(v)
}

/** 417 dakika -> "6 sa 57 dk" */
export const dur = (min: number) => {
  const h = Math.floor(min / 60)
  const m = Math.round(min % 60)
  if (h === 0) return `${m} dk`
  if (m === 0) return `${h} sa`
  return `${h} sa ${m} dk`
}

/** ufuk dakikası -> "30.06 · 17:36" */
export const stamp = (t: number, startISO: string) => {
  const d = new Date(startISO + 'T00:00:00')
  d.setDate(d.getDate() + Math.floor(t / 1440))
  const mm = ((t % 1440) + 1440) % 1440
  return (
    String(d.getDate()).padStart(2, '0') +
    '.' +
    String(d.getMonth() + 1).padStart(2, '0') +
    ' · ' +
    String(Math.floor(mm / 60)).padStart(2, '0') +
    ':' +
    String(mm % 60).padStart(2, '0')
  )
}

/** ufuk dakikası -> "17:36" */
export const clock = (t: number) => {
  const mm = ((t % 1440) + 1440) % 1440
  return String(Math.floor(mm / 60)).padStart(2, '0') + ':' + String(mm % 60).padStart(2, '0')
}

export const DOW = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
export const DOW_LONG = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
export const AY = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']

/** "29.06.2026" -> "29 Haz Pzt" */
export const shortDate = (dmy: string) => {
  const [d, m, y] = dmy.split('.').map(Number)
  const dt = new Date(y, m - 1, d)
  return `${String(d).padStart(2, '0')} ${AY[m - 1]} ${DOW[(dt.getDay() + 6) % 7]}`
}
