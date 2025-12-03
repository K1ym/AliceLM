# BiLearner Frontend Generation Prompt

## 核心理念 (最重要)

BiLearner 不是视频管理工具，是**知识对话助手**。

设计哲学：
- **Conversation-First**: 对话是核心，不是视频网格
- **Zero-Friction**: 一个输入框解决所有需求（提问/导入/搜索）
- **Warm Minimal**: 温暖的极简，有温度的文案
- **Depth over Decoration**: 用层次感代替装饰

用户打开应用的感受应该是：
> "这是我的知识助手，我可以问它任何学过的东西"

而不是：
> "这是一个管理我视频的后台"

---

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS v4
- **Components**: shadcn/ui (覆盖默认样式)
- **Icons**: Lucide React
- **State**: React Query + Zustand
- **Animation**: Framer Motion (克制使用)

---

## Layout: Conversation-First Architecture

**像ChatGPT，不像Notion**

```
┌─────────────────────────────────────────────────────────────────────────┐
│   BiLearner                                              [?] [Avatar]   │
├─────────────────────┬───────────────────────────────────────────────────┤
│                     │                                                   │
│   + 新对话          │                                                   │
│                     │                                                   │
│   ─────────────     │           "有什么想知道的？"                       │
│   最近对话          │                                                   │
│   ─────────────     │     你的知识库有 42 个视频，涵盖                   │
│                     │     技术 / 设计 / 商业 等领域                      │
│   设计思维是什么    │                                                   │
│   3小时前           │     ┌───────────────────────────────────────┐     │
│                     │     │ 问任何问题，或粘贴B站链接导入...       │     │
│   React性能优化     │     └───────────────────────────────────────┘     │
│   昨天              │                                                   │
│                     │              (大量留白)                           │
│   ─────────────     │                                                   │
│   视频库 (42)   >   │     最近学习   [缩略图] [缩略图] [缩略图]          │
│   设置              │                                                   │
│                     │                                                   │
└─────────────────────┴───────────────────────────────────────────────────┘
        ^                                    ^
   对话历史侧边栏                       主内容区：欢迎 + 输入框
   (240px, 可收起)                     (居中, max-w-2xl, 大量留白)
```

**关键区别**:
| 旧设计 | 新设计 |
|--------|--------|
| 图标导航栏 + 视频网格 | 对话历史 + 输入框 |
| 工具感 | 助手感 |
| 信息密集 | 大量留白 |

### 2. 圆角规格

```css
--radius-sm: 8px;     /* 小按钮 */
--radius-md: 12px;    /* 输入框、图标按钮 */
--radius-lg: 16px;    /* 卡片 */
--radius-xl: 20px;    /* 侧边栏、大容器 */
--radius-full: 9999px; /* 胶囊标签 */
```

### 3. 颜色 - 仅灰度

```css
neutral-50:  #FAFAFA  /* 背景 */
neutral-100: #F5F5F5  /* 卡片背景 */
neutral-200: #E5E5E5  /* 边框 */
neutral-400: #A3A3A3  /* 次要文字 */
neutral-500: #737373  /* 辅助文字 */
neutral-900: #171717  /* 主文字、主按钮 */
```

**禁止**: 紫色、蓝色、渐变、彩色图标

---

## 智能输入框 (核心组件)

**一个输入框，三种意图自动识别**：

```tsx
function SmartInput() {
  const [value, setValue] = useState('');
  const [intent, setIntent] = useState<'idle' | 'import' | 'ask' | 'search'>('idle');
  
  useEffect(() => {
    if (value.includes('bilibili.com') || value.startsWith('BV')) {
      setIntent('import');
    } else if (value.endsWith('?') || /^(什么|如何|为什么|怎么)/.test(value)) {
      setIntent('ask');
    } else if (value.length > 0) {
      setIntent('search');
    } else {
      setIntent('idle');
    }
  }, [value]);
  
  return (
    <div className="relative">
      <input
        value={value}
        onChange={e => setValue(e.target.value)}
        placeholder="问任何问题，或粘贴B站链接导入..."
        className="w-full px-5 py-4 text-lg rounded-2xl border border-neutral-200 
                   focus:border-neutral-400 focus:ring-0 transition-all
                   shadow-sm hover:shadow-md"
      />
      
      {/* 导入意图：显示视频预览卡片 */}
      {intent === 'import' && <ImportPreviewCard url={value} />}
      
      {/* 搜索意图：显示匹配视频 */}
      {intent === 'search' && <SearchResults query={value} />}
    </div>
  );
}
```

---

## 视觉质感 (Depth over Decoration)

**不是扁平，而是有层次的纸质感**：

```tsx
// 输入框：微微浮起
className="shadow-sm hover:shadow-md transition-shadow"

// 卡片：真实的纸感
className="bg-white rounded-xl border border-neutral-100 shadow-sm 
           hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"

// 侧边栏：轻微分隔
className="border-r border-neutral-100"  // 不是 border-neutral-200，更轻

// 加载状态：呼吸效果，不是转圈
className="animate-pulse bg-neutral-100"
```

**微交互**：
```tsx
// 按钮按下效果
className="active:scale-95 transition-transform"

// 列表项悬停
className="hover:bg-neutral-50 rounded-lg transition-colors"
```

---

## Pages to Create

### P0 - 首屏体验

1. **全局 Layout** (`/dashboard/layout.tsx`)
   - 左侧：对话历史侧边栏 (240px, 可收起)
   - 顶部：极简顶栏 (logo + 头像)
   - 中央：主内容区 (max-w-2xl, 居中)

2. **Welcome + 对话** (`/dashboard/page.tsx`)
   - 欢迎语（根据时间变化）
   - 上下文提示（"42个视频..."）
   - 智能输入框（核心）
   - 最近学习（小缩略图）
   - 对话开始后平滑过渡到对话UI

3. **视频库** (`/dashboard/library/page.tsx`)
   - 搜索框
   - 状态筛选
   - 视频卡片网格

4. **视频详情** (`/dashboard/video/[id]/page.tsx`)
   - B站嵌入播放器
   - Tab: 摘要 / 转写 / 问答
   - 时间戳点击跳转

### P1 - 补充功能

5. **设置页面** - ASR/LLM配置
6. **导入预览卡片** - 粘贴URL后的浮层

## UX Requirements (必须遵守)

1. **空状态**: 必须有引导文案和操作按钮
2. **处理状态**: 显示进度条和预计时间
3. **流式响应**: 对话使用打字机效果
4. **快捷键**: 支持 ⌘+K 搜索
5. **错误提示**: 友好文案 + 可执行动作
6. **响应式**: 移动端侧边栏收起为底部导航

## File Structure

```
apps/web/src/
├── app/
│   └── dashboard/
│       ├── layout.tsx        # 全局布局
│       ├── page.tsx          # 首页
│       ├── library/
│       │   └── page.tsx      # 视频库
│       ├── video/
│       │   └── [id]/
│       │       └── page.tsx  # 视频详情
│       ├── chat/
│       │   └── page.tsx      # 对话
│       └── settings/
│           └── page.tsx      # 设置
├── components/
│   ├── layout/
│   │   ├── floating-sidebar.tsx
│   │   ├── top-bar.tsx
│   │   └── nav-button.tsx
│   ├── dashboard/
│   │   ├── central-input.tsx
│   │   ├── video-card.tsx
│   │   ├── video-grid.tsx
│   │   ├── processing-list.tsx
│   │   └── empty-state.tsx
│   ├── video/
│   │   ├── summary-tab.tsx
│   │   ├── transcript-tab.tsx
│   │   └── qa-tab.tsx
│   └── chat/
│       ├── message-bubble.tsx
│       ├── citation-card.tsx
│       └── chat-input.tsx
└── lib/
    ├── api.ts               # API 调用封装
    └── stores/              # Zustand stores
```

## API Endpoints (Mock Data First)

先用 mock 数据，后续接入真实 API：

```typescript
// 视频列表
GET /api/videos -> Video[]

// 视频详情
GET /api/videos/[id] -> VideoDetail

// 对话
POST /api/chat -> StreamResponse

// 导入
POST /api/videos -> { id, status }
```

## Output Requirements

1. 生成完整可运行的代码
2. 每个文件单独输出，标明路径
3. 使用 TypeScript
4. 包含必要的类型定义
5. 先用 mock 数据让页面可交互
6. 遵循 PRD 中的设计规范和 UX 要求

## Start

请先创建:
1. 全局 Layout (浮动侧边栏 + 顶栏)
2. Dashboard 首页
3. VideoCard 组件

然后我会告诉你继续创建其他页面。

---

**附件**: PRD_FRONTEND.md (完整产品需求文档)
