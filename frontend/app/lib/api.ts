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
  leagueId: string,
  role: string,
): Promise<{ data: DashboardData; connected: boolean }> {
  const query = new URLSearchParams();
  if (leagueId) query.set("league_id", leagueId);
  if (role) query.set("role", role);
  const qs = query.toString() ? `?${query}` : "";
  const leagueQuery = new URLSearchParams();
  if (leagueId) leagueQuery.set("league_id", leagueId);
  const leagueQs = leagueQuery.toString() ? `?${leagueQuery}` : "";
  try {
    const [meta, leagues, heroes, players, overview, matchups, teammates, builds, runes, combinations] = await Promise.all([
      request<DashboardData["meta"]>("/api/meta"),
      request<DashboardData["leagues"]>("/api/leagues"),
      request<DashboardData["heroes"]>("/api/heroes"),
      request<DashboardData["players"]>("/api/players"),
      request<Overview>(`/api/heroes/${heroId}/overview${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/matchups${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/teammates${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/builds${qs}`),
      request<ItemList>(`/api/heroes/${heroId}/runes${qs}`),
      request<ItemList>(`/api/combinations${leagueQs}`),
    ]);
    return { data: { meta, leagues, heroes, players, overview, matchups, teammates, builds, runes, combinations }, connected: true };
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

export async function loadPlayer(playerKey: string, leagueId: string) {
  const query = new URLSearchParams();
  if (leagueId) query.set("league_id", leagueId);
  return request<{
    summary: Record<string, string | number>;
    heroes: Array<Record<string, string | number>>;
    trend: Array<Record<string, string | number>>;
  }>(`/api/players/${encodeURIComponent(playerKey)}/overview?${query}`);
}

export async function loadCombinations(
  size: 2 | 3,
  heroIds: number[],
  leagueId: string,
) {
  const query = new URLSearchParams({ size: String(size), min_games: "1" });
  if (leagueId) query.set("league_id", leagueId);
  heroIds.forEach((heroId) => query.append("hero_ids", String(heroId)));
  return request<ItemList>(`/api/combinations?${query}`);
}

export type ComboSort = "games" | "win_rate";

export async function loadCombinationRankings(
  leagueId: string,
  sortBy: ComboSort,
  heroId: number | null = null,
) {
  const query = new URLSearchParams({
    min_games: heroId === null ? "2" : "1",
    limit: "30",
    sort_by: sortBy,
  });
  if (leagueId) query.set("league_id", leagueId);
  if (heroId !== null) query.set("hero_id", String(heroId));

  const duoQuery = new URLSearchParams(query);
  duoQuery.set("size", "2");
  const trioQuery = new URLSearchParams(query);
  trioQuery.set("size", "3");
  const [duos, trios] = await Promise.all([
    request<ItemList>(`/api/combinations?${duoQuery}`),
    request<ItemList>(`/api/combinations?${trioQuery}`),
  ]);
  return { duos, trios };
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
