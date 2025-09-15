from typing import Optional, List

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    freshness: Optional[str] = 'noLimit'
    summary: Optional[bool] = True
    include: Optional[str] = None
    exclude: Optional[str] = None
    count: Optional[int] = 10


class SearchResponse(BaseModel):
    _type: str = 'SearchResponse'
    queryContext: "WebSearchQueryContext"
    webPages: "WebSearchWebPages"


class WebSearchQueryContext(BaseModel):
    originalQuery: str


class WebSearchWebPages(BaseModel):
    webSearchUrl: str
    totalEstimatedMatches: int
    value: List["WebPageValue"]
    someResultsRemoved: bool


class WebPageValue(BaseModel):
    id: str
    name: str
    url: str
    displayUrl: str
    snippet: str
    summary: Optional[str] = None
    siteName: str
    siteIcon: str
    datePublished: str
    cachedPageUrl: Optional[str] = None
    language: Optional[str] = None
    isFamilyFriendly: Optional[bool] = None
    isNavigational: Optional[bool] = None
