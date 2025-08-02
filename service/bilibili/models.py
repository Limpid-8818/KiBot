from typing import Optional
from pydantic import BaseModel


# 二维码登录相关模型
class QRCodeGenerateResponse(BaseModel):
    """二维码生成响应"""
    code: int
    message: str
    ttl: int
    data: Optional['QRCodeData'] = None


class QRCodeData(BaseModel):
    """二维码数据"""
    url: str
    qrcode_key: str


class QRCodePollResponse(BaseModel):
    """二维码轮询响应"""
    code: int
    message: str
    data: Optional['QRCodePollData'] = None


class QRCodePollData(BaseModel):
    """二维码轮询数据"""
    url: str
    refresh_token: str
    timestamp: int
    code: int
    message: str


class BiliCookie(BaseModel):
    """B站Cookie信息"""
    DedeUserID: str
    DedeUserID__ckMd5: str
    SESSDATA: str
    bili_jct: str


# Cookie刷新相关模型
class CookieInfoResponse(BaseModel):
    """Cookie信息检查响应"""
    code: int
    message: str
    ttl: int
    data: Optional['CookieInfoData'] = None


class CookieInfoData(BaseModel):
    """Cookie信息数据"""
    refresh: bool
    timestamp: int


class CookieRefreshResponse(BaseModel):
    """Cookie刷新响应"""
    code: int
    message: str
    ttl: int
    data: Optional['CookieRefreshData'] = None


class CookieRefreshData(BaseModel):
    """Cookie刷新数据"""
    status: int
    message: str
    refresh_token: str


class CookieConfirmResponse(BaseModel):
    """Cookie确认响应"""
    code: int
    message: str
    ttl: int


# 更新前向引用
QRCodeGenerateResponse.model_rebuild()
QRCodePollResponse.model_rebuild()
CookieInfoResponse.model_rebuild()
CookieRefreshResponse.model_rebuild() 