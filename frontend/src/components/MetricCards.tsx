import type { MetricsResponse } from '../api/types'

interface MetricCardsProps {
  metrics: MetricsResponse | null
  loading: boolean
  error: string | null
}

function fmt(v: number | null, decimals = 1): string {
  return v == null ? 'N/A' : v.toFixed(decimals)
}

function MetricCard({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div
      role="group"
      aria-label={label}
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '1rem',
        minWidth: '120px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{value}</div>
      {unit && <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{unit}</div>}
    </div>
  )
}

export function MetricCards({ metrics, loading, error }: MetricCardsProps) {
  if (loading) return <div role="status" aria-live="polite">Loading metrics...</div>
  if (error) return <div role="alert" style={{ color: 'red' }}>Metrics error: {error}</div>
  if (!metrics) return <div role="status">No metrics available.</div>

  return (
    <section
      aria-label="Accuracy metrics"
      style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', padding: '1rem 0' }}
    >
      <MetricCard label="MAE" value={fmt(metrics.mae, 0)} unit="MW" />
      <MetricCard label="RMSE" value={fmt(metrics.rmse, 0)} unit="MW" />
      <MetricCard label="Bias" value={fmt(metrics.bias, 0)} unit="MW" />
      <MetricCard label="nMAE" value={metrics.nmae == null ? 'N/A' : `${metrics.nmae.toFixed(1)}%`} />
      <MetricCard
        label="nRMSE"
        value={metrics.nrmse == null ? 'N/A' : `${metrics.nrmse.toFixed(1)}%`}
      />
      <MetricCard
        label="Completeness"
        value={`${(metrics.completeness * 100).toFixed(1)}%`}
        unit={`${metrics.hoursComplete}/${metrics.hoursTotal} hours`}
      />
    </section>
  )
}
