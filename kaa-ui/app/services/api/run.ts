import { get, post } from "../http";

export type RunState = { is_running: boolean; is_stopping: boolean; is_paused: boolean };
export type TaskRow = { name: string; status_text: string };

export const getRunState = () => get<RunState>("/api/v1/run/state");
export const postRunToggle = () => post<RunState>("/api/v1/run/toggle");
export const postRunStartAll = () => post<RunState>("/api/v1/run/start_all");
export const postRunStopAll = () => post<RunState>("/api/v1/run/stop_all");
export const postRunPauseToggle = () => post<RunState>("/api/v1/run/pause_toggle");
export const getTasks = () => get<TaskRow[]>("/api/v1/tasks"); 