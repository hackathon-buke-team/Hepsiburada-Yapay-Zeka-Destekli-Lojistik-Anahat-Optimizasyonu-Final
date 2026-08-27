/* panel.json'un birebir şeması — kaynak/build_panel_data.py üretir. */

export interface Meta {
  horizon: [string, string]
  start: string
  ndays: number
  plan_rows: number
  legs: number
  vehicles: number
  rent_vehicles: number
  spot_vehicles: number
  chains: number
  pickups: number
  total_cost: number
  sla_cost: number
  desi: number
  km: number
  avg_fill: number
  avg_fill_leg: number
}

export interface Centre {
  n: string
  lat: number
  lon: number
  hand: number
  tir: number
}

export type VType = 'Tır' | 'Kamyon' | 'Hafif Kamyon' | 'Kamyonet'
export type Kind = 'Kiralık' | 'Spot'

export interface Lane {
  a: number
  b: number
  km: number
  sla: number
  dur: Record<VType, number>
  seen: 0 | 1
}

export interface VTypeSpec {
  n: VType
  cap: number
  rent_h: number
  rent_km: number
  spot_h: number
  spot_km: number
}

export interface RentedRoute {
  a: number
  b: number
  n: number
  t: VType
}

/** Bir bacak = tek araç hareketi (çıkış merkezi -> varış merkezi). */
export interface Leg {
  v: string
  kind: Kind
  vt: VType
  a: number
  b: number
  dd: string
  dt: string
  ad: string
  at: string
  desi: number
  /** bu bacağın çıkışında gerçekten yüklenen desi (aktarma geçişi hariç) */
  load: number
  /** bu bacağın varışında gerçekten indirilen desi */
  drop: number
  parts: number
  sla: number
  cost: number
  trav: number
  /** varışta indirilen yükün elleçleme dakikası (parçaların toplamı) */
  hun: number
  /** çıkışta yüklenen yükün elleçleme dakikası (parçaların toplamı) */
  hld: number
  ids: string[]
  t0: number
  t1: number
  km: number
  cap: number
  fill: number
  vi: number
}

/** Fiziksel araç: bir ya da daha fazla bacağı sırayla koşar. */
export interface Vehicle {
  id: string
  kind: Kind
  vt: VType
  cap: number
  legs: number[]
  desi: number
  cost: number
  sla: number
  km: number
  parts: number
  stops: number
  t0: number
  t1: number
  use: number
  dd: string
  path: number[]
  pickup: 0 | 1
  picked: number
  fill: number
}

export interface DayRow {
  d: string
  iso: string
  dow: number
  legs: number
  vehicles: number
  desi: number
  cost: number
  sla: number
  km: number
  rent: number
  spot: number
}

export interface LaneFlow {
  a: number
  b: number
  legs: number
  desi: number
  cost: number
  sla: number
}

export interface Forecast {
  rows: number
  zero: number
  total: number
  daily: { iso: string; d: string; dow: number; desi: number }[]
  slot: Record<string, number>
  lane: { a: number; b: number; desi: number }[]
}

export interface History {
  start: string
  dow0: number
  median: number
  days: number[]
  flag: number[]
  dowmed: Record<string, number>
  excluded: { iso: string; d: string; v: number; r: number; me: 0 | 1; h: string }[]
}

export interface StageRow {
  total_cost: number
  vehicle_cost: number
  sla_penalty: number
  routes: number
  avg_fill: number
  spot_n: number
  plan_rows: number
  fill_cdf: number[]
  chain_size_counts: Record<string, number>
  vehicle_mix: Record<string, number>
  [k: string]: unknown
}

export interface DeckData {
  meta: { max_chain_stops: number }
  cleaning: {
    raw_rows: number
    history_days: number
    od_in_history: number
    od_in_lane_matrix: number
    transfer_centres: number
    history_grid_rows: number
    excluded_dates: number
    training_grid_rows: number
    excluded_grid_rows: number
  }
  calendar: {
    day_before_month_end: number
    month_end: number
    first_day_after_month_end: number
    normal: number
  }
  forecast_vs_dow: {
    labels: string[]
    forecast: number[]
    dow_mean: number[]
    total_forecast: number
    rows: number
    zero_rows: number
  }
  backtest: Record<string, { naive: number; dow_median: number; ours: number }>
  stages: Record<string, StageRow>
  milkrun: {
    groups_considered: number
    pairs_evaluated: number
    triples_evaluated: number
    chains_accepted: number
    chain_size_mix: Record<string, number>
    source_vehicles_replaced: number
    parts_consolidated: number
    desi_consolidated: number
    chain_type_mix: Record<string, number>
    local_saving_tl: number
  }
  pickup: {
    routes_considered: number
    rented_routes_skipped: number
    donors_available: number
    pairs_examined: number
    profitable_candidates: number
    pickups_accepted: number
    rejected_by_ledger: number
    donor_vehicles_removed: number
    parts_picked_up: number
    desi_picked_up: number
    pickup_type_mix: Record<string, number>
    local_saving_tl: number
  }
  repair: { donors_considered: number; moves_accepted: number; vehicles_removed: number }
}

export interface PanelData {
  meta: Meta
  centres: Centre[]
  lanes: Lane[]
  vtypes: VTypeSpec[]
  rented: RentedRoute[]
  legs: Leg[]
  vehicles: Vehicle[]
  daily: DayRow[]
  /** hakem defteri: merkez-gün başına gerçekten elleçlenen desi */
  loadgrid: number[][]
  /** kötümser üst sınır: bacağın tüm desisi iki uca da yazılır */
  loadgrid_ust: number[][]
  tirgrid: number[][]
  laneflow: LaneFlow[]
  forecast: Forecast
  history: History
  stages: DeckData
}
