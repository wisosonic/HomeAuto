import { useEffect, useState } from "react";
import EventLog from "./components/EventLog.jsx";
import SensorCard from "./components/SensorCard.jsx";
import SensorsPage from "./components/SensorsPage.jsx";
import WiringPage from "./components/WiringPage.jsx";
import { useSensors } from "./useSensors.js";

const PAGES = [
  { id: "dashboard", label: "Dashboard", hash: "#/" },
  { id: "sensors", label: "Sensors", hash: "#/sensors" },
  { id: "wiring", label: "Wiring", hash: "#/wiring" },
];

// Minimal hash routing so no router dependency is needed.
function usePage() {
  const read = () => PAGES.find((p) => p.hash === location.hash)?.id ?? "dashboard";
  const [page, setPage] = useState(read);
  useEffect(() => {
    const on = () => setPage(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return page;
}

export default function App() {
  // Keep the live connection open on every page so events are never missed.
  const { sensors, events, connected, mock, clearEvents, setEnabled } = useSensors();
  const page = usePage();

  return (
    <div className="app">
      <header>
        <h1>HomeAuto</h1>
        <nav>
          {PAGES.map((p) => (
            <a key={p.id} href={p.hash} className={page === p.id ? "active" : ""}>
              {p.label}
            </a>
          ))}
        </nav>
        {mock && <span className="badge">mock mode</span>}
        <span className={`conn ${connected ? "ok" : ""}`}>{connected ? "live" : "reconnecting…"}</span>
      </header>

      {page === "wiring" && <WiringPage />}
      {page === "sensors" && <SensorsPage sensors={sensors} onToggle={setEnabled} />}
      {page === "dashboard" && (
        <main>
          <section className="grid">
            {sensors.map((s) => (
              <SensorCard key={s.name} sensor={s} mock={mock} />
            ))}
            {sensors.length === 0 && <p className="empty">Waiting for backend…</p>}
          </section>
          <EventLog events={events} onClear={clearEvents} />
        </main>
      )}
    </div>
  );
}
