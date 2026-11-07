import { simulate } from "../api.js";

const LABELS = {
  motion: { icon: "🚶", active: "Motion detected", idle: "No motion" },
  sound: { icon: "🔊", active: "Sound detected", idle: "Quiet" },
  flame: { icon: "🔥", active: "Flame detected", idle: "No flame" },
  obstacle: { icon: "🧱", active: "Obstacle", idle: "Clear" },
  rain: { icon: "🌧️", active: "Rain", idle: "Dry" },
  vibration: { icon: "📳", active: "Vibration", idle: "Still" },
};

export function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString();
}

export function sensorLabels(kind) {
  return LABELS[kind] ?? { icon: "📟", active: "Active", idle: "Idle" };
}

export default function SensorCard({ sensor, mock }) {
  const l = sensorLabels(sensor.kind);
  const off = !sensor.enabled;
  const on = sensor.active && !off;
  const alert = on && sensor.kind === "flame";

  return (
    <div className={`card ${on ? "on" : ""} ${alert ? "alert" : ""} ${off ? "off" : ""}`}>
      <div className="card-head">
        <span className="icon">{l.icon}</span>
        <div>
          <h3>{sensor.name.replace("_", " ")}</h3>
          <small>GPIO {sensor.pin}</small>
        </div>
        <span className="dot" />
      </div>
      <p className="state">{off ? "Disabled" : sensor.active ? l.active : l.idle}</p>
      <p className="meta">
        {sensor.detection_count} detections
        {sensor.last_event && <> · last {formatTime(sensor.last_event.timestamp)}</>}
      </p>
      {mock && (
        <div className="sim">
          <button disabled={off} onClick={() => simulate(sensor.name, true)}>Trigger</button>
          <button disabled={off} onClick={() => simulate(sensor.name, false)}>Clear</button>
        </div>
      )}
    </div>
  );
}
