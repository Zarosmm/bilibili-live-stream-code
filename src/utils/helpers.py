"""
通用工具函数
"""

from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import QTimer
from typing import Optional


def show_message(
    parent: Optional[QWidget], title: str, message: str, msg_type: str = "info"
) -> None:
    """显示消息框"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)

    if msg_type == "error":
        msg_box.setIcon(QMessageBox.Icon.Critical)
    elif msg_type == "warning":
        msg_box.setIcon(QMessageBox.Icon.Warning)
    elif msg_type == "question":
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return msg_box.exec() == QMessageBox.StandardButton.Yes
    else:
        msg_box.setIcon(QMessageBox.Icon.Information)

    msg_box.exec()


def show_question(parent: Optional[QWidget], title: str, message: str) -> bool:
    """显示询问对话框，返回True表示用户选择了Yes"""
    return show_message(parent, title, message, "question")


class PeriodicTimer:
    """周期性定时器封装"""

    def __init__(self, interval: int, callback):
        self.timer = QTimer()
        self.timer.timeout.connect(callback)
        self.interval = interval

    def start(self):
        """开始定时器"""
        self.timer.start(self.interval)

    def stop(self):
        """停止定时器"""
        self.timer.stop()

    def is_active(self) -> bool:
        """检查定时器是否活跃"""
        return self.timer.isActive()
