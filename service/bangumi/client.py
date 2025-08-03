import httpx
from typing import Optional, List

from infra.logger import logger
from .models import CalendarDay, Weekday, Subject, SubjectImage, SubjectRating


class BangumiClient:
    def __init__(self, base_url: str = "https://api.bgm.tv"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "KiBot/1.0 (https://github.com/Limpid-8818/KiBot.git)",
            "Accept": "application/json"
        }
        # Bangumi 官方的要求，不添加 User-Agent 可能会被拒绝，请参考 https://github.com/bangumi/api/blob/master/docs-raw/user%20agent.md
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(10, connect=5),
        )

    async def get_calendar(self) -> Optional[List[CalendarDay]]:
        """获取每日放送信息"""
        try:
            response = await self.client.get(f"{self.base_url}/calendar")
        except httpx.TimeoutException:
            logger.warn("Bangumi", "获取日历超时")
            return None
        except Exception as e:
            logger.warn("Bangumi", f"请求日历API时出错: {e}")
            return None

        if response.status_code != 200:
            logger.warn("Bangumi", f"获取日历失败: HTTP {response.status_code}")
            return None

        try:
            data = response.json()
        except Exception as e:
            logger.warn("Bangumi", f"JSON 解析失败: {e}")
            return None

        return self._parse_calendar(data)

    def _parse_calendar(self, data: List[dict]) -> List[CalendarDay]:
        """解析日历数据"""
        calendar = []
        
        for day_data in data:
            weekday = Weekday(
                en=day_data["weekday"]["en"],
                cn=day_data["weekday"]["cn"],
                ja=day_data["weekday"]["ja"],
                id=day_data["weekday"]["id"]
            )
            
            items = []
            for item_data in day_data["items"]:
                # 只处理动画类型 (type=2)
                if item_data.get("type") == 2:
                    subject = self._parse_subject(item_data)
                    if subject:
                        items.append(subject)
            
            calendar.append(CalendarDay(weekday=weekday, items=items))
        
        return calendar

    @staticmethod
    def _parse_subject(data: dict) -> Optional[Subject]:
        """解析条目数据"""
        try:
            # 检查必需字段
            required_fields = ["id", "url", "type", "name", "images"]
            for field in required_fields:
                if field not in data:
                    logger.warn("Bangumi", f"缺少必需字段: {field}")
                    return None
            
            images = SubjectImage(
                large=data["images"]["large"],
                common=data["images"]["common"],
                medium=data["images"]["medium"],
                small=data["images"]["small"],
                grid=data["images"]["grid"]
            )
            
            rating_data = data.get("rating", {})
            rating = SubjectRating(
                total=rating_data.get("total", 0),
                count=rating_data.get("count", {}),
                score=rating_data.get("score", 0.0)
            )
            
            return Subject(
                id=data["id"],
                url=data["url"],
                type=data["type"],
                name=data["name"],
                name_cn=data.get("name_cn", ""),
                summary=data.get("summary", ""),
                air_date=data.get("air_date", ""),
                air_weekday=data.get("air_weekday", 0),
                images=images,
                rating=rating,
                rank=data.get("rank", 0),
            )
        except Exception as e:
            logger.warn("Bangumi", f"解析条目数据时出错: {e}")
            return None
