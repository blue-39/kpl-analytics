"use client";

import type { EChartsCoreOption } from "echarts/core";
import { FormEvent, useEffect, useMemo, useState } from "react";
import Chart from "./chart";
import { askAgent, loadDashboard, loadPlayer } from "../lib/api";
import { demoData } from "../lib/demo-data";
import type { DashboardData } from "../lib/types";

type Mode = "hero" | "player" | "combo";
type PlayerData = {
  summary: Record<string, string | number>;
  heroes: Array<Record<string, string | number>>;
  trend: Array<Record<string, string | number>>;
};

const today = new Date();
const oneYearAgo = new Date(today);
oneYearAgo.setFullYear(today.getFullYear() - 1);
const isoDate = (value: Date) => value.toISOString().slice(0, 10);
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

export default function Dashboard() {
  const [mode, setMode] = useState<Mode>("hero");
  const [data, setData] = useState<DashboardData>(demoData);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [heroId, setHeroId] = useState(531);
  const [playerKey, setPlayerKey] = useState("10005:钟意");
  const [playerData, setPlayerData] = useState<PlayerData>(fallbackPlayer);
  const [startDate, setStartDate] = useState(isoDate(oneYearAgo));
  const [endDate, setEndDate] = useState(isoDate(today));
  const [role, setRole] = useState("");
  const [question, setQuestion] = useState("近一年镜的胜率、BP率和主要对位情况怎么样？");
  const [agentAnswer, setAgentAnswer] = useState("输入问题后，查询计划会被校验并交给统计引擎执行。大模型不直接编写 SQL。 ");
  const [agentBusy, setAgentBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    if (mode === "player") {
      try {
        setPlayerData(await loadPlayer(playerKey, startDate, endDate));
        setConnected(true);
      } catch {
        setPlayerData(fallbackPlayer);
        setConnected(false);
      }
    } else {
      const result = await loadDashboard(heroId, startDate, endDate, role);
      setData(result.data);
      setConnected(result.connected);
    }
    setLoading(false);
  }

  useEffect(() => {
    void loadDashboard(531, isoDate(oneYearAgo), isoDate(today), "").then((result) => {
      setData(result.data);
      setConnected(result.connected);
    });
  }, []);

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

  const draftOption = useMemo<EChartsCoreOption>(() => ({
    color: ["#d34b4b"],
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 34, right: 16, top: 12, bottom: 28 },
    xAxis: { type: "category", data: data.overview.draft_slots.map((row) => `P${row.slot}`), axisLabel: { color: "#8f929a" }, axisLine: { lineStyle: { color: "#34363d" } } },
    yAxis: { type: "value", axisLabel: { color: "#8f929a", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#25272d" } } },
    series: [{ type: "bar", data: data.overview.draft_slots.map((row) => Number(row.share)), barWidth: "52%", itemStyle: { borderRadius: [4, 4, 0, 0] } }],
  }), [data.overview.draft_slots]);

  const playerTrendOption = useMemo<EChartsCoreOption>(() => ({
    color: ["#e84d4d", "#e6b85c"],
    tooltip: { trigger: "axis" },
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
      setAgentAnswer(`${response.answer} · 规划器：${response.planner}`);
      setConnected(true);
    } catch {
      setAgentAnswer("API 尚未启动，因此暂时无法执行自然语言查询。可运行 `kpl-analytics serve` 后重试。 ");
    }
    setAgentBusy(false);
  }

  return (
    <main>
      <header className="topbar">
        <div className="brand"><span className="brand-mark">K</span><span><strong>KPL DATA LAB</strong><small>王者荣耀职业联赛数据分析</small></span></div>
        <nav aria-label="主要视图">
          <button className={mode === "hero" ? "active" : ""} onClick={() => setMode("hero")}>英雄洞察</button>
          <button className={mode === "player" ? "active" : ""} onClick={() => setMode("player")}>选手档案</button>
          <button className={mode === "combo" ? "active" : ""} onClick={() => setMode("combo")}>阵容组合</button>
        </nav>
        <div className="status"><span className={connected ? "dot live" : "dot"} />{connected ? "本地 API 已连接" : "演示数据"}</div>
      </header>

      <section className="hero-strip">
        <div>
          <span className="eyebrow">LOCAL-FIRST · OPEN DATA</span>
          <h1>把每一局职业赛，变成可追问的答案</h1>
          <p>覆盖英雄 BP、对位、搭档、出装、铭文与选手表现；所有统计均可回溯到局级样本。</p>
        </div>
        <div className="coverage">
          <span><strong>{data.meta.coverage.battles}</strong> 小局</span>
          <span><strong>{data.meta.coverage.heroes}</strong> 英雄</span>
          <span><strong>{data.meta.coverage.players}</strong> 选手</span>
          <small>{data.meta.coverage.start_date} — {data.meta.coverage.end_date}</small>
        </div>
      </section>

      <section className="filters" aria-label="数据筛选">
        <label>{mode === "player" ? "选择选手" : "选择英雄"}
          {mode === "player" ? (
            <select value={playerKey} onChange={(event) => setPlayerKey(event.target.value)}>{data.players.map((player) => <option value={player.player_key} key={player.player_key}>{player.player_name} · {player.team_name}</option>)}</select>
          ) : (
            <select value={heroId} onChange={(event) => setHeroId(Number(event.target.value))}>{data.heroes.map((hero) => <option value={hero.hero_id} key={hero.hero_id}>{hero.hero_name} · {hero.games}局</option>)}</select>
          )}
        </label>
        <label>开始日期<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
        <label>结束日期<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
        <label>分路<select value={role} disabled={mode === "player"} onChange={(event) => setRole(event.target.value)}><option value="">全部分路</option><option>对抗路</option><option>打野</option><option>中路</option><option>发育路</option><option>游走</option></select></label>
        <button className="primary" onClick={() => void refresh()} disabled={loading}>{loading ? "统计中…" : "应用筛选"}</button>
      </section>

      {mode === "hero" && <HeroView data={data} summary={summary} trendOption={trendOption} draftOption={draftOption} />}
      {mode === "player" && <PlayerView data={playerData} trendOption={playerTrendOption} />}
      {mode === "combo" && <ComboView data={data} />}

      <section className="agent-panel">
        <div className="agent-label"><span>AI</span><div><h2>自然语言数据助理</h2><p>问题 → 受控查询计划 → 统计引擎 → 可核对答案</p></div></div>
        <form onSubmit={submitAgent}>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} aria-label="向数据助理提问" />
          <button type="submit" disabled={agentBusy}>{agentBusy ? "查询中…" : "执行查询"}</button>
        </form>
        <p className="agent-answer">{agentAnswer}</p>
        <div className="suggestions">
          {["近一年公孙离常见搭档是谁？", "钟意的英雄池和胜率", "近半年高胜率英雄组合"].map((text) => <button key={text} onClick={() => setQuestion(text)}>{text}</button>)}
        </div>
      </section>

      <footer><span>KPL Data Lab · MIT License</span><span>数据模式：{data.meta.data_mode === "demo" ? "演示数据（可替换为公开接口回填）" : "公开赛事数据"}</span></footer>
    </main>
  );
}

function HeroView({ data, summary, trendOption, draftOption }: { data: DashboardData; summary: DashboardData["overview"]["summary"]; trendOption: EChartsCoreOption; draftOption: EChartsCoreOption }) {
  return <>
    <section className="section-head"><div><span className="eyebrow">HERO OVERVIEW</span><h2>{String(summary.hero_name || "英雄")} · 数据总览</h2></div><span className="sample">基于 {summary.picks || 0} 局选取样本</span></section>
    <section className="kpi-grid">
      <Kpi label="选取率" value={number(summary.pick_rate, "%")} note={`${summary.picks || 0} / ${summary.total_games || 0} 局`} />
      <Kpi label="胜率" value={number(summary.win_rate, "%")} note={`${summary.wins || 0} 场胜利`} hot />
      <Kpi label="BP 率" value={number(summary.bp_rate, "%")} note={`${summary.bans || 0} 次禁用`} />
      <Kpi label="KDA" value={number(summary.kda)} note={`${summary.kills || 0} / ${summary.deaths || 0} / ${summary.assists || 0}`} />
    </section>
    <section className="chart-grid"><article className="panel span-two"><PanelTitle title="指标趋势" subtitle="按月份聚合 · 百分比" /><Chart option={trendOption} /></article><article className="panel"><PanelTitle title="选取顺位" subtitle="全局第 N 个 Pick" /><Chart option={draftOption} /></article></section>
    <section className="table-grid">
      <article className="panel"><PanelTitle title="同位置对位" subtitle="对手英雄与交手结果" /><StatsTable rows={data.matchups.items} nameKey="hero_name" columns={["games", "win_rate", "kda"]} /></article>
      <article className="panel"><PanelTitle title="高频搭档" subtitle="同阵营共同登场" /><StatsTable rows={data.teammates.items} nameKey="hero_name" columns={["role_name", "games", "win_rate"]} /></article>
    </section>
    <section className="table-grid">
      <article className="panel"><PanelTitle title="完整出装" subtitle="以结束时装备栏统计" /><RankList rows={data.builds.items} nameKey="build" valueKey="share" suffix="%" /></article>
      <article className="panel"><PanelTitle title="铭文使用" subtitle="铭文出现局数与使用率" /><RankList rows={data.runes.items} nameKey="rune_name" valueKey="usage_rate" suffix="%" /></article>
    </section>
  </>;
}

function PlayerView({ data, trendOption }: { data: PlayerData; trendOption: EChartsCoreOption }) {
  const s = data.summary;
  return <>
    <section className="section-head"><div><span className="eyebrow">PLAYER PROFILE</span><h2>{String(s.player_name)} · {String(s.team_name)}</h2></div><span className="sample">{String(s.role_name)} · {s.games} 局样本</span></section>
    <section className="kpi-grid"><Kpi label="胜率" value={number(s.win_rate, "%")} note={`${s.wins || 0} 场胜利`} hot /><Kpi label="KDA" value={number(s.kda)} note={`${s.kills} / ${s.deaths} / ${s.assists}`} /><Kpi label="MVP" value={String(s.mvp_count || 0)} note="所选时段" /><Kpi label="英雄数" value={String(data.heroes.length)} note="有出场记录" /></section>
    <section className="chart-grid"><article className="panel span-two"><PanelTitle title="选手状态趋势" subtitle="月度胜率与 KDA" /><Chart option={trendOption} /></article><article className="panel"><PanelTitle title="英雄池" subtitle="按出场次数排序" /><StatsTable rows={data.heroes} nameKey="hero_name" columns={["games", "win_rate", "kda"]} /></article></section>
  </>;
}

function ComboView({ data }: { data: DashboardData }) {
  return <><section className="section-head"><div><span className="eyebrow">LINEUP SYNERGY</span><h2>英雄组合表现</h2></div><span className="sample">组合样本需共同登场</span></section><section className="combo-grid">{data.combinations.items.map((row, index) => <article className="combo-card" key={`${row.hero1_id}-${row.hero2_id}`}><span className="rank">0{index + 1}</span><div className="duo"><strong>{row.hero1_name}</strong><span>＋</span><strong>{row.hero2_name}</strong></div><div className="combo-numbers"><span><b>{row.games}</b> 局</span><span><b>{number(row.win_rate, "%")}</b> 胜率</span></div><div className="meter"><i style={{ width: `${row.win_rate}%` }} /></div></article>)}</section></>;
}

function Kpi({ label, value, note, hot = false }: { label: string; value: string; note: string; hot?: boolean }) { return <article className={`kpi ${hot ? "hot" : ""}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></article>; }
function PanelTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div className="panel-title"><h3>{title}</h3><span>{subtitle}</span></div>; }

function StatsTable({ rows, nameKey, columns }: { rows: Array<Record<string, string | number>>; nameKey: string; columns: string[] }) {
  const labels: Record<string, string> = { role_name: "位置", games: "场次", win_rate: "胜率", kda: "KDA" };
  return <div className="stats-table"><div className="table-row table-head"><span>英雄</span>{columns.map((column) => <span key={column}>{labels[column]}</span>)}</div>{rows.slice(0, 6).map((row, index) => <div className="table-row" key={`${row[nameKey]}-${index}`}><span><i>{String(row[nameKey]).slice(0, 1)}</i>{row[nameKey]}</span>{columns.map((column) => <span key={column}>{column === "win_rate" ? number(row[column], "%") : row[column]}</span>)}</div>)}</div>;
}

function RankList({ rows, nameKey, valueKey, suffix }: { rows: Array<Record<string, string | number>>; nameKey: string; valueKey: string; suffix: string }) {
  return <div className="rank-list">{rows.slice(0, 5).map((row, index) => <div key={`${row[nameKey]}-${index}`}><span className="rank">0{index + 1}</span><p><strong>{row[nameKey]}</strong><small>{row.games} 局{row.win_rate !== undefined ? ` · 胜率 ${number(row.win_rate, "%")}` : row.copies !== undefined ? ` · ${row.copies} 枚` : ""}</small></p><b>{number(row[valueKey], suffix)}</b></div>)}</div>;
}
