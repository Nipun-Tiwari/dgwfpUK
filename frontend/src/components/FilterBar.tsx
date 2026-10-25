interface FilterBarProps {
  from: string
  to: string
  onFromChange: (v: string) => void
  onToChange: (v: string) => void
}

export function FilterBar({ from, to, onFromChange, onToChange }: FilterBarProps) {
  return (
    <div
      role="search"
      aria-label="Date range filter"
      style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '1rem' }}
    >
      <label htmlFor="date-from">From</label>
      <input
        id="date-from"
        type="date"
        min="2026-01-01"
        max="2026-01-31"
        value={from}
        onChange={(e) => onFromChange(e.target.value)}
        aria-label="From date"
      />
      <label htmlFor="date-to">To</label>
      <input
        id="date-to"
        type="date"
        min="2026-01-01"
        max="2026-01-31"
        value={to}
        onChange={(e) => onToChange(e.target.value)}
        aria-label="To date"
      />
    </div>
  )
}
