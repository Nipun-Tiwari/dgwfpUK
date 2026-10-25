# Demo Script — Part 1: Customer Pitch (≤ 5 min)

---

## Setup (before recording)

- Open the dashboard at the deployed Render URL (or localhost:5173 if demoing locally).
- Verify `/health` returns `dataLoaded: true`.
- Set the date filter to a single day — suggested: **2026-01-15** (typically a day with good coverage).
- Have browser DevTools open on the Network tab so you can show the API call (optional).
- Close all other browser tabs.

---

## Script

### [0:00] Hook — the business problem

> "Every wind farm operator, energy trader, and system balancer depends on day-ahead wind forecasts.
> But how accurate are those forecasts really? And at the moment a trading decision is made — not in
> hindsight, but using only what was known at the time — how much should you trust the number?
>
> This dashboard answers that question for January 2026 UK national wind generation."

---

### [0:30] Opening the dashboard

> "Here's the dashboard. The first thing you see is this permanent disclaimer — this is a prototype,
> not an operational tool, and no commercial decisions should be made from it without independent
> verification. That stays visible throughout."

*[Point at the disclaimer banner.]*

---

### [0:45] Selecting a date

> "I'm going to look at 15 January 2026. I select it in the filter — and the dashboard fires a single
> API call to the backend and updates everything in one go."

*[Set the date filter to 2026-01-15. Let the data load.]*

---

### [1:00] Reading the chart

> "This is the forecast vs actual chart. The blue line is the WINDFOR day-ahead forecast — the number
> Elexon published the morning before delivery. The orange line is what actually happened, measured from
> FUELHH half-hourly metered generation data.
>
> You can see [describe what you see — e.g. 'the forecast tracked the trend well but overestimated
> the late-afternoon ramp by about 1,500 MW'].
>
> Hover over any point to see the exact forecast MW, actual MW, and the error in MW."

*[Hover over a few points on the chart to show the tooltip.]*

---

### [1:45] Metric cards

> "The four cards at the top summarise accuracy for the selected period.
>
> MAE — mean absolute error — tells us the average size of a miss, regardless of direction.
> For this day it's [read value] MW.
>
> RMSE is [read value] MW — it penalises large errors more heavily, so if RMSE is much bigger than MAE,
> there were a few very large misses.
>
> Bias is [read value] MW — [positive means the forecast consistently overestimated, negative means
> underestimated]. That matters for balancing cost.
>
> Normalised MAE and RMSE express error as a percentage of mean actual generation — useful when
> comparing across time periods with different wind levels."

---

### [2:45] Completeness and the interval table

> "Completeness — [read value]% of hours — tells me how many delivery hours had both a valid metered
> actual and an eligible forecast at the time of the decision. Hours that are incomplete are shown as
> gaps in the chart, and grey rows in this table — never as zeros, which would distort the statistics.
>
> The table is sortable by absolute error. Let me sort it."

*[Click the 'Absolute Error' column header to sort.]*

> "[Point to the worst hour.] This was the biggest miss: [read the hour and error value]. That's the
> kind of outlier that drives the RMSE above the MAE."

---

### [3:30] Decision-time cutoff and provisional nature

> "Every number on this dashboard is computed using only forecasts that were published by 09:20 UTC the
> morning before delivery — that's the cutoff marked in the Provenance Panel here.
>
> This cutoff is **provisional**. The PRD specifies approximate publication cadences, and what we
> actually see in the Elexon API are publish times of around 02:30, 04:30, 07:30, 09:30 UTC. The logic
> is robust to this — it simply takes the latest vintage at or before the cutoff — but the exact cutoff
> value is a parameter you would refine with a real procurement team."

*[Point to the Provenance Panel.]*

---

### [4:15] Procurement-scope limitation

> "One important limitation: this dashboard covers **national-level** wind generation only. It does not
> break down by region, wind farm, or technology type. That matters for procurement — you can use this
> to assess the aggregate forecast quality, but a site-specific or portfolio-level analysis would need
> additional data sources."

---

### [4:30] Value and close

> "So the value here is simple: you can open this dashboard the morning after any day in January 2026,
> pick the delivery date, and immediately see — with full provenance — how accurate the Elexon day-ahead
> forecast was at the moment it would have been used to make a decision.
>
> That's the foundation for any systematic forecast accuracy programme: quantified, reproducible,
> assumption-transparent."

---

*[End of Part 1 — target: ~5 minutes]*
