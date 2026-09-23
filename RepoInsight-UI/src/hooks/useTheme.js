import { useEffect, useState } from 'react'

const STORAGE_KEY = 'repoinsight-theme'

export function getInitialTheme() {
  if (typeof window === 'undefined') return 'dark'
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(STORAGE_KEY, theme)
}

export function useTheme() {
  const [theme, setThemeState] = useState(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  function setTheme(next) {
    setThemeState(next)
  }

  function toggleTheme() {
    setThemeState(t => (t === 'dark' ? 'light' : 'dark'))
  }

  return { theme, setTheme, toggleTheme }
}
