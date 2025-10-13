import { create } from 'zustand';
import { call, on } from '../lib/rpc';

export interface RunStatus {
  running: boolean;
  paused: boolean;
  current_task?: string;
  message?: string;
  progress?: {
    current: number;
    total: number;
  };
}

interface RunState {
  status: RunStatus;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchStatus: () => Promise<void>;
  startAll: () => Promise<void>;
  stopAll: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  togglePause: () => Promise<void>;
}

export const useRunStore = create<RunState>((set, get) => {
  // 订阅运行状态通知
  on('status/run', (data: RunStatus) => {
    set({ status: data });
  });

  return {
    status: {
      running: false,
      paused: false,
    },
    loading: false,
    error: null,

    fetchStatus: async () => {
      try {
        set({ loading: true, error: null });
        const status = await call<RunStatus>('engine.status');
        set({ status, loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    startAll: async () => {
      try {
        set({ loading: true, error: null });
        await call('engine.start_all');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    stopAll: async () => {
      try {
        set({ loading: true, error: null });
        await call('engine.stop_all');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    pause: async () => {
      try {
        set({ loading: true, error: null });
        await call('engine.pause');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    resume: async () => {
      try {
        set({ loading: true, error: null });
        await call('engine.resume');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    togglePause: async () => {
      try {
        set({ loading: true, error: null });
        await call('engine.toggle_pause');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },
  };
});

