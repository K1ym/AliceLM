"use client";

import { useParams } from "next/navigation";

/**
 * /video/[id] - 视频详情页
 * Phase A: 路由骨架
 */
export default function VideoDetailPage() {
  const params = useParams();
  const videoId = params.id;

  return (
    <div className="flex flex-col h-full">
      <header className="border-b p-4">
        <h1 className="text-xl font-semibold">Video Detail</h1>
        <p className="text-sm text-muted-foreground">视频 ID: {videoId}</p>
      </header>
      
      <main className="flex-1 p-4 overflow-auto">
        <div className="flex items-center justify-center h-full text-muted-foreground">
          <p>视频详情页开发中...</p>
        </div>
      </main>
    </div>
  );
}
