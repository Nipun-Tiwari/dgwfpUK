import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import type { MetricsResponse, RequestState } from '../api/types'

export function useMetrics(from: string, to: string): RequestState<MetricsResponse> {
  const [state, setState] = useState<RequestState<MetricsResponse>>({
    data: null,
    loading: false,
    error: null,
  })

  useEffect(() => {
    if (!from || !to) return
    const controller = new AbortController()
    setState({ data: null, loading: true, error: null })

    apiFetch<MetricsResponse>(`/api/metrics?from=${from}&to=${to}`, controller.signal)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((err) => {
        if (err.name === 'AbortError') return
        setState({ data: null, loading: false, error: err.message })
      })

    return () => controller.abort()
  }, [from, to])

  return state
}
