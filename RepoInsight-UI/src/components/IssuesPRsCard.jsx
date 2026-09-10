import React from 'react'
import { Card, SectionLabel, Divider, Row } from './UI'

export function IssuesCard({ data }) {
  const { issues } = data
  const total = issues.open_count + issues.closed_sampled
  const closedPct = total ? Math.round(issues.closed_sampled / total * 100) : 0

  return (
    <Card>
      <SectionLabel>issues</SectionLabel>

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 6 }}>
          <span style={{ color: 'var(--green)' }}>● {issues.closed_sampled} closed</span>
          <span style={{ color: 'var(--red)' }}>● {issues.open_count} open</span>
        </div>
        <div style={{ height: 8, background: 'var(--red)', borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${closedPct}%`, background: 'var(--green)', borderRadius: 4 }} />
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, textAlign: 'center', fontFamily: 'var(--font-mono)' }}>
          {closedPct}% resolution rate (sampled)
        </div>
      </div>

      <Divider />

      <Row left="Avg close time" right={issues.avg_close_time_days != null ? `${issues.avg_close_time_days}d` : '—'} mono />
      <Row left="Median close time" right={issues.median_close_time_days != null ? `${issues.median_close_time_days}d` : '—'} mono />
      <Row left={`Stale (>${issues.stale_threshold_days}d)`} right={
        <span style={{ color: issues.stale_issues_count > 10 ? 'var(--yellow)' : 'var(--text-primary)' }}>
          {issues.stale_issues_count}
        </span>
      } />

      {issues.top_labels.length > 0 && (
        <>
          <Divider />
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>top labels</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            {issues.top_labels.slice(0, 6).map(l => (
              <div key={l.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '70%' }}>{l.name}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{l.count}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}

export function PullRequestsCard({ data }) {
  const { pull_requests: pr } = data

  const mergeColor = pr.merge_rate_pct > 70 ? 'var(--green)'
    : pr.merge_rate_pct > 40 ? 'var(--yellow)'
    : 'var(--red)'

  return (
    <Card>
      <SectionLabel>pull requests</SectionLabel>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 16 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 40, fontWeight: 700, color: mergeColor, lineHeight: 1 }}>
          {pr.merge_rate_pct.toFixed(0)}%
        </span>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>merge rate</span>
      </div>

      <div style={{ height: 8, background: 'var(--red)', borderRadius: 4, overflow: 'hidden', marginBottom: 8 }}>
        <div style={{ height: '100%', width: `${pr.merge_rate_pct}%`, background: 'var(--green)', borderRadius: 4 }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
        <span>● {pr.merged_count} merged</span>
        <span>● {pr.rejected_count} closed without merge</span>
      </div>

      <Divider />

      <Row left="Open PRs" right={pr.open_count} mono />
      <Row left="Avg time to merge" right={pr.avg_time_to_merge_days != null ? `${pr.avg_time_to_merge_days}d` : '—'} mono />
      <Row left="Median time to merge" right={pr.median_time_to_merge_days != null ? `${pr.median_time_to_merge_days}d` : '—'} mono />
      <Row left="Avg first response" right={pr.avg_first_response_hours != null ? `${pr.avg_first_response_hours.toFixed(1)}h` : '—'} mono />
    </Card>
  )
}
