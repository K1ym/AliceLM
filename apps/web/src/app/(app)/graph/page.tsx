"use client";

/**
 * /graph - 知识图谱
 * Phase A: 路由骨架
 */
export default function GraphPage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Knowledge Graph</h1>
        <p className="text-sm text-muted-foreground">概念与关联可视化</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>知识图谱开发中...</p>
        </div>
      </main>
    </div>
  );
}
