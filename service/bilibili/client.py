import httpx
import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from infra.logger import logger
from .models import QRCodeGenerateResponse, QRCodePollResponse, BiliCookie


"""
相关 API 参考 https://socialsisteryi.github.io/bilibili-API-collect/docs/login/login_action/QR.html#web%E7%AB%AF%E6%89%AB%E7%A0%81%E7%99%BB%E5%BD%95
"""


class BiliClient:
    def __init__(self):
        self.base_url = "https://passport.bilibili.com"
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

    async def close(self):
        """关闭客户端"""
        await self.client.aclose() 