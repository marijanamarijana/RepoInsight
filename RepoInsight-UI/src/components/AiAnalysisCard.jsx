import React from 'react'
import { Card, CardSection } from './UI'

function BulletList({ items, variant }) {
  if (!items?.length) {
    return <p className="ai-prose-sm" style={{ color: 'var(--text-muted)' }}>—</p>
  }
  return (
    <ul className={`ai-list ${variant}`}>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}

export default function AiAnalysisCard({ insight, error, loading, onRun, disabled }) {
  return (
    <Card className="dashboard-span-full">
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
        <div>
          <CardSection title="AI deep analysis" finePrint="README · open issues · metrics narrative" />
          <p className="ai-prose-sm" style={{ maxWidth: 560 }}>
            A written read of repository health, strengths, risks, and what to look at next.
          </p>
        </div>
        <button
          type="button"
          className="ai-run"
          onClick={onRun}
          disabled={disabled || loading}
        >
          {loading ? 'Analyzing with AI…' : 'Run AI analysis'}
        </button>
      </div>

      {error && (
        <div style={{
          background: 'var(--error-bg)',
          border: '1px solid var(--red)',
          borderRadius: 'var(--radius-sm)',
          padding: 14,
          fontSize: 13,
          color: 'var(--red)',
          fontFamily: 'var(--font-mono)',
        }}>
          {error}
        </div>
      )}

      {!insight && !error && !loading && (
        <p className="ai-prose-sm" style={{ color: 'var(--text-secondary)' }}>
          Run deep AI analysis on the current repository
        </p>
      )}

      {insight && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <p className="ai-prose-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {insight.provider} · {insight.model}
          </p>

          <section>
            <CardSection title="health summary" />
            <p className="ai-prose">{insight.health_summary}</p>
          </section>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <section>
              <CardSection title="strengths" />
              <BulletList items={insight.strengths} variant="ai-list-strengths" />
            </section>
            <section>
              <CardSection title="risks" />
              <BulletList items={insight.risks} variant="ai-list-risks" />
            </section>
            <section>
              <CardSection title="recommendations" />
              <BulletList items={insight.recommendations} variant="ai-list-recs" />
            </section>
          </div>

          {(insight.readme_assessment || insight.community_signals) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
              {insight.readme_assessment && (
                <section>
                  <CardSection title="README" />
                  <p className="ai-prose-sm">{insight.readme_assessment}</p>
                </section>
              )}
              {insight.community_signals && (
                <section>
                  <CardSection title="community" />
                  <p className="ai-prose-sm">{insight.community_signals}</p>
                </section>
              )}
            </div>
          )}

          <p className="ai-prose-sm" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
            {insight.disclaimer}
          </p>
        </div>
      )}
    </Card>
  )
}
