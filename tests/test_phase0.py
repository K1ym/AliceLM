"""
Phase 0: 基础设施测试
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from packages.config import get_settings
from packages.db.models import (
    Tenant,
    TenantConfig,
    TenantPlan,
    User,
    UserRole,
    Video,
    VideoStatus,
    WatchedFolder,
)


class TestProjectStructure:
    """P0-AC-01: 项目结构完整性测试"""

    def test_directories_exist(self):
        """验证核心目录存在"""
        base_path = Path(__file__).parent.parent
        
        required_dirs = [
            "apps",
            "apps/api",
            "apps/web",
            "services",
            "services/watcher",
            "services/processor",
            "services/asr",
            "services/ai",
            "services/mcp",
            "services/notifier",
            "packages",
            "packages/db",
            "packages/config",
            "tests",
            "config",
            "docs",
        ]
        
        for dir_name in required_dirs:
            dir_path = base_path / dir_name
            assert dir_path.exists(), f"目录 {dir_name} 不存在"

    def test_pyproject_exists(self):
        """验证pyproject.toml存在"""
        base_path = Path(__file__).parent.parent
        assert (base_path / "pyproject.toml").exists()


class TestDatabaseSetup:
    """P0-AC-02: 数据库测试"""

    def test_create_tenant(self, db_session: Session):
        """创建租户"""
        tenant = Tenant(name="Test Org", slug="test-org")
        db_session.add(tenant)
        db_session.commit()
        
        assert tenant.id is not None
        assert tenant.plan == TenantPlan.FREE
        assert tenant.is_active is True

    def test_create_user_with_tenant(self, db_session: Session):
        """创建用户并关联租户"""
        tenant = Tenant(name="Test", slug="test")
        user = User(email="test@example.com", username="testuser", tenant=tenant)
        db_session.add_all([tenant, user])
        db_session.commit()
        
        assert user.tenant_id == tenant.id
        assert user.role == UserRole.MEMBER

    def test_create_video(self, db_session: Session, sample_tenant: Tenant):
        """创建视频"""
        video = Video(
            source_type="bilibili", source_id="BV123456",
            title="测试视频",
            author="UP主",
            duration=300,
            tenant_id=sample_tenant.id,
        )
        db_session.add(video)
        db_session.commit()
        
        assert video.id is not None
        # status 可能返回字符串或枚举，统一比较值
        assert str(video.status) == "pending" or video.status == VideoStatus.PENDING

    def test_video_tenant_isolation(self, db_session: Session):
        """视频租户隔离"""
        t1 = Tenant(name="T1", slug="t1")
        t2 = Tenant(name="T2", slug="t2")
        db_session.add_all([t1, t2])
        db_session.commit()
        
        v1 = Video(source_type="bilibili", source_id="BV123", title="Video1", author="A", tenant_id=t1.id)
        v2 = Video(source_type="bilibili", source_id="BV456", title="Video2", author="B", tenant_id=t2.id)
        db_session.add_all([v1, v2])
        db_session.commit()
        
        # 验证隔离
        assert v1.tenant_id != v2.tenant_id
        
        # 同一租户下bvid唯一
        v3 = Video(source_type="bilibili", source_id="BV789", title="Video3", author="C", tenant_id=t1.id)
        db_session.add(v3)
        db_session.commit()
        
        t1_videos = db_session.query(Video).filter(Video.tenant_id == t1.id).all()
        assert len(t1_videos) == 2

    def test_tenant_config(self, db_session: Session, sample_tenant: Tenant):
        """租户配置"""
        config = TenantConfig(
            tenant_id=sample_tenant.id,
            key="asr_provider",
            value="faster_whisper",
        )
        db_session.add(config)
        db_session.commit()
        
        assert config.id is not None

    def test_watched_folder(self, db_session: Session, sample_tenant: Tenant):
        """监控收藏夹"""
        folder = WatchedFolder(
            tenant_id=sample_tenant.id,
            folder_id="12345",
            folder_type="favlist",
            name="测试收藏夹",
        )
        db_session.add(folder)
        db_session.commit()
        
        assert folder.id is not None
        assert folder.is_active is True


class TestConfigSystem:
    """P0-AC-03: 配置系统测试"""

    def test_load_default_settings(self):
        """加载默认配置"""
        settings = get_settings()
        
        assert settings.app_name == "AliceLM"
        # 支持更多 ASR 提供商
        assert settings.asr.provider in ["whisper_local", "faster_whisper", "groq_whisper", "xunfei"]
        assert settings.llm.provider in ["openai", "anthropic", "ollama"]

    def test_env_override(self, monkeypatch):
        """环境变量覆盖配置"""
        monkeypatch.setenv("ALICE_ASR__PROVIDER", "xunfei")
        monkeypatch.setenv("ALICE_DEBUG", "true")
        
        # 重新加载配置
        from packages.config.settings import Settings
        settings = Settings()
        
        assert settings.asr.provider == "xunfei"
        assert settings.debug is True

    def test_database_config(self):
        """数据库配置"""
        settings = get_settings()
        
        assert settings.database.url is not None
        assert "sqlite" in settings.database.url or "postgresql" in settings.database.url

    def test_yaml_config_path(self):
        """YAML配置文件路径"""
        # F7 配置管理：配置文件迁移到 config/base/
        config_path = Path(__file__).parent.parent / "config" / "base" / "default.yaml"
        assert config_path.exists(), "默认配置文件不存在"
