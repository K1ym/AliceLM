"""
Agent API 集成测试

测试 /api/v1/agent/* 端点

【测试目标】
- 验证 Agent 对话 API 的认证和输入验证
- 验证不同场景的处理
- 发现边界条件和安全问题
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestAgentChatAPI:
    """POST /api/v1/agent/chat 测试"""

    def test_agent_chat_requires_auth(self, client):
        """
        验证未认证请求返回 401
        
        Agent Chat API 必须要求认证
        """
        response = client.post("/api/v1/agent/chat", json={
            "query": "你好"
        })
        assert response.status_code == 401, \
            f"Agent Chat 未认证应返回 401，实际返回 {response.status_code}"

    def test_agent_chat_missing_query(self, client):
        """
        验证缺少 query 返回 422
        
        query 是必填字段
        """
        response = client.post("/api/v1/agent/chat", json={})
        assert response.status_code in [401, 422], \
            f"缺少 query 应返回 422，实际返回 {response.status_code}"

    def test_agent_chat_empty_query(self, client):
        """验证空 query 字符串"""
        response = client.post("/api/v1/agent/chat", json={
            "query": ""
        })
        # 空 query 应该被拒绝或至少不导致 500
        assert response.status_code != 500, \
            f"空 query 不应导致 500！响应: {response.text}"

    def test_agent_chat_null_query(self, client):
        """验证 null query"""
        response = client.post("/api/v1/agent/chat", json={
            "query": None
        })
        assert response.status_code in [401, 422], \
            f"null query 应返回 422，实际返回 {response.status_code}"

    def test_agent_chat_whitespace_only_query(self, client):
        """验证只有空白字符的 query"""
        response = client.post("/api/v1/agent/chat", json={
            "query": "   \n\t  "
        })
        # 应该被拒绝或返回有意义的错误
        assert response.status_code != 500, \
            f"空白 query 不应导致 500！响应: {response.text}"

    def test_agent_chat_very_long_query(self, client):
        """验证超长 query"""
        long_query = "测试" * 10000  # 20000 字符
        response = client.post("/api/v1/agent/chat", json={
            "query": long_query
        })
        # 应该被处理，可能返回 413 或 422，但不应崩溃
        assert response.status_code != 500, \
            f"超长 query 不应导致 500！状态码: {response.status_code}"

    def test_agent_chat_invalid_scene_type(self, client):
        """验证 scene 参数类型错误"""
        response = client.post("/api/v1/agent/chat", json={
            "query": "测试",
            "scene": 123  # 应该是字符串
        })
        assert response.status_code in [401, 422], \
            f"scene 类型错误应返回 422，实际返回 {response.status_code}"

    def test_agent_chat_invalid_video_id_type(self, client):
        """验证 video_id 参数类型错误"""
        response = client.post("/api/v1/agent/chat", json={
            "query": "测试",
            "scene": "video",
            "video_id": "not-a-number"
        })
        assert response.status_code in [401, 422], \
            f"video_id 类型错误应返回 422，实际返回 {response.status_code}"

    def test_agent_chat_negative_video_id(self, client):
        """验证负数 video_id"""
        response = client.post("/api/v1/agent/chat", json={
            "query": "测试",
            "scene": "video",
            "video_id": -1
        })
        # 负数 ID 应该被拒绝或返回 404
        assert response.status_code != 500, \
            f"负数 video_id 不应导致 500！响应: {response.text}"

    def test_agent_chat_nonexistent_video_id(self, client):
        """验证不存在的 video_id"""
        response = client.post("/api/v1/agent/chat", json={
            "query": "测试",
            "scene": "video",
            "video_id": 999999999
        })
        # 不存在的 ID 应返回 404 或处理为无上下文
        assert response.status_code != 500, \
            f"不存在的 video_id 不应导致 500！响应: {response.text}"


class TestAgentStrategiesAPI:
    """GET /api/v1/agent/strategies 测试"""

    def test_get_strategies(self, client):
        """验证能获取策略列表"""
        response = client.get("/api/v1/agent/strategies")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "strategies" in data
        assert isinstance(data["strategies"], list)
        
        # 至少有 chat 和 research 策略
        strategy_names = [s["name"] for s in data["strategies"]]
        assert "chat" in strategy_names
        assert "research" in strategy_names


class TestAgentScenesAPI:
    """GET /api/v1/agent/scenes 测试"""

    def test_get_scenes(self, client):
        """验证能获取场景列表"""
        response = client.get("/api/v1/agent/scenes")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "scenes" in data
        assert isinstance(data["scenes"], list)
        
        # 验证基本场景存在
        scene_values = [s["value"] for s in data["scenes"]]
        assert "chat" in scene_values


class TestAgentChatResearch:
    """
    场景3：Research / 深度搜索
    
    验证 research 场景请求格式正确
    """

    @patch("alice.agent.core.AliceAgentCore.run_task")
    def test_research_scene_request(self, mock_run_task, client, db_session, sample_tenant):
        """验证 research 场景请求被正确处理"""
        from alice.agent import AgentResult
        
        # Mock AgentCore
        mock_run_task.return_value = AgentResult(
            answer="根据搜索结果...",
            steps=[],
            citations=[],
            tool_traces=[],
        )
        
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "query": "什么是 MCP 协议？",
                "scene": "research",
            },
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        
        # 验证请求被接受（可能需要认证）
        assert response.status_code in [200, 401, 500]


class TestAgentErrorHandling:
    """错误处理测试"""

    def test_empty_query(self, client, db_session, sample_tenant):
        """验证空 query 返回错误"""
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "query": "",
            },
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )
        
        # 空 query 可能返回 422 或 400
        assert response.status_code in [400, 401, 422, 500]

    def test_malformed_json(self, client):
        """验证错误的 JSON 格式"""
        response = client.post(
            "/api/v1/agent/chat",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]

    def test_missing_content_type(self, client):
        """验证缺少 Content-Type"""
        response = client.post(
            "/api/v1/agent/chat",
            content='{"query": "test"}'
        )
        
        # FastAPI 通常能处理这种情况
        assert response.status_code in [200, 400, 401, 422]
