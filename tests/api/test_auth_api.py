"""
Auth API 集成测试

测试 /api/v1/auth/* 端点

【测试目标】
- 验证认证流程的正确性
- 发现边界条件下的问题
- 确保错误响应格式符合规范
"""

import pytest


class TestAuthLoginAPI:
    """POST /api/v1/auth/login 测试"""

    def test_login_missing_fields(self, client):
        """
        验证缺少必要字段返回 422
        
        预期：应返回 422 Unprocessable Entity
        """
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422, f"缺少字段应返回 422，实际返回 {response.status_code}"
        
        # 验证错误响应格式
        data = response.json()
        assert "detail" in data, "错误响应应包含 detail 字段"

    def test_login_missing_password(self, client):
        """验证只有 email 没有 password 返回 422"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 422, f"缺少 password 应返回 422，实际返回 {response.status_code}"

    def test_login_missing_email(self, client):
        """验证只有 password 没有 email 返回 422"""
        response = client.post("/api/v1/auth/login", json={
            "password": "password123"
        })
        assert response.status_code == 422, f"缺少 email 应返回 422，实际返回 {response.status_code}"

    def test_login_invalid_email_format(self, client):
        """
        验证无效邮箱格式
        
        预期：应返回 422（格式验证失败）或 401（认证失败）
        BUG: 如果返回 500，说明后端没有正确处理无效输入
        """
        response = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "password123"
        })
        
        # 严格验证：不应该返回 500
        assert response.status_code != 500, \
            f"无效邮箱不应导致 500 错误！响应内容: {response.text}"
        
        # 应返回 422 或 401
        assert response.status_code in [401, 422], \
            f"无效邮箱应返回 401 或 422，实际返回 {response.status_code}"

    def test_login_user_not_found(self, client):
        """
        验证用户不存在时返回 401
        
        预期：应返回 401 Unauthorized
        BUG: 如果返回 500，说明数据库查询异常未被正确捕获
        """
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        # 严格验证：不应该返回 500
        assert response.status_code != 500, \
            f"用户不存在不应导致 500 错误！响应内容: {response.text}"
        
        assert response.status_code == 401, \
            f"用户不存在应返回 401，实际返回 {response.status_code}"

    def test_login_empty_email(self, client):
        """验证空邮箱字符串"""
        response = client.post("/api/v1/auth/login", json={
            "email": "",
            "password": "password123"
        })
        assert response.status_code in [401, 422], \
            f"空邮箱应返回 401 或 422，实际返回 {response.status_code}"

    def test_login_empty_password(self, client):
        """验证空密码字符串"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": ""
        })
        assert response.status_code in [401, 422], \
            f"空密码应返回 401 或 422，实际返回 {response.status_code}"


class TestAuthRegisterAPI:
    """POST /api/v1/auth/register 测试"""

    def test_register_missing_fields(self, client):
        """验证缺少必要字段返回 422"""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422, \
            f"缺少字段应返回 422，实际返回 {response.status_code}"

    def test_register_invalid_email_format(self, client):
        """
        验证无效邮箱格式
        
        预期：应返回 422
        BUG: 如果返回 500，说明输入验证不完善
        """
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "username": "testuser"
        })
        
        assert response.status_code != 500, \
            f"无效邮箱不应导致 500 错误！响应内容: {response.text}"
        
        assert response.status_code == 422, \
            f"无效邮箱应返回 422，实际返回 {response.status_code}"

    def test_register_short_password(self, client):
        """
        验证密码太短
        
        预期：应返回 422 或 400
        """
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "123",
            "username": "testuser"
        })
        assert response.status_code in [400, 422], \
            f"短密码应返回 400 或 422，实际返回 {response.status_code}"

    def test_register_missing_username(self, client):
        """验证缺少用户名"""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })
        # 取决于 username 是否必填
        assert response.status_code in [200, 400, 422], \
            f"缺少用户名应返回合理状态码，实际返回 {response.status_code}"


class TestAuthMeAPI:
    """GET /api/v1/auth/me 测试"""

    def test_me_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401, \
            f"/me 未认证应返回 401，实际返回 {response.status_code}"

    def test_me_invalid_token(self, client):
        """验证无效 token 返回 401"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401, \
            f"无效 token 应返回 401，实际返回 {response.status_code}"

    def test_me_malformed_auth_header(self, client):
        """验证格式错误的 Authorization header"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "NotBearer token"}
        )
        assert response.status_code == 401, \
            f"格式错误的 Auth header 应返回 401，实际返回 {response.status_code}"

    def test_me_empty_token(self, client):
        """验证空 token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 401, \
            f"空 token 应返回 401，实际返回 {response.status_code}"


class TestAuthProfileAPI:
    """PUT /api/v1/auth/profile 测试"""

    def test_profile_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.put("/api/v1/auth/profile", json={
            "username": "newname"
        })
        assert response.status_code == 401, \
            f"更新 profile 未认证应返回 401，实际返回 {response.status_code}"


class TestAuthPasswordAPI:
    """PUT /api/v1/auth/password 测试"""

    def test_password_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.put("/api/v1/auth/password", json={
            "old_password": "old",
            "new_password": "new_password123"
        })
        assert response.status_code == 401, \
            f"更新密码未认证应返回 401，实际返回 {response.status_code}"


class TestAuthLogoutAPI:
    """POST /api/v1/auth/logout 测试"""

    def test_logout_requires_auth(self, client):
        """
        验证未认证请求的处理
        
        注意：logout 可能允许未认证请求（幂等设计）
        """
        response = client.post("/api/v1/auth/logout")
        # logout 可能返回 200（幂等）或 401（严格认证）
        # 但绝不应该返回 500
        assert response.status_code != 500, \
            f"logout 不应返回 500！响应内容: {response.text}"


class TestAuthSecurityEdgeCases:
    """安全边界测试"""

    def test_sql_injection_email(self, client):
        """测试 SQL 注入防护"""
        response = client.post("/api/v1/auth/login", json={
            "email": "' OR '1'='1",
            "password": "password"
        })
        # 应该正常返回错误，不应崩溃
        assert response.status_code != 500, \
            f"SQL 注入尝试不应导致 500！响应: {response.text}"

    def test_very_long_email(self, client):
        """测试超长邮箱"""
        long_email = "a" * 1000 + "@example.com"
        response = client.post("/api/v1/auth/login", json={
            "email": long_email,
            "password": "password"
        })
        # 应该返回验证错误，不应崩溃
        assert response.status_code in [401, 422], \
            f"超长邮箱应返回 401 或 422，实际返回 {response.status_code}"

    def test_very_long_password(self, client):
        """测试超长密码"""
        long_password = "a" * 10000
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": long_password
        })
        # 应该正常处理，不应崩溃
        assert response.status_code in [401, 422], \
            f"超长密码应返回 401 或 422，实际返回 {response.status_code}"

    def test_unicode_in_credentials(self, client):
        """测试 Unicode 字符"""
        response = client.post("/api/v1/auth/login", json={
            "email": "测试@例子.com",
            "password": "密码123"
        })
        # 应该正常处理
        assert response.status_code in [401, 422], \
            f"Unicode 凭据应返回 401 或 422，实际返回 {response.status_code}"

    def test_null_values(self, client):
        """测试 null 值"""
        response = client.post("/api/v1/auth/login", json={
            "email": None,
            "password": None
        })
        assert response.status_code == 422, \
            f"null 值应返回 422，实际返回 {response.status_code}"
