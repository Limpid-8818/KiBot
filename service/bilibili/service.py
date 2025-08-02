import json
import os
from typing import Optional, Tuple
from datetime import datetime

from infra.logger import logger
from .client import BiliClient
from .models import BiliCookie
from ..utils.qrcode_generator import QRCodeGenerator


class BiliService:
    def __init__(self):
        self.client = BiliClient()
        self.cookie_file = "cache/bilibili_cookies.json"
        self.qr_generator = QRCodeGenerator()

    async def generate_login_qrcode(self) -> Optional[Tuple[str, str]]:
        """
        生成登录二维码
        """
        return await self.client.generate_qrcode()

    async def wait_for_qrcode_login(self, qrcode_key: str, timeout: int = 180) -> Optional[BiliCookie]:
        """
        等待扫码登录完成
        """
        return await self.client.wait_for_login(qrcode_key, timeout)

    def save_cookies(self, cookies: BiliCookie) -> bool:
        """
        保存Cookie到文件
        """
        try:
            os.makedirs("cache", exist_ok=True)
            cookie_data = {
                "DedeUserID": cookies.DedeUserID,
                "DedeUserID__ckMd5": cookies.DedeUserID__ckMd5,
                "SESSDATA": cookies.SESSDATA,
                "bili_jct": cookies.bili_jct,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.warn("BiliService", f"保存Cookie失败: {e}")
            return False

    def load_cookies(self) -> Optional[BiliCookie]:
        """
        从文件加载Cookie
        """
        try:
            if not os.path.exists(self.cookie_file):
                return None
            
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            
            return BiliCookie(
                DedeUserID=cookie_data["DedeUserID"],
                DedeUserID__ckMd5=cookie_data["DedeUserID__ckMd5"],
                SESSDATA=cookie_data["SESSDATA"],
                bili_jct=cookie_data["bili_jct"]
            )
        except Exception as e:
            logger.warn("BiliService", f"加载Cookie失败: {e}")
            return None

    def has_valid_cookies(self) -> bool:
        """
        检查Cookie有效性
        """
        cookies = self.load_cookies()
        return cookies is not None

    def display_qrcode(self, qr_url: str, show_terminal: bool = True, save_image: bool = False):
        """
        显示二维码
        """
        if show_terminal:
            terminal_qr = self.qr_generator.generate_terminal_qr(qr_url)
            if terminal_qr:
                logger.info("BiliService", "请在B站APP中扫描以下二维码：")
                print("\n" + "="*50)
                print(terminal_qr)
                print("="*50 + "\n")
            else:
                logger.info("BiliService", f"请访问以下链接进行登录：{qr_url}")
        
        if save_image:
            # 保存二维码图片，这里再调用时选择不存了，图片存服务器上也没必要
            if self.qr_generator.save_qr_image(qr_url, "bilibili_login_qr.png"):
                logger.info("BiliService", "二维码图片已保存为 bilibili_login_qr.png")
            else:
                logger.warn("BiliService", "二维码图片保存失败")

    async def login_with_qrcode(self, show_terminal_qr: bool = True, save_qr_image: bool = False) -> Optional[BiliCookie]:
        """
        扫码登录流程
        """
        qr_result = await self.generate_login_qrcode()
        if not qr_result:
            return None
        
        qr_url, qrcode_key = qr_result
        
        self.display_qrcode(qr_url, show_terminal_qr, save_qr_image)
        
        cookies = await self.wait_for_qrcode_login(qrcode_key)
        if not cookies:
            return None
        
        if self.save_cookies(cookies):
            logger.info("BiliService", "Cookie保存成功！")
        else:
            logger.warn("BiliService", "Cookie保存失败！")
        
        return cookies

    async def close(self):
        """关闭服务"""
        await self.client.close() 