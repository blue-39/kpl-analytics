"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  clearLLMConfiguration,
  getAdminStatus,
  getAvailableLeagues,
  getCurrentJob,
  getLLMStatus,
  saveLLMConfiguration,
  startAudit,
  startBackfill,
  startBuild,
} from "../lib/api";
import type { AdminStatus, JobStatus, LeagueOption, LLMStatus } from "../lib/api";

const kindNames = { backfill: "比赛回填", build: "构建数据库", audit: "完整性审计" };
const statusNames = { idle: "空闲", running: "运行中", succeeded: "已完成", failed: "失败" };

export default function AdminView() {
  const [status, setStatus] = useState<AdminStatus | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [llm, setLLM] = useState<LLMStatus | null>(null);
  const [leagues, setLeagues] = useState<LeagueOption[]>([]);
  const [selectedLeagueIds, setSelectedLeagueIds] = useState<string[]>([]);
  const [loadingLeagues, setLoadingLeagues] = useState(true);
  const [endpoint, setEndpoint] = useState("https://api.openai.com/v1/chat/completions");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void Promise.all([getAdminStatus(), getCurrentJob(), getLLMStatus()])
      .then(([nextStatus, nextJob, nextLLM]) => {
        if (!active) return;
        setStatus(nextStatus);
        setJob(nextJob);
        setLLM(nextLLM);
        if (nextLLM.endpoint) setEndpoint(nextLLM.endpoint);
        if (nextLLM.model) setModel(nextLLM.model);
      })
      .catch((error: Error) => active && setMessage(error.message));
    void getAvailableLeagues()
      .then((response) => active && setLeagues(response.items))
      .catch((error: Error) => active && setMessage(`赛事列表读取失败：${error.message}`))
      .finally(() => active && setLoadingLeagues(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (job?.status !== "running") return;
    const timer = window.setInterval(() => {
      void getCurrentJob().then((nextJob) => {
        setJob(nextJob);
        if (nextJob.status !== "running") {
          void getAdminStatus().then(setStatus);
        }
      }).catch((error: Error) => setMessage(error.message));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job?.status]);

  async function launch(action: () => Promise<JobStatus>) {
    setMessage("");
    try {
      setJob(await action());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "任务启动失败");
    }
  }

  async function saveLLM(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const next = await saveLLMConfiguration(endpoint.trim(), model.trim(), apiKey);
      setLLM(next);
      setApiKey("");
      setMessage("模型配置已写入后端内存，现在可以直接在下方向 Agent 提问。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "模型配置失败");
    } finally {
      setSaving(false);
    }
  }

  function toggleLeague(leagueId: string) {
    setSelectedLeagueIds((current) => current.includes(leagueId)
      ? current.filter((id) => id !== leagueId)
      : [...current, leagueId]);
  }

  async function clearLLM() {
    setSaving(true);
    setMessage("");
    try {
      const next = await clearLLMConfiguration();
      setLLM(next);
      setApiKey("");
      setMessage(next.source === "environment" ? "已恢复环境变量中的模型配置。" : "已清除内存中的模型配置。规则查询仍可使用。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "清除配置失败");
    } finally {
      setSaving(false);
    }
  }

  const running = job?.status === "running";
  const progress = job?.progress || {};
  const dataMode = status?.meta.data_mode === "real" ? "真实公开赛事数据" : "演示数据";

  return <>
    <section className="section-head admin-heading">
      <div><span className="eyebrow">LOCAL CONTROL CENTER</span><h2>数据与 Agent 管理</h2></div>
      <span className="sample">仅控制本机服务 · 不执行任意命令</span>
    </section>

    <section className="admin-summary">
      <article><span>当前数据库</span><strong>{dataMode}</strong><small>{status?.meta.coverage.battles ?? "—"} 小局</small></article>
      <article><span>原始归档</span><strong>{status?.raw_archive_exists ? "已存在" : "尚未回填"}</strong><small>{status?.raw_detail_files ?? "—"} 个局详情 JSON</small></article>
      <article><span>模型规划器</span><strong>{llm?.configured ? "已连接" : "未配置"}</strong><small>{llm?.model || "当前使用规则规划器"}</small></article>
    </section>

    <section className="admin-grid">
      <article className="panel admin-panel">
        <div className="panel-title"><h3>比赛数据流水线</h3><span>回填 → 建库 → 审计</span></div>
        <div className="pipeline-actions">
          <div className="pipeline-step league-step">
            <span className="step-number">01</span>
            <div><h4>选择并回填公开赛事</h4><p>可选赛事从公开联赛列表动态读取。进行中的赛事自动以今天为截止日期，并在再次回填时发现新增的已完成比赛。</p></div>
            <div className="league-picker">
              <div className="league-picker-head">
                <span>{loadingLeagues ? "正在读取赛事…" : `已选择 ${selectedLeagueIds.length} / ${leagues.filter((item) => item.selectable).length} 项`}</span>
                <div><button type="button" onClick={() => setSelectedLeagueIds(leagues.filter((item) => item.selectable).map((item) => item.league_id))}>全选</button><button type="button" onClick={() => setSelectedLeagueIds([])}>清空</button><button type="button" onClick={() => { setLoadingLeagues(true); void getAvailableLeagues().then((response) => setLeagues(response.items)).catch((error: Error) => setMessage(error.message)).finally(() => setLoadingLeagues(false)); }}>刷新列表</button></div>
              </div>
              <div className="league-options">
                {leagues.map((league) => <label className={`league-option ${selectedLeagueIds.includes(league.league_id) ? "selected" : ""} ${!league.selectable ? "disabled" : ""}`} key={league.league_id}>
                  <input type="checkbox" disabled={!league.selectable || running} checked={selectedLeagueIds.includes(league.league_id)} onChange={() => toggleLeague(league.league_id)} />
                  <span><strong>{league.league_name}</strong><small>{league.start_date} — {league.effective_end_date}</small></span>
                  <i className={league.availability}>{league.availability === "in_progress" ? "进行中 · 回填至今天" : league.availability === "completed" ? "已结束" : "未开始"}</i>
                </label>)}
              </div>
            </div>
            <div className="pipeline-controls league-actions">
              <span>将回填所选赛事中截至当前已经完成的小局</span>
              <button className="primary" disabled={running || selectedLeagueIds.length === 0} onClick={() => void launch(() => startBackfill(selectedLeagueIds))}>回填所选赛事</button>
            </div>
          </div>
          <div className="pipeline-step">
            <span className="step-number">02</span>
            <div><h4>构建真实数据库</h4><p>从本地 JSON 重建 DuckDB，并把看板切换到真实数据；失败时自动恢复原数据库。</p></div>
            <button className="secondary" disabled={running || !status?.raw_archive_exists} onClick={() => {
              if (window.confirm("将使用原始归档重建当前数据库，是否继续？")) void launch(startBuild);
            }}>构建并切换</button>
          </div>
          <div className="pipeline-step">
            <span className="step-number">03</span>
            <div><h4>执行完整性审计</h4><p>检查每局十名选手、双方队伍、唯一胜者、BP Pick 数和未知英雄。</p></div>
            <button className="secondary" disabled={running} onClick={() => void launch(startAudit)}>开始审计</button>
          </div>
        </div>
      </article>

      <article className="panel job-panel">
        <div className="panel-title"><h3>任务状态</h3><span className={`job-chip ${job?.status || "idle"}`}>{statusNames[job?.status || "idle"]}</span></div>
        <div className="job-state">
          <span>{job?.kind ? kindNames[job.kind] : "暂无后台任务"}</span>
          <strong>{job?.message || "点击左侧按钮开始"}</strong>
          {job?.kind === "backfill" && <dl>
            <div><dt>联赛</dt><dd>{progress.league_index || 0} / {progress.league_total || progress.leagues || 0}</dd></div>
            <div><dt>比赛</dt><dd>{progress.matches || 0}</dd></div>
            <div><dt>小局</dt><dd>{progress.battles || 0}</dd></div>
            <div><dt>新详情</dt><dd>{progress.details || 0}</dd></div>
            <div><dt>已跳过</dt><dd>{progress.skipped || 0}</dd></div>
          </dl>}
          {running && <div className="activity"><i /></div>}
          {job?.error && <p className="error-text">{job.error}</p>}
          {job?.result && <pre>{JSON.stringify(job.result, null, 2)}</pre>}
        </div>
      </article>
    </section>

    <section className="panel llm-panel">
      <div className="panel-title"><h3>大模型连接</h3><span>{llm?.configured ? `已启用 · ${llm.source === "runtime" ? "网页配置" : "环境变量"}` : "可选"}</span></div>
      <form onSubmit={saveLLM}>
        <label>Chat Completions Endpoint<input type="url" required value={endpoint} onChange={(event) => setEndpoint(event.target.value)} placeholder="https://provider.example/v1/chat/completions" /></label>
        <label>Model<input required value={model} onChange={(event) => setModel(event.target.value)} placeholder="填写服务商提供的模型名称" /></label>
        <label>API Key<input type="password" required value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" placeholder={llm?.has_api_key ? "已配置；重新保存时请再次输入" : "仅发送到本机后端内存"} /></label>
        <div className="llm-buttons"><button className="primary" type="submit" disabled={saving}>{saving ? "保存中…" : "保存并启用"}</button><button className="secondary" type="button" disabled={saving} onClick={() => void clearLLM()}>清除网页配置</button></div>
      </form>
      <p className="security-note">API Key 不写入文件、不放入浏览器存储，也不会由查询接口返回；重启后端后需重新输入。此管理 API 没有登录鉴权，请只在 127.0.0.1 本机使用。</p>
    </section>

    {message && <p className="admin-message" role="status">{message}</p>}
  </>;
}
