"""B站用户相关模型"""

from typing import Optional
from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """用户基本信息"""
    mid: int = 0
    name: str = ""
    face: str = ""          # 头像
    sign: str = ""          # 签名
    level: int = 0          # 等级
    sex: str = "保密"

    class Config:
        extra = "ignore"


class UserStat(BaseModel):
    """用户统计"""
    follower: int = 0       # 粉丝数
    following: int = 0      # 关注数

    class Config:
        extra = "ignore"


class UserCard(BaseModel):
    """用户名片"""
    card: UserInfo = Field(default_factory=UserInfo)
    follower: int = 0       # 粉丝数（API 返回在外层）
    following: int = 0      # 关注数

    class Config:
        extra = "ignore"

    @property
    def info(self) -> UserInfo:
        """获取用户信息（兼容设计文档）"""
        return self.card

    @property
    def stat(self) -> UserStat:
        """获取用户统计（从外层数据构造）"""
        return UserStat(follower=self.follower, following=self.following)
