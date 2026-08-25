"use client";

import type { EChartsCoreOption } from "echarts/core";
import { FormEvent, useEffect, useMemo, useState } from "react";
import AdminView from "./admin-view";
import Chart from "./chart";
import { askAgent, loadCombinationRankings, loadDashboard, loadPlayer } from "../lib/api";
import type { ComboSort } from "../lib/api";
import { demoData, demoTrioCombinations } from "../lib/demo-data";
import type { DashboardData, Hero, ItemList, League } from "../lib/types";

type Mode = "hero" | "player" | "combo" | "admin";
type PlayerData = {
  summary: Record<string, string | number>;
  heroes: Array<Record<string, string | number>>;
  trend: Array<Record<string, string | number>>;
};
type CombinationData = { duos: ItemList; trios: ItemList };

const ROLES = ["对抗路", "打野", "中路", "发育路", "游走"];
const number = (value: unknown, suffix = "") => `${Number(value || 0).toFixed(1)}${suffix}`;

const fallbackPlayer: PlayerData = {
  summary: { player_name: "钟意", team_name: "成都AG超玩会", role_name: "打野", games: 18, wins: 11, win_rate: 61.1, kda: 5.02, kills: 4.2, deaths: 2.1, assists: 6.4, mvp_count: 4 },
  heroes: [
    { hero_id: 531, hero_name: "镜", games: 7, win_rate: 71.4, kda: 5.8 },
    { hero_id: 502, hero_name: "裴擒虎", games: 6, win_rate: 66.7, kda: 5.1 },
    { hero_id: 517, hero_name: "大司命", games: 5, win_rate: 40, kda: 3.9 },
  ],
  trend: [
    { month: "2026-03", games: 4, win_rate: 50, kda: 4.4 },
    { month: "2026-05", games: 6, win_rate: 66.7, kda: 5.3 },
    { month: "2026-07", games: 8, win_rate: 62.5, kda: 5.1 },
  ],
};

function leagueName(leagues: League[], leagueId: string) {
  return leagues.find((league) => league.league_id === leagueId)?.league_name || "全部已入库比赛";
}

function heroesFor(heroes: Hero[], role: string, search: string) {
  const keyword = search.trim().toLocaleLowerCase();
  return heroes.filter((hero) => (
    hero.roles.includes(role)
    && (!keyword || hero.hero_name.toLocaleLowerCase().includes(keyword))
  ));
}

function slotChart(
  rows: Array<Record<string, string | number>>,
  count: number,
  label: (slot: number) => string,
): EChartsCoreOption {
  const values = Array.from({ length: count }, (_, index) => {
    const row = rows.find((item) => Number(item.slot) === index + 1);
    return Number(row?.share || 0);
  });
  return {
    color: ["#d34b4b"],
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (value) => `${value}%` },
    grid: { left: 34, right: 16, top: 12, bottom: 28 },
    xAxis: { type: "category", data: values.map((_, index) => label(index + 1)), axisLabel: { color: "#8f929a" }, axisLine: { lineStyle: { color: "#34363d" } } },
    yAxis: { type: "value", axisLabel: { color: "#8f929a", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#25272d" } } },
    series: [{ type: "bar", data: values, barWidth: "52%", itemStyle: { borderRadius: [4, 4, 0, 0] } }],
  };
}

export default function Dashboard() {
  const [mode, setMode] = useState<Mode>("hero");
  const [data, setData] = useState<DashboardData>(demoData);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [heroId, setHeroId] = useState(531);
  const [role, setRole] = useState("打野");
  const [heroSearch, setHeroSearch] = useState("");
  const [leagueId, setLeagueId] = useState("demo-kpl");
  const [playerKey, setPlayerKey] = useState("10005:钟意");
  const [club, setClub] = useState("");
  const [playerSearch, setPlayerSearch] = useState("");
  const [playerData, setPlayerData] = useState<PlayerData>(fallbackPlayer);
  const [comboSort, setComboSort] = useState<ComboSort>("games");
  const [comboRole, setComboRole] = useState("打野");
  const [comboSearch, setComboSearch] = useState("");
  const [comboHeroId, setComboHeroId] = useState<number | null>(null);
  const [comboData, setComboData] = useState<CombinationData>({
    duos: demoData.combinations,
    trios: demoTrioCombinations,
  });
  const [comboError, setComboError] = useState("");
  const [question, setQuestion] = useState("镜在当前赛季的胜率、BP率和主要对位情况怎么样？");
  const [agentAnswer, setAgentAnswer] = useState("输入问题后，查询计划会被校验并交给统计引擎执行。大模型不直接编写 SQL。 ");
  const [agentBusy, setAgentBusy] = useState(false);

  const filteredHeroes = heroesFor(data.heroes, role, heroSearch);
  const filteredComboHeroes = heroesFor(data.heroes, comboRole, comboSearch);
  const clubs = Array.from(new Set(data.players.map((player) => player.team_name))).sort();
  const filteredPlayers = data.players.filter((player) => {
    const matchesClub = !club || player.team_name === club;
    const keyword = playerSearch.trim().toLocaleLowerCase();
    return matchesClub && (!keyword || player.player_name.toLocaleLowerCase().includes(keyword));
  });

  useEffect(() => {
    void loadDashboard(531, "", "打野").then(async (initial) => {
      const selectedLeague = initial.data.leagues[0]?.league_id || "";
      const result = selectedLeague
        ? await loadDashboard(531, selectedLeague, "打野")
        : initial;
      setData(result.data);
      setLeagueId(selectedLeague);
      setConnected(result.connected);
      if (result.connected) {
        try {
          setComboData(await loadCombinationRankings(selectedLeague, "games"));
        } catch {
          setComboData({ duos: demoData.combinations, trios: demoTrioCombinations });
        }
      }
    });
  }, []);

  async function refreshHero() {
    setLoading(true);
    const result = await loadDashboard(heroId, leagueId, role);
    setData(result.data);
    setConnected(result.connected);
    setLoading(false);
  }

  async function refreshPlayer() {
    setLoading(true);
    try {
      setPlayerData(await loadPlayer(playerKey, leagueId));
      setConnected(true);
    } catch {
      setPlayerData(fallbackPlayer);
      setConnected(false);
    }
    setLoading(false);
  }

  async function selectMode(nextMode: Mode) {
    setMode(nextMode);
    if (nextMode === "player") await refreshPlayer();
    if (nextMode === "combo") await refreshCombinations();
  }

  function changeHeroRole(nextRole: string) {
    setRole(nextRole);
    setHeroSearch("");
    const firstHero = data.heroes.find((hero) => hero.roles.includes(nextRole));
    if (firstHero) setHeroId(firstHero.hero_id);
  }

  async function refreshCombinations(
    targetLeague = leagueId,
    targetSort = comboSort,
    targetHero = comboHeroId,
  ) {
    setLoading(true);
    setComboError("");
    try {
      setComboData(await loadCombinationRankings(targetLeague, targetSort, targetHero));
      setConnected(true);
    } catch (error) {
      setComboError(error instanceof Error ? error.message : "组合查询失败。");
    }
    setLoading(false);
  }

  const summary = data.overview.summary;
  const trendOption = useMemo<EChartsCoreOption>(() => ({
    color: ["#e84d4d", "#e6b85c", "#70a99b"],
    tooltip: { trigger: "axis", backgroundColor: "#18191d", borderColor: "#33363d", textStyle: { color: "#f5f1e8" } },
    legend: { right: 0, textStyle: { color: "#8f929a" }, data: ["选取率", "胜率", "BP率"] },
    grid: { left: 38, right: 18, top: 42, bottom: 30 },
    xAxis: { type: "category", data: data.overview.trend.map((row) => String(row.month).slice(0, 7)), axisLine: { lineStyle: { color: "#34363d" } }, axisLabel: { color: "#7f8289" } },
    yAxis: { type: "value", min: 0, max: 100, axisLabel: { color: "#7f8289", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#25272d" } } },
    series: [
      { name: "选取率", type: "line", smooth: true, symbol: "circle", data: data.overview.trend.map((row) => Number(row.pick_rate)), areaStyle: { opacity: 0.08 } },
      { name: "胜率", type: "line", smooth: true, data: data.overview.trend.map((row) => Number(row.win_rate)) },
      { name: "BP率", type: "line", smooth: true, data: data.overview.trend.map((row) => Number(row.bp_rate)), lineStyle: { type: "dashed" } },
    ],
  }), [data.overview.trend]);

  const globalDraftOption = useMemo(
    () => slotChart(data.overview.draft_slots, 10, (slot) => `P${slot}`),
    [data.overview.draft_slots],
  );
  const teamDraftOption = useMemo(
    () => slotChart(data.overview.team_draft_slots, 5, (slot) => `己${slot}`),
    [data.overview.team_draft_slots],
  );
  const playerTrendOption = useMemo<EChartsCoreOption>(() => ({
    color: ["#e84d4d", "#e6b85c"], tooltip: { trigger: "axis" },
    grid: { left: 38, right: 18, top: 36, bottom: 28 },
    xAxis: { type: "category", data: playerData.trend.map((row) => String(row.month).slice(0, 7)), axisLabel: { color: "#8f929a" }, axisLine: { lineStyle: { color: "#34363d" } } },
    yAxis: [{ type: "value", axisLabel: { color: "#8f929a", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#25272d" } } }, { type: "value", show: false }],
    series: [
      { name: "胜率", type: "line", smooth: true, data: playerData.trend.map((row) => Number(row.win_rate)) },
      { name: "KDA", type: "bar", yAxisIndex: 1, data: playerData.trend.map((row) => Number(row.kda)), barWidth: 18 },
    ],
  }), [playerData.trend]);

  async function submitAgent(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;
    setAgentBusy(true);
    try {
      const response = await askAgent(question);
      const planner = response.planner === "llm" ? "大模型" : response.planner === "rules_fallback" ? "大模型失败，已回退规则" : "本地规则";
      setAgentAnswer(`${response.answer} · 规划器：${planner}`);
      setConnected(true);
    } catch (error) {
      setAgentAnswer(error instanceof Error ? error.message : "自然语言查询执行失败。");
    }
    setAgentBusy(false);
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand"><span className="brand-mark">K</span><span><strong>KPL DATA LAB</strong><small>王者荣耀职业联赛数据分析</small></span></div>
        <nav aria-label="主要视图">
          <button className={mode === "hero" ? "active" : ""} onClick={() => void selectMode("hero")}>英雄洞察</button>
          <button className={mode === "player" ? "active" : ""} onClick={() => void selectMode("player")}>选手档案</button>
          <button className={mode === "combo" ? "active" : ""} onClick={() => void selectMode("combo")}>阵容组合</button>
          <button className={mode === "admin" ? "active" : ""} onClick={() => void selectMode("admin")}>数据管理</button>
        </nav>
        <div className="status"><span className={connected ? "dot live" : "dot"} />{connected ? "本地 API 已连接" : "演示数据"}</div>
      </header>

      <section className="hero-strip">
        <div><span className="eyebrow">LOCAL-FIRST · OPEN DATA</span><h1>把每一局职业赛，变成可追问的答案</h1><p>覆盖英雄 BP、对位、搭档、出装、铭文与选手表现；所有统计均可回溯到局级样本。</p></div>
        <div className="coverage"><span><strong>{data.meta.coverage.battles}</strong> 小局</span><span><strong>{data.meta.coverage.heroes}</strong> 英雄</span><span><strong>{data.meta.coverage.players}</strong> 选手</span><small>{data.meta.coverage.start_date} — {data.meta.coverage.end_date}</small></div>
      </section>

      {mode === "hero" && <section className="filters" aria-label="英雄数据筛选">
        <label>先选分路<select value={role} onChange={(event) => changeHeroRole(event.target.value)}>{ROLES.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>搜索英雄<input type="search" value={heroSearch} onChange={(event) => setHeroSearch(event.target.value)} placeholder="输入英雄名" /></label>
        <label>选择英雄<select value={filteredHeroes.some((hero) => hero.hero_id === heroId) ? heroId : ""} onChange={(event) => setHeroId(Number(event.target.value))}><option value="" disabled>请选择英雄</option>{filteredHeroes.map((hero) => <option value={hero.hero_id} key={hero.hero_id}>{hero.hero_name}</option>)}</select></label>
        <LeagueSelect leagues={data.leagues} value={leagueId} onChange={setLeagueId} />
        <button className="primary" onClick={() => void refreshHero()} disabled={loading || !filteredHeroes.some((hero) => hero.hero_id === heroId)}>{loading ? "统计中…" : "应用筛选"}</button>
      </section>}

      {mode === "player" && <section className="filters" aria-label="选手数据筛选">
        <label>筛选俱乐部<select value={club} onChange={(event) => { setClub(event.target.value); setPlayerSearch(""); }}><option value="">全部俱乐部</option>{clubs.map((team) => <option key={team}>{team}</option>)}</select></label>
        <label>搜索选手<input type="search" value={playerSearch} onChange={(event) => setPlayerSearch(event.target.value)} placeholder="输入选手名" /></label>
        <label>选择选手<select value={filteredPlayers.some((player) => player.player_key === playerKey) ? playerKey : ""} onChange={(event) => setPlayerKey(event.target.value)}><option value="" disabled>请选择选手</option>{filteredPlayers.map((player) => <option value={player.player_key} key={player.player_key}>{player.player_name} · {player.team_name}</option>)}</select></label>
        <LeagueSelect leagues={data.leagues} value={leagueId} onChange={setLeagueId} />
        <button className="primary" onClick={() => void refreshPlayer()} disabled={loading || !filteredPlayers.some((player) => player.player_key === playerKey)}>{loading ? "统计中…" : "应用筛选"}</button>
      </section>}

      {mode === "hero" && <HeroView data={data} summary={summary} trendOption={trendOption} globalDraftOption={globalDraftOption} teamDraftOption={teamDraftOption} />}
      {mode === "player" && <PlayerView data={playerData} trendOption={playerTrendOption} league={leagueName(data.leagues, leagueId)} />}
      {mode === "combo" && <ComboView data={comboData} heroes={data.heroes} filteredHeroes={filteredComboHeroes} leagues={data.leagues} leagueId={leagueId} setLeagueId={setLeagueId} sort={comboSort} setSort={setComboSort} role={comboRole} setRole={(value) => { setComboRole(value); setComboSearch(""); setComboHeroId(null); }} search={comboSearch} setSearch={(value) => { setComboSearch(value); const exact = data.heroes.find((hero) => hero.roles.includes(comboRole) && hero.hero_name === value.trim()); setComboHeroId(exact?.hero_id ?? null); }} heroId={comboHeroId} setHeroId={setComboHeroId} query={() => void refreshCombinations()} clear={() => { setComboSearch(""); setComboHeroId(null); void refreshCombinations(leagueId, comboSort, null); }} loading={loading} error={comboError} />}
      {mode === "admin" && <AdminView />}

      <section className="agent-panel">
        <div className="agent-label"><span>AI</span><div><h2>自然语言数据助理</h2><p>问题 → 受控查询计划 → 统计引擎 → 可核对答案</p></div></div>
        <form onSubmit={submitAgent}><input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="向数据助理提问" /><button type="submit" disabled={agentBusy}>{agentBusy ? "查询中…" : "执行查询"}</button></form>
        <p className="agent-answer">{agentAnswer}</p>
        <div className="suggestions">{["公孙离常见搭档是谁？", "钟意的英雄池和胜率", "高胜率英雄组合"].map((text) => <button key={text} onClick={() => setQuestion(text)}>{text}</button>)}</div>
      </section>

      <footer><span>KPL Data Lab · MIT License</span><span>数据模式：{data.meta.data_mode === "demo" ? "演示数据（可替换为公开接口回填）" : "公开赛事数据"}</span></footer>
    </main>
  );
}

function LeagueSelect({ leagues, value, onChange }: { leagues: League[]; value: string; onChange: (value: string) => void }) {
  return <label>选择比赛<select value={value} onChange={(event) => onChange(event.target.value)}>{leagues.map((league) => <option value={league.league_id} key={league.league_id}>{league.league_name}</option>)}</select></label>;
}

function HeroView({ data, summary, trendOption, globalDraftOption, teamDraftOption }: { data: DashboardData; summary: DashboardData["overview"]["summary"]; trendOption: EChartsCoreOption; globalDraftOption: EChartsCoreOption; teamDraftOption: EChartsCoreOption }) {
  return <>
    <section className="section-head"><div><span className="eyebrow">HERO OVERVIEW</span><h2>{String(summary.hero_name || "英雄")} · 数据总览</h2></div><span className="sample">基于 {summary.picks || 0} 局选取样本</span></section>
    <section className="kpi-grid"><Kpi label="选取率" value={number(summary.pick_rate, "%")} note={`${summary.picks || 0} / ${summary.total_games || 0} 局`} /><Kpi label="胜率" value={number(summary.win_rate, "%")} note={`${summary.wins || 0} 场胜利`} hot /><Kpi label="BP 率" value={number(summary.bp_rate, "%")} note={`${summary.bans || 0} 次禁用`} /><Kpi label="KDA" value={number(summary.kda)} note={`${summary.kills || 0} / ${summary.deaths || 0} / ${summary.assists || 0}`} /></section>
    <section className="chart-grid hero-chart-grid"><article className="panel"><PanelTitle title="指标趋势" subtitle="赛事范围内按月份聚合" /><Chart option={trendOption} /></article><article className="panel"><PanelTitle title="全局选取顺位" subtitle="本局第 1–10 个 Pick" /><Chart option={globalDraftOption} /></article><article className="panel"><PanelTitle title="己方选取顺位" subtitle="己方第 1–5 个 Pick" /><Chart option={teamDraftOption} /></article></section>
    <section className="table-grid"><article className="panel"><PanelTitle title="同位置对位" subtitle="对手英雄与交手结果" /><StatsTable rows={data.matchups.items} nameKey="hero_name" columns={["games", "win_rate", "kda"]} /></article><article className="panel"><PanelTitle title="高频搭档" subtitle="同阵营共同登场" /><StatsTable rows={data.teammates.items} nameKey="hero_name" columns={["role_name", "games", "win_rate"]} /></article></section>
    <section className="table-grid"><article className="panel"><PanelTitle title="单件装备" subtitle="该装备在英雄出场样本中的出现率" /><RankList rows={data.builds.items} nameKey="item_name" valueKey="usage_rate" suffix="%" /></article><article className="panel rune-panel"><PanelTitle title="150 级铭文页" subtitle="按每局整套铭文组合统计" /><RankList rows={data.runes.items} nameKey="rune_set" valueKey="usage_rate" suffix="%" /></article></section>
  </>;
}

function PlayerView({ data, trendOption, league }: { data: PlayerData; trendOption: EChartsCoreOption; league: string }) {
  const s = data.summary;
  return <><section className="section-head"><div><span className="eyebrow">PLAYER PROFILE</span><h2>{String(s.player_name)} · {String(s.team_name)}</h2></div><span className="sample">{String(s.role_name)} · {league} · {s.games} 局样本</span></section><section className="kpi-grid"><Kpi label="胜率" value={number(s.win_rate, "%")} note={`${s.wins || 0} 场胜利`} hot /><Kpi label="KDA" value={number(s.kda)} note={`${s.kills} / ${s.deaths} / ${s.assists}`} /><Kpi label="MVP" value={String(s.mvp_count || 0)} note="所选赛事" /><Kpi label="英雄数" value={String(data.heroes.length)} note="有出场记录" /></section><section className="chart-grid"><article className="panel span-two"><PanelTitle title="选手状态趋势" subtitle="月度胜率与 KDA" /><Chart option={trendOption} /></article><article className="panel"><PanelTitle title="英雄池" subtitle="按出场次数排序" /><StatsTable rows={data.heroes} nameKey="hero_name" columns={["games", "win_rate", "kda"]} /></article></section></>;
}

function ComboView({ data, heroes, filteredHeroes, leagues, leagueId, setLeagueId, sort, setSort, role, setRole, search, setSearch, heroId, setHeroId, query, clear, loading, error }: { data: CombinationData; heroes: Hero[]; filteredHeroes: Hero[]; leagues: League[]; leagueId: string; setLeagueId: (value: string) => void; sort: ComboSort; setSort: (value: ComboSort) => void; role: string; setRole: (value: string) => void; search: string; setSearch: (value: string) => void; heroId: number | null; setHeroId: (value: number | null) => void; query: () => void; clear: () => void; loading: boolean; error: string }) {
  const selectedHero = heroes.find((hero) => hero.hero_id === heroId);
  const scopeLabel = selectedHero
    ? `包含 ${selectedHero.hero_name} 的全部组合`
    : `全部组合 · 按${sort === "games" ? "出场次数" : "胜率"}排序`;
  return <>
    <section className="section-head combo-heading"><div><span className="eyebrow">LINEUP SYNERGY</span><h2>英雄组合表现</h2></div><span className="sample">{scopeLabel}</span></section>
    <section className="combo-filter panel">
      <div className="combo-filter-grid">
        <LeagueSelect leagues={leagues} value={leagueId} onChange={setLeagueId} />
        <label>榜单排序<select value={sort} onChange={(event) => setSort(event.target.value as ComboSort)}><option value="games">出场次数</option><option value="win_rate">胜率</option></select></label>
        <label>英雄分路<select value={role} onChange={(event) => setRole(event.target.value)}>{ROLES.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label>搜索一个英雄<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="留空则查看完整榜单" /></label>
        <label>包含英雄<select value={heroId ?? ""} onChange={(event) => setHeroId(event.target.value ? Number(event.target.value) : null)}><option value="">不指定英雄</option>{filteredHeroes.map((hero) => <option value={hero.hero_id} key={hero.hero_id}>{hero.hero_name}</option>)}</select></label>
      </div>
      <div className="combo-actions"><span>{selectedHero ? `将列出所有包含「${selectedHero.hero_name}」的双英雄和三英雄组合。` : "未指定英雄时，同时展示双英雄榜和三英雄榜。"}</span><span className="error-text">{error}</span><div>{heroId !== null && <button className="secondary" onClick={clear} disabled={loading}>清除英雄</button>}<button className="primary" onClick={query} disabled={loading}>{loading ? "查询中…" : "更新组合榜"}</button></div></div>
    </section>
    <CombinationSection title="双英雄组合" data={data.duos} />
    <CombinationSection title="三英雄组合" data={data.trios} />
  </>;
}

function CombinationSection({ title, data }: { title: string; data: ItemList }) {
  return <section className="combo-section"><div className="combo-list-head"><h3>{title}</h3><span>{data.items.length} 个组合</span></div><div className="combo-grid">{data.items.length === 0 ? <article className="empty-state">当前条件下没有共同出场记录。</article> : data.items.map((row, index) => { const games = Number(row.games || 0); const wins = Number(row.wins || 0); return <article className="combo-card" key={`${row.hero1_id}-${row.hero2_id}-${row.hero3_id || ""}`}><span className="rank">{String(index + 1).padStart(2, "0")}</span><div className="duo"><strong>{row.hero1_name}</strong><span>＋</span><strong>{row.hero2_name}</strong>{row.hero3_name && <><span>＋</span><strong>{row.hero3_name}</strong></>}</div><div className="combo-stats"><span><small>出场</small><b>{games} 局</b></span><span><small>胜负</small><b>{wins} 胜 {Math.max(games - wins, 0)} 负</b></span><span><small>出场率</small><b>{number(row.appearance_rate, "%")}</b></span><span><small>胜率</small><b>{number(row.win_rate, "%")}</b></span></div><div className="meter"><i style={{ width: `${row.win_rate}%` }} /></div></article>; })}</div></section>;
}

function Kpi({ label, value, note, hot = false }: { label: string; value: string; note: string; hot?: boolean }) { return <article className={`kpi ${hot ? "hot" : ""}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>; }
function PanelTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div className="panel-title"><h3>{title}</h3><span>{subtitle}</span></div>; }

function StatsTable({ rows, nameKey, columns }: { rows: Array<Record<string, string | number>>; nameKey: string; columns: string[] }) {
  const labels: Record<string, string> = { role_name: "位置", games: "场次", win_rate: "胜率", kda: "KDA" };
  return <div className="stats-table"><div className="table-row table-head"><span>英雄</span>{columns.map((column) => <span key={column}>{labels[column]}</span>)}</div>{rows.slice(0, 6).map((row, index) => <div className="table-row" key={`${row[nameKey]}-${index}`}><span><i>{String(row[nameKey]).slice(0, 1)}</i>{row[nameKey]}</span>{columns.map((column) => <span key={column}>{column === "win_rate" ? number(row[column], "%") : row[column]}</span>)}</div>)}</div>;
}

function RankList({ rows, nameKey, valueKey, suffix }: { rows: Array<Record<string, string | number>>; nameKey: string; valueKey: string; suffix: string }) {
  return <div className="rank-list">{rows.slice(0, 6).map((row, index) => <div key={`${row[nameKey]}-${index}`}><span className="rank">0{index + 1}</span><p><strong>{row[nameKey]}</strong><small>{row.games} 局{row.rune_level !== undefined ? ` · ${row.rune_level} 级` : ""}{row.win_rate !== undefined ? ` · 胜率 ${number(row.win_rate, "%")}` : ""}</small></p><b>{number(row[valueKey], suffix)}</b></div>)}</div>;
}
