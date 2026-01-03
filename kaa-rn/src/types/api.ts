export interface ApiResponse<T> {
  success: boolean;
  data?: T | null;
  error?: { code: string; message: string; detail?: Record<string, any> } | null;
}

export type EndAction = 'none' | 'shutdown' | 'hibernate';

export interface QuickSettingsDto {
  purchase: boolean;
  assignment: boolean;
  contest: boolean;
  produce: boolean;
  mission_reward: boolean;
  club_reward: boolean;
  activity_funds: boolean;
  presents: boolean;
  capsule_toys: boolean;
  upgrade_support_card: boolean;
  end_action: EndAction;
}

export interface QuickSettingItem {
  id: string;
  name: string;
  icon?: string | null;
  has_settings?: boolean;
  value_key?: string | null;
}

export interface QuickSettingsResponse {
  values: QuickSettingsDto;
  items: QuickSettingItem[];
}

export interface RunButtonStatus {
  status: 'start' | 'stop' | 'stopping';
  interactive: boolean;
}

export interface PauseButtonStatus {
  status: 'pause' | 'resume';
  interactive: boolean;
}

export interface TaskRuntimeDto {
  display: string; // HH:MM:SS
  seconds: number;
  running: boolean;
}

export interface TaskOverviewDto {
  paused?: boolean | null;
  run_button: RunButtonStatus;
  pause_button: PauseButtonStatus;
  runtime: TaskRuntimeDto;
}
