import json
import os

import httpx

from config import PLATFORM_USERNAME, PLATFORM_PASSWORD


class DataCubeImporter:
    def __init__(self, base_url: str = "http://127.0.0.1:8561"):
        self.base_url = base_url.rstrip("/")
        self.client: httpx.AsyncClient | None = None
        self.session_cookies: dict | None = None
        self._api_login = "/datacube/loginAction.do"
        self._api_import = "/datacube/cubeAction.do?method=import"
        self._api_check = "/datacube/cubeAction.do?method=checkStatus"

    async def _ensure_client(self):
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    def configure_api(self, login_path: str | None = None, import_path: str | None = None, check_path: str | None = None, base_url: str | None = None):
        if base_url:
            self.base_url = base_url.rstrip("/")
        if login_path:
            self._api_login = login_path
        if import_path:
            self._api_import = import_path
        if check_path:
            self._api_check = check_path

    async def login(self) -> dict:
        await self._ensure_client()
        username = PLATFORM_USERNAME
        password = PLATFORM_PASSWORD
        try:
            resp = await self.client.post(
                self._api_login,
                data={"username": username, "password": password},
            )
            resp.raise_for_status()
            self.session_cookies = dict(resp.cookies)
            result = resp.json() if "json" in resp.headers.get("content-type", "") else {"status": "ok"}
            if not self.session_cookies:
                self.session_cookies = {"session_id": result.get("sessionId", "")}
            return {"success": True, "message": "登录成功", "data": result}
        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"登录失败，HTTP状态码: {e.response.status_code}", "data": None}
        except httpx.RequestError as e:
            return {"success": False, "message": f"网络错误: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "message": f"登录异常: {str(e)}", "data": None}

    async def import_cube(self, cube_content: dict, file_name: str | None = None) -> dict:
        await self._ensure_client()
        if not self.session_cookies:
            login_result = await self.login()
            if not login_result["success"]:
                return login_result
        try:
            content_str = json.dumps(cube_content, ensure_ascii=False)
            files = {"file": (file_name or "model.cube", content_str, "application/octet-stream")}
            resp = await self.client.post(
                self._api_import,
                files=files,
                cookies=self.session_cookies,
            )
            resp.raise_for_status()
            try:
                result = resp.json()
            except Exception:
                result = {"status": resp.status_code, "text": resp.text}
            return {"success": True, "message": "导入成功", "data": result}
        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"导入失败，HTTP状态码: {e.response.status_code}", "data": None}
        except httpx.RequestError as e:
            return {"success": False, "message": f"网络错误: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "message": f"导入异常: {str(e)}", "data": None}

    async def check_status(self, model_name: str) -> dict:
        await self._ensure_client()
        if not self.session_cookies:
            login_result = await self.login()
            if not login_result["success"]:
                return login_result
        try:
            resp = await self.client.get(
                self._api_check,
                params={"name": model_name},
                cookies=self.session_cookies,
            )
            resp.raise_for_status()
            try:
                result = resp.json()
            except Exception:
                result = {"status": resp.status_code, "text": resp.text}
            return {"success": True, "message": "查询成功", "data": result}
        except httpx.HTTPStatusError as e:
            return {"success": False, "message": f"查询失败，HTTP状态码: {e.response.status_code}", "data": None}
        except httpx.RequestError as e:
            return {"success": False, "message": f"网络错误: {str(e)}", "data": None}
        except Exception as e:
            return {"success": False, "message": f"查询异常: {str(e)}", "data": None}

    async def import_from_path(self, file_path: str) -> dict:
        if not os.path.isfile(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}", "data": None}
        if not file_path.endswith(".cube"):
            return {"success": False, "message": "仅支持.cube文件", "data": None}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cube_content = json.load(f)
        except json.JSONDecodeError:
            return {"success": False, "message": "cube文件格式错误，无法解析JSON", "data": None}
        except Exception as e:
            return {"success": False, "message": f"读取文件失败: {str(e)}", "data": None}
        file_name = os.path.basename(file_path)
        return await self.import_cube(cube_content, file_name=file_name)
