import json
import os
from typing import Optional, Tuple, List
from datetime import datetime

from infra.logger import logger
from .client import BiliClient
from .models import BiliCookie, DynamicResponse, DynamicItem
from .utils.cookie_refresher import CookieRefresher
from .utils.qrcode_generator import QRCodeGenerator


class BiliService:
    def __init__(self):
        self.client = BiliClient()
        self.cookie_file = "cache/bilibili_cookies.json"
        self.qr_generator = QRCodeGenerator()
        self.cookie_refresher = CookieRefresher(self.client.client)

    async def generate_login_qrcode(self) -> Optional[Tuple[str, str]]:
        """
        生成登录二维码
        """
        return await self.client.generate_qrcode()

    async def wait_for_qrcode_login(self, qrcode_key: str, timeout: int = 180) -> Optional[Tuple[BiliCookie, str]]:
        """
        等待扫码登录完成
        """
        return await self.client.wait_for_login(qrcode_key, timeout)

    def save_cookies(self, cookies: BiliCookie, refresh_token: str = "") -> bool:
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
                "refresh_token": refresh_token,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.warn("BiliService", f"保存Cookie失败: {e}")
            return False

    def load_cookies(self) -> Optional[Tuple[BiliCookie, str]]:
        """
        从文件加载Cookie和refresh_token
        """
        try:
            if not os.path.exists(self.cookie_file):
                return None
            
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookie_data = json.load(f)
            
            cookies = BiliCookie(
                DedeUserID=cookie_data["DedeUserID"],
                DedeUserID__ckMd5=cookie_data["DedeUserID__ckMd5"],
                SESSDATA=cookie_data["SESSDATA"],
                bili_jct=cookie_data["bili_jct"]
            )
            
            refresh_token = cookie_data.get("refresh_token", "")
            
            return cookies, refresh_token
        except Exception as e:
            logger.warn("BiliService", f"加载Cookie失败: {e}")
            return None

    def has_valid_cookies(self) -> bool:
        """
        检查Cookie有效性
        """
        result = self.load_cookies()
        return result is not None

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

    async def login_with_qrcode(self, show_terminal_qr: bool = True, save_qr_image: bool = False) -> Optional[Tuple[BiliCookie, str]]:
        """
        扫码登录流程
        """
        qr_result = await self.generate_login_qrcode()
        if not qr_result:
            return None
        
        qr_url, qrcode_key = qr_result
        
        self.display_qrcode(qr_url, show_terminal_qr, save_qr_image)
        
        # 等待用户扫码登录，直接获取Cookie和refresh_token
        result = await self.wait_for_qrcode_login(qrcode_key)
        if not result:
            return None
        
        cookies, refresh_token = result
        
        if self.save_cookies(cookies, refresh_token):
            logger.info("BiliService", "Cookie和refresh_token保存成功！")
        else:
            logger.warn("BiliService", "Cookie和refresh_token保存失败！")
        
        return cookies, refresh_token

    async def get_valid_cookies(self) -> Optional[Tuple[BiliCookie, str]]:
        """
        获取有效的Cookie（包含自动刷新）
        """
        result = self.load_cookies()
        if not result:
            return None
        
        cookies, refresh_token = result
        
        refresh_result = await self.cookie_refresher.refresh_cookies_if_needed(cookies, refresh_token)
        if refresh_result:
            new_cookies, new_refresh_token = refresh_result
            if self.save_cookies(new_cookies, new_refresh_token):
                logger.info("BiliService", "Cookie刷新后已保存")
            return new_cookies, new_refresh_token
        
        return cookies, refresh_token

    async def ensure_valid_cookies(self) -> Optional[Tuple[BiliCookie, str]]:
        """
        确保Cookie有效，如果无效则重新登录
        """
        result = await self.get_valid_cookies()
        if result:
            return result
        
        logger.info("BiliService", "Cookie无效，需要重新登录")
        return await self.login_with_qrcode()

    async def get_user_dynamics(self, host_mid: int, offset: str = "", update_baseline: str = "") -> Optional[DynamicResponse]:
        """
        获取指定UP主的动态列表
        Args:
            host_mid: UP主UID
            offset: 分页偏移量
            update_baseline: 更新基线
        Returns:
            DynamicResponse / None
        """
        result = await self.ensure_valid_cookies()
        if not result:
            logger.warn("BiliService", "无法获取有效Cookie，无法获取动态")
            return None
        
        cookies, _ = result
        
        # 获取动态
        return await self.client.get_user_dynamics(host_mid, cookies, offset, update_baseline)