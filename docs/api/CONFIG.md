# 配置管理 API

## 端点概览

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/v1/config` | 获取当前配置 |
| PUT | `/api/v1/config/asr` | 更新ASR配置 |
| PUT | `/api/v1/config/llm` | 更新LLM配置 |
| PUT | `/api/v1/config/notify` | 更新通知配置 |
| GET | `/api/v1/config/asr/providers` | 获取ASR提供商列表 |
| GET | `/api/v1/config/llm/presets` | 获取LLM预设 |

## 功能状态

| 配置项 | 前端支持 | 后端API | 说明 |
|--------|----------|---------|------|
| ASR 模型切换 | 待开发 | ✅ 已实现 | 支持动态切换 |
| LLM 模型切换 | 待开发 | ✅ 已实现 | 支持动态切换 |
| API Key 设置 | 待开发 | ✅ 已实现 | 租户级别存储 |
| 通知设置 | 待开发 | ✅ 已实现 | 支持动态切换 |

---

## GET /api/v1/config

获取当前配置 (API Key 脱敏)

### 响应

```json
{
  "asr": {
    "provider": "faster_whisper",
    "model_size": "medium",
    "device": "auto"
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "base_url": "https://api.openai.com/v1",
    "has_api_key": true
  },
  "notify": {
    "wechat_enabled": false,
    "webhook_url": null
  }
}
```

---

## PUT /api/v1/config/asr

更新 ASR 配置

### 请求

```json
{
  "provider": "faster_whisper",
  "model_size": "large",
  "device": "auto"
}
```

### 响应

```json
{
  "success": true,
  "message": "ASR配置已更新"
}
```

---

## PUT /api/v1/config/llm

更新 LLM 配置

### 请求

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx"
}
```

---

## GET /api/v1/config/asr/providers

获取支持的 ASR 提供商

### 响应

```json
{
  "providers": [
    {"id": "faster_whisper", "name": "Faster-Whisper", "description": "4x加速版"},
    {"id": "whisper_local", "name": "Whisper Local", "description": "OpenAI本地版"},
    {"id": "xunfei", "name": "讯飞语音", "description": "讯飞实时识别"},
    {"id": "openai_whisper", "name": "OpenAI API", "description": "云端API"}
  ],
  "model_sizes": [
    {"id": "tiny", "vram": "1GB", "speed": "32x"},
    {"id": "base", "vram": "1GB", "speed": "16x"},
    {"id": "small", "vram": "2GB", "speed": "6x"},
    {"id": "medium", "vram": "5GB", "speed": "2x"},
    {"id": "large", "vram": "10GB", "speed": "1x"}
  ]
}
```

---

## GET /api/v1/config/llm/presets

获取 LLM 预设配置

### 响应

```json
{
  "presets": [
    {
      "id": "openai",
      "name": "OpenAI",
      "base_url": "https://api.openai.com/v1",
      "models": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
    },
    {
      "id": "deepseek",
      "name": "DeepSeek",
      "base_url": "https://api.deepseek.com/v1",
      "models": ["deepseek-chat", "deepseek-reasoner"]
    }
  ]
}
```

---

## 前端使用示例

```typescript
import { configApi } from '@/lib/api';

// 获取当前配置
const { data: config } = await configApi.get();

// 更新 LLM 配置
await configApi.updateLLM({
  provider: 'openai',
  model: 'gpt-4o',
  base_url: 'https://api.openai.com/v1',
  api_key: 'sk-xxx',
});

// 获取预设
const { data: presets } = await configApi.getLLMPresets();
```

---

## 现有配置方式

### 1. YAML 配置文件

`config/default.yaml`:

```yaml
# ASR配置
asr:
  provider: "faster_whisper"   # whisper_local / faster_whisper / xunfei
  model_size: "medium"         # tiny / base / small / medium / large
  device: "auto"               # auto / cpu / cuda / mps

# LLM配置
llm:
  provider: "openai"
  model: "gpt-4o-mini"
  # base_url: 通过环境变量设置
  # api_key: 通过环境变量设置
```

### 2. 环境变量

```bash
# .env 或 export
export BILI_ASR__PROVIDER="faster_whisper"
export BILI_ASR__MODEL_SIZE="large"

export BILI_LLM__PROVIDER="openai"
export BILI_LLM__MODEL="gpt-4o"
export BILI_LLM__API_KEY="sk-xxx"
export BILI_LLM__BASE_URL="https://api.openai.com/v1"

export BILI_WECHAT__WEBHOOK_URL="https://..."
export BILI_WECHAT__ENABLED="true"
```

### 3. 支持的模型配置

**ASR 模型**:
| Provider | model_size | 说明 |
|----------|------------|------|
| `whisper_local` | tiny/base/small/medium/large | OpenAI Whisper 本地 |
| `faster_whisper` | tiny/base/small/medium/large | 4x 加速版 |
| `xunfei` | - | 讯飞语音识别 |
| `openai_whisper` | whisper-1 | OpenAI API |

**LLM 模型** (OpenAI兼容):
| Provider | base_url | model |
|----------|----------|-------|
| OpenAI | `https://api.openai.com/v1` | gpt-4o-mini / gpt-4o |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat |
| SiliconFlow | `https://api.siliconflow.cn/v1` | Qwen/Qwen2.5-7B |
| Ollama | `http://localhost:11434/v1` | qwen2.5 / llama3.2 |

---

## 需要实现的 API (P2)

### GET /api/v1/config

获取当前配置 (脱敏)

```json
{
  "asr": {
    "provider": "faster_whisper",
    "model_size": "medium",
    "device": "auto"
  },
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "has_api_key": true
  },
  "wechat": {
    "enabled": false
  }
}
```

### PUT /api/v1/config/asr

更新 ASR 配置

```json
{
  "provider": "faster_whisper",
  "model_size": "large"
}
```

### PUT /api/v1/config/llm

更新 LLM 配置

```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key": "sk-xxx",
  "base_url": "https://api.openai.com/v1"
}
```

### PUT /api/v1/config/notify

更新通知配置

```json
{
  "wechat_enabled": true,
  "webhook_url": "https://..."
}
```

---

## 前端 Settings 页面设计

暂时方案：显示只读配置信息 + 引导用户修改配置文件

```
┌─────────────────────────────────────────────────────────────┐
│  设置                                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ASR 语音识别                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  当前: Faster-Whisper (medium)                       │   │
│  │                                                     │   │
│  │  ⚠️ 修改配置请编辑 config/default.yaml              │   │
│  │     或设置环境变量 BILI_ASR__PROVIDER               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  LLM 语言模型                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  当前: OpenAI gpt-4o-mini                            │   │
│  │  API Key: ✅ 已配置                                  │   │
│  │                                                     │   │
│  │  ⚠️ 修改配置请设置环境变量:                          │   │
│  │     BILI_LLM__MODEL=gpt-4o                          │   │
│  │     BILI_LLM__API_KEY=sk-xxx                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [查看完整配置文档]                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 开发计划

| 阶段 | 任务 | 优先级 |
|------|------|--------|
| Phase 1 | 前端显示只读配置 | P1 |
| Phase 2 | 后端实现配置API | P2 |
| Phase 3 | 前端实现配置修改UI | P2 |

---

## 临时解决方案

用户如需更换模型：

1. 停止服务
2. 修改 `config/default.yaml` 或设置环境变量
3. 重启服务

```bash
# 切换到 GPT-4o
export BILI_LLM__MODEL="gpt-4o"

# 切换到 DeepSeek
export BILI_LLM__BASE_URL="https://api.deepseek.com/v1"
export BILI_LLM__MODEL="deepseek-chat"
export BILI_LLM__API_KEY="your-deepseek-key"

# 重启后端
uvicorn apps.api.main:app --reload
```
