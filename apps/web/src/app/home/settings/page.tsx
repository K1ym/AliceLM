"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Folder as FolderIcon, Mic, Brain, Bell, RefreshCw, Trash2, Plus, Tv, Loader2, CheckCircle, XCircle, User, LogOut, Eye, EyeOff, Settings2, FileText, RotateCcw, ListTodo, Play, AlertTriangle, HardDrive } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { useRouter } from "next/navigation";
import { configApi, foldersApi, bilibiliApi, authApi, videosApi, systemApi, Folder, ConfigResponse, UserInfo, LLMEndpoint, ModelTaskConfig, ModelTasksConfig, PromptsResponse, ProcessingQueue, QueueVideo, StorageStats } from "@/lib/api";

type SettingsTab = "profile" | "bilibili" | "folders" | "llm" | "model_tasks" | "prompts" | "queue" | "storage" | "notify";

const TABS: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: "profile", label: "个人信息", icon: User },
  { id: "bilibili", label: "B站账号", icon: Tv },
  { id: "folders", label: "收藏夹", icon: FolderIcon },
  { id: "queue", label: "处理队列", icon: ListTodo },
  { id: "storage", label: "存储管理", icon: HardDrive },
  { id: "llm", label: "AI端点", icon: Brain },
  { id: "model_tasks", label: "任务模型", icon: Settings2 },
  { id: "prompts", label: "Prompt", icon: FileText },
  { id: "notify", label: "通知", icon: Bell },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [folders, setFolders] = useState<Folder[]>([]);
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [foldersRes, configRes, userRes] = await Promise.all([
        foldersApi.list(),
        configApi.get(),
        authApi.me(),
      ]);
      if (foldersRes.data) setFolders(foldersRes.data);
      if (configRes.data) setConfig(configRes.data);
      if (userRes.data) setUserInfo(userRes.data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  }

  function handleUserUpdate(user: UserInfo) {
    setUserInfo(user);
  }

  async function handleDeleteFolder(id: number) {
    try {
      await foldersApi.delete(id);
      setFolders(folders.filter((f) => f.id !== id));
    } catch {
      // Ignore
    }
  }

  return (
    <div className="h-full flex flex-col md:flex-row overflow-hidden">
      {/* Sidebar - 移动端横向滚动，桌面端竖向 */}
      <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-neutral-100 bg-white">
        <h1 className="text-xl font-semibold text-neutral-900 p-4 pb-2 md:mb-2 md:px-6">设置</h1>
        <nav className="flex md:flex-col gap-1 px-2 pb-2 md:px-4 md:pb-4 overflow-x-auto scrollbar-hide">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-neutral-100 text-neutral-900"
                  : "text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900"
              }`}
            >
              <tab.icon size={16} />
              <span className="hidden md:inline">{tab.label}</span>
              <span className="md:hidden">{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 md:p-10">
        {loading ? (
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-neutral-200 rounded w-1/3" />
            <div className="h-4 bg-neutral-200 rounded w-2/3" />
          </div>
        ) : (
          <>
            {activeTab === "profile" && (
              <ProfileSection userInfo={userInfo} onUpdate={handleUserUpdate} />
            )}
            {activeTab === "bilibili" && <BilibiliSection />}
            {activeTab === "folders" && (
              <FoldersSection
                folders={folders}
                onDelete={handleDeleteFolder}
                onRefresh={loadData}
              />
            )}
            {activeTab === "queue" && <QueueSection />}
            {activeTab === "storage" && <StorageSection />}
            {activeTab === "llm" && <LLMSection config={config} onRefresh={loadData} />}
            {activeTab === "model_tasks" && <ModelTasksSection config={config} onRefresh={loadData} />}
            {activeTab === "prompts" && <PromptsSection />}
            {activeTab === "notify" && <NotifySection config={config} />}
          </>
        )}
      </div>
    </div>
  );
}

function FoldersSection({
  folders,
  onDelete,
  onRefresh,
}: {
  folders: Folder[];
  onDelete: (id: number) => void;
  onRefresh: () => void;
}) {
  const [newFolderId, setNewFolderId] = useState("");
  const [adding, setAdding] = useState(false);

  async function handleAdd() {
    if (!newFolderId.trim()) return;
    setAdding(true);
    try {
      await foldersApi.add(newFolderId.trim(), "favlist");
      setNewFolderId("");
      onRefresh();
    } catch {
      // Ignore
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">监控的收藏夹</h2>
      <p className="text-sm text-neutral-500 mb-6">
        添加B站收藏夹ID，系统会自动同步新视频
      </p>

      {/* Add new */}
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={newFolderId}
          onChange={(e) => setNewFolderId(e.target.value)}
          placeholder="输入收藏夹ID (如: 12345678)"
          className="flex-1 px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !newFolderId.trim()}
          className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Plus size={16} />
          添加
        </button>
      </div>

      {/* List */}
      <div className="space-y-3">
        {folders.length > 0 ? (
          folders.map((folder) => (
            <div
              key={folder.id}
              className="flex items-center justify-between p-4 bg-white border border-neutral-100 rounded-xl"
            >
              <div>
                <div className="font-medium text-neutral-900">{folder.name}</div>
                <div className="text-xs text-neutral-500 mt-1">
                  {folder.video_count} 个视频
                  {folder.last_scan_at && ` | 上次扫描: ${folder.last_scan_at}`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button className="p-2 text-neutral-400 hover:text-neutral-900 rounded-lg hover:bg-neutral-100">
                  <RefreshCw size={16} />
                </button>
                <button
                  onClick={() => onDelete(folder.id)}
                  className="p-2 text-neutral-400 hover:text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-10 text-neutral-400">
            暂无监控的收藏夹
          </div>
        )}
      </div>
    </div>
  );
}

// ASR提供商配置
const ASR_PROVIDERS = {
  local: [
    { id: "faster_whisper", name: "Faster-Whisper", description: "本地运行，4x加速版Whisper，推荐" },
    { id: "whisper_local", name: "Whisper Local", description: "OpenAI Whisper本地版" },
  ],
  api: [
    { id: "openai_whisper", name: "OpenAI Whisper API", base_url: "https://api.openai.com/v1", models: ["whisper-1"] },
    { id: "groq_whisper", name: "Groq Whisper", base_url: "https://api.groq.com/openai/v1", models: ["whisper-large-v3", "whisper-large-v3-turbo"] },
    { id: "deepgram", name: "Deepgram", base_url: "https://api.deepgram.com/v1", models: ["nova-2", "nova-2-general"] },
  ],
};

const LOCAL_MODEL_SIZES = [
  { id: "tiny", name: "Tiny", desc: "最快，精度低" },
  { id: "base", name: "Base", desc: "" },
  { id: "small", name: "Small", desc: "" },
  { id: "medium", name: "Medium", desc: "推荐" },
  { id: "large", name: "Large", desc: "精度高" },
  { id: "large-v3", name: "Large-v3", desc: "最新版本" },
];

function ASRSection({ config }: { config: ConfigResponse | null }) {
  const [provider, setProvider] = useState(config?.asr?.provider || "faster_whisper");
  const [modelSize, setModelSize] = useState(config?.asr?.model_size || "medium");
  const [apiBaseUrl, setApiBaseUrl] = useState(config?.asr?.api_base_url || "");
  const [apiKey, setApiKey] = useState("");
  const [apiModel, setApiModel] = useState(config?.asr?.api_model || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const isLocalMode = ASR_PROVIDERS.local.some(p => p.id === provider);
  const currentApiProvider = ASR_PROVIDERS.api.find(p => p.id === provider);

  useEffect(() => {
    if (config?.asr) {
      setProvider(config.asr.provider);
      setModelSize(config.asr.model_size);
      setApiBaseUrl(config.asr.api_base_url || "");
      setApiModel(config.asr.api_model || "");
    }
  }, [config]);

  function handleProviderChange(newProvider: string) {
    setProvider(newProvider);
    const apiProvider = ASR_PROVIDERS.api.find(p => p.id === newProvider);
    if (apiProvider) {
      setApiBaseUrl(apiProvider.base_url);
      setApiModel(apiProvider.models[0] || "");
    }
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      await configApi.updateASR({
        provider,
        model_size: modelSize,
        device: "auto",
        api_base_url: isLocalMode ? undefined : apiBaseUrl,
        api_key: isLocalMode ? undefined : (apiKey || undefined),
        api_model: isLocalMode ? undefined : apiModel,
      });
      setMessage({ type: "success", text: "ASR配置已保存" });
      setApiKey("");
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">语音识别设置</h2>
      <p className="text-sm text-neutral-500 mb-6">配置用于转写视频的语音识别服务</p>

      <div className="space-y-4">
        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <label className="block text-sm font-medium text-neutral-900 mb-2">
            服务提供商
          </label>
          <select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
          >
            <optgroup label="本地模式">
              {ASR_PROVIDERS.local.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </optgroup>
            <optgroup label="API模式">
              {ASR_PROVIDERS.api.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </optgroup>
          </select>
        </div>

        {isLocalMode ? (
          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              模型大小
            </label>
            <select
              value={modelSize}
              onChange={(e) => setModelSize(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
            >
              {LOCAL_MODEL_SIZES.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} {s.desc && `(${s.desc})`}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <>
            <div className="p-4 bg-white border border-neutral-100 rounded-xl">
              <label className="block text-sm font-medium text-neutral-900 mb-2">
                API Base URL
              </label>
              <input
                type="text"
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              />
            </div>

            <div className="p-4 bg-white border border-neutral-100 rounded-xl">
              <label className="block text-sm font-medium text-neutral-900 mb-2">
                模型
              </label>
              <select
                value={apiModel}
                onChange={(e) => setApiModel(e.target.value)}
                className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              >
                {currentApiProvider?.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            <div className="p-4 bg-white border border-neutral-100 rounded-xl">
              <label className="block text-sm font-medium text-neutral-900 mb-2">
                API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={config?.asr?.has_api_key ? "已配置 (留空保持不变)" : "输入API Key"}
                className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              />
              {config?.asr?.has_api_key && (
                <p className="text-xs text-green-600 mt-1">API Key 已配置</p>
              )}
            </div>
          </>
        )}

        {message && (
          <p className={`text-sm ${message.type === "success" ? "text-green-600" : "text-red-500"}`}>
            {message.text}
          </p>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={16} className="animate-spin" />}
          保存设置
        </button>
      </div>
    </div>
  );
}

// LLM提供商配置
const LLM_PROVIDERS: Record<string, { base_url: string; default_models: string[] }> = {
  openai: { base_url: "https://api.openai.com/v1", default_models: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"] },
  deepseek: { base_url: "https://api.deepseek.com/v1", default_models: ["deepseek-chat", "deepseek-reasoner"] },
  siliconflow: { base_url: "https://api.siliconflow.cn/v1", default_models: ["Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-V3"] },
  ollama: { base_url: "http://localhost:11434/v1", default_models: ["qwen2.5", "llama3.2", "deepseek-r1:8b"] },
  groq: { base_url: "https://api.groq.com/openai/v1", default_models: ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"] },
};

function LLMSection({ config, onRefresh }: { config: ConfigResponse | null; onRefresh?: () => void }) {
  // 当前使用的配置
  const [selectedEndpoint, setSelectedEndpoint] = useState<string>(""); // 空=预设, 否则=自定义端点id
  const [provider, setProvider] = useState(config?.llm?.provider || "openai");
  const [model, setModel] = useState(config?.llm?.model || "gpt-4o-mini");
  const [baseUrl, setBaseUrl] = useState(config?.llm?.base_url || LLM_PROVIDERS.openai.base_url);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // 添加新端点
  const [showAddEndpoint, setShowAddEndpoint] = useState(false);
  const [newEndpointName, setNewEndpointName] = useState("");
  const [newEndpointUrl, setNewEndpointUrl] = useState("");
  const [newEndpointKey, setNewEndpointKey] = useState("");
  const [addingEndpoint, setAddingEndpoint] = useState(false);

  // 自定义端点列表
  const endpoints = config?.llm_endpoints || [];

  useEffect(() => {
    if (config?.llm) {
      setProvider(config.llm.provider);
      setModel(config.llm.model);
      if (config.llm.base_url) setBaseUrl(config.llm.base_url);
      if (config.llm.endpoint_id) {
        setSelectedEndpoint(config.llm.endpoint_id);
      }
    }
  }, [config]);

  // 初始化可用模型列表
  useEffect(() => {
    if (selectedEndpoint) {
      const ep = endpoints.find(e => e.id === selectedEndpoint);
      if (ep) {
        setAvailableModels(ep.models);
        setBaseUrl(ep.base_url);
      }
    } else {
      const preset = LLM_PROVIDERS[provider];
      if (preset?.default_models.length > 0) {
        setAvailableModels(preset.default_models);
      }
    }
  }, [provider, selectedEndpoint, endpoints]);

  function handleProviderChange(newProvider: string) {
    setSelectedEndpoint("");
    setProvider(newProvider);
    const preset = LLM_PROVIDERS[newProvider];
    if (preset) {
      setBaseUrl(preset.base_url);
      setAvailableModels(preset.default_models);
      if (preset.default_models.length > 0) {
        setModel(preset.default_models[0]);
      }
    }
  }

  function handleEndpointSelect(endpointId: string) {
    if (!endpointId) {
      setSelectedEndpoint("");
      handleProviderChange(provider);
      return;
    }
    const ep = endpoints.find(e => e.id === endpointId);
    if (ep) {
      setSelectedEndpoint(endpointId);
      setBaseUrl(ep.base_url);
      setAvailableModels(ep.models);
      if (ep.models.length > 0) {
        setModel(ep.models[0]);
      }
    }
  }

  async function handleAddEndpoint() {
    if (!newEndpointName || !newEndpointUrl || !newEndpointKey) {
      setMessage({ type: "error", text: "请填写完整信息" });
      return;
    }
    setAddingEndpoint(true);
    setMessage(null);
    try {
      const res = await configApi.createLLMEndpoint({
        name: newEndpointName,
        base_url: newEndpointUrl,
        api_key: newEndpointKey,
      });
      setMessage({ type: "success", text: `端点已添加，获取到 ${res.data.models.length} 个模型` });
      setShowAddEndpoint(false);
      setNewEndpointName("");
      setNewEndpointUrl("");
      setNewEndpointKey("");
      // 延迟刷新确保数据同步
      setTimeout(() => onRefresh?.(), 100);
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "添加失败" });
    } finally {
      setAddingEndpoint(false);
    }
  }

  async function handleDeleteEndpoint(endpointId: string) {
    try {
      await configApi.deleteLLMEndpoint(endpointId);
      if (selectedEndpoint === endpointId) {
        setSelectedEndpoint("");
      }
      onRefresh?.();
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "删除失败" });
    }
  }

  async function handleRefreshEndpoint(endpointId: string) {
    try {
      const res = await configApi.refreshEndpointModels(endpointId);
      setMessage({ type: "success", text: `刷新成功，获取到 ${res.data.models.length} 个模型` });
      onRefresh?.();
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "刷新失败" });
    }
  }

  async function handleSave() {
    // 使用自定义端点时不需要单独的API Key
    if (!selectedEndpoint && !apiKey && !config?.llm?.has_api_key) {
      setMessage({ type: "error", text: "请输入API Key" });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await configApi.updateLLM({
        provider: selectedEndpoint ? "custom_endpoint" : provider,
        model,
        base_url: selectedEndpoint ? undefined : baseUrl,
        api_key: selectedEndpoint ? undefined : (apiKey || undefined),
        endpoint_id: selectedEndpoint || undefined,
      });
      setMessage({ type: "success", text: "LLM配置已保存" });
      setApiKey("");
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">AI模型设置</h2>
      <p className="text-sm text-neutral-500 mb-6">配置用于摘要和问答的大语言模型</p>

      {/* 自定义端点列表 */}
      {endpoints.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-neutral-700">我的API端点</h3>
          </div>
          <div className="space-y-2">
            {endpoints.map((ep) => (
              <div
                key={ep.id}
                className={`p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-colors ${
                  selectedEndpoint === ep.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-neutral-200 hover:border-neutral-300"
                }`}
                onClick={() => handleEndpointSelect(ep.id)}
              >
                <div>
                  <div className="font-medium text-sm">{ep.name}</div>
                  <div className="text-xs text-neutral-500">{ep.base_url}</div>
                  <div className="text-xs text-neutral-400 mt-1">{ep.models.length} 个模型</div>
                </div>
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => handleRefreshEndpoint(ep.id)}
                    className="p-1.5 text-neutral-400 hover:text-blue-600"
                    title="刷新模型列表"
                  >
                    <RefreshCw size={14} />
                  </button>
                  <button
                    onClick={() => handleDeleteEndpoint(ep.id)}
                    className="p-1.5 text-neutral-400 hover:text-red-600"
                    title="删除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 添加新端点 */}
      {showAddEndpoint ? (
        <div className="mb-6 p-4 border border-dashed border-neutral-300 rounded-xl space-y-3">
          <h3 className="text-sm font-medium">添加API端点</h3>
          <input
            type="text"
            value={newEndpointName}
            onChange={(e) => setNewEndpointName(e.target.value)}
            placeholder="名称 (如: My HF Proxy)"
            className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm"
          />
          <input
            type="text"
            value={newEndpointUrl}
            onChange={(e) => setNewEndpointUrl(e.target.value)}
            placeholder="API URL (如: https://xxx.hf.space/v1)"
            className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm"
          />
          <input
            type="password"
            value={newEndpointKey}
            onChange={(e) => setNewEndpointKey(e.target.value)}
            placeholder="API Key"
            className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={handleAddEndpoint}
              disabled={addingEndpoint}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm flex items-center gap-1"
            >
              {addingEndpoint && <Loader2 size={14} className="animate-spin" />}
              添加
            </button>
            <button
              onClick={() => setShowAddEndpoint(false)}
              className="px-3 py-1.5 border border-neutral-200 rounded-lg text-sm"
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAddEndpoint(true)}
          className="mb-6 w-full p-3 border border-dashed border-neutral-300 rounded-xl text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-600 flex items-center justify-center gap-2"
        >
          <Plus size={16} />
          添加自定义API端点
        </button>
      )}

      {/* 预设提供商 */}
      {!selectedEndpoint && (
        <div className="space-y-4">
          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              预设服务商
            </label>
            <select
              value={provider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
            >
              <option value="openai">OpenAI</option>
              <option value="deepseek">DeepSeek</option>
              <option value="siliconflow">SiliconFlow</option>
              <option value="groq">Groq</option>
              <option value="ollama">Ollama (本地)</option>
            </select>
          </div>

          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config?.llm?.has_api_key ? "已配置 (留空保持不变)" : "输入API Key"}
              className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
            />
            {config?.llm?.has_api_key && (
              <p className="text-xs text-green-600 mt-1">API Key 已配置</p>
            )}
          </div>
        </div>
      )}

      {/* 模型选择 */}
      <div className="mt-4 p-4 bg-white border border-neutral-100 rounded-xl">
        <label className="block text-sm font-medium text-neutral-900 mb-2">
          模型
        </label>
        {availableModels.length > 0 ? (
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        ) : (
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="输入模型名称"
            className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
          />
        )}
      </div>

      {message && (
        <p className={`mt-4 text-sm ${message.type === "success" ? "text-green-600" : "text-red-500"}`}>
          {message.text}
        </p>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="mt-4 px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 flex items-center gap-2"
      >
        {saving && <Loader2 size={16} className="animate-spin" />}
        保存设置
      </button>
    </div>
  );
}

// 任务类型配置及其所需的模型类型
const TASK_TYPES = [
  { id: "chat", name: "对话问答", desc: "聊天对话、知识库问答", modelType: "chat" },
  { id: "summary", name: "视频摘要", desc: "生成视频内容摘要", modelType: "chat" },
  { id: "knowledge", name: "知识图谱", desc: "提取知识点和概念关系", modelType: "chat" },
  { id: "mindmap", name: "思维导图", desc: "生成视频内容思维导图", modelType: "chat" },
  { id: "tagger", name: "标签提取", desc: "提取视频主题标签", modelType: "chat" },
  { id: "context_compress", name: "上下文压缩", desc: "超长对话历史压缩", modelType: "chat" },
  { id: "asr", name: "语音识别", desc: "视频音频转文字", modelType: "audio" },
  { id: "embedding", name: "向量化", desc: "RAG知识库向量化", modelType: "embedding" },
] as const;

type TaskType = typeof TASK_TYPES[number]["id"];
type ModelType = "chat" | "embedding" | "audio";

function ModelTasksSection({ config, onRefresh }: { config: ConfigResponse | null; onRefresh?: () => void }) {
  const [tasks, setTasks] = useState<ModelTasksConfig>(config?.model_tasks || {});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const endpoints = config?.llm_endpoints || [];

  // 收集所有可用的模型（来自所有端点）
  const allModels = endpoints.flatMap(ep => ep.models.map(m => ({ model: m, endpointId: ep.id, endpointName: ep.name })));

  useEffect(() => {
    if (config?.model_tasks) {
      setTasks(config.model_tasks);
    }
  }, [config]);

  function handleTaskChange(taskType: TaskType, endpointId: string, model: string) {
    setTasks(prev => ({
      ...prev,
      [taskType]: endpointId ? { endpoint_id: endpointId, model } : undefined,
    }));
  }

  function getSelectedValue(taskType: TaskType) {
    const task = tasks[taskType];
    if (task?.endpoint_id && task?.model) {
      return `${task.endpoint_id}|${task.model}`;
    }
    return "";
  }

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      await configApi.updateModelTasks(tasks);
      setMessage({ type: "success", text: "任务模型配置已保存" });
      onRefresh?.();
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">任务模型配置</h2>
      <p className="text-sm text-neutral-500 mb-6">为不同任务指定不同的AI模型，充分利用各模型优势</p>

      {endpoints.length === 0 ? (
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-center">
          <p className="text-amber-800">请先在"AI端点"页面添加API端点</p>
        </div>
      ) : (
        <div className="space-y-4">
          {TASK_TYPES.map(task => {
            // 根据任务需要的模型类型过滤
            const requiredType = task.modelType as ModelType;
            
            return (
              <div key={task.id} className="p-4 bg-white border border-neutral-100 rounded-xl">
                <div className="mb-3">
                  <div className="font-medium text-neutral-900">{task.name}</div>
                  <div className="text-xs text-neutral-500">{task.desc}</div>
                </div>
                <select
                  value={getSelectedValue(task.id)}
                  onChange={(e) => {
                    const [endpointId, model] = e.target.value.split("|");
                    handleTaskChange(task.id, endpointId, model);
                  }}
                  className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
                >
                  <option value="">使用默认LLM配置</option>
                  {endpoints.map(ep => {
                    // 使用models_with_type过滤，如果没有则显示全部
                    const filteredModels = ep.models_with_type?.length > 0
                      ? ep.models_with_type.filter(m => m.type === requiredType)
                      : ep.models.map(m => ({ id: m, name: m, type: "chat" as const }));
                    
                    if (filteredModels.length === 0) return null;
                    
                    return (
                      <optgroup key={ep.id} label={ep.name}>
                        {filteredModels.map(model => (
                          <option key={`${ep.id}|${model.id}`} value={`${ep.id}|${model.id}`}>
                            {model.name}
                          </option>
                        ))}
                      </optgroup>
                    );
                  })}
                </select>
                {tasks[task.id]?.model && (
                  <p className="text-xs text-green-600 mt-1">
                    已选: {tasks[task.id]?.model}
                  </p>
                )}
              </div>
            );
          })}

          {message && (
            <p className={`text-sm ${message.type === "success" ? "text-green-600" : "text-red-500"}`}>
              {message.text}
            </p>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 size={16} className="animate-spin" />}
            保存配置
          </button>
        </div>
      )}
    </div>
  );
}

function NotifySection({ config }: { config: ConfigResponse | null }) {
  const [wechatEnabled, setWechatEnabled] = useState(config?.notify?.wechat_enabled || false);
  const [webhookUrl, setWebhookUrl] = useState(config?.notify?.webhook_url || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (config?.notify) {
      setWechatEnabled(config.notify.wechat_enabled);
      setWebhookUrl(config.notify.webhook_url || "");
    }
  }, [config]);

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      await configApi.updateNotify({ wechat_enabled: wechatEnabled, webhook_url: webhookUrl || undefined });
      setMessage({ type: "success", text: "通知配置已保存" });
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "保存失败" });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">通知设置</h2>
      <p className="text-sm text-neutral-500 mb-6">配置视频处理完成后的通知方式</p>

      <div className="space-y-4">
        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-neutral-900">企业微信通知</div>
              <div className="text-xs text-neutral-500 mt-1">
                通过Webhook推送处理完成通知
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={wechatEnabled}
                onChange={(e) => setWechatEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-neutral-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-neutral-900"></div>
            </label>
          </div>
        </div>

        <div className="p-4 bg-white border border-neutral-100 rounded-xl">
          <label className="block text-sm font-medium text-neutral-900 mb-2">
            Webhook URL
          </label>
          <input
            type="text"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
            className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
          />
        </div>

        {message && (
          <p className={`text-sm ${message.type === "success" ? "text-green-600" : "text-red-500"}`}>
            {message.text}
          </p>
        )}

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={16} className="animate-spin" />}
          保存设置
        </button>
      </div>
    </div>
  );
}

function ProfileSection({ 
  userInfo, 
  onUpdate 
}: { 
  userInfo: UserInfo | null;
  onUpdate: (user: UserInfo) => void;
}) {
  const router = useRouter();
  const [username, setUsername] = useState(userInfo?.username || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [profileMessage, setProfileMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (userInfo) {
      setUsername(userInfo.username);
    }
  }, [userInfo]);

  async function handleSaveProfile() {
    if (!username.trim()) return;
    setSavingProfile(true);
    setProfileMessage(null);
    try {
      const res = await authApi.updateProfile({ username: username.trim() });
      if (res.data) {
        onUpdate(res.data);
        setProfileMessage({ type: "success", text: "保存成功" });
      }
    } catch (err: any) {
      setProfileMessage({ type: "error", text: err.response?.data?.detail || "保存失败" });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleChangePassword() {
    if (!currentPassword || !newPassword) return;
    if (newPassword !== confirmPassword) {
      setPasswordMessage({ type: "error", text: "两次输入的新密码不一致" });
      return;
    }
    if (newPassword.length < 6) {
      setPasswordMessage({ type: "error", text: "新密码至少6位" });
      return;
    }
    setSavingPassword(true);
    setPasswordMessage(null);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setPasswordMessage({ type: "success", text: "密码修改成功" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPasswordMessage({ type: "error", text: err.response?.data?.detail || "密码修改失败" });
    } finally {
      setSavingPassword(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    router.replace("/login");
  }

  return (
    <div className="max-w-2xl space-y-8">
      {/* 基本信息 */}
      <div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-2">基本信息</h2>
        <p className="text-sm text-neutral-500 mb-6">管理你的账户信息</p>

        <div className="space-y-4">
          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              邮箱
            </label>
            <input
              type="email"
              value={userInfo?.email || ""}
              disabled
              className="w-full px-4 py-2 bg-neutral-50 border border-neutral-200 rounded-xl text-sm text-neutral-500 cursor-not-allowed"
            />
            <p className="text-xs text-neutral-400 mt-1">邮箱不可修改</p>
          </div>

          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
            />
          </div>

          {profileMessage && (
            <p className={`text-sm ${profileMessage.type === "success" ? "text-green-600" : "text-red-500"}`}>
              {profileMessage.text}
            </p>
          )}

          <button
            onClick={handleSaveProfile}
            disabled={savingProfile || !username.trim() || username === userInfo?.username}
            className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {savingProfile && <Loader2 size={16} className="animate-spin" />}
            保存信息
          </button>
        </div>
      </div>

      {/* 修改密码 */}
      <div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-2">修改密码</h2>
        <p className="text-sm text-neutral-500 mb-6">定期修改密码以保护账户安全</p>

        <div className="space-y-4">
          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              当前密码
            </label>
            <div className="relative">
              <input
                type={showCurrentPassword ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-4 py-2 pr-10 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              >
                {showCurrentPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              新密码
            </label>
            <div className="relative">
              <input
                type={showNewPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="至少6位"
                className="w-full px-4 py-2 pr-10 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
              >
                {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="p-4 bg-white border border-neutral-100 rounded-xl">
            <label className="block text-sm font-medium text-neutral-900 mb-2">
              确认新密码
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 border border-neutral-200 rounded-xl text-sm focus:outline-none focus:border-neutral-400"
            />
          </div>

          {passwordMessage && (
            <p className={`text-sm ${passwordMessage.type === "success" ? "text-green-600" : "text-red-500"}`}>
              {passwordMessage.text}
            </p>
          )}

          <button
            onClick={handleChangePassword}
            disabled={savingPassword || !currentPassword || !newPassword || !confirmPassword}
            className="px-4 py-2 bg-neutral-900 text-white rounded-xl text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {savingPassword && <Loader2 size={16} className="animate-spin" />}
            修改密码
          </button>
        </div>
      </div>

      {/* 退出登录 */}
      <div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-2">账户操作</h2>
        <p className="text-sm text-neutral-500 mb-6">退出当前账户</p>

        <button
          onClick={handleLogout}
          className="px-4 py-2 text-red-600 border border-red-200 rounded-xl text-sm font-medium hover:bg-red-50 flex items-center gap-2"
        >
          <LogOut size={16} />
          退出登录
        </button>
      </div>
    </div>
  );
}

function BilibiliSection() {
  const [bindStatus, setBindStatus] = useState<{
    is_bound: boolean;
    bilibili_uid: string | null;
    username: string | null;
    is_vip: boolean;
    is_expired: boolean;
  } | null>(null);
  const [qrcode, setQrcode] = useState<{ url: string; qrcode_key: string } | null>(null);
  const [scanStatus, setScanStatus] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadBindStatus();
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  async function loadBindStatus() {
    try {
      const res = await bilibiliApi.getStatus();
      if (res.data) {
        setBindStatus(res.data);
      }
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  }

  async function generateQRCode() {
    setGenerating(true);
    setScanStatus("");
    try {
      const res = await bilibiliApi.getQRCode();
      if (res.data) {
        setQrcode(res.data);
        startPolling(res.data.qrcode_key);
      }
    } catch {
      setScanStatus("生成二维码失败");
    } finally {
      setGenerating(false);
    }
  }

  function startPolling(qrcode_key: string) {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }

    pollingRef.current = setInterval(async () => {
      try {
        const res = await bilibiliApi.pollQRCode(qrcode_key);
        if (res.data) {
          setScanStatus(res.data.message);
          
          if (res.data.status === "confirmed") {
            clearInterval(pollingRef.current!);
            setQrcode(null);
            loadBindStatus();
          } else if (res.data.status === "expired" || res.data.status === "error") {
            clearInterval(pollingRef.current!);
            setQrcode(null);
          }
        }
      } catch {
        // Ignore
      }
    }, 2000);
  }

  async function handleUnbind() {
    if (!confirm("确定要解绑B站账号吗?")) return;
    
    try {
      await bilibiliApi.unbind();
      setBindStatus({ is_bound: false, bilibili_uid: null, username: null, is_vip: false, is_expired: false });
    } catch {
      // Ignore
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-neutral-200 rounded w-1/3" />
          <div className="h-4 bg-neutral-200 rounded w-2/3" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-lg font-semibold text-neutral-900 mb-2">B站账号绑定</h2>
      <p className="text-sm text-neutral-500 mb-6">
        绑定B站账号后可自动获取收藏夹、下载高清视频
      </p>

      {bindStatus?.is_bound && !qrcode ? (
        <div className={`p-6 bg-white border rounded-xl ${bindStatus.is_expired ? 'border-red-200' : 'border-neutral-100'}`}>
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              bindStatus.is_expired ? 'bg-red-100' : 'bg-pink-100'
            }`}>
              {bindStatus.is_expired ? (
                <XCircle className="text-red-500" size={24} />
              ) : (
                <CheckCircle className="text-pink-500" size={24} />
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-neutral-900">
                  {bindStatus.username || `UID: ${bindStatus.bilibili_uid}`}
                </span>
                {bindStatus.is_vip && (
                  <span className="px-2 py-0.5 bg-pink-100 text-pink-600 text-xs rounded-full font-medium">
                    大会员
                  </span>
                )}
              </div>
              {bindStatus.is_expired ? (
                <div className="text-sm text-red-500 mt-1">
                  登录已过期，请重新绑定
                </div>
              ) : (
                <div className="text-sm text-neutral-500 mt-1">
                  UID: {bindStatus.bilibili_uid}
                </div>
              )}
            </div>
            {bindStatus.is_expired ? (
              <button
                onClick={generateQRCode}
                disabled={generating}
                className="px-4 py-2 bg-pink-500 text-white rounded-lg text-sm font-medium hover:bg-pink-600 disabled:opacity-50"
              >
                重新绑定
              </button>
            ) : (
              <button
                onClick={handleUnbind}
                className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg text-sm font-medium transition-colors"
              >
                解除绑定
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="p-6 bg-white border border-neutral-100 rounded-xl">
          {qrcode ? (
            <div className="flex flex-col items-center">
              <div className="p-4 bg-white rounded-xl border border-neutral-200">
                <QRCodeSVG value={qrcode.url} size={200} />
              </div>
              <div className="mt-4 text-center">
                <p className="text-sm text-neutral-700 font-medium">
                  请使用B站APP扫描二维码
                </p>
                {scanStatus && (
                  <p className={`text-sm mt-2 ${
                    scanStatus.includes("成功") ? "text-green-600" : 
                    scanStatus.includes("失效") ? "text-red-500" : "text-neutral-500"
                  }`}>
                    {scanStatus}
                  </p>
                )}
              </div>
              <button
                onClick={() => {
                  if (pollingRef.current) clearInterval(pollingRef.current);
                  setQrcode(null);
                  setScanStatus("");
                }}
                className="mt-4 px-4 py-2 text-neutral-600 hover:bg-neutral-100 rounded-lg text-sm font-medium transition-colors"
              >
                取消
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center py-8">
              <div className="w-16 h-16 bg-neutral-100 rounded-full flex items-center justify-center mb-4">
                <Tv className="text-neutral-400" size={32} />
              </div>
              <p className="text-neutral-600 mb-4">未绑定B站账号</p>
              <button
                onClick={generateQRCode}
                disabled={generating}
                className="px-6 py-2.5 bg-pink-500 text-white rounded-xl text-sm font-medium hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {generating ? (
                  <>
                    <Loader2 className="animate-spin" size={16} />
                    生成中...
                  </>
                ) : (
                  "扫码绑定B站账号"
                )}
              </button>
              {scanStatus && (
                <p className="text-sm text-red-500 mt-3">{scanStatus}</p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-6 p-4 bg-neutral-50 rounded-xl">
        <h3 className="text-sm font-medium text-neutral-700 mb-2">绑定后可获得</h3>
        <ul className="text-sm text-neutral-500 space-y-1">
          <li>- 自动获取你的B站收藏夹列表</li>
          <li>- 下载1080P高清视频</li>
          <li>- 大会员用户可下载4K视频</li>
          <li>- 自动同步稍后再看</li>
        </ul>
      </div>
    </div>
  );
}


// Prompt配置
function PromptsSection() {
  const [prompts, setPrompts] = useState<PromptsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [editingType, setEditingType] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    try {
      const res = await configApi.getPrompts();
      if (res.data) setPrompts(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(promptType: string) {
    setSaving(promptType);
    try {
      await configApi.updatePrompt(promptType, editContent);
      await loadPrompts();
      setEditingType(null);
    } catch {
      // ignore
    } finally {
      setSaving(null);
    }
  }

  async function handleReset(promptType: string) {
    setSaving(promptType);
    try {
      await configApi.resetPrompt(promptType);
      await loadPrompts();
      setEditingType(null);
    } catch {
      // ignore
    } finally {
      setSaving(null);
    }
  }

  function startEdit(promptType: string) {
    if (!prompts) return;
    const current = prompts.prompts[promptType] || prompts.defaults[promptType] || "";
    setEditContent(current);
    setEditingType(promptType);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!prompts) return null;

  const promptTypes = Object.keys(prompts.defaults);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium text-neutral-900">Prompt 配置</h2>
        <p className="text-sm text-neutral-500 mt-1">
          自定义AI在不同任务中使用的系统提示词
        </p>
      </div>

      <div className="space-y-4">
        {promptTypes.map((type) => {
          const isEditing = editingType === type;
          const hasCustom = !!prompts.prompts[type];
          const currentValue = prompts.prompts[type] || prompts.defaults[type];
          const isStructured = prompts.structured?.includes(type);

          return (
            <div key={type} className={`border rounded-xl p-4 ${isStructured ? "border-amber-200 bg-amber-50/30" : "border-neutral-200"}`}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-medium text-neutral-900">{prompts.descriptions[type]}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-xs text-neutral-500">类型: {type}</p>
                    {isStructured && (
                      <span className="text-xs px-2 py-0.5 bg-amber-100 text-amber-700 rounded">
                        需保持JSON格式
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {hasCustom && (
                    <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                      已自定义
                    </span>
                  )}
                  {!isEditing && (
                    <button
                      onClick={() => startEdit(type)}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      编辑
                    </button>
                  )}
                </div>
              </div>

              {isEditing ? (
                <div className="space-y-3">
                  {isStructured && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                      此prompt需要输出特定JSON格式，修改时请保持格式不变，否则可能导致功能异常。
                    </div>
                  )}
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full h-64 p-3 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 font-mono"
                    placeholder="输入自定义prompt..."
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSave(type)}
                      disabled={saving === type}
                      className="px-4 py-2 bg-neutral-900 text-white text-sm rounded-lg hover:bg-neutral-800 disabled:opacity-50"
                    >
                      {saving === type ? "保存中..." : "保存"}
                    </button>
                    <button
                      onClick={() => setEditingType(null)}
                      className="px-4 py-2 text-neutral-600 text-sm hover:text-neutral-900"
                    >
                      取消
                    </button>
                    {hasCustom && (
                      <button
                        onClick={() => handleReset(type)}
                        disabled={saving === type}
                        className="px-4 py-2 text-red-600 text-sm hover:text-red-700 flex items-center gap-1"
                      >
                        <RotateCcw size={14} />
                        恢复默认
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setEditContent(prompts.defaults[type]);
                      }}
                      className="px-4 py-2 text-neutral-500 text-sm hover:text-neutral-700"
                    >
                      查看默认值
                    </button>
                  </div>
                </div>
              ) : (
                <pre className="text-xs text-neutral-600 bg-neutral-50 p-3 rounded-lg overflow-x-auto max-h-32 overflow-y-auto whitespace-pre-wrap">
                  {currentValue.slice(0, 200)}
                  {currentValue.length > 200 && "..."}
                </pre>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


// 处理队列
function QueueSection() {
  const [queue, setQueue] = useState<ProcessingQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    loadQueue();
    // 每5秒刷新一次
    const interval = setInterval(loadQueue, 5000);
    return () => clearInterval(interval);
  }, []);

  async function loadQueue() {
    try {
      const res = await videosApi.getQueue();
      if (res.data) setQueue(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleProcess(videoId: number) {
    setProcessing(videoId);
    try {
      await videosApi.processNow(videoId);
      await loadQueue();
    } catch {
      // ignore
    } finally {
      setProcessing(null);
    }
  }

  async function handleCancel(videoId: number) {
    if (!confirm("确定要取消此任务吗？")) return;
    try {
      await videosApi.cancelProcess(videoId);
      await loadQueue();
    } catch {
      // ignore
    }
  }

  async function handleRemove(videoId: number) {
    if (!confirm("确定要从队列中移除此视频吗？这将删除视频记录。")) return;
    try {
      await videosApi.removeFromQueue(videoId);
      await loadQueue();
    } catch {
      // ignore
    }
  }

  function formatTime(isoString: string | null): string {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString("zh-CN", { 
      month: "2-digit", 
      day: "2-digit", 
      hour: "2-digit", 
      minute: "2-digit" 
    });
  }

  function getStatusLabel(status: string): { label: string; color: string } {
    switch (status) {
      case "pending": return { label: "等待中", color: "bg-neutral-100 text-neutral-600" };
      case "downloading": return { label: "下载中", color: "bg-blue-100 text-blue-700" };
      case "transcribing": return { label: "转写中", color: "bg-purple-100 text-purple-700" };
      case "analyzing": return { label: "分析中", color: "bg-amber-100 text-amber-700" };
      case "done": return { label: "已完成", color: "bg-green-100 text-green-700" };
      case "failed": return { label: "失败", color: "bg-red-100 text-red-700" };
      default: return { label: status, color: "bg-neutral-100 text-neutral-600" };
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
      </div>
    );
  }

  if (!queue) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium text-neutral-900">处理队列</h2>
          <p className="text-sm text-neutral-500 mt-1">
            查看视频处理状态
          </p>
        </div>
        <button
          onClick={loadQueue}
          className="p-2 hover:bg-neutral-100 rounded-lg text-neutral-500"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {/* 队列统计 */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
          <p className="text-2xl font-bold text-blue-700">{queue.queue_count}</p>
          <p className="text-sm text-blue-600">待处理</p>
        </div>
        <div className="bg-red-50 border border-red-100 rounded-xl p-4">
          <p className="text-2xl font-bold text-red-700">{queue.failed_count}</p>
          <p className="text-sm text-red-600">失败</p>
        </div>
      </div>

      {/* 处理中/待处理 */}
      {queue.queue.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-neutral-700 mb-3">
            处理中 / 待处理 ({queue.queue.length})
          </h3>
          <div className="space-y-2">
            {queue.queue.map((video) => {
              const status = getStatusLabel(video.status);
              return (
                <div
                  key={video.id}
                  className="flex items-center gap-3 p-3 bg-white border border-neutral-200 rounded-xl hover:border-neutral-300 cursor-pointer"
                  onClick={() => router.push(`/home/video/${video.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-900 truncate">{video.title}</p>
                    <p className="text-xs text-neutral-500">{video.bvid} - {formatTime(video.created_at)}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${status.color}`}>
                    {status.label}
                  </span>
                  {video.status === "pending" ? (
                    <div className="flex gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleProcess(video.id); }}
                        disabled={processing === video.id}
                        className="p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        title="开始处理"
                      >
                        {processing === video.id ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Play size={14} />
                        )}
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRemove(video.id); }}
                        className="p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        title="移除"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleCancel(video.id); }}
                      className="p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      title="取消处理"
                    >
                      <XCircle size={14} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 失败列表 */}
      {queue.failed.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
            <AlertTriangle size={16} />
            失败 ({queue.failed.length})
          </h3>
          <div className="space-y-2">
            {queue.failed.map((video) => (
              <div
                key={video.id}
                className="flex items-center gap-3 p-3 bg-red-50 border border-red-100 rounded-xl"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate">{video.title}</p>
                  <p className="text-xs text-red-600 truncate">{video.error_message || "未知错误"}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleProcess(video.id)}
                    disabled={processing === video.id}
                    className="px-3 py-1 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    {processing === video.id ? "重试中..." : "重试"}
                  </button>
                  <button
                    onClick={() => handleRemove(video.id)}
                    className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-100 rounded-lg"
                    title="移除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 最近完成 */}
      {queue.recent_done.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-green-700 mb-3 flex items-center gap-2">
            <CheckCircle size={16} />
            最近完成
          </h3>
          <div className="space-y-2">
            {queue.recent_done.map((video) => (
              <div
                key={video.id}
                className="flex items-center gap-3 p-3 bg-green-50 border border-green-100 rounded-xl cursor-pointer hover:border-green-200"
                onClick={() => router.push(`/home/video/${video.id}`)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate">{video.title}</p>
                  <p className="text-xs text-green-600">{formatTime(video.processed_at)}</p>
                </div>
                <span className="px-2 py-1 text-xs font-medium rounded bg-green-100 text-green-700">
                  已完成
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 空状态 */}
      {queue.queue.length === 0 && queue.failed.length === 0 && queue.recent_done.length === 0 && (
        <div className="text-center py-10 text-neutral-400">
          <ListTodo size={32} className="mx-auto mb-2 opacity-50" />
          暂无任务
        </div>
      )}
    </div>
  );
}

function StorageSection() {
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [cleaning, setCleaning] = useState(false);
  const [cleanResult, setCleanResult] = useState<{ cleaned: number; freed: number } | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  async function loadStats() {
    setLoading(true);
    try {
      const res = await systemApi.getStorage();
      if (res.data) setStats(res.data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleCleanup() {
    if (!confirm("确定要清理已处理视频的临时文件吗？\n\n将删除：音频文件、下载缓存\n保留：转写文本、数据库记录")) {
      return;
    }
    setCleaning(true);
    setCleanResult(null);
    try {
      const res = await systemApi.cleanup(1);
      if (res.data) {
        setCleanResult({ cleaned: res.data.cleaned_count, freed: res.data.freed_mb });
        loadStats();
      }
    } catch {
      // Ignore
    } finally {
      setCleaning(false);
    }
  }

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-neutral-200 rounded w-1/3" />
        <div className="h-32 bg-neutral-200 rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-neutral-900 mb-1">存储管理</h2>
        <p className="text-sm text-neutral-500">查看存储使用情况，清理不需要的临时文件</p>
      </div>

      {stats && (
        <>
          {/* 视频统计 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-neutral-50 rounded-xl p-4">
              <p className="text-2xl font-bold text-neutral-900">{stats.total_videos}</p>
              <p className="text-sm text-neutral-500">总视频数</p>
            </div>
            <div className="bg-green-50 rounded-xl p-4">
              <p className="text-2xl font-bold text-green-700">{stats.processed_videos}</p>
              <p className="text-sm text-green-600">已处理</p>
            </div>
            <div className="bg-amber-50 rounded-xl p-4">
              <p className="text-2xl font-bold text-amber-700">{stats.pending_videos}</p>
              <p className="text-sm text-amber-600">待处理</p>
            </div>
            <div className="bg-red-50 rounded-xl p-4">
              <p className="text-2xl font-bold text-red-700">{stats.failed_videos}</p>
              <p className="text-sm text-red-600">失败</p>
            </div>
          </div>

          {/* 存储使用 */}
          <div className="bg-white border border-neutral-200 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-neutral-700 mb-4">存储使用</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">音频文件</span>
                <span className="text-sm font-medium text-neutral-900">
                  {stats.audio_files_count} 个 / {stats.audio_files_size_mb.toFixed(1)} MB
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">下载缓存</span>
                <span className="text-sm font-medium text-neutral-900">
                  {stats.download_files_size_mb.toFixed(1)} MB
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-neutral-600">转写文本</span>
                <span className="text-sm font-medium text-neutral-900">
                  {stats.transcript_files_size_mb.toFixed(1)} MB
                </span>
              </div>
              <div className="border-t pt-3 flex justify-between items-center">
                <span className="text-sm font-medium text-neutral-700">总计</span>
                <span className="text-base font-bold text-neutral-900">
                  {stats.total_size_mb.toFixed(1)} MB
                </span>
              </div>
            </div>
          </div>

          {/* 清理操作 */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-amber-800 mb-2">清理临时文件</h3>
            <p className="text-sm text-amber-700 mb-4">
              清理处理完成超过1天的音频文件和下载缓存。转写文本和数据库记录将保留。
            </p>
            <div className="flex items-center gap-4">
              <button
                onClick={handleCleanup}
                disabled={cleaning}
                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2"
              >
                {cleaning ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    清理中...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    立即清理
                  </>
                )}
              </button>
              <button
                onClick={loadStats}
                className="px-4 py-2 text-neutral-600 hover:text-neutral-900"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            {cleanResult && (
              <div className="mt-4 p-3 bg-green-100 text-green-800 rounded-lg text-sm">
                清理完成：删除 {cleanResult.cleaned} 个视频的临时文件，释放 {cleanResult.freed.toFixed(1)} MB
              </div>
            )}
          </div>

          {/* 自动清理说明 */}
          <div className="text-sm text-neutral-500">
            <p>系统会在每天凌晨4点自动清理处理完成超过1天的临时文件。</p>
          </div>
        </>
      )}
    </div>
  );
}
