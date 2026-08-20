import type { DashboardData } from "./types";

export const demoData: DashboardData = {
  meta: {
    data_mode: "demo",
    built_at: "本地演示数据",
    coverage: {
      start_date: "2025-04-07",
      end_date: "2026-08-17",
      battles: 72,
      matches: 24,
      heroes: 15,
      players: 20,
      teams: 4,
    },
  },
  heroes: [
    { hero_id: 531, hero_name: "镜", games: 27, win_rate: 59.3 },
    { hero_id: 199, hero_name: "公孙离", games: 25, win_rate: 56 },
    { hero_id: 179, hero_name: "女娲", games: 24, win_rate: 54.2 },
    { hero_id: 525, hero_name: "鲁班大师", games: 23, win_rate: 56.5 },
    { hero_id: 518, hero_name: "马超", games: 22, win_rate: 50 },
  ],
  players: [
    { player_key: "10005:钟意", player_name: "钟意", team_name: "成都AG超玩会", role_name: "打野", games: 18, win_rate: 61.1 },
    { player_key: "10013:小胖", player_name: "小胖", team_name: "重庆狼队", role_name: "打野", games: 18, win_rate: 55.6 },
    { player_key: "10005:一诺", player_name: "一诺", team_name: "成都AG超玩会", role_name: "发育路", games: 18, win_rate: 61.1 },
  ],
  overview: {
    summary: {
      hero_id: 531, hero_name: "镜", picks: 27, wins: 16, bans: 18, total_games: 72,
      pick_rate: 37.5, win_rate: 59.3, bp_rate: 62.5, kda: 4.72,
      kills: 4.1, deaths: 2.3, assists: 6.8,
    },
    roles: [{ role_name: "打野", games: 27, share: 100, win_rate: 59.3 }],
    draft_slots: [
      { slot: 1, games: 5, share: 18.5 }, { slot: 2, games: 4, share: 14.8 },
      { slot: 5, games: 8, share: 29.6 }, { slot: 8, games: 6, share: 22.2 },
      { slot: 10, games: 4, share: 14.8 },
    ],
    trend: [
      { month: "2025-09", pick_rate: 31, win_rate: 50, bp_rate: 54 },
      { month: "2025-11", pick_rate: 38, win_rate: 57, bp_rate: 61 },
      { month: "2026-01", pick_rate: 41, win_rate: 62, bp_rate: 67 },
      { month: "2026-03", pick_rate: 35, win_rate: 55, bp_rate: 58 },
      { month: "2026-05", pick_rate: 46, win_rate: 64, bp_rate: 71 },
      { month: "2026-07", pick_rate: 42, win_rate: 60, bp_rate: 68 },
    ],
    sample_size: 27,
  },
  matchups: {
    items: [
      { hero_id: 502, hero_name: "裴擒虎", role_name: "打野", games: 11, win_rate: 63.6, kda: 4.9 },
      { hero_id: 517, hero_name: "大司命", role_name: "打野", games: 9, win_rate: 55.6, kda: 4.3 },
      { hero_id: 531, hero_name: "镜", role_name: "打野", games: 7, win_rate: 57.1, kda: 4.6 },
    ], sample_size: 27,
  },
  teammates: {
    items: [
      { hero_id: 199, hero_name: "公孙离", role_name: "发育路", games: 13, win_rate: 69.2 },
      { hero_id: 179, hero_name: "女娲", role_name: "中路", games: 12, win_rate: 66.7 },
      { hero_id: 525, hero_name: "鲁班大师", role_name: "游走", games: 11, win_rate: 63.6 },
    ], sample_size: 36,
  },
  builds: {
    items: [
      { build: "巡守利斧 → 抵抗之靴 → 暗影战斧 → 不死鸟之眼", games: 16, share: 59.3, win_rate: 62.5 },
      { build: "贪婪之噬 → 抵抗之靴 → 宗师之力 → 破军", games: 7, share: 25.9, win_rate: 57.1 },
      { build: "巡守利斧 → 冷静之靴 → 暗影战斧 → 碎星锤", games: 4, share: 14.8, win_rate: 50 },
    ], sample_size: 27,
  },
  runes: {
    items: [
      { rune_id: "1512", rune_name: "宿命", copies: 270, games: 27, usage_rate: 100 },
      { rune_id: "2520", rune_name: "狩猎", copies: 270, games: 27, usage_rate: 100 },
      { rune_id: "3509", rune_name: "虚空", copies: 270, games: 27, usage_rate: 100 },
    ], sample_size: 81,
  },
  combinations: {
    items: [
      { hero1_id: 179, hero1_name: "女娲", hero2_id: 199, hero2_name: "公孙离", games: 18, win_rate: 66.7 },
      { hero1_id: 199, hero1_name: "公孙离", hero2_id: 525, hero2_name: "鲁班大师", games: 16, win_rate: 68.8 },
      { hero1_id: 518, hero1_name: "马超", hero2_id: 531, hero2_name: "镜", games: 13, win_rate: 61.5 },
    ], sample_size: 47,
  },
};
