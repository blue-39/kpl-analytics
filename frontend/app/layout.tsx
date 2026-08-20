import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KPL Data Lab｜职业联赛数据分析",
  description: "本地优先的王者荣耀 KPL 历史对局、英雄、选手与阵容分析工具。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "KPL Data Lab",
    description: "从局级公开赛事数据查询英雄、选手、BP、对位、出装与阵容组合。",
    type: "website",
    images: [{ url: "/og-preview.jpg", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "KPL Data Lab",
    description: "本地优先的 KPL 历史对局分析工具。",
    images: ["/og-preview.jpg"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
