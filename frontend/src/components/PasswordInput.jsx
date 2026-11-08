import { useState } from "react";

/** Password input with a show/hide (eye) toggle. Accepts the usual <input> props. */
export default function PasswordInput(props) {
  const [visible, setVisible] = useState(false);
  const label = visible ? "Hide password" : "Show password";
  return (
    <span className="pw-field">
      <input {...props} type={visible ? "text" : "password"} />
      <button type="button" className="pw-toggle" onClick={() => setVisible((v) => !v)} aria-label={label} title={label} aria-pressed={visible}>
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
          <circle cx="12" cy="12" r="3" />
          {visible && <path d="M3 3l18 18" />}
        </svg>
      </button>
    </span>
  );
}
