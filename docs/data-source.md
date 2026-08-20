# 数据源与采集策略

## 当前使用的公开入口

赛事数据来自腾讯王者荣耀赛事站点在浏览器中使用的公开 JSON 接口：

| 数据 | URL |
| --- | --- |
| 联赛列表 | `https://prod.comp.smoba.qq.com/leaguesite/leagues/open` |
| 联赛赛程 | `https://prod.comp.smoba.qq.com/leaguesite/matches/open?league_id=...` |
| 比赛小局 | `https://prod.comp.smoba.qq.com/leaguesite/match/battles/open?match_id=...` |
| 小局详情 | `https://prod.comp.smoba.qq.com/leaguesite/battle/open?battle_id=...` |
| 铭文名称映射 | `https://pvp.qq.com/web201605/js/ming.json` |

小局详情是最重要的响应：其中可观察到 BP 序列、双方队伍统计、选手与英雄、最终装备列表、召唤师技能、铭文 ID 等字段。具体可用性取决于赛事和响应版本，构建器不会把缺失值伪造成已知值。

这些 URL 是网页当前使用的公开资源，不代表上游提供了稳定性 SLA，也不代表获得了数据再分发许可。因此仓库只保存代码和小规模合成测试数据，不提交抓取结果。

## 回填过程

1. 拉取联赛列表，按联赛开始或结束时间截取近两年。
2. 顺序获取每个联赛的比赛列表。
3. 顺序获取每场比赛的小局列表。
4. 对未归档的小局获取详情；已有文件默认跳过。
5. 每个响应先写临时文件，再原子替换为正式 JSON。
6. 写入本次回填 manifest，并离线构建 DuckDB。

默认请求间隔为 0.2 秒，可通过 `KPL_REQUEST_DELAY` 调大。采集器不做多线程轰炸，也不包含绕过访问控制的逻辑。

## 上游变化处理

- 保留原始 JSON，解析逻辑升级后可离线重建。
- `kpl-analytics audit` 检查每局 10 名选手、2 支队伍、唯一获胜方、10 个 Pick 和英雄 ID 完整性。
- 上游接口报错、返回非对象 JSON 或业务错误码时，采集器会有限重试后停止，而不是写入伪造数据。
- 若真实数据审计失败，应先检查原始响应并扩展版本兼容层，不应忽略失败。
