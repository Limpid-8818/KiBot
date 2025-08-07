import asyncio
import json
from typing import Dict, Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from infra.config.settings import settings
from infra.logger import logger
from service.llm.models import ChatMessage, ChatRequest, ChatResponse, IntentRecognitionResult
from service.llm.prompts import prompts
from service.llm.tools import ToolManager


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
        self.tool_manager = ToolManager()
        self.intent_chain: Runnable = self._build_intent_chain()
        self.session_store: Dict[str, CustomConversationSummaryMemory] = {}

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

    async def chat_with_memory(self, msg: str, session_id: str, user_id: str) -> ChatResponse:
        if session_id not in self.session_store:
            self.session_store[session_id] = CustomConversationSummaryMemory(self.llm)

        memory = self.session_store[session_id]
        summary = memory.load_summary()

        prompt_template = """
                {system_prompt}

                对话历史摘要:
                {chat_history}

                当前输入: {input}
                
                输入包含用户id，但你无需在回复内容中包含类似结构（不用在开头加“希：”）
                """
        prompt = PromptTemplate(
            input_variables=["system_prompt", "chat_history", "input"],
            template=prompt_template
        )

        chain = prompt | self.llm
        response = await chain.ainvoke({
            "system_prompt": prompts.DEFAULT_SYSTEM_PROMPT,
            "chat_history": summary,
            "input": f"{user_id}: {msg}"
        })

        memory.save_context(f"{user_id}: {msg}", response.content)
        memory.update_summary()  # 更新摘要

        return ChatResponse(reply=response.content)

    async def generate_greeting(self, msg: str) -> ChatResponse:
        prompt = PromptTemplate.from_template(prompts.GREETING_PROMPT).format(content=msg)
        req = ChatRequest(
            messages=[
                ChatMessage(role="system", content=prompt),
            ],
        )
        lc_msgs = self._to_lc_messages(req.messages)
        response = await self.llm.ainvoke(lc_msgs)
        return ChatResponse(reply=response.content)

    async def agent_chat(self, msg: str) -> ChatResponse:
        prompt_template = """
                {system_prompt}
                
                {input}
                
                {tool_calling}
        """
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["system_prompt", "input", "tool_calling"],
        )
        chain = prompt | self.llm

        ir_output = await self.intent_chain.ainvoke({"user_query": msg})
        ir_result = IntentRecognitionResult(**ir_output)
        logger.info("LLM Tool Calling", f"意图识别结果: {ir_output}")
        if ir_result.should_call_tool and ir_result.tool_name:
            tool_calling_result = await self.tool_manager.call_tool(ir_result)
            if tool_calling_result.success:
                tool_calling_text = self._format_tool_success_response(tool_calling_result.tool_name,
                                                                       tool_calling_result.result)
            else:
                tool_calling_text = self._format_tool_error_response(tool_calling_result.tool_name,
                                                                     tool_calling_result.error)
            logger.info("LLM Tool Calling", tool_calling_text)
        else:
            tool_calling_text = ""

        response = await chain.ainvoke({
            "system_prompt": prompts.DEFAULT_SYSTEM_PROMPT,
            "input": msg,
            "tool_calling": tool_calling_text,
        })

        return ChatResponse(reply=response.content)

    # 格式化工具调用成功的响应
    @staticmethod
    def _format_tool_success_response(tool_name: str, result: Any) -> str:
        return f"通过工具「{tool_name}」获取结果：\n{str(result)}"

    # 格式化工具调用失败的响应
    @staticmethod
    def _format_tool_error_response(tool_name: str, error: str) -> str:
        return f"工具「{tool_name}」调用失败：\n{error}"

    def _build_intent_chain(self) -> Runnable:
        tools_definition = json.dumps([tool.get_definition() for tool in self.tool_manager.tools.values()],
                                      ensure_ascii=False, indent=2)

        prompt = PromptTemplate(
            template=prompts.FUNCTION_CALLING_INTENT_PROMPT,
            input_variables=["tools", "user_query"],
            partial_variables={"tools": tools_definition},
        )

        judge_llm = ChatOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            max_tokens=512,
            temperature=0.1,  # 使用更低的temperature保证更低的随机性
            timeout=30.0,
            streaming=False,
        )

        parser = JsonOutputParser(pydantic_object=IntentRecognitionResult)

        chain = prompt | judge_llm | parser

        return chain


class CustomConversationSummaryMemory:
    def __init__(self, llm: Runnable):
        self.llm = llm
        self.message_history = InMemoryChatMessageHistory()
        self.summary = ""

    def save_context(self, input_msg: str, output_msg: str):
        self.message_history.add_user_message(input_msg)
        self.message_history.add_ai_message(output_msg)

    def load_summary(self) -> str:
        return self.summary

    def update_summary(self):
        # 将当前摘要和新对话合并，生成新的摘要
        messages = self.message_history.messages
        if self.summary:
            # 如果已有摘要，将摘要和新对话合并
            combined_messages = f"{self.summary}\n" + "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
        else:
            # 如果没有摘要，直接使用新对话
            combined_messages = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])

        summary_prompt = PromptTemplate(
            input_variables=["messages"],
            template="总结以下的对话内容形成最多200字的摘要，摘要需要尽可能保留对话的关键信息，请注意要明确根据数字（用户id）来区分不同用户所说的内容:\n{messages}"
        )
        summary_request = summary_prompt.format(
            messages=combined_messages
        )
        summary_response = self.llm.invoke([SystemMessage(content=summary_request)])
        self.summary = summary_response.content
        self.message_history.clear()  # 清空当前对话历史，准备下一轮对话


async def test():
    svc = LLMService()
    res = await svc.agent_chat("能帮我查查北京现在有没有什么气象预警消息吗")
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
