import httpx
import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from infra.logger import logger
from .models import (
    QRCodeGenerateResponse, QRCodePollResponse, BiliCookie,
    DynamicResponse
)


"""
相关 API 参考 https://socialsisteryi.github.io/bilibili-API-collect/docs/login/login_action/QR.html#web%E7%AB%AF%E6%89%AB%E7%A0%81%E7%99%BB%E5%BD%95
"""


class BiliClient:
    def __init__(self):
        self.base_url = "https://passport.bilibili.com"
        self.api_base_url = "https://api.bilibili.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Referer": "https://passport.bilibili.com/login",
        }   # 随便造一个
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=httpx.Timeout(10, connect=5),
            follow_redirects=True
        )


    # -----------------这是一条登录/鉴权部分的分割线----------------- #
    async def generate_qrcode(self) -> Optional[Tuple[str, str]]:
        """
        生成二维码
        """
        url = f"{self.base_url}/x/passport-login/web/qrcode/generate"
        
        try:
            response = await self.client.get(url)
        except httpx.Timeout:
            logger.warn("BiliClient", "生成二维码超时")
            return None
        except Exception as e:
            logger.warn("BiliClient", f"生成二维码请求失败: {e}")
            return None

        if response.status_code != 200:
            logger.warn("BiliClient", f"生成二维码失败: HTTP {response.status_code}")
            return None

        try:
            data = response.json()
            qr_response = QRCodeGenerateResponse(**data)
        except Exception as e:
            logger.warn("BiliClient", f"解析二维码响应失败: {e}")
            return None

        if qr_response.code != 0:
            logger.warn("BiliClient", f"生成二维码失败: {qr_response.message}")
            return None

        if not qr_response.data:
            logger.warn("BiliClient", "二维码数据为空")
            return None

        return qr_response.data.url, qr_response.data.qrcode_key

    async def poll_qrcode(self, qrcode_key: str) -> Optional[QRCodePollResponse]:
        """
        轮询扫码登录状态
        """
        url = f"{self.base_url}/x/passport-login/web/qrcode/poll"
        params = {"qrcode_key": qrcode_key}

        try:
            response = await self.client.get(url, params=params)
        except httpx.Timeout:
            logger.warn("BiliClient", "轮询二维码超时")
            return None
        except Exception as e:
            logger.warn("BiliClient", f"轮询二维码请求失败: {e}")
            return None

        if response.status_code != 200:
            logger.warn("BiliClient", f"轮询二维码失败: HTTP {response.status_code}")
            return None

        try:
            data = response.json()
            poll_response = QRCodePollResponse(**data)
        except Exception as e:
            logger.warn("BiliClient", f"解析轮询响应失败: {e}")
            return None

        return poll_response

    async def extract_cookies_from_url(self, url: str) -> Optional[BiliCookie]:
        """
        从登录成功返回的URL中提取Cookie信息
        """
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            cookie_dict = {
                'DedeUserID': query_params.get('DedeUserID', [''])[0],
                'DedeUserID__ckMd5': query_params.get('DedeUserID__ckMd5', [''])[0],
                'SESSDATA': query_params.get('SESSDATA', [''])[0],
                'bili_jct': query_params.get('bili_jct', [''])[0]
            }
            
            # 验证所有必需的cookie字段是否存在且不为空
            if all(cookie_dict.values()):
                return BiliCookie(**cookie_dict)
            else:
                logger.warn("BiliClient", "URL中缺少必需的Cookie参数")
                return None
                
        except Exception as e:
            logger.warn("BiliClient", f"从URL解析Cookie失败: {e}")
            return None

    async def wait_for_login(self, qrcode_key: str, timeout: int = 180) -> Optional[Tuple[BiliCookie, str]]:
        """
        等待用户扫码登录，二维码默认失效的时间为180秒
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 检查超时
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.warn("BiliClient", "二维码登录超时")
                return None

            # 轮询
            poll_response = await self.poll_qrcode(qrcode_key)
            if not poll_response:
                await asyncio.sleep(2)
                continue

            if poll_response.code != 0:
                logger.warn("BiliClient", f"轮询失败: {poll_response.message}")
                await asyncio.sleep(2)
                continue

            if not poll_response.data:
                await asyncio.sleep(2)
                continue

            if poll_response.data.code == 0:
                # 登录成功，这里需要直接对该轮询中的返回内容进行解析，获取Cookie和refresh_token
                logger.info("BiliClient", "扫码登录成功，获取Cookie和refresh_token...")
                cookies = await self.extract_cookies_from_url(poll_response.data.url)
                if cookies:
                    refresh_token = poll_response.data.refresh_token
                    if not refresh_token:
                        logger.warn("BiliClient", "无法提取refresh_token")
                        return None
                    return cookies, refresh_token
                else:
                    logger.warn("BiliClient", "无法提取Cookie")
                    return None
            elif poll_response.data.code == 86038:
                logger.warn("BiliClient", "二维码已失效")
                return None
            elif poll_response.data.code == 86090:
                logger.info("BiliClient", "二维码已扫码，等待确认...")
            elif poll_response.data.code == 86101:
                logger.info("BiliClient", "等待扫码...")
            else:
                logger.warn("BiliClient", f"未知状态码: {poll_response.data.code}")

            await asyncio.sleep(2)
    # -----------------登录/鉴权部分到此结束----------------- #


    # -----------------这是一条获取动态部分的分割线----------------- #
    async def get_user_dynamics(self, host_mid: int, cookies: BiliCookie, offset: str = "", update_baseline: str = "") -> Optional[DynamicResponse]:
        """
        获取指定UP主的动态列表
        Args:
            host_mid: UP主UID
            cookies: 用户Cookie
            offset: 分页偏移量
            update_baseline: 更新基线（被坑了，这个 API 的这个参数根本没有限制作用）
        Returns:
            DynamicResponse / None
        """
        url = f"{self.api_base_url}/x/polymer/web-dynamic/v1/feed/all"
        
        params = {
            "host_mid": host_mid,
            "platform": "web",
            "features": "itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote,decorationCard,onlyfansAssetsV2,forwardListHidden,ugcDelete",
            "web_location": "333.1365"
        }
        
        if offset:
            params["offset"] = offset
        if update_baseline:
            params["update_baseline"] = update_baseline
        
        cookie_dict = {
            "SESSDATA": cookies.SESSDATA,
            "bili_jct": cookies.bili_jct,
            "DedeUserID": cookies.DedeUserID,
            "DedeUserID__ckMd5": cookies.DedeUserID__ckMd5
        }
        
        try:
            response = await self.client.get(url, params=params, cookies=cookie_dict)
        except httpx.Timeout:
            logger.warn("BiliClient", f"获取UP主 {host_mid} 动态超时")
            return None
        except Exception as e:
            logger.warn("BiliClient", f"获取UP主 {host_mid} 动态请求失败: {e}")
            return None

        if response.status_code != 200:
            logger.warn("BiliClient", f"获取UP主 {host_mid} 动态失败: HTTP {response.status_code}")
            return None

        try:
            data = response.json()
            dynamic_response = DynamicResponse(**data)
        except Exception as e:
            logger.warn("BiliClient", f"解析UP主 {host_mid} 动态响应失败: {e}")
            return None

        if dynamic_response.code != 0:
            logger.warn("BiliClient", f"获取UP主 {host_mid} 动态失败: {dynamic_response.message}")
            return None

        return dynamic_response
    # -----------------获取动态部分到此结束----------------- #


    async def close(self):
        """关闭客户端"""
        await self.client.aclose()