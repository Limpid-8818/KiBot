from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from infra.config.settings import settings
from service.llm.models import ChatMessage, ChatRequest, ChatResponse
from service.llm.prompts import prompts


class LLMService:
    def __init__(self):
        self.llm: Runnable = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            max_tokens=512,
            temperature=0.7,
            timeout=30.0,
            streaming=False,
        )

    @staticmethod
    def _to_lc_messages(msgs: list[ChatMessage]) -> list[SystemMessage | HumanMessage | AIMessage]:
        """Pydantic Model -> LangChain Message"""
        mapping = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage,
        }
        return [mapping[m.role](content=m.content) for m in msgs]

    async def chat(self, msg: str) -> ChatResponse:
        req = ChatRequest(
            messages=[
                ChatMessage(role="system", content=prompts.DEFAULT_SYSTEM_PROMPT),
                ChatMessage(role="user", content=msg),
            ],
        )
        lc_msgs = self._to_lc_messages(req.messages)
        response = await self.llm.ainvoke(lc_msgs)
        return ChatResponse(reply=response.content)
