import { useState } from "react";
import { changePassword } from "../api.js";
import { notify } from "../notify.js";

export default function AccountPage({ user }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [again, setAgain] = useState("");
  const [busy, setBusy] = useState(false);

  const mismatch = again !== "" && next !== again;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await changePassword(current, next);
      notify.success("Password changed. Your other sessions were signed out.");
      setCurrent("");
      setNext("");
      setAgain("");
    } catch (err) {
      notify.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <h2>Account</h2>
      <p className="hint">
        Signed in as <strong>{user.username}</strong> with the role <strong>{user.role}</strong>.
      </p>
      <p className="perm-list">
        {user.permissions.map((p) => (
          <span key={p} className="tag">{p}</span>
        ))}
      </p>

      <h3>Change password</h3>
      <form className="stack" onSubmit={submit}>
        <label>
          Current password
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
        </label>
        <label>
          New password <small>(8 to 128 characters)</small>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" minLength={8} required />
        </label>
        <label>
          Repeat new password
          <input type="password" value={again} onChange={(e) => setAgain(e.target.value)} autoComplete="new-password" required />
        </label>
        {mismatch && <p className="form-error">The passwords do not match.</p>}
        <button className="btn primary" disabled={busy || mismatch || !current || next.length < 8 || !again}>
          Change password
        </button>
      </form>
    </section>
  );
}
