"""B站视频相关模型"""

from typing import Optional, List
from pydantic import BaseModel, Field


class VideoOwner(BaseModel):
    """视频 UP主"""
    mid: int = 0
    name: str = ""
    face: str = ""

    class Config:
        extra = "ignore"


class VideoStat(BaseModel):
    """视频统计数据"""
    view: int = 0       # 播放量
    danmaku: int = 0    # 弹幕数
    reply: int = 0      # 评论数
    favorite: int = 0   # 收藏数
    coin: int = 0       # 投币数
    share: int = 0      # 分享数
    like: int = 0       # 点赞数

    class Config:
        extra = "ignore"


class VideoDimension(BaseModel):
    """视频分辨率"""
    width: int = 0
    height: int = 0
    rotate: int = 0

    class Config:
        extra = "ignore"


class VideoPage(BaseModel):
    """视频分P"""
    cid: int = 0
    page: int = 0
    part: str = ""      # 分P标题
    duration: int = 0   # 时长（秒）

    class Config:
        extra = "ignore"


class VideoInfo(BaseModel):
    """视频详细信息"""
    bvid: str = ""
    aid: int = 0
    title: str = ""
    pic: str = ""                   # 封面
    desc: str = ""                  # 简介
    pubdate: int = 0                # 发布时间戳
    duration: int = 0               # 总时长（秒）
    owner: VideoOwner = Field(default_factory=VideoOwner)
    stat: VideoStat = Field(default_factory=VideoStat)
    dimension: VideoDimension = Field(default_factory=VideoDimension)
    pages: List[VideoPage] = Field(default_factory=list)
    tname: str = ""                 # 分区名

    class Config:
        extra = "ignore"

    @property
    def url(self) -> str:
        """视频链接"""
        return f"https://www.bilibili.com/video/{self.bvid}"

    @property
    def duration_text(self) -> str:
        """格式化时长"""
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
