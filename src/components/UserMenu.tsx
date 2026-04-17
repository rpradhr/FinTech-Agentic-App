import { useState } from "react";
import { auth, endpoints } from "@/lib/api";
import { LogIn, LogOut, UserCircle2 } from "lucide-react";
import { toast } from "sonner";

const ROLE_PRESETS: { label: string; user_id: string; roles: string[] }[] = [
  { label: "Fraud Analyst", user_id: "analyst-1", roles: ["fraud_analyst"] },
  { label: "Underwriter", user_id: "uw-1", roles: ["underwriter"] },
  { label: "Advisor", user_id: "adv-1", roles: ["advisor"] },
  { label: "Branch Manager", user_id: "bm-1", roles: ["branch_manager"] },
  { label: "Admin", user_id: "admin-1", roles: ["admin"] },
];

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState(auth.getUser());

  const login = async (preset: (typeof ROLE_PRESETS)[number]) => {
    try {
      await endpoints.devLogin(preset.user_id, preset.roles);
      setUser({ user_id: preset.user_id, roles: preset.roles });
      setOpen(false);
      toast.success(`Signed in as ${preset.label}`);
    } catch (e) {
      toast.error(`Login failed: ${(e as Error).message}`);
    }
  };

  const logout = () => {
    auth.clearToken();
    setUser(null);
    setOpen(false);
    toast.message("Signed out");
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="m3-state inline-flex items-center gap-2 rounded-full bg-surface-container-high px-3 py-1.5 text-sm font-medium text-on-surface"
      >
        <UserCircle2 className="h-5 w-5" />
        <span className="hidden sm:inline">{user?.user_id ?? "Sign in"}</span>
      </button>
      {open && (
        <div className="absolute right-0 top-12 z-40 w-64 rounded-2xl border border-outline-variant bg-surface-container-high p-2 m3-elev-3">
          {user ? (
            <>
              <div className="px-3 py-2 text-xs text-on-surface-variant">
                <div className="font-semibold text-on-surface">{user.user_id}</div>
                <div>{user.roles.join(", ") || "no roles"}</div>
              </div>
              <button
                onClick={logout}
                className="m3-state flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-on-surface"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </>
          ) : (
            <>
              <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
                Dev sign-in
              </div>
              {ROLE_PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => login(p)}
                  className="m3-state flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-on-surface"
                >
                  <LogIn className="h-4 w-4" />
                  {p.label}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
