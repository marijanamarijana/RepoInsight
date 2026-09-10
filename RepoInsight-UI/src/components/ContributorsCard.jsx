import React from 'react'
import { Card, SectionLabel, Divider, MiniBar } from './UI'

function busFactorColor(n) {
  if (n === 1) return 'var(--red)'
  if (n <= 3) return 'var(--yellow)'
  return 'var(--green)'
}

export default function ContributorsCard({ data }) {
  const { contributors } = data
  const maxContrib = contributors.top_contributors[0]?.contributions ?? 1

  return (
    <Card>
      <SectionLabel>contributors</SectionLabel>

      <div style={{ display: 'flex', gap: 20, marginBottom: 16 }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 36,
            fontWeight: 700,
            color: busFactorColor(contributors.bus_factor),
            lineHeight: 1,
          }}>
            {contributors.bus_factor}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>bus factor</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
            {contributors.bus_factor === 1 ? '⚠ single point of failure' :
             contributors.bus_factor <= 3 ? 'moderate risk' : 'healthy spread'}
          </div>
        </div>
        <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 20 }}>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 36,
            fontWeight: 700,
            color: 'var(--text-primary)',
            lineHeight: 1,
          }}>
            {contributors.gini_coefficient.toFixed(2)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>gini coeff.</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
            {contributors.gini_coefficient < 0.4 ? 'well distributed' :
             contributors.gini_coefficient < 0.7 ? 'moderate concentration' : 'highly concentrated'}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
        {Object.entries(contributors.ownership).map(([pct, n]) => (
          <div key={pct} style={{
            background: 'var(--bg-base)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px 10px',
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
          }}>
            {pct} → <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{n}</span> people
          </div>
        ))}
      </div>

      <Divider />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {contributors.top_contributors.slice(0, 8).map((c, i) => (
          <div key={c.login}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <img
                src={c.avatar_url}
                alt={c.login}
                style={{ width: 20, height: 20, borderRadius: '50%', flexShrink: 0 }}
              />
              <a
                href={`https://github.com/${c.login}`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 13, color: 'var(--text-primary)', textDecoration: 'none', flex: 1 }}
              >
                {c.login}
              </a>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-secondary)' }}>
                {c.contributions.toLocaleString()} · {c.percentage.toFixed(1)}%
              </span>
            </div>
            <MiniBar value={c.contributions} max={maxContrib} color={i === 0 ? 'var(--blue)' : 'var(--border-focus)'} />
          </div>
        ))}
      </div>
    </Card>
  )
}
