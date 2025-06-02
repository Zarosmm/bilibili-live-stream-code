"""
B站API相关的核心业务逻辑
"""

import requests
from typing import Dict, Tuple, Optional


class BilibiliAPI:
    """B站API处理类"""

    def __init__(self):
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://link.bilibili.com",
            "referer": "https://link.bilibili.com/p/center/index",
            "sec-ch-ua": '"Microsoft Edge";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.user_agent,
        }

    def get_qrcode_data(self) -> Optional[Dict]:
        """生成登录二维码的URL和key"""
        try:
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers)
            result = response.json()
            if result.get("code") == 0:
                return result["data"]
            return None
        except Exception:
            return None

    def get_qrcode(self) -> Dict:
        """生成登录二维码的URL和key (保持向后兼容)"""
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers)
        return response.json()["data"]

    def check_qr_login(self, qrcode_key: str) -> Tuple[int, Optional[Dict]]:
        """检查二维码扫描后的登录状态，返回(状态码, cookies字典)"""
        try:
            url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
            headers = {"User-Agent": self.user_agent}
            params = {"qrcode_key": qrcode_key}
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                return -1, None

            data = response.json()
            status_code = data.get("data", {}).get("code", -1)

            if status_code == 0:  # 登录成功
                # 从响应头中提取cookies
                cookies = {}
                for cookie in response.cookies:
                    cookies[cookie.name] = cookie.value
                return status_code, cookies
            else:
                return status_code, None

        except Exception:
            return -1, None

    def cookies_dict_to_string(self, cookies: Dict) -> str:
        """将cookies字典转换为字符串"""
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])

    def cookies_string_to_dict(self, cookie_str: str) -> Dict:
        """将cookie字符串转换为字典"""
        cookies = {}
        if cookie_str:
            for item in cookie_str.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value
        return cookies

    def get_live_areas(self, cookies: Dict) -> Optional[Dict]:
        """获取直播分区列表"""
        try:
            url = "https://api.live.bilibili.com/room/v1/Area/getList?show_pinyin=1"
            response = requests.get(url, cookies=cookies, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def start_live(
        self, room_id: int, csrf: str, area_v2: int, cookies: Dict
    ) -> Tuple[bool, Optional[Dict]]:
        """开始直播并获取推流码，返回(成功状态, 推流数据)"""
        data = {
            "room_id": room_id,
            "platform": "android_link",
            "area_v2": area_v2,
            "backup_stream": "0",
            "csrf_token": csrf,
            "csrf": csrf,
        }

        try:
            response = requests.post(
                "https://api.live.bilibili.com/room/v1/Room/startLive",
                cookies=cookies,
                headers=self.headers,
                data=data,
            )

            result = response.json()
            if result.get("code") == 0:
                return True, result.get("data")
            else:
                return False, result

        except Exception:
            return False, None

    def stop_live(self, room_id: int, csrf: str, cookies: Dict) -> bool:
        """停止直播，返回成功状态"""
        data = {
            "room_id": room_id,
            "platform": "android_link",
            "csrf_token": csrf,
            "csrf": csrf,
        }

        try:
            response = requests.post(
                "https://api.live.bilibili.com/room/v1/Room/stopLive",
                cookies=cookies,
                headers=self.headers,
                data=data,
            )

            result = response.json()
            return result.get("code") == 0

        except Exception:
            return False

    def update_live_title(
        self, room_id: int, title: str, csrf: str, cookies: Dict
    ) -> bool:
        """更新直播标题"""
        if len(title) > 20:
            return False

        data = {
            "room_id": room_id,
            "platform": "android_link",
            "title": title,
            "csrf_token": csrf,
            "csrf": csrf,
        }

        try:
            response = requests.post(
                "https://api.live.bilibili.com/room/v1/Room/update",
                headers=self.headers,
                cookies=cookies,
                data=data,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("code") == 0
            return False

        except Exception:
            return False

    def get_room_id_and_csrf(
        self, cookies: Dict
    ) -> Tuple[Optional[int], Optional[str]]:
        """获取用户的直播间ID和CSRF令牌"""
        room_id = None
        csrf = None

        dede_user_id = cookies.get("DedeUserID")
        if not dede_user_id:
            return None, None

        url = f"https://api.live.bilibili.com/room/v2/Room/room_id_by_uid?uid={dede_user_id}"

        try:
            response = requests.get(url, headers={"User-Agent": self.user_agent})
            data = response.json()
        except Exception:
            return None, None
        else:
            if data.get("code") == 0:
                room_id = data.get("data", {}).get("room_id")

        csrf = cookies.get("bili_jct")

        return room_id, csrf
