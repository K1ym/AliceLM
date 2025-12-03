# AliceLM UI 优化计划

> 基于 Design System v1.1 的实现差距分析与优化路线图

**创建时间:** 2024年12月  
**状态:** 规划中

---

## 一、优先级定义

| 级别 | 定义 | 时间 |
|------|------|------|
| **P0** | 阻塞发布的问题 | 立即 |
| **P1** | 影响用户体验的核心问题 | 本周 |
| **P2** | 提升一致性的优化 | 下周 |
| **P3** | 锦上添花的改进 | 待定 |

---

## 二、P1 优先任务

### 2.1 文案规范化

**问题**: 部分文案不符合 Voice & Tone 规范

| 位置 | 当前 | 修改为 |
|------|------|--------|
| Hero 按钮 | "Get Started" | "开始使用" |
| Sidebar 空状态 | "No conversations" | "暂无对话" |
| Sidebar 空状态 | "Click above to start..." | "点击上方开始新对话" |
| Loading | 各处不统一 | "正在加载..." |
| 搜索占位符 | "Search..." | "搜索..." |

**涉及文件**:
- `apps/web/src/components/landing/hero.tsx`
- `apps/web/src/components/dashboard/Sidebar.tsx`
- `apps/web/src/components/notion-prompt-form.tsx`

---

### 2.2 Chat 页面输入框统一

**问题**: Dashboard 首页用 NotionPromptForm，Chat 页面用简单 textarea

**方案**: Chat 页面也使用 NotionPromptForm（简化版）

**修改**:
```tsx
// apps/web/src/app/dashboard/page.tsx
// 聊天模式下的输入框也使用 NotionPromptForm
<NotionPromptForm 
  onSubmit={handleSendInChat}
  placeholder="继续对话..."
  className="w-full"
/>
```

---

### 2.3 意图系统视觉一致性

**问题**: 意图 Badge 样式在不同组件中不一致

**规范**:
| 意图 | 背景色 | 文字色 | 图标 |
|------|--------|--------|------|
| Ask/AI | bg-amber-50 | text-amber-700 | Sparkles |
| Import | bg-blue-50 | text-blue-700 | Link |
| Search | bg-neutral-100 | text-neutral-600 | Search |

**创建共享组件**: `components/ui/intent-badge.tsx`

---

## 三、P2 优化任务

### 3.1 添加 Design Token 到 CSS

**文件**: `apps/web/src/app/globals.css`

```css
:root {
  /* 语义色 */
  --accent-amber: #F59E0B;
  --accent-blue: #2563EB;
  --accent-green: #10B981;
  --accent-red: #EF4444;
  --accent-pink: #EC4899;
  
  /* 阴影 */
  --shadow-xs: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
  --shadow-focus: 0 0 0 3px rgba(0,0,0,0.1);
  
  /* 动效时长 */
  --duration-fast: 100ms;
  --duration-normal: 200ms;
  --duration-slow: 300ms;
  --duration-slower: 500ms;
  
  /* 缓动函数 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

---

### 3.2 优化 AI 思考状态动画

**当前**: `animate-pulse` (简单闪烁)

**规范**: 呼吸动画 (scale 1.0 - 1.02)

**添加动画**:
```css
@keyframes breathing {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.02); opacity: 0.8; }
}

.animate-breathing {
  animation: breathing 2s ease-in-out infinite;
}
```

---

### 3.3 NotionPromptForm 中文化

**修改项**:
| 当前 | 修改为 |
|------|--------|
| "Add context" | "添加上下文" |
| "Mention a person, page, or date" | "提及页面或日期" |
| "Search pages..." | "搜索页面..." |
| "Pages" | "页面" |
| "Users" | "用户" |
| "Auto" | "自动" |
| "Web search" | "网页搜索" |
| "Connect Apps" | "连接应用" |

---

## 四、P3 改进任务

### 4.1 添加 Skeleton 骨架屏

**场景**:
- 视频列表加载
- 对话历史加载
- 知识库列表加载

**组件**: `components/ui/skeleton.tsx`

---

### 4.2 Alice 柔雾主题

**添加**:
```css
.theme-alice-fog {
  --background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 50%, #fafafa 100%);
}

.fog-card {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}
```

---

### 4.3 移动端适配

**检查项**:
- [ ] Sidebar 响应式折叠
- [ ] 触控反馈 (active states)
- [ ] 安全区域适配
- [ ] 字号调整

---

## 五、执行顺序

```
Week 1 (P1)
├── 2.1 文案规范化
├── 2.2 Chat 输入框统一
└── 2.3 意图系统视觉一致性

Week 2 (P2)
├── 3.1 Design Token 添加
├── 3.2 AI 思考动画优化
└── 3.3 NotionPromptForm 中文化

Week 3+ (P3)
├── 4.1 Skeleton 骨架屏
├── 4.2 Alice 柔雾主题
└── 4.3 移动端适配
```

---

## 六、验收标准

### P1 完成标准
- [ ] 所有面向用户的文案符合 Voice & Tone 规范
- [ ] 输入框组件统一使用 NotionPromptForm
- [ ] 意图 Badge 样式全局一致

### P2 完成标准
- [ ] Design Token 在 globals.css 中定义
- [ ] 组件使用 Token 而非硬编码值
- [ ] AI 思考状态有呼吸动画

### P3 完成标准
- [ ] 列表加载有骨架屏
- [ ] 移动端体验流畅
- [ ] 柔雾主题可选

---

*本计划随开发进度更新，优先级可能调整。*
