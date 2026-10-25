import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TimeseriesPoint } from '../api/types'

interface ForecastChartProps {
  points: TimeseriesPoint[]
  loading: boolean
  error: string | null
}

function formatHour(iso: string) {
  return iso.slice(11, 16)
}

export function ForecastChart({ points, loading, error }: ForecastChartProps) {
  if (loading) return <div role="status" aria-live="polite">Loading chart...</div>
  if (error) return <div role="alert" style={{ color: 'red' }}>Chart error: {error}</div>
  if (!points.length) return <div role="status">No data for selected range.</div>

  const data = points.map((p) => ({
    hour: formatHour(p.deliveryHour),
    forecast: p.complete ? p.forecast : null,
    actual: p.complete ? p.actual : null,
  }))

  return (
    <section aria-label="Forecast vs Actual chart">
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={data} margin={{ top: 8, right: 24, left: 16, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="hour"
            label={{ value: 'Hour (UTC)', position: 'insideBottom', offset: -4 }}
          />
          <YAxis label={{ value: 'MW', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            formatter={(value: any, name: any) =>
              value == null ? ['—', String(name)] : [`${Number(value).toFixed(0)} MW`, String(name)]
            }
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#2563eb"
            dot={false}
            connectNulls={false}
            name="Forecast"
          />
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#16a34a"
            dot={false}
            connectNulls={false}
            name="Actual"
          />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
