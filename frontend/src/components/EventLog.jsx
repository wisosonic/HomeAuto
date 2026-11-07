import { formatTime } from "./SensorCard.jsx";

export default function EventLog({ events }) {
  return (
    <section className="log">
      <h2>Events</h2>
      {events.length === 0 ? (
        <p className="empty">No events yet.</p>
      ) : (
        <ul>
          {events.map((e, i) => (
            <li key={`${e.timestamp}-${e.sensor}-${i}`}>
              <time>{formatTime(e.timestamp)}</time>
              <span className="who">{e.sensor.replace("_", " ")}</span>
              <span className={`tag ${e.active ? "on" : ""}`}>
                {e.active ? "active" : "idle"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
