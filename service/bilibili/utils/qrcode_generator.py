import qrcode
from typing import Optional


class QRCodeGenerator:
    """
    二维码生成器，用于根据 URL 构造二维码，避免访问浏览器
    """
    @staticmethod
    def generate_terminal_qr(url: str, size: int = 10) -> Optional[str]:
        """
        生成终端显示的二维码
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            
            qr.add_data(url)
            qr.make(fit=True)
            matrix = qr.get_matrix()
            
            # 转换为终端显示的字符
            terminal_qr = []
            for row in matrix:
                line = ""
                for cell in row:
                    line += "██" if cell else "  "
                terminal_qr.append(line)
            
            return "\n".join(terminal_qr)
            
        except Exception as e:
            print(f"生成二维码失败: {e}")
            return None
    
    @staticmethod
    def save_qr_image(url: str, filename: str = "qrcode.png") -> bool:
        """
        保存二维码图片到本地
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)        
            img = qr.make_image(fill_color="black", back_color="white")  
            img.save(filename)
            return True
            
        except Exception as e:
            print(f"保存二维码图片失败: {e}")
            return False
