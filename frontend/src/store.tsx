import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface AppState {
  /** Bumps whenever a new analysis run is loaded, so pages refetch. */
  version: number;
  refresh: () => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const value = useMemo(() => ({ version, refresh }), [version, refresh]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
