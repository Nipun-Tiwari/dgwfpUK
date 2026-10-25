export interface HealthResponse {
  status: string
  dataLoaded: boolean
}

export interface MetaResponse {
  ingestedAt: string
  cutoff: string
  units: string
  timezoneNote: string
  sources: string[]
  deliveryDateRange: { from: string; to: string }
  forecastPublishRange: { from: string; to: string }
  generationUnitsNote: string
}

export interface MetricsResponse {
  mae: number | null
  rmse: number | null
  bias: number | null
  nmae: number | null
  nrmse: number | null
  normalizedOmitted: boolean
  completeness: number
  hoursTotal: number
  hoursComplete: number
  hoursIncomplete: number
  hoursMissingForecast: number
  hoursMissingActual: number
  units: string
}

export interface TimeseriesPoint {
  deliveryHour: string
  forecast: number | null
  actual: number | null
  error: number | null
  selectedPublishTime: string | null
  complete: boolean
}

export interface TimeseriesResponse {
  units: string
  points: TimeseriesPoint[]
}

export interface ApiError {
  error: string
  message: string
}

export interface RequestState<T> {
  data: T | null
  loading: boolean
  error: string | null
}
