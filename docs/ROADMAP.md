# 🚀 AliceLM 开发路线图

> 本文档定义开发阶段、任务分解、验收标准和测试方案

---

## 📊 当前进度

```
Phase 0: 基础设施   [██████████] 100% ✅ (8/8 任务完成)
Phase 1: MVP核心    [██████████] 100% ✅ (12/12 任务完成)
Phase 2: AI增强     [█████████░] 90% ✅ (13/14 任务完成)
Phase 3: 多端集成   [██████████] 100% ✅ (11/11 任务完成)
Phase 4: 知识网络   [██░░░░░░░░] 20% 🔄 进行中
```

**最后更新**: 2024-12-04  
**当前阶段**: Phase 3 完成 ✅ → Phase 4 进行中  
**已交付**: Web UI + API + MCP Server + 分层架构重构

---

## 1. 开发阶段总览

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

| 阶段 | 目标 | 核心交付 | 预计时间 |
|------|------|----------|----------|
| **Phase 0** | 搭建基础设施 | 项目骨架、DB、配置系统 | 1周 |
| **Phase 1** | 跑通核心闭环 | 收藏→转写→通知 | 2周 |
| **Phase 2** | AI能力增强 | 摘要、问答、RAGFlow集成 | 2周 |
| **Phase 3** | 多端接入 | Web UI、MCP Server | 2周 |
| **Phase 4** | 知识网络 | 关联、图谱、学习追踪 | 2周 |
| **Phase 5** | 生产就绪 | 多租户、监控、优化 | 持续 |

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

*文档版本: v0.1*  
*创建日期: 2024-12-01*
*最后更新: 2024-12-01*
