import type { MetaResponse, MetricsResponse } from '../api/types'

interface ProvenancePanelProps {
  meta: MetaResponse | null
  metrics: MetricsResponse | null
}

export function ProvenancePanel({ meta, metrics }: ProvenancePanelProps) {
  if (!meta) return null
  return (
    <section
      aria-label="Data provenance"
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        padding: '1rem',
        fontSize: '0.875rem',
        lineHeight: '1.6',
        backgroundColor: '#f9fafb',
        marginTop: '1rem',
      }}
    >
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Data Provenance</h3>
      <dl style={{ margin: 0 }}>
        <dt>
          <strong>Cutoff</strong>
        </dt>
        <dd>
          {meta.cutoff} <em>(provisional)</em>
        </dd>
        <dt>
          <strong>Units</strong>
        </dt>
        <dd>{meta.units}</dd>
        <dt>
          <strong>Timezone</strong>
        </dt>
        <dd>{meta.timezoneNote}</dd>
        <dt>
          <strong>Sources</strong>
        </dt>
        <dd>{meta.sources.join(', ')}</dd>
        <dt>
          <strong>Delivery period</strong>
        </dt>
        <dd>
          {meta.deliveryDateRange.from} — {meta.deliveryDateRange.to}
        </dd>
        <dt>
          <strong>Forecast publish period</strong>
        </dt>
        <dd>
          {meta.forecastPublishRange.from} — {meta.forecastPublishRange.to}
        </dd>
        <dt>
          <strong>Ingested at</strong>
        </dt>
        <dd>{meta.ingestedAt}</dd>
        {metrics && (
          <>
            <dt>
              <strong>Completeness</strong>
            </dt>
            <dd>
              {(metrics.completeness * 100).toFixed(1)}% ({metrics.hoursComplete}/
              {metrics.hoursTotal} hours complete)
            </dd>
            {metrics.hoursIncomplete > 0 && (
              <>
                <dt>
                  <strong>Incomplete hours</strong>
                </dt>
                <dd>
                  {metrics.hoursIncomplete} hours excluded from metrics
                  {metrics.hoursMissingForecast > 0 &&
                    ` (${metrics.hoursMissingForecast} missing forecast`}
                  {metrics.hoursMissingActual > 0 &&
                    `; ${metrics.hoursMissingActual} missing actual`}
                  {metrics.hoursIncomplete > 0 && ')'}
                </dd>
              </>
            )}
          </>
        )}
        <dt>
          <strong>Generation units note</strong>
        </dt>
        <dd style={{ maxWidth: '600px' }}>{meta.generationUnitsNote}</dd>
      </dl>
    </section>
  )
}
