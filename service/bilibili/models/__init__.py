# B站服务数据模型

from .common import BiliResponse, BiliCookie
from .auth import QRCodeGenerateResponse, QRCodeData, QRCodePollResponse, QRCodePollData
from .auth import CookieInfoResponse, CookieInfoData, CookieRefreshResponse, CookieRefreshData, CookieConfirmResponse
from .dynamic import (
    DynamicType, DynamicAuthor, DynamicArchive, ArchiveStat,
    DrawItem, DynamicDraw, DynamicArticle, DynamicMusic, DynamicCommon,
    DynamicMajor, DynamicDesc, ModuleDynamic, DynamicModule,
    DynamicItem, DynamicListData
)
from .video import VideoOwner, VideoStat, VideoDimension, VideoPage, VideoInfo
from .user import UserInfo, UserStat, UserCard
from .live import LiveRoomInfo, LiveRoomOldInfo

__all__ = [
    # common
    "BiliResponse", "BiliCookie",
    # auth
    "QRCodeGenerateResponse", "QRCodeData", "QRCodePollResponse", "QRCodePollData",
    "CookieInfoResponse", "CookieInfoData", "CookieRefreshResponse", "CookieRefreshData", "CookieConfirmResponse",
    # dynamic
    "DynamicType", "DynamicAuthor", "DynamicArchive", "ArchiveStat",
    "DrawItem", "DynamicDraw", "DynamicArticle", "DynamicMusic", "DynamicCommon",
    "DynamicMajor", "DynamicDesc", "ModuleDynamic", "DynamicModule",
    "DynamicItem", "DynamicListData",
    # video
    "VideoOwner", "VideoStat", "VideoDimension", "VideoPage", "VideoInfo",
    # user
    "UserInfo", "UserStat", "UserCard",
    # live
    "LiveRoomInfo", "LiveRoomOldInfo",
]
