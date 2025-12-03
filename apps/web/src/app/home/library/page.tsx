"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Image from "next/image";
import { Search, Filter, Plus, FolderHeart, Tv, Play, Loader2 } from "lucide-react";
import { VideoCard } from "@/components/core/VideoCard";
import { FolderCard, BilibiliVideoCard } from "@/components/library";
import { videosApi, bilibiliApi, foldersApi, importApi, BilibiliFolderInfo, BilibiliFolderDetailResponse } from "@/lib/api";
import type { Video } from "@/types/home";

type ViewMode = "library" | "bilibili";
type VideoStatus = "all" | "done" | "processing" | "failed" | "pending";

const STATUS_TABS: { label: string; value: VideoStatus }[] = [
  { label: "全部", value: "all" },
  { label: "已完成", value: "done" },
  { label: "处理中", value: "processing" },
  { label: "失败", value: "failed" },
];

function LibraryContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialSearch = searchParams.get("search") || "";

  const [viewMode, setViewMode] = useState<ViewMode>("library");
  const [videos, setVideos] = useState<Video[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<VideoStatus>("all");
  const [search, setSearch] = useState(initialSearch);
  const [loading, setLoading] = useState(true);
  
  // B站收藏夹状态
  const [bilibiliFolders, setBilibiliFolders] = useState<{
    created: BilibiliFolderInfo[];
    collected_folders: BilibiliFolderInfo[];
    collected_seasons: BilibiliFolderInfo[];
  } | null>(null);
  const [bilibiliLoading, setBilibiliLoading] = useState(false);
  const [addingFolder, setAddingFolder] = useState<string | null>(null);
  
  // 收藏夹详情状态
  const [selectedFolder, setSelectedFolder] = useState<BilibiliFolderInfo | null>(null);
  const [folderDetail, setFolderDetail] = useState<BilibiliFolderDetailResponse | null>(null);
  const [folderDetailLoading, setFolderDetailLoading] = useState(false);
  const [importingVideo, setImportingVideo] = useState<string | null>(null);
  
  // 添加收藏夹弹窗状态
  const [addModalFolder, setAddModalFolder] = useState<BilibiliFolderInfo | null>(null);
  const [importMode, setImportMode] = useState<'all' | 'new'>('all'); // 默认导入全部

  useEffect(() => {
    loadVideos();
  }, [filter, search]);

  useEffect(() => {
    if (viewMode === "bilibili" && !bilibiliFolders) {
      loadBilibiliFolders();
    }
  }, [viewMode]);

  async function loadVideos() {
    setLoading(true);
    try {
      const params: { status?: string; search?: string; page_size?: number } = {
        page_size: 20,
      };
      if (filter !== "all") {
        params.status = filter;
      }
      if (search) {
        params.search = search;
      }
      const res = await videosApi.list(params);
      if (res.data) {
        setVideos(res.data.items as Video[]);
        setTotal(res.data.total);
      }
    } catch {
      // 开发模式忽略
    } finally {
      setLoading(false);
    }
  }

  async function loadBilibiliFolders() {
    setBilibiliLoading(true);
    try {
      const res = await bilibiliApi.getFolders();
      if (res.data) {
        setBilibiliFolders(res.data);
      }
    } catch {
      // 可能未绑定B站账号
    } finally {
      setBilibiliLoading(false);
    }
  }

  function openAddModal(folder: BilibiliFolderInfo) {
    setAddModalFolder(folder);
    setImportMode('all');
  }

  async function confirmAddFolder() {
    if (!addModalFolder) return;
    
    const shouldImport = importMode === 'all';
    setAddingFolder(addModalFolder.id);
    setAddModalFolder(null);
    
    try {
      const res = await foldersApi.add(addModalFolder.id, addModalFolder.folder_type, shouldImport);
      const videoCount = res.data?.video_count || 0;
      alert(shouldImport 
        ? `添加成功，已导入${videoCount}个视频` 
        : "添加成功，将仅监控新视频"
      );
      setViewMode("library");
      loadVideos();
    } catch {
      alert("添加失败，可能已存在");
    } finally {
      setAddingFolder(null);
    }
  }

  async function handleOpenFolder(folder: BilibiliFolderInfo) {
    setSelectedFolder(folder);
    setFolderDetailLoading(true);
    setFolderDetail(null);
    try {
      const res = await bilibiliApi.getFolderVideos(folder.folder_type, folder.id);
      if (res.data) {
        setFolderDetail(res.data);
      }
    } catch {
      alert("获取视频列表失败");
      setSelectedFolder(null);
    } finally {
      setFolderDetailLoading(false);
    }
  }

  async function handleImportVideo(bvid: string) {
    setImportingVideo(bvid);
    try {
      await importApi.single({ url: `https://www.bilibili.com/video/${bvid}` });
      alert("导入成功");
    } catch {
      alert("导入失败");
    } finally {
      setImportingVideo(null);
    }
  }

  function handleBackToFolders() {
    setSelectedFolder(null);
    setFolderDetail(null);
  }

  return (
    <div className="p-6 md:p-10 max-w-7xl mx-auto h-full overflow-y-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-light text-neutral-900 mb-2">知识库</h1>
          <p className="text-neutral-500 font-light">管理和浏览你的知识库</p>
        </div>

        <div className="flex items-center gap-3">
          {viewMode === "library" && (
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 w-4 h-4" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索转写内容..."
                className="pl-9 pr-4 py-2 bg-white border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400 w-full md:w-64"
              />
            </div>
          )}
          <button className="p-2 bg-white border border-neutral-200 rounded-xl hover:bg-neutral-50 text-neutral-600">
            <Filter className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* View Mode Toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setViewMode("library")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            viewMode === "library"
              ? "bg-neutral-900 text-white"
              : "bg-white border border-neutral-200 text-neutral-600 hover:border-neutral-300"
          }`}
        >
          <Play className="w-4 h-4" />
          我的知识库
        </button>
        <button
          onClick={() => setViewMode("bilibili")}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            viewMode === "bilibili"
              ? "bg-pink-500 text-white"
              : "bg-white border border-neutral-200 text-neutral-600 hover:border-neutral-300"
          }`}
        >
          <Tv className="w-4 h-4" />
          B站收藏夹
        </button>
      </div>

      {viewMode === "library" ? (
        <>
          {/* Status Tabs */}
          <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value)}
                className={`
                  px-4 py-1.5 rounded-full text-sm font-medium transition-colors whitespace-nowrap
                  ${
                    filter === tab.value
                      ? "bg-neutral-900 text-white"
                      : "bg-white border border-neutral-200 text-neutral-600 hover:border-neutral-300"
                  }
                `}
              >
                {tab.label}
                {tab.value === "all" && total > 0 && (
                  <span className="ml-2 opacity-60 text-xs">{total}</span>
                )}
              </button>
            ))}
          </div>

          {/* Video Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-white rounded-2xl border border-neutral-100 overflow-hidden animate-pulse"
                >
                  <div className="aspect-video bg-neutral-200" />
                  <div className="p-4 space-y-3">
                    <div className="h-4 bg-neutral-200 rounded w-3/4" />
                    <div className="h-3 bg-neutral-200 rounded w-1/2" />
                  </div>
                </div>
              ))
            ) : videos.length > 0 ? (
              videos.map((video) => <VideoCard key={video.id} video={video} />)
            ) : (
              <div className="col-span-full py-20 text-center">
                <p className="text-neutral-400 mb-4">
                  {search ? "未找到匹配的视频" : "还没有视频"}
                </p>
              </div>
            )}

            {/* Add New Card */}
            <div
              className="border-2 border-dashed border-neutral-200 rounded-2xl flex flex-col items-center justify-center text-neutral-400 hover:border-neutral-400 hover:text-neutral-600 hover:bg-neutral-50 transition-all cursor-pointer min-h-[240px]"
              onClick={() => setViewMode("bilibili")}
            >
              <div className="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center mb-3">
                <Plus className="w-6 h-6" />
              </div>
              <span className="text-sm font-medium">从B站导入</span>
            </div>
          </div>
        </>
      ) : selectedFolder ? (
        /* 收藏夹详情视图 */
        <div>
          <button
            onClick={handleBackToFolders}
            className="flex items-center gap-2 text-neutral-500 hover:text-neutral-900 mb-6 text-sm"
          >
            <span>&larr;</span> 返回收藏夹列表
          </button>
          
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-medium text-neutral-900">{selectedFolder.title}</h2>
              <p className="text-sm text-neutral-500 mt-1">
                {selectedFolder.media_count} 个视频
                {selectedFolder.folder_type === "season" && " (合集)"}
              </p>
            </div>
            <button
              onClick={() => openAddModal(selectedFolder)}
              disabled={addingFolder === selectedFolder.id}
              className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
            >
              {addingFolder === selectedFolder.id ? "添加中..." : "添加到监控"}
            </button>
          </div>

          {folderDetailLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
            </div>
          ) : folderDetail ? (
            <div className="space-y-3">
              {folderDetail.videos.map((video) => (
                <BilibiliVideoCard
                  key={video.bvid}
                  video={video}
                  onImport={handleImportVideo}
                  importing={importingVideo === video.bvid}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        /* B站收藏夹列表视图 */
        <div>
          {bilibiliLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
            </div>
          ) : !bilibiliFolders ? (
            <div className="py-20 text-center">
              <Tv className="w-16 h-16 mx-auto text-neutral-300 mb-4" />
              <p className="text-neutral-500 mb-4">请先在设置中绑定B站账号</p>
              <button
                onClick={() => router.push("/home/settings")}
                className="px-4 py-2 bg-pink-500 text-white rounded-xl text-sm font-medium hover:bg-pink-600"
              >
                前往绑定
              </button>
            </div>
          ) : (
            <div className="space-y-8">
              {/* 我创建的收藏夹 */}
              {bilibiliFolders.created.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-neutral-500 mb-4 flex items-center gap-2">
                    <FolderHeart className="w-4 h-4" />
                    我的收藏夹
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {bilibiliFolders.created.map((folder) => (
                      <FolderCard
                        key={folder.id}
                        folder={folder}
                        onAdd={openAddModal}
                        onOpen={handleOpenFolder}
                        adding={addingFolder === folder.id}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 订阅的收藏夹 */}
              {bilibiliFolders.collected_folders.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-neutral-500 mb-4 flex items-center gap-2">
                    <FolderHeart className="w-4 h-4" />
                    订阅的收藏夹
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {bilibiliFolders.collected_folders.map((folder) => (
                      <FolderCard
                        key={folder.id}
                        folder={folder}
                        onAdd={openAddModal}
                        onOpen={handleOpenFolder}
                        adding={addingFolder === folder.id}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 订阅的合集 */}
              {bilibiliFolders.collected_seasons.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-neutral-500 mb-4 flex items-center gap-2">
                    <Play className="w-4 h-4" />
                    订阅的合集
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {bilibiliFolders.collected_seasons.map((folder) => (
                      <FolderCard
                        key={folder.id}
                        folder={folder}
                        onAdd={openAddModal}
                        onOpen={handleOpenFolder}
                        adding={addingFolder === folder.id}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 空状态 */}
              {bilibiliFolders.created.length === 0 &&
                bilibiliFolders.collected_folders.length === 0 &&
                bilibiliFolders.collected_seasons.length === 0 && (
                  <div className="py-20 text-center">
                    <p className="text-neutral-400">暂无收藏夹</p>
                  </div>
                )}
            </div>
          )}
        </div>
      )}

      {/* 添加收藏夹弹窗 */}
      {addModalFolder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-neutral-900 mb-2">
              添加到监控
            </h3>
            <p className="text-sm text-neutral-500 mb-4">
              {addModalFolder.title} ({addModalFolder.media_count}个视频)
            </p>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-neutral-700 mb-2">
                导入方式
              </label>
              <select
                value={importMode}
                onChange={(e) => setImportMode(e.target.value as 'all' | 'new')}
                className="w-full px-3 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              >
                <option value="all">导入全部视频</option>
                <option value="new">仅监控新视频</option>
              </select>
              <p className="text-xs text-neutral-400 mt-2">
                {importMode === 'all' 
                  ? "立即导入收藏夹中的所有视频到知识库" 
                  : "仅监控之后新增的视频，不导入历史内容"}
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setAddModalFolder(null)}
                className="flex-1 px-4 py-2 border border-neutral-200 rounded-xl text-sm font-medium text-neutral-600 hover:bg-neutral-50"
              >
                取消
              </button>
              <button
                onClick={confirmAddFolder}
                className="flex-1 px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800"
              >
                确认添加
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={<div className="p-10">加载中...</div>}>
      <LibraryContent />
    </Suspense>
  );
}
