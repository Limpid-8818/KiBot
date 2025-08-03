from typing import Optional, List, Dict, Any
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


# 动态相关模型，具体格式参考 https://socialsisteryi.github.io/bilibili-API-collect/docs/dynamic/all.html#%E8%8E%B7%E5%8F%96%E5%85%A8%E9%83%A8%E5%8A%A8%E6%80%81%E5%88%97%E8%A1%A8
# 二编，获取动态所使用的API针对部分类型的动态返回的动态内容并不全，所以下面的数据模型基本没用，留着以后再完善吧
class DynamicResponse(BaseModel):
    """动态列表响应"""
    code: int
    message: str
    ttl: int
    data: Optional['DynamicData'] = None


class DynamicData(BaseModel):
    """动态数据"""
    has_more: bool
    items: List['DynamicItem']
    offset: str
    update_baseline: str
    update_num: int


class DynamicItem(BaseModel):
    """动态条目"""
    basic: 'DynamicBasic'
    id_str: str
    modules: 'DynamicModules'
    type: str   # 动态类型，具体见 https://socialsisteryi.github.io/bilibili-API-collect/docs/dynamic/dynamic_enum.html#%E5%8A%A8%E6%80%81%E7%B1%BB%E5%9E%8B
    visible: bool
    orig: Optional['DynamicItem'] = None


class DynamicBasic(BaseModel):
    """动态基础信息"""
    comment_id_str: str   # 需要用，与动态类型有关，比如 DYNAMIC_TYPE_AV 则代表发布视频的AV号	
    comment_type: int   # 数字标识符，没啥用
    like_icon: Dict[str, Any]   # 鸟用没有
    rid_str: str   # 和 comment_id_str 差不多，没啥用


class DynamicModules(BaseModel):
    """动态模块信息"""
    module_author: 'ModuleAuthor'   # UP主信息
    module_dynamic: 'ModuleDynamic'   # 动态内容信息	
    module_more: Optional[Dict[str, Any]] = None
    module_stat: Optional['ModuleStat'] = None   # 动态统计数据
    module_interaction: Optional[Dict[str, Any]] = None
    module_fold: Optional[Dict[str, Any]] = None
    module_dispute: Optional[Dict[str, Any]] = None
    module_tag: Optional[Dict[str, Any]] = None


class ModuleAuthor(BaseModel):
    """UP主信息"""
    face: str
    face_nft: bool
    following: Optional[bool]
    jump_url: str
    label: str
    mid: int
    name: str
    pub_action: Optional[str] = None  # 发布动作，如"发布了视频"、"发布了动态"等
    official_verify: Optional[Dict[str, Any]] = None


class ModuleDynamic(BaseModel):
    """动态内容信息"""
    additional: Optional[Dict[str, Any]] = None   # 内容卡片信息，不管
    desc: Optional['DynamicDesc'] = None   # 动态文字内容
    major: Optional['DynamicMajor'] = None   # 动态主体对象，转发动态为NULL
    topic: Optional[Dict[str, Any]] = None   # 话题，不管


class DynamicDesc(BaseModel):
    """动态描述"""
    rich_text_nodes: Optional[List[Dict[str, Any]]] = None   # 富文本内容
    text: str   # 纯文本内容


class DynamicMajor(BaseModel):
    """动态主要内容"""
    archive: Optional[Dict[str, Any]] = None
    draw: Optional[Dict[str, Any]] = None
    article: Optional[Dict[str, Any]] = None
    live_rcmd: Optional[Dict[str, Any]] = None
    ugc_season: Optional[Dict[str, Any]] = None
    live: Optional[Dict[str, Any]] = None
    music: Optional[Dict[str, Any]] = None
    common: Optional[Dict[str, Any]] = None
    type: str


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


# 延迟解析，避免类型检查出错
QRCodeGenerateResponse.model_rebuild()
QRCodePollResponse.model_rebuild()
DynamicResponse.model_rebuild()
CookieInfoResponse.model_rebuild()
CookieRefreshResponse.model_rebuild() 