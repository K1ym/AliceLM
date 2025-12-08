"""
Pytest配置和fixtures

提供测试用的数据库、API 客户端和各种 fixtures

关键设计：
- 所有 API 测试使用同一个内存数据库实例
- test_db_session 供测试代码直接操作数据库
- API 通过依赖注入使用同一个数据库
"""

import os
import tempfile
from typing import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# 设置测试环境（必须在导入其他模块之前）
os.environ["ALICE_DB__URL"] = "sqlite:///:memory:"
os.environ["ALICE_DEBUG"] = "true"
os.environ["ALICE_LLM__API_KEY"] = "test-key"
os.environ["ALICE_LLM__BASE_URL"] = "http://localhost:11434/v1"

from packages.db.database import Base
from packages.db.models import Tenant, User, Video


# ============== 核心数据库 Fixtures ==============

@pytest.fixture(scope="function")
def db_engine():
    """
    创建测试数据库引擎
    
    使用 StaticPool 确保多线程下使用同一连接
    这对于 FastAPI TestClient 在后台线程运行至关重要
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 关键：所有请求使用同一连接
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    创建测试数据库会话
    
    用于单元测试中直接操作数据库
    """
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============== API 集成测试 Fixtures ==============

@pytest.fixture(scope="function")
def test_app(db_engine):
    """
    创建测试用 FastAPI 应用
    
    关键：使用与其他 fixtures 相同的 db_engine
    确保依赖注入返回正确的数据库会话
    """
    from fastapi.testclient import TestClient
    from apps.api.main import app
    from apps.api.deps import get_db, get_current_tenant, get_current_user
    
    # 创建绑定到同一 engine 的 session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    
    # 创建默认测试租户和管理员用户
    setup_session = TestSessionLocal()
    try:
        test_tenant = Tenant(name="Test Tenant", slug="test-tenant")
        setup_session.add(test_tenant)
        setup_session.commit()
        test_tenant_id = test_tenant.id
        
        # 创建开发模式下的默认用户
        admin_user = User(
            email="admin@local",
            username="admin",
            tenant_id=test_tenant_id,
        )
        setup_session.add(admin_user)
        setup_session.commit()
    finally:
        setup_session.close()
    
    def override_get_db():
        """返回绑定到测试 engine 的数据库会话"""
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # 注册依赖覆盖
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # 清理
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(test_app) -> Generator:
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    with TestClient(test_app) as c:
        yield c


@pytest.fixture(scope="function")
def test_db_session(db_engine) -> Generator[Session, None, None]:
    """
    API 测试专用的数据库会话
    
    与 test_app 共享同一个 db_engine，
    确保测试代码插入的数据对 API 可见
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_tenant(db_session: Session) -> Tenant:
    """创建测试租户（用于单元测试）"""
    tenant = Tenant(name="Test Org", slug="test-org")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_tenant(test_db_session: Session) -> Tenant:
    """
    获取 API 测试用的租户
    
    这会返回 test_app 中创建的默认租户
    """
    tenant = test_db_session.query(Tenant).filter(Tenant.slug == "test-tenant").first()
    if not tenant:
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_db_session.add(tenant)
        test_db_session.commit()
        test_db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_user(db_session: Session, sample_tenant: Tenant) -> User:
    """创建测试用户（用于单元测试）"""
    user = User(
        email="test@example.com",
        username="testuser",
        tenant_id=sample_tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user(test_db_session: Session, test_tenant: Tenant) -> User:
    """
    创建 API 测试用的用户
    
    使用 test_db_session 确保与 API 共享数据库
    """
    from packages.db.models import User
    
    user = User(
        email="testuser@example.com",
        username="testuser",
        tenant_id=test_tenant.id,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_db_session, test_tenant) -> dict:
    """
    获取认证 headers
    
    1. 在共享数据库中创建测试用户
    2. 通过 API 登录获取 token
    """
    import hashlib
    from packages.db.models import User
    
    # 创建带密码的用户
    password = "testpass123"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    user = User(
        email="auth_test@example.com",
        username="authuser",
        password_hash=password_hash,
        tenant_id=test_tenant.id,
    )
    test_db_session.add(user)
    test_db_session.commit()
    
    # 通过 API 登录
    response = client.post("/api/v1/auth/login", json={
        "email": "auth_test@example.com",
        "password": password,
    })
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    # 如果登录失败，返回空 headers（可能认证服务实现不同）
    return {}


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_video(db_session: Session, sample_tenant: Tenant) -> Video:
    """创建测试视频（用于单元测试）"""
    video = Video(
        source_type="bilibili",
        source_id="BV1test123",
        title="测试视频",
        author="测试作者",
        tenant_id=sample_tenant.id,
        status="done",
        duration=120,
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)
    return video


@pytest.fixture
def test_video(test_db_session: Session, test_tenant: Tenant) -> Video:
    """创建 API 测试用的视频"""
    video = Video(
        source_type="bilibili",
        source_id="BV1apitest",
        title="API测试视频",
        author="测试作者",
        tenant_id=test_tenant.id,
        status="done",
        duration=120,
    )
    test_db_session.add(video)
    test_db_session.commit()
    test_db_session.refresh(video)
    return video
