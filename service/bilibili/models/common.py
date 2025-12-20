"""B站 API 通用模型"""

from typing import Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class BiliResponse(BaseModel, Generic[T]):
    """B站 API 通用响应"""
    code: int
    message: str
    ttl: int = 1
    data: Optional[T] = None

    @property
    def is_success(self) -> bool:
        """判断请求是否成功"""
        return self.code == 0


class BiliCookie(BaseModel):
    """B站 Cookie 信息"""
    DedeUserID: str
    DedeUserID__ckMd5: str
    SESSDATA: str
    bili_jct: str

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "SESSDATA": self.SESSDATA,
            "bili_jct": self.bili_jct,
            "DedeUserID": self.DedeUserID,
            "DedeUserID__ckMd5": self.DedeUserID__ckMd5
        }
