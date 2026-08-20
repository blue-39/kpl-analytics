CREATE TABLE IF NOT EXISTS metadata (
  key VARCHAR PRIMARY KEY,
  value VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS leagues (
  league_id VARCHAR PRIMARY KEY,
  league_name VARCHAR,
  league_type VARCHAR,
  start_time TIMESTAMP,
  end_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
  match_id VARCHAR PRIMARY KEY,
  league_id VARCHAR,
  cc_match_id VARCHAR,
  stage VARCHAR,
  bo INTEGER,
  start_time TIMESTAMP,
  team1_id VARCHAR,
  team1_name VARCHAR,
  team2_id VARCHAR,
  team2_name VARCHAR
);

CREATE TABLE IF NOT EXISTS battles (
  battle_id VARCHAR PRIMARY KEY,
  match_id VARCHAR,
  battle_seq INTEGER,
  game_date DATE,
  duration_ms BIGINT,
  winning_camp INTEGER,
  status INTEGER,
  source_complete BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS team_battles (
  battle_id VARCHAR,
  camp INTEGER,
  team_id VARCHAR,
  team_name VARCHAR,
  is_win BOOLEAN,
  kills INTEGER,
  deaths INTEGER,
  assists INTEGER,
  gold BIGINT,
  towers INTEGER,
  dragons INTEGER,
  PRIMARY KEY (battle_id, camp)
);

CREATE TABLE IF NOT EXISTS player_battles (
  battle_id VARCHAR,
  player_key VARCHAR,
  player_name VARCHAR,
  actual_player_name VARCHAR,
  team_id VARCHAR,
  team_name VARCHAR,
  camp INTEGER,
  role_id INTEGER,
  role_name VARCHAR,
  hero_id INTEGER,
  hero_name VARCHAR,
  is_win BOOLEAN,
  kills INTEGER,
  deaths INTEGER,
  assists INTEGER,
  gold BIGINT,
  damage BIGINT,
  damage_to_heroes BIGINT,
  damage_taken BIGINT,
  participation_rate DOUBLE,
  mvp_score DOUBLE,
  is_mvp BOOLEAN,
  PRIMARY KEY (battle_id, player_key)
);

CREATE TABLE IF NOT EXISTS bp_actions (
  battle_id VARCHAR,
  action_index INTEGER,
  camp INTEGER,
  action_type VARCHAR,
  hero_id INTEGER,
  hero_name VARCHAR,
  phase_position INTEGER,
  pick_index INTEGER,
  PRIMARY KEY (battle_id, action_index)
);

CREATE TABLE IF NOT EXISTS player_items (
  battle_id VARCHAR,
  player_key VARCHAR,
  slot INTEGER,
  item_id INTEGER,
  item_name VARCHAR,
  PRIMARY KEY (battle_id, player_key, slot)
);

CREATE TABLE IF NOT EXISTS player_runes (
  battle_id VARCHAR,
  player_key VARCHAR,
  rune_id VARCHAR,
  rune_name VARCHAR,
  count INTEGER,
  PRIMARY KEY (battle_id, player_key, rune_id)
);

CREATE INDEX IF NOT EXISTS player_battles_hero_idx ON player_battles(hero_id);
CREATE INDEX IF NOT EXISTS player_battles_player_idx ON player_battles(player_key);
CREATE INDEX IF NOT EXISTS battles_date_idx ON battles(game_date);
CREATE INDEX IF NOT EXISTS bp_actions_hero_idx ON bp_actions(hero_id);
