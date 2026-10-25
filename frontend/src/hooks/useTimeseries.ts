import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import type { RequestState, TimeseriesResponse } from '../api/types'

export function useTimeseries(from: string, to: string): RequestState<TimeseriesResponse> {
  const [state, setState] = useState<RequestState<TimeseriesResponse>>({
    data: null,
    loading: false,
    error: null,
  })

  useEffect(() => {
    if (!from || !to) return
    const controller = new AbortController()
    setState({ data: null, loading: true, error: null })

    apiFetch<TimeseriesResponse>(`/api/timeseries?from=${from}&to=${to}`, controller.signal)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => {
        if (err.name === 'AbortError') return
        setState({ data: null, loading: false, error: err.message })
      })

    return () => controller.abort()
  }, [from, to])

  return state
}
