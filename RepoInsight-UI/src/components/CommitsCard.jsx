import React from 'react'
import { Card, SectionLabel, Row, Divider } from './UI'

export default function CommitsCard({ data }) {
  const { recent_commits: rc } = data
  const maxCount = Math.max(...rc.commits_by_hour.map(h => h.count), 1)

  return (
    <Card>
      <SectionLabel>recent commits — {rc.total_sampled} sampled</SectionLabel>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>commit hour (UTC)</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 2 }}>
          {rc.commits_by_hour.map(({ hour, count }) => {
            const intensity = count / maxCount
            const bg = count === 0
              ? 'var(--border)'
              : `rgba(88,166,255,${0.15 + intensity * 0.85})`
            const isActive = hour === rc.peak_hour_utc
            return (
              <div
                key={hour}
                title={`${String(hour).padStart(2,'0')}:00 — ${count} commits`}
                style={{
                  height: 28,
                  borderRadius: 3,
                  background: bg,
                  outline: isActive ? '2px solid var(--blue)' : 'none',
                  position: 'relative',
                  cursor: 'default',
                }}
              />
            )
          })}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 2, marginTop: 3 }}>
          {rc.commits_by_hour.map(({ hour }) => (
            <div key={hour} style={{ textAlign: 'center', fontSize: 9, color: hour % 4 === 0 ? 'var(--text-muted)' : 'transparent' }}>
              {hour}
            </div>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
          peak: <span style={{ color: 'var(--blue)', fontFamily: 'var(--font-mono)' }}>{String(rc.peak_hour_utc).padStart(2,'0')}:00 UTC</span>
        </div>
      </div>

      <Divider />

      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>commit message length</div>
      <Row left="Average" right={`${rc.avg_message_length} chars`} mono />
      <Row left="Min" right={`${rc.min_message_length} chars`} mono />
      <Row left="Max" right={`${rc.max_message_length} chars`} mono />
    </Card>
  )
}
