"""
主窗口UI模块
"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QMessageBox,
    QGroupBox,
    QDialog,
    QApplication,
    QGridLayout,
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from typing import Dict, Optional
import sys

from src.core.bilibili_api import BilibiliAPI
from src.core.config_manager import ConfigManager
from src.core.partition_manager import PartitionManager
from src.utils.qr_generator import QRCodeGenerator


class LoginDialog(QDialog):
    """登录对话框，显示二维码"""

    login_successful = Signal(dict)

    def __init__(self, api: BilibiliAPI, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("扫码登录")
        self.setFixedSize(300, 350)

        layout = QVBoxLayout(self)

        self.qr_label = QLabel("正在生成二维码...")
        self.qr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_label)

        self.status_label = QLabel("请使用B站APP扫描二维码")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.qrcode_key = None
        self.login_timer = QTimer(self)
        self.login_timer.timeout.connect(self.check_login_status)

        self.load_qrcode()

    def load_qrcode(self):
        """加载并显示二维码"""
        qr_data = self.api.get_qrcode_data()
        if qr_data and "url" in qr_data and "qrcode_key" in qr_data:
            self.qrcode_key = qr_data["qrcode_key"]
            pixmap = QRCodeGenerator.generate_qr_pixmap(qr_data["url"], size=(200, 200))
            if pixmap:
                self.qr_label.setPixmap(pixmap)
                self.login_timer.start(2000)  # 每2秒检查一次
            else:
                self.status_label.setText("生成二维码失败")
        else:
            self.status_label.setText("获取二维码数据失败")

    def check_login_status(self):
        """检查登录状态"""
        if not self.qrcode_key:
            return

        status_code, cookies = self.api.check_qr_login(self.qrcode_key)

        if status_code == 0 and cookies:
            self.login_timer.stop()
            self.status_label.setText("登录成功！")
            self.login_successful.emit(cookies)
            self.accept()
        elif status_code == 86038:  # 二维码已失效
            self.login_timer.stop()
            self.status_label.setText("二维码已失效，请重新登录")
            self.qr_label.setText("二维码已失效")
        elif status_code == 86090:  # 二维码已扫描，等待确认
            self.status_label.setText("已扫描，请在手机上确认登录")
        elif status_code == 86101:  # 未扫描
            self.status_label.setText("请使用B站APP扫描二维码")
        elif status_code == -1:  # 请求错误
            self.login_timer.stop()
            self.status_label.setText("检查登录状态失败，请重试")

    def closeEvent(self, event):
        self.login_timer.stop()
        super().closeEvent(event)


class MainWindow(QMainWindow):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("B站直播推流码获取工具")
        self.setGeometry(100, 100, 600, 700)  # x, y, width, height

        self.api = BilibiliAPI()
        self.config_manager = ConfigManager()
        self.partition_manager = PartitionManager()

        self.room_id: Optional[int] = None
        self.csrf: Optional[str] = None
        self.cookies: Optional[Dict[str, str]] = None
        self.live_started = False
        self.current_rtmp_addr: Optional[str] = None
        self.current_rtmp_code: Optional[str] = None

        self._init_ui()
        self._load_saved_data()

    def _init_ui(self):
        """初始化UI组件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 登录区域
        login_group = QGroupBox("登录信息")
        login_layout = QVBoxLayout()
        self.login_status_label = QLabel("未登录")
        self.login_button = QPushButton("登录B站")
        self.login_button.clicked.connect(self.show_login_dialog)
        self.logout_button = QPushButton("退出登录")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setEnabled(False)
        login_layout.addWidget(self.login_status_label)
        login_layout.addWidget(self.login_button)
        login_layout.addWidget(self.logout_button)
        login_group.setLayout(login_layout)
        main_layout.addWidget(login_group)

        # 2. 直播设置区域
        settings_group = QGroupBox("直播设置")
        settings_layout = QGridLayout()

        settings_layout.addWidget(QLabel("直播分区主题:"), 0, 0)
        self.area_theme_combo = QComboBox()
        self.area_theme_combo.addItems(self.partition_manager.get_all_themes())
        self.area_theme_combo.currentTextChanged.connect(self.update_area_combo)
        settings_layout.addWidget(self.area_theme_combo, 0, 1)

        settings_layout.addWidget(QLabel("直播分区:"), 1, 0)
        self.area_combo = QComboBox()
        settings_layout.addWidget(self.area_combo, 1, 1)
        self.update_area_combo(self.area_theme_combo.currentText())  # 初始化分区

        settings_layout.addWidget(QLabel("直播标题:"), 2, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(20)
        self.title_edit.setPlaceholderText("不超过20个字符")
        settings_layout.addWidget(self.title_edit, 2, 1)

        self.update_title_button = QPushButton("更新标题")
        self.update_title_button.clicked.connect(self.update_live_title)
        settings_layout.addWidget(self.update_title_button, 2, 2)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # 3. 直播控制区域
        control_group = QGroupBox("直播控制")
        control_layout = QHBoxLayout()
        self.start_live_button = QPushButton("开始直播")
        self.start_live_button.clicked.connect(self.toggle_live_stream)
        self.start_live_button.setEnabled(False)
        control_layout.addWidget(self.start_live_button)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # 4. 推流信息区域
        stream_info_group = QGroupBox("推流信息")
        stream_info_layout = QVBoxLayout()

        # 复制按钮区域
        button_layout = QHBoxLayout()
        self.copy_addr_button = QPushButton("复制服务器地址")
        self.copy_addr_button.clicked.connect(self.copy_server_address)
        self.copy_addr_button.setEnabled(False)
        self.copy_code_button = QPushButton("复制推流码")
        self.copy_code_button.clicked.connect(self.copy_stream_code)
        self.copy_code_button.setEnabled(False)
        button_layout.addWidget(self.copy_addr_button)
        button_layout.addWidget(self.copy_code_button)

        # 推流信息显示区域
        self.rtmp_addr_label = QLabel("服务器地址: 未获取")
        self.rtmp_code_label = QLabel("推流码: 未获取")

        stream_info_layout.addLayout(button_layout)
        stream_info_layout.addWidget(self.rtmp_addr_label)
        stream_info_layout.addWidget(self.rtmp_code_label)
        stream_info_group.setLayout(stream_info_layout)
        main_layout.addWidget(stream_info_group)

        # 5. 日志区域 (可选)
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout()
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        log_layout.addWidget(self.log_edit)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        main_layout.addStretch()
        self._update_ui_state()

    def _load_saved_data(self):
        """加载保存的cookies和配置"""
        saved_login_info = self.config_manager.load_login_data()
        if saved_login_info:
            try:
                self.cookies = self.api.cookies_string_to_dict(
                    saved_login_info["cookies"]
                )
                self.room_id = int(saved_login_info["room_id"])
                self.csrf = saved_login_info["csrf"]
                self.login_status_label.setText(f"已登录 (房间号: {self.room_id})")
                self.log_message("成功加载保存的登录信息。")
                self._on_login_success()
            except Exception as e:
                self.log_message(f"加载保存的登录信息失败: {e}")
                self.config_manager.clear_cookies()

        # 加载上次窗口位置等配置
        geometry = self.config_manager.get("window_geometry")
        if geometry:
            self.setGeometry(*geometry)

        # 加载上次选择的分区和标题
        last_area_theme = self.config_manager.get("last_area_theme")
        if last_area_theme:
            self.area_theme_combo.setCurrentText(last_area_theme)

        last_area_name = self.config_manager.get("last_area_name")
        if last_area_name:
            self.update_area_combo(
                self.area_theme_combo.currentText()
            )  # 确保分区列表已加载
            self.area_combo.setCurrentText(last_area_name)

        last_title = self.config_manager.get("last_title")
        if last_title:
            self.title_edit.setText(last_title)

    def _save_current_settings(self):
        """保存当前UI设置（分区、标题）"""
        self.config_manager.set("last_area_theme", self.area_theme_combo.currentText())
        self.config_manager.set("last_area_name", self.area_combo.currentText())
        self.config_manager.set("last_title", self.title_edit.text())

    def _update_ui_state(self):
        """根据登录和直播状态更新UI元素可用性"""
        logged_in = (
            self.cookies is not None
            and self.room_id is not None
            and self.csrf is not None
        )

        self.login_button.setEnabled(not logged_in)
        self.logout_button.setEnabled(logged_in)

        self.area_theme_combo.setEnabled(logged_in)
        self.area_combo.setEnabled(logged_in)
        self.title_edit.setEnabled(logged_in)
        self.update_title_button.setEnabled(logged_in)
        self.start_live_button.setEnabled(logged_in)

        # 复制按钮仅在直播开始后可用
        stream_info_available = bool(
            self.live_started and self.current_rtmp_addr and self.current_rtmp_code
        )
        self.copy_addr_button.setEnabled(stream_info_available)
        self.copy_code_button.setEnabled(stream_info_available)

        if self.live_started:
            self.start_live_button.setText("停止直播")
            self.area_theme_combo.setEnabled(False)
            self.area_combo.setEnabled(False)
            self.title_edit.setEnabled(False)
            self.update_title_button.setEnabled(False)
        else:
            self.start_live_button.setText("开始直播")
            if logged_in:  # 只有登录后才能启用这些
                self.area_theme_combo.setEnabled(True)
                self.area_combo.setEnabled(True)
                self.title_edit.setEnabled(True)
                self.update_title_button.setEnabled(True)

    def show_login_dialog(self):
        """显示登录对话框"""
        dialog = LoginDialog(self.api, self)
        dialog.login_successful.connect(self.handle_login_success)
        dialog.exec()

    @Slot(dict)
    def handle_login_success(self, cookies: Dict[str, str]):
        """处理登录成功逻辑"""
        self.cookies = cookies
        room_id, csrf = self.api.get_room_id_and_csrf(self.cookies)

        if room_id and csrf:
            self.room_id = int(room_id)
            self.csrf = csrf
            self.login_status_label.setText(f"已登录 (房间号: {self.room_id})")
            self.log_message(
                f"登录成功！房间号: {self.room_id}, CSRF: {self.csrf[:10]}..."
            )

            if self.config_manager.get("auto_save_cookies", True):
                cookie_str = self.api.cookies_dict_to_string(self.cookies)
                self.config_manager.save_cookies(
                    str(self.room_id), cookie_str, self.csrf
                )
                self.log_message("Cookies已保存.")

            self._on_login_success()
        else:
            self.log_message("登录成功，但获取房间信息失败。请重试。")
            QMessageBox.critical(
                self, "登录失败", "无法获取房间信息，请重试或检查网络连接。"
            )
            self.cookies = None  # 重置

        self._update_ui_state()

    def _on_login_success(self):
        """登录成功后的通用操作"""
        # 更新分区数据
        if self.cookies:
            self.log_message("正在更新直播分区列表...")
            area_data = self.api.get_live_areas(self.cookies)
            if area_data:
                # 更新本地分区文件
                try:
                    self.partition_manager.update_partition_data(area_data)
                    self.log_message("直播分区列表已更新并保存到本地文件")

                    # 重新加载分区数据到UI
                    current_theme = self.area_theme_combo.currentText()
                    self.area_theme_combo.clear()
                    self.area_theme_combo.addItems(
                        self.partition_manager.get_all_themes()
                    )

                    # 尝试恢复之前选择的主题，如果不存在则选择第一个
                    if current_theme in self.partition_manager.get_all_themes():
                        self.area_theme_combo.setCurrentText(current_theme)
                    elif self.partition_manager.get_all_themes():
                        self.area_theme_combo.setCurrentText(
                            self.partition_manager.get_all_themes()[0]
                        )

                    # 更新分区列表
                    self.update_area_combo(self.area_theme_combo.currentText())

                except Exception as e:
                    self.log_message(f"更新分区数据失败: {e}")
                    self.log_message("将继续使用本地缓存数据")
            else:
                self.log_message("获取直播分区列表失败。将使用本地缓存数据。")
        self._update_ui_state()

    def logout(self):
        """处理登出逻辑"""
        self.cookies = None
        self.room_id = None
        self.csrf = None
        self.live_started = False
        self.current_rtmp_addr = None
        self.current_rtmp_code = None
        self.login_status_label.setText("未登录")
        self.rtmp_addr_label.setText("服务器地址: 未获取")
        self.rtmp_code_label.setText("推流码: 未获取")
        self.config_manager.clear_cookies()
        self.config_manager.clear_stream_code()
        self.log_message("已退出登录，并清除本地登录信息和推流码。")
        self._update_ui_state()

    @Slot(str)
    def update_area_combo(self, theme_name: str):
        """根据选择的主题更新分区下拉框"""
        self.area_combo.clear()
        if theme_name:
            partitions = self.partition_manager.get_theme_partitions(theme_name)
            self.area_combo.addItems(partitions)

    def update_live_title(self):
        """更新直播标题"""
        if not self.cookies or not self.room_id or not self.csrf:
            QMessageBox.warning(self, "错误", "请先登录！")
            return

        new_title = self.title_edit.text().strip()
        if not new_title:
            QMessageBox.information(self, "提示", "标题未更改（输入为空）。")
            return

        if len(new_title) > 20:
            QMessageBox.warning(self, "错误", "标题长度不能超过20个字符！")
            return

        success = self.api.update_live_title(
            self.room_id, new_title, self.csrf, self.cookies
        )
        if success:
            self.log_message(f"直播标题已更新为: {new_title}")
            # QMessageBox.information(self, "成功", "直播标题更新成功！")
            self.config_manager.set("last_title", new_title)  # 保存新标题
        else:
            self.log_message("直播标题更新失败。")
            QMessageBox.warning(
                self, "失败", "直播标题更新失败，请检查网络或稍后重试。"
            )

    def toggle_live_stream(self):
        """开始或停止直播"""
        if not self.cookies or not self.room_id or not self.csrf:
            QMessageBox.warning(self, "错误", "请先登录！")
            return

        if self.live_started:
            # 停止直播
            success = self.api.stop_live(self.room_id, self.csrf, self.cookies)
            if success:
                self.live_started = False
                self.current_rtmp_addr = None
                self.current_rtmp_code = None
                self.rtmp_addr_label.setText("服务器地址: 未获取")
                self.rtmp_code_label.setText("推流码: 未获取")
                self.config_manager.clear_stream_code()
                self.log_message("直播已停止。")
                # QMessageBox.information(self, "成功", "直播已成功停止！")
            else:
                self.log_message("停止直播失败。")
                QMessageBox.warning(
                    self, "失败", "停止直播失败，请尝试手动停止或检查网络。"
                )
        else:
            # 开始直播
            selected_theme = self.area_theme_combo.currentText()
            selected_area_name = self.area_combo.currentText()
            if not selected_area_name:
                QMessageBox.warning(self, "错误", "请选择一个直播分区！")
                return

            area_id = self.partition_manager.get_partition_by_name(
                selected_area_name, selected_theme
            )
            if area_id is None:
                QMessageBox.critical(
                    self, "错误", f"无法找到分区 '{selected_area_name}' 的ID。"
                )
                return

            # 更新标题（如果用户有输入）
            current_title = self.title_edit.text().strip()
            if current_title:
                title_success = self.api.update_live_title(
                    self.room_id, current_title, self.csrf, self.cookies
                )
                if title_success:
                    self.log_message(f"直播标题已设置为: {current_title}")
                    self.config_manager.set("last_title", current_title)
                else:
                    self.log_message("设置直播标题失败，将使用B站默认或上次标题。")
                    QMessageBox.warning(
                        self,
                        "标题设置失败",
                        "尝试设置直播标题失败，将继续开始直播流程。",
                    )

            self.log_message(
                f"尝试在分区 {selected_area_name} (ID: {area_id}) 开始直播..."
            )
            success, stream_data = self.api.start_live(
                self.room_id, self.csrf, area_id, self.cookies
            )

            if success and stream_data and "rtmp" in stream_data:
                self.live_started = True
                rtmp_info = stream_data["rtmp"]
                addr = rtmp_info.get("addr")
                code = rtmp_info.get("code")
                self.current_rtmp_addr = addr
                self.current_rtmp_code = code
                self.rtmp_addr_label.setText(f"服务器地址: {addr}")
                self.rtmp_code_label.setText(f"推流码: {code}")
                self.config_manager.save_stream_code(addr, code)
                self.log_message(f"直播已开始！服务器: {addr}, 推流码: {code[:10]}...")
                # QMessageBox.information(
                #     self, "成功", "直播已成功开始！推流码已显示并保存。"
                # )
                self._save_current_settings()  # 保存当前分区和标题设置
            else:
                self.log_message("开始直播失败。可能是Cookie失效或API错误。")
                QMessageBox.critical(
                    self,
                    "失败",
                    "开始直播失败！请检查Cookie是否有效、网络连接或查看日志。",
                )
                # 尝试清除可能失效的cookies
                if (
                    stream_data
                    and stream_data.get("message", "").find("主播身份校验失败") != -1
                ):
                    self.log_message(
                        "检测到主播身份校验失败，可能Cookie已过期，正在清除本地Cookie..."
                    )
                    self.logout()  # 登出以清除
                    QMessageBox.warning(
                        self, "登录失效", "登录凭据可能已过期，请重新登录。"
                    )

        self._update_ui_state()

    def copy_server_address(self):
        """复制服务器地址到剪贴板"""
        if self.current_rtmp_addr:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.current_rtmp_addr)
            self.log_message(f"服务器地址已复制到剪贴板: {self.current_rtmp_addr}")
            QMessageBox.information(self, "复制成功", "服务器地址已复制到剪贴板！")
        else:
            QMessageBox.warning(self, "错误", "没有可复制的服务器地址！")

    def copy_stream_code(self):
        """复制推流码到剪贴板"""
        if self.current_rtmp_code:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.current_rtmp_code)
            self.log_message(f"推流码已复制到剪贴板: {self.current_rtmp_code[:10]}...")
            QMessageBox.information(self, "复制成功", "推流码已复制到剪贴板！")
        else:
            QMessageBox.warning(self, "错误", "没有可复制的推流码！")

    def log_message(self, message: str):
        """在日志区域显示消息"""
        self.log_edit.append(message)
        QApplication.processEvents()  # 确保UI更新

    def closeEvent(self, event):
        """处理窗口关闭事件，保存配置"""
        # 保存窗口几何信息
        self.config_manager.set(
            "window_geometry", [self.x(), self.y(), self.width(), self.height()]
        )
        self._save_current_settings()
        self.config_manager.save_config()  # 确保所有配置写入文件
        self.log_message("配置已保存，应用程序即将关闭。")
        super().closeEvent(event)


if __name__ == "__main__":
    # 此部分仅用于测试，实际运行通过 main.py
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
