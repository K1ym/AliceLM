"""
ServiceFactory - Service 创建中心

职责：统一创建 Service 实例，决定使用哪个 Provider
替代老的散落 Service 初始化逻辑
"""

from pathlib import Path
from typing import Dict, Optional, Any
import yaml

from packages.logging import get_logger
from .types import ServiceConfig, ProviderConfig

logger = get_logger(__name__)


class ServiceFactory:
    """
    Service 工厂（控制平面核心组件）
    
    行为：
    1. 从 config/services.yaml 加载服务配置
    2. 根据 provider 名称选择实现
    3. 支持 fallback 降级
    """
    
    def __init__(
        self,
        services: Dict[str, ServiceConfig],
        providers: Dict[str, ProviderConfig],
    ):
        self._services = services
        self._providers = providers
        self._instance_cache: Dict[str, Any] = {}
        logger.info(f"ServiceFactory initialized with {len(services)} services")
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/services.yaml") -> "ServiceFactory":
        """从 YAML 文件加载"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Services config not found: {yaml_path}, using empty config")
            return cls({}, {})
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        services = {}
        for name, config in data.get("services", {}).items():
            services[name] = ServiceConfig(**config)
        
        providers = {}
        for name, config in data.get("providers", {}).items():
            providers[name] = ProviderConfig(**config)
        
        return cls(services, providers)
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """获取服务配置"""
        return self._services.get(service_name)
    
    def get_provider_name(self, service_name: str) -> Optional[str]:
        """获取服务当前使用的 provider"""
        config = self._services.get(service_name)
        return config.provider if config else None
    
    # ========== RAG Service ==========
    
    def create_rag_service(self, tenant_id: Optional[int] = None) -> Any:
        """创建 RAG 服务"""
        from services.ai import RAGService
        
        config = self._services.get("rag")
        if not config:
            return RAGService()
        
        # 目前 RAGService 内部已处理 provider 选择
        # 未来可根据 config.provider 选择不同实现
        return RAGService()
    
    # ========== Search Service ==========
    
    def create_search_service(self, tenant_id: Optional[int] = None) -> Any:
        """创建搜索服务"""
        from alice.search import SearchAgentService
        
        config = self._services.get("search")
        provider = config.provider if config else "tavily"
        
        # SearchAgentService 内部会根据配置选择 provider
        return SearchAgentService()
    
    # ========== ASR Service ==========
    
    def create_asr_service(self, tenant_id: Optional[int] = None) -> Any:
        """创建 ASR 服务"""
        from services.asr import ASRManager
        
        config = self._services.get("asr")
        if not config:
            return ASRManager()
        
        # ASRManager 内部已处理 provider 选择
        return ASRManager()
    
    # ========== Downloader Service ==========
    
    def create_downloader_service(self, tenant_id: Optional[int] = None) -> Any:
        """创建下载服务"""
        from services.downloader import BBDownService
        
        config = self._services.get("downloader")
        if not config:
            return BBDownService()
        
        # 目前只有 BBDown 实现
        return BBDownService()
    
    # ========== Embedding Service ==========
    
    def create_embedding_service(self, tenant_id: Optional[int] = None) -> Any:
        """创建 Embedding 服务"""
        from services.ai import EmbeddingService
        
        config = self._services.get("embedding")
        # EmbeddingService 使用 ModelRegistry 获取模型配置
        return EmbeddingService()
    
    # ========== Video Pipeline ==========
    
    def create_video_pipeline(self, tenant_id: Optional[int] = None) -> Any:
        """创建视频处理管道"""
        from services.processor import VideoPipeline
        
        return VideoPipeline(
            downloader=self.create_downloader_service(tenant_id),
            asr_manager=self.create_asr_service(tenant_id),
        )
    
    # ========== 通用方法 ==========
    
    def get_or_create(self, service_name: str, tenant_id: Optional[int] = None) -> Any:
        """获取或创建服务实例（带缓存）"""
        cache_key = f"{service_name}:{tenant_id or 'default'}"
        
        if cache_key in self._instance_cache:
            return self._instance_cache[cache_key]
        
        # 根据服务名创建
        factory_method = {
            "rag": self.create_rag_service,
            "search": self.create_search_service,
            "asr": self.create_asr_service,
            "downloader": self.create_downloader_service,
            "embedding": self.create_embedding_service,
            "video_pipeline": self.create_video_pipeline,
        }.get(service_name)
        
        if not factory_method:
            raise ValueError(f"Unknown service: {service_name}")
        
        instance = factory_method(tenant_id)
        self._instance_cache[cache_key] = instance
        return instance
    
    def clear_cache(self):
        """清除实例缓存"""
        self._instance_cache.clear()
