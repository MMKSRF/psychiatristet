import { create } from "zustand";
import { jwtDecode } from "jwt-decode";

const storageKey = "carebridge-token";

function readSession() {
  const token = localStorage.getItem(storageKey);
  if (!token) return { token: null, user: null };
  try {
    const claims = jwtDecode(token);
    if (!claims.exp || claims.exp * 1000 <= Date.now()) throw new Error("Session expired");
    return {
      token,
      user: {
        username: claims.sub,
        role: claims.role,
        psychiatrist_id: claims.psychiatrist_id ?? null,
      },
    };
  } catch {
    localStorage.removeItem(storageKey);
    return { token: null, user: null };
  }
}

export const useSession = create((set) => ({
  ...readSession(),
  setSession: (token, user) => {
    localStorage.setItem(storageKey, token);
    set({ token, user });
  },
  clearSession: () => {
    localStorage.removeItem(storageKey);
    set({ token: null, user: null });
  },
}));

if (typeof window !== "undefined") {
  window.addEventListener("carebridge:unauthorized", () => useSession.getState().clearSession());
}
