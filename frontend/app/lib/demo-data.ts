import type { DashboardData, ItemList } from "./types";

export const demoTrioCombinations: ItemList = {
  items: [
    { hero1_id: 179, hero1_name: "女娲", hero2_id: 199, hero2_name: "公孙离", hero3_id: 525, hero3_name: "鲁班大师", games: 12, wins: 8, win_rate: 66.7, appearance_rate: 8.3 },
    { hero1_id: 518, hero1_name: "马超", hero2_id: 531, hero2_name: "镜", hero3_id: 159, hero3_name: "朵莉亚", games: 9, wins: 6, win_rate: 66.7, appearance_rate: 6.3 },
  ],
  sample_size: 144,
};

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
    { hero_id: 518, hero_name: "马超", roles: ["对抗路"], games: 22, win_rate: 50 },
    { hero_id: 514, hero_name: "亚连", roles: ["对抗路"], games: 24, win_rate: 54.2 },
    { hero_id: 536, hero_name: "夏洛特", roles: ["对抗路"], games: 26, win_rate: 50 },
    { hero_id: 531, hero_name: "镜", roles: ["打野"], games: 27, win_rate: 59.3 },
    { hero_id: 517, hero_name: "大司命", roles: ["打野"], games: 24, win_rate: 50 },
    { hero_id: 502, hero_name: "裴擒虎", roles: ["打野"], games: 21, win_rate: 47.6 },
    { hero_id: 179, hero_name: "女娲", roles: ["中路"], games: 24, win_rate: 54.2 },
    { hero_id: 110, hero_name: "嬴政", roles: ["中路"], games: 24, win_rate: 50 },
    { hero_id: 152, hero_name: "王昭君", roles: ["中路"], games: 24, win_rate: 45.8 },
    { hero_id: 199, hero_name: "公孙离", roles: ["发育路"], games: 25, win_rate: 56 },
    { hero_id: 112, hero_name: "鲁班七号", roles: ["发育路"], games: 24, win_rate: 50 },
    { hero_id: 519, hero_name: "敖隐", roles: ["发育路"], games: 23, win_rate: 47.8 },
    { hero_id: 525, hero_name: "鲁班大师", roles: ["游走"], games: 23, win_rate: 56.5 },
    { hero_id: 159, hero_name: "朵莉亚", roles: ["游走"], games: 24, win_rate: 50 },
    { hero_id: 126, hero_name: "夏侯惇", roles: ["游走"], games: 25, win_rate: 48 },
  ],
  leagues: [
    { league_id: "demo-kpl", league_name: "KPL 本地演示赛季", start_date: "2025-04-07", end_date: "2026-08-17", battles: 72, matches: 24 },
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
    team_draft_slots: [
      { slot: 1, games: 5, share: 18.5 }, { slot: 2, games: 7, share: 25.9 },
      { slot: 3, games: 8, share: 29.6 }, { slot: 4, games: 4, share: 14.8 },
      { slot: 5, games: 3, share: 11.1 },
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
      { item_id: 1522, item_name: "巡守利斧", games: 25, usage_rate: 92.6, win_rate: 60 },
      { item_id: 1422, item_name: "抵抗之靴", games: 22, usage_rate: 81.5, win_rate: 59.1 },
      { item_id: 1137, item_name: "暗影战斧", games: 20, usage_rate: 74.1, win_rate: 65 },
      { item_id: 1334, item_name: "不死鸟之眼", games: 14, usage_rate: 51.9, win_rate: 57.1 },
    ], sample_size: 27,
  },
  runes: {
    items: [
      { rune_set: "10宿命 · 10狩猎 · 10虚空", rune_count: 30, rune_level: 150, games: 21, usage_rate: 77.8, win_rate: 61.9 },
      { rune_set: "9异变 · 1红月 · 10狩猎 · 10鹰眼", rune_count: 30, rune_level: 150, games: 6, usage_rate: 22.2, win_rate: 50 },
    ], sample_size: 27,
  },
  combinations: {
    items: [
      { hero1_id: 179, hero1_name: "女娲", hero2_id: 199, hero2_name: "公孙离", games: 18, wins: 12, win_rate: 66.7, appearance_rate: 12.5 },
      { hero1_id: 199, hero1_name: "公孙离", hero2_id: 525, hero2_name: "鲁班大师", games: 16, wins: 11, win_rate: 68.8, appearance_rate: 11.1 },
      { hero1_id: 518, hero1_name: "马超", hero2_id: 531, hero2_name: "镜", games: 13, wins: 8, win_rate: 61.5, appearance_rate: 9 },
    ], sample_size: 144,
  },
};
