"""B站登录认证相关模型"""

from typing import Optional
from pydantic import BaseModel


# === 二维码登录相关模型 ===

class QRCodeData(BaseModel):
    """二维码数据"""
    url: str
    qrcode_key: str


class QRCodeGenerateResponse(BaseModel):
    """二维码生成响应"""
    code: int
    message: str
    ttl: int = 1
    data: Optional[QRCodeData] = None


class QRCodePollData(BaseModel):
    """二维码轮询数据"""
    url: str
    refresh_token: str
    timestamp: int
    code: int
    message: str


class QRCodePollResponse(BaseModel):
    """二维码轮询响应"""
    code: int
    message: str
    data: Optional[QRCodePollData] = None


# === Cookie 刷新相关模型 ===

class CookieInfoData(BaseModel):
    """Cookie 信息数据"""
    refresh: bool
    timestamp: int


class CookieInfoResponse(BaseModel):
    """Cookie 信息检查响应"""
    code: int
    message: str
    ttl: int = 1
    data: Optional[CookieInfoData] = None


class CookieRefreshData(BaseModel):
    """Cookie 刷新数据"""
    status: int
    message: str
    refresh_token: str


class CookieRefreshResponse(BaseModel):
    """Cookie 刷新响应"""
    code: int
    message: str
    ttl: int = 1
    data: Optional[CookieRefreshData] = None


class CookieConfirmResponse(BaseModel):
    """Cookie 确认响应"""
    code: int
    message: str
    ttl: int = 1
