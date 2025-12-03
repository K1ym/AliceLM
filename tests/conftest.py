"""
Pytest配置和fixtures
"""

import os
import tempfile
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 设置测试环境
os.environ["ALICE_DB__URL"] = "sqlite:///:memory:"
os.environ["ALICE_DEBUG"] = "true"

from packages.db.database import Base
from packages.db.models import Tenant, User, Video


@pytest.fixture(scope="function")
def db_engine():
    """创建测试数据库引擎"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_tenant(db_session: Session) -> Tenant:
    """创建测试租户"""
    tenant = Tenant(name="Test Org", slug="test-org")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def sample_user(db_session: Session, sample_tenant: Tenant) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        username="testuser",
        tenant_id=sample_tenant.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
