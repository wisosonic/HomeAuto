import { useCallback, useEffect, useMemo, useState } from "react";
import { getMe, login as apiLogin, logout as apiLogout, setToken, setUnauthorizedHandler } from "./api.js";
import { notify } from "./notify.js";

const KEY = "homeauto.token";

// localStorage can throw (private mode, blocked storage): the app then just asks to sign in each time.
const store = {
  get: () => {
    try {
      return localStorage.getItem(KEY);
    } catch {
      return null;
    }
  },
  set: (v) => {
    try {
      v ? localStorage.setItem(KEY, v) : localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  },
};

/** Login state: the current user (with permissions) and the session token. */
export function useAuth() {
  const [token, setTok] = useState(() => store.get());
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false); // false while a stored token is being checked

  const clear = useCallback(() => {
    setToken(null);
    store.set(null);
    setTok(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      clear();
      notify.warning("Your session has ended, please sign in again");
    });
  }, [clear]);

  useEffect(() => {
    if (!token) return setReady(true);
    if (user) return;
    setToken(token);
    getMe()
      .then(setUser)
      .catch(() => clear()) // expired or revoked
      .finally(() => setReady(true));
  }, [token, user, clear]);

  const login = useCallback(async (username, password) => {
    const res = await apiLogin(username, password);
    setToken(res.token);
    store.set(res.token);
    setUser(res.user);
    setTok(res.token);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      /* the token may already be dead; log out locally anyway */
    }
    clear();
  }, [clear]);

  const can = useMemo(() => {
    const set = new Set(user?.permissions ?? []);
    return (perm) => set.has(perm);
  }, [user]);

  return { user, token, ready, login, logout, can, clear };
}
