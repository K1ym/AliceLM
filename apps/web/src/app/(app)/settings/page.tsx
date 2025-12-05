"use client";

/**
 * /settings - 设置
 * Phase A: 路由骨架
 */
export default function SettingsPage() {
  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">配置与偏好设置</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>设置页面开发中...</p>
        </div>
      </main>
    </div>
  );
}
