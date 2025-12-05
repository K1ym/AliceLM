"use client";

/**
 * /chat - 对话场景
 * Phase A: 路由骨架
 * Phase C: Agent 化改造
 */
export default function ChatPage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Chat</h1>
        <p className="text-sm text-muted-foreground">与 Alice 对话</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>Chat 功能开发中...</p>
        </div>
      </main>
    </div>
  );
}
