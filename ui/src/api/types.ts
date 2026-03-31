// TypeScript types mirroring Python config models

export type BackendType = 'custom' | 'mumu12' | 'mumu12v5' | 'leidian' | 'dmm';
export type DeviceRecipes = 'adb' | 'uiautomator2' | 'windows' | 'remote_windows' | 'nemu_ipc' | 'windows_background';

export interface BackendConfig {
  type: BackendType;
  instance_id: string | null;
  adb_ip: string;
  adb_port: number;
  adb_emulator_name: string | null;
  screenshot_impl: DeviceRecipes;
  check_emulator: boolean;
  emulator_path: string | null;
  emulator_args: string;
  windows_window_title: string;
  windows_ahk_path: string | null;
  mumu_background_mode: boolean;
  target_screenshot_interval: number | null;
  cursor_wait_speed: number;
}

export interface UserConfig {
  name: string;
  id: string;
  category: string;
  description: string;
  backend: BackendConfig;
  keep_screenshots: boolean;
  options: AppOptions;
}

export interface PurchaseConfig {
  enabled: boolean;
  money_enabled: boolean;
  money_items: number[];
  money_refresh: boolean;
  ap_enabled: boolean;
  ap_items: number[];
  weekly_enabled: boolean;
}

export interface ActivityFundsConfig {
  enabled: boolean;
}

export interface PresentsConfig {
  enabled: boolean;
}

export interface AssignmentConfig {
  enabled: boolean;
  mini_live_reassign_enabled: boolean;
  mini_live_duration: 4 | 6 | 12;
  online_live_reassign_enabled: boolean;
  online_live_duration: 4 | 6 | 12;
}

export interface ContestConfig {
  enabled: boolean;
  select_which_contestant: 1 | 2 | 3;
  when_no_set: 'remind' | 'wait' | 'auto_set' | 'auto_set_silent';
}

export interface ProduceConfig {
  enabled: boolean;
  selected_solution_id: string | null;
  produce_count: number;
  produce_timeout_cd: number;
  interrupt_timeout: number;
  enable_fever_month: 'on' | 'off' | 'ignore';
}

export interface MissionRewardConfig {
  enabled: boolean;
}

export interface ClubRewardConfig {
  enabled: boolean;
  selected_note: number;
}

export interface StartGameConfig {
  enabled: boolean;
  disable_gakumas_localify: boolean;
  dmm_game_path: string | null;
  dmm_bypass: boolean;
  start_through_kuyo: boolean;
  game_package_name: string;
}

export interface EndGameConfig {
  exit_kaa: boolean;
  kill_game: boolean;
  kill_dmm: boolean;
  kill_emulator: boolean;
  shutdown: boolean;
  hibernate: boolean;
  restore_gakumas_localify: boolean;
}

export interface IdleConfig {
  enabled: boolean;
  idle_seconds: number;
  minimize_on_pause: boolean;
}

export interface MiscConfig {
  check_update: 'never' | 'startup';
  auto_install_update: boolean;
  expose_to_lan: boolean;
  update_channel: 'release' | 'beta';
  log_level: 'debug' | 'verbose';
}

export interface TraceConfig {
  recommend_card_detection: boolean;
}

export interface CapsuleToysConfig {
  enabled: boolean;
}

export interface UpgradeSupportCardConfig {
  enabled: boolean;
}

export interface AppOptions {
  purchase: PurchaseConfig;
  activity_funds: ActivityFundsConfig;
  presents: PresentsConfig;
  assignment: AssignmentConfig;
  contest: ContestConfig;
  produce: ProduceConfig;
  mission_reward: MissionRewardConfig;
  club_reward: ClubRewardConfig;
  start_game: StartGameConfig;
  end_game: EndGameConfig;
  idle: IdleConfig;
  misc: MiscConfig;
  trace: TraceConfig;
  capsule_toys: CapsuleToysConfig;
  upgrade_support_card: UpgradeSupportCardConfig;
}

export interface ProduceSolution {
  id: string;
  name: string;
  description: string | null;
  data: ProduceData;
}

export interface ProduceData {
  mode: 'regular' | 'pro' | 'master';
  idol: string | null;
  memory_set: number | null;
  support_card_set: number | null;
  auto_set_memory: boolean;
  auto_set_support_card: boolean;
  use_pt_boost: boolean;
  use_note_boost: boolean;
  follow_producer: boolean;
  self_study_lesson: 'dance' | 'visual' | 'vocal';
  prefer_lesson_ap: boolean;
  battle_strategy: 'bandai' | 'expert';
  actions_order: string[];
  recommend_card_detection_mode: 'normal' | 'strict';
  use_ap_drink: boolean;
  skip_commu: boolean;
}

export interface TaskStatus {
  name: string;
  status: string;
}

export interface RunStatus {
  text: string;
  interactive: boolean;
}

export interface VersionsData {
  installed_version: string | null;
  latest: string | null;
  launcher_version: string | null;
  versions: string[];
}

export interface IdolCard {
  skin_id: string;
  name: string;
  is_another: boolean;
  another_name: string | null;
}

export interface EmulatorInstance {
  id: string;
  display_name: string;
}

// RPC method signatures
export interface KaaApi {
  // App info
  'app.getVersion': () => Promise<string>;
  'app.getUpgradeMessage': () => Promise<string | null>;

  // Task control
  'task.startAll': () => Promise<void>;
  'task.startSingle': (params: { task_name: string }) => Promise<void>;
  'task.stopAll': () => Promise<void>;
  'task.togglePause': () => Promise<boolean | null>;
  'task.getRunStatus': () => Promise<RunStatus>;
  'task.getPauseStatus': () => Promise<{ text: string; interactive: boolean }>;
  'task.getStatuses': () => Promise<TaskStatus[]>;
  'task.getRuntime': () => Promise<string>;
  'task.getAllNames': () => Promise<string[]>;

  // Configuration
  'config.get': () => Promise<UserConfig>;
  'config.save': (params: { options?: Partial<AppOptions>; backend?: Partial<BackendConfig> }) => Promise<void>;
  'config.getEmulatorInstances': (params: { type: string }) => Promise<EmulatorInstance[]>;

  // Produce solutions
  'produce.listSolutions': () => Promise<ProduceSolution[]>;
  'produce.getSolution': (params: { id: string }) => Promise<ProduceSolution>;
  'produce.createSolution': (params: { name: string }) => Promise<ProduceSolution>;
  'produce.deleteSolution': (params: { id: string }) => Promise<void>;
  'produce.saveSolution': (params: { solution: ProduceSolution }) => Promise<void>;

  // Update
  'update.listVersions': () => Promise<VersionsData>;
  'update.installVersion': (params: { version: string }) => Promise<void>;

  // Feedback
  'feedback.createReport': (params: { title: string; description: string; upload: boolean }) => Promise<string>;

  // Telemetry
  'telemetry.isEnabled': () => Promise<boolean>;
  'telemetry.enable': () => Promise<void>;
  'telemetry.disable': () => Promise<void>;

  // Idol cards
  'idol.getAll': () => Promise<IdolCard[]>;
}

// WebSocket events emitted by server
export interface ServerEvents {
  'task.started': void;
  'task.stopped': { reason: string };
  'task.statusChanged': { name: string; status: string };
  'task.runtime': { runtime: string };
}
