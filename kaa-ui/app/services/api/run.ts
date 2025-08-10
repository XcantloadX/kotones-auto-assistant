import { get, post } from "../http";

export type RunButtonState = { text: string; interactive: boolean };
export type TaskRow = { name: string; status_text: string };

export const getRunButtonState = () => get<RunButtonState>("/api/v1/run/button_state");
export const getPauseButtonState = () => get<RunButtonState>("/api/v1/run/pause_button_state");
export const postRunToggle = () => post<RunButtonState>("/api/v1/run/toggle");
export const postRunStartAll = () => post<RunButtonState>("/api/v1/run/start_all");
export const postRunStopAll = () => post<RunButtonState>("/api/v1/run/stop_all");
export const postRunPauseToggle = () => post<RunButtonState>("/api/v1/run/pause_toggle");
export const getTasks = () => get<TaskRow[]>("/api/v1/tasks"); 