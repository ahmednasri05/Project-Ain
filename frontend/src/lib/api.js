const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ── Reports ────────────────────────────────────────────────────────────────

export function fetchReports(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v)
  })
  return request(`/api/reports?${qs}`)
}

export function fetchReport(id) {
  return request(`/api/reports/${id}`)
}

// ── Analyze ────────────────────────────────────────────────────────────────

export function analyzeUrl(url, { force = false, skipSentiment = false } = {}) {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify({ url, force, skip_sentiment: skipSentiment }),
  })
}

// ── Pipeline runs ──────────────────────────────────────────────────────────

export function fetchPipelineRuns(limit = 50) {
  return request(`/api/pipeline-runs?limit=${limit}`)
}

// ── Failed requests ────────────────────────────────────────────────────────

export function fetchFailedRequests() {
  return request("/api/failed-requests")
}

export function retryFailedRequest(id) {
  return request(`/api/failed-requests/${id}/retry`, { method: "POST" })
}

// ── Stats ──────────────────────────────────────────────────────────────────

export function fetchStats(params = {}) {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v)
  })
  return request(`/api/stats?${qs}`)
}
