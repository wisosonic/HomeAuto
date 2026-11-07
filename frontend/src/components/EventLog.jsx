import { useState } from "react";
import { confirmDialog, notify } from "../notify.js";
import { formatTime } from "./SensorCard.jsx";

export default function EventLog({ events, onClear }) {
  const [busy, setBusy] = useState(false);

  const clear = async () => {
    const ok = await confirmDialog({
      title: "Clear all events?",
      text: "This permanently deletes the stored event history.",
      confirmText: "Yes, clear them",
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try {
      const { deleted } = await onClear();
      notify.success(`${deleted} event${deleted === 1 ? "" : "s"} cleared`);
    } catch (e) {
      notify.error(`Could not clear events: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="log">
      <div className="log-head">
        <h2>Events</h2>
        <button className="btn danger" onClick={clear} disabled={busy || events.length === 0}>
          Clear
        </button>
      </div>
      {events.length === 0 ? (
        <p className="empty">No events yet.</p>
      ) : (
        <ul>
          {events.map((e, i) => (
            <li key={`${e.timestamp}-${e.sensor}-${i}`}>
              <time>{formatTime(e.timestamp)}</time>
              <span className="who">{e.sensor.replace("_", " ")}</span>
              <span className={`tag ${e.active ? "on" : ""}`}>{e.active ? "active" : "idle"}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
