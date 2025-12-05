"use client";

/**
 * /console - Agent 控制台
 * Phase A: 路由骨架
 * Phase D: AgentRun 列表与详情、Eval 视图
 */
export default function ConsolePage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Console</h1>
        <p className="text-sm text-muted-foreground">Agent 运行监控与调试</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>Console 开发中...</p>
        </div>
      </main>
    </div>
  );
}
