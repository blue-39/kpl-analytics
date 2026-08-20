export type Hero = {
  hero_id: number;
  hero_name: string;
  games: number;
  win_rate: number;
};

export type Player = {
  player_key: string;
  player_name: string;
  team_name: string;
  role_name: string;
  games: number;
  win_rate: number;
};

export type Overview = {
  summary: Record<string, string | number | null>;
  roles: Array<Record<string, string | number>>;
  draft_slots: Array<Record<string, string | number>>;
  trend: Array<Record<string, string | number>>;
  sample_size: number;
};

export type ItemList = {
  items: Array<Record<string, string | number>>;
  sample_size: number;
};

export type Meta = {
  data_mode: string;
  built_at: string | null;
  coverage: {
    start_date: string;
    end_date: string;
    battles: number;
    matches: number;
    heroes: number;
    players: number;
    teams: number;
  };
};

export type DashboardData = {
  meta: Meta;
  heroes: Hero[];
  players: Player[];
  overview: Overview;
  matchups: ItemList;
  teammates: ItemList;
  builds: ItemList;
  runes: ItemList;
  combinations: ItemList;
};
