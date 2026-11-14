const API = (import.meta.env?.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw Object.assign(new Error("Can't reach the planning server. Check your connection and try again."), { field: null });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw Object.assign(new Error(data.error || `Request failed (${res.status})`), { field: data.field });
  }
  return data;
}

export const searchPlaces = (q, signal) =>
  request(`/api/geocode/?q=${encodeURIComponent(q)}`, { signal }).then((d) => d.results || []);

export const reversePlace = (lat, lon) => request(`/api/reverse/?lat=${lat}&lon=${lon}`);

export const planTrip = (payload) =>
  request("/api/plan-trip/", { method: "POST", body: JSON.stringify(payload) });
