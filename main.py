import asyncio

from core.bot_core import Bot


async def main():
    bot = Bot.create()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
