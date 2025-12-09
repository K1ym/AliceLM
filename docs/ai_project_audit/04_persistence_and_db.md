# 数据持久化与数据库结构

## 使用的数据库与存储技术

| 技术 | 场景 | 配置位置 |
|------|------|----------|
| **SQLite** (默认) | 主事务数据库，存储所有业务实体 | `ALICE_DB__URL` 默认 `sqlite:///data/bili_learner.db` |
| **PostgreSQL** (可选) | 生产环境替代 SQLite | `config/prod/default.yaml` 注释中 |
| **ChromaDB** | 向量存储，视频转写文本检索 | 持久化目录 `data/chroma` |
| **RAGFlow** (可选) | 生产向量/检索服务 | docker-compose profile `rag`，依赖 MySQL+Redis+Elasticsearch |
| **Redis** (可选) | 任务队列/缓存（compose 中定义，代码未直接调用） | docker-compose |
| **文件系统** | 视频/音频/转写文件存储 | `data/` 挂载卷 |

**ORM 框架**: SQLAlchemy (`packages/db/database.py`)

## 核心表结构

### 租户与用户

#### tenants（租户）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| name | String(100) | - | 租户名称 |
| slug | String(50) | UNIQUE, INDEX | 租户标识符 |
| plan | Enum | default=free | 订阅计划 |
| plan_expires_at | DateTime | nullable | 计划过期时间 |
| max_videos | Integer | - | 视频配额 |
| max_storage_gb | Integer | - | 存储配额 |
| max_users | Integer | - | 用户配额 |
| is_active | Boolean | - | 是否激活 |
| created_at | DateTime | - | 创建时间 |

#### users（用户）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| email | String(255) | UNIQUE, INDEX | 邮箱（全局唯一） |
| username | String(50) | - | 用户名 |
| password_hash | String | nullable | 密码哈希 |
| wechat_openid | String | nullable, INDEX | 微信 OpenID |
| role | Enum | default=member | 角色 |
| is_active | Boolean | - | 是否激活 |
| last_login_at | DateTime | nullable | 最后登录 |
| created_at | DateTime | - | 创建时间 |

#### user_platform_bindings（平台绑定）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| user_id | Integer | FK→users, INDEX | 用户 ID |
| platform | String(20) | UNIQUE(user_id, platform) | 平台名称 |
| platform_uid | String(100) | - | 平台用户 ID |
| credentials | Text | nullable | 凭证 JSON（明文存储） |
| is_active | Boolean | - | 是否激活 |
| created_at | DateTime | - | 创建时间 |

### 内容管理

#### videos（视频）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| watched_folder_id | Integer | FK→watched_folders, nullable, ondelete=SET NULL | 来源文件夹 |
| source_type | String(20) | INDEX | 来源类型 |
| source_id | String(100) | INDEX | 来源 ID |
| source_url | String | nullable | 来源 URL |
| title | String(500) | - | 标题 |
| author | String(100) | - | 作者 |
| duration | Integer | default=0 | 时长（秒） |
| cover_url | String | nullable | 封面 URL |
| status | String(20) | default="pending" | 处理状态 |
| error_message | Text | nullable | 错误信息 |
| retry_count | Integer | - | 重试次数 |
| video_path | String | nullable | 视频文件路径 |
| audio_path | String | nullable | 音频文件路径 |
| transcript_path | String | nullable | 转写文件路径 |
| summary | Text | nullable | AI 摘要 |
| key_points | Text | nullable | 关键点 |
| concepts | Text | nullable | 概念 |
| asr_provider | String | nullable | ASR 提供商 |
| llm_provider | String | nullable | LLM 提供商 |
| collected_at | DateTime | nullable | 采集时间 |
| processed_at | DateTime | nullable | 处理完成时间 |
| created_at | DateTime | default=now | 创建时间 |
| updated_at | DateTime | onupdate=now | 更新时间 |

**唯一约束**: `(tenant_id, source_type, source_id)`

#### tags（标签）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| name | String(50) | UNIQUE | 标签名（全局唯一） |
| category | String | nullable | 分类 |

#### video_tags（视频-标签关联）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| video_id | Integer | PK, FK→videos | 视频 ID |
| tag_id | Integer | PK, FK→tags | 标签 ID |
| confidence | Float | default=1.0 | 置信度 |

#### watched_folders（监控文件夹）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| folder_id | String(50) | UNIQUE(tenant_id, folder_id) | 文件夹 ID |
| folder_type | String(20) | - | 文件夹类型 |
| name | String(200) | - | 名称 |
| platform | String(20) | default=bilibili | 平台 |
| last_scan_at | DateTime | nullable | 最后扫描时间 |
| is_active | Boolean | - | 是否激活 |

### 对话与 Agent

#### conversations（对话）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| user_id | Integer | FK→users, INDEX | 用户 ID |
| title | String | nullable | 标题 |
| compressed_context | Text | nullable | 压缩上下文 |
| compressed_at_message_id | Integer | nullable | 压缩点消息 ID |
| created_at | DateTime | default=now | 创建时间 |
| updated_at | DateTime | onupdate=now | 更新时间 |

#### messages（消息）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| conversation_id | Integer | FK→conversations, INDEX, ondelete=CASCADE | 对话 ID |
| role | Enum | - | 角色 |
| content | Text | - | 内容 |
| sources | Text | nullable | 来源引用 |
| created_at | DateTime | default=now | 创建时间 |

#### agent_runs（Agent 运行记录）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| user_id | Integer | FK→users, nullable, INDEX | 用户 ID |
| scene | String(50) | - | 场景 |
| query | Text | - | 查询 |
| strategy | String | nullable | 策略 |
| status | Enum | default=running | 状态 |
| answer | Text | nullable | 回答 |
| citations | Text | nullable | 引用 |
| error | Text | nullable | 错误 |
| prompt_tokens | Integer | nullable | Prompt token 数 |
| completion_tokens | Integer | nullable | Completion token 数 |
| created_at | DateTime | default=now | 创建时间 |
| completed_at | DateTime | nullable | 完成时间 |

#### agent_steps（Agent 步骤）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| run_id | Integer | FK→agent_runs, INDEX, ondelete=CASCADE | 运行 ID |
| step_idx | Integer | - | 步骤索引 |
| thought | Text | nullable | 思考 |
| tool_name | String | nullable | 工具名 |
| tool_args | Text | nullable | 工具参数 |
| observation | Text | nullable | 观察结果 |
| error | Text | nullable | 错误 |
| created_at | DateTime | default=now | 创建时间 |

### 时间线与学习记录

#### timeline_events（时间线事件）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| user_id | Integer | FK→users, nullable, INDEX | 用户 ID |
| event_type | Enum | INDEX | 事件类型 |
| scene | Enum | INDEX | 场景 |
| video_id | Integer | FK→videos, nullable, INDEX | 关联视频 |
| conversation_id | Integer | FK→conversations, nullable | 关联对话 |
| title | String | nullable | 标题 |
| context | Text | nullable | 上下文 |
| created_at | DateTime | default=now, INDEX | 创建时间 |

#### learning_records（学习记录 - 旧兼容）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id | Integer | FK→tenants, INDEX | 所属租户 |
| user_id | Integer | FK→users, INDEX | 用户 ID |
| video_id | Integer | FK→videos, INDEX | 视频 ID |
| action | String(20) | - | 动作 |
| duration | Integer | nullable | 时长 |
| created_at | DateTime | - | 创建时间 |
| extra_data | Text | nullable | 额外数据 |

### 配置表

#### tenant_configs / user_configs
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| tenant_id/user_id | Integer | FK, INDEX | 关联 ID |
| key | String(100) | UNIQUE(tenant/user_id, key) | 配置键 |
| value | Text | - | 配置值 |

## 索引与性能相关考量

### 已建索引

| 表 | 索引 | 类型 |
|----|------|------|
| videos | `(tenant_id, source_type, source_id)` | UNIQUE |
| videos | `ix_tenant_status (tenant_id, status)` | 复合 |
| videos | `ix_tenant_source_type (tenant_id, source_type)` | 复合 |
| users | `email` | UNIQUE |
| tenants | `slug` | UNIQUE |
| timeline_events | `(tenant_id, user_id, created_at)` | 复合 |
| timeline_events | `(tenant_id, event_type, created_at)` | 复合 |
| 各 FK 字段 | 标记 `index=True` 的字段 | 单列 |

### 潜在缺失索引

| 场景 | 建议索引 |
|------|----------|
| 视频列表按时间排序 | `videos (tenant_id, created_at DESC)` |
| 对话列表查询 | `conversations (tenant_id, user_id, updated_at DESC)` |
| Agent 运行历史 | `agent_runs (tenant_id, created_at DESC)` |

### 性能风险

- `videos.status` 使用字符串而非 Enum，无数据库层校验
- 大量查询按 `created_at` 排序但缺少组合索引
- `ConversationRepository` 按 `video_id` 过滤，但模型未定义该字段

## 数据一致性与约束设计

### 外键约束

| 关系 | ondelete 行为 |
|------|---------------|
| messages → conversations | CASCADE |
| agent_steps → agent_runs | CASCADE |
| videos → watched_folders | SET NULL |
| 其他 FK | 默认 RESTRICT |

### ⚠️ SQLite 外键问题

```python
# database.py 未启用外键约束
# SQLite 默认 PRAGMA foreign_keys=OFF
# 导致 ondelete 约束不生效，可能产生孤儿记录
```

### 多租户隔离

| 表 | 隔离方式 | 风险 |
|----|----------|------|
| videos, conversations, agent_runs 等 | `tenant_id` 字段 | ✅ 正常 |
| tags | 全局唯一 `name` | ⚠️ 跨租户共享命名空间 |
| users | 全局唯一 `email` | ⚠️ 跨租户冲突 |
| video_tags | 依赖 video FK | ⚠️ 无显式 tenant_id |

### 软删除

- 部分表有 `is_active` 字段，但无统一软删除机制
- 删除操作多为直接 DELETE（如 `ConversationRepository.delete_with_messages`）
- 不触发 ORM 级联事件

### 枚举约束

| 字段 | 实现方式 | 数据库约束 |
|------|----------|------------|
| videos.status | String(20) | ❌ 无 CHECK |
| timeline_events.event_type | SQLAlchemy Enum | ✅ 有（非 SQLite） |
| messages.role | SQLAlchemy Enum | ✅ 有（非 SQLite） |

## 迁移管理

### 当前状态

- **DDL 生成**: `Base.metadata.create_all()` 自动建表
- **迁移框架**: ❌ 未使用 Alembic
- **手动迁移**: `scripts/migrations/001_multi_source.py`（仅 SQLite）

### 迁移脚本内容

```python
# 001_multi_source.py - 使用原生 sqlite3
# 1. 向 videos 添加 source_id 字段
# 2. 创建 user_platform_bindings 表
# 3. 迁移旧 bilibili 字段
# 4. 添加索引
```

## 风险与疑点

### 🔴 高风险

| 问题 | 影响 | 建议 |
|------|------|------|
| SQLite 外键未启用 | 数据完整性无保障，孤儿记录 | 添加 `PRAGMA foreign_keys=ON` 事件钩子 |
| 无系统化迁移 | 表结构升级困难，环境漂移 | 引入 Alembic |
| `credentials` 明文存储 | 第三方 token 泄露风险 | 加密存储 |
| `Conversation.video_id` 缺失 | Repository 查询会报错 | 补充字段或修改查询 |

### 🟡 中风险

| 问题 | 影响 | 建议 |
|------|------|------|
| PostgreSQL 未测试 | 切换生产数据库可能失败 | 添加集成测试 |
| 多租户隔离不完整 | tags/email 跨租户冲突 | 重新设计唯一约束 |
| 状态字段无 CHECK | 脏数据可能入库 | 使用 Enum 类型或添加约束 |
| 必填字段未设 NOT NULL | 依赖应用层校验 | 加强数据库约束 |

### 🟢 低风险

| 问题 | 影响 | 建议 |
|------|------|------|
| 缺少时间排序索引 | 列表查询性能 | 按需添加复合索引 |
| Redis 未实际使用 | compose 资源浪费 | 移除或实现队列功能 |
