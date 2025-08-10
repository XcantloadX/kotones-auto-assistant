import { get } from "../http";

export const getLast = (size: "thumb" | "full" = "thumb") => get<string>(`/api/v1/screen/last?size=${size}`);
export const getCurrent = (size: "thumb" | "full" = "thumb") => get<string>(`/api/v1/screen/current?size=${size}`); 