import { useState } from "react";
import { notify } from "../notify.js";
import { sensorInfo } from "../sensorInfo.js";
import { formatTime, sensorLabels } from "./SensorCard.jsx";

export default function SensorsPage({ sensors, onToggle }) {
  const [pending, setPending] = useState({}); // name -> true while a request is in flight

  const toggle = async (s) => {
    const label = s.name.replace("_", " ");
    const enable = !s.enabled;
    setPending((p) => ({ ...p, [s.name]: true }));
    try {
      await onToggle(s.name, enable);
      notify.success(`${label} ${enable ? "enabled" : "disabled"}`);
    } catch (e) {
      notify.error(`Could not ${enable ? "enable" : "disable"} ${label}: ${e.message}`);
    } finally {
      setPending((p) => ({ ...p, [s.name]: false }));
    }
  };

  const enabledCount = sensors.filter((s) => s.enabled).length;

  return (
    <section className="panel">
      <h2>Sensors</h2>
      <p className="hint">
        {enabledCount} of {sensors.length} enabled. A disabled sensor releases its GPIO pin and produces no
        events. The setting is saved and survives restarts.
      </p>
      {sensors.length === 0 && <p className="empty">Waiting for backend…</p>}
      <ul className="sensor-list">
        {sensors.map((s) => {
          const l = sensorLabels(s.kind);
          const info = sensorInfo(s.kind);
          const status = !s.enabled ? "Disabled" : s.active ? l.active : l.idle;
          return (
            <li key={s.name} className={s.enabled ? "" : "off"}>
              <div className="row">
                <span className="icon">{l.icon}</span>
                <div className="info">
                  <strong>
                    {s.name.replace("_", " ")}
                    {info.model && <span className="model"> · {info.model}</span>}
                  </strong>
                  <small>
                    GPIO {s.pin} · {s.detection_count} detections
                    {s.last_event && <> · last {formatTime(s.last_event.timestamp)}</>}
                  </small>
                </div>
                <span className={`tag ${s.enabled && s.active ? "on" : ""}`}>{status}</span>
                <label className="switch" title={s.enabled ? "Disable sensor" : "Enable sensor"}>
                  <input
                    type="checkbox"
                    role="switch"
                    checked={s.enabled}
                    disabled={pending[s.name]}
                    onChange={() => toggle(s)}
                    aria-label={`${s.enabled ? "Disable" : "Enable"} ${s.name}`}
                  />
                  <span className="slider" />
                </label>
              </div>

              <p className="desc">{info.summary}</p>
              <details className="more">
                <summary>What it reports and how to use it</summary>
                <dl>
                  <dt>Reports</dt>
                  <dd>
                    {info.gives}
                    <br />
                    <span className="states">
                      Shown here as “{l.active}” or “{l.idle}”.
                    </span>
                  </dd>
                  {info.goodFor && (
                    <>
                      <dt>Good for</dt>
                      <dd>{info.goodFor}</dd>
                    </>
                  )}
                  {info.notes && (
                    <>
                      <dt>Keep in mind</dt>
                      <dd>{info.notes}</dd>
                    </>
                  )}
                </dl>
              </details>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
