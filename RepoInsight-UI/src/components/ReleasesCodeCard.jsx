import React from 'react'
import { Card, SectionLabel, Row, Divider } from './UI'

export function ReleasesCard({ data }) {
  const { releases } = data

  return (
    <Card>
      <SectionLabel>releases</SectionLabel>

      <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
            {releases.total_fetched}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>total releases</div>
        </div>
        {releases.avg_days_between_releases != null && (
          <div style={{ borderLeft: '1px solid var(--border)', paddingLeft: 20 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, lineHeight: 1 }}>
              {releases.avg_days_between_releases}d
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>avg cadence</div>
          </div>
        )}
      </div>

      {releases.fastest_gap_days != null && (
        <>
          <Row left="Fastest gap" right={`${releases.fastest_gap_days}d`} mono />
          <Row left="Slowest gap" right={`${releases.slowest_gap_days}d`} mono />
          <Divider />
        </>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {releases.last_releases.slice(0, 6).map(r => (
          <div key={r.tag} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--blue)' }}>{r.tag}</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {r.is_prerelease && (
                <span style={{ fontSize: 10, color: 'var(--yellow)' }}>pre</span>
              )}
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {r.published_at.slice(0, 10)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

export function CodeFrequencyCard({ data }) {
  const { code_frequency: cf } = data
  const maxVal = Math.max(...cf.recent_weeks.flatMap(w => [w.additions, w.deletions]), 1)

  function fmtLines(n) {
    if (n >= 1000000) return (n/1000000).toFixed(1)+'M'
    if (n >= 1000) return (n/1000).toFixed(1)+'k'
    return n.toString()
  }

  return (
    <Card>
      <SectionLabel>code frequency</SectionLabel>

      <div style={{ display: 'flex', gap: 20, marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: 'var(--green)' }}>
            +{fmtLines(cf.total_additions)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>total additions</div>
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: 'var(--red)' }}>
            -{fmtLines(cf.total_deletions)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>total deletions</div>
        </div>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 22,
            fontWeight: 700,
            color: cf.net_lines >= 0 ? 'var(--green)' : 'var(--red)',
          }}>
            {cf.net_lines >= 0 ? '+' : ''}{fmtLines(cf.net_lines)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>net</div>
        </div>
      </div>

      <Divider />
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>last 12 weeks</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {cf.recent_weeks.slice(-8).map(w => (
          <div key={w.week_start}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginBottom: 2, fontFamily: 'var(--font-mono)' }}>
              <span>{w.week_start}</span>
              <span style={{ color: 'var(--green)' }}>+{w.additions.toLocaleString()}</span>
              <span style={{ color: 'var(--red)' }}>-{w.deletions.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', gap: 1, height: 4 }}>
              <div style={{ flex: w.additions, background: 'var(--green)', borderRadius: '2px 0 0 2px', opacity: 0.7 }} />
              <div style={{ flex: w.deletions, background: 'var(--red)', borderRadius: '0 2px 2px 0', opacity: 0.7 }} />
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
