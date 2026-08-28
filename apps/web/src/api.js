/**
 * MediVault web API client — talks only to the BFF (apps/api).
 * Never send X-User-ID from the browser; the gateway injects it from JWT.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '';

function authHeaders(token, extra = {}) {
  const headers = { ...extra };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function parseError(res) {
  let detail = `Request failed (${res.status})`;
  try {
    const data = await res.json();
    detail = data.detail || JSON.stringify(data);
  } catch {
    /* ignore */
  }
  throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
}

export async function register(email, password, locale = 'en-IN') {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, locale_preference: locale }),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function me(token) {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(token),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function listReports(token) {
  const res = await fetch(`${API_BASE}/reports`, {
    headers: authHeaders(token),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function getReport(token, reportId) {
  const res = await fetch(`${API_BASE}/reports/${reportId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function uploadReport(token, file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/reports`, {
    method: 'POST',
    headers: authHeaders(token),
    body: form,
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function seedDemoReport(token, panel = 'cbc') {
  const res = await fetch(`${API_BASE}/reports/demo/seed?panel=${encodeURIComponent(panel)}`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function getTimelineSummary(token) {
  const res = await fetch(`${API_BASE}/timeline`, {
    headers: authHeaders(token),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function getTimelineAnomaly(token, testName) {
  const res = await fetch(
    `${API_BASE}/timeline/${encodeURIComponent(testName)}/anomaly`,
    { headers: authHeaders(token) },
  );
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function askQuestion(token, question, locale = 'en-IN', sessionId = null) {
  const res = await fetch(`${API_BASE}/qa`, {
    method: 'POST',
    headers: authHeaders(token, { 'Content-Type': 'application/json' }),
    body: JSON.stringify({
      question,
      locale,
      session_id: sessionId,
    }),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function pollReportUntilDone(token, reportId, { timeoutMs = 90000, intervalMs = 1500 } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const report = await getReport(token, reportId);
    if (report.parsed_status === 'complete' || report.parsed_status === 'failed') {
      return report;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error('Timed out waiting for report parsing');
}
