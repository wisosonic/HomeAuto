import { useEffect, useState } from "react";
import { getEvents, getInfo, wsUrl } from "./api.js";

const MAX_EVENTS = 100;

/**
 * Live sensor state: WebSocket (auto-reconnect) for snapshot + events,
 * REST for initial history and backend info.
 */
export function useSensors() {
  const [sensors, setSensors] = useState({}); // name -> snapshot
  const [events, setEvents] = useState([]); // newest first
  const [connected, setConnected] = useState(false);
  const [mock, setMock] = useState(false);

  useEffect(() => {
    getInfo().then((i) => setMock(i.mock)).catch(() => {});
    getEvents(MAX_EVENTS).then(setEvents).catch(() => {});
  }, []);

  useEffect(() => {
    let ws;
    let timer;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) timer = setTimeout(connect, 2000);
      };
      ws.onmessage = (m) => {
        const msg = JSON.parse(m.data);
        if (msg.type === "snapshot") {
          setSensors(Object.fromEntries(msg.sensors.map((s) => [s.name, s])));
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
  }, []);

  return { sensors: Object.values(sensors), events, connected, mock };
}
