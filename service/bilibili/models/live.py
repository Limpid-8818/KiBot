"""B站直播间数据模型"""

from typing import Optional
from pydantic import BaseModel


class LiveRoomInfo(BaseModel):
    """直播间信息（批量查询API返回）"""
    title: str = ""                     # 直播间标题
    room_id: int = 0                    # 直播间房间号（长号）
    uid: int = 0                        # 主播mid
    online: int = 0                     # 在线人数
    live_time: int = 0                  # 开播时间戳（未开播为0）
    live_status: int = 0                # 直播状态: 0未开播, 1直播中, 2轮播中
    short_id: int = 0                   # 直播间短号
    area_name: str = ""                 # 分区名
    area_v2_name: str = ""              # 新版分区名
    area_v2_parent_name: str = ""       # 父分区名
    uname: str = ""                     # 主播用户名
    face: str = ""                      # 主播头像url
    cover_from_user: str = ""           # 直播间封面url
    keyframe: str = ""                  # 直播间关键帧url

    class Config:
        extra = "ignore"

    @property
    def is_living(self) -> bool:
        """是否正在直播"""
        return self.live_status == 1

    @property
    def live_url(self) -> str:
        """直播间链接"""
        return f"https://live.bilibili.com/{self.room_id}"

    @property
    def cover(self) -> str:
        """封面（优先关键帧，无则用用户封面）"""
        return self.keyframe or self.cover_from_user or ""


class LiveRoomOldInfo(BaseModel):
    """直播间信息（getRoomInfoOld API返回）"""
    roomStatus: int = 0                 # 直播间状态: 0无房间, 1有房间
    roundStatus: int = 0                # 轮播状态: 0未轮播, 1轮播
    live_status: int = 0                # 直播状态: 0未开播, 1直播中
    url: str = ""                       # 直播间网页url
    title: str = ""                     # 直播间标题
    cover: str = ""                     # 直播间封面url
    online: int = 0                     # 直播间人气
    roomid: int = 0                     # 直播间id（短号）

    class Config:
        extra = "ignore"

    @property
    def is_living(self) -> bool:
        """是否正在直播"""
        return self.live_status == 1
