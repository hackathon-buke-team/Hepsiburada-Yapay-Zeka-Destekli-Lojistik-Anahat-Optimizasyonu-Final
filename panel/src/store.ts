import { useMemo } from 'react'
import raw from './data/panel.json'
import type { Leg, PanelData, Vehicle, XYPoint } from './types.ext'
import { GB, gx, gy } from './lib/geo'

export const D = raw as unknown as PanelData

/** Merkez indeksine göre önceden hesaplanmış harita koordinatları. */
export const XY: XYPoint[] = D.centres.map((c) => ({ x: gx(c.lon), y: gy(c.lat) }))
export const BOX = { w: GB.W, h: GB.H }

export const NAME = D.centres.map((c) => c.n)
export const IX: Record<string, number> = Object.fromEntries(NAME.map((n, i) => [n, i]))

export const HAND_MAX = Math.max(...D.centres.map((c) => c.hand))
export const HAND_TOTAL = D.centres.reduce((a, c) => a + c.hand, 0)
export const TIR_TOTAL = D.centres.reduce((a, c) => a + c.tir, 0)

/** (a,b) -> hat */
export const LANE = new Map(D.lanes.map((l) => [l.a * 100 + l.b, l]))
export const laneOf = (a: number, b: number) => LANE.get(a * 100 + b)

/** Zorunlu kiralık rotaların hat anahtarları. */
export const RENTED_KEYS = new Set(D.rented.map((r) => r.a * 100 + r.b))

/** Ufuk içindeki çıkış tarihleri (plan bacaklarından). */
export const DATES = D.daily.map((d) => d.d)

/** Araç türü sırası — grafiklerde hep aynı sırada. */
export const VT_ORDER = ['Kamyonet', 'Hafif Kamyon', 'Kamyon', 'Tır'] as const

/* ══════════════ süzgeç ══════════════ */
export interface Filter {
  /** '' = tüm ufuk, aksi hâlde "29.06.2026" */
  date: string
  kind: 'all' | 'Kiralık' | 'Spot'
  vt: 'all' | string
  /** yalnız çok duraklı zincirler */
  chainsOnly: boolean
  /** yalnız yol üstü yük alan araçlar */
  pickupOnly: boolean
}

export const FILTER0: Filter = {
  date: '',
  kind: 'all',
  vt: 'all',
  chainsOnly: false,
  pickupOnly: false,
}

export function matchVehicle(v: Vehicle, f: Filter): boolean {
  if (f.date && v.dd !== f.date) return false
  if (f.kind !== 'all' && v.kind !== f.kind) return false
  if (f.vt !== 'all' && v.vt !== f.vt) return false
  if (f.chainsOnly && v.stops < 2) return false
  if (f.pickupOnly && !v.pickup) return false
  return true
}

export interface Slice {
  vehicles: Vehicle[]
  legs: Leg[]
  cost: number
  sla: number
  desi: number
  km: number
  chains: number
  pickups: number
  rent: number
  spot: number
  avgFill: number
  /** merkez indeksine göre çıkış/varış bacak sayısı */
  out: number[]
  in: number[]
}

export function useSlice(f: Filter): Slice {
  return useMemo(() => {
    const vehicles = D.vehicles.filter((v) => matchVehicle(v, f))
    const legs: Leg[] = []
    for (const v of vehicles) for (const i of v.legs) legs.push(D.legs[i])
    const out = new Array(18).fill(0)
    const inn = new Array(18).fill(0)
    let cost = 0
    let sla = 0
    let desi = 0
    let km = 0
    for (const l of legs) {
      cost += l.cost
      sla += l.sla
      desi += l.desi
      km += l.km
      out[l.a]++
      inn[l.b]++
    }
    const spotV = vehicles.filter((v) => v.kind === 'Spot')
    return {
      vehicles,
      legs,
      cost,
      sla,
      desi,
      km,
      chains: vehicles.filter((v) => v.stops > 1).length,
      pickups: vehicles.filter((v) => v.pickup).length,
      rent: vehicles.length - spotV.length,
      spot: spotV.length,
      avgFill: spotV.length ? spotV.reduce((a, v) => a + v.fill, 0) / spotV.length : 0,
      out,
      in: inn,
    }
  }, [f.date, f.kind, f.vt, f.chainsOnly, f.pickupOnly])
}

/* ══════════════ aşama merdiveni ══════════════ */
export const STAGES = ['Stage 0', 'Stage 1', 'Stage 2', 'Stage 3'] as const
export const STAGE_LABEL: Record<string, string> = {
  'Stage 0': 'temel plan',
  'Stage 1': 'aynı-hat onarım',
  'Stage 2': 'milk-run',
  'Stage 3': 'yük alma',
}
export const S = (k: string) => D.stages.stages[k]

/** Bir bacağın SLA durumu. */
export const legLate = (l: Leg) => l.sla > 0

/** Aracın zincir yolu üzerindeki bacakları (zaman sırasında). */
export const vehicleLegs = (v: Vehicle): Leg[] => v.legs.map((i) => D.legs[i])
