const API_PREFIX = '/api'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch {
    throw new Error('Backend tidak dapat dihubungi. Jalankan API di port 8000.')
  }
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(body?.error?.message || `Permintaan gagal (${response.status}).`)
    error.code = body?.error?.code
    throw error
  }
  return body
}

export const api = {
  health: () => request('/health'),
  createThread: (title) => request('/threads', { method: 'POST', body: JSON.stringify({ title }) }),
  renameThread: (id, title) => request(`/threads/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteThread: (id) => request(`/threads/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  sendMessage: (id, message) => request(`/threads/${encodeURIComponent(id)}/messages`, { method: 'POST', body: JSON.stringify({ message }) }),
  getDocument: (id) => request(`/documents/${encodeURIComponent(id)}`),
  convert: (id) => request(`/documents/${encodeURIComponent(id)}/conversions`, { method: 'POST' }),
  downloadUrl: (path) => path.startsWith('/api/files/') ? path : null,
}
