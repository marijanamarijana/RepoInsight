const BASE = 'http://localhost:8000/graphQL'

export async function analyzeRepo(repo, token) {
  const params = new URLSearchParams({ repo })
  if (token) params.set('token', token)
  const res = await fetch(`${BASE}/analyze/full?${params}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getRateLimit(token) {
  const params = token ? new URLSearchParams({ token }) : new URLSearchParams()
  const res = await fetch(`${BASE}/analyze/rate-limit?${params}`)
  if (!res.ok) return null
  return res.json()
}
