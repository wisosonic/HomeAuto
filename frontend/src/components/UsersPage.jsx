import { useCallback, useEffect, useState } from "react";
import {
  createRole, createUser, deleteRole, deleteUser, getPermissions, getRoles, getUsers, updateRole, updateUser,
} from "../api.js";
import { confirmDialog, notify, promptDialog } from "../notify.js";
import PasswordInput from "./PasswordInput.jsx";

/** Run an admin action, then refresh. Errors from the server are shown as toasts. */
function useAction(reload) {
  return useCallback(
    async (fn, success) => {
      try {
        await fn();
        if (success) notify.success(success);
        await reload();
        return true;
      } catch (e) {
        notify.error(e.message);
        return false;
      }
    },
    [reload]
  );
}

function UsersPanel({ me, users, roles, reload }) {
  const run = useAction(reload);
  const [form, setForm] = useState({ username: "", password: "", role: "viewer" });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const add = async (e) => {
    e.preventDefault();
    const ok = await run(() => createUser(form.username, form.password, form.role), `User ${form.username} created`);
    if (ok) setForm((f) => ({ ...f, username: "", password: "" }));
  };

  const resetPassword = async (u) => {
    const pw = await promptDialog({
      title: `New password for ${u.username}`,
      text: "Their current sessions will be signed out.",
      label: "At least 8 characters",
      inputType: "password",
      confirmText: "Set password",
    });
    if (pw) run(() => updateUser(u.username, { password: pw }), `Password for ${u.username} changed`);
  };

  const remove = async (u) => {
    const ok = await confirmDialog({
      title: `Delete ${u.username}?`,
      text: "The account and its sessions are removed.",
      confirmText: "Yes, delete",
      danger: true,
    });
    if (ok) run(() => deleteUser(u.username), `User ${u.username} deleted`);
  };

  return (
    <section className="panel">
      <h2>Users</h2>
      <table className="table">
        <thead>
          <tr><th>User</th><th>Role</th><th>Active</th><th /></tr>
        </thead>
        <tbody>
          {users.map((u) => {
            const self = u.username === me.username;
            return (
              <tr key={u.id} className={u.active ? "" : "off"}>
                <td>
                  <strong>{u.username}</strong>
                  {self && <span className="tag"> you</span>}
                </td>
                <td>
                  <select value={u.role} onChange={(e) => run(() => updateUser(u.username, { role: e.target.value }), `${u.username} is now ${e.target.value}`)} aria-label={`Role of ${u.username}`}>
                    {roles.map((r) => <option key={r.name}>{r.name}</option>)}
                  </select>
                </td>
                <td>
                  <label className="switch" title={u.active ? "Disable account" : "Enable account"}>
                    <input
                      type="checkbox"
                      role="switch"
                      checked={u.active}
                      onChange={() => run(() => updateUser(u.username, { active: !u.active }), `${u.username} ${u.active ? "disabled" : "enabled"}`)}
                      aria-label={`${u.active ? "Disable" : "Enable"} ${u.username}`}
                    />
                    <span className="slider" />
                  </label>
                </td>
                <td className="actions">
                  <button className="btn" onClick={() => resetPassword(u)}>Reset password</button>
                  <button className="btn danger" onClick={() => remove(u)} disabled={self} title={self ? "You cannot delete yourself" : ""}>
                    Delete
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h3>Add user</h3>
      <form className="inline-form" onSubmit={add}>
        <input placeholder="username" value={form.username} onChange={set("username")} autoComplete="off" required aria-label="Username" />
        <PasswordInput placeholder="password (8+ characters)" value={form.password} onChange={set("password")} autoComplete="new-password" minLength={8} required aria-label="Password" />
        <select value={form.role} onChange={set("role")} aria-label="Role">
          {roles.map((r) => <option key={r.name}>{r.name}</option>)}
        </select>
        <button className="btn primary">Add user</button>
      </form>
    </section>
  );
}

function PermissionBoxes({ perms, value, onChange, disabled }) {
  const toggle = (name) => onChange(value.includes(name) ? value.filter((p) => p !== name) : [...value, name]);
  return (
    <div className="perm-grid">
      {perms.map((p) => (
        <label key={p.name} title={p.description} className={disabled ? "dim" : ""}>
          <input type="checkbox" checked={value.includes(p.name)} disabled={disabled} onChange={() => toggle(p.name)} />
          <span>
            <code>{p.name}</code>
            <small>{p.description}</small>
          </span>
        </label>
      ))}
    </div>
  );
}

function RoleCard({ role, perms, canEdit, run }) {
  const [draft, setDraft] = useState(role.permissions);
  useEffect(() => setDraft(role.permissions), [role.permissions]);
  const dirty = draft.slice().sort().join() !== role.permissions.join();
  const readOnly = !canEdit || role.locked;

  const remove = async () => {
    const ok = await confirmDialog({ title: `Delete role ${role.name}?`, confirmText: "Yes, delete", danger: true });
    if (ok) run(() => deleteRole(role.name), `Role ${role.name} deleted`);
  };

  return (
    <li className="role">
      <div className="row">
        <strong>{role.name}</strong>
        {role.builtin && <span className="tag">built-in</span>}
        {role.locked && <span className="tag">always full access</span>}
        <small>{role.users} user{role.users === 1 ? "" : "s"}</small>
        <span className="spacer" />
        {canEdit && !role.locked && (
          <>
            <button className="btn primary" disabled={!dirty} onClick={() => run(() => updateRole(role.name, draft), `Role ${role.name} saved`)}>
              Save
            </button>
            {!role.builtin && (
              <button className="btn danger" onClick={remove} disabled={role.users > 0} title={role.users > 0 ? "Still assigned to users" : ""}>
                Delete
              </button>
            )}
          </>
        )}
      </div>
      <PermissionBoxes perms={perms} value={draft} onChange={setDraft} disabled={readOnly} />
    </li>
  );
}

function RolesPanel({ roles, perms, canEdit, reload }) {
  const run = useAction(reload);
  const [name, setName] = useState("");
  const [draft, setDraft] = useState(["sensors.view"]);

  const add = async (e) => {
    e.preventDefault();
    const ok = await run(() => createRole(name, draft), `Role ${name} created`);
    if (ok) {
      setName("");
      setDraft(["sensors.view"]);
    }
  };

  return (
    <section className="panel">
      <h2>Roles and permissions</h2>
      <p className="hint">
        A user has one role, and the role decides what they can see and do. Changes apply immediately.
        {!canEdit && " You can view roles but not change them."}
      </p>
      <ul className="roles">
        {roles.map((r) => <RoleCard key={r.name} role={r} perms={perms} canEdit={canEdit} run={run} />)}
      </ul>
      {canEdit && (
        <>
          <h3>New role</h3>
          <form className="stack" onSubmit={add}>
            <input placeholder="role name (e.g. guest)" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" required aria-label="Role name" />
            <PermissionBoxes perms={perms} value={draft} onChange={setDraft} />
            <button className="btn primary" disabled={!name}>Create role</button>
          </form>
        </>
      )}
    </section>
  );
}

export default function UsersPage({ me, can }) {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [perms, setPerms] = useState([]);
  const canUsers = can("users.manage");

  const reload = useCallback(async () => {
    const [r, p, u] = await Promise.all([getRoles(), getPermissions(), canUsers ? getUsers() : []]);
    setRoles(r);
    setPerms(p);
    setUsers(u);
  }, [canUsers]);

  useEffect(() => {
    reload().catch((e) => notify.error(e.message));
  }, [reload]);

  return (
    <>
      {canUsers && <UsersPanel me={me} users={users} roles={roles} reload={reload} />}
      <RolesPanel roles={roles} perms={perms} canEdit={can("roles.manage")} reload={reload} />
    </>
  );
}
