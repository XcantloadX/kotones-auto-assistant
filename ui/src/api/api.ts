import { call } from './client';
import type {
  RunStatus,
  TaskStatus,
  UserConfig,
  AppOptions,
  BackendConfig,
  EmulatorInstance,
  ProduceSolution,
  VersionsData,
  IdolCard,
} from './types';

// Typed wrapper around the RPC client
export const api = {
  app: {
    getVersion: () => call<string>('app.getVersion'),
    getUpgradeMessage: () => call<string | null>('app.getUpgradeMessage'),
  },

  task: {
    startAll: () => call<void>('task.startAll'),
    startSingle: (task_name: string) => call<void>('task.startSingle', { task_name }),
    stopAll: () => call<void>('task.stopAll'),
    togglePause: () => call<boolean | null>('task.togglePause'),
    getRunStatus: () => call<RunStatus>('task.getRunStatus'),
    getPauseStatus: () => call<{ text: string; interactive: boolean }>('task.getPauseStatus'),
    getStatuses: () => call<TaskStatus[]>('task.getStatuses'),
    getRuntime: () => call<string>('task.getRuntime'),
    getAllNames: () => call<string[]>('task.getAllNames'),
  },

  config: {
    get: () => call<UserConfig>('config.get'),
    save: (params: { options?: Partial<AppOptions>; backend?: Partial<BackendConfig> }) =>
      call<void>('config.save', params as Record<string, unknown>),
    saveField: (path: string, value: unknown) =>
      call<void>('config.saveField', { path, value } as Record<string, unknown>),
    getEmulatorInstances: (type: string) =>
      call<EmulatorInstance[]>('config.getEmulatorInstances', { type }),
  },

  produce: {
    listSolutions: () => call<ProduceSolution[]>('produce.listSolutions'),
    getSolution: (id: string) => call<ProduceSolution>('produce.getSolution', { id }),
    createSolution: (name: string) => call<ProduceSolution>('produce.createSolution', { name }),
    deleteSolution: (id: string) => call<void>('produce.deleteSolution', { id }),
    saveSolution: (solution: ProduceSolution) =>
      call<void>('produce.saveSolution', { solution: solution as unknown as Record<string, unknown> }),
  },

  update: {
    listVersions: () => call<VersionsData>('update.listVersions'),
    installVersion: (version: string) => call<void>('update.installVersion', { version }),
  },

  feedback: {
    createReport: (title: string, description: string, upload: boolean) =>
      call<string>('feedback.createReport', { title, description, upload }),
  },

  telemetry: {
    isEnabled: () => call<boolean>('telemetry.isEnabled'),
    enable: () => call<void>('telemetry.enable'),
    disable: () => call<void>('telemetry.disable'),
  },

  idol: {
    getAll: () => call<IdolCard[]>('idol.getAll'),
  },
};
