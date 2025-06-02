import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """主程序入口"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("B站直播推流码获取工具")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("BilibiliLiveStreamCode")

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
