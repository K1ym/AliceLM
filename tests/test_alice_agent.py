"""
Stage S0: Alice Agent 模块测试
"""

import pytest


class TestAliceAgentStructure:
    """S0: 代码结构对齐测试"""

    def test_agent_types_import(self):
        """验证 agent types 可导入"""
        from alice.agent import (
            Scene,
            AgentTask,
            AgentResult,
            AgentStep,
            AgentPlan,
            AgentCitation,
        )
        
        # 验证 Scene 枚举
        assert Scene.CHAT.value == "chat"
        assert Scene.RESEARCH.value == "research"
        assert Scene.TIMELINE.value == "timeline"

    def test_agent_core_import(self):
        """验证 AliceAgentCore 可导入"""
        from alice.agent import AliceAgentCore
        
        # AliceAgentCore 需要 db session (S2 改动)
        assert AliceAgentCore is not None

    def test_strategy_import(self):
        """验证 Strategy 相关类可导入"""
        from alice.agent import (
            Strategy,
            StrategySelector,
            ChatStrategy,
            ResearchStrategy,
            TimelineStrategy,
        )
        
        selector = StrategySelector()
        assert selector is not None
        
        # 验证策略可实例化
        chat = ChatStrategy()
        assert chat.name == "chat"
        assert "ask_video" in chat.allowed_tools

    def test_task_planner_import(self):
        """验证 TaskPlanner 可导入"""
        from alice.agent import TaskPlanner
        
        planner = TaskPlanner()
        assert planner is not None

    def test_tool_executor_import(self):
        """验证 ToolExecutor 可导入"""
        from alice.agent import ToolExecutor
        
        executor = ToolExecutor()
        assert executor is not None

    def test_tool_router_import(self):
        """验证 ToolRouter 可导入"""
        from alice.agent import ToolRouter, AliceTool
        
        router = ToolRouter()
        assert router is not None
        
        # 验证空路由返回空列表
        schemas = router.list_tool_schemas()
        assert schemas == []


class TestAliceSearchStructure:
    """S0: SearchAgent 结构测试"""

    def test_search_agent_import(self):
        """验证 SearchAgentService 可导入"""
        from alice.search import SearchAgentService, SearchAgentResult, SearchSource
        
        service = SearchAgentService()
        assert service is not None


class TestAgentTask:
    """AgentTask 数据类测试"""

    def test_agent_task_creation(self):
        """验证 AgentTask 可创建"""
        from alice.agent import AgentTask, Scene
        
        task = AgentTask(
            tenant_id="test-tenant",
            scene=Scene.CHAT,
            query="这个视频讲了什么？",
            user_id="user-1",
            video_id=123,
        )
        
        assert task.tenant_id == "test-tenant"
        assert task.scene == Scene.CHAT
        assert task.query == "这个视频讲了什么？"
        assert task.video_id == 123

    def test_agent_result_creation(self):
        """验证 AgentResult 可创建"""
        from alice.agent import AgentResult, AgentCitation
        
        result = AgentResult(
            answer="这个视频讲的是...",
            citations=[
                AgentCitation(
                    type="video",
                    id="123",
                    title="测试视频",
                    snippet="视频片段...",
                )
            ],
        )
        
        assert result.answer == "这个视频讲的是..."
        assert len(result.citations) == 1
        assert result.citations[0].type == "video"


class TestStrategySelector:
    """StrategySelector 测试"""

    def test_select_chat_strategy(self):
        """验证 chat 场景选择 ChatStrategy"""
        from alice.agent import AgentTask, Scene, StrategySelector, ChatStrategy
        
        selector = StrategySelector()
        task = AgentTask(tenant_id="t1", scene=Scene.CHAT, query="test")
        
        strategy = selector.select(task)
        assert isinstance(strategy, ChatStrategy)
        assert strategy.name == "chat"

    def test_select_research_strategy(self):
        """验证 research 场景选择 ResearchStrategy"""
        from alice.agent import AgentTask, Scene, StrategySelector, ResearchStrategy
        
        selector = StrategySelector()
        task = AgentTask(tenant_id="t1", scene=Scene.RESEARCH, query="test")
        
        strategy = selector.select(task)
        assert isinstance(strategy, ResearchStrategy)
        assert "deep_web_research" in strategy.allowed_tools


# ============== Stage S2 Tests ==============

class TestAliceAgentCoreS2:
    """S2: AliceAgentCore 骨架测试"""

    def test_run_agent_task_import(self):
        """验证 run_agent_task 便捷函数可导入"""
        from alice.agent import run_agent_task
        assert run_agent_task is not None

    def test_agent_core_requires_db(self):
        """验证 AliceAgentCore 需要 db session"""
        from alice.agent import AliceAgentCore
        
        # 不传 db 会报错
        try:
            core = AliceAgentCore()
            assert False, "Should require db"
        except TypeError:
            pass  # Expected


class TestAgentAPIRoutes:
    """S2: Agent API 路由测试"""

    def test_agent_router_import(self):
        """验证 agent router 可导入"""
        from apps.api.routers.agent import router
        assert router is not None

    def test_agent_chat_request_schema(self):
        """验证 AgentChatRequest schema"""
        from apps.api.routers.agent import AgentChatRequest
        
        req = AgentChatRequest(query="测试问题")
        assert req.query == "测试问题"
        assert req.scene == "chat"  # 默认值
        
        req2 = AgentChatRequest(
            query="研究问题",
            scene="research",
            video_id=123,
        )
        assert req2.scene == "research"
        assert req2.video_id == 123

    def test_agent_chat_response_schema(self):
        """验证 AgentChatResponse schema"""
        from apps.api.routers.agent import AgentChatResponse
        
        resp = AgentChatResponse(
            answer="这是回答",
            citations=[],
            steps=[],
            strategy="chat",
            processing_time_ms=100,
        )
        assert resp.answer == "这是回答"
        assert resp.strategy == "chat"

    def test_agent_routes_registered(self):
        """验证 Agent 路由已注册到 app"""
        from apps.api.main import app
        
        paths = [r.path for r in app.routes]
        assert "/api/v1/agent/chat" in paths
        assert "/api/v1/agent/strategies" in paths
        assert "/api/v1/agent/scenes" in paths


# ============== Stage S3 Tests ==============

class TestToolRouter:
    """S3: ToolRouter 测试"""

    def test_tool_router_create_with_basic_tools(self):
        """验证 ToolRouter 可创建并注册基础工具"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_basic_tools()
        tools = router.list_tools()
        
        assert len(tools) >= 6
        assert "echo" in tools
        assert "current_time" in tools
        assert "sleep" in tools
        assert "get_timeline_summary" in tools
        assert "get_video_summary" in tools
        assert "search_videos" in tools

    def test_tool_router_list_schemas(self):
        """验证 ToolRouter 可获取工具 schema"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_basic_tools()
        schemas = router.list_tool_schemas()
        
        assert len(schemas) >= 6
        
        # 验证 schema 格式
        for s in schemas:
            assert s["type"] == "function"
            assert "function" in s
            assert "name" in s["function"]
            assert "description" in s["function"]
            assert "parameters" in s["function"]

    def test_tool_router_filter_tools(self):
        """验证 ToolRouter 可按允许列表过滤工具"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_basic_tools()
        schemas = router.list_tool_schemas(allowed_tools=["echo", "current_time"])
        
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "echo" in names
        assert "current_time" in names


class TestBasicTools:
    """S3: 基础工具测试"""

    def test_echo_tool(self):
        """验证 Echo 工具"""
        import asyncio
        from alice.agent.tools import EchoTool
        
        tool = EchoTool()
        result = asyncio.run(tool.run({"message": "Hello!"}))
        assert "[Echo] Hello!" == result

    def test_current_time_tool(self):
        """验证 CurrentTime 工具"""
        import asyncio
        from alice.agent.tools import CurrentTimeTool
        
        tool = CurrentTimeTool()
        
        # 测试 human 格式
        result = asyncio.run(tool.run({"format": "human"}))
        assert "年" in result and "月" in result
        
        # 测试 iso 格式
        result = asyncio.run(tool.run({"format": "iso"}))
        assert "T" in result

    def test_get_timeline_summary_tool_mock(self):
        """验证 GetTimelineSummary 工具（模拟模式）"""
        import asyncio
        from alice.agent.tools import GetTimelineSummaryTool
        
        tool = GetTimelineSummaryTool(db=None)
        result = asyncio.run(tool.run({"days": 7}))
        assert "模拟" in result or "天" in result

    def test_get_video_summary_tool_mock(self):
        """验证 GetVideoSummary 工具（模拟模式）"""
        import asyncio
        from alice.agent.tools import GetVideoSummaryTool
        
        tool = GetVideoSummaryTool(db=None)
        result = asyncio.run(tool.run({"video_id": 123}))
        assert "模拟" in result or "视频" in result


class TestToolExecution:
    """S3: 工具执行测试"""

    def test_execute_tool(self):
        """验证 ToolRouter.execute"""
        import asyncio
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_basic_tools()
        result = asyncio.run(router.execute("echo", {"message": "test"}))
        assert result == "[Echo] test"

    def test_execute_safe_success(self):
        """验证 ToolRouter.execute_safe 成功"""
        import asyncio
        from alice.agent import ToolRouter, ToolResult
        
        router = ToolRouter.create_with_basic_tools()
        result = asyncio.run(router.execute_safe("echo", {"message": "safe"}))
        
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.output == "[Echo] safe"

    def test_execute_safe_unknown_tool(self):
        """验证 ToolRouter.execute_safe 处理未知工具"""
        import asyncio
        from alice.agent import ToolRouter, ToolResult
        
        router = ToolRouter.create_with_basic_tools()
        result = asyncio.run(router.execute_safe("unknown_tool", {}))
        
        assert isinstance(result, ToolResult)
        assert result.success is False
        assert "Unknown tool" in result.error


# ============== Stage S4 Tests ==============

class TestTaskPlannerS4:
    """S4: TaskPlanner 测试"""

    def test_plan_step_state_enum(self):
        """验证 PlanStepState 枚举"""
        from alice.agent import PlanStepState
        
        assert PlanStepState.NOT_STARTED.value == "not_started"
        assert PlanStepState.IN_PROGRESS.value == "in_progress"
        assert PlanStepState.COMPLETED.value == "completed"
        assert PlanStepState.BLOCKED.value == "blocked"
        
        # 验证 get_active_states
        active = PlanStepState.get_active_states()
        assert "not_started" in active
        assert "in_progress" in active
        assert "completed" not in active

    def test_task_planner_simple_query(self):
        """验证 TaskPlanner 简单查询检测"""
        import asyncio
        from alice.agent import TaskPlanner, AgentTask, Scene
        
        planner = TaskPlanner(use_llm_planning=False)
        task = AgentTask(tenant_id="t1", scene=Scene.CHAT, query="你好")
        
        plan = asyncio.run(planner.plan(task))
        
        assert len(plan.steps) == 1
        assert "直接回答" in plan.steps[0]

    def test_task_planner_store_plan(self):
        """验证 TaskPlanner 计划存储"""
        from alice.agent import TaskPlanner
        
        planner = TaskPlanner(use_llm_planning=False)
        planner._store_plan("plan_123", "测试计划", ["步骤1", "步骤2"])
        
        assert "plan_123" in planner.plans
        assert planner.plans["plan_123"]["title"] == "测试计划"
        assert len(planner.plans["plan_123"]["steps"]) == 2

    def test_task_planner_mark_step(self):
        """验证 TaskPlanner 步骤状态标记"""
        from alice.agent import TaskPlanner, PlanStepState
        
        planner = TaskPlanner(use_llm_planning=False)
        planner._store_plan("plan_456", "测试", ["步骤1", "步骤2"])
        
        planner.mark_step("plan_456", 0, PlanStepState.COMPLETED.value)
        
        assert planner.plans["plan_456"]["step_statuses"][0] == "completed"

    def test_task_planner_get_plan_text(self):
        """验证 TaskPlanner 计划文本生成"""
        from alice.agent import TaskPlanner, PlanStepState
        
        planner = TaskPlanner(use_llm_planning=False)
        planner._store_plan("plan_789", "测试计划", ["步骤1", "步骤2"])
        planner.mark_step("plan_789", 0, PlanStepState.COMPLETED.value)
        
        text = planner.get_plan_text("plan_789")
        
        assert "测试计划" in text
        assert "[✓]" in text  # 已完成步骤
        assert "[ ]" in text  # 未开始步骤


class TestToolExecutorS4:
    """S4: ToolExecutor 测试"""

    def test_agent_run_state_enum(self):
        """验证 AgentRunState 枚举"""
        from alice.agent import AgentRunState
        
        assert AgentRunState.IDLE.value == "idle"
        assert AgentRunState.RUNNING.value == "running"
        assert AgentRunState.FINISHED.value == "finished"
        assert AgentRunState.ERROR.value == "error"

    def test_tool_executor_init(self):
        """验证 ToolExecutor 初始化"""
        from alice.agent import ToolExecutor, ToolRouter, AgentRunState
        
        router = ToolRouter.create_with_basic_tools()
        executor = ToolExecutor(tool_router=router, max_steps=5, max_observe=1000)
        
        assert executor.max_steps == 5
        assert executor.max_observe == 1000
        assert executor.state == AgentRunState.IDLE
        assert executor.tool_router is not None

    def test_tool_executor_terminal_tools(self):
        """验证 ToolExecutor 终止工具检测"""
        from alice.agent import ToolExecutor
        
        executor = ToolExecutor()
        
        assert executor._is_terminal_tool("terminate")
        assert executor._is_terminal_tool("finish")
        assert executor._is_terminal_tool("final_answer")
        assert not executor._is_terminal_tool("echo")

    def test_tool_executor_parse_response(self):
        """验证 ToolExecutor 响应解析"""
        from alice.agent import ToolExecutor
        
        executor = ToolExecutor()
        
        # JSON 格式
        result = executor._parse_response('{"thought": "test", "action": "echo"}')
        assert result["thought"] == "test"
        assert result["action"] == "echo"
        
        # 带 markdown 格式
        result = executor._parse_response('```json\n{"thought": "md", "final_answer": "done"}\n```')
        assert result["thought"] == "md"
        assert result["final_answer"] == "done"

    def test_tool_executor_format_tools(self):
        """验证 ToolExecutor 工具格式化"""
        from alice.agent import ToolExecutor, ToolRouter
        
        router = ToolRouter.create_with_basic_tools()
        executor = ToolExecutor(tool_router=router)
        
        schemas = router.list_tool_schemas(["echo", "current_time"])
        text = executor._format_tools_for_prompt(schemas)
        
        assert "echo" in text
        assert "current_time" in text


# ============== Stage S5 Tests ==============

class TestAliceSearchStructure:
    """S0: SearchAgent 结构测试"""

    def test_search_agent_import(self):
        """验证 SearchAgentService 可导入"""
        from alice.search import SearchAgentService, SearchAgentResult, SearchSource
        
        assert SearchAgentService is not None
        assert SearchAgentResult is not None
        assert SearchSource is not None

    def test_search_source_dataclass(self):
        """验证 SearchSource 数据结构"""
        from alice.search import SearchSource
        
        source = SearchSource(
            url="https://example.com",
            title="Test Title",
            snippet="Test snippet",
            score=0.9,
        )
        
        assert source.url == "https://example.com"
        assert source.title == "Test Title"
        assert source.score == 0.9

    def test_search_agent_result_dataclass(self):
        """验证 SearchAgentResult 数据结构"""
        from alice.search import SearchAgentResult, SearchSource
        
        result = SearchAgentResult(
            query="test query",
            sub_queries=["sub1", "sub2"],
            sources=[SearchSource(url="https://example.com")],
            answer="Test answer",
        )
        
        assert result.query == "test query"
        assert len(result.sub_queries) == 2
        assert len(result.sources) == 1
        assert result.answer == "Test answer"

    def test_search_agent_run(self):
        """验证 SearchAgentService.run 基本流程"""
        import asyncio
        from alice.search import SearchAgentService, MockSearchProvider
        
        service = SearchAgentService(search_provider=MockSearchProvider())
        result = asyncio.run(service.run("test query"))
        
        assert result.query == "test query"
        assert len(result.sources) > 0
        assert result.answer is not None

    def test_mock_search_provider(self):
        """验证 MockSearchProvider"""
        import asyncio
        from alice.search import MockSearchProvider
        
        provider = MockSearchProvider()
        results = asyncio.run(provider.search("test", top_k=3))
        
        assert len(results) == 3
        assert results[0].url.startswith("https://")


class TestDeepWebResearchToolS5:
    """S5: DeepWebResearchTool 测试"""

    def test_deep_web_research_tool_import(self):
        """验证 DeepWebResearchTool 导入"""
        from alice.agent.tools import DeepWebResearchTool
        
        tool = DeepWebResearchTool()
        assert tool.name == "deep_web_research"
        assert "query" in tool.parameters["properties"]

    def test_tool_router_with_search_tools(self):
        """验证 ToolRouter 包含搜索工具"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_all_tools()
        tools = router.list_tools()
        
        assert "deep_web_research" in tools

    def test_research_strategy_has_deep_web_research(self):
        """验证 ResearchStrategy 包含 deep_web_research"""
        from alice.agent import ResearchStrategy
        
        strategy = ResearchStrategy()
        assert "deep_web_research" in strategy.allowed_tools

    def test_deep_web_research_tool_run(self):
        """验证 DeepWebResearchTool.run"""
        import asyncio
        from alice.agent.tools import DeepWebResearchTool
        from alice.search import SearchAgentService, MockSearchProvider
        
        search_agent = SearchAgentService(search_provider=MockSearchProvider())
        tool = DeepWebResearchTool(search_agent=search_agent)
        
        result = asyncio.run(tool.run({"query": "test query"}))
        
        assert "query" in result
        assert "sources" in result
        assert "answer" in result


# ============== Stage S6 Tests ==============

class TestExtToolsS6:
    """S6: 扩展工具库测试"""

    def test_ext_tools_import(self):
        """验证扩展工具模块导入"""
        from alice.agent.tools.ext import (
            CalculatorTool,
            CurrentTimeTool,
            FileReadTool,
            HttpRequestTool,
            RssTool,
        )
        
        assert CalculatorTool is not None
        assert CurrentTimeTool is not None
        assert FileReadTool is not None
        assert HttpRequestTool is not None
        assert RssTool is not None

    def test_calculator_tool(self):
        """验证 CalculatorTool"""
        import asyncio
        from alice.agent.tools.ext import CalculatorTool
        
        tool = CalculatorTool()
        assert tool.name == "calculator"
        
        result = asyncio.run(tool.run({"expression": "2 + 3 * 4"}))
        assert result["result"] == 14
        
        result = asyncio.run(tool.run({"expression": "(10 - 5) ** 2"}))
        assert result["result"] == 25

    def test_current_time_ext_tool(self):
        """验证扩展版 CurrentTimeTool"""
        import asyncio
        from alice.agent.tools.ext import CurrentTimeTool
        
        tool = CurrentTimeTool()
        result = asyncio.run(tool.run({"timezone": "UTC"}))
        
        assert "iso" in result
        assert "formatted" in result
        assert "UTC" in result["iso"] or "+00:00" in result["iso"]

    def test_sleep_tool(self):
        """验证 SleepTool"""
        import asyncio
        from alice.agent.tools.ext import SleepTool
        
        tool = SleepTool()
        result = asyncio.run(tool.run({"seconds": 0.1}))
        
        assert "started_at" in result
        assert "ended_at" in result
        assert result["slept_seconds"] == 0.1

    def test_environment_tool(self):
        """验证 EnvironmentTool"""
        import asyncio
        import os
        from alice.agent.tools.ext import EnvironmentTool
        
        os.environ["ALICE_TEST_VAR"] = "test_value"
        
        tool = EnvironmentTool()
        result = asyncio.run(tool.run({"action": "get", "name": "ALICE_TEST_VAR"}))
        
        assert result["value"] == "test_value"
        
        del os.environ["ALICE_TEST_VAR"]

    def test_journal_tool(self):
        """验证 JournalTool"""
        import asyncio
        from alice.agent.tools.ext import JournalTool
        
        tool = JournalTool()
        
        # 写入
        result = asyncio.run(tool.run({"action": "write", "content": "test entry"}))
        assert result["success"] is True
        
        # 读取
        result = asyncio.run(tool.run({"action": "read", "limit": 5}))
        assert len(result["entries"]) > 0
        
        # 清空
        asyncio.run(tool.run({"action": "clear"}))

    def test_file_read_tool_security(self):
        """验证 FileReadTool 安全限制"""
        import asyncio
        from alice.agent.tools.ext import FileReadTool
        
        tool = FileReadTool()
        
        # 尝试读取不安全路径
        result = asyncio.run(tool.run({"path": "/etc/passwd"}))
        assert "error" in result
        assert "不允许" in result["error"]

    def test_http_request_tool_security(self):
        """验证 HttpRequestTool 安全限制"""
        import asyncio
        from alice.agent.tools.ext import HttpRequestTool
        
        tool = HttpRequestTool()
        
        # 尝试访问内部地址
        result = asyncio.run(tool.run({"url": "http://localhost:8080"}))
        assert "error" in result

    def test_tool_router_with_ext_tools(self):
        """验证 ToolRouter 包含扩展工具"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_ext_tools()
        tools = router.list_tools()
        
        # 检查扩展工具已注册
        assert "calculator" in tools
        assert "http_request" in tools
        assert "rss" in tools
        assert "cron" in tools
        assert "file_read" in tools

    def test_unsafe_tools_not_registered_by_default(self):
        """验证高危工具默认不注册"""
        from alice.agent import ToolRouter
        
        router = ToolRouter.create_with_ext_tools()
        tools = router.list_tools()
        
        # 高危工具不应该在默认列表中
        assert "shell" not in tools
        assert "python_repl" not in tools
        assert "use_computer" not in tools


# ============== Stage S7 Tests ==============

class TestMcpClientS7:
    """S7: MCP Client 测试"""

    def test_mcp_client_import(self):
        """验证 MCP Client 导入"""
        from alice.agent.mcp_client import (
            McpClient,
            McpRegistry,
            MockMcpClient,
            McpToolDescription,
            McpToolResult,
            McpServerStatus,
        )
        
        assert McpClient is not None
        assert McpRegistry is not None
        assert MockMcpClient is not None

    def test_mock_mcp_client_connect(self):
        """验证 Mock MCP Client 连接"""
        import asyncio
        from alice.agent.mcp_client import MockMcpClient, McpServerStatus
        
        client = MockMcpClient("test_mock")
        result = asyncio.run(client.connect())
        
        assert result is True
        assert client.status == McpServerStatus.CONNECTED

    def test_mock_mcp_client_list_tools(self):
        """验证 Mock MCP Client 工具列表"""
        import asyncio
        from alice.agent.mcp_client import MockMcpClient
        
        client = MockMcpClient("test_mock")
        asyncio.run(client.connect())
        
        tools = asyncio.run(client.list_tools())
        
        assert len(tools) == 2
        tool_names = [t["name"] for t in tools]
        assert "mock_echo" in tool_names
        assert "mock_add" in tool_names

    def test_mock_mcp_client_call_tool(self):
        """验证 Mock MCP Client 工具调用"""
        import asyncio
        from alice.agent.mcp_client import MockMcpClient
        
        client = MockMcpClient("test_mock")
        asyncio.run(client.connect())
        
        # 测试 echo
        result = asyncio.run(client.call_tool("mock_echo", {"message": "hello"}))
        assert result.success is True
        assert "hello" in result.content
        
        # 测试 add
        result = asyncio.run(client.call_tool("mock_add", {"a": 3, "b": 5}))
        assert result.success is True
        assert result.content["result"] == 8

    def test_mcp_registry(self):
        """验证 MCP Registry"""
        from alice.agent.mcp_client import McpRegistry, McpEndpointConfig
        
        registry = McpRegistry([
            McpEndpointConfig(name="test1", endpoint="http://localhost:3001"),
            McpEndpointConfig(name="test2", endpoint="http://localhost:3002"),
        ])
        
        endpoints = registry.list_endpoints()
        assert "test1" in endpoints
        assert "test2" in endpoints
        
        client = registry.get_client("test1")
        assert client is not None


class TestMcpBackedToolS7:
    """S7: MCP Backed Tool 测试"""

    def test_mcp_backed_tool_import(self):
        """验证 McpBackedTool 导入"""
        from alice.agent.tool_router import McpBackedTool
        
        assert McpBackedTool is not None

    def test_tool_router_with_mock_mcp(self):
        """验证 ToolRouter 包含 Mock MCP 工具"""
        import asyncio
        from alice.agent import ToolRouter
        
        router = asyncio.run(ToolRouter.create_with_mcp(use_mock=True))
        tools = router.list_tools()
        
        # 检查 MCP 工具已注册
        assert "mock_echo" in tools
        assert "mock_add" in tools

    def test_tool_router_execute_mcp_tool(self):
        """验证 ToolRouter 执行 MCP 工具"""
        import asyncio
        from alice.agent import ToolRouter
        
        router = asyncio.run(ToolRouter.create_with_mcp(use_mock=True))
        
        # 执行 MCP 工具
        result = asyncio.run(router.execute("mock_echo", {"message": "test"}))
        assert "test" in result
        
        result = asyncio.run(router.execute("mock_add", {"a": 10, "b": 20}))
        assert result["result"] == 30

    def test_tool_router_list_schemas_includes_mcp(self):
        """验证 list_tool_schemas 包含 MCP 工具"""
        import asyncio
        from alice.agent import ToolRouter
        
        router = asyncio.run(ToolRouter.create_with_mcp(use_mock=True))
        schemas = router.list_tool_schemas()
        
        schema_names = [s["function"]["name"] for s in schemas]
        assert "mock_echo" in schema_names
        assert "mock_add" in schema_names

    def test_mcp_tool_no_conflict_with_local(self):
        """验证 MCP 工具不与本地工具冲突"""
        import asyncio
        from alice.agent import ToolRouter
        
        router = asyncio.run(ToolRouter.create_with_mcp(use_mock=True))
        tools = router.list_tools()
        
        # 本地工具和 MCP 工具都存在
        assert "echo" in tools  # 本地工具
        assert "mock_echo" in tools  # MCP 工具


# ============== Stage S8 Tests ==============

class TestUnifiedEntrypointsS8:
    """S8: 统一入口测试"""

    def test_entrypoints_import(self):
        """验证统一入口模块导入"""
        from alice.one import (
            handle_chat_request,
            handle_qa_request,
            handle_video_chat_request,
            handle_console_request,
        )
        
        assert handle_chat_request is not None
        assert handle_qa_request is not None
        assert handle_video_chat_request is not None
        assert handle_console_request is not None


class TestEvalModuleS8:
    """S8: Eval 模块测试"""

    def test_eval_import(self):
        """验证 Eval 模块导入"""
        from alice.eval import (
            EvalCase,
            EvalSuite,
            EvalResult,
            EvalRunner,
            SimpleScorer,
        )
        
        assert EvalCase is not None
        assert EvalSuite is not None
        assert EvalResult is not None
        assert EvalRunner is not None
        assert SimpleScorer is not None

    def test_eval_case_creation(self):
        """验证 EvalCase 创建"""
        from alice.eval import EvalCase
        
        case = EvalCase(
            scene="chat",
            query="测试问题",
            expected_keywords=["关键词1", "关键词2"],
        )
        
        assert case.scene == "chat"
        assert case.query == "测试问题"
        assert len(case.expected_keywords) == 2

    def test_eval_suite_from_dict(self):
        """验证 EvalSuite.from_dict_list"""
        from alice.eval import EvalSuite
        
        cases_data = [
            {"scene": "chat", "query": "问题1"},
            {"scene": "research", "query": "问题2", "expected_keywords": ["key1"]},
        ]
        
        suite = EvalSuite.from_dict_list("test_suite", cases_data)
        
        assert suite.name == "test_suite"
        assert len(suite.cases) == 2
        assert suite.cases[0].scene == "chat"
        assert suite.cases[1].expected_keywords == ["key1"]

    def test_default_eval_suite(self):
        """验证默认测试套件"""
        from alice.eval.runner import get_default_suite
        
        suite = get_default_suite()
        
        assert suite.name == "default"
        assert len(suite.cases) >= 3


class TestPermissionsS8:
    """S8: 权限模块测试"""

    def test_permissions_import(self):
        """验证权限模块导入"""
        from alice.agent import (
            ToolVisibilityPolicy,
            UserRole,
            get_allowed_tools_for_context,
        )
        
        assert ToolVisibilityPolicy is not None
        assert UserRole is not None
        assert get_allowed_tools_for_context is not None

    def test_normal_user_cannot_access_unsafe(self):
        """验证普通用户无法访问高危工具"""
        from alice.agent import ToolVisibilityPolicy
        
        policy = ToolVisibilityPolicy(user_role="normal", scene="chat")
        
        assert policy.is_tool_allowed("echo") is True
        assert policy.is_tool_allowed("calculator") is True
        assert policy.is_tool_allowed("shell") is False
        assert policy.is_tool_allowed("python_repl") is False

    def test_admin_can_access_unsafe_when_enabled(self):
        """验证管理员启用后可访问高危工具"""
        from alice.agent import ToolVisibilityPolicy
        
        policy = ToolVisibilityPolicy(
            user_role="admin",
            scene="console",
            enable_unsafe=True,
        )
        
        assert policy.is_tool_allowed("shell") is True
        assert policy.is_tool_allowed("python_repl") is True

    def test_scene_restricts_tools(self):
        """验证场景限制工具"""
        from alice.agent import ToolVisibilityPolicy
        
        # chat 场景不允许 web 工具
        chat_policy = ToolVisibilityPolicy(user_role="normal", scene="chat")
        
        # research 场景允许 web 工具
        research_policy = ToolVisibilityPolicy(user_role="normal", scene="research")
        
        assert research_policy.is_tool_allowed("deep_web_research") is True

    def test_filter_tools(self):
        """验证工具过滤"""
        from alice.agent import ToolVisibilityPolicy
        
        policy = ToolVisibilityPolicy(user_role="normal", scene="chat")
        
        all_tools = ["echo", "calculator", "shell", "python_repl"]
        allowed = policy.filter_tools(all_tools)
        
        assert "echo" in allowed
        assert "calculator" in allowed
        assert "shell" not in allowed
        assert "python_repl" not in allowed


class TestAgentRunLoggerS8:
    """S8: Agent Run Logger 测试"""

    def test_run_logger_import(self):
        """验证 Run Logger 导入"""
        from alice.agent import (
            AgentRunLogger,
            AgentRunLog,
            get_agent_run_logger,
        )
        
        assert AgentRunLogger is not None
        assert AgentRunLog is not None
        assert get_agent_run_logger is not None

    def test_run_logger_stats(self):
        """验证 Run Logger 统计"""
        from alice.agent import AgentRunLogger
        
        logger = AgentRunLogger(storage_path=None)
        stats = logger.get_stats()
        
        assert "total_runs" in stats
        assert "success_rate" in stats
        assert "avg_duration_ms" in stats
        assert "scenes" in stats
