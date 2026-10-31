import { createContext, useContext } from "react";
import type { Workspace } from "./types";
export type AppContextType = {
  workspace: Workspace;
  path: (p: string) => string;
  notify: (message: string, tone?: string) => void;
  go: (page: string, id?: string) => void;
  refresh: () => void;
  epoch: number;
};
export const AppContext = createContext<AppContextType>(null!);
export const useApp = () => useContext(AppContext);
