import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, TextIO

Level = Literal["DEBUG", "INFO", "WARN", "ERROR"]


class _ColoredFormatter:
    _colors = {
        "DEBUG": "\033[36m",  # 青
        "INFO": "\033[32m",   # 绿
        "WARN": "\033[33m",   # 黄
        "ERROR": "\033[31m",  # 红
        "RESET": "\033[0m",
    }

    @classmethod
    def colorize(cls, level: Level, text: str) -> str:
        return f"{cls._colors[level]}{text}{cls._colors['RESET']}"


class Logger:
    _level_rank = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}
    _current_level: int = 1  # 默认 INFO
    _log_file: Optional[TextIO] = None
    _log_file_path: Optional[str] = None
    _initialized: bool = False

    @classmethod
    def configure(cls, level: Level = "INFO", log_file: str = ""):
        """
        配置日志系统

        Args:
            level: 日志级别
            log_file: 日志文件路径，为空则不输出到文件
        """
        cls._current_level = cls._level_rank.get(level.upper(), 1)

        # 关闭之前的日志文件
        if cls._log_file and not cls._log_file.closed:
            cls._log_file.close()
            cls._log_file = None

        # 打开新的日志文件
        if log_file:
            cls._log_file_path = log_file
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            cls._log_file = open(log_path, "a", encoding="utf-8")

        cls._initialized = True
        cls.info("Logger", f"日志系统已初始化 (级别: {level}, 文件: {log_file or '无'})")

    @classmethod
    def _ensure_initialized(cls):
        """确保日志系统已初始化，未初始化时使用环境变量配置"""
        if not cls._initialized:
            level = os.getenv("LOG_LEVEL", "INFO").upper()
            if level not in cls._level_rank:
                level = "INFO"
            cls._current_level = cls._level_rank[level]

            log_file = os.getenv("LOG_FILE", "")
            if log_file:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                cls._log_file = open(log_path, "a", encoding="utf-8")
                cls._log_file_path = log_file

            cls._initialized = True

    @classmethod
    def _log(cls, level: Level, module: str, msg: str):
        cls._ensure_initialized()

        if cls._level_rank[level] < cls._current_level:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [{level}] {module} | {msg}"

        # 输出到控制台
        colored = _ColoredFormatter.colorize(level, line)
        print(colored, file=sys.stderr)

        # 输出到文件
        if cls._log_file and not cls._log_file.closed:
            cls._log_file.write(line + "\n")
            cls._log_file.flush()

    @classmethod
    def debug(cls, module: str, msg: str):
        """记录 DEBUG 级别日志"""
        cls._log("DEBUG", module, msg)

    @classmethod
    def info(cls, module: str, msg: str):
        """记录 INFO 级别日志"""
        cls._log("INFO", module, msg)

    @classmethod
    def warn(cls, module: str, msg: str):
        """记录 WARN 级别日志"""
        cls._log("WARN", module, msg)

    @classmethod
    def warning(cls, module: str, msg: str):
        """记录 WARN 级别日志（别名）"""
        cls._log("WARN", module, msg)

    @classmethod
    def error(cls, module: str, msg: str):
        """记录 ERROR 级别日志"""
        cls._log("ERROR", module, msg)

    @classmethod
    def close(cls):
        """关闭日志文件"""
        if cls._log_file and not cls._log_file.closed:
            cls._log_file.close()
            cls._log_file = None


logger = Logger
