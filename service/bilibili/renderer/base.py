"""渲染器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class MessageMode(str, Enum):
    """消息发送模式"""
    SIMPLE = "simple"           # 简单模式：纯文本 + 图片分开发送
    SEGMENTS = "segments"       # 消息段模式：使用 OneBot 消息段格式
    FORWARD = "forward"         # 合并转发模式：将内容打包为合并转发消息


@dataclass
class RenderedContent:
    """渲染结果"""
    text: str                                   # 文本内容
    images: List[str] = field(default_factory=list)  # 图片 URL 列表
    mode: MessageMode = MessageMode.SIMPLE      # 消息发送模式
    # 可选：用于视频卡片
    video_card: Optional[Dict[str, str]] = None  # {"title", "desc", "cover", "url"}

    def to_segments(self) -> List[Dict[str, Any]]:
        """
        转换为 OneBot 消息段格式
        返回格式: [{"type": "text/image", "data": {...}}, ...]
        """
        segments = []

        # 添加文本
        if self.text:
            segments.append({
                "type": "text",
                "data": {"text": self.text}
            })

        # 添加图片
        for image_url in self.images:
            segments.append({
                "type": "image",
                "data": {"file": image_url}
            })

        return segments

    def to_forward_nodes(self, bot_id: str, bot_name: str = "Ki酱") -> List[Dict[str, Any]]:
        """
        转换为合并转发消息节点格式
        """
        nodes = []

        # 文本节点
        if self.text:
            nodes.append({
                "type": "node",
                "data": {
                    "user_id": bot_id,
                    "nickname": bot_name,
                    "content": [{"type": "text", "data": {"text": self.text}}]
                }
            })

        # 图片节点（每张图片一个节点）
        for image_url in self.images:
            nodes.append({
                "type": "node",
                "data": {
                    "user_id": bot_id,
                    "nickname": bot_name,
                    "content": [{"type": "image", "data": {"file": image_url}}]
                }
            })

        return nodes


class BaseRenderer(ABC):
    """渲染器基类"""

    @abstractmethod
    def render(self, data) -> RenderedContent:
        """渲染数据为可发送的内容"""
        pass
