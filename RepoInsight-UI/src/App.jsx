import React, { useState } from 'react'
import { analyzeRepo, fetchAiInsights } from './utils/api'
import AiAnalysisCard from './components/AiAnalysisCard'
import { useTheme } from './hooks/useTheme'
import SearchBar from './components/SearchBar'
import OverviewCard from './components/OverviewCard'
import HeartbeatCard from './components/HeartbeatCard'
import ContributorsCard from './components/ContributorsCard'
import CommitsCard from './components/CommitsCard'
import { IssuesCard, PullRequestsCard } from './components/IssuesPRsCard'
import { ReleasesCard, CodeFrequencyCard } from './components/ReleasesCodeCard'
import SummaryCard from './components/SummaryCard'
import LanguagesCard from "./components/LanguagesCard";

const EXAMPLES = ['react/react', 'Microsoft365DSC/Microsoft365DSC', 'vercel/next.js', 'tensorflow/tensorflow']

const TOKEN_KEY = 'repoinsight-github-token'

export default function App() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [repo, setRepo] = useState('')
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) || '')
  const [lastRepo, setLastRepo] = useState(null)
  const [aiInsight, setAiInsight] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState(null)
  const { theme, toggleTheme } = useTheme()

  function handleTokenChange(next) {
    setToken(next)
    if (next) sessionStorage.setItem(TOKEN_KEY, next)
    else sessionStorage.removeItem(TOKEN_KEY)
  }

  async function handleSubmit(nextRepo) {
    const slug = (nextRepo ?? repo).trim()
    if (!slug) return
    setRepo(slug)
    setLoading(true)
    setError(null)
    setData(null)
    setLastRepo(slug)
    setAiInsight(null)
    setAiError(null)
    try {
      const result = await analyzeRepo(slug, token.trim())
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleAiAnalysis() {
    if (!lastRepo) return
    setAiLoading(true)
    setAiError(null)
    try {
      const result = await fetchAiInsights(lastRepo, token.trim())
      setAiInsight(result)
    } catch (err) {
      setAiError(err.message)
      setAiInsight(null)
    } finally {
      setAiLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>

      <header style={{
        borderBottom: '1px solid var(--border)',
        padding: '0 24px',
        height: 52,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--bg-card)',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Logo />
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 15, color: 'var(--text-primary)' }}>
            RepoInsight
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            powered by GitHub API
          </span>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </header>

      <div style={{
        padding: data ? '20px 24px' : '80px 24px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
        transition: 'padding 0.3s ease',
        borderBottom: data ? '1px solid var(--border)' : 'none',
        background: data ? 'var(--bg-card)' : 'transparent',
      }}>
        {!data && (
          <>
            <h1 style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 'clamp(28px, 5vw, 48px)',
              fontWeight: 700,
              color: 'var(--text-primary)',
              textAlign: 'center',
              letterSpacing: '-0.02em',
            }}>
              Analyze any GitHub repo
            </h1>
            <p style={{ fontSize: 15, color: 'var(--text-secondary)', textAlign: 'center', maxWidth: 480 }}>
              Commits, contributors, issues, PRs, releases, and code health - all from the public API.
            </p>
          </>
        )}

        <SearchBar
          repo={repo}
          onRepoChange={setRepo}
          token={token}
          onTokenChange={handleTokenChange}
          onSubmit={handleSubmit}
          loading={loading}
          compact={!!data}
        />

        {!data && !loading && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Try:</span>
            {EXAMPLES.map(r => (
              <button
                key={r}
                onClick={() => handleSubmit(r)}
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderRadius: 20,
                  padding: '3px 12px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  color: 'var(--blue)',
                  cursor: 'pointer',
                }}
              >
                {r}
              </button>
            ))}
          </div>
        )}
      </div>

      <main style={{ flex: 1, padding: '24px', maxWidth: 1280, margin: '0 auto', width: '100%' }}>

        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center', padding: '60px 0' }}>
            <PulseRing />
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-secondary)' }}>
              Analyzing <span style={{ color: 'var(--blue)' }}>{lastRepo}</span>…
            </p>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Fetching commits, issues, PRs, releases, and contributor stats
            </p>
          </div>
        )}

        {error && (
          <div style={{
            background: 'var(--error-bg)',
            border: '1px solid var(--red)',
            borderRadius: 'var(--radius-md)',
            padding: 20,
            color: 'var(--red)',
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
          }}>
            <strong>Error:</strong> {error}
            <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
              Check the repo slug (owner/repo), your token, or rate limit status.
            </div>
          </div>
        )}

        {data && (
          <div className="dashboard-grid">
            <OverviewCard data={data} className="dashboard-span-full" />
            <HeartbeatCard data={data} theme={theme} className="dashboard-span-full" />
            <SummaryCard data={data} className="dashboard-span-full" />
            <AiAnalysisCard
              insight={aiInsight}
              error={aiError}
              loading={aiLoading}
              onRun={handleAiAnalysis}
              disabled={!data}
            />
            <LanguagesCard data={data} />
            <IssuesCard data={data} />
            <PullRequestsCard data={data} />
            <CommitsCard data={data} />
            <ReleasesCard data={data} />
            <ContributorsCard data={data} />
            <CodeFrequencyCard data={data} className="dashboard-span-full" />
          </div>
        )}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '14px 24px',
        textAlign: 'center',
        fontSize: 11,
        color: 'var(--text-muted)',
        fontFamily: 'var(--font-mono)',
      }}>
        RepoInsight · public GitHub REST API · data is live, not cached
      </footer>
    </div>
  )
}

function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <rect width="22" height="22" rx="6" fill="var(--blue)" opacity="0.15"/>
      <path d="M11 3 L19 7 L19 15 L11 19 L3 15 L3 7 Z" stroke="var(--blue)" strokeWidth="1.5" fill="none"/>
      <circle cx="11" cy="11" r="2.5" fill="var(--blue)"/>
      <line x1="11" y1="5" x2="11" y2="8.5" stroke="var(--blue)" strokeWidth="1.5"/>
    </svg>
  )
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}

function PulseRing() {
  return (
    <div style={{ position: 'relative', width: 60, height: 60 }}>
      <style>{`
        @keyframes pulse-ring {
          0% { transform: scale(0.5); opacity: 1; }
          100% { transform: scale(1.5); opacity: 0; }
        }
      `}</style>
      <div style={{
        position: 'absolute', inset: 0, borderRadius: '50%',
        border: '2px solid var(--blue)',
        animation: 'pulse-ring 1.2s ease-out infinite',
      }}/>
      <div style={{
        position: 'absolute', inset: 0, borderRadius: '50%',
        border: '2px solid var(--blue)',
        animation: 'pulse-ring 1.2s ease-out infinite',
        animationDelay: '0.4s',
      }}/>
      <div style={{
        position: 'absolute', inset: 8, borderRadius: '50%',
        background: 'var(--blue)',
        opacity: 0.3,
      }}/>
    </div>
  )
}
