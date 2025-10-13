import { create } from 'zustand';
import { call, on } from '../lib/rpc';

export interface Task {
  name: string;
  display_name: string;
  description?: string;
  enabled: boolean;
}

export interface TaskStatus {
  name: string;
  running: boolean;
  message?: string;
}

interface TaskState {
  tasks: Task[];
  currentTask: TaskStatus | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchTasks: () => Promise<void>;
  startTask: (name: string) => Promise<void>;
  stopTask: () => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => {
  // 订阅任务状态通知
  on('status/task', (data: TaskStatus) => {
    set({ currentTask: data });
  });

  return {
    tasks: [],
    currentTask: null,
    loading: false,
    error: null,

    fetchTasks: async () => {
      try {
        set({ loading: true, error: null });
        const tasks = await call<Task[]>('task.list');
        set({ tasks, loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    startTask: async (name: string) => {
      try {
        set({ loading: true, error: null });
        await call('task.start', { name });
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },

    stopTask: async () => {
      try {
        set({ loading: true, error: null });
        await call('task.stop');
        set({ loading: false });
      } catch (err: any) {
        set({ error: err.message, loading: false });
        throw err;
      }
    },
  };
});

