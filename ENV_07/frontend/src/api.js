const KEY = "env07.session";

export const session = {
  get() {
    try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; }
  },
  set(v) {
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch { }
  },
  clear() {
    try { localStorage.removeItem(KEY); } catch { }
  },
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = session.get()?.token;
  if (token) headers.Authorization = "Bearer " + token;

  let res;
  try {
    res = await fetch("/api" + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error("Không kết nối được backend (cổng 8000)");
  }
  let data = null;
  try { data = await res.json(); } catch { }

  if (res.status === 401 && !path.startsWith("/auth/login")) {
    session.clear();
    onUnauthorized();
  }
  if (!res.ok) {
    const d = data?.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join("; ") : `Lỗi ${res.status}`);
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  getBackgrounds: () => request("/settings/backgrounds"),
  setBackground: (scope, b) => request(`/settings/backgrounds/${scope}`, { method: "PUT", body: b }),
  register: (b) => request("/auth/register", { method: "POST", body: b }),
  login: (username, password) => request("/auth/login", { method: "POST", body: { username, password } }),
  logout: () => request("/auth/logout", { method: "POST" }),
  me: () => request("/auth/me"),
  roles: () => request("/roles"),
  users: () => request("/users"),
  addUser: (b) => request("/users", { method: "POST", body: b }),
  updateUser: (id, b) => request(`/users/${id}`, { method: "PUT", body: b }),
  deleteUser: (id) => request(`/users/${id}`, { method: "DELETE" }),
  activateUser: (id) => request(`/users/${id}/activate`, { method: "POST" }),

  crops: () => request("/crops"),
  addCrop: (b) => request("/crops", { method: "POST", body: b }),
  updateCrop: (id, b) => request(`/crops/${id}`, { method: "PUT", body: b }),
  deleteCrop: (id) => request(`/crops/${id}`, { method: "DELETE" }),
  saveStages: (id, list) => request(`/crops/${id}/stages`, { method: "PUT", body: list }),

  plant: () => request("/plant"),
  plantings: () => request("/plantings"),
  startPlanting: (b) => request("/plantings", { method: "POST", body: b }),
  updatePlanting: (b) => request("/plantings/active", { method: "PUT", body: b }),
  finishPlanting: () => request("/plantings/active/finish", { method: "POST" }),
  setMode: (auto) => request("/plant/mode", { method: "POST", body: { auto_mode: auto } }),

  dashboard: () => request("/dashboard"),
  readings: (n = 60) => request(`/readings?limit=${n}`),
  events: () => request("/events"),

  pumpRequests: () => request("/pump-requests"),
  requestPump: (liters, reason) => request("/pump-requests", { method: "POST", body: { liters, reason } }),
  approveRequest: (id, note) => request(`/pump-requests/${id}/approve`, { method: "POST", body: { note } }),
  rejectRequest: (id, note) => request(`/pump-requests/${id}/reject`, { method: "POST", body: { note } }),
  stopPump: () => request("/pump/stop", { method: "POST" }),

  recs: () => request("/recommendations"),
  generate: () => request("/recommendations", { method: "POST" }),
  apply: (id) => request(`/recommendations/${id}/apply`, { method: "POST" }),
  override: (id, b) => request(`/recommendations/${id}/override`, { method: "POST", body: b }),
  reject: (id, b) => request(`/recommendations/${id}/reject`, { method: "POST", body: b }),
  overrides: (id) => request(`/recommendations/${id}/overrides`),
};
