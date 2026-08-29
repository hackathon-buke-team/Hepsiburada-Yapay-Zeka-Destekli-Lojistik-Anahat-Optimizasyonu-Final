import { describe, expect, it } from 'vitest'
import { PANO0, fromHash, toFilter, toHash, type PanoState } from './pano'

describe('toHash', () => {
  it('varsayılan durumda yalnız görünümü yazar', () => {
    expect(toHash(PANO0)).toBe('#ozet')
  })

  it('varsayılandan farklı alanları sorgu dizesi olarak ekler', () => {
    const h = toHash({ ...PANO0, view: 'harita', date: '01.07.2026', sel: 'V0187' })
    expect(h.startsWith('#harita?')).toBe(true)
    expect(decodeURIComponent(h)).toContain('d=01.07.2026')
    expect(decodeURIComponent(h)).toContain('v=V0187')
  })

  it('varsayılana eşit alanları yazmaz', () => {
    expect(toHash({ ...PANO0, view: 'filo' })).toBe('#filo')
  })

  it('tüm katmanlar açıkken katman anahtarını yazmaz', () => {
    expect(toHash({ ...PANO0, view: 'harita' })).toBe('#harita')
  })
})

describe('fromHash', () => {
  it('boş girdide varsayılanı döndürür', () => {
    expect(fromHash('')).toEqual(PANO0)
    expect(fromHash('#')).toEqual(PANO0)
  })

  it('bilinmeyen görünümü yok sayar', () => {
    expect(fromHash('#yokboyle').view).toBe(PANO0.view)
  })

  it('bilinmeyen anahtarları sessizce atar', () => {
    const s = fromHash('#harita?d=01.07.2026&zzz=9')
    expect(s.view).toBe('harita')
    expect(s.date).toBe('01.07.2026')
  })

  it('sayısal alanları çözer, bozuk sayıda varsayılana düşer', () => {
    expect(fromHash('#harita?vw=2.5').vw).toBe(2.5)
    expect(fromHash('#harita?vw=abc').vw).toBe(PANO0.vw)
  })

  it('katman anahtarlarını çözer', () => {
    expect(fromHash('#harita?l=kiralik,zincir').layers).toEqual({
      kiralik: true,
      spot: false,
      zincir: true,
      pickup: false,
    })
  })

  it('boş katman listesinde hepsini kapatır', () => {
    expect(fromHash('#harita?l=')).toMatchObject({
      layers: { kiralik: false, spot: false, zincir: false, pickup: false },
    })
  })

  it('geçersiz kind değerini all yapar', () => {
    expect(fromHash('#filo?k=Uydurma').kind).toBe('all')
  })

  it('varsayılan nesneyi kirletmez', () => {
    const a = fromHash('#harita?l=spot')
    expect(a.layers.kiralik).toBe(false)
    expect(PANO0.layers.kiralik).toBe(true)
  })
})

describe('gidiş-dönüş', () => {
  it('her alanı koruyarak dönüştürür', () => {
    const s: PanoState = {
      view: 'harita',
      date: '03.07.2026',
      kind: 'Spot',
      vt: 'Kamyon',
      chainsOnly: true,
      pickupOnly: true,
      sel: 'V0541',
      focus: 7,
      mode: 'zaman',
      t: 1830,
      speed: 16,
      vx: -120,
      vy: 40,
      vw: 2.4,
      layers: { kiralik: false, spot: true, zincir: true, pickup: false },
      q: 'mersin',
    }
    expect(fromHash(toHash(s))).toEqual(s)
  })

  it('boşluk içeren aramayı korur', () => {
    const s = { ...PANO0, view: 'filo', q: 'yalova eskişehir' }
    expect(fromHash(toHash(s)).q).toBe('yalova eskişehir')
  })
})

describe('toFilter', () => {
  it('yalnız süzgeç alanlarını çıkarır', () => {
    const s = { ...PANO0, date: '01.07.2026', vt: 'Tır', sel: 'V0001', vw: 3 }
    expect(toFilter(s)).toEqual({
      date: '01.07.2026',
      kind: 'all',
      vt: 'Tır',
      chainsOnly: false,
      pickupOnly: false,
    })
  })
})
