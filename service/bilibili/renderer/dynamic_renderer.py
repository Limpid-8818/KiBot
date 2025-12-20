"""动态内容渲染器"""

from ..models.dynamic import DynamicItem, DynamicType
from .base import BaseRenderer, RenderedContent


class DynamicRenderer(BaseRenderer):
    """动态内容渲染器"""

    def render(self, dynamic: DynamicItem) -> RenderedContent:
        """根据动态类型分发渲染"""
        handlers = {
            DynamicType.AV: self._render_video,
            DynamicType.DRAW: self._render_draw,
            DynamicType.WORD: self._render_word,
            DynamicType.FORWARD: self._render_forward,
            DynamicType.ARTICLE: self._render_article,
            DynamicType.MUSIC: self._render_music,
            DynamicType.COMMON: self._render_common,
            DynamicType.PGC: self._render_pgc,
            DynamicType.UGC_SEASON: self._render_ugc_season,
        }

        dynamic_type = dynamic.dynamic_type
        handler = handlers.get(dynamic_type, self._render_unknown)
        return handler(dynamic)

    def _render_header(self, dynamic: DynamicItem) -> str:
        """渲染动态头部（作者信息）"""
        author = dynamic.author
        action = author.pub_action or "发布了动态"
        time_str = author.pub_time or ""
        return f"🔔 {author.name} {action}\n⏰ {time_str}\n"

    def _render_video(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染视频动态"""
        header = self._render_header(dynamic)
        major = dynamic.content.major
        if not major or not major.archive:
            return self._render_unknown(dynamic)

        archive = major.archive
        stat = archive.stat

        text = f"""{header}
📺 {archive.title}
⏱️ 时长: {archive.duration_text}
▶️ {stat.play} 播放 | 💬 {stat.danmaku} 弹幕

📝 {archive.desc[:100]}{'...' if len(archive.desc) > 100 else ''}

🔗 {archive.url}"""

        images = [archive.cover] if archive.cover else []

        # 添加视频卡片信息，用于生成分享卡片
        video_card = {
            "title": archive.title,
            "desc": f"{stat.play} 播放 | {archive.duration_text}",
            "cover": archive.cover,
            "url": archive.url
        }

        return RenderedContent(text=text, images=images, video_card=video_card)

    def _render_draw(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染图文动态（支持 MAJOR_TYPE_OPUS 和旧版 MAJOR_TYPE_DRAW）"""
        header = self._render_header(dynamic)
        desc = dynamic.content.desc.text if dynamic.content.desc else ""
        major = dynamic.content.major

        # 优先使用新版 MAJOR_TYPE_OPUS 格式
        if major and major.opus:
            opus = major.opus
            # 使用 opus 的摘要文本，如果没有则使用 desc
            content_text = opus.text or desc
            title_line = f"📰 {opus.title}\n\n" if opus.title else ""

            text = f"""{header}
{title_line}📝 {content_text}

🖼️ 共 {len(opus.pics)} 张图片

🔗 {dynamic.url}"""

            # 最多取前4张图片
            images = opus.images[:4]
            return RenderedContent(text=text, images=images)

        # 兼容旧版 MAJOR_TYPE_DRAW 格式
        if major and major.draw:
            draw = major.draw
            text = f"""{header}
📝 {desc}

🖼️ 共 {len(draw.items)} 张图片

🔗 {dynamic.url}"""

            # 最多取前4张图片
            images = [item.src for item in draw.items[:4]]
            return RenderedContent(text=text, images=images)

        # 如果都没有，降级为纯文字渲染
        return self._render_word(dynamic)

    def _render_word(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染纯文字动态"""
        header = self._render_header(dynamic)
        desc = dynamic.content.desc.text if dynamic.content.desc else ""

        text = f"""{header}
📝 {desc}

🔗 {dynamic.url}"""

        return RenderedContent(text=text)

    def _render_forward(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染转发动态"""
        header = self._render_header(dynamic)
        desc = dynamic.content.desc.text if dynamic.content.desc else ""

        # 渲染原动态
        orig_content = ""
        orig_images = []
        if dynamic.orig:
            orig_rendered = self.render(dynamic.orig)
            orig_content = f"\n━━━ 原动态 ━━━\n{orig_rendered.text}"
            orig_images = orig_rendered.images

        text = f"""{header}
💬 {desc}
{orig_content}"""

        return RenderedContent(text=text, images=orig_images)

    def _render_article(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染专栏文章动态"""
        header = self._render_header(dynamic)
        major = dynamic.content.major

        if not major or not major.article:
            return self._render_unknown(dynamic)

        article = major.article
        text = f"""{header}
📑 {article.title}

📝 {article.desc[:150]}{'...' if len(article.desc) > 150 else ''}

🔗 {article.url}"""

        images = article.covers[:1] if article.covers else []
        return RenderedContent(text=text, images=images)

    def _render_music(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染音乐动态"""
        header = self._render_header(dynamic)
        major = dynamic.content.major

        if not major or not major.music:
            return self._render_unknown(dynamic)

        music = major.music
        text = f"""{header}
🎵 {music.title}

🔗 {music.url}"""

        images = [music.cover] if music.cover else []
        return RenderedContent(text=text, images=images)

    def _render_common(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染通用卡片动态"""
        header = self._render_header(dynamic)
        major = dynamic.content.major

        if not major or not major.common:
            return self._render_unknown(dynamic)

        common = major.common
        text = f"""{header}
📌 {common.title}

📝 {common.desc}

🔗 {common.jump_url}"""

        images = [common.cover] if common.cover else []
        return RenderedContent(text=text, images=images)

    def _render_pgc(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染番剧/影视动态"""
        header = self._render_header(dynamic)
        major = dynamic.content.major

        if not major or not major.pgc:
            return self._render_unknown(dynamic)

        pgc = major.pgc
        text = f"""{header}
🎬 {pgc.title}

🔗 {pgc.jump_url}"""

        images = [pgc.cover] if pgc.cover else []
        return RenderedContent(text=text, images=images)

    def _render_ugc_season(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染合集动态"""
        header = self._render_header(dynamic)

        # 合集结构较复杂，使用通用渲染
        text = f"""{header}
📚 合集更新

🔗 {dynamic.url}"""

        return RenderedContent(text=text)

    def _render_unknown(self, dynamic: DynamicItem) -> RenderedContent:
        """渲染未知类型动态"""
        header = self._render_header(dynamic)

        text = f"""{header}
⚠️ 暂不支持的动态类型: {dynamic.type}

🔗 {dynamic.url}"""

        return RenderedContent(text=text)
