import React from 'react'
import { Card, SectionLabel } from './UI'

function scoreHealth(summary) {
  let score = 0
  if (summary.bus_factor >= 3) score += 20
  else if (summary.bus_factor === 2) score += 10
  if (summary.days_since_last_push < 7) score += 20
  else if (summary.days_since_last_push < 30) score += 10
  else if (summary.days_since_last_push < 90) score += 5
  if (summary.pr_merge_rate_pct > 70) score += 20
  else if (summary.pr_merge_rate_pct > 40) score += 10
  if (summary.gini_coefficient < 0.5) score += 20
  else if (summary.gini_coefficient < 0.7) score += 10
  if (summary.total_releases > 5) score += 20
  else if (summary.total_releases > 0) score += 10
  return Math.min(100, score)
}

function scoreColor(s) {
  if (s >= 70) return 'var(--green)'
  if (s >= 40) return 'var(--yellow)'
  return 'var(--red)'
}

function scoreLabel(s) {
  if (s >= 70) return 'Healthy'
  if (s >= 40) return 'Moderate'
  return 'Needs attention'
}

export default function SummaryCard({ data }) {
  const { summary } = data
  const score = scoreHealth(summary)
  const color = scoreColor(score)

  const metrics = [
    {
      label: 'Bus factor',
      value: summary.bus_factor,
      status: summary.bus_factor >= 3 ? 'green' : summary.bus_factor === 2 ? 'yellow' : 'red',
      note: summary.bus_factor >= 3 ? 'good' : summary.bus_factor === 2 ? 'watch' : 'risk',
    },
    {
      label: 'Gini coeff.',
      value: summary.gini_coefficient.toFixed(2),
      status: summary.gini_coefficient < 0.5 ? 'green' : summary.gini_coefficient < 0.7 ? 'yellow' : 'red',
      note: summary.gini_coefficient < 0.5 ? 'distributed' : 'concentrated',
    },
    {
      label: 'PR merge rate',
      value: `${summary.pr_merge_rate_pct.toFixed(0)}%`,
      status: summary.pr_merge_rate_pct > 70 ? 'green' : summary.pr_merge_rate_pct > 40 ? 'yellow' : 'red',
      note: summary.pr_merge_rate_pct > 70 ? 'healthy' : 'low',
    },
    {
      label: 'Days since push',
      value: `${summary.days_since_last_push}d`,
      status: summary.days_since_last_push < 30 ? 'green' : summary.days_since_last_push < 90 ? 'yellow' : 'red',
      note: summary.days_since_last_push < 30 ? 'active' : 'stale',
    },
    {
      label: 'Avg PR merge',
      value: summary.avg_pr_merge_days != null ? `${summary.avg_pr_merge_days}d` : '—',
      status: null,
      note: '',
    },
    {
      label: 'Avg issue close',
      value: summary.avg_issue_close_days != null ? `${summary.avg_issue_close_days}d` : '—',
      status: null,
      note: '',
    },
  ]

  const statusColor = { green: 'var(--green)', yellow: 'var(--yellow)', red: 'var(--red)' }

  return (
    <Card style={{ gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'flex-start' }}>

        <div style={{ textAlign: 'center', minWidth: 120 }}>
          <SectionLabel>health score</SectionLabel>
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border)" strokeWidth="8" />
            <circle
              cx="50" cy="50" r="42"
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 42}`}
              strokeDashoffset={`${2 * Math.PI * 42 * (1 - score / 100)}`}
              transform="rotate(-90 50 50)"
              style={{ filter: `drop-shadow(0 0 6px ${color})`, transition: 'stroke-dashoffset 1s ease' }}
            />
            <text x="50" y="46" textAnchor="middle" fill={color} fontSize="22" fontWeight="700" fontFamily="JetBrains Mono">{score}</text>
            <text x="50" y="62" textAnchor="middle" fill="var(--text-muted)" fontSize="10" fontFamily="Inter">{scoreLabel(score)}</text>
          </svg>
        </div>

        <div style={{ flex: 1, minWidth: 280 }}>
          <SectionLabel>key metrics</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
            {metrics.map(m => (
              <div key={m.label} style={{
                background: 'var(--bg-base)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 12px',
              }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{m.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: m.status ? statusColor[m.status] : 'var(--text-primary)' }}>
                  {m.value}
                </div>
                {m.note && <div style={{ fontSize: 11, color: m.status ? statusColor[m.status] : 'var(--text-muted)', marginTop: 2 }}>{m.note}</div>}
              </div>
            ))}
          </div>
        </div>

        <div>
          <SectionLabel>top contributors</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {summary.top_contributors.map((login, i) => (
              <a
                key={login}
                href={`https://github.com/${login}`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 13, color: 'var(--blue)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', width: 16 }}>{i + 1}.</span>
                {login}
              </a>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}
