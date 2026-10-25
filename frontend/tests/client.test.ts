// TEST FIXTURE — not real data
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockFetch = vi.fn()
;(globalThis as any).fetch = mockFetch

describe('apiFetch', () => {
  beforeEach(() => {
    mockFetch.mockReset()
    vi.resetModules()
  })

  it('returns data on successful fetch', async () => {
    const { apiFetch } = await import('../src/api/client')
    const mockData = { mae: 800, rmse: 900, bias: -100, units: 'MW' }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    })
    const result = await apiFetch('/api/metrics?from=2026-01-01&to=2026-01-01')
    expect(result).toEqual(mockData)
  })

  it('throws on error response', async () => {
    const { apiFetch } = await import('../src/api/client')
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ message: 'Database not loaded.' }),
    })
    await expect(
      apiFetch('/api/metrics?from=2026-01-01&to=2026-01-01'),
    ).rejects.toThrow('Database not loaded.')
  })

  it('handles null fields in timeseries points', async () => {
    const { apiFetch } = await import('../src/api/client')
    const mockData = {
      units: 'MW',
      points: [
        {
          deliveryHour: '2026-01-01T00:00:00Z',
          forecast: null,
          actual: null,
          error: null,
          selectedPublishTime: null,
          complete: false,
        },
      ],
    }
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockData })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result: any = await apiFetch('/api/timeseries?from=2026-01-01&to=2026-01-01')
    expect(result.points[0].forecast).toBeNull()
    expect(result.points[0].actual).toBeNull()
  })
})
