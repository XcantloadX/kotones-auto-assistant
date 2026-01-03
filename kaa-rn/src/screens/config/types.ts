export const SETTINGS_SECTIONS = [
  {
    id: 'basic',
    label: '基本',
    icon: 'cog',
    children: [
      { id: 'basic_emulator', label: '模拟器设置' },
      { id: 'basic_launch', label: '启动游戏设置' },
      { id: 'basic_after', label: '任务结束设置' },
    ]
  },
  {
    id: 'daily',
    label: '日常',
    icon: 'calendar-check',
    children: [
      { id: 'daily_store', label: '商店购买设置' },
      { id: 'daily_work', label: '工作设置' },
      { id: 'daily_contest', label: '竞赛设置' },
      { id: 'daily_rewards', label: '奖励领取设置' },
    ]
  },
  { id: 'training', label: '培育', icon: 'school' },
  {
    id: 'misc',
    label: '杂项',
    icon: 'dots-horizontal',
    children: [
      { id: 'misc_general', label: '通用设置' },
      { id: 'misc_idle', label: '闲置挂机设置' },
      { id: 'misc_debug', label: '调试设置' },
    ]
  },
];

export const EMULATOR_TYPES = [
  { value: 'mumu12', label: 'MuMu 12' },
  { value: 'mumu12v5', label: 'MuMu 12 v5.x' },
  { value: 'leidian', label: '雷电' },
  { value: 'custom', label: '自定义' },
  { value: 'dmm', label: 'DMM' },
];

export const ANDROID_EMULATOR_VALUES = ['mumu12', 'mumu12v5', 'leidian', 'custom'];

export function isAndroidEmulator(type?: string): boolean {
  return !!type && ANDROID_EMULATOR_VALUES.includes(type);
}

export const SELECT_CONTESTANT_OPTIONS = [
  { value: 1, label: '1' },
  { value: 2, label: '2' },
  { value: 3, label: '3' },
];

export const CONTEST_WHEN_NO_SET_OPTIONS = [
  { value: 'remind', label: '提醒并跳过' },
  { value: 'wait', label: '提醒并等待手动编成' },
  { value: 'auto_set', label: '自动编成并提醒' },
  { value: 'auto_set_silent', label: '自动编成不提醒' },
];

export const FEVER_MONTH_OPTIONS = [
  { value: 'ignore', label: '不操作' },
  { value: 'on', label: '自动启用' },
  { value: 'off', label: '自动禁用' },
];

export const ASSIGNMENT_DURATION_OPTIONS = [
  { value: 4, label: '4' },
  { value: 6, label: '6' },
  { value: 12, label: '12' },
];

export const CLUB_REWARD_NOTE_OPTIONS = [
  { value: 3, label: '感性(声乐)' },
  { value: 4, label: '感性(舞蹈)' },
  { value: 5, label: '感性(形象)' },
  { value: 6, label: '理性(声乐)' },
  { value: 7, label: '理性(舞蹈)' },
  { value: 8, label: '理性(形象)' },
  { value: 9, label: '非凡(声乐)' },
  { value: 10, label: '非凡(舞蹈)' },
  { value: 11, label: '非凡(形象)' },
];

export type ConfigFormData = {
  backend: {
    type?: string;
    screenshot_impl?: string;
    target_screenshot_interval?: string | number;
    instance_id?: string;
    mumu_background_mode?: boolean;
    adb_ip?: string;
    adb_port?: string | number;
    check_emulator?: boolean;
    emulator_path?: string | null;
    adb_emulator_name?: string | null;
    emulator_args?: string;
    windows_window_title?: string | null;
    windows_ahk_path?: string | null;
  };
  options: {
    purchase: {
      enabled: boolean;
      money_enabled: boolean;
      money_items: number[];
      money_refresh: boolean;
      ap_enabled: boolean;
      ap_items: number[];
      weekly_enabled: boolean;
    };
    assignment: {
      enabled: boolean;
      mini_live_reassign_enabled: boolean;
      mini_live_duration: number;
      online_live_reassign_enabled: boolean;
      online_live_duration: number;
    };
    contest: {
      enabled: boolean;
      select_which_contestant: number;
      when_no_set: string;
    };
    produce: {
      enabled: boolean;
      selected_solution_id?: string | null;
      produce_count: number;
      produce_timeout_cd: number;
      interrupt_timeout: number;
      enable_fever_month: string;
    };
    mission_reward: { enabled: boolean };
    club_reward: { enabled: boolean; selected_note?: number };
    upgrade_support_card: { enabled: boolean };
    capsule_toys: {
      enabled: boolean;
      friend_capsule_toys_count: number;
      sense_capsule_toys_count: number;
      logic_capsule_toys_count: number;
      anomaly_capsule_toys_count: number;
    };
    presents: { enabled: boolean };
    activity_funds: { enabled: boolean };
    start_game: {
      enabled: boolean;
      disable_gakumas_localify?: boolean;
      start_through_kuyo?: boolean;
      game_package_name?: string;
      kuyo_package_name?: string;
      dmm_game_path?: string | null;
      dmm_bypass?: boolean;
    };
    end_game: {
      exit_kaa: boolean;
      kill_game: boolean;
      kill_dmm: boolean;
      kill_emulator: boolean;
      shutdown: boolean;
      hibernate: boolean;
      restore_gakumas_localify: boolean;
    };
    misc: {
      check_update: string;
      auto_install_update: boolean;
      expose_to_lan: boolean;
      update_channel: string;
      log_level: string;
    };
    idle: {
      enabled: boolean;
      idle_seconds: number;
      minimize_on_pause: boolean;
    };
    trace: { recommend_card_detection: boolean };
  };
  keep_screenshots?: boolean;
};