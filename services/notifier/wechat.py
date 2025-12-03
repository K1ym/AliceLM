"""
企业微信通知
支持Webhook机器人和应用消息
"""

import json
from typing import Optional

import httpx

from packages.config import get_config
from packages.logging import get_logger

from .base import NotifierBase, NotifyMessage

logger = get_logger(__name__)


class WeChatWorkNotifier(NotifierBase):
    """企业微信通知器"""

    name = "wechat_work"

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        corp_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        """
        初始化企业微信通知器
        
        支持两种方式：
        1. Webhook机器人（简单）
        2. 应用消息（需要corp_id, agent_id, secret）
        """
        config = get_config()
        
        self.webhook_url = webhook_url or config.wechat.webhook_url
        self.corp_id = corp_id or config.wechat.corp_id
        self.agent_id = agent_id or config.wechat.agent_id
        self.secret = secret or config.wechat.secret
        
        self._access_token = None
        self._token_expires = 0

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.webhook_url) or bool(self.corp_id and self.secret)

    def send(self, message: NotifyMessage) -> bool:
        """发送通知"""
        if self.webhook_url:
            return self._send_webhook(message)
        elif self.corp_id and self.secret:
            return self._send_app_message(message)
        else:
            logger.warning("wechat_not_configured")
            return False

    def _send_webhook(self, message: NotifyMessage) -> bool:
        """通过Webhook发送"""
        # 构建Markdown消息
        content = f"## {message.title}\n\n{message.content}"
        if message.url:
            content += f"\n\n[查看详情]({message.url})"

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(self.webhook_url, json=payload)
                result = resp.json()

                if result.get("errcode") == 0:
                    logger.info("wechat_sent", method="webhook", title=message.title)
                    return True
                else:
                    logger.error(
                        "wechat_failed",
                        method="webhook",
                        errcode=result.get("errcode"),
                        errmsg=result.get("errmsg"),
                    )
                    return False
        except Exception as e:
            logger.error("wechat_error", method="webhook", error=str(e))
            return False

    def _get_access_token(self) -> Optional[str]:
        """获取应用access_token"""
        import time

        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {"corpid": self.corp_id, "corpsecret": self.secret}

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, params=params)
                result = resp.json()

                if result.get("errcode") == 0:
                    self._access_token = result["access_token"]
                    self._token_expires = time.time() + result["expires_in"] - 60
                    return self._access_token
                else:
                    logger.error(
                        "wechat_token_failed",
                        errcode=result.get("errcode"),
                        errmsg=result.get("errmsg"),
                    )
                    return None
        except Exception as e:
            logger.error("wechat_token_error", error=str(e))
            return None

    def _send_app_message(self, message: NotifyMessage) -> bool:
        """通过应用消息发送"""
        token = self._get_access_token()
        if not token:
            return False

        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        # 构建文本卡片消息
        content = message.content[:120]  # 描述最多128字节
        
        payload = {
            "touser": "@all",
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": message.title,
                "description": content,
                "url": message.url or f"https://www.bilibili.com/video/{message.video_bvid}",
                "btntxt": "查看详情",
            },
        }

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(url, json=payload)
                result = resp.json()

                if result.get("errcode") == 0:
                    logger.info("wechat_sent", method="app", title=message.title)
                    return True
                else:
                    logger.error(
                        "wechat_failed",
                        method="app",
                        errcode=result.get("errcode"),
                        errmsg=result.get("errmsg"),
                    )
                    return False
        except Exception as e:
            logger.error("wechat_error", method="app", error=str(e))
            return False

    def send_video_complete(self, bvid: str, title: str, transcript_preview: str) -> bool:
        """发送视频处理完成通知"""
        message = NotifyMessage(
            title=f"📹 视频转写完成",
            content=f"**{title}**\n\n> {transcript_preview[:100]}...",
            url=f"https://www.bilibili.com/video/{bvid}",
            video_bvid=bvid,
        )
        return self.send(message)

    def send_error(self, bvid: str, title: str, error: str) -> bool:
        """发送处理失败通知"""
        message = NotifyMessage(
            title=f"❌ 视频处理失败",
            content=f"**{title}**\n\n错误: {error[:100]}",
            video_bvid=bvid,
        )
        return self.send(message)
