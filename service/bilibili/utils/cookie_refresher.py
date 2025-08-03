import time
import re
from typing import Optional, Tuple
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
import binascii

from infra.logger import logger
from ..models import CookieInfoResponse, CookieRefreshResponse, CookieConfirmResponse, BiliCookie


"""
感谢 https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html 对b站 Cookie 刷新机制逆向的详细整理。
"""


class CookieRefresher:
    """B站Cookie自动刷新器"""
    
    # RSA公钥（用于生成CorrespondPath），由 https://github.com/SocialSisterYi/bilibili-API-collect/issues/524 提供，具体的实现也参考了 Demo 内容
    RSA_PUBLIC_KEY = '''\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----'''
    
    def __init__(self, client):
        self.client = client
    
    def generate_correspond_path(self, timestamp: int) -> str:
        """
        生成CorrespondPath
        """
        try:
            key = RSA.importKey(self.RSA_PUBLIC_KEY)
            cipher = PKCS1_OAEP.new(key, SHA256)
            message = f'refresh_{timestamp}'.encode()
            encrypted = cipher.encrypt(message)
            return binascii.b2a_hex(encrypted).decode()
            
        except Exception as e:
            logger.warn("CookieRefresher", f"生成CorrespondPath失败: {e}")
            return ""
    
    async def check_cookie_refresh_needed(self, cookies: BiliCookie) -> Optional[Tuple[bool, int]]:
        """
        检查是否需要刷新Cookie
        """
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/info"
        params = {"csrf": cookies.bili_jct}
        
        cookie_dict = {
            "SESSDATA": cookies.SESSDATA,
            "bili_jct": cookies.bili_jct,
            "DedeUserID": cookies.DedeUserID,
            "DedeUserID__ckMd5": cookies.DedeUserID__ckMd5
        }
        
        try:
            response = await self.client.get(url, params=params, cookies=cookie_dict)
        except Exception as e:
            logger.warn("CookieRefresher", f"检查Cookie刷新状态失败: {e}")
            return None
        
        if response.status_code != 200:
            logger.warn("CookieRefresher", f"检查Cookie刷新状态HTTP错误: {response.status_code}")
            return None
        
        try:
            data = response.json()
            info_response = CookieInfoResponse(**data)
        except Exception as e:
            logger.warn("CookieRefresher", f"解析Cookie信息响应失败: {e}")
            return None
        
        if info_response.code != 0:
            logger.warn("CookieRefresher", f"检查Cookie刷新状态失败: {info_response.message}")
            return None
        
        if not info_response.data:
            logger.warn("CookieRefresher", "Cookie信息数据为空")
            return None
        
        # 其中 refresh 表示是否需要刷新，timestamp 表示时间戳（用于获取 refresh_csrf）
        return info_response.data.refresh, info_response.data.timestamp
    
    async def get_refresh_csrf(self, correspond_path: str, cookies: BiliCookie) -> Optional[str]:
        """
        获取refresh_csrf
        """
        url = f"https://www.bilibili.com/correspond/1/{correspond_path}"
        
        cookie_dict = {
            "SESSDATA": cookies.SESSDATA,
            "bili_jct": cookies.bili_jct,
            "DedeUserID": cookies.DedeUserID,
            "DedeUserID__ckMd5": cookies.DedeUserID__ckMd5
        }
        
        try:
            response = await self.client.get(url, cookies=cookie_dict)
        except Exception as e:
            logger.warn("CookieRefresher", f"获取refresh_csrf失败: {e}")
            return None
        
        if response.status_code != 200:
            logger.warn("CookieRefresher", f"获取refresh_csrf HTTP错误: {response.status_code}")
            return None
        
        # 请求该 url 会返回一个 html 页面，实时刷新口令 refresh_csrf 存放于 html 标签中，形如 <div id="1-name">XXXX</div>，这里使用正则表达式进行提取
        try:
            html_content = response.text
            match = re.search(r'<div id="1-name">([a-f0-9]{32})</div>', html_content)
            if match:
                return match.group(1)
            else:
                logger.warn("CookieRefresher", "未找到refresh_csrf")
                return None
        except Exception as e:
            logger.warn("CookieRefresher", f"解析refresh_csrf失败: {e}")
            return None
    
    async def refresh_cookies(self, refresh_csrf: str, refresh_token: str, cookies: BiliCookie) -> Optional[Tuple[BiliCookie, str]]:
        """
        刷新Cookie
        """
        url = "https://passport.bilibili.com/x/passport-login/web/cookie/refresh"
        data = {
            "csrf": cookies.bili_jct,
            "refresh_csrf": refresh_csrf,
            "source": "main_web",
            "refresh_token": refresh_token
        }
        
        cookie_dict = {
            "SESSDATA": cookies.SESSDATA,
            "bili_jct": cookies.bili_jct,
            "DedeUserID": cookies.DedeUserID,
            "DedeUserID__ckMd5": cookies.DedeUserID__ckMd5
        }
        
        try:
            response = await self.client.post(url, data=data, cookies=cookie_dict)
        except Exception as e:
            logger.warn("CookieRefresher", f"刷新Cookie失败: {e}")
            return None
        
        if response.status_code != 200:
            logger.warn("CookieRefresher", f"刷新Cookie HTTP错误: {response.status_code}")
            return None
        
        try:
            response_data = response.json()
            refresh_response = CookieRefreshResponse(**response_data)
        except Exception as e:
            logger.warn("CookieRefresher", f"解析刷新响应失败: {e}")
            return None
        
        if refresh_response.code != 0:
            logger.warn("CookieRefresher", f"刷新Cookie失败: {refresh_response.message}")
            return None
        
        # 从响应头中提取新的Cookie
        new_cookies = response.cookies
        if not new_cookies.get("SESSDATA") or not new_cookies.get("bili_jct"):
            logger.warn("CookieRefresher", "响应中缺少必需的Cookie")
            return None
        
        new_cookie = BiliCookie(
            DedeUserID=new_cookies.get("DedeUserID", cookies.DedeUserID),
            DedeUserID__ckMd5=new_cookies.get("DedeUserID__ckMd5", cookies.DedeUserID__ckMd5),
            SESSDATA=new_cookies.get("SESSDATA"),
            bili_jct=new_cookies.get("bili_jct")
        )
        
        new_refresh_token = ""
        if refresh_response.data:
            new_refresh_token = refresh_response.data.refresh_token
        
        # 返回新的 Cookie和新的 refresh_token
        return new_cookie, new_refresh_token
    
    async def confirm_refresh(self, old_refresh_token: str, new_cookies: BiliCookie) -> bool:
        """
        确认刷新
        """
        url = "https://passport.bilibili.com/x/passport-login/web/confirm/refresh"
        data = {
            "csrf": new_cookies.bili_jct,
            "refresh_token": old_refresh_token
        }
        
        # 设置新的Cookie
        cookie_dict = {
            "SESSDATA": new_cookies.SESSDATA,
            "bili_jct": new_cookies.bili_jct,
            "DedeUserID": new_cookies.DedeUserID,
            "DedeUserID__ckMd5": new_cookies.DedeUserID__ckMd5
        }
        
        try:
            response = await self.client.post(url, data=data, cookies=cookie_dict)
        except Exception as e:
            logger.warn("CookieRefresher", f"确认刷新失败: {e}")
            return False
        
        if response.status_code != 200:
            logger.warn("CookieRefresher", f"确认刷新HTTP错误: {response.status_code}")
            return False
        
        try:
            response_data = response.json()
            confirm_response = CookieConfirmResponse(**response_data)
        except Exception as e:
            logger.warn("CookieRefresher", f"解析确认响应失败: {e}")
            return False
        
        if confirm_response.code != 0:
            logger.warn("CookieRefresher", f"确认刷新失败: {confirm_response.message}")
            return False
        
        return True
    
    async def refresh_cookies_if_needed(self, cookies: BiliCookie, refresh_token: str) -> Optional[Tuple[BiliCookie, str]]:
        """
        一个用于检测是否需要刷新 Cookie 并执行刷新的完整流程的接口
        """
        # 1. 检查是否需要刷新
        check_result = await self.check_cookie_refresh_needed(cookies)
        if not check_result:
            logger.warn("CookieRefresher", "无法检查Cookie刷新状态")
            return None
        
        need_refresh, timestamp = check_result
        if not need_refresh:
            logger.info("CookieRefresher", "Cookie无需刷新")
            return None
        
        logger.info("CookieRefresher", "开始刷新Cookie...")
        
        # 2. 生成CorrespondPath
        correspond_path = self.generate_correspond_path(timestamp)
        if not correspond_path:
            logger.warn("CookieRefresher", "生成CorrespondPath失败")
            return None
        
        # 3. 获取refresh_csrf
        refresh_csrf = await self.get_refresh_csrf(correspond_path, cookies)
        if not refresh_csrf:
            logger.warn("CookieRefresher", "获取refresh_csrf失败")
            return None
        
        # 4. 刷新Cookie
        refresh_result = await self.refresh_cookies(refresh_csrf, refresh_token, cookies)
        if not refresh_result:
            logger.warn("CookieRefresher", "刷新Cookie失败")
            return None
        
        new_cookies, new_refresh_token = refresh_result
        
        # 5. 确认刷新
        if not await self.confirm_refresh(refresh_token, new_cookies):
            logger.warn("CookieRefresher", "确认刷新失败")
            return None
        
        logger.info("CookieRefresher", "Cookie刷新成功")
        return new_cookies, new_refresh_token 