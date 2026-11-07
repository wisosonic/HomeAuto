async function request(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const getInfo = () => request("/api/info");
export const getEvents = (limit = 100) => request(`/api/events?limit=${limit}`);
export const simulate = (name, active) =>
  request(`/api/sensors/${name}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active }),
  });

export const wsUrl = () =>
  `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
