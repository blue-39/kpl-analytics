# KPL Data Lab Web

基于 React 19、vinext 和 ECharts 的本地统计看板。

```bash
pnpm install
pnpm run dev
```

默认请求 `http://127.0.0.1:8000`。可以通过 `NEXT_PUBLIC_API_URL` 修改。API 不可用时网页会显示明确标记的演示数据，不会把演示数字伪装成真实比赛统计。

```bash
pnpm run lint
pnpm test
```
