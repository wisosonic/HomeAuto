import { useEffect, useState } from "react";
import AccountPage from "./components/AccountPage.jsx";
import EventLog from "./components/EventLog.jsx";
import LoginPage from "./components/LoginPage.jsx";
import SchedulesPage from "./components/SchedulesPage.jsx";
import SensorCard from "./components/SensorCard.jsx";
import SensorsPage from "./components/SensorsPage.jsx";
import UsersPage from "./components/UsersPage.jsx";
import WiringPage from "./components/WiringPage.jsx";
import { useAuth } from "./useAuth.js";
import { useSensors } from "./useSensors.js";

// `needs`: the user must hold at least one of these permissions to see the page (none = any user).
const PAGES = [
  { id: "dashboard", label: "Dashboard", hash: "#/", needs: ["sensors.view"] },
  { id: "sensors", label: "Sensors", hash: "#/sensors", needs: ["sensors.view"] },
  { id: "schedules", label: "Schedules", hash: "#/schedules", needs: ["schedules.view"] },
  { id: "wiring", label: "Wiring", hash: "#/wiring", needs: ["wiring.view"] },
  { id: "users", label: "Users", hash: "#/users", needs: ["users.manage", "roles.manage"] },
  { id: "account", label: "Account", hash: "#/account", needs: [], hidden: true },
];

// Minimal hash routing so no router dependency is needed.
function usePage(allowed) {
  const read = () => PAGES.find((p) => p.hash === location.hash)?.id ?? "dashboard";
  const [page, setPage] = useState(read);
  useEffect(() => {
    const on = () => setPage(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  // a page the user may not open (typed URL, or permissions changed): show the first allowed one
  return allowed.some((p) => p.id === page) ? page : allowed[0]?.id ?? "account";
}

function Shell({ auth }) {
  const { user, token, can, logout } = auth;
  // Keep the live connection open on every page so events are never missed.
  const { sensors, events, connected, mock, clearEvents, setEnabled } = useSensors(token, can);
  const allowed = PAGES.filter((p) => p.needs.length === 0 || p.needs.some(can));
  const page = usePage(allowed);

  return (
    <div className="app">
      <header>
        <h1>HomeAuto</h1>
        <nav>
          {allowed.filter((p) => !p.hidden).map((p) => (
            <a key={p.id} href={p.hash} className={page === p.id ? "active" : ""}>
              {p.label}
            </a>
          ))}
        </nav>
        {mock && <span className="badge">mock mode</span>}
        <span className={`conn ${connected ? "ok" : ""}`}>{connected ? "live" : "reconnecting…"}</span>
        <a href="#/account" className={`who-am-i ${page === "account" ? "active" : ""}`} title={`Role: ${user.role}`}>
          {user.username}
        </a>
        <button className="btn" onClick={logout}>Sign out</button>
      </header>

      {page === "account" && <AccountPage user={user} />}
      {page === "users" && <UsersPage me={user} can={can} />}
      {page === "wiring" && <WiringPage />}
      {page === "schedules" && <SchedulesPage sensors={sensors} canManage={can("schedules.manage")} />}
      {page === "sensors" && <SensorsPage sensors={sensors} onToggle={setEnabled} canControl={can("sensors.control")} />}
      {page === "dashboard" && (
        <main>
          <section className="grid">
            {sensors.map((s) => (
              <SensorCard key={s.name} sensor={s} mock={mock && can("sensors.simulate")} />
            ))}
            {sensors.length === 0 && <p className="empty">Waiting for backend…</p>}
          </section>
          {can("events.view") && <EventLog events={events} onClear={clearEvents} canClear={can("events.clear")} />}
        </main>
      )}
      {allowed.length === 1 && page === "account" && (
        <p className="hint">Your role has no access to sensors yet. Ask an administrator to update it.</p>
      )}
    </div>
  );
}

export default function App() {
  const auth = useAuth();
  if (!auth.ready) return null; // checking a stored token: avoid flashing the login form
  if (!auth.user) return <LoginPage onLogin={auth.login} />;
  return <Shell auth={auth} />;
}
