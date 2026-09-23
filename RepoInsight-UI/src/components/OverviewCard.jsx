import React from 'react'
import { Card, Badge, SampleFinePrint } from './UI'
import { REPOSITORY_TOPICS } from '../constants/sampling'

function fmt(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toString()
}

export default function OverviewCard({ data, className = '' }) {
  const { overview } = data
  const idleColor = overview.days_since_last_push > 180
    ? 'var(--red)' : overview.days_since_last_push > 30
    ? 'var(--yellow)' : 'var(--green)'

  return (
    <Card className={className}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <svg width="18" height="18" viewBox="0 0 16 16" fill="var(--text-secondary)">
              <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h7A2.5 2.5 0 0 1 14 2.5v10.042a.5.5 0 0 1-.765.424L8 9.754l-5.235 3.212A.5.5 0 0 1 2 12.542V2.5z"/>
            </svg>
            <a
              href={`https://github.com/${overview.full_name}`}
              target="_blank"
              rel="noreferrer"
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 18,
                fontWeight: 700,
                color: 'var(--blue)',
                textDecoration: 'none',
              }}
            >
              {overview.full_name}
            </a>
            {overview.is_archived && <Badge color="var(--yellow)">archived</Badge>}
            {overview.is_fork && <Badge color="var(--purple)">fork</Badge>}
          </div>

          {overview.description && (
            <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 10, maxWidth: 520 }}>
              {overview.description}
            </p>
          )}

          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {overview.primary_language && <Badge color="var(--blue)">{overview.primary_language}</Badge>}
            {overview.license && <Badge color="var(--text-secondary)">{overview.license}</Badge>}
            {overview.topics.slice(0, 5).map(t => (
              <Badge key={t} color="var(--purple)">{t}</Badge>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
          <StatPill icon="★" value={fmt(overview.stars)} label="stars" />
          <StatPill icon="⑂" value={fmt(overview.forks)} label="forks" />
          <StatPill icon="!" value={fmt(overview.open_issues)} label="open issues" />
          <StatPill icon="◷" value={`${overview.days_since_last_push}d`} label="since last push" color={idleColor} />
        </div>
      </div>

      <div style={{ marginTop: 14, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        created {overview.created_at.slice(0, 10)} · last push {overview.last_pushed_at.slice(0, 10)}
        <span style={{ margin: '0 6px', opacity: 0.5 }}>·</span>
        <SampleFinePrint>up to {REPOSITORY_TOPICS} repository topics</SampleFinePrint>
      </div>
    </Card>
  )
}

function StatPill({ icon, value, label, color = 'var(--text-primary)' }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
        {icon} {label}
      </div>
    </div>
  )
}
