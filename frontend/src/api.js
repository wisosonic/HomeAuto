// The session token lives in memory here; useAuth.js persists it and calls setToken.
let token = null;
let onUnauthorized = () => {};

export const setToken = (t) => {
  token = t;
};
/** Called when a request made with a token comes back 401 (session expired or ended). */
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

async function request(path, options = {}) {
  const headers = { ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401 && token && path !== "/api/auth/login") onUnauthorized();
  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      /* not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : `${res.status} ${res.statusText}`);
  }
  return res.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getInfo = () => request("/api/info");
export const getWiring = (enabledOnly = false) => request(`/api/wiring${enabledOnly ? "?enabled_only=true" : ""}`);
export const getEvents = (limit = 100) => request(`/api/events?limit=${limit}`);
export const clearEvents = () => request("/api/events", { method: "DELETE" });
export const setSensorEnabled = (name, enabled) =>
  request(`/api/sensors/${name}/enabled`, json("PUT", { enabled }));
export const simulate = (name, active) =>
  request(`/api/sensors/${name}/simulate`, json("POST", { active }));

// schedule rules (start/end are epoch seconds)
export const getSchedules = () => request("/api/schedules");
export const createSchedule = (rule) => request("/api/schedules", json("POST", rule));
export const updateSchedule = (id, rule) => request(`/api/schedules/${id}`, json("PUT", rule));
export const deleteSchedule = (id) => request(`/api/schedules/${id}`, { method: "DELETE" });

// auth
export const login = (username, password) => request("/api/auth/login", json("POST", { username, password }));
export const logout = () => request("/api/auth/logout", { method: "POST" });
export const getMe = () => request("/api/auth/me");
export const changePassword = (current_password, new_password) =>
  request("/api/auth/password", json("POST", { current_password, new_password }));

// users and roles
const enc = encodeURIComponent;
export const getUsers = () => request("/api/users");
export const createUser = (username, password, role) =>
  request("/api/users", json("POST", { username, password, role }));
export const updateUser = (username, changes) => request(`/api/users/${enc(username)}`, json("PATCH", changes));
export const deleteUser = (username) => request(`/api/users/${enc(username)}`, { method: "DELETE" });
export const getRoles = () => request("/api/roles");
export const getPermissions = () => request("/api/permissions");
export const createRole = (name, permissions) => request("/api/roles", json("POST", { name, permissions }));
export const updateRole = (name, permissions) =>
  request(`/api/roles/${enc(name)}`, json("PUT", { permissions }));
export const deleteRole = (name) => request(`/api/roles/${enc(name)}`, { method: "DELETE" });

export const wsUrl = () =>
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
