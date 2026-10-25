import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import type { TimeseriesPoint } from '../src/api/types'
import { IntervalTable } from '../src/components/IntervalTable'

function createMockPoints(count: number): TimeseriesPoint[] {
  return Array.from({ length: count }, (_, i) => {
    const hourNum = String(i % 24).padStart(2, '0')
    const dayNum = String(Math.floor(i / 24) + 1).padStart(2, '0')
    const forecast = 1000 + i * 10
    const actual = 1000 + i * 5
    return {
      deliveryHour: `2026-01-${dayNum}T${hourNum}:00:00Z`,
      forecast,
      actual,
      error: forecast - actual,
      selectedPublishTime: `2026-01-${dayNum}T07:30:00Z`,
      complete: true,
    }
  })
}

describe('IntervalTable with Pagination', () => {
  it('renders loading state', () => {
    render(<IntervalTable points={[]} loading={true} error={null} />)
    expect(screen.getByRole('status')).toHaveTextContent(/loading table/i)
  })

  it('renders error state', () => {
    render(<IntervalTable points={[]} loading={false} error="Failed to fetch" />)
    expect(screen.getByRole('alert')).toHaveTextContent(/Table error: Failed to fetch/i)
  })

  it('renders empty state when points array is empty', () => {
    render(<IntervalTable points={[]} loading={false} error={null} />)
    expect(screen.getByRole('status')).toHaveTextContent(/no interval data/i)
  })

  it('defaults to 20 rows per page', () => {
    const points = createMockPoints(70)
    render(<IntervalTable points={points} loading={false} error={null} />)

    // Table body rows should be 20
    const rows = screen.getAllByRole('row')
    // 1 header row + 20 data rows = 21
    expect(rows).toHaveLength(21)

    // Check summary text
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 1–20 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 4')

    // Page size select has value 20
    const select = screen.getByLabelText(/rows per page/i) as HTMLSelectElement
    expect(select.value).toBe('20')

    // Previous and First buttons disabled on page 1
    expect(screen.getByLabelText(/previous page/i)).toBeDisabled()
    expect(screen.getByLabelText(/first page/i)).toBeDisabled()
    expect(screen.getByLabelText(/next page/i)).toBeEnabled()
    expect(screen.getByLabelText(/last page/i)).toBeEnabled()
  })

  it('navigates through pages with Next, Previous, Last, and First buttons', async () => {
    const user = userEvent.setup()
    const points = createMockPoints(70)
    render(<IntervalTable points={points} loading={false} error={null} />)

    // Click Next
    await user.click(screen.getByLabelText(/next page/i))
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 21–40 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 2 of 4')
    expect(screen.getByLabelText(/previous page/i)).toBeEnabled()
    expect(screen.getByLabelText(/first page/i)).toBeEnabled()

    // Click Last
    await user.click(screen.getByLabelText(/last page/i))
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 61–70 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 4 of 4')
    expect(screen.getByLabelText(/next page/i)).toBeDisabled()
    expect(screen.getByLabelText(/last page/i)).toBeDisabled()

    // Click Previous
    await user.click(screen.getByLabelText(/previous page/i))
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 41–60 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 3 of 4')

    // Click First
    await user.click(screen.getByLabelText(/first page/i))
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 1–20 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 4')
  })

  it('changes page size to 50 and 100', async () => {
    const user = userEvent.setup()
    const points = createMockPoints(70)
    render(<IntervalTable points={points} loading={false} error={null} />)

    const select = screen.getByLabelText(/rows per page/i)

    // Switch to 50
    await user.selectOptions(select, '50')
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 1–50 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 2')
    // 1 header + 50 rows = 51
    expect(screen.getAllByRole('row')).toHaveLength(51)

    // Switch to 100
    await user.selectOptions(select, '100')
    expect(screen.getByText(/showing/i)).toHaveTextContent('Showing 1–70 of 70 records')
    expect(screen.getByTestId('page-indicator')).toHaveTextContent('Page 1 of 1')
    expect(screen.getAllByRole('row')).toHaveLength(71)
    expect(screen.getByLabelText(/next page/i)).toBeDisabled()
    expect(screen.getByLabelText(/previous page/i)).toBeDisabled()
  })

  it('sorts records globally across all pages before paginating', async () => {
    const user = userEvent.setup()
    const points = createMockPoints(70)
    render(<IntervalTable points={points} loading={false} error={null} />)

    // Click "|Error| (MW)" to sort ascending
    const absErrorHeader = screen.getByText(/\|error\| \(mw\)/i)
    await user.click(absErrorHeader)

    // In createMockPoints, error increases with i: i=0 error=0, i=69 error=345
    // Ascending should have row 1 error = 0
    let rows = screen.getAllByRole('row')
    expect(rows[1]).toHaveTextContent('2026-01-01 00:00')

    // Click again to sort descending
    await user.click(absErrorHeader)
    rows = screen.getAllByRole('row')
    // Descending should place the highest error (i=69) on Page 1
    // i=69 -> day 3, hour 21
    expect(rows[1]).toHaveTextContent('2026-01-03 21:00')
    // It should still only display 20 rows on Page 1
    expect(rows).toHaveLength(21)
  })
})
