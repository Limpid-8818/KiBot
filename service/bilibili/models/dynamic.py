"""B站动态相关模型"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class DynamicType(str, Enum):
    """动态类型枚举"""
    AV = "DYNAMIC_TYPE_AV"                    # 视频
    DRAW = "DYNAMIC_TYPE_DRAW"                # 图文
    WORD = "DYNAMIC_TYPE_WORD"                # 纯文字
    FORWARD = "DYNAMIC_TYPE_FORWARD"          # 转发
    ARTICLE = "DYNAMIC_TYPE_ARTICLE"          # 专栏
    MUSIC = "DYNAMIC_TYPE_MUSIC"              # 音乐
    LIVE_RCMD = "DYNAMIC_TYPE_LIVE_RCMD"      # 直播推荐
    LIVE = "DYNAMIC_TYPE_LIVE"                # 直播
    COMMON = "DYNAMIC_TYPE_COMMON_SQUARE"     # 通用卡片
    PGC = "DYNAMIC_TYPE_PGC"                  # 番剧/电影等
    COURSES = "DYNAMIC_TYPE_COURSES"          # 课程
    UGC_SEASON = "DYNAMIC_TYPE_UGC_SEASON"    # 合集
    NONE = "DYNAMIC_TYPE_NONE"                # 无效/已删除

    @classmethod
    def _missing_(cls, value):
        """处理未知类型"""
        return cls.NONE


# === 作者信息 ===

class DynamicAuthor(BaseModel):
    """动态作者信息"""
    mid: int = 0
    name: str = ""
    face: str = ""
    pub_action: str = ""           # "发布了视频"、"投稿了"等
    pub_time: str = ""             # 发布时间文本，如 "2小时前"
    pub_ts: int = 0                # 发布时间戳

    class Config:
        extra = "ignore"


# === 视频内容 ===

class ArchiveStat(BaseModel):
    """视频统计"""
    play: str = "0"       # 播放量
    danmaku: str = "0"    # 弹幕数

    class Config:
        extra = "ignore"


class DynamicArchive(BaseModel):
    """视频动态内容"""
    aid: int = 0
    bvid: str = ""
    title: str = ""
    desc: str = ""
    cover: str = ""                # 封面图 URL
    duration_text: str = ""        # 时长文本 "12:34"
    stat: ArchiveStat = Field(default_factory=ArchiveStat)
    jump_url: str = ""             # 跳转链接

    class Config:
        extra = "ignore"

    @property
    def url(self) -> str:
        """视频链接"""
        if self.bvid:
            return f"https://www.bilibili.com/video/{self.bvid}"
        return self.jump_url


# === 图文内容 ===

class DrawItem(BaseModel):
    """图片项（旧版 MAJOR_TYPE_DRAW）"""
    src: str = ""       # 图片 URL
    width: int = 0
    height: int = 0

    class Config:
        extra = "ignore"


class DynamicDraw(BaseModel):
    """图文动态内容（旧版 MAJOR_TYPE_DRAW）"""
    items: List[DrawItem] = Field(default_factory=list)

    class Config:
        extra = "ignore"


# === Opus 内容（新版图文动态） ===

class OpusPic(BaseModel):
    """Opus 图片项"""
    url: str = ""       # 图片 URL
    width: int = 0
    height: int = 0

    class Config:
        extra = "ignore"


class OpusSummary(BaseModel):
    """Opus 摘要"""
    text: str = ""
    rich_text_nodes: List[Any] = Field(default_factory=list)

    class Config:
        extra = "ignore"


class DynamicOpus(BaseModel):
    """Opus 内容（新版图文动态，MAJOR_TYPE_OPUS）"""
    pics: List[OpusPic] = Field(default_factory=list)
    summary: Optional[OpusSummary] = None
    title: Optional[str] = None
    jump_url: str = ""

    class Config:
        extra = "ignore"

    @property
    def text(self) -> str:
        """获取摘要文本"""
        return self.summary.text if self.summary else ""

    @property
    def images(self) -> List[str]:
        """获取图片 URL 列表"""
        return [pic.url for pic in self.pics if pic.url]


# === 专栏内容 ===

class DynamicArticle(BaseModel):
    """专栏文章内容"""
    id: int = 0
    title: str = ""
    desc: str = ""
    covers: List[str] = Field(default_factory=list)
    label: str = ""     # 分类标签
    jump_url: str = ""

    class Config:
        extra = "ignore"

    @property
    def url(self) -> str:
        """专栏链接"""
        if self.id:
            return f"https://www.bilibili.com/read/cv{self.id}"
        return self.jump_url


# === 音乐内容 ===

class DynamicMusic(BaseModel):
    """音乐动态内容"""
    id: int = 0
    title: str = ""
    cover: str = ""
    label: str = ""     # "音频"
    jump_url: str = ""

    class Config:
        extra = "ignore"

    @property
    def url(self) -> str:
        """音频链接"""
        if self.id:
            return f"https://www.bilibili.com/audio/au{self.id}"
        return self.jump_url


# === 直播内容 ===

class DynamicLive(BaseModel):
    """直播动态内容"""
    id: int = 0
    title: str = ""
    cover: str = ""
    live_state: int = 0     # 0: 未开播, 1: 直播中
    jump_url: str = ""

    class Config:
        extra = "ignore"


# === 通用卡片 ===

class DynamicCommon(BaseModel):
    """通用卡片内容"""
    title: str = ""
    desc: str = ""
    cover: str = ""
    jump_url: str = ""       # 跳转链接

    class Config:
        extra = "ignore"


# === PGC 番剧内容 ===

class DynamicPGC(BaseModel):
    """番剧/影视动态内容"""
    epid: int = 0
    title: str = ""
    cover: str = ""
    jump_url: str = ""
    season_id: int = 0
    sub_type: int = 0       # 1: 番剧, 2: 电影, 3: 纪录片等

    class Config:
        extra = "ignore"


# === 动态主体 ===

class DynamicMajor(BaseModel):
    """动态主要内容"""
    type: str = ""
    archive: Optional[DynamicArchive] = None
    draw: Optional[DynamicDraw] = None
    opus: Optional[DynamicOpus] = None          # 新版图文动态（MAJOR_TYPE_OPUS）
    article: Optional[DynamicArticle] = None
    music: Optional[DynamicMusic] = None
    common: Optional[DynamicCommon] = None
    live: Optional[DynamicLive] = None
    live_rcmd: Optional[Dict[str, Any]] = None  # 直播推荐结构较复杂，暂用 dict
    pgc: Optional[DynamicPGC] = None
    ugc_season: Optional[Dict[str, Any]] = None  # 合集

    class Config:
        extra = "ignore"


# === 动态文字描述 ===

class RichTextNode(BaseModel):
    """富文本节点"""
    type: str = ""          # RICH_TEXT_NODE_TYPE_TEXT, RICH_TEXT_NODE_TYPE_AT 等
    text: str = ""
    orig_text: str = ""
    emoji: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"


class DynamicDesc(BaseModel):
    """动态文字描述"""
    text: str = ""
    rich_text_nodes: List[RichTextNode] = Field(default_factory=list)

    class Config:
        extra = "ignore"


# === 动态模块 ===

class ModuleDynamic(BaseModel):
    """动态内容模块"""
    desc: Optional[DynamicDesc] = None
    major: Optional[DynamicMajor] = None
    topic: Optional[Dict[str, Any]] = None      # 话题
    additional: Optional[Dict[str, Any]] = None  # 附加内容

    class Config:
        extra = "ignore"


class ModuleStat(BaseModel):
    """动态统计模块"""
    comment: Dict[str, Any] = Field(default_factory=dict)   # 评论数
    forward: Dict[str, Any] = Field(default_factory=dict)   # 转发数
    like: Dict[str, Any] = Field(default_factory=dict)      # 点赞数

    class Config:
        extra = "ignore"

    @property
    def comment_count(self) -> int:
        return self.comment.get("count", 0)

    @property
    def forward_count(self) -> int:
        return self.forward.get("count", 0)

    @property
    def like_count(self) -> int:
        return self.like.get("count", 0)


class DynamicModule(BaseModel):
    """动态模块集合"""
    module_author: DynamicAuthor = Field(default_factory=DynamicAuthor)
    module_dynamic: ModuleDynamic = Field(default_factory=ModuleDynamic)
    module_stat: Optional[ModuleStat] = None
    module_more: Optional[Dict[str, Any]] = None
    module_interaction: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"


# === 动态基础信息 ===

class DynamicBasic(BaseModel):
    """动态基础信息"""
    comment_id_str: str = ""
    comment_type: int = 0
    rid_str: str = ""

    class Config:
        extra = "ignore"


# === 动态条目 ===

class DynamicItem(BaseModel):
    """动态条目"""
    basic: DynamicBasic = Field(default_factory=DynamicBasic)
    id_str: str = ""
    type: str = ""
    modules: DynamicModule = Field(default_factory=DynamicModule)
    visible: bool = True
    orig: Optional['DynamicItem'] = None  # 转发原动态

    class Config:
        extra = "ignore"

    @property
    def dynamic_type(self) -> DynamicType:
        """获取动态类型枚举"""
        return DynamicType(self.type)

    @property
    def author(self) -> DynamicAuthor:
        """获取作者信息"""
        return self.modules.module_author

    @property
    def content(self) -> ModuleDynamic:
        """获取动态内容"""
        return self.modules.module_dynamic

    @property
    def stat(self) -> Optional[ModuleStat]:
        """获取统计信息"""
        return self.modules.module_stat

    @property
    def url(self) -> str:
        """动态链接"""
        return f"https://t.bilibili.com/{self.id_str}"


# 解决循环引用
DynamicItem.model_rebuild()


# === 动态列表响应 ===

class DynamicListData(BaseModel):
    """动态列表数据"""
    has_more: bool = False
    items: List[DynamicItem] = Field(default_factory=list)
    offset: str = ""
    update_baseline: str = ""
    update_num: int = 0

    class Config:
        extra = "ignore"
