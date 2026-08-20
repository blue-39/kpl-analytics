import type { Metadata } from "next";
import Dashboard from "./components/dashboard";

export const metadata: Metadata = {
  title: "KPL Data Lab｜英雄与选手数据分析",
  description: "查询 KPL 英雄 BP、胜率、对位、阵容、出装、铭文及选手表现。",
};

export default function Home() {
  return <Dashboard />;
}
