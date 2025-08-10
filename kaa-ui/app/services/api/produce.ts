import { get, post, put as httpPut } from "../http";

export type ProduceData = {
  mode: "regular" | "pro" | "master";
  self_study_lesson: "dance" | "visual" | "vocal";
};

export type ProduceSolution = {
  id: string;
  name: string;
  description?: string | null;
  data: ProduceData;
};

export const listSolutions = () => get<ProduceSolution[]>("/api/v1/produce/solutions");
export const createSolution = (name: string) => post<ProduceSolution>(`/api/v1/produce/solutions?name=${encodeURIComponent(name)}`);
export const updateSolution = (id: string, body: ProduceSolution) => httpPut<ProduceSolution>(`/api/v1/produce/solutions/${id}`, body);
export const deleteSolution = (id: string) => fetch(`/api/v1/produce/solutions/${id}`, { method: "DELETE" }); 