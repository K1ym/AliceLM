"""
配置服务
用户配置相关的业务逻辑
"""

import json
from typing import Optional

from packages.logging import get_logger

from ..repositories.config_repo import ConfigRepository

logger = get_logger(__name__)


class ConfigService:
    """配置服务类"""
    
    def __init__(self, config_repo: ConfigRepository):
        self.repo = config_repo
    
    def get_config_dict(self, user_id: int, config_key: str) -> dict:
        """获取配置字典"""
        value = self.repo.get_value(user_id, config_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return {}
    
    def get_task_llm_config(self, user_id: int, task_type: str) -> dict:
        """
        获取特定任务的LLM配置
        
        Args:
            user_id: 用户ID
            task_type: 任务类型 (chat/summary/knowledge/mindmap/tagger/context_compress)
        
        Returns:
            dict: {"base_url": str, "api_key": str, "model": str}
        """
        tasks_config = self.get_config_dict(user_id, "model_tasks")
        task_config = tasks_config.get(task_type, {}) if tasks_config else {}
        
        if task_config:
            endpoint_id = task_config.get("endpoint_id")
            if endpoint_id:
                endpoints_raw = self.get_config_dict(user_id, "llm_endpoints")
                endpoints_list = endpoints_raw.get("endpoints", []) if endpoints_raw else []
                endpoint = next((ep for ep in endpoints_list if ep.get("id") == endpoint_id), None)
                if endpoint:
                    return {
                        "base_url": endpoint["base_url"],
                        "api_key": endpoint["api_key"],
                        "model": task_config.get("model", ""),
                    }
            else:
                return {
                    "base_url": task_config.get("base_url", ""),
                    "api_key": "",
                    "model": task_config.get("model", ""),
                }
        
        # 回退到默认LLM配置
        llm_config = self.get_config_dict(user_id, "llm")
        return {
            "base_url": llm_config.get("base_url", ""),
            "api_key": llm_config.get("api_key", ""),
            "model": llm_config.get("model", "gpt-4o-mini"),
        }
    
    def get_user_prompt(self, user_id: int, prompt_key: str) -> str:
        """获取用户提示词"""
        prompts_config = self.get_config_dict(user_id, "prompts")
        return prompts_config.get(prompt_key, "")
    
    def get_config(self, user_id: int, key: str) -> Optional[str]:
        """获取用户配置原始值"""
        return self.repo.get_value(user_id, key)
    
    def set_config(self, user_id: int, key: str, value: str) -> None:
        """设置用户配置"""
        self.repo.set_value(user_id, key, value)
