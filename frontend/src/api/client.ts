const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, signal?: AbortSignal): Promise<T> {
  const resp = await fetch(`${BACKEND_URL}${path}`, { signal })
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try {
      const body = await resp.json()
      msg = body.message ?? body.detail?.message ?? msg
    } catch {
      // ignore parse errors
    }
    throw new Error(msg)
  }
  return resp.json() as Promise<T>
}
