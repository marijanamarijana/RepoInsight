import React, { useState } from 'react'

export default function SearchBar({ repo, onRepoChange, token, onTokenChange, onSubmit, loading, compact }) {
  const [showToken, setShowToken] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (repo.trim()) onSubmit(repo.trim())
  }

  return (
    <form onSubmit={handleSubmit} className="search-shell">
      <div className="search-row">
        <span className="search-prompt">$</span>
        <input
          className="search-input"
          value={repo}
          onChange={e => onRepoChange(e.target.value)}
          placeholder="owner/repo  or  https://github.com/owner/repo"
          disabled={loading}
          aria-label="GitHub repository"
        />
        <button
          type="submit"
          className="search-submit"
          disabled={loading || !repo.trim()}
        >
          {loading ? <Spinner /> : null}
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      <div className="token-field">
        <label className="token-label" htmlFor="github-token">
          GitHub token <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(optional)</span>
        </label>
        <div className="token-row">
          <input
            id="github-token"
            className="token-input"
            type={showToken ? 'text' : 'password'}
            value={token}
            onChange={e => onTokenChange(e.target.value)}
            placeholder="Paste a personal access token"
            autoComplete="off"
            spellCheck={false}
            aria-describedby={compact ? undefined : 'github-token-hint'}
          />
          <button
            type="button"
            className="token-toggle"
            onClick={() => setShowToken(v => !v)}
            aria-pressed={showToken}
          >
            {showToken ? 'Hide' : 'Show'}
          </button>
        </div>
        {!compact && (
          <p id="github-token-hint" className="token-hint">
            Optional, and only kept in this browser tab. A token lets GitHub return fuller data.{' '}
            <a href="https://github.com/settings/tokens" target="_blank" rel="noreferrer">
              Create a token
            </a>
          </p>
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
