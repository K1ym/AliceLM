# 多内容源重构计划

## 背景

当前代码与 B 站深度耦合，无法支持 YouTube、播客/RSS、本地文件等内容源。本文档规划从"B 站视频助手"到"通用知识助手"的重构路径。

## 核心问题

| 问题 | 位置 | 影响 |
|------|------|------|
| `bvid` 字段硬编码 | `packages/db/models.py` | 数据模型绑定 B 站 |
| `bilibili_uid/sessdata` 在 User 表 | `packages/db/models.py` | 平台凭证无法扩展 |
| 下载器无抽象 | `services/downloader/` | 无法支持新平台 |
| Pipeline 硬编码 B 站逻辑 | `services/processor/pipeline.py` | 处理流程不通用 |
| API/前端依赖 `bvid` | `apps/api/`, `apps/web/` | 接口不通用 |

## 设计目标

1. **数据模型通用化**：`bvid` → `source_id`，支持任意内容源
2. **下载器抽象**：`ContentDownloader` 接口 + 平台实现
3. **Pipeline 适配**：根据 `source_type` 分发处理逻辑
4. **API 破坏性变更**：前端同步适配

## 第一个新内容源：播客/RSS

选择播客/RSS 作为第一个扩展目标，因为：
- 下载逻辑简单（HTTP 直接下载音频）
- 不需要复杂的认证
- 验证抽象设计是否正确

---

## Phase 1: 数据模型重构

### 1.1 Video 表变更

```python
# 变更前
class Video(Base):
    bvid: Mapped[str] = mapped_column(String(20), index=True)
    source_type: Mapped[str] = mapped_column(String(20), default="bilibili")

    __table_args__ = (
        UniqueConstraint("tenant_id", "bvid", name="uq_tenant_video"),
    )

# 变更后
class Video(Base):
    source_type: Mapped[str] = mapped_column(String(20), default="bilibili", index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)  # bvid / youtube_id / rss_guid / file_hash
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_id", name="uq_tenant_source"),
        Index("ix_tenant_source_type", "tenant_id", "source_type"),
    )
```

### 1.2 新增 UserPlatformBinding 表

```python
class UserPlatformBinding(Base):
    """用户平台绑定"""
    __tablename__ = "user_platform_bindings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)

    platform: Mapped[str] = mapped_column(String(20))  # bilibili / youtube / ...
    platform_uid: Mapped[str] = mapped_column(String(100))
    credentials: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: token/sessdata/...

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "platform", name="uq_user_platform"),
    )
```

### 1.3 User 表清理

```python
# 移除
bilibili_uid: Mapped[Optional[str]]
bilibili_sessdata: Mapped[Optional[str]]

# 新增关系
platform_bindings: Mapped[List["UserPlatformBinding"]] = relationship(...)
```

### 1.4 WatchedFolder 表调整

```python
# 变更前
folder_type: Mapped[str]  # favlist / season / subscription

# 变更后
source_type: Mapped[str]  # bilibili_favlist / bilibili_season / youtube_playlist / rss_feed
```

### 1.5 数据迁移脚本

```python
# alembic/versions/xxx_multi_source.py

def upgrade():
    # 1. 添加新字段
    op.add_column('videos', sa.Column('source_id', sa.String(100), nullable=True))

    # 2. 迁移数据
    op.execute("UPDATE videos SET source_id = bvid WHERE source_id IS NULL")

    # 3. 设置 NOT NULL
    op.alter_column('videos', 'source_id', nullable=False)

    # 4. 删除旧约束，添加新约束
    op.drop_constraint('uq_tenant_video', 'videos')
    op.create_unique_constraint('uq_tenant_source', 'videos', ['tenant_id', 'source_type', 'source_id'])

    # 5. 删除旧字段
    op.drop_column('videos', 'bvid')

    # 6. 创建 UserPlatformBinding 表
    op.create_table('user_platform_bindings', ...)

    # 7. 迁移 User 表的 bilibili 凭证
    op.execute("""
        INSERT INTO user_platform_bindings (user_id, platform, platform_uid, credentials)
        SELECT id, 'bilibili', bilibili_uid, json_object('sessdata', bilibili_sessdata)
        FROM users WHERE bilibili_uid IS NOT NULL
    """)

    # 8. 删除 User 表的 bilibili 字段
    op.drop_column('users', 'bilibili_uid')
    op.drop_column('users', 'bilibili_sessdata')
```

---

## Phase 2: 下载器抽象

### 2.1 定义接口

```python
# services/downloader/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

class DownloadMode(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"

@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    subtitle_content: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0

class ContentDownloader(ABC):
    """内容下载器抽象接口"""

    @property
    @abstractmethod
    def source_type(self) -> str:
        """返回支持的内容源类型"""
        pass

    @abstractmethod
    async def download(
        self,
        source_id: str,
        mode: DownloadMode = DownloadMode.AUDIO,
        output_dir: Optional[Path] = None,
    ) -> DownloadResult:
        """下载内容"""
        pass

    @abstractmethod
    async def get_metadata(self, source_id: str) -> dict:
        """获取内容元数据（标题、作者、时长等）"""
        pass
```

### 2.2 B 站实现

```python
# services/downloader/bilibili.py

class BilibiliDownloader(ContentDownloader):

    @property
    def source_type(self) -> str:
        return "bilibili"

    async def download(self, source_id: str, mode: DownloadMode, output_dir: Path) -> DownloadResult:
        # 复用现有 BBDownService 逻辑
        ...

    async def get_metadata(self, source_id: str) -> dict:
        # 调用 B 站 API
        ...
```

### 2.3 播客/RSS 实现

```python
# services/downloader/podcast.py

class PodcastDownloader(ContentDownloader):

    @property
    def source_type(self) -> str:
        return "podcast"

    async def download(self, source_id: str, mode: DownloadMode, output_dir: Path) -> DownloadResult:
        # source_id 是音频 URL 或 RSS item guid
        # 直接 HTTP 下载
        ...

    async def get_metadata(self, source_id: str) -> dict:
        # 从 RSS feed 解析
        ...
```

### 2.4 工厂函数

```python
# services/downloader/__init__.py

_downloaders: dict[str, ContentDownloader] = {}

def register_downloader(downloader: ContentDownloader):
    _downloaders[downloader.source_type] = downloader

def get_downloader(source_type: str) -> ContentDownloader:
    if source_type not in _downloaders:
        raise ValueError(f"Unsupported source type: {source_type}")
    return _downloaders[source_type]

# 注册默认下载器
register_downloader(BilibiliDownloader())
register_downloader(PodcastDownloader())
```

---

## Phase 3: Pipeline 适配

### 3.1 修改 VideoPipeline

```python
# services/processor/pipeline.py

class VideoPipeline:

    def process(self, video: Video, db: Session, user_id: Optional[int] = None) -> Video:
        try:
            # Step 1: 根据 source_type 获取下载器
            downloader = get_downloader(video.source_type)

            video.status = VideoStatus.DOWNLOADING.value
            db.commit()

            logger.info("pipeline_step", step="download", source_type=video.source_type, source_id=video.source_id)

            # Step 2: 下载
            result = await downloader.download(
                source_id=video.source_id,
                mode=DownloadMode.AUDIO,
                output_dir=self.output_dir / video.source_type / video.source_id,
            )

            if not result.success:
                raise Exception(f"Download failed: {result.error}")

            audio_path = result.file_path
            ai_subtitle = result.subtitle_content

            # Step 3: 转写（逻辑不变）
            ...

            # Step 4: AI 分析（逻辑不变）
            ...
```

### 3.2 文件命名规范

```python
# 变更前
txt_path = self.transcript_dir / f"{bvid}.txt"

# 变更后
txt_path = self.transcript_dir / f"{video.source_type}_{video.source_id}.txt"
# 或者直接用 video.id
txt_path = self.transcript_dir / f"{video.id}.txt"
```

---

## Phase 3.5: RAG 适配

### 3.5.1 修改 metadata 字段

```python
# alice/rag/service.py

# 变更前
metadata = {
    "bvid": video.bvid,
    "author": video.author,
    "duration": video.duration,
}

# 变更后
metadata = {
    "source_type": video.source_type,
    "source_id": video.source_id,
    "author": video.author,
    "duration": video.duration,
}
```

### 3.5.2 FallbackRAGService 同步修改

```python
# 变更前
metadata={"bvid": v.bvid}

# 变更后
metadata={"source_type": v.source_type, "source_id": v.source_id}
```

---

## Phase 4: API 适配

### 4.1 Schema 变更

```python
# apps/api/schemas.py

class VideoResponse(BaseModel):
    id: int
    source_type: str
    source_id: str
    source_url: Optional[str]
    title: str
    author: str
    # ... 其他字段
```

### 4.2 Repository 变更

```python
# apps/api/repositories/video_repo.py

def get_by_source(self, tenant_id: int, source_type: str, source_id: str) -> Optional[Video]:
    return (
        self.db.query(Video)
        .filter(
            Video.tenant_id == tenant_id,
            Video.source_type == source_type,
            Video.source_id == source_id,
        )
        .first()
    )
```

### 4.3 Router 变更

```python
# apps/api/routers/videos.py

# 变更前
@router.post("/import")
async def import_video(url: str):
    bvid = parse_bvid(url)
    ...

# 变更后
@router.post("/import")
async def import_video(url: str):
    source_type, source_id = parse_source(url)  # 自动识别平台
    ...
```

---

## Phase 5: 前端适配

### 5.1 类型定义

```typescript
// apps/web/src/lib/api/types.ts

interface Video {
  id: number
  source_type: string  // "bilibili" | "youtube" | "podcast" | "local"
  source_id: string
  source_url?: string
  title: string
  author: string
  // ...
}
```

### 5.2 条件渲染

```tsx
// 播放器嵌入
{video.source_type === 'bilibili' && (
  <iframe src={`//player.bilibili.com/player.html?bvid=${video.source_id}`} />
)}
{video.source_type === 'youtube' && (
  <iframe src={`https://www.youtube.com/embed/${video.source_id}`} />
)}
{video.source_type === 'podcast' && (
  <audio src={video.source_url} controls />
)}

// 外链
function getSourceUrl(video: Video): string {
  switch (video.source_type) {
    case 'bilibili': return `https://www.bilibili.com/video/${video.source_id}`
    case 'youtube': return `https://www.youtube.com/watch?v=${video.source_id}`
    case 'podcast': return video.source_url || '#'
    default: return '#'
  }
}
```

---

## 实施顺序

1. **Phase 1**: 数据模型重构 + 迁移脚本
2. **Phase 4**: API 适配（同时进行，因为 API 依赖数据模型）
3. **Phase 5**: 前端适配（API 完成后）
4. **Phase 2**: 下载器抽象（可并行）
5. **Phase 3**: Pipeline 适配（依赖下载器抽象）

## 风险点

1. **数据迁移**：需要在低峰期执行，建议先备份
2. **前端同步**：API 变更后前端必须同步更新，否则会崩溃
3. **测试覆盖**：现有测试可能依赖 `bvid`，需要更新
4. **Pipeline async 改造**：当前 `process()` 是 sync，下载器改 async 后需要适配

## 注意事项

### Pipeline async 适配

当前 `VideoPipeline.process()` 是同步方法，但新的 `ContentDownloader.download()` 是 async。两种处理方式：

**方案 A：保持 sync，用 asyncio.run() 包装（推荐，改动小）**
```python
def process(self, video: Video, db: Session, ...):
    downloader = get_downloader(video.source_type)
    result = asyncio.run(downloader.download(video.source_id, ...))
    ...
```

**方案 B：Pipeline 改成 async（改动大，需要适配调度层）**
```python
async def process(self, video: Video, db: Session, ...):
    downloader = get_downloader(video.source_type)
    result = await downloader.download(video.source_id, ...)
    ...
```

建议先用方案 A，后续再考虑全面 async 化。

### 测试数据更新

现有测试用 `bvid` 造假数据，需要同步更新：

```python
# 变更前
video = Video(bvid="BV1234567890", title="Test", ...)

# 变更后
video = Video(source_type="bilibili", source_id="BV1234567890", title="Test", ...)
```

需要更新的测试文件：
- `tests/conftest.py` — fixtures
- `tests/api/test_videos_api.py`
- 其他使用 Video 模型的测试

## 验收标准

- [ ] 现有 B 站视频功能正常
- [ ] 可以导入播客/RSS 内容
- [ ] API 返回 `source_type` + `source_id`
- [ ] 前端根据 `source_type` 正确渲染
