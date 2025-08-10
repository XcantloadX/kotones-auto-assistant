import { create } from "zustand";
import { devtools } from "zustand/middleware";
import * as runApi from "../services/api/run";
import * as cfgApi from "../services/api/config";

export interface RunState {
  tasks: runApi.TaskRow[];
  quick: cfgApi.QuickSettings;
  endAction: cfgApi.EndAction;
  loading: boolean;
  error?: string;
  isRunning: boolean;
  isPaused: boolean;
  isStopping: boolean;
  refresh: () => Promise<void>;
  toggleRun: () => Promise<void>;
  togglePause: () => Promise<void>;
  setQuick: (patch: Partial<cfgApi.QuickSettings>) => Promise<void>;
  saveEndAction: (action: cfgApi.EndAction) => Promise<void>;
}

const defaultQuick: cfgApi.QuickSettings = {
  purchase: false,
  assignment: false,
  contest: false,
  produce: false,
  mission_reward: false,
  club_reward: false,
  activity_funds: false,
  presents: false,
  capsule_toys: false,
  upgrade_support_card: false,
};

function deriveQuickAndEndAction(confDoc: any): { quick: cfgApi.QuickSettings; endAction: cfgApi.EndAction } {
  const user = confDoc?.data?.user_configs?.[0];
  const opts = user?.options ?? {};
  const q: cfgApi.QuickSettings = {
    purchase: !!opts.purchase?.enabled,
    assignment: !!opts.assignment?.enabled,
    contest: !!opts.contest?.enabled,
    produce: !!opts.produce?.enabled,
    mission_reward: !!opts.mission_reward?.enabled,
    club_reward: !!opts.club_reward?.enabled,
    activity_funds: !!opts.activity_funds?.enabled,
    presents: !!opts.presents?.enabled,
    capsule_toys: !!opts.capsule_toys?.enabled,
    upgrade_support_card: !!opts.upgrade_support_card?.enabled,
  };
  let endAction: cfgApi.EndAction = "DO_NOTHING";
  if (opts?.end_game?.shutdown) endAction = "SHUTDOWN";
  else if (opts?.end_game?.hibernate) endAction = "HIBERNATE";
  return { quick: q, endAction };
}

export const useRunStore = create<RunState>()(
  devtools((set, get) => ({
    tasks: [],
    quick: defaultQuick,
    endAction: "DO_NOTHING",
    loading: false,
    isRunning: false,
    isPaused: false,
    isStopping: false,
    async refresh() {
      set({ loading: true });
      try {
        const [state, tasks, conf] = await Promise.all([
          runApi.getRunState(),
          runApi.getTasks(),
          cfgApi.getConfig(),
        ]);
        const { quick, endAction } = deriveQuickAndEndAction(conf);
        set({
          tasks,
          quick,
          endAction,
          isRunning: state.is_running,
          isPaused: state.is_paused,
          isStopping: state.is_stopping,
          loading: false,
        });
      } catch (e: any) {
        set({ error: e?.message ?? String(e), loading: false });
      }
    },
    async toggleRun() {
      set({ loading: true });
      try {
        const state = await runApi.postRunToggle();
        const tasks = await runApi.getTasks();
        set({
          isRunning: state.is_running,
          isPaused: state.is_paused,
          isStopping: state.is_stopping,
          tasks,
          loading: false,
        });
      } catch (e: any) {
        set({ error: e?.message ?? String(e), loading: false });
      }
    },
    async togglePause() {
      set({ loading: true });
      try {
        const state = await runApi.postRunPauseToggle();
        set({
          isRunning: state.is_running,
          isPaused: state.is_paused,
          isStopping: state.is_stopping,
          loading: false,
        });
      } catch (e: any) {
        set({ error: e?.message ?? String(e), loading: false });
      }
    },
    async setQuick(patch) {
      try {
        const next = await cfgApi.patchQuick(patch);
        set({ quick: next });
      } catch (e: any) {
        set({ error: e?.message ?? String(e) });
      }
    },
    async saveEndAction(action) {
      try {
        await cfgApi.putEndAction(action);
        set({ endAction: action });
      } catch (e: any) {
        set({ error: e?.message ?? String(e) });
      }
    },
  }))
); 