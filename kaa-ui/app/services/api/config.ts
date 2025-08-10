import { get, patch, put } from "../http";

export type QuickSettings = {
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
};

export type EndAction = "DO_NOTHING" | "SHUTDOWN" | "HIBERNATE";

export const getConfig = () => get<{ data: unknown }>("/api/v1/config");
export const putConfig = (data: unknown) => put<{ ok: boolean; message: string }>("/api/v1/config", { data });
export const patchQuick = (quick: Partial<QuickSettings>) => patch<QuickSettings>("/api/v1/config/quick", quick);
export const putEndAction = (action: EndAction) => put<{ ok: boolean }>("/api/v1/config/end_action", { action }); 