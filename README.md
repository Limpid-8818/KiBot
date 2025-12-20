<div style="text-align: center; background-color: white; padding: 20px; border-radius: 30px;">
  <img src="./static/kibot_logo.png" alt="KiBot Logo" width="200" style="display: block; margin: 0 auto;">
  <h1 style="color: black; margin: 0; font-size: 3em;">KiBot - 二次元风格 QQ 群 Agent</h1>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/NapCat-Supported-purple.svg" alt="NapCat">
</p>

## 项目简介

KiBot（中文名 "希"）是一个具有二次元风格的 QQ 群智能机器人，希望打破传统群机器人的机械感，以活泼可爱的少女形象融入群聊氛围。其名字来源于日语中的 "希望（きぼう）"，象征着为群聊带来欢乐与帮助的愿景。

希拥有蓝白渐变色的头发和海蓝色的瞳色，身着蓝白色系的 JC 学生制服，性格开朗活泼，偶尔会害羞，善于使用网络热梗和二次元元素与群成员互动。

## 核心功能

| 功能 | 描述 |
|------|------|
| 🤖 **智能对话** | 基于 LLM 的自然语言交互，支持 Function Calling |
| 📚 **文档检索 (RAG)** | 基于 FAISS 的本地文档知识库查询 |
| 🌤️ **天气服务** | 实时天气、预警信息、台风监测、定时推送 |
| 📺 **番剧追踪** | Bangumi 集成，新番更新推送 |
| 📱 **B站集成** | UP主动态订阅、直播开播提醒 |
| 📅 **日程提醒** | 节假日祝福、特殊日期提醒 |

## 技术栈

- **语言**: Python 3.11+
- **包管理**: [uv](https://github.com/astral-sh/uv)
- **Web 框架**: FastAPI + uvicorn
- **协议端框架**: [NapCatQQ](https://github.com/NapNeko/NapCatQQ)
- **LLM 框架**: [LangChain](https://github.com/langchain-ai/langchain)
- **向量存储**: FAISS
- **网络请求**: httpx, websockets
- **定时任务**: APScheduler
- **数据验证**: Pydantic

## 项目结构

```
KiBot/
├── main.py                    # 程序入口
├── core/                      # 核心模块
│   ├── bot_core.py            # Bot 类，组装所有组件
│   ├── handler.py             # 业务逻辑处理
│   ├── router.py              # 消息路由与命令分发
│   └── pusher/                # 定时推送服务
│       ├── pusher.py
│       ├── weather_scheduler.py
│       ├── bangumi_scheduler.py
│       ├── bilibili_scheduler.py
│       └── live_scheduler.py
├── adapter/                   # 协议适配层
│   └── napcat/
│       ├── webhook_server.py  # Webhook 服务器
│       ├── ws_client.py       # WebSocket 客户端
│       ├── http_api.py        # NapCat HTTP API
│       └── models.py          # 事件模型
├── service/                   # 业务服务
│   ├── llm/                   # LLM 对话服务
│   ├── rag/                   # 文档检索服务
│   ├── weather/               # 天气服务
│   ├── bangumi/               # 番剧服务
│   ├── bilibili/              # B站服务
│   ├── calendar/              # 日历服务
│   └── search/                # 联网搜索服务
├── infra/                     # 基础设施
│   ├── logger.py              # 日志工具
│   └── config/
│       └── settings.py        # 配置管理
├── .github/                   # GitHub 模板
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── pyproject.toml             # 项目配置
└── .env.example               # 环境变量示例
```

## 快速开始

### 环境要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (推荐) 或 pip
- NapCatQQ

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/Yokumii/KiBot.git
cd KiBot
```

2. **安装依赖**

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

3. **配置 NapCatQQ**

参考官方文档：[NapCat 配置指南](https://napneko.github.io/guide/napcat)

启动 NapCatQQ 并登录机器人账号，根据连接模式配置：

- **Webhook 模式**：配置 HTTP 服务器 + Webhook 上报
- **WebSocket 模式**：配置 HTTP 服务器 + WebSocket 服务器

4. **配置环境变量**

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 日志配置
LOG_LEVEL=INFO                    # DEBUG, INFO, WARN, ERROR
LOG_FILE=                         # 日志文件路径（可选）

# 连接模式
CONNECTION_MODE=webhook           # webhook 或 websocket

# NapCat WebSocket（websocket 模式）
NAPCAT_WS=ws://127.0.0.1:3001
NAPCAT_WS_AUTH_TOKEN=your_token

# NapCat HTTP API（两种模式都需要）
NAPCAT_HTTP=http://127.0.0.1:3000
NAPCAT_HTTP_AUTH_TOKEN=your_token

# Webhook 配置（webhook 模式）
NAPCAT_WEBHOOK_SECRET=your_secret
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=8000

# LLM 服务
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4o

# 和风天气 API
WEATHER_API_HOST=https://devapi.qweather.com
WEATHER_API_KEY=your_api_key

# Embeddings（RAG 功能）
EMBEDDINGS_BASE_URL=your_base_url
EMBEDDINGS_API_KEY=your_api_key
EMBEDDINGS_MODEL=your_model

# 联网搜索（可选）
WEB_SEARCH_URL=your_search_url
WEB_SEARCH_API_KEY=your_api_key
```

5. **启动机器人**

```bash
uv run python main.py
# 或
python main.py
```

## 使用说明

### 基础交互

- 在群聊中 @机器人 即可开始对话
- 支持自然语言调用各种服务（Function Calling）

### 命令列表

#### 天气服务 `/天气`

```
/天气 [城市]           实时天气查询
/天气 预警 [城市]       天气预警信息
/天气 台风             实时台风监测
/天气 订阅 [城市]       订阅天气推送
/天气 取消订阅 [城市]   取消订阅
```

#### 番剧服务 `/番剧`

```
/番剧 今日放送          今日更新番剧
/番剧 订阅             订阅番剧更新推送
/番剧 取消订阅          取消订阅
```

#### B站服务 `/b站`

```
/b站 订阅 [UID]         订阅UP主动态
/b站 取消订阅 [UID]     取消订阅动态
/b站 检查 [UID]         检查最新动态
/b站 直播订阅 [UID]     订阅直播开播提醒
/b站 直播取消 [UID]     取消直播订阅
/b站 直播列表           查看直播订阅列表
/b站 登录               扫码登录B站账号
```

#### 帮助 `/帮助`

```
/帮助                   查看帮助信息
```

### 自然语言调用

无需记忆命令，直接 @机器人 用自然语言交流：

- "北京今天天气怎么样？"
- "帮我查一下台风路径"
- "今天有什么新番更新？"

### 自定义人设

修改 `service/llm/prompts/prompts.py` 中的 `DEFAULT_SYSTEM_PROMPT` 即可自定义机器人人设。

## 扩展开发

### 添加新功能模块

1. 在 `service/` 目录下创建新模块
2. 实现核心业务逻辑
3. 在 `core/router.py` 中注册命令路由
4. 在 `core/handler.py` 中编写处理逻辑
5. 在 `service/llm/tools.py` 中注册为 LLM 工具（可选）

### 连接模式说明

| 模式 | 优点 | 适用场景 |
|------|------|----------|
| **Webhook** | 无需长连接，资源占用低 | 公网服务器部署 |
| **WebSocket** | 实时性更好，配置简单 | 本地部署、内网环境 |

## 贡献者

<a href=" ">
  <img src="https://contrib.rocks/image?repo=Limpid-8818/KiBot" />
</a>

## 贡献指南

欢迎贡献代码！请查看 [Issue 模板](.github/ISSUE_TEMPLATE) 和 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 致谢

- [NapCatQQ](https://github.com/NapNeko/NapCatQQ) - 现代化的 QQ 协议端框架
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用开发框架
- [和风天气](https://www.qweather.com/) - 天气数据服务
- [Bangumi](https://bangumi.tv/) - 番剧数据来源

## License

[MIT License](LICENSE)
