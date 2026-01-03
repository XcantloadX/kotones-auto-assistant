const API_BASE = typeof process !== 'undefined' && process.env.KAA_API_BASE ? process.env.KAA_API_BASE : 'http://localhost:4825/api';

import type { QuickSettingsDto, QuickSettingsResponse, TaskOverviewDto } from '../types/api';

async function apiGet(path: string, params?: Record<string, string>) {
  const url = new URL(API_BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString(), { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const payload = await res.json();
  // Backend returns ApiResponse { success, data, error }
  if (!payload?.success) {
    const msg = payload?.error?.message || `API error on GET ${path}`;
    throw new Error(msg);
  }
  return payload.data;
}

async function apiPost(path: string, body: any) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  const payload = await res.json();
  if (!payload?.success) {
    const msg = payload?.error?.message || `API error on POST ${path}`;
    throw new Error(msg);
  }
  return payload.data;
}

export async function getQuickSettings(): Promise<QuickSettingsResponse> {
  return apiGet('/config', { action: 'get_quick' }) as Promise<QuickSettingsResponse>;
}

export async function patchQuickSettings(patch: Record<string, any>): Promise<QuickSettingsResponse> {
  return apiPost('/config', { action: 'patch_quick', patch }) as Promise<QuickSettingsResponse>;
}

export async function getTaskOverview(): Promise<TaskOverviewDto> {
  return apiGet('/tasks', { action: 'overview' }) as Promise<TaskOverviewDto>;
}

export async function getBackendVersion(): Promise<string | null> {
  try {
    return apiGet('/system', { action: 'get_version' }) as Promise<string | null>;
  } catch (e) {
    return null;
  }
}

export async function postTaskAction(payload: any): Promise<any> {
  return apiPost('/tasks', payload);
}

export default { apiGet, apiPost };
