const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}
