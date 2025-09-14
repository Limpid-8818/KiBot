import os
import sys
from datetime import datetime
from typing import Literal

Level = Literal["DEBUG", "INFO", "WARN", "ERROR"]


class _ColoredFormatter:
    _colors = {
        "DEBUG": "\033[36m",  # 青
        "INFO": "\033[32m",  # 绿
        "WARN": "\033[33m",  # 黄
        "ERROR": "\033[31m",  # 红
        "RESET": "\033[0m",
    }

    @classmethod
    def colorize(cls, level: Level, text: str) -> str:
        return f"{cls._colors[level]}{text}{cls._colors['RESET']}"


class Logger:
    _level_rank = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
    _current_level = _level_rank.get(os.getenv("LOG_LEVEL", "INFO").upper(), 1)

    @classmethod
    def _log(cls, level: Level, module: str, msg: str):
        if cls._level_rank[level] < cls._current_level:
            return
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [{level}] {module} | {msg}"
        colored = _ColoredFormatter.colorize(level, line)
        print(colored, file=sys.stderr)

    @staticmethod
    def debug(module: str, msg: str):
        Logger._log("DEBUG", module, msg)

    @staticmethod
    def info(module: str, msg: str):
        Logger._log("INFO", module, msg)

    @staticmethod
    def warn(module: str, msg: str):
        Logger._log("WARN", module, msg)

    @staticmethod
    def error(module: str, msg: str):
        Logger._log("ERROR", module, msg)


logger = Logger
