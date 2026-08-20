# 自然语言查询 Agent

Agent 不直接访问 DuckDB，也不允许模型生成 SQL。执行链如下：

1. 规则规划器或可选大模型从问题中识别英雄/选手、时间、分路和分析类型。
2. 输出经过 Pydantic 校验的 `QueryPlan`。
3. 服务端把计划映射到固定的参数化统计函数。
4. 返回计划、样本量、聚合结果和简短说明，便于用户核对。

当前允许的分析类型是：

- `hero_overview`
- `matchups`
- `teammates`
- `builds`
- `runes`
- `combinations`
- `player_overview`

大模型只接收 QueryPlan Schema 和数据库中已有的英雄/选手词表，不接收 API Key 之外的秘密。模型超时、返回非法 JSON 或计划校验失败时，系统回退到本地规则规划器。

未来扩展比较、队伍和单局回溯时，应先增加一个明确的 DSL 动作和对应的参数化统计函数，再允许模型选择它；不要添加“执行任意 SQL”动作。
