import { create } from 'zustand';
import type { TaskStatus } from '../api/types';

interface AppState {
  // Task state
  taskStatuses: TaskStatus[];
  taskRuntime: string;
  isRunningAll: boolean;
  isStopping: boolean;
  isPaused: boolean;

  // Navigation
  activeTab: string;

  // Setters
  setTaskStatuses: (statuses: TaskStatus[]) => void;
  setTaskRuntime: (runtime: string) => void;
  setIsRunningAll: (v: boolean) => void;
  setIsStopping: (v: boolean) => void;
  setIsPaused: (v: boolean) => void;
  setActiveTab: (tab: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  taskStatuses: [],
  taskRuntime: '未运行',
  isRunningAll: false,
  isStopping: false,
  isPaused: false,
  activeTab: 'status',

  setTaskStatuses: (taskStatuses) => set({ taskStatuses }),
  setTaskRuntime: (taskRuntime) => set({ taskRuntime }),
  setIsRunningAll: (isRunningAll) => set({ isRunningAll }),
  setIsStopping: (isStopping) => set({ isStopping }),
  setIsPaused: (isPaused) => set({ isPaused }),
  setActiveTab: (activeTab) => set({ activeTab }),
}));
