import asyncio

import httpx

from infra.config.settings import settings
from infra.logger import logger
from .models import SearchRequest, SearchResponse


class SearchClient:

    def __init__(self):
        self.host = settings.WEB_SEARCH_URL
        self.api_key = settings.WEB_SEARCH_API_KEY
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"},
            base_url=self.host,
            timeout=httpx.Timeout(10),
        )

    async def search(self, query: str, count: int = 10) -> SearchResponse | None:
        url = "/v1/web-search"
        searchRequest = SearchRequest(query=query, count=(str(count)))
        payload = searchRequest.model_dump()

        try:
            response = await self.client.post(url=url, json=payload)
        except httpx.TimeoutException:
            logger.warn("Web Search", "Timeout")
            return None

        if response.status_code != 200:
            logger.warn("Web Search", f"Search Request failed. Code: "
                                      f"{response.status_code} Message: {response.json().get("msg")}")
            return None

        data = response.json()
        searchResponse = SearchResponse(**data.get("data"))

        return searchResponse

    async def fund_remaining(self) -> float | None:
        url = "/v1/fund/remaining"

        response = await self.client.get(url=url)

        if response.status_code != 200:
            logger.warn("Web Search", f"Remaining Request failed. Code: {response.status_code}")
            return None

        data = response.json().get("data")
        if data:
            return float(data.get("remaining"))

        logger.warn("Web Search", "Parsing Fund Remaining Failed")
        return None


async def main():
    client = SearchClient()
    fund = await client.fund_remaining()
    print(fund)
    searchResult = await client.search(query="百度")
    print(searchResult)

if __name__ == "__main__":
    asyncio.run(main())
