# KiBot - 二次元风格 QQ 群智能机器人

“灵码杯”参赛作品

参赛赛道：智享生活

## 项目创意

相信有很多人都在B站或者是一些博客网站上看到过“教你自己部署一个QQ机器人”之类的教程，但绝大多数都是基于机器人框架的一键部署，并没有过于深入，功能也较为单一。因此我想要一个可扩展的，由大语言模型驱动的，真正能让群用户感觉智能的Bot，就好像真的是我们身边的一位群友。

KiBot（中文名 "希"）是一款具有二次元风格的 QQ 群智能机器人，希望打破传统群机器人的机械感，以活泼可爱的少女形象融入群聊氛围。其名字来源于日语中的 "希望（きぼう）"，象征着为群聊带来欢乐与帮助的愿景。

希拥有蓝白渐变色的头发和海蓝色的瞳色，身着蓝白色系的 JC 学生制服，性格开朗活泼，偶尔会害羞，善于使用网络热梗和二次元元素与群成员互动，建立轻松愉快的交流环境。（是的这是自设，求个绘画大神能把这个 OC 变成设定图

为了实现足够深度足够沉浸的群对话体验，避免使用显式的机器人指令调用服务，采用了 function calling，支持各种工具的调用，也能允许灵活配置自定义工具。带给群用户接近 Agent 的对话体验。

## 核心功能

1. **智能对话交互**：以自然、亲切的口语化表达与群成员交流，避免机械感
2. **文档检索（RAG）**：基于本地文档库进行知识查询，提供精准信息
3. **天气服务**：

- 获取指定城市今日天气
- 实时天气查询
- 天气预警信息推送

* 台风 / 热带风暴监测

4. **日程提醒**：支持在特殊节日推送推送祝福或提醒
5. **哔哩哔哩集成**：支持通过二维码登录 B 站，订阅up主更新推送

6. **Bangumi 集成**：支持推送新番信息

7. **function calling**：所有以上服务均支持用自然语言调用，对用户发言进行智能意图识别，并调用对应工具

## 技术栈

- **语言**：Python
- **机器人协议端框架**：NapCat（感谢这个框架，没有它就不会有这个项目的诞生，仓库地址：[NapNeko/NapCatQQ: Modern protocol-side framework based on NTQQ](https://github.com/NapNeko/NapCatQQ)）
- **自然语言处理**：langchain
- **向量存储**：FAISS
- **网络请求**：httpx, websockets
- **定时任务**：APScheduler
- **浏览器交互**：Playwright
- **二维码处理**：qrcode
- **数据验证**：Pydantic
- **embedding 服务**：Dashscope

## 项目结构

```
KiBot/
├── core/                  # 核心模块
│   ├── bot_core.py        # 机器人核心逻辑
|   ├── handler.py		   # 指令处理
|   ├── router.py		   # 指令分发
│   └── pusher/            # 推送服务，处理各类消息推送
│       ├── ......
│       └── pusher.py      # 推送器类实现
├── infra/ 				   # 全局静态工具与配置
|   ├── logger.py		   # 日志工具
|	└── config/			   # 配置
├── adapter/ 			   # 机器人协议端交互层
|	└── napcat/			   
│       ├── http_api.py    # 调用NapCat API
│       └── ws_client.py   # 接收上报信息
├── service/               # 业务服务模块
│   ├── rag/               # 文档检索服务
│   ├── llm/               # 大语言模型相关
│   │   ├── tools.py       # 工具定义，供LLM调用
│   │   ├── prompts/       # 提示词模板
│   │   └── chat.py        # 对话管理，处理LLM交互
│   ├── weather/           # 天气服务
│   ├── bangumi/ 		   # Bangumi服务
│   ├── calendar/		   # 日程服务
│   └── bilibili/          # B站相关功能
├── main.py                # 程序入口
├── .env				   # 项目环境变量 
└── requirements.txt       # 依赖列表
```

## 部署指南

1. 创建虚拟环境

```shell
python -m venv <venv_name>
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

2. 安装依赖

```shell
pip install -r requirements.txt
```

请注意，playwright 在安装后需要安装相关库并初始化，请在激活虚拟环境后执行：

```shell
playwright install
```

3. 配置 NapCatQQ

参考以下网站：[NapCat | NapCatQQ](https://napneko.github.io/guide/napcat)

启动 NapCatQQ 并登录机器人账号，配置 WebSocket 服务器和 Http 服务器

4. 配置项目环境变量

编辑 `.env` 文件

```
NAPCAT_WS=<NAPCAT WebSocket>
NAPCAT_HTTP=<NAPCAT HTTP>

LLM_BASE_URL=<LLM BASE URL>
LLM_API_KEY=<LLM API KEY>
LLM_MODEL=<LLM MODEL>

WEATHER_API_HOST=<和风天气 API HOST>
WEATHER_API_KEY=<和风天气 API KEY>

EMBEDDINGS_BASE_URL=<EMBEDDINGS BASE URL>
EMBEDDINGS_API_KEY=<EMBEDDINGS API KEY>
EMBEDDINGS_MODEL=<EMBEDDINGS MODEL>
```

5. 启动机器人

```shell
python main.py
```

## 使用说明

- 机器人加入群聊后，可直接 @机器人进行对话

- 日常聊天中会自动使用网络热梗和二次元元素（可能会有点尬，人设如此）

- 支持文档相关查询（需提前准备文档）

- 服务列表：

  - /天气

    ```
    /天气 [城市]         -> 实时天气
    /天气 预警 [城市]     -> 预警信息
    /天气 台风           -> 实时台风信息
    /天气 订阅 [城市]     -> 添加订阅城市
    /天气 取消订阅 [城市]  -> 删除订阅城市
    ```

  - /番剧

    ```
    /番剧 今日放送		-> 今日更新番剧
    /番剧 订阅			 -> 订阅番剧更新推送
    /番剧 取消订阅		-> 取消订阅
    ```

  - /B站
  
    ```
    /b站 订阅 [uid]	-> 订阅up主更新
    /b站 取消订阅 [uid] -> 取消订阅
    /b站 检查 [uid]	-> 检查更新
    ```

* function calling 目前支持天气服务和RAG服务："@机器人 北京今天天气怎么样？"

* Bot 人设自定义：按自己的喜好修改 `service/llm/prompts/prompts.py` 中的 `DEFAULT_SYSTEM_PROMPT` 即可

## 扩展功能

1. 在 `service` 目录下创建新的功能模块目录
2. 实现功能核心逻辑，遵循现有模块的设计模式
3. 在 `core/router.py` 中注册指令路由
4. 在 `core/handler.py` 中编写指令处理及回复逻辑
5. 在 `service/llm/tools.py` 中注册新功能作为工具
6. 编写单元测试并验证功能

## 贡献指南

欢迎通过以下方式贡献项目：

1. 提交 issue 报告 bug 或提出功能建议
2. 提交 pull request 改进代码
3. 完善此文档
4. 分享使用经验
