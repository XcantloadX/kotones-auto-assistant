import { create } from 'zustand';
import { call } from '../lib/rpc';

export interface ProduceConfig {
  id: string;
  name: string;
  data: any;
  created_at?: string;
  updated_at?: string;
}

interface ProduceState {
  configs: ProduceConfig[];
  currentConfig: ProduceConfig | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchConfigs: () => Promise<void>;
  fetchConfig: (id: string) => Promise<void>;
  createConfig: (name: string) => Promise<void>;
  updateConfig: (id: string, data: any) => Promise<void>;
  deleteConfig: (id: string) => Promise<void>;
}

export const useProduceStore = create<ProduceState>((set, get) => ({
  configs: [],
  currentConfig: null,
  loading: false,
  error: null,

  fetchConfigs: async () => {
    try {
      set({ loading: true, error: null });
      const configs = await call<ProduceConfig[]>('produce.list');
      set({ configs, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  fetchConfig: async (id: string) => {
    try {
      set({ loading: true, error: null });
      const config = await call<ProduceConfig>('produce.read', { id });
      set({ currentConfig: config, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  createConfig: async (name: string) => {
    try {
      set({ loading: true, error: null });
      const config = await call<ProduceConfig>('produce.create', { name });
      set({ loading: false });
      await get().fetchConfigs();
      return config;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  updateConfig: async (id: string, data: any) => {
    try {
      set({ loading: true, error: null });
      await call('produce.update', { id, data });
      set({ loading: false });
      await get().fetchConfigs();
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  deleteConfig: async (id: string) => {
    try {
      set({ loading: true, error: null });
      await call('produce.delete', { id });
      set({ loading: false });
      await get().fetchConfigs();
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },
}));

