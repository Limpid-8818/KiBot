from typing import List, Optional

from .client import SearchClient
from .models import WebPageValue


class SearchService:
    def __init__(self):
        self.client = SearchClient()

    async def search(self, query: str, count: int = 10) -> List[WebPageValue]:
        response = await self.client.search(query, count=count)

        if response and response.webPages and response.webPages.value:
            return response.webPages.value
        return []

    async def search_for_text(self, query: str, count: int = 10) -> List[str]:
        results = await self.search(query, count=count)
        # 提取所有结果中的 summary 字段，并过滤可能存在的空值
        return [result.summary for result in results if result.summary]

    async def get_remaining_funds(self) -> Optional[float]:
        return await self.client.fund_remaining()
