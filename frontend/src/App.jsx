import EventLog from "./components/EventLog.jsx";
import SensorCard from "./components/SensorCard.jsx";
import { useSensors } from "./useSensors.js";

export default function App() {
  const { sensors, events, connected, mock } = useSensors();

  return (
    <div className="app">
      <header>
        <h1>HomeAuto</h1>
        {mock && <span className="badge">mock mode</span>}
        <span className={`conn ${connected ? "ok" : ""}`}>
          {connected ? "live" : "reconnecting…"}
        </span>
      </header>

      <main>
        <section className="grid">
          {sensors.map((s) => (
            <SensorCard key={s.name} sensor={s} mock={mock} />
          ))}
          {sensors.length === 0 && <p className="empty">Waiting for backend…</p>}
        </section>
        <EventLog events={events} />
      </main>
    </div>
  );
}
