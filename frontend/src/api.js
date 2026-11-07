async function request(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getInfo = () => request("/api/info");
export const getWiring = () => request("/api/wiring");
export const getEvents = (limit = 100) => request(`/api/events?limit=${limit}`);
export const clearEvents = () => request("/api/events", { method: "DELETE" });
export const setSensorEnabled = (name, enabled) =>
  request(`/api/sensors/${name}/enabled`, json("PUT", { enabled }));
export const simulate = (name, active) =>
  request(`/api/sensors/${name}/simulate`, json("POST", { active }));

export const wsUrl = () =>
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
