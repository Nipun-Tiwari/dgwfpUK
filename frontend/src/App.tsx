import { useEffect, useState } from 'react'
import { apiFetch } from './api/client'
import type { MetaResponse } from './api/types'
import { FilterBar } from './components/FilterBar'
import { ForecastChart } from './components/ForecastChart'
import { IntervalTable } from './components/IntervalTable'
import { MetricCards } from './components/MetricCards'
import { ProvenancePanel } from './components/ProvenancePanel'
import { useMetrics } from './hooks/useMetrics'
import { useTimeseries } from './hooks/useTimeseries'

const DISCLAIMER =
  'This tool evaluates wind forecast accuracy only. It cannot compute procurement volume without demand and non-wind supply data.'

export default function App() {
  const [from, setFrom] = useState('2026-01-01')
  const [to, setTo] = useState('2026-01-07')
  const [meta, setMeta] = useState<MetaResponse | null>(null)

  const metrics = useMetrics(from, to)
  const timeseries = useTimeseries(from, to)

  useEffect(() => {
    apiFetch<MetaResponse>('/api/meta')
      .then(setMeta)
      .catch(() => {})
  }, [])

  return (
    <div
      style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '1200px', margin: '0 auto', padding: '1rem' }}
    >
      <header>
        <h1 style={{ fontSize: '1.5rem', margin: '0 0 0.5rem' }}>
          UK National Wind Forecast Accuracy Dashboard
        </h1>
        <div
          role="note"
          aria-label="Procurement scope disclaimer"
          style={{
            background: '#fef3c7',
            border: '1px solid #fbbf24',
            borderRadius: '6px',
            padding: '0.5rem 1rem',
            marginBottom: '1rem',
            fontSize: '0.875rem',
          }}
        >
          <strong>Scope note:</strong> {DISCLAIMER}
        </div>
      </header>

      <FilterBar from={from} to={to} onFromChange={setFrom} onToChange={setTo} />

      <MetricCards metrics={metrics.data} loading={metrics.loading} error={metrics.error} />

      <ForecastChart
        points={timeseries.data?.points ?? []}
        loading={timeseries.loading}
        error={timeseries.error}
      />

      <IntervalTable
        points={timeseries.data?.points ?? []}
        loading={timeseries.loading}
        error={timeseries.error}
      />

      <ProvenancePanel meta={meta} metrics={metrics.data} />
    </div>
  )
}
