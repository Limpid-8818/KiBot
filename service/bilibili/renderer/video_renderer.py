"""视频信息渲染器"""

from ..models.video import VideoInfo
from .base import BaseRenderer, RenderedContent


class VideoRenderer(BaseRenderer):
    """视频信息渲染器"""

    def render(self, video: VideoInfo) -> RenderedContent:
        """渲染视频详细信息"""
        stat = video.stat

        text = f"""📺 {video.title}

👤 UP主: {video.owner.name}
📁 分区: {video.tname}
⏱️ 时长: {video.duration_text}

📊 数据统计:
  ▶️ {self._format_num(stat.view)} 播放
  💬 {self._format_num(stat.danmaku)} 弹幕
  💰 {self._format_num(stat.coin)} 投币
  ⭐ {self._format_num(stat.favorite)} 收藏
  👍 {self._format_num(stat.like)} 点赞

📝 简介:
{video.desc[:200]}{'...' if len(video.desc) > 200 else ''}

🔗 {video.url}"""

        images = [video.pic] if video.pic else []

        # 添加视频卡片信息
        video_card = {
            "title": video.title,
            "desc": f"{video.owner.name} | {self._format_num(stat.view)}播放",
            "cover": video.pic,
            "url": video.url
        }

        return RenderedContent(text=text, images=images, video_card=video_card)

    @staticmethod
    def _format_num(num: int) -> str:
        """格式化数字"""
        if num >= 100000000:
            return f"{num / 100000000:.1f}亿"
        elif num >= 10000:
            return f"{num / 10000:.1f}万"
        return str(num)
