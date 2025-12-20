"""
KiBot 主入口文件

支持 WebSocket 和 Webhook 两种模式，通过 CONNECTION_MODE 配置切换
"""
import asyncio

from infra.config.settings import Settings
from infra.logger import Logger


async def main():
    """主函数：初始化 Bot 并启动服务"""
    # 加载配置并初始化日志系统
    settings = Settings()
    Logger.configure(level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)

    # 延迟导入，确保日志系统已配置
    from core.bot_core import Bot

    # 创建 Bot 实例
    bot = Bot.create()

    # 启动定时推送任务
    bot.start_pusher()

    # 根据配置的连接模式启动服务
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        Logger.info("Main", "Received shutdown signal, exiting gracefully...")
    except Exception as e:
        Logger.error("Main", f"Unexpected error: {e}")
        raise
    finally:
        Logger.close()
