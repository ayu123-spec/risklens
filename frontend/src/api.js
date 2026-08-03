// Central API helper. Uses VITE_API_URL in production, proxy in dev.
const API_BASE = import.meta.env.VITE_API_URL || "";

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`);
  return res.json();
}

export async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail ? JSON.stringify(d.detail) : `POST ${path} failed (${res.status})`);
  }
  return res.json();
}
