import React, { useRef, useEffect } from 'react'
import { Card, SectionLabel } from './UI'

const DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
const DAY_FULL = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function HeartbeatCard({ data }) {
  const { commit_activity } = data
  const canvasRef = useRef(null)
  const weeks = commit_activity.weeks || []
  const totals = weeks.map(w => w.total)
  const peak = Math.max(...totals, 1)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !totals.length) return
    const ctx = canvas.getContext('2d')
    const W = canvas.width
    const H = canvas.height
    ctx.clearRect(0, 0, W, H)

    const n = totals.length
    const step = W / (n - 1)
    const points = totals.map((v, i) => ({
      x: i * step,
      y: H - 8 - (v / peak) * (H - 20),
    }))

    const grad = ctx.createLinearGradient(0, 0, 0, H)
    grad.addColorStop(0, 'rgba(88,166,255,0.25)')
    grad.addColorStop(1, 'rgba(88,166,255,0)')
    ctx.beginPath()
    ctx.moveTo(points[0].x, H)
    points.forEach(p => ctx.lineTo(p.x, p.y))
    ctx.lineTo(points[n - 1].x, H)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    ctx.shadowColor = 'rgba(88,166,255,0.6)'
    ctx.shadowBlur = 12
    ctx.beginPath()
    ctx.moveTo(points[0].x, points[0].y)
    for (let i = 1; i < points.length - 1; i++) {
      const mx = (points[i].x + points[i + 1].x) / 2
      const my = (points[i].y + points[i + 1].y) / 2
      ctx.quadraticCurveTo(points[i].x, points[i].y, mx, my)
    }
    ctx.lineTo(points[n - 1].x, points[n - 1].y)
    ctx.strokeStyle = '#58A6FF'
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.shadowBlur = 0

    ctx.beginPath()
    ctx.moveTo(0, H - 8)
    ctx.lineTo(W, H - 8)
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.lineWidth = 1
    ctx.stroke()
  }, [totals, peak])

  const dayData = commit_activity.commits_by_day || {}
  const maxDay = Math.max(...Object.values(dayData), 1)

  return (
    <Card style={{ gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 24 }}>

        <div style={{ flex: 2, minWidth: 300 }}>
          <SectionLabel>commit activity — 52 weeks</SectionLabel>
          <div style={{ position: 'relative' }}>
            <canvas
              ref={canvasRef}
              width={600}
              height={100}
              style={{ width: '100%', height: 100, display: 'block' }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            <span>52 weeks ago</span>
            <span>peak {commit_activity.peak_week_commits} / avg {commit_activity.avg_commits_per_week}/wk</span>
            <span>now</span>
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 180 }}>
          <SectionLabel>by day of week</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {DAY_FULL.map((day) => {
              const count = dayData[day] ?? 0
              const pct = (count / maxDay) * 100
              return (
                <div key={day} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', width: 28 }}>{day.slice(0,3)}</span>
                  <div style={{ flex: 1, height: 6, background: 'var(--border)', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${pct}%`, background: 'var(--blue)', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', width: 36, textAlign: 'right' }}>{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Card>
  )
}
