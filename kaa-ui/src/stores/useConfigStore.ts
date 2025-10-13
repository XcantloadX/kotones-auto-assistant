import { create } from 'zustand';
import { call } from '../lib/rpc';

interface ConfigState {
  config: any | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchConfig: () => Promise<void>;
  saveConfig: (config: any) => Promise<void>;
  reloadConfig: () => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: null,
  loading: false,
  error: null,

  fetchConfig: async () => {
    try {
      set({ loading: true, error: null });
      const config = await call('config.get');
      set({ config, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  saveConfig: async (config: any) => {
    try {
      set({ loading: true, error: null });
      await call('config.save', { options: config });
      set({ config, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  reloadConfig: async () => {
    try {
      set({ loading: true, error: null });
      await call('config.reload');
      await get().fetchConfig();
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

}));

