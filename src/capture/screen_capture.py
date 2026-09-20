"""
画面キャプチャモジュール
mssを使用して画面の指定範囲をキャプチャする
"""
import mss
from PIL import Image
from typing import Tuple, Optional
import tempfile
import os


class ScreenCapture:
    """画面キャプチャを行うクラス"""
    
    def __init__(self):
        self.sct = mss.mss()
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """
        指定した矩形範囲をキャプチャする
        
        Args:
            x: 左上のX座標
            y: 左上のY座標
            width: 幅
            height: 高さ
            
        Returns:
            PIL.Image: キャプチャした画像
        """
        monitor = {
            "left": x,
            "top": y,
            "width": width,
            "height": height
        }
        screenshot = self.sct.grab(monitor)
        # mssのスクリーンショットをPIL Imageに変換
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img
    
    def capture_region_from_rect(self, rect: Tuple[int, int, int, int]) -> Image.Image:
        """
        矩形タプルから範囲をキャプチャする
        
        Args:
            rect: (x, y, width, height) のタプル
            
        Returns:
            PIL.Image: キャプチャした画像
        """
        x, y, width, height = rect
        return self.capture_region(x, y, width, height)
    
    def capture_full_screen(self, monitor_index: int = 0) -> Image.Image:
        """
        指定したモニター全体をキャプチャする
        
        Args:
            monitor_index: モニターのインデックス（0はプライマリ）
            
        Returns:
            PIL.Image: キャプチャした画像
        """
        monitors = self.sct.monitors
        if monitor_index >= len(monitors):
            monitor_index = 0
        monitor = monitors[monitor_index]
        screenshot = self.sct.grab(monitor)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    
    def save_capture(self, image: Image.Image, filepath: Optional[str] = None) -> str:
        """
        キャプチャした画像を保存する
        
        Args:
            image: 保存する画像
            filepath: 保存先パス（Noneの場合は一時ファイル）
            
        Returns:
            str: 保存したファイルパス
        """
        if filepath is None:
            fd, filepath = tempfile.mkstemp(suffix=".png")
            os.close(fd)
        image.save(filepath, "PNG")
        return filepath
    
    
    def get_monitors(self) -> list:
        """
        利用可能なモニター情報を取得する
        
        Returns:
            list: モニター情報のリスト
        """
        return self.sct.monitors


if __name__ == "__main__":
    # テスト用コード
    capture = ScreenCapture()
    print("Available monitors:", capture.get_monitors())
    
    # フルスクリーンキャプチャテスト
    img = capture.capture_full_screen()
    path = capture.save_capture(img)
    print(f"Full screen captured: {path}")
