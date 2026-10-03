import React from 'react'
import { Card, CardSection } from './UI'

function BulletList({ items, color = 'var(--text-secondary)' }) {
  if (!items?.length) {
    return <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>—</p>
  }
  return (
    <ul style={{ margin: 0, paddingLeft: 18, color, fontSize: 13, lineHeight: 1.55 }}>
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: 6 }}>{item}</li>
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
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, maxWidth: 560 }}>
            AI deep analysis and insight
          </p>
        </div>
        <button
          type="button"
          onClick={onRun}
          disabled={disabled || loading}
          style={{
            background: loading ? 'var(--border)' : 'var(--blue)',
            color: loading ? 'var(--text-muted)' : '#fff',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 18px',
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
            fontWeight: 600,
            cursor: disabled || loading ? 'not-allowed' : 'pointer',
            opacity: disabled ? 0.5 : 1,
          }}
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

      {insight && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', margin: 0 }}>
            {insight.provider} · {insight.model}
          </p>

          <section>
            <CardSection title="health summary" />
            <p style={{ fontSize: 15, lineHeight: 1.6, color: 'var(--text-primary)', margin: 0 }}>
              {insight.health_summary}
            </p>
          </section>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <section>
              <CardSection title="strengths" />
              <BulletList items={insight.strengths} color="var(--green)" />
            </section>
            <section>
              <CardSection title="risks" />
              <BulletList items={insight.risks} color="var(--yellow)" />
            </section>
            <section>
              <CardSection title="recommendations" />
              <BulletList items={insight.recommendations} />
            </section>
          </div>

          {(insight.readme_assessment || insight.community_signals) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
              {insight.readme_assessment && (
                <section>
                  <CardSection title="README" />
                  <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--text-secondary)', margin: 0 }}>
                    {insight.readme_assessment}
                  </p>
                </section>
              )}
              {insight.community_signals && (
                <section>
                  <CardSection title="community" />
                  <p style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--text-secondary)', margin: 0 }}>
                    {insight.community_signals}
                  </p>
                </section>
              )}
            </div>
          )}

          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, fontStyle: 'italic' }}>
            {insight.disclaimer}
          </p>
        </div>
      )}
    </Card>
  )
}
