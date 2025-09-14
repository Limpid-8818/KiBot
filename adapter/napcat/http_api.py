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
        with httpx.Client(base_url=str(self._client.base_url), headers={'Authorization': f'Bearer {self._auth_token}'}) as client:
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
