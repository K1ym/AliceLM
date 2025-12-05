"use client";

/**
 * /timeline - 时间线
 * Phase A: 路由骨架
 * Phase B: 正式实现 TimelineEvent 展示
 */
export default function TimelinePage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Timeline</h1>
        <p className="text-sm text-muted-foreground">学习轨迹与事件记录</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>时间线开发中...</p>
        </div>
      </main>
    </div>
  );
}
