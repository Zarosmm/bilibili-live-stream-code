"""
配置管理器
"""

import json
import os
from typing import Dict, Optional, Any


class ConfigManager:
    """配置文件管理器"""

    def __init__(self, config_dir: str = "data"):
        self.config_dir = config_dir
        self.cookies_file = os.path.join(config_dir, "cookies.json")
        self.config_file = os.path.join(config_dir, "config.json")
        self.stream_code_file = os.path.join(config_dir, "stream_code.txt")

        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)

        # 加载配置到内存
        self._config_data = self.load_config()

    def save_login_data(self, room_id: int, cookies_str: str, csrf: str) -> bool:
        """保存登录数据"""
        try:
            data = {"room_id": room_id, "cookies": cookies_str, "csrf": csrf}
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def save_cookies(self, room_id: str, cookies_str: str, csrf: str) -> bool:
        """保存cookies (兼容旧接口)"""
        return self.save_login_data(int(room_id), cookies_str, csrf)

    def load_login_data(self) -> Optional[Dict]:
        """加载登录数据"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def clear_login_data(self) -> bool:
        """清除登录数据"""
        try:
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
            return True
        except Exception:
            return False

    def clear_cookies(self) -> bool:
        """清除cookies (兼容旧接口)"""
        return self.clear_login_data()

    def save_stream_code(self, rtmp_addr: str, rtmp_code: str) -> bool:
        """保存推流码"""
        try:
            content = f"服务器地址：{rtmp_addr}\n推流码：{rtmp_code}"
            with open(self.stream_code_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False

    def clear_stream_code(self) -> bool:
        """清除推流码文件"""
        try:
            if os.path.exists(self.stream_code_file):
                os.remove(self.stream_code_file)
            return True
        except Exception:
            return False

    def save_config(self, config: Optional[Dict] = None) -> bool:
        """保存配置"""
        try:
            data_to_save = config if config is not None else self._config_data
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def load_config(self) -> Dict:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        self._config_data[key] = value
