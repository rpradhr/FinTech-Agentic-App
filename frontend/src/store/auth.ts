import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  userId: string | null;
  roles: string[];
  setAuth: (token: string, userId: string, roles: string[]) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      userId: null,
      roles: [],
      setAuth: (token, userId, roles) => {
        localStorage.setItem("access_token", token);
        set({ token, userId, roles });
      },
      logout: () => {
        localStorage.removeItem("access_token");
        set({ token: null, userId: null, roles: [] });
      },
      isAuthenticated: () => !!get().token,
    }),
    { name: "auth-store" }
  )
);
