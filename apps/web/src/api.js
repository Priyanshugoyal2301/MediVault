/** Same-origin BFF client. Credentials stay in an HttpOnly session cookie. */
const BASE = import.meta.env.VITE_API_BASE || '';
export class ApiError extends Error { constructor(message, status) { super(message); this.status = status; } }
function notifyExpiredSession(response, path) {
  // Invalid sign-in/MFA attempts are local form errors, not session expiry.
  if(response.status===401 && !path.startsWith('/auth/'))
    window.dispatchEvent(new Event('medivault:session-expired'));
}
export async function request(path, {method = 'GET', body, headers = {}, signal} = {}) {
  const form = body instanceof FormData;
  const response = await fetch(BASE + path, { method, credentials: 'include', cache: 'no-store', signal,
    headers: {...(body && !form ? {'Content-Type': 'application/json'} : {}), ...headers},
    body: body ? (form ? body : JSON.stringify(body)) : undefined });
  if (!response.ok) {
    notifyExpiredSession(response,path);
    let message = `Request failed (${response.status}). Please try again.`;
    try { const data = await response.json(); message = typeof data.detail === 'string' ? data.detail :
      Array.isArray(data.detail) ? data.detail.map(x => `${x.loc.at(-1)}: ${x.msg}`).join('; ') : message; } catch {}
    const error = new ApiError(message, response.status);
    error.mfaRequired = response.headers.get('X-MFA-Required') === 'true';
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
export const patientPath = (id, resource) => `/care/patients/${encodeURIComponent(id)}/${resource}`;
export const scoped = (path, patientId) => `${path}${path.includes('?') ? '&' : '?'}patient_id=${encodeURIComponent(patientId)}`;
export async function listAll(path) {
  const rows = [];
  for (let offset=0; offset<10000; offset+=100) {
    const page = await request(`${path}${path.includes('?')?'&':'?'}offset=${offset}`);
    rows.push(...page);
    if(page.length<100)return rows;
  }
  throw new Error('This record contains more than 10,000 entries. A paginated review is required.');
}
export async function documentBlob(id, patientId) {
  const response = await fetch(BASE + scoped(`/reports/${id}/file`, patientId), {credentials:'include', cache:'no-store'});
  notifyExpiredSession(response,'/reports');
  if (!response.ok) throw new ApiError('The original document could not be downloaded.', response.status);
  return response.blob();
}
export async function downloadDocument(id, patientId, filename) {
  const url = URL.createObjectURL(await documentBlob(id, patientId));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
