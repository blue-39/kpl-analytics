import { demoData } from "./demo-data";
import type { DashboardData, ItemList, Overview } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null;
    throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export type JobStatus = {
  id: string | null;
  kind: "backfill" | "build" | "audit" | null;
  status: "idle" | "running" | "succeeded" | "failed";
  message: string;
  progress: Record<string, string | number>;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
};

export type AdminStatus = {
  raw_archive_exists: boolean;
  raw_detail_files: number;
  raw_match_files: number;
  database_exists: boolean;
  meta: DashboardData["meta"];
};

export type LLMStatus = {
  configured: boolean;
  endpoint: string | null;
  model: string | null;
  has_api_key: boolean;
  source: "runtime" | "environment" | "none";
};

export type LeagueOption = {
  league_id: string;
  league_name: string;
  start_date: string;
  end_date: string;
  effective_end_date: string;
  availability: "completed" | "in_progress" | "upcoming";
  selectable: boolean;
  league_icon: string | null;
};

export async function loadDashboard(
  heroId: number,
  startDate: string,
  endDate: string,
  role: string,
): Promise<{ data: DashboardData; connected: boolean }> {
  const query = new URLSearchParams();
  if (startDate) query.set("start_date", startDate);
  if (endDate) query.set("end_date", endDate);
  if (role) query.set("role", role);
  const qs = query.toString() ? `?${query}` : "";
  const globalQuery = new URLSearchParams();
  if (startDate) globalQuery.set("start_date", startDate);
  if (endDate) globalQuery.set("end_date", endDate);
  try {
    const [meta, heroes, players, overview, matchups, teammates, builds, runes, combinations] = await Promise.all([
      request<DashboardData["meta"]>("/api/meta"),
      request<DashboardData["heroes"]>("/api/heroes"),
      request<DashboardData["players"]>("/api/players"),
      request<Overview>(`/api/heroes/${heroId}/overview${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/matchups${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/teammates${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/builds${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/runes${qs}`),
      request<ItemList>(`/api/combinations?${globalQuery}`),
    ]);
    return { data: { meta, heroes, players, overview, matchups, teammates, builds, runes, combinations }, connected: true };
  } catch {
    const selected = demoData.heroes.find((hero) => hero.hero_id === heroId);
    return {
      data: selected
        ? { ...demoData, overview: { ...demoData.overview, summary: { ...demoData.overview.summary, hero_id: selected.hero_id, hero_name: selected.hero_name } } }
        : demoData,
      connected: false,
    };
  }
}

export async function loadPlayer(playerKey: string, startDate: string, endDate: string) {
  const query = new URLSearchParams();
  if (startDate) query.set("start_date", startDate);
  if (endDate) query.set("end_date", endDate);
  return request<{
    summary: Record<string, string | number>;
    heroes: Array<Record<string, string | number>>;
    trend: Array<Record<string, string | number>>;
  }>(`/api/players/${encodeURIComponent(playerKey)}/overview?${query}`);
}

export async function askAgent(question: string) {
  return request<{
    answer: string;
    planner: string;
    plan: Record<string, unknown>;
    result: Record<string, unknown>;
  }>("/api/query", { method: "POST", body: JSON.stringify({ question }) });
}

export function getAdminStatus() {
  return request<AdminStatus>("/api/admin/status");
}

export function getCurrentJob() {
  return request<JobStatus>("/api/admin/job");
}

export function getAvailableLeagues() {
  return request<{ items: LeagueOption[] }>("/api/admin/leagues");
}

export function startBackfill(leagueIds: string[]) {
  return request<JobStatus>("/api/admin/backfill", {
    method: "POST",
    body: JSON.stringify({ league_ids: leagueIds }),
  });
}

export function startBuild() {
  return request<JobStatus>("/api/admin/build", { method: "POST" });
}

export function startAudit() {
  return request<JobStatus>("/api/admin/audit", { method: "POST" });
}

export function getLLMStatus() {
  return request<LLMStatus>("/api/settings/llm");
}

export function saveLLMConfiguration(endpoint: string, model: string, apiKey: string) {
  return request<LLMStatus>("/api/settings/llm", {
    method: "POST",
    body: JSON.stringify({ endpoint, model, api_key: apiKey }),
  });
}

export function clearLLMConfiguration() {
  return request<LLMStatus>("/api/settings/llm/clear", { method: "POST" });
}
