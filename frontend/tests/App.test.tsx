// TEST FIXTURE — not real data
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import App from '../src/App'

vi.mock('../src/api/client', () => ({
  apiFetch: vi.fn().mockRejectedValue(new Error('no backend')),
}))

vi.mock('../src/hooks/useMetrics', () => ({
  useMetrics: () => ({ data: null, loading: false, error: null }),
}))

vi.mock('../src/hooks/useTimeseries', () => ({
  useTimeseries: () => ({ data: null, loading: false, error: null }),
}))

describe('App', () => {
  it('renders the disclaimer', () => {
    render(<App />)
    expect(screen.getByRole('note', { name: /disclaimer/i })).toBeInTheDocument()
  })

  it('renders the dashboard heading', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /Wind Forecast Accuracy/i })).toBeInTheDocument()
  })
})
