"""
控制平面 API 测试
"""

import asyncio
import importlib.metadata as metadata
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch


def run_async(coro):
    """在同步测试中运行异步代码"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def write_base_config(tmp_path: Path, files: dict) -> Path:
    """在临时目录下创建 base 配置文件"""
    base_path = tmp_path / "base"
    base_path.mkdir(exist_ok=True)
    for filename, content in files.items():
        (base_path / filename).write_text(content)
    return base_path


def ensure_email_validator():
    """
    pydantic 对 email 字段会 import email_validator，本地依赖缺失会导致测试导入失败。
    注入一个轻量的 mock 模块以便测试通过，不影响生产代码。
    """
    if "email_validator" in sys.modules:
        return
    module = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        ...

    def validate_email(email, *_args, **_kwargs):
        return {"email": email}

    module.EmailNotValidError = EmailNotValidError
    module.validate_email = validate_email
    sys.modules["email_validator"] = module

    # 兼容 pydantic 对 email-validator 版本检查
    original_version = metadata.version

    def fake_version(name: str):
        if name == "email-validator":
            return "2.0.0"
        return original_version(name)

    metadata.version = fake_version


class TestControlPlaneModelsAPI:
    """模型 API 测试"""

    def test_list_model_profiles(self, tmp_path):
        """测试列出模型 profiles"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_model_profiles

        write_base_config(
            tmp_path,
            {
                "models.yaml": """
model_profiles:
  alice.chat.main:
    kind: chat
    provider: openai
    model: gpt-4
  alice.embed.default:
    kind: embedding
    provider: openai
    model: text-embedding-3
task_defaults:
  chat: alice.chat.main
  embedding: alice.embed.default
""",
                "prompts.yaml": "prompts: {}",
                "tools.yaml": "tools: []\nscene_defaults: {}",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))

        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_model_profiles(kind=None, user=mock_user))

        assert len(result.profiles) == 2

        profile_ids = [p.id for p in result.profiles]
        assert "alice.chat.main" in profile_ids
        assert "alice.embed.default" in profile_ids

    def test_list_model_profiles_by_kind(self, tmp_path):
        """测试按类型过滤"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_model_profiles

        write_base_config(
            tmp_path,
            {
                "models.yaml": """
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
""",
                "prompts.yaml": "prompts: {}",
                "tools.yaml": "tools: []\nscene_defaults: {}",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_model_profiles(kind="chat", user=mock_user))

        assert len(result.profiles) == 1
        assert result.profiles[0].kind == "chat"


class TestControlPlaneToolsAPI:
    """工具 API 测试"""

    def test_list_tools_for_scene(self, tmp_path):
        """测试列出场景工具"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_tools

        write_base_config(
            tmp_path,
            {
                "models.yaml": "model_profiles: {}\ntask_defaults: {}",
                "prompts.yaml": "prompts: {}",
                "tools.yaml": """
tools:
  - name: calculator
    impl: test.CalculatorTool
    enabled: true
  - name: web_search
    impl: test.WebSearchTool
    enabled: true
scene_defaults:
  chat: ["calculator"]
  research: ["calculator", "web_search"]
""",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_tools(scene="chat", user=mock_user))

        assert result.scene == "chat"
        assert len(result.tools) == 1
        assert result.tools[0].name == "calculator"

    def test_list_all_scenes(self, tmp_path):
        """测试列出所有场景"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_tools

        write_base_config(
            tmp_path,
            {
                "models.yaml": "model_profiles: {}\ntask_defaults: {}",
                "prompts.yaml": "prompts: {}",
                "tools.yaml": """
tools:
  - name: echo
    impl: test.EchoTool
    enabled: true
scene_defaults:
  chat: ["echo"]
  research: ["echo"]
""",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_tools(scene=None, user=mock_user))

        assert result.all_scenes is not None
        assert "chat" in result.all_scenes
        assert "research" in result.all_scenes


class TestControlPlanePromptsAPI:
    """Prompt API 测试"""

    def test_list_prompts(self, tmp_path):
        """测试列出 prompts"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_prompts

        write_base_config(
            tmp_path,
            {
                "models.yaml": "model_profiles: {}\ntask_defaults: {}",
                "prompts.yaml": """
prompts:
  alice.system.base: "You are Alice, an AI assistant."
  alice.task.summary: "You are a summarization assistant."
""",
                "tools.yaml": "tools: []\nscene_defaults: {}",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_prompts(key=None, user=mock_user))

        assert len(result.prompts) == 2

        keys = [p.key for p in result.prompts]
        assert "alice.system.base" in keys
        assert "alice.task.summary" in keys

    def test_list_prompts_by_key(self, tmp_path):
        """测试按 key 过滤"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import list_prompts

        write_base_config(
            tmp_path,
            {
                "models.yaml": "model_profiles: {}\ntask_defaults: {}",
                "prompts.yaml": """
prompts:
  alice.system.base: "System prompt"
  alice.task.summary: "Summary prompt"
""",
                "tools.yaml": "tools: []\nscene_defaults: {}",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            result = run_async(list_prompts(key="alice.system.base", user=mock_user))

        assert len(result.prompts) == 1
        assert result.prompts[0].key == "alice.system.base"


class TestControlPlaneSummaryAPI:
    """摘要 API 测试"""

    def test_get_summary(self, tmp_path):
        """测试获取控制平面摘要"""
        from alice.control_plane import AliceControlPlane
        ensure_email_validator()
        from apps.api.routers.control_plane import get_control_plane_summary

        write_base_config(
            tmp_path,
            {
                "models.yaml": """
model_profiles:
  alice.chat.main:
    kind: chat
    provider: openai
    model: gpt-4
task_defaults:
  chat: alice.chat.main
""",
                "prompts.yaml": """
prompts:
  alice.system.base: "Test prompt"
""",
                "tools.yaml": """
tools:
  - name: echo
    impl: test.EchoTool
    enabled: true
scene_defaults:
  chat: ["echo"]
""",
                "services.yaml": "services: {}\nproviders: {}",
            },
        )

        cp = AliceControlPlane.from_config(str(tmp_path))
        mock_user = Mock()
        mock_user.id = 1

        with patch("alice.control_plane.get_control_plane", return_value=cp):
            with patch.dict(
                "os.environ",
                {"OPENAI_API_KEY": "test", "OPENAI_BASE_URL": "https://api.test.com"},
            ):
                result = run_async(get_control_plane_summary(user=mock_user))

        # 验证结构
        assert "chat" in result.models
        assert "chat" in result.scenes
        assert "alice.system.base" in result.prompts
