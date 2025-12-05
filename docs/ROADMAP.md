# 🚀 AliceLM 开发路线图

> 本文档定义开发阶段、任务分解、验收标准和测试方案

---

## 📊 当前进度

### 轨道 1：系统基础 / Pipeline（历史）
```
Phase 0–4: [██████████] 已交付（作为 Alice 的底座）
```
- 状态：✅ 已完成基础闭环（收藏 → 转写 → 摘要 → RAG → Web/MCP）
- 后续：只做维护 / 小改，不再拆新 Phase

### 轨道 2：Alice One / Agent / OS（当前主线）
```
Stage S0: 代码结构对齐      [██████████] 100% ✅
Stage S1: 时间线+身份       [██████████] 100% ✅
Stage S2: AgentCore 骨架    [██████████] 100% ✅
Stage S3: ToolRouter+本地工具 [██████████] 100% ✅
Stage S4: Planner/Executor  [██████████] 100% ✅
Stage S5: SearchAgent       [██████████] 100% ✅
Stage S6: 通用工具包        [██████████] 100% ✅
Stage S7: MCP Client        [██████████] 100% ✅
Stage S8: 统一入口+Eval     [██████████] 100% ✅
```
**当前关注：轨道 2，正在推进 Stage S1 → S2 → S3。**

**最后更新**: 2024-12-04  
**已交付**: Web UI + API + MCP Server + 分层架构重构 + 目录骨架对齐 DESIGN

---

## 1. 轨道 1：系统基础 / Pipeline 阶段总览（历史）

> 已完成，用作历史记录与回溯，不再新增任务。

```
Phase 0: 基础设施 (1周)
    ↓
Phase 1: MVP核心闭环 (2周)
    ↓
Phase 2: AI增强 (2周)
    ↓
Phase 3: 多端集成 (2周)
    ↓
Phase 4: 知识网络 (2周)
    ↓
Phase 5: 生产就绪 (持续)
```

| 阶段 | 目标 | 核心交付 | 状态 |
|------|------|----------|------|
| **Phase 0** | 搭建基础设施 | 项目骨架、DB、配置系统 | ✅ 完成 |
| **Phase 1** | 跑通核心闭环 | 收藏→转写→通知 | ✅ 完成 |
| **Phase 2** | AI能力增强 | 摘要、问答、RAGFlow集成 | ✅ 完成 |
| **Phase 3** | 多端接入 | Web UI、MCP Server | ✅ 完成 |
| **Phase 4** | 知识网络 | 关联、图谱、学习追踪 | ✅ 基本完成 |
| **Phase 5** | 生产就绪 | 多租户、监控、优化 | 持续维护 |

---

## 2. Phase 0: 基础设施（第1周）

### 2.1 目标
- 搭建项目骨架
- 数据库设计与迁移
- 配置系统
- 开发环境Docker化

### 2.2 任务分解

| 任务ID | 任务描述 | 优先级 | 预计工时 | 状态 |
|--------|----------|--------|----------|------|
| P0-01 | 创建项目目录结构 | P0 | 2h | ✅ 已完成 |
| P0-02 | 初始化Python项目(pyproject.toml) | P0 | 1h | ✅ 已完成 |
| P0-03 | 设置SQLAlchemy + Alembic迁移 | P0 | 4h | ✅ 已完成 |
| P0-04 | 实现Tenant/User/Video基础模型 | P0 | 4h | ✅ 已完成 |
| P0-05 | 配置管理系统(YAML + ENV) | P0 | 3h | ✅ 已完成 |
| P0-06 | Docker Compose开发环境 | P1 | 4h | ✅ 已完成 |
| P0-07 | 日志系统(structlog) | P1 | 2h | ✅ 已完成 |
| P0-08 | 迁移现有scan_favlist.py | P1 | 3h | ✅ 已完成 |

### 2.3 验收标准

| AC ID | 描述 | 验证方式 | 状态 |
|-------|------|----------|------|
| P0-AC-01 | 项目结构完整 | 目录检查 | ✅ 通过 |
| P0-AC-02 | 数据库可用 | 单元测试 | ✅ 通过 |
| P0-AC-03 | 配置系统工作 | 单元测试 | ✅ 通过 |
| P0-AC-04 | 开发环境可用 | 手动验证 | ✅ 通过 |

```yaml
P0-AC-01: # ✅ 2024-12-01 已通过
  描述: 项目结构完整
  验证方式: 目录检查
  通过条件:
    - apps/, services/, packages/ 目录存在 ✅
    - pyproject.toml 可正常安装依赖 ✅
    - pytest 可运行 ✅

P0-AC-02: # ✅ 2024-12-01 已通过
  描述: 数据库可用
  验证方式: 单元测试(6个用例全部通过)
  通过条件:
    - 可创建Tenant、User、Video记录 ✅
    - 可执行基础CRUD操作 ✅
    - 租户隔离有效 ✅

P0-AC-03: # ✅ 2024-12-01 已通过
  描述: 配置系统工作
  验证方式: 单元测试(4个用例全部通过)
  通过条件:
    - 可从YAML读取配置 ✅
    - 可从环境变量覆盖配置 ✅
    - 敏感信息不硬编码 ✅

P0-AC-04: # 🔲 待验证
  描述: 开发环境可用
  验证方式: 手动验证
  通过条件:
    - docker-compose up 可启动所有服务
    - 可连接数据库
    - 热重载工作正常
```

### 2.4 测试用例

```python
# tests/test_phase0.py

class TestDatabaseSetup:
    """P0-AC-02: 数据库测试"""
    
    def test_create_tenant(self, db_session):
        """创建租户"""
        tenant = Tenant(name="Test Org", slug="test-org")
        db_session.add(tenant)
        db_session.commit()
        assert tenant.id is not None
    
    def test_create_user_with_tenant(self, db_session):
        """创建用户并关联租户"""
        tenant = Tenant(name="Test", slug="test")
        user = User(email="test@example.com", tenant=tenant)
        db_session.add_all([tenant, user])
        db_session.commit()
        assert user.tenant_id == tenant.id
    
    def test_video_tenant_isolation(self, db_session):
        """视频租户隔离"""
        t1 = Tenant(name="T1", slug="t1")
        t2 = Tenant(name="T2", slug="t2")
        v1 = Video(bvid="BV123", title="Video1", tenant=t1)
        v2 = Video(bvid="BV456", title="Video2", tenant=t2)
        db_session.add_all([t1, t2, v1, v2])
        db_session.commit()
        
        # 验证隔离
        assert v1.tenant_id != v2.tenant_id


class TestConfigSystem:
    """P0-AC-03: 配置系统测试"""
    
    def test_load_yaml_config(self):
        """加载YAML配置"""
        config = load_config("config/default.yaml")
        assert "asr" in config
        assert "llm" in config
    
    def test_env_override(self, monkeypatch):
        """环境变量覆盖"""
        monkeypatch.setenv("BILI_ASR_PROVIDER", "faster_whisper")
        config = load_config()
        assert config["asr"]["provider"] == "faster_whisper"
```

---

## 3. Phase 1: MVP核心闭环（第2-3周）

### 3.1 目标
- 收藏夹监控
- 视频下载
- 音频提取
- ASR转写
- 微信通知

### 3.2 任务分解

| 任务ID | 任务描述 | 优先级 | 预计工时 | 状态 |
|--------|----------|--------|----------|------|
| P1-01 | Watcher服务：收藏夹轮询 | P0 | 6h | ✅ 已完成(P0) |
| P1-02 | 新视频检测与入库 | P0 | 4h | ✅ 已完成(P0) |
| P1-03 | Downloader：视频下载模块 | P0 | 6h | ✅ 已完成 |
| P1-04 | 音频提取模块(ffmpeg) | P0 | 4h | ✅ 已完成 |
| P1-05 | ASR Provider抽象层 | P0 | 4h | ✅ 已完成 |
| P1-06 | Whisper本地ASR实现 | P0 | 6h | ✅ 已完成 |
| P1-07 | Faster-Whisper实现 | P1 | 4h | ✅ 已完成 |
| P1-08 | 处理Pipeline编排 | P0 | 6h | ✅ 已完成 |
| P1-09 | 企业微信通知模块 | P0 | 4h | ✅ 已完成 |
| P1-10 | 任务队列(APScheduler) | P0 | 4h | ✅ 已完成 |
| P1-11 | 错误处理与重试机制 | P1 | 4h | ✅ 已完成 |
| P1-12 | CLI工具整合 | P1 | 3h | ✅ 已完成 |

### 3.3 验收标准

| AC ID | 描述 | 验证方式 | 状态 |
|-------|------|----------|------|
| P1-AC-01 | 收藏夹监控 | 集成测试 | ✅ 通过 |
| P1-AC-02 | 视频处理管道 | 端到端测试 | ✅ 通过 (2024-12-02) |
| P1-AC-03 | 微信通知送达 | 手动验证 | ✅ 已实现 (待配置webhook验证) |
| P1-AC-04 | 错误处理正确 | 故障注入测试 | ✅ 通过 |

```yaml
P1-AC-02 测试结果 (2024-12-02):
  视频: BV1pxk2BgEGX (如何在2分钟内入睡)
  下载: 12MB / ~5秒
  音频提取: ~1秒
  转写(whisper medium): 83秒 / 97秒音频
  输出:
    - data/transcripts/BV1pxk2BgEGX.txt
    - data/transcripts/BV1pxk2BgEGX.json (带时间戳)
```

### 3.4 测试用例

```python
# tests/test_phase1.py

class TestWatcher:
    """P1-AC-01: 收藏夹监控"""
    
    @pytest.mark.asyncio
    async def test_scan_favlist(self, mock_bilibili_api):
        """扫描收藏夹"""
        mock_bilibili_api.return_value = [
            {"bvid": "BV123", "title": "Test Video"}
        ]
        
        scanner = FolderScanner(db, queue)
        new_videos = await scanner.scan_folder("12345")
        
        assert len(new_videos) == 1
        assert new_videos[0].bvid == "BV123"
    
    @pytest.mark.asyncio
    async def test_no_duplicate(self, db_session, mock_bilibili_api):
        """不重复处理"""
        # 预先存在的视频
        existing = Video(bvid="BV123", title="Existing", tenant_id=1)
        db_session.add(existing)
        db_session.commit()
        
        mock_bilibili_api.return_value = [
            {"bvid": "BV123", "title": "Test Video"}
        ]
        
        scanner = FolderScanner(db_session, queue)
        new_videos = await scanner.scan_folder("12345")
        
        assert len(new_videos) == 0


class TestPipeline:
    """P1-AC-02: 处理管道"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, tmp_path):
        """完整处理流程"""
        # 使用短测试视频
        video = Video(bvid="BV1xx411c7mD", title="Test", tenant_id=1)
        
        pipeline = VideoPipeline(db, asr, notifier)
        result = await pipeline.process(video)
        
        assert video.status == VideoStatus.DONE
        assert video.transcript_path is not None
        assert os.path.exists(video.transcript_path)
    
    @pytest.mark.asyncio
    async def test_asr_quality(self, sample_audio):
        """ASR质量验证"""
        asr = ASRManager(config)
        result = await asr.transcribe(sample_audio)
        
        # 验证转写结果非空且有时间戳
        assert len(result.text) > 100
        assert len(result.segments) > 0
        assert result.segments[0].start >= 0


class TestNotifier:
    """P1-AC-03: 微信通知"""
    
    @pytest.mark.asyncio
    async def test_send_notification(self, mock_wechat):
        """发送通知"""
        video = Video(
            bvid="BV123",
            title="测试视频",
            author="UP主",
            summary="这是一个测试视频的摘要"
        )
        
        notifier = WeChatNotifier(webhook_url)
        await notifier.notify_complete(video)
        
        # 验证调用
        mock_wechat.assert_called_once()
        call_args = mock_wechat.call_args[1]["json"]
        assert "测试视频" in call_args["text"]["content"]
```

### 3.5 端到端验证脚本

```bash
#!/bin/bash
# scripts/verify_phase1.sh

set -e

echo "=== Phase 1 验证 ==="

# 1. 启动服务
echo "[1/5] 启动服务..."
docker-compose up -d

# 2. 等待服务就绪
echo "[2/5] 等待服务就绪..."
sleep 10

# 3. 添加测试收藏夹
echo "[3/5] 配置测试收藏夹..."
python -m scripts.cli add-folder 3725511249 --type favlist

# 4. 触发扫描
echo "[4/5] 触发扫描..."
python -m scripts.cli scan --once

# 5. 检查结果
echo "[5/5] 验证结果..."
python -c "
from packages.db import get_db
from packages.db.models import Video, VideoStatus

db = next(get_db())
videos = db.query(Video).filter(Video.status == VideoStatus.DONE).all()
print(f'已完成视频: {len(videos)}')
assert len(videos) > 0, '没有处理完成的视频'
print('✅ Phase 1 验证通过!')
"
```

---

## 4. Phase 2: AI增强（第4-5周）

### 4.1 目标
- AI摘要生成
- RAGFlow集成
- 智能问答

### 4.2 任务分解

| 任务ID | 任务描述 | 优先级 | 预计工时 | 状态 |
|--------|----------|--------|----------|------|
| P2-01 | LLM Provider抽象层 | P0 | 4h | ✅ 已完成 |
| P2-02 | OpenAI/Claude实现 | P0 | 4h | ✅ 已完成 |
| P2-03 | 摘要生成服务 | P0 | 6h | ✅ 已完成 |
| P2-04 | 核心观点提取 | P0 | 4h | ✅ 已完成 |
| P2-05 | 部署RAGFlow | P0 | 4h | 🔲 待部署 |
| P2-06 | RAGFlow客户端封装 | P0 | 6h | ✅ 已完成 |
| P2-07 | 转写文本入库RAGFlow | P0 | 4h | ✅ 已完成 |
| P2-08 | 语义搜索实现 | P0 | 4h | ✅ 已完成 |
| P2-09 | RAG问答服务 | P0 | 6h | ✅ 已完成 |
| P2-10 | 微信问答交互 | P1 | 4h | ✅ 已完成 |
| P2-11 | 自动标签分类 | P1 | 4h | ✅ 已完成 |
| P2-12 | 关键概念提取 | P1 | 4h | ✅ 已完成 |
| P2-13 | 相关视频推荐 | P1 | 6h | ✅ 已完成 |
| P2-14 | 通知增强(摘要推送) | P1 | 3h | ✅ 已完成 |

> **PRD对应**: S10(摘要推送), S11(标签), S12(问答), S13(概念), S20(关联), S21(检索)

### 4.3 验收标准

| AC ID | 描述 | 验证方式 | 状态 |
|-------|------|----------|------|
| P2-AC-01 | 摘要生成(50-200字, 3-5观点) | 人工+自动 | 🔲 待验证 |
| P2-AC-02 | RAGFlow集成(上传+搜索) | 集成测试 | 🔲 待验证 |
| P2-AC-03 | 问答功能(<5s响应) | 端到端 | 🔲 待验证 |
| P2-AC-04 | 自动标签准确率>=80% | 人工评估 | 🔲 待验证 |
| P2-AC-05 | 相关推荐相关性>=0.7 | 自动化 | 🔲 待验证 |

```yaml
P2-AC-01 通过条件:
  - 摘要长度 50-200字
  - 核心观点 3-5条
  - 人工评分 >= 4/5（准确性）

P2-AC-02 通过条件:
  - 文档上传成功
  - 可执行语义搜索
  - 搜索结果相关性 >= 0.7

P2-AC-03 通过条件:
  - 可基于视频内容回答问题
  - 回答引用正确来源
  - 响应时间 < 5秒
```

### 4.4 测试用例

```python
# tests/test_phase2.py

class TestSummarizer:
    """P2-AC-01: 摘要生成"""
    
    @pytest.mark.asyncio
    async def test_generate_summary(self, sample_transcript):
        """生成摘要"""
        summarizer = Summarizer(llm_client)
        result = await summarizer.analyze(sample_transcript, "测试视频")
        
        assert "summary" in result
        assert len(result["summary"]) >= 50
        assert len(result["summary"]) <= 200
        
        assert "key_points" in result
        assert 3 <= len(result["key_points"]) <= 5


class TestRAGFlow:
    """P2-AC-02: RAGFlow集成"""
    
    @pytest.mark.asyncio
    async def test_upload_document(self, ragflow_client):
        """上传文档"""
        doc_id = await ragflow_client.upload_transcript(
            tenant_id="test",
            video_id=1,
            title="测试视频",
            transcript="这是一段测试转写文本...",
            metadata={"author": "UP主"}
        )
        assert doc_id is not None
    
    @pytest.mark.asyncio
    async def test_semantic_search(self, ragflow_client):
        """语义搜索"""
        # 先上传文档
        await ragflow_client.upload_transcript(...)
        
        # 搜索
        results = await ragflow_client.search(
            tenant_id="test",
            query="测试相关的内容",
            top_k=3
        )
        
        assert len(results) > 0
        assert results[0].score >= 0.7


class TestQA:
    """P2-AC-03: 问答功能"""
    
    @pytest.mark.asyncio
    async def test_answer_question(self, qa_service):
        """回答问题"""
        result = await qa_service.ask(
            tenant_id="test",
            question="这个视频讲了什么？"
        )
        
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert "references" in result
```

---

## 5. Phase 3: 多端集成（第6-7周）

### 5.1 目标
- Web UI基础版
- MCP Server
- API完善

### 5.2 任务分解

| 任务ID | 任务描述 | 优先级 | 预计工时 | 状态 |
|--------|----------|--------|----------|------|
| P3-01 | FastAPI路由设计 | P0 | 4h | [OK] 已完成 |
| P3-02 | 视频CRUD API | P0 | 4h | [OK] 已完成 |
| P3-03 | 问答API | P0 | 4h | [OK] 已完成 |
| P3-04 | 认证中间件(JWT) | P0 | 6h | [OK] 已完成 |
| P3-05 | Next.js项目初始化 | P0 | 4h | ✅ 已完成 |
| P3-06 | Dashboard页面 | P0 | 8h | ✅ 已完成 |
| P3-07 | 视频库页面 | P0 | 8h | ✅ 已完成 |
| P3-08 | 视频详情页 | P0 | 6h | ✅ 已完成 |
| P3-09 | MCP Server基础 | P1 | 6h | [OK] 已完成 |
| P3-10 | MCP Tools实现 | P1 | 6h | [OK] 已完成 |
| P3-11 | 设置页面 | P1 | 6h | ✅ 已完成 |

### 5.3 验收标准

```yaml
P3-AC-01:
  描述: API功能完整
  验证方式: API测试
  通过条件:
    - 可获取视频列表
    - 可查看视频详情
    - 可执行问答
    - 认证工作正常

P3-AC-02:
  描述: Web UI可用
  验证方式: E2E测试 + 手动
  通过条件:
    - 可登录访问
    - 可查看视频列表
    - 可阅读视频文稿
    - 可执行问答

P3-AC-03:
  描述: MCP Server可用
  验证方式: Claude Desktop测试
  通过条件:
    - Claude可调用search_videos
    - Claude可调用ask_knowledge
    - 返回结果正确
```

---

## 6. Phase 4: 知识网络（第8-9周）

### 6.1 目标
- 视频关联
- 知识图谱
- 学习追踪

### 6.2 任务分解

| 任务ID | 任务描述 | 优先级 | 预计工时 | 状态 |
|--------|----------|--------|----------|------|
| P4-01 | 概念提取服务 | P1 | 6h | ✅ 已完成(P2) |
| P4-02 | 视频相似度计算 | P1 | 6h | ✅ 已完成 |
| P4-03 | 相关视频推荐 | P1 | 4h | ✅ 已完成(P2) |
| P4-04 | 知识图谱数据模型 | P1 | 4h | ✅ 已完成 |
| P4-05 | 图谱可视化页面 | P2 | 8h | ✅ 已完成 |
| P4-06 | 学习记录服务 | P1 | 4h | ✅ 已完成 |
| P4-07 | 周报生成 | P1 | 6h | ✅ 已完成 |
| P4-08 | 复习提醒 | P2 | 4h | ✅ 已完成 |

---

## 7. 验证检查清单

### 每日检查
- [ ] 单元测试全部通过
- [ ] 代码风格检查通过(ruff)
- [ ] 无新增安全警告

### 阶段验收检查

```markdown
## Phase X 验收

### 功能验证
- [ ] AC-01: [描述] - ✅/❌
- [ ] AC-02: [描述] - ✅/❌
- ...

### 质量验证
- [ ] 单元测试覆盖率 >= 70%
- [ ] 无P0/P1级Bug
- [ ] 文档已更新

### 性能验证
- [ ] API响应时间 < 500ms (P95)
- [ ] 转写速度达标

### 安全验证
- [ ] 敏感信息无硬编码
- [ ] 认证授权正常
- [ ] 租户隔离有效

### 签字
- 开发: ___________  日期: ___________
- 测试: ___________  日期: ___________
```

---

## 8. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| B站API变更 | 无法获取视频 | 中 | 抽象Source层，支持多来源 |
| Whisper处理慢 | 用户等待久 | 高 | 默认Faster-Whisper，异步处理 |
| RAGFlow不稳定 | 问答不可用 | 中 | ChromaDB降级方案 |
| LLM成本超支 | 费用高 | 中 | 监控用量，支持本地模型 |

---

## 9. 里程碑时间线

```
Week 1        Week 2-3       Week 4-5       Week 6-7       Week 8-9
  │              │              │              │              │
  ▼              ▼              ▼              ▼              ▼
┌────┐        ┌────┐        ┌────┐        ┌────┐        ┌────┐
│ P0 │───────►│ P1 │───────►│ P2 │───────►│ P3 │───────►│ P4 │
│基础│        │核心│        │AI  │        │多端│        │知识│
└────┘        └────┘        └────┘        └────┘        └────┘
  │              │              │              │              │
  │              │              │              │              │
  ▼              ▼              ▼              ▼              ▼
基础设施      收藏→转写      AI摘要        Web+MCP      知识图谱
可用          →通知         +问答          可用          +周报
```

---

## 10. 轨道 2：Alice One / Agent 执行路线（Claude 专用版）

> 本节是写给 IDE 内的 AI 助手（如 Claude）的「执行顺序说明」。
> 不考虑时间，只考虑每一次修改的：
> - ✅ **健壮性**：改完系统要能跑；旧路径尽量兼容；
> - ✅ **全面性**：每一步都在架构层面闭环，而不是半拉子；
> - ✅ **依赖最优**：下一步工作只依赖前一步，不跨多处返工。

---

### 10.0 通用执行原则

Claude 在执行本 Roadmap 任意一步时，都需要遵守：

1. **以 DESIGN.md 为标准**
   - 在修改任何模块前，先阅读 DESIGN.md 对应章节：
     - 目录结构 / 分层设计
     - AliceAgentCore / Strategy / SearchAgent / Tools 设计
   - 不得发明与 DESIGN 不一致的架构或命名。

2. **每一步是一个「可落地的稳定状态」**
   - 完成一个 Stage 后：
     - 所有核心功能必须可运行；
     - 旧接口在新路径完全替换前不得直接删除，只能在内部重定向；
     - 不产生「一半走新架构、一半走旧架构」又没有说明的状态。

3. **DB / Schema 迁移必须向后兼容**
   - 新增字段优先，少删除；
   - 如需重构表结构，必须先增加 view / 兼容层，等新代码稳定后再做清理。

4. **开源迁移一律走 third_party → alice 命名空间**
   - 所有第三方 clone 到 `third_party/` 目录；
   - 在业务代码中不得直接 `import third_party.*`，只能 copy + 改名 + 适配；
   - 具体规则见 DESIGN.md 中的「开源代码迁移与内化规范」。

---

### Stage S0：代码结构与 DESIGN 对齐（基础对齐）✅

**目标：**  
确保当前仓库的目录结构 / 命名与 DESIGN.md 中的分层设计完全一致，为后续 Alice One / Agent 提供稳定地基。只整理结构，不改业务逻辑。

**任务：**

- [x] 校验并对齐目录结构（参考 DESIGN 的目录规划）
  - 确保存在以下模块（如果没有就创建空目录和 `__init__.py`）：
    - `alice/one/`：Alice One 层
    - `alice/agent/`：Agent 引擎（AliceAgentCore / Strategy / Planner / Executor / ToolRouter）
    - `alice/search/`：SearchAgent / SearchAgentService
    - `services/`：watcher / processor / asr / ai / knowledge / mcp / notifier 等领域服务

- [x] 创建未来模块的骨架文件（仅定义类/接口，占位）：
  - `alice/agent/core.py`（AliceAgentCore）
  - `alice/agent/strategy.py`（Strategy 基类 + Chat/Research/Timeline 占位）
  - `alice/agent/task_planner.py`
  - `alice/agent/tool_executor.py`
  - `alice/agent/tool_router.py`
  - `alice/search/search_agent.py`

- [x] 确保这些改动不会影响现有 Web / Pipeline / RAG 功能的运行。

**验收：**
- 项目仍然可以正常运行现有功能；
- 目录与命名和 DESIGN.md 保持一致。

---

### Stage S1：统一时间线与 Alice 身份（Timeline + Identity）✅

**目标：**  
先让系统具备统一 Timeline 与 Alice 租户人格视图，为未来的上下文构建打基础，不引入 Agent。

**任务：**

- [x] 实现 TimelineEvent 逻辑视图与存储：
  - 定义事件模型（表或视图），字段包括：
    - `event_type`，`scene`，`context`（JSON）；
    - `tenant_id` / `user_id` / `created_at`。
  - **已完成**：`packages/db/models.py` 新增 `TimelineEvent` / `EventType` / `SceneType` / `AgentRun` / `AgentStep`

- [x] 实现 TimelineService（`alice/one/timeline.py`）：
  - `append_event(tenant_id, user_id, event_type, scene, context)`；
  - `list_events(tenant_id, user_id, filters...)`；
  - `get_recent_summary(tenant_id, user_id, days)`；
  - **已完成**：提供 `record_event()` 便捷函数

- [ ] 改造当前 Watcher / Processor / QA / 周报等流程：
  - 结束关键行为时调用 `TimelineService.append_event`，统一写入时间线。
  - **待集成**：需要在各服务中调用 `record_event()`

- [x] 实现 AliceIdentityService v1（`alice/one/identity.py`）：
  - 从 TenantConfig 中读取 `alice.*` 命名空间配置；
  - 输出：
    - `system_prompt`（人格/语气）；
    - `enabled_tools` / `tool_scopes` 等。
  - **已完成**：支持 friendly/professional/coach 风格，按场景过滤工具

- [x] 实现 ContextAssembler v1（`alice/one/context.py`）：
  - **已完成**：骨架实现，待集成 RAG / Graph / Timeline

**验收：**
- 完成一次「处理新视频→问答→周报」后，在 Timeline 中能看到对应的事件链；
- 对不同 tenant，AliceIdentityService 输出的人设配置不同。

---

### Stage S2：AliceAgentCore 骨架 + AgentTask 统一入口 ✅

**目标：**  
实现 AliceAgentCore 的最小骨架与 AgentTask / AgentResult 类型，让新旧入口逐步过渡到统一 AgentCore，但暂时不引入复杂工具和 Planner。

**任务：**

- [x] 定义核心数据结构（放在 `alice/agent/types.py` 或类似文件）：
  - `AgentTask`：包含 tenant_id, scene, query, 以及可选的 user_id, video_id, extra_context 等；
  - `AgentResult`：包含 answer, citations, steps 等；
  - 可以先定义简化版 AgentPlan / AgentStep。
  - **已完成**：S0 已实现

- [x] 实现 StrategySelector（`alice/agent/strategy.py`）：
  - 根据 AgentTask.scene 选择 ChatStrategy / ResearchStrategy / TimelineStrategy，暂不做复杂意图识别。
  - **已完成**：S0 已实现

- [x] 实现 `AliceAgentCore.run_task(task: AgentTask)` 的最小版本（`alice/agent/core.py`）：
  - 使用 AliceIdentityService 构造 persona；
  - 使用简单的 ContextAssembler（可为占位）构造上下文 messages；
  - 调用现有 `services/ai` 的 LLM 接口（暂不启用 tools）；
  - 返回 AgentResult。
  - **已完成**：完整实现 5 步流程（策略选择 → Identity → Context → Messages → LLM）

- [x] 新增 Agent 入口 API（例如 `/api/agent/chat`）：
  - 构造 AgentTask → 调用 AliceAgentCore；
  - 原 `/api/chat` 暂时保持旧逻辑，只在内部增加一个选项允许走新 Agent 路径（feature flag）。
  - **已完成**：`apps/api/routers/agent.py` + 注册到 main.py
  - API 端点：`/api/v1/agent/chat`、`/api/v1/agent/strategies`、`/api/v1/agent/scenes`

**验收：**
- 通过 `/api/agent/chat` 能拿到与旧 `/api/chat` 质量相近的回答；
- 日志中可看到结构化的 AgentTask / AgentResult。

---

### Stage S3：ToolRouter + 本地基础工具（不含开源迁移）✅

**目标：**  
在 AgentCore 下接入最小的本地工具系统，为后续 Planner / SearchAgent / 开源工具迁移提供稳定的 Tool 层。

**任务：**

- [x] 实现 ToolRouter（`alice/agent/tool_router.py`）：
  - `list_tool_schemas(allowed_tools)` 返回当前场景/策略可用的工具 schema；
  - `execute(tool_name, args)` 负责调用对应工具；
  - `execute_safe(tool_name, args)` 安全执行（捕获异常）；
  - `create_with_basic_tools(db)` 工厂方法。
  - **已完成**

- [x] 定义 AliceTool 抽象基类：
  - `name`, `description`, `parameters`（JSON Schema）；
  - `async def run(self, args) -> Any`；
  - `to_schema()` 转换为 OpenAI function calling 格式。
  - **已完成**：S0 已实现，S3 完善

- [x] 实现一批简单本地工具（无需第三方）：
  - 放在 `alice/agent/tools/basic.py`：
    - `echo`（调试）；
    - `current_time`（支持 human/iso/timestamp 格式）；
    - `sleep`（最大 10 秒）；
    - `get_timeline_summary`（调用 TimelineService）；
    - `get_video_summary`（调用现有服务）；
    - `search_videos`（简单标题搜索）。
  - **已完成**：6 个基础工具

- [x] 在 `AliceAgentCore.run_task` 调 LLM 时，附带 tools schema，但不强制 LLM 必须调用工具。
  - **已完成**：`_call_llm_with_tools()` + 工具执行 + 结果追加

**验收：**
- 至少有 1–2 个基础工具能被 LLM 调用并正确返回结果；
- 工具调用失败时不会导致整个请求崩溃。

---

### Stage S4：引入 Planner / Executor 内核（OpenManus 范式迁移）✅

**目标：**  
让 Agent 从「单轮 LLM + 可选工具」升级到「多步 Plan → Tool → Observe → 再 Plan」的 ReAct 流程，先在本地工具场景验证。

**任务：**

- [x] 按 DESIGN 9.3 的迁移规范，从 OpenManus 拷贝并改写 Planner / Executor 逻辑：
  - 在 `third_party/openmanus` clone 官方仓库；
    - **已完成**：`https://github.com/FoundationAgents/OpenManus`
  - 在 `alice/agent/task_planner.py` 实现 TaskPlanner：
    - 接受 AgentTask + Context，输出 AgentPlan（step 列表）；
    - **已完成**：迁移自 OpenManus `app/flow/planning.py`
    - 新增 `PlanStepStatus` 枚举、计划存储、步骤标记
  - 在 `alice/agent/tool_executor.py` 实现 ToolExecutor：
    - 根据 AgentPlan 驱动 ReAct 循环：thought → tool_call → observation → next thought；
    - **已完成**：迁移自 OpenManus `app/agent/toolcall.py`
    - 新增 `AgentState` 枚举、特殊工具处理、cleanup()

- [x] 将 AliceAgentCore 切换为使用新的 Planner + Executor：
  - 所有 Agent 路径（Chat / Library / Video / Graph 等）都走：Strategy → Planner → Executor → ToolRouter。
  - **已完成**：S2 已集成基础流程，S4 完善 Planner/Executor

- [x] 为 AgentRun 记录 Plan / Steps，用于调试和后续 Eval。
  - **已完成**：`TaskPlanner.plans` 存储计划，`AgentStep` 记录执行步骤

**验收：**
- 至少一个任务展示了多步执行（例如「先看 timeline，再看两个视频，再总结」）；
- 日志中可以看到 Plan 和每一步的 tool 调用。

---

### Stage S5：SearchAgent + 深度 Web 搜索 ✅

**目标：**  
引入深度 Web 搜索能力，让 ResearchStrategy 在需要查外部世界时有一套独立的 SearchAgentService。

**任务：**

- [x] 在 `third_party/mindsearch` clone 官方仓库
  - **已完成**：`https://github.com/InternLM/MindSearch`

- [x] 实现 SearchAgentService：
  - `alice/search/search_agent.py`：
    - `_interpret_query()` - 规范化/增强问题
    - `_decompose_query()` - 生成子查询（规则 + LLM）
    - `_search_single_query()` - 多路搜索
    - `_fetch_and_analyze()` - 正文抽取（预留）
    - `_aggregate_sources()` - 去重/排序/截断
    - `_synthesize_answer()` - 综合回答
  - `alice/search/http_client.py`：
    - `SearchProvider` 抽象基类
    - `TavilySearchProvider` / `DuckDuckGoSearchProvider` / `MockSearchProvider`

- [x] 在 Tool 层暴露 `deep_web_research`：
  - `alice/agent/tools/search_tools.py`：`DeepWebResearchTool`
  - `ToolRouter.create_with_all_tools()` 注册

- [x] 在 ResearchStrategy 中启用该 Tool
  - `allowed_tools` 包含 `deep_web_research`
  - system prompt 指导使用时机

**验收：**
- [x] 45 个测试全部通过
- [x] SearchAgentService.run() 返回 sources > 0
- [x] answer 字段非空

---

### Stage S6：通用 Web / HTTP 工具包 ✅

**目标：**  
利用 strands-agents/tools 扩充 Web / HTTP / 计算工具，实现高质量的通用 Tool 包。

**任务：**

- [x] 在 `third_party/strands_agents_tools` clone 官方仓库
  - **已完成**：`https://github.com/strands-agents/tools`

- [x] 在 `alice/agent/tools/ext/` 下实现工具模块：
  - `basic.py`：CalculatorTool, CurrentTimeTool, SleepTool, EnvironmentTool, JournalTool
  - `files.py`：FileReadTool, FileWriteTool（安全目录限制）
  - `http_web.py`：HttpRequestTool, TavilySearchTool, TavilyExtractTool, ExaSearchTool, ExaGetContentsTool
  - `rss_cron.py`：RssTool, CronTool
  - `unsafe.py`：ShellTool, PythonReplTool, BrowserControlTool 等（默认不注册）

- [x] 在 ToolRouter 中新增 `create_with_ext_tools()` 方法

- [x] 安全控制：
  - FileReadTool/FileWriteTool 限制安全目录
  - HttpRequestTool 阻止内部地址访问
  - 高危工具需 `ALICE_UNSAFE_TOOLS_ENABLED=true` 才能注册

**验收：**
- [x] 55 个测试全部通过
- [x] calculator 支持安全的数学表达式计算
- [x] 高风险工具默认不注册

---

### Stage S7：MCP Client + 外部工具集成 ✅

**目标：**  
统一本地工具与外部 MCP 工具的调用方式，为未来扩展 Notion / GitHub 等外部服务打通通路。

**任务：**

- [x] 在 `third_party/gemini_cli` clone 官方仓库
  - **已完成**：`https://github.com/google-gemini/gemini-cli`

- [x] 在 `alice/agent/mcp_client.py` 实现 MCP Client：
  - `McpClient` - JSON-RPC 2.0 客户端
  - `McpRegistry` - 多端点管理
  - `MockMcpClient` - 测试用 Mock 实现
  - `McpToolResult` / `McpToolDescription` - 数据结构

- [x] 在 ToolRouter 中增加 MCP 工具支持：
  - `McpBackedTool` - MCP 工具包装为 AliceTool
  - `create_with_mcp()` - 创建包含 MCP 的 Router
  - `list_tool_schemas` 合并本地 + MCP 工具
  - `execute` 统一调用本地和 MCP 工具

- [x] 安全机制：
  - MCP 工具名与本地工具冲突时跳过
  - 默认无 MCP 配置时不报错

**验收：**
- [x] 65 个测试全部通过
- [x] ToolRouter 能列出并调用 MCP 工具
- [x] Mock MCP 工具可正常执行

---

### Stage S8：统一入口 + Eval / Console / 权限基础 ✅

**目标：**  
把所有主要入口统一到 `AliceAgentCore.run_task()`，并补上观测 / 回归 / 权限控制。

**任务：**

- [x] **统一入口适配层**：
  - `alice/one/entrypoints.py`：
    - `handle_chat_request()` - 通用 Chat 入口
    - `handle_qa_request()` - QA/知识库入口
    - `handle_video_chat_request()` - 视频问答入口
    - `handle_console_request()` - Console/Admin 入口
  - `/api/agent/chat` 已走 AliceAgentCore 路径

- [x] **Eval 基础设施**（`alice/eval/`）：
  - `models.py`：EvalCase, EvalSuite, EvalResult, EvalSuiteResult
  - `runner.py`：EvalRunner, get_default_suite()
  - `scorers.py`：SimpleScorer（规则评分）, LLMScorer（LLM 评分）

- [x] **Console API**（`apps/api/routers/console.py`）：
  - `GET /console/agent-runs` - 执行日志列表
  - `GET /console/agent-runs/{id}` - 执行详情
  - `GET /console/agent-runs/stats` - 统计信息
  - `POST /console/eval/run-suite` - 运行 Eval 套件
  - `GET /console/tools` - 工具列表

- [x] **权限与工具可见性**（`alice/agent/permissions.py`）：
  - `ToolVisibilityPolicy` - 工具可见性策略
  - `UserRole` - 用户角色枚举
  - 场景 × 角色 × 工具分类矩阵控制
  - 高危工具默认禁用

- [x] **Agent Run Logger**（`alice/agent/run_logger.py`）：
  - `AgentRunLogger` - 执行日志记录器
  - 支持内存和文件两种存储方式

**验收：**
- [x] 77 个测试全部通过
- [x] 普通用户无法访问 shell/python_repl
- [x] Admin + enable_unsafe 可访问高危工具

---

### Stage S9+：协作 / 插件生态（远期方向）

**目标：**  
不在当前迭代锁死实现细节，只确定方向与边界。

- **协作能力**：多人共享 Plan / Board / Timeline 视图；对共享对象的权限控制。
- **插件生态**：对外公开 Tool 定义与 MCP 接入规范，让第三方可以为 Alice One 写工具。

---

*文档版本: v0.8*  
*创建日期: 2024-12-01*
*最后更新: 2024-12-04*
