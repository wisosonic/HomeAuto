import { useEffect, useState } from "react";
import { getWiring } from "../api.js";
import WiringDiagram from "./WiringDiagram.jsx";

const STEPS = [
  "Power the Pi OFF while wiring.",
  "Plug each module's 3 pins into row a, in its own set of columns (see table).",
  "Pi 3V3 → 3.3V rail and Pi GND → GND rail (female-to-male). Bridge the rails if your breadboard splits them mid-way.",
  "Rail → module (male-to-male): 3.3V rail to each VCC column, GND rail to each GND column.",
  "PIR only: Pi 5V pin straight to the PIR's VCC column. There is no 5V rail.",
  "Signals (female-to-male): one wire per module, Pi GPIO pin → the module's signal column.",
  "Match each module's pins by its silkscreen label (VCC/+, GND/G/-, DO/OUT/S). Leave AO unconnected.",
];

const CHECKS = [
  "Only the PIR VCC is on 5V; every other module is on the 3.3V rail.",
  "No AO pin is wired.",
  "GND rail is connected to the Pi's GND pin.",
  "No signal wire touches a rail; the 5V wire does not touch the 3.3V rail.",
];

export default function WiringPage() {
  const [wiring, setWiring] = useState(null);
  const [error, setError] = useState(null);
  const [checked, setChecked] = useState({});

  useEffect(() => {
    getWiring().then(setWiring).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="empty">Could not load wiring: {error}</p>;
  if (!wiring) return <p className="empty">Loading wiring…</p>;

  return (
    <div className="wiring">
      <section className="panel">
        <h2>Breadboard diagram</h2>
        <p className="hint">
          Generated from the backend pin map (<code>pinmap.py</code>). Wires in rows b–e of a column connect to
          that column's module pin. The pin order drawn is illustrative: match your module's silkscreen labels.
        </p>
        <div className="diagram-scroll">
          <WiringDiagram wiring={wiring} />
        </div>
      </section>

      <section className="panel">
        <h2>Pin configuration</h2>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Sensor</th>
                <th>GPIO (BCM)</th>
                <th>Pi pin</th>
                <th>Signal pin</th>
                <th>VCC</th>
                <th>Active</th>
                <th>Columns (VCC / sig / GND)</th>
              </tr>
            </thead>
            <tbody>
              {wiring.modules.map((m) => (
                <tr key={m.key}>
                  <td>{m.label}</td>
                  <td>GPIO{m.gpio}</td>
                  <td>{m.physical_pin ?? "?"}</td>
                  <td>{m.signal_label}</td>
                  <td className={m.vcc === "5V" ? "warn" : ""}>{m.vcc === "5V" ? "5V (Pi pin 2)" : "3.3V rail"}</td>
                  <td>{m.active}</td>
                  <td>
                    {m.columns.vcc} / {m.columns.signal} / {m.columns.gnd}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint">
          Power pins: {wiring.power.map((p) => `${p.name} = pin ${p.physical_pin}`).join(" · ")}. Change GPIOs
          only in <code>backend/homeauto/pinmap.py</code>.
        </p>
      </section>

      <div className="two-col">
        <section className="panel">
          <h2>Wiring steps</h2>
          <ol className="steps">
            {STEPS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </section>
        <section className="panel">
          <h2>Check before power-on</h2>
          <ul className="checks">
            {CHECKS.map((c) => (
              <li key={c}>
                <label>
                  <input
                    type="checkbox"
                    checked={!!checked[c]}
                    onChange={(e) => setChecked({ ...checked, [c]: e.target.checked })}
                  />{" "}
                  {c}
                </label>
              </li>
            ))}
          </ul>
          <p className="hint warn">A 5V signal into a Pi GPIO can damage the board.</p>
        </section>
      </div>
    </div>
  );
}
