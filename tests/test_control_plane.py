"""
控制平面单元测试
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock


def run_async(coro):
    """辅助函数：在同步测试中运行异步代码"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestModelRegistry:
    """ModelRegistry 测试"""
    
    def test_from_yaml_loads_profiles(self, tmp_path):
        """测试从 YAML 加载 profile"""
        from alice.control_plane import ModelRegistry
        
        # 创建测试 YAML
        yaml_content = """
model_profiles:
  test.chat.main:
    kind: chat
    provider: openai
    model: gpt-4
task_defaults:
  chat: test.chat.main
"""
        yaml_file = tmp_path / "models.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ModelRegistry.from_yaml(str(yaml_file))
        
        assert len(registry.list_profiles()) == 1
        profile = registry.get_profile("test.chat.main")
        assert profile is not None
        assert profile.provider == "openai"
        assert profile.model == "gpt-4"
    
    def test_list_profiles_by_kind(self, tmp_path):
        """测试按类型过滤 profile"""
        from alice.control_plane import ModelRegistry
        
        yaml_content = """
model_profiles:
  test.chat:
    kind: chat
    provider: openai
    model: gpt-4
  test.embed:
    kind: embedding
    provider: openai
    model: text-embedding-3
task_defaults: {}
"""
        yaml_file = tmp_path / "models.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ModelRegistry.from_yaml(str(yaml_file))
        
        chat_profiles = registry.list_profiles(kind="chat")
        assert len(chat_profiles) == 1
        assert "test.chat" in chat_profiles
        
        embed_profiles = registry.list_profiles(kind="embedding")
        assert len(embed_profiles) == 1
        assert "test.embed" in embed_profiles
    
    def test_resolve_for_task_uses_defaults(self, tmp_path):
        """测试解析任务使用默认 profile"""
        from alice.control_plane import ModelRegistry
        
        yaml_content = """
model_profiles:
  test.chat.main:
    kind: chat
    provider: deepseek
    model: deepseek-chat
task_defaults:
  chat: test.chat.main
"""
        yaml_file = tmp_path / "models.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ModelRegistry.from_yaml(str(yaml_file))
        
        async def _test():
            with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key', 'DEEPSEEK_BASE_URL': 'https://api.test.com'}):
                resolved = await registry.resolve_for_task("chat")
            return resolved
        
        resolved = run_async(_test())
        
        assert resolved.provider == "deepseek"
        assert resolved.model == "deepseek-chat"
        assert resolved.kind == "chat"


class TestPromptStore:
    """PromptStore 测试"""
    
    def test_from_yaml_loads_prompts(self, tmp_path):
        """测试从 YAML 加载 prompt"""
        from alice.control_plane import PromptStore
        
        yaml_content = """
prompts:
  alice.system.base: |
    你是 Alice，一个 AI 助手。
  alice.task.summary: |
    请总结以下内容。
"""
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text(yaml_content)
        
        store = PromptStore.from_yaml(str(yaml_file))
        
        keys = store.list_keys()
        assert "alice.system.base" in keys
        assert "alice.task.summary" in keys
    
    def test_get_returns_default_prompt(self, tmp_path):
        """测试获取默认 prompt"""
        from alice.control_plane import PromptStore
        
        yaml_content = """
prompts:
  test.prompt: "Hello {name}!"
"""
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text(yaml_content)
        
        store = PromptStore.from_yaml(str(yaml_file))
        
        async def _test():
            # 无模板变量
            prompt1 = await store.get("test.prompt")
            # 有模板变量
            prompt2 = await store.get("test.prompt", name="Alice")
            return prompt1, prompt2
        
        prompt1, prompt2 = run_async(_test())
        
        assert prompt1 == "Hello {name}!"
        assert prompt2 == "Hello Alice!"
    
    def test_get_returns_empty_for_missing_key(self, tmp_path):
        """测试获取不存在的 key 返回空"""
        from alice.control_plane import PromptStore
        
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text("prompts: {}")
        
        store = PromptStore.from_yaml(str(yaml_file))
        
        prompt = run_async(store.get("non.existent.key"))
        assert prompt == ""
    
    def test_legacy_key_mapping(self, tmp_path):
        """测试老 key 映射到新 key"""
        from alice.control_plane import PromptStore
        
        yaml_content = """
prompts:
  alice.task.chat: "Chat prompt"
  alice.task.summary: "Summary prompt"
  alice.task.tagger: "Tagger prompt"
"""
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text(yaml_content)
        
        store = PromptStore.from_yaml(str(yaml_file))
        
        async def _test():
            # 使用老 key 获取
            chat = await store.get("chat")
            summary = await store.get("summary")
            tagger = await store.get("tagger")
            return chat, summary, tagger
        
        chat, summary, tagger = run_async(_test())
        
        assert chat == "Chat prompt"
        assert summary == "Summary prompt"
        assert tagger == "Tagger prompt"
    
    def test_get_sync_returns_yaml_default(self, tmp_path):
        """测试同步方法返回 YAML 默认值"""
        from alice.control_plane import PromptStore
        
        yaml_content = """
prompts:
  alice.task.chat: "Sync chat prompt"
"""
        yaml_file = tmp_path / "prompts.yaml"
        yaml_file.write_text(yaml_content)
        
        store = PromptStore.from_yaml(str(yaml_file))
        
        # 同步获取
        prompt = store.get_sync("chat")  # 使用老 key
        assert prompt == "Sync chat prompt"
        
        # 新 key 也可以
        prompt2 = store.get_sync("alice.task.chat")
        assert prompt2 == "Sync chat prompt"


class TestToolRegistry:
    """ToolRegistry 测试"""
    
    def test_from_yaml_loads_tools(self, tmp_path):
        """测试从 YAML 加载工具配置"""
        from alice.control_plane import ToolRegistry
        
        yaml_content = """
tools:
  - name: calculator
    impl: some.module.CalculatorTool
    enabled: true
    scenes: ["chat", "research"]
  - name: shell
    impl: some.module.ShellTool
    enabled: false
    unsafe: true
    scenes: ["console"]
scene_defaults:
  chat: ["calculator"]
  console: ["shell"]
"""
        yaml_file = tmp_path / "tools.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ToolRegistry.from_yaml(str(yaml_file))
        
        all_tools = registry.list_tools(enabled_only=False)
        assert len(all_tools) == 2
        
        enabled_tools = registry.list_tools(enabled_only=True)
        assert len(enabled_tools) == 1
        assert enabled_tools[0].name == "calculator"
    
    def test_list_tools_for_scene(self, tmp_path):
        """测试获取场景可用工具"""
        from alice.control_plane import ToolRegistry
        
        yaml_content = """
tools:
  - name: calculator
    impl: test.Calculator
    enabled: true
  - name: web_search
    impl: test.WebSearch
    enabled: true
scene_defaults:
  chat: ["calculator"]
  research: ["calculator", "web_search"]
"""
        yaml_file = tmp_path / "tools.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ToolRegistry.from_yaml(str(yaml_file))
        
        chat_tools = registry.list_tools_for_scene("chat")
        assert chat_tools == ["calculator"]
        
        research_tools = registry.list_tools_for_scene("research")
        assert len(research_tools) == 2
    
    def test_enable_disable_tool(self, tmp_path):
        """测试启用/禁用工具"""
        from alice.control_plane import ToolRegistry
        
        yaml_content = """
tools:
  - name: test_tool
    impl: test.Tool
    enabled: true
scene_defaults: {}
"""
        yaml_file = tmp_path / "tools.yaml"
        yaml_file.write_text(yaml_content)
        
        registry = ToolRegistry.from_yaml(str(yaml_file))
        
        # 初始启用
        config = registry.get_tool_config("test_tool")
        assert config.enabled is True
        
        # 禁用
        registry.disable_tool("test_tool")
        config = registry.get_tool_config("test_tool")
        assert config.enabled is False
        
        # 启用
        registry.enable_tool("test_tool")
        config = registry.get_tool_config("test_tool")
        assert config.enabled is True


class TestServiceFactory:
    """ServiceFactory 测试"""
    
    def test_from_yaml_loads_services(self, tmp_path):
        """测试从 YAML 加载服务配置"""
        from alice.control_plane import ServiceFactory
        
        yaml_content = """
services:
  rag:
    provider: chroma
    fallback: chroma
  search:
    provider: tavily
providers:
  chroma:
    impl: services.rag.ChromaProvider
  tavily:
    impl: services.search.TavilyProvider
"""
        yaml_file = tmp_path / "services.yaml"
        yaml_file.write_text(yaml_content)
        
        factory = ServiceFactory.from_yaml(str(yaml_file))
        
        rag_config = factory.get_service_config("rag")
        assert rag_config is not None
        assert rag_config.provider == "chroma"
        
        search_provider = factory.get_provider_name("search")
        assert search_provider == "tavily"


class TestAliceControlPlane:
    """AliceControlPlane 测试"""
    
    def test_from_config_creates_all_components(self, tmp_path):
        """测试从配置创建所有组件"""
        from alice.control_plane import AliceControlPlane
        
        # 创建配置文件
        (tmp_path / "models.yaml").write_text("model_profiles: {}\ntask_defaults: {}")
        (tmp_path / "prompts.yaml").write_text("prompts: {}")
        (tmp_path / "tools.yaml").write_text("tools: []\nscene_defaults: {}")
        (tmp_path / "services.yaml").write_text("services: {}\nproviders: {}")
        
        cp = AliceControlPlane.from_config(str(tmp_path))
        
        assert cp.models is not None
        assert cp.prompts is not None
        assert cp.tools is not None
        assert cp.services is not None
    
    def test_convenience_methods(self, tmp_path):
        """测试便捷方法"""
        from alice.control_plane import AliceControlPlane
        
        # 配置需要放在 base/ 子目录
        base_path = tmp_path / "base"
        base_path.mkdir()
        
        (base_path / "models.yaml").write_text("""
model_profiles:
  test.chat:
    kind: chat
    provider: openai
    model: gpt-4
task_defaults:
  chat: test.chat
""")
        (base_path / "prompts.yaml").write_text("""
prompts:
  test.system: "You are a test assistant."
""")
        (base_path / "tools.yaml").write_text("""
tools:
  - name: calculator
    impl: test.Calc
    enabled: true
scene_defaults:
  chat: ["calculator"]
""")
        (base_path / "services.yaml").write_text("services: {}\nproviders: {}")
        
        cp = AliceControlPlane.from_config(str(tmp_path))
        
        # 测试 list 方法
        profiles = cp.list_model_profiles()
        assert "test.chat" in profiles
        
        keys = cp.list_prompt_keys()
        assert "test.system" in keys
        
        tools = cp.list_tools_for_scene("chat")
        assert "calculator" in tools
