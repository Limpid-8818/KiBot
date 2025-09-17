from typing import Optional, Dict, List

from service.llm.models import Tool, IntentRecognitionResult, ToolCallResult
from service.rag.service import RAGService
from service.search.service import SearchService
from service.weather.models import WeatherResponse, StormResponse, StormItem, StormInfo
from service.weather.service import WeatherService


class ToolManager:
    def __init__(self):
        self.tools: Optional[Dict[str, Tool]] = {
            "rag_query": Tool(
                name="rag_query",
                description="使用文档检索系统查询相关知识，当需要回答基于特定文档的问题时使用",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询的问题或关键词"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "返回的相关文档数量，默认3",
                            "minimum": 1,
                            "maximum": 5
                        }
                    },
                    "required": ["query"]
                },
                func=rag_query
            ),
            "get_today_weather": Tool(
                name="get_today_weather",
                description="获取指定城市今天的天气信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["city"]
                },
                func=get_today_weather
            ),
            "get_now_weather": Tool(
                name="get_now_weather",
                description="获取指定城市的实时天气信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["city"]
                },
                func=get_now_weather
            ),
            "get_weather_warning": Tool(
                name="get_weather_warning",
                description="获取指定城市实时发布的天气预警信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["city"]
                },
                func=get_weather_warning
            ),
            "get_active_storms": Tool(
                name="get_active_storms",
                description="获取目前西北太平洋正在活跃的台风/热带风暴的信息",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                func=get_active_storms
            ),
            "web_search": Tool(
                name="web_search",
                description="检索网络上的相关文本内容，返回搜索结果中的文字片段，适用于需要最新信息或需要网络知识的情况",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索的关键词或问题"
                        },
                        "count": {
                            "type": "integer",
                            "description": "返回的结果数量，默认10",
                            "minimum": 10,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                },
                func=web_search
            ),
            "show_functions": Tool(
                name="show_functions",
                description="当用户询问机器人有什么功能、能做什么、可以提供哪些帮助时，或用户可能需要使用帮助时，"
                            "或用户询问是否拥有某功能、能否做到某事时，调用此工具获取功能介绍",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                func=show_functions
            )
        }

    async def call_tools(self, recognition_result: IntentRecognitionResult) -> List[ToolCallResult]:
        results = []
        if not recognition_result.should_call_tool or not recognition_result.tool_calls:
            results.append(ToolCallResult(
                tool_name="",
                parameters={},
                success=False,
                result=None,
                error="无需调用工具"
            ))
            return results

        for call_plan in recognition_result.tool_calls:
            tool_name = call_plan.tool_name
            if tool_name not in self.tools:
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    parameters=call_plan.tool_parameters or {},
                    success=False,
                    result=None,
                    error=f"工具不存在: {tool_name}"
                ))
                continue

            try:
                tool = self.tools[tool_name]
                result = await tool.invoke(call_plan.tool_parameters or {})
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    parameters=call_plan.tool_parameters or {},
                    success=True,
                    result=result
                ))
            except Exception as e:
                results.append(ToolCallResult(
                    tool_name=tool_name,
                    parameters=call_plan.tool_parameters or {},
                    success=False,
                    result=None,
                    error=str(e)
                ))

        return results


async def rag_query(query: str, top_k: int = 3) -> str:
    try:
        rag_service = RAGService()
        results = rag_service.query(query, top_k)

        if not results:
            raise Exception("未找到相关文档信息")

        formatted_result = "找到以下相关信息：\n"
        for i, doc in enumerate(results, 1):
            formatted_result += f"\n【相关片段 {i}】\n{doc['content']}\n"

        return formatted_result
    except Exception as e:
        raise Exception(f"查询失败：{str(e)}")


async def get_today_weather(city: str) -> str:
    weather_service = WeatherService()
    try:
        location_valid = await weather_service.check_location(city)
        if not location_valid:
            raise Exception(f"错误：无法识别城市 '{city}'，请检查城市名称是否正确")

        weather_response: Optional[WeatherResponse] = await weather_service.get_today(city)
        if not weather_response:
            raise Exception(f"错误：无法获取城市 '{city}' 今天的天气信息")

        location = weather_response.location
        daily_forecast = weather_response.daily[0] if weather_response.daily else None
        if not daily_forecast:
            raise Exception(f"错误：未获取到 '{location.name}' 今天的具体天气预报")

        # 格式化天气信息
        return (
            f"{location.name} 今天的天气情况：\n"
            f"天气状况：日间{daily_forecast.textDay} / 夜间{daily_forecast.textNight}\n"
            f"气温范围：{daily_forecast.tempMin}°C ~ {daily_forecast.tempMax}°C\n"
            f"风向风力：{daily_forecast.windDirDay} {daily_forecast.windScaleDay}级"
        )

    except Exception as e:
        # 捕获并处理所有可能的异常
        raise Exception(f"获取天气信息时发生错误：{str(e)}")


async def get_now_weather(city: str) -> str:
    weather_service = WeatherService()
    try:
        location_valid = await weather_service.check_location(city)
        if not location_valid:
            raise Exception(f"错误：无法识别城市 '{city}'，请检查城市名称是否正确")

        weather_response: Optional[WeatherResponse] = await weather_service.get_now(city)
        if not weather_response:
            raise Exception(f"错误：无法获取城市 '{city}' 的实时天气信息")

        location = weather_response.location
        weather_now = weather_response.now if weather_response.now else None
        if not weather_now:
            raise Exception(f"错误：未获取到 '{location.name}' 的实时天气信息")

        # 格式化天气信息
        return (
            f"{location.name} 实时天气\n"
            f"温度：{weather_now.temp}°C（体感 {weather_now.feelsLike}°C）\n"
            f"天气：{weather_now.text}\n"
            f"湿度：{weather_now.humidity}%\n"
            f"风力：{weather_now.windDir} {weather_now.windScale} 级"
        )

    except Exception as e:
        # 捕获并处理所有可能的异常
        raise Exception(f"获取实时天气信息时发生错误：{str(e)}")


async def get_weather_warning(city: str) -> str:
    weather_service = WeatherService()
    try:
        location_valid = await weather_service.check_location(city)
        if not location_valid:
            raise Exception(f"错误：无法识别城市 '{city}'，请检查城市名称是否正确")

        warning_response = await weather_service.get_warning(city)
        if not warning_response:
            raise Exception(f"错误：无法获取城市 '{city}' 的天气预警信息")

        location = warning_response.location
        weather_warning = warning_response.warningInfo if warning_response.warningInfo else None
        if not weather_warning:
            raise Exception(f"错误：未获取到 '{location.name}' 的天气预警信息")

        alerts = "\n".join([f"{w.title}\n{w.text}" for w in warning_response.warningInfo])
        return f"{city}的实时天气预警\n{alerts}"

    except Exception as e:
        raise Exception(f"获取实时天气预警信息时发生错误：{str(e)}")


async def get_active_storms() -> str:
    weather_service = WeatherService()
    try:
        # 调用天气服务获取活跃热带风暴列表
        storm_responses: Optional[List[StormResponse]] = await weather_service.get_storm()

        if not storm_responses:
            return "当前西北太平洋没有活跃的台风/热带风暴信息"

        result = ["当前活跃台风/热带风暴信息：\n"]

        for idx, storm_resp in enumerate(storm_responses, 1):
            storm: StormItem = storm_resp.storm
            info: StormInfo = storm_resp.stormInfo

            # 风暴类型映射
            storm_type_map = {
                "TD": "热带低压",
                "TS": "热带风暴",
                "STS": "强热带风暴",
                "TY": "台风",
                "STY": "强台风",
                "SuperTY": "超强台风"
            }

            # 方向映射
            dir_map = {
                "N": "北", "NNE": "东北偏北", "NE": "东北", "ENE": "东北偏东",
                "E": "东", "ESE": "东南偏东", "SE": "东南", "SSE": "东南偏南",
                "S": "南", "SSW": "西南偏南", "SW": "西南", "WSW": "西南偏西",
                "W": "西", "WNW": "西北偏西", "NW": "西北", "NNW": "西北偏北"
            }

            result.append(
                f"{idx}. {storm.name}\n"
                f"   类型：{storm_type_map.get(info.type, info.type)}\n"
                f"   位置：纬度 {info.lat}，经度 {info.lon}\n"
                f"   中心气压：{info.pressure} hPa\n"
                f"   最大风速：{info.windSpeed} m/s\n"
                f"   移动方向：{dir_map.get(info.moveDir, info.moveDir)}（{info.move360}°）\n"
                f"   移动速度：{info.moveSpeed} km/h\n"
                f"   发布时间：{info.pubTime}\n"
            )

        return "\n".join(result)

    except Exception as e:
        raise Exception(f"获取风暴信息时发生错误：{str(e)}")


async def web_search(query: str, count: int = 10) -> str:
    try:
        search_service = SearchService()

        # 调用search_for_text方法获取文本片段列表
        text_summaries = await search_service.search_for_text(query, count)

        if not text_summaries:
            raise Exception(f"未找到与 '{query}' 相关的文本内容")

        # 格式化结果
        result = [f"与 '{query}' 相关的搜索结果："]
        for i, snippet in enumerate(text_summaries, 1):
            result.append(f"\n【结果 {i}】\n{snippet}")

        return "\n".join(result)

    except Exception as e:
        raise Exception(f"搜索文本内容时发生错误：{str(e)}")


def show_functions() -> str:
    """返回机器人可用功能的介绍"""
    try:
        functions = """
    目前可以提供这些帮助哦：
    1. 日常聊天：陪你闲聊各种话题，分享趣事和梗~
    2. 天气服务：查询实时天气、今日天气、天气预警，还有台风信息呢
    3. 文档查询：在知识库中检索特定文档中的相关知识
    4. 网络搜索：获取最新的网络信息和内容
    5. 番剧服务：查询今日番剧放送信息，订阅每日推送
    6. B站服务：订阅UP主动态，及时获取更新提醒
    
    查询详细使用方法请@我+输入/帮助
        """
        return functions.strip()
    except Exception as e:
        raise Exception(f"获取功能列表失败：{str(e)}")
