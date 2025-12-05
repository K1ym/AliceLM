"use client";

/**
 * /tasks - 任务管理
 * Phase A: 路由骨架
 * Phase D+: 任务规划与跟踪
 */
export default function TasksPage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Tasks</h1>
        <p className="text-sm text-muted-foreground">任务与计划管理</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>任务管理开发中...</p>
        </div>
      </main>
    </div>
  );
}
