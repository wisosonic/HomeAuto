import { useCallback, useEffect, useState } from "react";
import { createSchedule, deleteSchedule, getSchedules, updateSchedule } from "../api.js";
import { confirmDialog, notify } from "../notify.js";

const pad = (n) => String(n).padStart(2, "0");
/** epoch seconds -> value for <input type="datetime-local"> (browser local time) */
const toInput = (sec) => {
  const d = new Date(sec * 1000);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const fromInput = (v) => new Date(v).getTime() / 1000;
const fmt = (sec) =>
  new Date(sec * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });

const blankForm = () => {
  const start = Math.ceil(Date.now() / 60000) * 60;
  return { name: "", sensors: [], start: toInput(start), end: toInput(start + 3600) };
};

export default function SchedulesPage({ sensors, canManage }) {
  const [rules, setRules] = useState(null);
  const [form, setForm] = useState(blankForm);
  const [editing, setEditing] = useState(null); // rule id being edited
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    () => getSchedules().then(setRules).catch((e) => notify.error(`Could not load schedules: ${e.message}`)),
    []
  );
  useEffect(() => {
    load();
    const t = setInterval(load, 10000); // statuses change as time passes
    return () => clearInterval(t);
  }, [load]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const toggleSensor = (name) =>
    setForm((f) => ({
      ...f,
      sensors: f.sensors.includes(name) ? f.sensors.filter((s) => s !== name) : [...f.sensors, name],
    }));

  const start = fromInput(form.start);
  const end = fromInput(form.end);
  const timeError = !form.start || !form.end ? "Pick a start and an end." : end <= start ? "The end must be after the start." : "";

  const reset = () => {
    setForm(blankForm());
    setEditing(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const body = { name: form.name, sensors: form.sensors, start, end };
      if (editing) await updateSchedule(editing, body);
      else await createSchedule(body);
      notify.success(editing ? "Rule updated" : "Rule created");
      reset();
      await load();
    } catch (err) {
      notify.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  const edit = (r) => {
    setEditing(r.id);
    setForm({ name: r.name, sensors: r.sensors, start: toInput(r.start), end: toInput(r.end) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const remove = async (r) => {
    const live = r.status === "active";
    const ok = await confirmDialog({
      title: `Delete “${r.name}”?`,
      text: live
        ? "This rule is running now. Its sensors go back to their saved on/off setting immediately."
        : "This cannot be undone.",
      confirmText: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteSchedule(r.id);
      notify.success("Rule deleted");
      if (editing === r.id) reset();
      await load();
    } catch (err) {
      notify.error(err.message);
    }
  };

  const names = sensors.map((s) => s.name);

  return (
    <section className="panel">
      <h2>Schedule rules</h2>
      <p className="hint">
        Between a rule's start and end, its sensors are switched on. When the rule ends they return to the
        on/off setting they had before (the one on the Sensors page). Times use this device's time zone.
      </p>

      {canManage && (
        <form className="stack schedule-form" onSubmit={submit}>
          <h3>{editing ? "Edit rule" : "New rule"}</h3>
          <label>
            Name
            <input value={form.name} onChange={set("name")} maxLength={60} placeholder="e.g. Away this weekend" required />
          </label>
          <div className="when">
            <label>
              Starts
              <input type="datetime-local" value={form.start} onChange={set("start")} required />
            </label>
            <label>
              Ends
              <input type="datetime-local" value={form.end} onChange={set("end")} required />
            </label>
          </div>
          {timeError && <p className="form-error">{timeError}</p>}
          <fieldset className="sensor-pick">
            <legend>Sensors to enable</legend>
            {names.length === 0 && <small>Waiting for backend…</small>}
            {names.map((n) => (
              <label key={n} className="pick">
                <input type="checkbox" checked={form.sensors.includes(n)} onChange={() => toggleSensor(n)} />
                {n.replace("_", " ")}
              </label>
            ))}
          </fieldset>
          <div className="form-actions">
            <button className="btn primary" disabled={busy || !!timeError || !form.name.trim() || form.sensors.length === 0}>
              {editing ? "Save changes" : "Create rule"}
            </button>
            {editing && (
              <button type="button" className="btn" onClick={reset}>
                Cancel
              </button>
            )}
          </div>
        </form>
      )}

      <h3>Rules</h3>
      {rules === null && <p className="empty">Loading…</p>}
      {rules?.length === 0 && <p className="empty">No rules yet.</p>}
      {rules?.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Sensors</th>
                <th>Starts</th>
                <th>Ends</th>
                <th>Status</th>
                {canManage && <th />}
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id} className={r.status === "ended" ? "ended" : ""}>
                  <td>
                    {r.name}
                    <br />
                    <small className="muted">by {r.created_by}</small>
                  </td>
                  <td>
                    <span className="perm-list">
                      {r.sensors.map((s) => (
                        <span key={s} className="tag">{s.replace("_", " ")}</span>
                      ))}
                    </span>
                  </td>
                  <td>{fmt(r.start)}</td>
                  <td>{fmt(r.end)}</td>
                  <td>
                    <span className={`tag ${r.status === "active" ? "on" : ""}`}>{r.status}</span>
                  </td>
                  {canManage && (
                    <td className="row-actions">
                      {r.status !== "ended" && (
                        <button className="btn" onClick={() => edit(r)}>Edit</button>
                      )}{" "}
                      <button className="btn danger" onClick={() => remove(r)}>Delete</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
