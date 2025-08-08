import asyncio
from typing import List, Literal, Optional, Dict, Any, Callable, Union, Awaitable
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = Field(...)
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    usage: Optional[dict] = None


class Tool(BaseModel):
    """工具定义模型，描述可用的工具及其参数"""
    name: str = Field(..., description="工具名称，必须唯一")
    description: str = Field(..., description="工具功能描述，用于让模型决定是否使用")
    parameters: Dict[str, Any] = Field(..., description="工具参数的JSON Schema定义")
    func: Union[Callable, Callable[..., Awaitable[Any]]] = Field(..., description="工具对应的实现函数（同步或异步）")

    def get_definition(self) -> Dict[str, Any]:
        """返回工具的定义字典，用于构建提示词"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

    async def invoke(self, parameters: Dict[str, Any]) -> Any:
        """调用工具函数并返回结果"""
        # 检查函数是否为异步函数
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**parameters)
        else:
            return self.func(**parameters)


class ToolCallResult(BaseModel):
    """工具调用结果模型"""
    tool_name: str
    parameters: Dict[str, Any]
    success: bool
    result: Any
    error: Optional[str] = None


class ToolCallPlan(BaseModel):
    """单个工具调用计划"""
    tool_name: str = Field(..., description="要调用的工具名称")
    tool_parameters: Dict[str, Any] = Field(..., description="工具调用参数")


class IntentRecognitionResult(BaseModel):
    """意图识别结果模型"""
    should_call_tool: bool = Field(..., description="是否需要调用工具")
    tool_calls: List[ToolCallPlan] = Field(default_factory=list, description="工具调用计划列表")
    confidence: float = Field(..., description="识别置信度，0-1之间")
