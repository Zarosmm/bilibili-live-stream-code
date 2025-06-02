"""
二维码生成工具
"""

import qrcode
import io
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QByteArray


class QRCodeGenerator:
    """二维码生成器"""

    @staticmethod
    def generate_qr_pixmap(url: str, size: tuple = (200, 200)) -> QPixmap:
        """生成二维码QPixmap用于Qt显示"""
        # 创建二维码实例
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # 生成PIL图像
        img = qr.make_image(fill_color="black", back_color="white")

        # 转换为字节流
        byte_array = QByteArray()
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        byte_array.append(buffer.getvalue())

        # 创建QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(byte_array, "PNG")

        # 缩放到指定大小
        return pixmap.scaled(size[0], size[1])

    @staticmethod
    def generate_qr_ascii(url: str) -> str:
        """生成ASCII二维码字符串"""
        output = io.StringIO()
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.print_ascii(out=output, tty=False, invert=False)
        return output.getvalue()
