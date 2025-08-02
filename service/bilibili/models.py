from typing import Optional
from pydantic import BaseModel


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


# 延迟解析，避免类型检查出错
QRCodeGenerateResponse.model_rebuild()
QRCodePollResponse.model_rebuild() 