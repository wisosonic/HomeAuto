import { useCallback, useEffect, useState } from "react";
import { clearEvents as apiClearEvents, getEvents, getInfo, setSensorEnabled, wsUrl } from "./api.js";
import { notify } from "./notify.js";

const MAX_EVENTS = 100;

/**
 * Live sensor state: WebSocket (auto-reconnect) for snapshot + events,
 * REST for initial history, backend info and the actions (clear, enable/disable).
 */
export function useSensors(token, can) {
  const [sensors, setSensors] = useState({}); // name -> snapshot
  const [events, setEvents] = useState([]); // newest first
  const [connected, setConnected] = useState(false);
  const [mock, setMock] = useState(false);

  useEffect(() => {
    getInfo().then((i) => setMock(i.mock)).catch(() => {});
    if (can("events.view")) getEvents(MAX_EVENTS).then(setEvents).catch(() => {});
  }, [can]);

  useEffect(() => {
    let ws;
    let timer;
    let closed = false;
    let everConnected = false;
    let lostNotified = false;

    const connect = () => {
      ws = new WebSocket(wsUrl());
      // the server expects the token as the first message (not in the URL, so it stays out of logs)
      ws.onopen = () => ws.send(JSON.stringify({ type: "auth", token }));
      const markConnected = () => {
        setConnected(true);
        if (lostNotified) notify.success("Connection restored");
        everConnected = true;
        lostNotified = false;
      };
      ws.onclose = (e) => {
        setConnected(false);
        if (closed) return;
        if (e.code === 4401 || e.code === 4403) {
          closed = true; // retrying with the same token cannot succeed
          notify.error(e.code === 4403 ? "Your role cannot see the live feed" : "Live feed refused the session");
          return;
        }
        // notify once per outage, and only if we had been connected before
        if (everConnected && !lostNotified) {
          lostNotified = true;
          notify.warning("Lost connection to the backend, reconnecting…");
        }
        timer = setTimeout(connect, 2000);
      };
      ws.onmessage = (m) => {
        const msg = JSON.parse(m.data);
        if (msg.type === "snapshot") {
          markConnected(); // the server only sends this once the token was accepted
          setSensors(Object.fromEntries(msg.sensors.map((s) => [s.name, s])));
        } else if (msg.type === "sensor_state") {
          setSensors((prev) => ({ ...prev, [msg.sensor.name]: msg.sensor }));
        } else if (msg.type === "events_cleared") {
          setEvents((prev) => (msg.sensor ? prev.filter((e) => e.sensor !== msg.sensor) : []));
          // detection counts and last-seen time are derived from the history, so reset them too
          setSensors((prev) =>
            Object.fromEntries(
              Object.entries(prev).map(([name, s]) =>
                !msg.sensor || name === msg.sensor ? [name, { ...s, detection_count: 0, last_event: null }] : [name, s]
              )
            )
          );
        } else if (msg.type === "event") {
          const { type, ...ev } = msg;
          setSensors((prev) => {
            const s = prev[ev.sensor];
            if (!s) return prev;
            return {
              ...prev,
              [ev.sensor]: {
                ...s,
                active: ev.active,
                detection_count: s.detection_count + (ev.active ? 1 : 0),
                last_event: ev,
              },
            };
          });
          setEvents((prev) => [ev, ...prev].slice(0, MAX_EVENTS));
        }
      };
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [token]);

  const clearEvents = useCallback(async () => {
    const result = await apiClearEvents(); // { deleted: n }
    setEvents([]);
    return result;
  }, []);

  const setEnabled = useCallback(async (name, enabled) => {
    const snap = await setSensorEnabled(name, enabled);
    setSensors((prev) => ({ ...prev, [name]: snap }));
  }, []);

  return { sensors: Object.values(sensors), events, connected, mock, clearEvents, setEnabled };
}
