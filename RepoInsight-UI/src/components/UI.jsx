import React from 'react'

export function Card({ children, className = '', style = {} }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-card)',
      padding: '20px',
      ...style,
    }} className={className}>
      {children}
    </div>
  )
}

export function SectionLabel({ children, style = {} }) {
  return (
    <p style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '10px',
      fontWeight: 500,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      color: 'var(--text-muted)',
      marginBottom: '10px',
      ...style,
    }}>
      {children}
    </p>
  )
}

export function SampleFinePrint({ children }) {
  return (
    <span style={{
      fontFamily: 'var(--font-mono)',
      fontSize: '9px',
      fontWeight: 400,
      letterSpacing: '0.02em',
      textTransform: 'none',
      color: 'var(--text-muted)',
      opacity: 0.9,
    }}>
      {children}
    </span>
  )
}

export function CardSection({ title, finePrint }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        flexWrap: 'wrap',
        gap: '4px 8px',
      }}>
        <SectionLabel style={{ marginBottom: 0 }}>{title}</SectionLabel>
        {finePrint ? <SampleFinePrint>{finePrint}</SampleFinePrint> : null}
      </div>
    </div>
  )
}

export function Stat({ value, label, color = 'var(--text-primary)', size = 28 }) {
  return (
    <div>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: `${size}px`,
        fontWeight: 700,
        color,
        lineHeight: 1.1,
      }}>
        {value}
      </div>
      {label && (
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: 4 }}>
          {label}
        </div>
      )}
    </div>
  )
}

export function Badge({ children, color = 'var(--blue)' }) {
  return (
    <span style={{
      display: 'inline-block',
      fontFamily: 'var(--font-mono)',
      fontSize: '11px',
      padding: '2px 8px',
      borderRadius: '20px',
      background: `${color}22`,
      color,
      border: `1px solid ${color}44`,
    }}>
      {children}
    </span>
  )
}


export function Divider() {
  return <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '16px 0' }} />
}

export function Row({ left, right, mono = false }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '5px 0',
      fontSize: '13px',
    }}>
      <span style={{ color: 'var(--text-secondary)' }}>{left}</span>
      <span style={{
        fontFamily: mono ? 'var(--font-mono)' : 'inherit',
        color: 'var(--text-primary)',
        fontWeight: 500,
      }}>
        {right}
      </span>
    </div>
  )
}

export function Skeleton({ width = '100%', height = 16, radius = 4, style = {} }) {
  return (
    <div style={{
      width,
      height,
      borderRadius: radius,
      background: 'linear-gradient(90deg, var(--bg-card) 0%, var(--border) 50%, var(--bg-card) 100%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.4s infinite',
      ...style,
    }} />
  )
}

export function MiniBar({ value, max, color = 'var(--blue)', height = 6 }) {
  const pct = max ? Math.min(100, (value / max) * 100) : 0
  return (
    <div style={{
      height,
      background: 'var(--border)',
      borderRadius: 3,
      overflow: 'hidden',
    }}>
      <div style={{
        height: '100%',
        width: `${pct}%`,
        background: color,
        borderRadius: 3,
        transition: 'width 0.6s ease',
      }} />
    </div>
  )
}

if (typeof document !== 'undefined' && !document.getElementById('ui-keyframes')) {
  const s = document.createElement('style')
  s.id = 'ui-keyframes'
  s.textContent = `@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`
  document.head.appendChild(s)
}
