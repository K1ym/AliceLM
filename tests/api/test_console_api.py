"""
Console API 集成测试

测试 /api/v1/console/* 端点

【测试目标】
- 验证 Console API 的认证和授权
- 验证 AgentRun 日志查询功能
- 验证 Eval 执行功能
- 发现边界条件下的问题
"""

import pytest
from unittest.mock import patch, MagicMock


class TestConsoleAgentRunsAPI:
    """GET /api/v1/console/agent-runs 测试"""

    def test_get_agent_runs_requires_auth(self, client):
        """
        验证未认证请求返回 401
        
        Console API 必须要求认证，不应暴露给匿名用户
        """
        response = client.get("/api/v1/console/agent-runs")
        assert response.status_code == 401, \
            f"Console API 未认证应返回 401，实际返回 {response.status_code}"

    def test_get_agent_runs_returns_list(self, client):
        """
        验证认证后返回列表格式
        
        即使为空，也应该返回空数组而非 null
        """
        response = client.get("/api/v1/console/agent-runs")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), \
                f"agent-runs 应返回数组，实际返回 {type(data)}"

    def test_get_agent_runs_invalid_limit(self, client):
        """验证无效的 limit 参数"""
        response = client.get("/api/v1/console/agent-runs?limit=-1")
        # 负数 limit 应返回 422 或被忽略
        assert response.status_code in [200, 401, 422], \
            f"负数 limit 应返回合理状态码，实际返回 {response.status_code}"

    def test_get_agent_runs_invalid_offset(self, client):
        """验证无效的 offset 参数"""
        response = client.get("/api/v1/console/agent-runs?offset=-1")
        assert response.status_code in [200, 401, 422], \
            f"负数 offset 应返回合理状态码，实际返回 {response.status_code}"

    def test_get_agent_runs_very_large_limit(self, client):
        """验证超大 limit 不会导致问题"""
        response = client.get("/api/v1/console/agent-runs?limit=999999")
        # 不应崩溃
        assert response.status_code != 500, \
            f"超大 limit 不应导致 500！响应: {response.text}"

    def test_get_agent_runs_invalid_scene_filter(self, client):
        """验证无效 scene 过滤器"""
        response = client.get("/api/v1/console/agent-runs?scene=invalid_scene_xyz")
        # 无效 scene 应返回空列表或被忽略，不应崩溃
        assert response.status_code != 500, \
            f"无效 scene 不应导致 500！响应: {response.text}"


class TestConsoleAgentRunDetailAPI:
    """GET /api/v1/console/agent-runs/{run_id} 测试"""

    def test_get_run_detail_requires_auth(self, client):
        """验证未认证请求返回 401"""
        response = client.get("/api/v1/console/agent-runs/some-id")
        assert response.status_code == 401, \
            f"详情 API 未认证应返回 401，实际返回 {response.status_code}"

    def test_get_run_detail_not_found(self, client):
        """
        验证不存在的 run_id 返回 404
        
        BUG: 如果返回 500，说明异常未被正确处理
        """
        response = client.get("/api/v1/console/agent-runs/nonexistent-id-12345")
        
        # 不应返回 500
        if response.status_code not in [401]:
            assert response.status_code == 404, \
                f"不存在的 ID 应返回 404，实际返回 {response.status_code}"

    def test_get_run_detail_empty_id(self, client):
        """验证空 ID 的处理"""
        # 尾部斜杠会被路由为列表端点
        response = client.get("/api/v1/console/agent-runs/")
        assert response.status_code in [200, 307, 401, 404, 405], \
            f"空 ID 应返回合理状态码，实际返回 {response.status_code}"

    def test_get_run_detail_special_characters_id(self, client):
        """验证特殊字符 ID 的处理"""
        response = client.get("/api/v1/console/agent-runs/../../etc/passwd")
        # 应该安全处理，不应崩溃
        assert response.status_code != 500, \
            f"特殊字符 ID 不应导致 500！响应: {response.text}"


class TestConsoleAgentRunStatsAPI:
    """GET /api/v1/console/agent-runs/stats 测试"""

    def test_get_stats_requires_auth(self, client):
        """验证统计 API 需要认证"""
        response = client.get("/api/v1/console/agent-runs/stats")
        assert response.status_code == 401, \
            f"统计 API 未认证应返回 401，实际返回 {response.status_code}"

    def test_get_stats_response_format(self, client):
        """验证统计响应格式正确"""
        response = client.get("/api/v1/console/agent-runs/stats")
        
        if response.status_code == 200:
            data = response.json()
            # 验证必要字段存在
            required_fields = ["total_runs", "success_rate", "avg_duration_ms", "scenes"]
            for field in required_fields:
                assert field in data, f"统计响应缺少字段: {field}"
            
            # 验证数据类型
            assert isinstance(data["total_runs"], int), "total_runs 应为整数"
            assert isinstance(data["success_rate"], (int, float)), "success_rate 应为数字"
            assert isinstance(data["scenes"], dict), "scenes 应为字典"


class TestConsoleEvalAPI:
    """POST /api/v1/console/eval/* 测试"""

    def test_run_eval_suite_requires_auth(self, client):
        """验证 Eval API 需要认证"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "test",
            "cases": []
        })
        assert response.status_code == 401, \
            f"Eval API 未认证应返回 401，实际返回 {response.status_code}"

    def test_run_eval_suite_missing_name(self, client):
        """验证缺少 name 字段"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "cases": []
        })
        # 缺少必要字段应返回 422
        assert response.status_code in [401, 422], \
            f"缺少 name 应返回 422，实际返回 {response.status_code}"

    def test_run_eval_suite_missing_cases(self, client):
        """验证缺少 cases 字段"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "test"
        })
        assert response.status_code in [401, 422], \
            f"缺少 cases 应返回 422，实际返回 {response.status_code}"

    def test_run_eval_suite_empty_body(self, client):
        """验证空请求体"""
        response = client.post("/api/v1/console/eval/run-suite", json={})
        assert response.status_code in [401, 422], \
            f"空请求体应返回 422，实际返回 {response.status_code}"

    def test_run_eval_suite_invalid_case_missing_query(self, client):
        """
        验证 case 缺少必要的 query 字段
        
        每个 case 必须有 query
        """
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "test",
            "cases": [
                {"scene": "chat"}  # 缺少 query
            ]
        })
        # 应返回验证错误
        assert response.status_code in [401, 422], \
            f"case 缺少 query 应返回 422，实际返回 {response.status_code}"

    def test_run_eval_suite_invalid_case_invalid_scene(self, client):
        """验证无效的 scene 值"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "test",
            "cases": [
                {"scene": "invalid_scene", "query": "test"}
            ]
        })
        # 可能接受（默认为 chat）或拒绝
        assert response.status_code != 500, \
            f"无效 scene 不应导致 500！响应: {response.text}"

    def test_run_eval_suite_null_cases(self, client):
        """验证 cases 为 null"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "test",
            "cases": None
        })
        assert response.status_code in [401, 422], \
            f"null cases 应返回 422，实际返回 {response.status_code}"

    def test_run_default_eval_requires_auth(self, client):
        """验证默认 Eval 需要认证"""
        response = client.post("/api/v1/console/eval/run-default")
        assert response.status_code == 401, \
            f"默认 Eval 未认证应返回 401，实际返回 {response.status_code}"


class TestConsoleToolsAPI:
    """GET /api/v1/console/tools 测试"""

    def test_get_tools_requires_auth(self, client):
        """验证工具列表需要认证"""
        response = client.get("/api/v1/console/tools")
        assert response.status_code == 401, \
            f"工具列表未认证应返回 401，实际返回 {response.status_code}"

    def test_get_tools_response_format(self, client):
        """验证工具列表响应格式"""
        response = client.get("/api/v1/console/tools")
        
        if response.status_code == 200:
            data = response.json()
            # 验证必要字段
            assert "tools" in data, "响应应包含 tools 字段"
            assert "total_tools" in data, "响应应包含 total_tools 字段"
            assert "allowed_tools" in data, "响应应包含 allowed_tools 字段"
            
            # 验证类型
            assert isinstance(data["tools"], list), "tools 应为数组"
            assert isinstance(data["total_tools"], int), "total_tools 应为整数"
            assert isinstance(data["allowed_tools"], int), "allowed_tools 应为整数"

    def test_get_tools_invalid_scene(self, client):
        """验证无效 scene 参数"""
        response = client.get("/api/v1/console/tools?scene=invalid_xyz")
        # 不应崩溃
        assert response.status_code != 500, \
            f"无效 scene 不应导致 500！响应: {response.text}"


class TestConsoleSecurityEdgeCases:
    """安全边界测试"""

    def test_sql_injection_in_run_id(self, client):
        """测试 run_id 参数 SQL 注入防护"""
        response = client.get("/api/v1/console/agent-runs/' OR '1'='1")
        assert response.status_code != 500, \
            f"SQL 注入尝试不应导致 500！响应: {response.text}"

    def test_xss_in_eval_suite_name(self, client):
        """测试 Eval suite name XSS 防护"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "<script>alert('xss')</script>",
            "cases": []
        })
        # 应正常处理，不应崩溃
        assert response.status_code in [401, 422, 200], \
            f"XSS 尝试应被正常处理，实际返回 {response.status_code}"

    def test_very_large_eval_suite(self, client):
        """测试超大 Eval 套件"""
        # 生成 1000 个 cases
        large_cases = [{"scene": "chat", "query": f"问题 {i}"} for i in range(1000)]
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "large_test",
            "cases": large_cases
        })
        # 可能因为超时或资源限制返回错误，但不应崩溃
        assert response.status_code != 500 or "timeout" in response.text.lower(), \
            f"超大套件不应导致非超时的 500！响应: {response.text[:200]}"

    def test_unicode_in_query(self, client):
        """测试 Unicode 字符处理"""
        response = client.post("/api/v1/console/eval/run-suite", json={
            "name": "unicode_test",
            "cases": [
                {"scene": "chat", "query": "你好世界 🌍 مرحبا"}
            ]
        })
        # 应正常处理 Unicode
        assert response.status_code != 500, \
            f"Unicode 不应导致 500！响应: {response.text}"


class TestConsoleAPIConsistency:
    """API 一致性测试"""

    def test_all_endpoints_return_json(self, client):
        """验证所有端点返回 JSON"""
        endpoints = [
            "/api/v1/console/agent-runs",
            "/api/v1/console/agent-runs/stats",
            "/api/v1/console/tools",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, \
                f"{endpoint} 应返回 JSON，实际 Content-Type: {content_type}"

    def test_error_responses_have_detail(self, client):
        """验证错误响应包含 detail 字段"""
        # 触发 401 错误
        response = client.get("/api/v1/console/agent-runs")
        
        if response.status_code == 401:
            data = response.json()
            assert "detail" in data, \
                "401 响应应包含 detail 字段"
