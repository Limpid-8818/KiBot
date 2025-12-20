import os
from typing import List, Dict, Any, Optional

import httpx

from infra.logger import Logger


class NapCatHttpClient:
    def __init__(self, http_url, auth_token):
        self._http_url = http_url
        self._auth_token = auth_token
        self._client = httpx.AsyncClient(base_url=http_url, headers={'Authorization': f'Bearer {auth_token}'})

    async def get_login_info(self):
        r = await self._client.post("/get_login_info", json={})
        r.raise_for_status()
        data = r.json()
        if data.get("retcode") != 0:
            raise RuntimeError(f"get_login_info failed: {data}")
        return data["data"]

    def get_login_info_sync(self):
        with httpx.Client(base_url=str(self._client.base_url),
                          headers={'Authorization': f'Bearer {self._auth_token}'}) as client:
            r = client.post("/get_login_info", json={})
            r.raise_for_status()
            data = r.json()
            if data.get("retcode") != 0:
                raise RuntimeError(data)
            return data["data"]

    async def send_group_msg(self, group_id: int, msg: str):
        api = "/send_group_msg"
        payload = {
            "group_id": group_id,
            "message": msg
        }
        Logger.info("Message sent", msg)
        await self._client.post(api, json=payload)

    async def send_group_msg_with_segments(self, group_id: int, segments: List[Dict[str, Any]]):
        """
        使用消息段格式发送群消息
        segments: OneBot 消息段列表，例如:
        [
            {"type": "text", "data": {"text": "文本内容"}},
            {"type": "image", "data": {"file": "http://example.com/image.jpg"}}
        ]
        """
        api = "/send_group_msg"
        payload = {
            "group_id": group_id,
            "message": segments
        }
        resp = await self._client.post(api, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # 检查 NapCat 返回的状态码
        if data.get("retcode") != 0:
            raise RuntimeError(f"send_group_msg failed: {data.get('message', data)}")
        Logger.info("Message segments sent", f"group={group_id}, segments_count={len(segments)}")
        return data

    async def send_group_image_msg(self, group_id: int, img_path: str):
        abs_img_path = os.path.abspath(img_path)
        api = "/send_group_msg"
        payload = {
            "group_id": group_id,
            "message": {
                "type": "image",
                "data": {
                    "file": abs_img_path
                }
            }
        }
        Logger.info("Image sent", f"image: {abs_img_path}")
        await self._client.post(api, json=payload)

    async def send_group_forward_msg(self, group_id: int, messages: List[Dict[str, Any]]) -> Optional[Dict]:
        """
        发送合并转发消息到群聊
        messages: node 消息列表，例如:
        [
            {
                "type": "node",
                "data": {
                    "user_id": "123456",
                    "nickname": "昵称",
                    "content": [{"type": "text", "data": {"text": "内容"}}]
                }
            }
        ]
        """
        api = "/send_group_forward_msg"
        payload = {
            "group_id": group_id,
            "messages": messages
        }
        Logger.info("Forward message sent", f"group={group_id}, nodes_count={len(messages)}")
        try:
            resp = await self._client.post(api, json=payload)
            return resp.json()
        except Exception as e:
            Logger.warning("Forward message failed", str(e))
            return None

    async def get_mini_app_ark(self, app_id: str, app_package: str, title: str,
                               desc: str, pic_url: str, jump_url: str) -> Optional[str]:
        """
        获取小程序卡片（如B站分享卡片）
        返回 arkJson 字符串，可用于发送 json 消息
        """
        api = "/get_mini_app_ark"
        payload = {
            "app_id": app_id,
            "app_package": app_package,
            "title": title,
            "desc": desc,
            "pic_url": pic_url,
            "jump_url": jump_url
        }
        try:
            resp = await self._client.post(api, json=payload)
            data = resp.json()
            if data.get("retcode") == 0:
                return data.get("data", {}).get("arkJson")
            else:
                Logger.warning("get_mini_app_ark failed", str(data))
                return None
        except Exception as e:
            Logger.warning("get_mini_app_ark error", str(e))
            return None

    async def send_group_json_msg(self, group_id: int, json_data: str):
        """
        发送 JSON 卡片消息（小程序卡片等）
        """
        api = "/send_group_msg"
        payload = {
            "group_id": group_id,
            "message": [
                {
                    "type": "json",
                    "data": {
                        "data": json_data
                    }
                }
            ]
        }
        Logger.info("JSON message sent", f"group={group_id}")
        resp = await self._client.post(api, json=payload)
        return resp.json()
