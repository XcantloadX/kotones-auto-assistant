import { get, post, put as httpPut } from "../http";

export type ProduceAction = 
  | "recommended" 
  | "visual" 
  | "vocal" 
  | "dance" 
  | "outing" 
  | "study" 
  | "allowance" 
  | "rest" 
  | "consult";

export type RecommendCardDetectionMode = "normal" | "strict";

export type ProduceData = {
  mode: "regular" | "pro" | "master";
  idol?: string | null;
  memory_set?: number | null;
  support_card_set?: number | null;
  auto_set_memory: boolean;
  auto_set_support_card: boolean;
  use_pt_boost: boolean;
  use_note_boost: boolean;
  follow_producer: boolean;
  self_study_lesson: "dance" | "visual" | "vocal";
  prefer_lesson_ap: boolean;
  actions_order: ProduceAction[];
  recommend_card_detection_mode: RecommendCardDetectionMode;
  use_ap_drink: boolean;
  skip_commu: boolean;
};

export type ProduceSolution = {
  id: string;
  name: string;
  description?: string | null;
  data: ProduceData;
};

export type IdolOption = {
  label: string;
  value: string;
};

export type ActionOption = {
  label: string;
  value: ProduceAction;
};

export const ACTION_OPTIONS: ActionOption[] = [
  { label: "推荐行动", value: "recommended" },
  { label: "形象课程", value: "visual" },
  { label: "声乐课程", value: "vocal" },
  { label: "舞蹈课程", value: "dance" },
  { label: "外出（おでかけ）", value: "outing" },
  { label: "文化课（授業）", value: "study" },
  { label: "活动支给（活動支給）", value: "allowance" },
  { label: "休息", value: "rest" },
  { label: "咨询（相談）", value: "consult" },
];

export const DETECTION_MODE_OPTIONS = [
  { label: "正常模式", value: "normal" as RecommendCardDetectionMode },
  { label: "严格模式", value: "strict" as RecommendCardDetectionMode },
];

export const listSolutions = () => get<ProduceSolution[]>("/api/v1/produce/solutions");
export const getSolution = (id: string) => get<ProduceSolution>(`/api/v1/produce/solutions/${id}`);
export const listIdols = () => get<IdolOption[]>("/api/v1/produce/idols");
export const createSolution = (name: string, description?: string) => {
  const params = new URLSearchParams({ name });
  if (description) {
    params.append("description", description);
  }
  return post<ProduceSolution>(`/api/v1/produce/solutions?${params}`);
};
export const updateSolution = (id: string, body: ProduceSolution) => httpPut<ProduceSolution>(`/api/v1/produce/solutions/${id}`, body);
export const deleteSolution = (id: string) => fetch(`/api/v1/produce/solutions/${id}`, { method: "DELETE" }); 