import { create } from "zustand";
import { devtools } from "zustand/middleware";
import * as api from "../services/api/config";

export interface ConfigState {
  doc: any | null;
  loading: boolean;
  message?: string;
  error?: string;
  dirty: boolean;
  load: () => Promise<void>;
  save: () => Promise<void>;
  setAt: (path: string, value: unknown) => void;
  getAt: <T = unknown>(path: string, defaultValue?: T) => T | undefined;
}

function setByPath(obj: any, path: string, value: unknown) {
  const parts = path.split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i]!;
    if (typeof cur[key] !== "object" || cur[key] === null) cur[key] = {};
    cur = cur[key];
  }
  cur[parts[parts.length - 1]!] = value;
}

function getByPath<T = unknown>(obj: any, path: string, defaultValue?: T): T | undefined {
  if (!obj) return defaultValue;
  const parts = path.split(".");
  let cur = obj as any;
  for (const p of parts) {
    if (cur == null) return defaultValue;
    cur = cur[p];
  }

  return (cur as T) ?? defaultValue;
}

export const useConfigStore = create<ConfigState>()(
  devtools((set, get) => ({
    doc: null,
    loading: false,
    dirty: false,
    async load() {
      set({ loading: true });
      try {
        const doc = await api.getConfig();
        set({ doc, loading: false, message: undefined, error: undefined, dirty: false });
      } catch (e: any) {
        set({ error: e?.message ?? String(e), loading: false });
      }
    },
    async save() {
      set({ loading: true });
      try {
        const wasDirty = get().dirty;
        const res = await api.putConfig(get().doc?.data ?? {});
        set({ message: wasDirty ? res.message : undefined, loading: false, dirty: false });
      } catch (e: any) {
        set({ error: e?.message ?? String(e), loading: false });
      }
    },
    setAt(path, value) {
      const draft = JSON.parse(JSON.stringify(get().doc ?? { data: {} }));
      setByPath(draft, path, value);
      set({ doc: draft, dirty: true });
    },
    getAt(path, defaultValue) {
      return getByPath(get().doc, path, defaultValue);
    },
  }))
); 