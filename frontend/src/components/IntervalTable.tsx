import { useState } from 'react'
import type { TimeseriesPoint } from '../api/types'

interface IntervalTableProps {
  points: TimeseriesPoint[]
  loading: boolean
  error: string | null
}

type SortKey = 'hour' | 'forecast' | 'actual' | 'error' | 'absError'

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const

export function IntervalTable({ points, loading, error }: IntervalTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('hour')
  const [sortAsc, setSortAsc] = useState(true)
  const [pageSize, setPageSize] = useState<number>(20)
  const [currentPage, setCurrentPage] = useState<number>(1)

  if (loading) return <div role="status" aria-live="polite">Loading table...</div>
  if (error) return <div role="alert" style={{ color: 'red' }}>Table error: {error}</div>
  if (!points.length) return <div role="status">No interval data.</div>

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((a) => !a)
    else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const sorted = [...points].sort((a, b) => {
    let av: number | null = null,
      bv: number | null = null
    if (sortKey === 'hour') {
      av = new Date(a.deliveryHour).getTime()
      bv = new Date(b.deliveryHour).getTime()
    } else if (sortKey === 'forecast') {
      av = a.forecast
      bv = b.forecast
    } else if (sortKey === 'actual') {
      av = a.actual
      bv = b.actual
    } else if (sortKey === 'error') {
      av = a.error
      bv = b.error
    } else if (sortKey === 'absError') {
      av = a.error == null ? null : Math.abs(a.error)
      bv = b.error == null ? null : Math.abs(b.error)
    }
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    return sortAsc ? av - bv : bv - av
  })

  // Pagination calculations
  const totalRecords = sorted.length
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize))
  const effectivePage = Math.min(Math.max(1, currentPage), totalPages)
  const startIndex = (effectivePage - 1) * pageSize
  const endIndex = Math.min(startIndex + pageSize, totalRecords)
  const paginatedRows = sorted.slice(startIndex, endIndex)

  function th(label: string, key: SortKey) {
    return (
      <th
        onClick={() => handleSort(key)}
        style={{ cursor: 'pointer', padding: '0.5rem', textAlign: 'right', userSelect: 'none' }}
        aria-sort={sortKey === key ? (sortAsc ? 'ascending' : 'descending') : 'none'}
      >
        {label} {sortKey === key ? (sortAsc ? '▲' : '▼') : ''}
      </th>
    )
  }

  const navBtnStyle = (disabled: boolean) => ({
    padding: '0.25rem 0.6rem',
    borderRadius: '4px',
    border: '1px solid #d1d5db',
    background: disabled ? '#f3f4f6' : '#fff',
    color: disabled ? '#9ca3af' : '#1f2937',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: '0.875rem',
    fontWeight: 500,
  })

  return (
    <section aria-label="Interval table" style={{ marginTop: '1.5rem', marginBottom: '1.5rem' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
          marginBottom: '0.5rem',
          fontSize: '0.875rem',
          color: '#4b5563',
        }}
      >
        <div>
          Showing <strong>{totalRecords === 0 ? 0 : startIndex + 1}</strong>–
          <strong>{endIndex}</strong> of <strong>{totalRecords}</strong> records
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label htmlFor="interval-page-size" style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <span>Rows per page:</span>
            <select
              id="interval-page-size"
              aria-label="Rows per page"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setCurrentPage(1)
              }}
              style={{
                padding: '0.25rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: '#fff',
                fontSize: '0.875rem',
                cursor: 'pointer',
              }}
            >
              {PAGE_SIZE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div style={{ overflowX: 'auto', border: '1px solid #e5e7eb', borderRadius: '6px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>
              {th('Hour (UTC)', 'hour')}
              {th('Forecast (MW)', 'forecast')}
              {th('Actual (MW)', 'actual')}
              {th('Error (MW)', 'error')}
              {th('|Error| (MW)', 'absError')}
            </tr>
          </thead>
          <tbody>
            {paginatedRows.map((p) => (
              <tr
                key={p.deliveryHour}
                style={{
                  borderBottom: '1px solid #f3f4f6',
                  backgroundColor: p.complete ? undefined : '#f9fafb',
                  color: p.complete ? undefined : '#9ca3af',
                }}
                aria-label={p.complete ? undefined : 'incomplete hour'}
              >
                <td style={{ padding: '0.375rem 0.5rem' }}>
                  {p.deliveryHour.slice(0, 16).replace('T', ' ')}
                </td>
                <td style={{ textAlign: 'right', padding: '0.375rem 0.5rem' }}>
                  {p.forecast == null ? '—' : p.forecast.toFixed(0)}
                </td>
                <td style={{ textAlign: 'right', padding: '0.375rem 0.5rem' }}>
                  {p.actual == null ? '—' : p.actual.toFixed(0)}
                </td>
                <td style={{ textAlign: 'right', padding: '0.375rem 0.5rem' }}>
                  {p.error == null ? '—' : p.error.toFixed(0)}
                </td>
                <td style={{ textAlign: 'right', padding: '0.375rem 0.5rem' }}>
                  {p.error == null ? '—' : Math.abs(p.error).toFixed(0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
          marginTop: '0.5rem',
          fontSize: '0.875rem',
        }}
      >
        <div data-testid="page-indicator" style={{ color: '#6b7280' }}>
          Page <strong>{effectivePage}</strong> of <strong>{totalPages}</strong>
        </div>

        <nav aria-label="Pagination Navigation" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <button
            type="button"
            onClick={() => setCurrentPage(1)}
            disabled={effectivePage <= 1}
            aria-label="First page"
            style={navBtnStyle(effectivePage <= 1)}
          >
            «
          </button>
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={effectivePage <= 1}
            aria-label="Previous page"
            style={navBtnStyle(effectivePage <= 1)}
          >
            ‹
          </button>
          <button
            type="button"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={effectivePage >= totalPages}
            aria-label="Next page"
            style={navBtnStyle(effectivePage >= totalPages)}
          >
            ›
          </button>
          <button
            type="button"
            onClick={() => setCurrentPage(totalPages)}
            disabled={effectivePage >= totalPages}
            aria-label="Last page"
            style={navBtnStyle(effectivePage >= totalPages)}
          >
            »
          </button>
        </nav>
      </div>
    </section>
  )
}
