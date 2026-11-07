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

export default function SensorCard({ sensor, mock }) {
  const l = LABELS[sensor.kind] ?? { icon: "📟", active: "Active", idle: "Idle" };
  const alert = sensor.active && sensor.kind === "flame";

  return (
    <div className={`card ${sensor.active ? "on" : ""} ${alert ? "alert" : ""}`}>
      <div className="card-head">
        <span className="icon">{l.icon}</span>
        <div>
          <h3>{sensor.name.replace("_", " ")}</h3>
          <small>GPIO {sensor.pin}</small>
        </div>
        <span className="dot" />
      </div>
      <p className="state">{sensor.active ? l.active : l.idle}</p>
      <p className="meta">
        {sensor.detection_count} detections
        {sensor.last_event && <> · last {formatTime(sensor.last_event.timestamp)}</>}
      </p>
      {mock && (
        <div className="sim">
          <button onClick={() => simulate(sensor.name, true)}>Trigger</button>
          <button onClick={() => simulate(sensor.name, false)}>Clear</button>
        </div>
      )}
    </div>
  );
}
