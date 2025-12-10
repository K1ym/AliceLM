# 🧠 AliceLM 愿景与实现分析

> 说明：本文件保留为 2024-12 的愿景解读与历史分析，内容未随代码演进更新。当前的路线图与实现状态请参考 `docs/strategy/ROADMAP.md` 与 `docs/strategy/ai_project_audit/08_upgrade_roadmap.md`（原 `1204PLAN.md` 已删除）。

---

## 核心洞察

### 1. "大 Alice" 的本质

读完 1204PLAN.md，我理解到这不是一个简单的功能列表，而是一个**设计哲学的转变**：

```
传统 AI 助手:
  每次对话 = 独立的问答
  用户 → 问题 → AI → 答案
  无状态，无记忆，无人格

大 Alice 设计:
  租户 = 一个完整的 Alice 实例
  所有入口 = 同一个 Alice 的不同"面具"
  所有对话 → 写入统一的时间线 + 记忆
  有人格，有偏好，有成长
```

**关键抽象**：
- `大 Alice` = 租户级人格 + 记忆 + 能力总线
- `对话 Alice` = 某个入口的"一次具体使用形态"

这意味着：**永远只有一个 Alice，UI 里出现的是她的不同"面具"和"工作模式"**。

---

## 2. 四份文档的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        文档关系图                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1204PLAN.md (愿景层)                                            │
│  └── "大 Alice"设计哲学                                          │
│  └── 功能思维导图                                                │
│  └── Level 0-4 能力层级                                          │
│           │                                                      │
│           │ 指导                                                  │
│           ▼                                                      │
│  AGENT_RESEARCH.md (调研层)                                      │
│  └── 4个开源项目深度分析                                         │
│  └── SurfSense: 最接近 AliceLM 定位                              │
│  └── 技术选型参考                                                │
│           │                                                      │
│           │ 借鉴                                                  │
│           ▼                                                      │
│  DESIGN.md (设计层)                                              │
│  └── 插件架构                                                    │
│  └── 多租户数据模型                                              │
│  └── RAGFlow 集成设计                                            │
│           │                                                      │
│           │ 实现                                                  │
│           ▼                                                      │
│  BACKEND_ARCHITECTURE.md (工程层)                                │
│  └── 分层架构: Router → Service → Repository                     │
│  └── Provider 模式                                               │
│  └── 当前代码结构                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 1204PLAN 的能力树解构

### 3.1 知识 & 信息底座 (SurfSense + graph-rag-agent 风格)

| 设计目标 | 现有实现 | 差距 |
|---------|---------|------|
| Source Connectors 统一接口 | ✅ Bilibili 专用 | 缺抽象层 |
| 统一 Ingestion Pipeline | ✅ VideoPipeline | 已有，可扩展 |
| 智能分块 + 嵌入 | ✅ ChromaDB | ⚠️ 单层，无 Reranker |
| 知识图谱 (实体/关系) | ⚠️ ConceptNode/Edge | 缺多 hop 查询 |
| graph.search / graph.neighbors | ⚠️ 基础实现 | 需升级 |

**关键洞察**：
```python
# 现有 (services/knowledge/graph.py)
KnowledgeGraphService:
  - build_graph()         # ✅ 构建
  - get_concept_videos()  # ✅ 概念→视频
  - get_related_concepts() # ⚠️ 仅共现

# 需要的 (1204PLAN 设计)
GraphService:
  - search(query)         # 语义搜索
  - neighbors(node_id)    # 邻居节点
  - walk_path(start, end) # 路径探索
  - multi_hop_qa(question) # 多跳问答
```

### 3.2 Agent 大脑 (OpenManus + Gemini CLI 风格)

| 设计目标 | 现有实现 | 差距 |
|---------|---------|------|
| AgentOrchestrator 统一入口 | ❌ 无 | 核心缺失 |
| ReAct 循环 | ❌ 无 | 需实现 |
| Tool Calling | ❌ 无 | 需实现 |
| Planning (任务分解) | ❌ 无 | 高级能力 |
| Tools Registry | ❌ 无 | 需实现 |

**这是最大的差距**。当前问答流程：
```python
# 现有 (固定流程)
def answer_question(question):
    context = rag_search(question)
    return llm_generate(context, question)

# 需要的 (Agent 化)
async def answer_question(question):
    task = AgentTask(question=question, scene="chat")
    return await AgentOrchestrator.run(task)
    # 内部: ReAct 循环，动态选工具，多步推理
```

### 3.3 大 Alice 层 (租户共生 + 时间线)

| 设计目标 | 现有实现 | 差距 |
|---------|---------|------|
| TenantProfile | ⚠️ TenantConfig (KV) | 需结构化 |
| UserProfile | ⚠️ UserConfig (KV) | 需结构化 |
| AliceIdentityService | ❌ 无 | 核心缺失 |
| ContextAssembler | ❌ 无 | 核心缺失 |
| TimelineEvent | ⚠️ LearningRecord | 雏形存在 |
| PersonaSnapshot | ❌ 无 | 需实现 |
| timeline.analyze_change | ❌ 无 | 高级能力 |

**关键洞察**：`LearningRecord` 是时间线的雏形：
```python
# 现有
LearningRecord:
  - action: viewed / asked / reviewed / exported
  - duration
  - extra_data (JSON)

# 需要的
TimelineEvent:
  - event_type: watch_video / ask_question / highlight / insight / plan_created
  - context: scene / related_videos / related_concepts
  - metadata: 更丰富
  
PersonaSnapshot:
  - period: 时间范围
  - topics: 主题分布
  - questions: 问题模式
  - changes: 观点变化
```

### 3.4 横切能力

| 能力 | 设计目标 | 现有 | 差距 |
|------|---------|------|------|
| **可观测性** | agent_runs 日志 | ❌ | 需实现 |
| **评测体系** | eval_cases / eval_runs | ❌ | 需实现 |
| **权限安全** | 工具级 scope | ⚠️ 基础 RBAC | 需细化 |
| **插件扩展** | Source/Tool Provider | ⚠️ Provider 模式 | 可扩展 |
| **协作** | 多用户共享 | ⚠️ 多租户 | 需增强 |

---

## 4. 服务架构映射

### 4.1 1204PLAN 设计的三个核心服务

```
┌─────────────────────────────────────────────────────────────────┐
│                   1204PLAN 服务架构                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  AliceIdentityService (人格生成器)                               │
│  ├── 输入: tenant_id, user_id                                   │
│  └── 输出:                                                       │
│      ├── system_prompt (Alice 人格)                              │
│      ├── available_tools (按权限过滤)                            │
│      └── settings (语言/风格/简洁度)                             │
│                                                                  │
│  ContextAssembler (上下文装配器)                                  │
│  ├── 输入: task (chat / library / graph / timeline)             │
│  └── 输出:                                                       │
│      ├── recent_messages (短期记忆)                              │
│      ├── knowledge_context (知识上下文)                          │
│      └── persona_snapshot (长期记忆精简版)                       │
│                                                                  │
│  TimelineService (时间线服务)                                     │
│  ├── append_event(event)                                         │
│  ├── query(user_id, filters)                                     │
│  └── analyze_change(user_id, period)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 现有代码对照

```
现有代码结构:
apps/api/services/
├── video_service.py      → 继续使用
├── chat_service.py       → 升级为调用 AgentOrchestrator
├── config_service.py     → 扩展为 AliceIdentityService 一部分
├── bilibili_service.py   → 继续使用
└── auth_service.py       → 继续使用

需要新增:
services/alice/
├── identity_service.py   # AliceIdentityService
├── context_assembler.py  # ContextAssembler
└── timeline_service.py   # TimelineService

services/agent/
├── orchestrator.py       # AgentOrchestrator
├── tools_registry.py     # 工具注册表
└── tools/                # 具体工具
    ├── search_videos.py
    ├── ask_video.py
    ├── search_graph.py
    └── timeline_query.py
```

---

## 5. 请求链对比

### 5.1 现有请求链

```
用户问题
    │
    ▼
[API Router] → ChatService.answer()
    │
    ▼
[固定流程]
  1. RAG 检索 (ChromaDB)
  2. LLM 生成
    │
    ▼
返回答案
```

### 5.2 1204PLAN 设计的请求链

```
用户问题 (任意入口: Web / 微信 / MCP / 视频侧栏)
    │
    ▼
[API Gateway + Auth] 注入 tenant_id / user_id / session_id
    │
    ▼
[Conversation API]
  1. 调 AliceIdentityService → 获取人格 + 工具列表
  2. 调 ContextAssembler → 组装上下文
    │
    ▼
[AgentOrchestrator.run(task)]
  - 用 Persona + Context 构造 messages
  - ReAct / Tools / Planning 循环
  - 记录 agent_run 日志
    │
    ▼
[Agent 输出答案]
  ├─→ TimelineService.append_event() # 记录事件
  ├─→ 可选更新 knowledge insight
    │
    ▼
[前端展示]
  - 主回答
  - 引用的视频/片段/概念
  - 执行轨迹 (dev 模式)
```

**核心差异**：
1. 统一入口 (scene 参数区分场景)
2. 动态工具选择
3. 事件记录到时间线
4. 可观测的执行轨迹

---

## 6. 前端演进

### 6.1 现有结构

```
/home/
├── page.tsx        # Dashboard + 对话混在一起
├── library/
├── video/[id]/
├── graph/
└── settings/
```

### 6.2 目标结构 (1204PLAN)

```
/home/
├── page.tsx        # Alice Home (总览)
│   ├── 快速对话入口
│   ├── 最近 insight
│   └── 时间线快照
│
├── chat/           # 专注对话 ← 新增
│   ├── 会话列表
│   ├── 对话区 (支持工具调用)
│   └── 上下文面板
│
├── library/
├── video/[id]/     # 右侧增加对话侧栏
├── graph/          # 支持"和 Alice 聊这个概念"
│
├── timeline/       # 新增 ← 核心页面
│   ├── 时间轴展示
│   └── "总结我最近在变什么"
│
├── console/        # 新增 (Dev 向)
│   ├── Agent 运行日志
│   └── 评测结果
│
└── settings/
```

**关键设计**：
- 所有页面右上角 = 同一个 Alice 头像
- chat / video / graph / timeline 右侧可嵌统一对话侧栏
- 强化"大 Alice"感

---

## 7. Level 演进路径

### Level 0 (当前)

```
✅ 多租户后端 + 分层架构
✅ 视频处理 Pipeline
✅ ChromaDB RAG
✅ 基础知识图谱
✅ APScheduler 定时任务
✅ Web + 微信 + MCP 多入口
```

### Level 1: 打通"大 Alice"骨架

**目标**：让所有入口看到的都是"同一个 Alice"

**后端任务**：
```python
# 1. 数据模型扩展
class TenantProfile(Base):
    persona_name: str           # Alice 的名字
    persona_style: str          # 语气风格
    enabled_tools: List[str]    # 启用的工具
    preferences: JSON           # 偏好设置

class TimelineEvent(Base):
    event_type: str             # watch / ask / highlight / insight
    scene: str                  # chat / library / graph
    context: JSON               # 相关视频/概念
    created_at: datetime

class PersonaSnapshot(Base):
    period_start: datetime
    period_end: datetime
    topics: JSON                # 主题分布
    patterns: JSON              # 问题模式
    changes: JSON               # 变化分析

# 2. 核心服务
services/alice/
├── identity_service.py
├── context_assembler.py
└── timeline_service.py
```

**前端任务**：
- 拆分 chat/ 页面
- 新增 timeline/ 页面
- 所有对话请求带 scene 参数

**结果**：有了完整意义上的"大 Alice"，对话只是视图。

### Level 2: Agent 化

**目标**：Alice 能做复杂跨视频/跨概念任务

**后端任务**：
```python
# AgentOrchestrator
services/agent/
├── orchestrator.py
│   class AgentOrchestrator:
│       async def run(self, task: AgentTask) -> AgentResult:
│           # ReAct 循环
│           while not done:
│               thought = await self.think(context)
│               action = await self.select_tool(thought)
│               observation = await self.execute_tool(action)
│               context.append(observation)
│
├── tools_registry.py
│   class ToolsRegistry:
│       def register(self, tool: Tool)
│       def get_tools(self, scope: List[str]) -> List[Tool]
│
└── tools/
    ├── search_videos.py
    ├── get_video_detail.py
    ├── ask_video.py
    ├── compare_videos.py
    ├── search_graph.py
    ├── get_concept_map.py
    └── timeline_query.py
```

**前端任务**：
- chat 页右侧上下文面板
- graph 页"和 Alice 聊这个概念"
- video 页右侧对话侧栏

### Level 3: 自我变化 & 评测

**目标**：Alice 能"聊你自己在变什么"

**后端任务**：
```python
# TimelineService 升级
async def analyze_change(self, user_id: int, period: str) -> ChangeAnalysis:
    events = await self.query(user_id, period)
    # 分析: 主题变化 / 观点反转 / 绕圈问题
    return ChangeAnalysis(...)

# EvalService
class EvalService:
    async def run_eval(self, case_ids: List[int]) -> EvalResult
    async def get_history(self) -> List[EvalRun]

# 数据模型
class AgentRun(Base):
    task_id: str
    steps: JSON     # [{thought, action, observation}]
    tokens_used: int
    duration_ms: int

class EvalCase(Base):
    question: str
    expected_tools: List[str]
    expected_answer_pattern: str

class EvalResult(Base):
    case_id: int
    run_id: int
    passed: bool
    actual_answer: str
```

**前端任务**：
- console/ 页面
- Agent 轨迹可视化

### Level 4: 权限 / 插件 / 协作

**目标**：AliceLM 可以是团队/社区的共享大脑平台

**后端任务**：
```python
# PluginRegistry
class PluginRegistry:
    def register_source(self, manifest: SourceManifest)
    def register_tool(self, manifest: ToolManifest)

# PermissionService
class PermissionService:
    def check_tool_access(self, user_id, tool_name) -> bool
    def get_user_tools(self, user_id) -> List[str]
```

---

## 8. 技术选型决策

基于 AGENT_RESEARCH.md 的调研：

| 组件 | 选择 | 理由 |
|------|------|------|
| **Agent 框架** | LangGraph (参考 SurfSense) | 成熟、可扩展 |
| **向量存储** | 保持 ChromaDB | 轻量够用，可升级 pgvector |
| **图谱存储** | 表结构 (现有) | 避免引入 Neo4j 复杂度 |
| **LLM** | 保持 OpenAI 兼容 | 已有 LiteLLM 雏形 |
| **任务队列** | 保持 APScheduler | 已有，稳定 |

**关于 LangGraph vs 自建**：

```
自建优势:
  - 完全控制
  - 无额外依赖

LangGraph 优势:
  - 成熟的 ReAct 实现
  - 可视化调试
  - 社区支持

建议: 先用 LangGraph，理解后可自建简化版
```

---

## 9. 关键实现顺序

```
┌─────────────────────────────────────────────────────────────────┐
│                      实现依赖图                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [数据模型]                                                       │
│  TenantProfile / TimelineEvent / PersonaSnapshot                 │
│       │                                                          │
│       ▼                                                          │
│  [AliceIdentityService]                                          │
│  └── 依赖: TenantProfile                                         │
│       │                                                          │
│       ▼                                                          │
│  [TimelineService]                                               │
│  └── 依赖: TimelineEvent                                         │
│       │                                                          │
│       ▼                                                          │
│  [ContextAssembler]                                              │
│  └── 依赖: AliceIdentityService + TimelineService               │
│       │                                                          │
│       ▼                                                          │
│  [ToolsRegistry + 基础工具]                                       │
│  └── 封装现有服务                                                │
│       │                                                          │
│       ▼                                                          │
│  [AgentOrchestrator]                                             │
│  └── 依赖: ContextAssembler + ToolsRegistry                     │
│       │                                                          │
│       ▼                                                          │
│  [前端改造]                                                       │
│  └── chat / timeline / console                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. 总结

### 核心理解

1. **大 Alice 不是功能，是哲学**
   - 从"工具"到"长期陪伴者"
   - 从"多次对话"到"统一人格 + 时间线"

2. **现有代码库是扎实的基础**
   - 分层架构 ✅
   - 多租户 ✅
   - Provider 模式 ✅
   - 定时任务 ✅

3. **核心差距是三个服务**
   - AliceIdentityService
   - ContextAssembler
   - AgentOrchestrator

4. **最大的飞跃是 Level 2 → Agent 化**
   - 从固定流程到动态推理
   - 从单步问答到多步规划

5. **SurfSense 是最好的参考**
   - LangGraph 工作流
   - 2层 RAG
   - 引用格式
   - 相似的技术栈

---

## 11. 前端体验设计（新增 Forweb 部分）

1204PLAN 新增了完整的前端 UX 设计说明书，这是将"大 Alice"哲学落地到用户体验的关键。

### 11.1 四大 UX 设计原则

| 原则 | 含义 | 设计体现 |
|------|------|---------|
| **One Alice, Multi Surfaces** | 一体多面 | 同一个 Alice 在不同页面呈现不同"形态" |
| **World × Me × We** | 三重视角 | 世界(知识) / 自我(变化) / 共创(计划) |
| **Agent 可见性** | 让"她在干嘛"可感知 | 状态 orb + 工具调用面板 |
| **Calm Depth** | 深但不吓人 | 默认柔和，高级功能藏一层 |

### 11.2 视觉风格 (VI)

```
配色方案:
  背景: 暗蓝灰 (#050814 / #0B1018)
  主色: 暖珊瑚/橘粉 (Her 的情绪感)
  辅色: 青绿/蓝 (图谱 & 线条)

形状语言:
  - 圆角偏大，布局偏网格
  - 带光晕的卡片/节点
  - Alice orb: 思考时呼吸、旋转几何线条

关键创新:
  - Alice 不是人形，而是有"情绪"的几何光球
  - 贯穿所有页面: 导航/对话气泡/侧栏
```

### 11.3 系统人格 (SI)

**人格关键词**: 观察 / 诚实 / 伴随 / 不油腻

**统一"声音"出口**:
- 首页欢迎语
- Timeline 总结卡片
- 学习路径描述
- 空状态提示文字

**多场景人格一致性**:
| 场景 | 语气 |
|------|------|
| Library | 学术 & 研究 |
| Timeline | 朋友式复盘 |
| Console | 工程师视角 |

### 11.4 全局 Shell 架构

```
┌──────────────────────────────────────────────────────────────────┐
│  Alice orb/logo     搜索栏（搜视频/概念/对话/事件）      用户头像 │
├───────────────┬───────────────────────────────┬─────────────────┤
│  导航栏       │         主内容区域            │   右侧上下文    │
│  - Home       │                               │  - Alice 状态   │
│  - Chat       │                               │  - 引用/工具    │
│  - Library    │                               │  （可折叠）     │
│  - Graph      │                               │                 │
│  - Timeline   │                               │                 │
│  - Tasks/Plan │                               │                 │
│  - Console    │                               │                 │
└───────────────┴───────────────────────────────┴─────────────────┘

关键创新: 右侧上下文栏
  - 类似 ChatGPT Atlas 侧边栏
  - Alice 的"并行思考"放在一侧，不挡主内容
```

### 11.5 核心页面设计要点

| 页面 | 核心功能 | 关键创新 |
|------|---------|---------|
| **Home** | 总览(世界+自我) | 一句话输入框 + 左右双列(World/Me) |
| **Chat** | 多场景对话 | 引用卡片(视频/概念/时间线) + 工具执行状态 |
| **Library** | 知识库 | 每卡片有"Alice 重点" + 多选研究 |
| **Video/[id]** | 视频详情 | 转写选中即问 + mini Chat 侧栏 |
| **Graph** | 知识图谱 | 点击节点即聊 + 概念详情面板 |
| **Timeline** | 自我时间线 | 纵向事件流 + 阶段性总结卡片 |
| **Tasks** | 计划/共创 | 看板式 + 每卡背后有 mini Chat |
| **Console** | 开发者视角 | Agent Runs / Eval / Tools / Plugins |

### 11.6 Chat 页面详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│ 顶部：场景标签 [通用聊天] [关于这台设备] [关于我的世界观]        │
├───────────────┬───────────────────────────────────────────────┤
│ 对话列表      │ 聊天区                                         │
│  - 会话A      │ ┌───────────────────────────────────────┐     │
│  - 会话B      │ │  用户气泡                              │     │
│               │ ├───────────────────────────────────────┤     │
│               │ │  Alice 气泡 + 引用卡片                 │     │
│               │ │   [视频#1片段] [概念卡] [时间线事件]   │     │
│               │ └───────────────────────────────────────┘     │
│               │  底部输入框 + 模式开关（严谨/灵感/...）         │
└───────────────┴───────────────────────────────────────────────┘

创新点:
  - 引用卡片统一样式（不是 [1][2] 脚注，而是可点击卡片）
  - Alice 气泡顶部: "正在查 3 个视频 / 2 个概念..."
```

### 11.7 Timeline 页面详细设计

```
┌─────────────────────────────────────────────────────────────────┐
│ 顶部：时间范围（一周/一月/一年）+ [让 Alice 总结我在变什么]     │
├─────────────────────────────────────────────────────────────────┤
│ 纵向时间线                                                      │
│   ●  今天  看了视频《...》，提问：xxx（标签：Agent）            │
│   │      选中：Alice 的短注释                                   │
│   ●  昨天  标记了 insight：「我想做一个 OS 级 Her」             │
│   ●  上周  提问：「我到底应不应该做产品 X」                     │
├─────────────────────────────────────────────────────────────────┤
│ 底部：Alice 的阶段性总结卡片                                    │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ 「最近你在变什么」                                    │     │
│  │ - 兴趣从 A → B                                        │     │
│  │ - 对话中怀疑减少，规划类问题增多                      │     │
│  │ - 有一个绕圈问题：...                                 │     │
│  │  [展开细节] [和 Alice 深聊这几点]                     │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 11.8 前端路由结构

```
app/
└── home/
    ├── page.tsx           # Alice Home（总览）
    ├── chat/
    │   └── page.tsx       # 对话 Alice
    ├── library/
    │   └── page.tsx       # 知识库
    ├── video/[id]/
    │   └── page.tsx       # 视频详情 + 侧边 Alice
    ├── graph/
    │   └── page.tsx       # 知识图谱
    ├── timeline/          # ← 新增
    │   └── page.tsx       # 时间线 & 自我变化
    ├── tasks/             # ← 新增
    │   └── page.tsx       # 计划 / 项目共创
    ├── console/           # ← 新增
    │   └── page.tsx       # Dev Console / Eval
    └── settings/
        └── page.tsx       # Persona / 工具 / 权限
```

### 11.9 前端实现优先级

```
Phase 1: 基础框架
  ├── 全局 Shell (三栏布局 + Alice orb)
  ├── Home 页面改造
  └── 统一的右侧上下文栏组件

Phase 2: 核心页面
  ├── Chat 页面拆分 + 引用卡片
  ├── Timeline 页面新增
  └── Video 页面侧栏 mini Chat

Phase 3: 高级页面
  ├── Tasks/Plan 看板
  ├── Graph 交互升级
  └── Console 开发者面板

Phase 4: 视觉打磨
  ├── Alice orb 动效
  ├── 暗色主题优化
  └── 响应式适配
```

---

## 12. 综合实现路径

结合后端 Level 和前端 Phase：

```
┌─────────────────────────────────────────────────────────────────┐
│                      实现路径总览                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Sprint 1: 大 Alice 骨架                                         │
│  ├── 后端: TimelineEvent 模型 + TimelineService                  │
│  ├── 后端: AliceIdentityService                                  │
│  └── 前端: 全局 Shell + Home 改造                                │
│                                                                  │
│  Sprint 2: Timeline 页面                                         │
│  ├── 后端: TimelineService.query() API                           │
│  ├── 前端: timeline/ 页面                                        │
│  └── 前端: 时间线事件卡片组件                                    │
│                                                                  │
│  Sprint 3: Chat 升级                                             │
│  ├── 后端: ContextAssembler                                      │
│  ├── 前端: Chat 页面拆分                                         │
│  └── 前端: 引用卡片组件 (视频/概念/时间线)                       │
│                                                                  │
│  Sprint 4: Agent 化                                              │
│  ├── 后端: AgentOrchestrator + ToolsRegistry                     │
│  ├── 前端: 工具执行状态组件                                      │
│  └── 前端: 右侧上下文栏                                          │
│                                                                  │
│  Sprint 5: 完善                                                  │
│  ├── 后端: analyze_change() 变化分析                             │
│  ├── 前端: Timeline 总结卡片                                     │
│  └── 前端: Tasks/Plan + Console                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*文档版本: v1.1*
*更新时间: 2024-12-04*
*新增: 前端体验设计部分 (Section 11-12)*
*目的: 深度理解 1204PLAN 设计哲学，对照现有代码库，规划演进路径*
