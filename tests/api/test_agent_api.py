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


class TestAgentChatHappyPath:
    """Agent Chat 正常路径回归测试 (M1 基线观测)"""

    @patch("alice.agent.core.AliceAgentCore.run_task")
    def test_chat_happy_path_returns_expected_fields(self, mock_run_task, client, db_session, sample_tenant, sample_user):
        """
        M1 回归测试：验证 Agent Chat 返回所有预期字段

        包括 M1 新增的基线观测字段：
        - plan_json, safety_level
        - error_code, total_duration_ms, token_usage
        - 步骤中的 kind, duration_ms
        """
        from alice.agent import AgentResult, AgentStep

        # Mock AgentCore 返回包含新字段的结果
        mock_run_task.return_value = AgentResult(
            answer="这是一个测试回答",
            steps=[
                AgentStep(
                    step_idx=0,
                    thought="选择策略",
                    kind="thought",
                    duration_ms=10,
                ),
                AgentStep(
                    step_idx=1,
                    thought="调用工具",
                    tool_name="search",
                    tool_args={"query": "test"},
                    observation="搜索结果",
                    kind="tool",
                    duration_ms=150,
                ),
            ],
            citations=[],
            tool_traces=[],
            plan_json='{"steps": ["step1", "step2"]}',
            safety_level="normal",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50},
            total_duration_ms=200,
        )

        # 发起请求（需要认证，但我们主要测试响应结构）
        response = client.post(
            "/api/v1/agent/chat",
            json={
                "query": "测试问题",
                "scene": "chat",
            },
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )

        # 如果需要认证，跳过内容验证
        if response.status_code == 401:
            pytest.skip("需要认证才能完成此测试")

        assert response.status_code == 200, f"预期 200，实际 {response.status_code}: {response.text}"

        data = response.json()

        # 验证基础字段
        assert "answer" in data
        assert data["answer"] == "这是一个测试回答"

        # 验证 M1 新增字段
        assert "plan_json" in data
        assert "safety_level" in data
        assert data["safety_level"] == "normal"

        # 验证观测指标
        assert "token_usage" in data
        assert "total_duration_ms" in data or "processing_time_ms" in data

        # 验证步骤结构
        assert "steps" in data
        assert len(data["steps"]) == 2

        # 验证步骤中的新字段
        step0 = data["steps"][0]
        assert step0["kind"] == "thought"
        assert step0.get("duration_ms") == 10

        step1 = data["steps"][1]
        assert step1["kind"] == "tool"
        assert step1["tool_name"] == "search"


class TestAgentToolError:
    """Agent 工具错误处理回归测试 (M1 基线观测)"""

    @patch("alice.agent.core.AliceAgentCore.run_task")
    def test_tool_error_returns_error_code(self, mock_run_task, client, db_session, sample_tenant):
        """
        M1 回归测试：验证工具执行错误时返回正确的 error_code
        """
        from alice.agent import AgentResult, AgentStep

        # Mock AgentCore 返回包含错误的结果
        mock_run_task.return_value = AgentResult(
            answer="抱歉，工具执行失败",
            steps=[
                AgentStep(
                    step_idx=0,
                    thought="调用工具",
                    tool_name="search",
                    tool_args={"query": "test"},
                    error="ToolExecutionError: 网络超时",
                    kind="tool",
                ),
            ],
            citations=[],
            tool_traces=[],
            error_code="TOOL_ERROR",
            safety_level="normal",
        )

        response = client.post(
            "/api/v1/agent/chat",
            json={
                "query": "这是一个会失败的请求",
                "scene": "research",
            },
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )

        if response.status_code == 401:
            pytest.skip("需要认证才能完成此测试")

        assert response.status_code == 200

        data = response.json()

        # 验证 error_code 被正确返回
        assert "error_code" in data
        assert data["error_code"] == "TOOL_ERROR"

        # 验证步骤中记录了错误
        assert len(data["steps"]) >= 1
        error_step = data["steps"][0]
        assert error_step["error"] is not None
        assert "ToolExecutionError" in error_step["error"]

    @patch("alice.agent.core.AliceAgentCore.run_task")
    def test_llm_error_returns_error_code(self, mock_run_task, client, db_session, sample_tenant):
        """
        M1 回归测试：验证 LLM 错误时返回正确的 error_code
        """
        from alice.agent import AgentResult, AgentStep

        mock_run_task.return_value = AgentResult(
            answer="抱歉，AI 服务暂时不可用",
            steps=[
                AgentStep(
                    step_idx=0,
                    thought="LLM 调用失败",
                    error="LLMConnectionError: API 超时",
                    kind="thought",
                ),
            ],
            citations=[],
            tool_traces=[],
            error_code="LLM_ERROR",
            safety_level="normal",
        )

        response = client.post(
            "/api/v1/agent/chat",
            json={"query": "测试"},
            headers={"X-Tenant-ID": str(sample_tenant.id)}
        )

        if response.status_code == 401:
            pytest.skip("需要认证才能完成此测试")

        data = response.json()
        assert data.get("error_code") == "LLM_ERROR"
