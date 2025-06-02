"""
分区搜索相关功能
"""

import json
import re
import os
from typing import List, Dict, Optional


class PartitionManager:
    """直播分区管理器"""

    def __init__(self, partition_file: str = "data/partition.json"):
        self.partition_file = partition_file
        self.partition_data = None
        self.load_partition_data()

    def load_partition_data(self) -> None:
        """加载分区数据"""
        try:
            with open(self.partition_file, "r", encoding="utf-8") as f:
                self.partition_data = json.load(f).get("data", [])
        except FileNotFoundError:
            self.partition_data = []

    def get_all_themes(self) -> List[str]:
        """获取所有分区主题名称"""
        if not self.partition_data:
            return []
        return [theme.get("name", "") for theme in self.partition_data]

    def get_theme_partitions(self, theme_name: str) -> List[str]:
        """获取指定主题下的所有分区名称"""
        if not self.partition_data:
            return []

        for theme in self.partition_data:
            if theme.get("name") == theme_name:
                partition_list = theme.get("list", [])
                return [partition.get("name", "") for partition in partition_list]
        return []

    def search_partitions(self, search_word: str, theme_name: str) -> List[Dict]:
        """搜索分区"""
        if not self.partition_data or not search_word:
            return []

        results = []
        input_pattern = self._get_pinyin_pattern(search_word)

        for theme in self.partition_data:
            if theme.get("name") == theme_name:
                partition_list = theme.get("list", [])
                for partition in partition_list:
                    name = partition.get("name", "")
                    pinyin_str = partition.get("pinyin", "")

                    # 检查是否匹配汉字或拼音
                    if search_word in name or self._match_pinyin(
                        pinyin_str, input_pattern
                    ):
                        results.append(
                            {
                                "name": name,
                                "id": partition.get("id"),
                                "pinyin": pinyin_str,
                            }
                        )
                break

        return results

    def get_partition_by_name(self, name: str, theme_name: str) -> Optional[int]:
        """根据分区名称获取分区ID"""
        search_results = self.search_partitions(name, theme_name)
        for result in search_results:
            if result["name"] == name:
                return result["id"]
        return None

    def _get_pinyin_pattern(self, input_word: str) -> Optional[re.Pattern]:
        """获取拼音首字母的正则表达式"""
        if not input_word.isalpha():
            return None

        input_lower = input_word.lower()
        pattern = re.compile("".join(f"{c}.*" for c in input_lower), re.IGNORECASE)
        return pattern

    def _match_pinyin(self, word: str, pattern: Optional[re.Pattern]) -> bool:
        """判断是否匹配拼音首字母"""
        if pattern and pattern.match(word):
            return True
        return False

    def update_partition_data(self, new_data: Dict) -> None:
        """更新分区数据并保存到文件"""

        # 确保data目录存在
        os.makedirs(os.path.dirname(self.partition_file), exist_ok=True)

        # 保存新数据到文件
        with open(self.partition_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)

        # 重新加载数据到内存
        self.partition_data = new_data.get("data", [])
