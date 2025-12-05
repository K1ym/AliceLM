"use client";

/**
 * /library - 视频库
 * Phase A: 路由骨架
 */
export default function LibraryPage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Library</h1>
        <p className="text-sm text-muted-foreground">视频知识库</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>Library 功能开发中...</p>
        </div>
      </main>
    </div>
  );
}
