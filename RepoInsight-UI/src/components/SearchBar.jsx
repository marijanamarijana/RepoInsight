import React, { useState } from 'react'

export default function SearchBar({ onSubmit, loading }) {
  const [repo, setRepo] = useState('')
  const [token, setToken] = useState('')
  const [showToken, setShowToken] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (repo.trim()) onSubmit(repo.trim(), token.trim())
  }

  return (
    <form onSubmit={handleSubmit} style={{ width: '100%', maxWidth: 680 }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-md)',
        padding: '4px 4px 4px 16px',
        boxShadow: '0 0 0 1px transparent',
        transition: 'box-shadow 0.2s, border-color 0.2s',
        gap: 8,
      }}
      onFocus={e => e.currentTarget.style.borderColor = 'var(--border-focus)'}
      onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
      >
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 13, userSelect: 'none' }}>
          $
        </span>
        <input
          value={repo}
          onChange={e => setRepo(e.target.value)}
          placeholder="facebook/react  or  https://github.com/owner/repo"
          disabled={loading}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: 14,
            padding: '8px 0',
          }}
        />
        <button
          type="submit"
          disabled={loading || !repo.trim()}
          style={{
            background: loading ? 'var(--border)' : 'var(--blue)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 18px',
            fontFamily: 'var(--font-ui)',
            fontWeight: 600,
            fontSize: 13,
            cursor: loading || !repo.trim() ? 'not-allowed' : 'pointer',
            transition: 'background 0.15s',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          {loading ? <Spinner /> : null}
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          type="button"
          onClick={() => setShowToken(v => !v)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <span style={{ fontSize: 10 }}>{showToken ? '▼' : '▶'}</span>
          GitHub token (recommended)
        </button>

        {showToken && (
          <input
            type="password"
            value={token}
            onChange={e => setToken(e.target.value)}
            placeholder="ghp_…"
            style={{
              flex: 1,
              background: 'var(--bg-input)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 10px',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              outline: 'none',
            }}
          />
        )}
        {!showToken && (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Without a token: 60 req/hr limit. With token: 5,000/hr.
          </span>
        )}
      </div>
    </form>
  )
}

function Spinner() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" style={{ animation: 'spin 0.7s linear infinite' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <circle cx="7" cy="7" r="5.5" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2"/>
      <path d="M7 1.5 A5.5 5.5 0 0 1 12.5 7" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}
