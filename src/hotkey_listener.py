"""
グローバルホットキーリスナー
Cmd+Shift+T でアプリを起動する
"""
from pynput import keyboard
from typing import Callable, Optional
import threading


class HotkeyListener:
    """グローバルホットキーを監視するクラス"""
    
    def __init__(self, callback: Callable[[], None]):
        """
        ホットキーリスナーを初期化
        
        Args:
            callback: ホットキーが押された時に呼び出されるコールバック
        """
        self.callback = callback
        self.listener = None
        self.current_keys = set()
        
        # ホットキーの組み合わせ (Cmd+Shift+T)
        self.hotkey_combination = {
            keyboard.Key.cmd,
            keyboard.Key.shift,
        }
        self.hotkey_char = 't'
    
    def _on_press(self, key):
        """キー押下時のハンドラ"""
        try:
            # 修飾キーをセットに追加
            if hasattr(key, 'value'):
                self.current_keys.add(key)
            
            # 文字キーのチェック
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                
                # 修飾キーが押されていてかつ目的のキーが押された
                if (self.hotkey_combination.issubset(self.current_keys) and 
                    char == self.hotkey_char):
                    # コールバックを別スレッドで実行
                    threading.Thread(target=self.callback, daemon=True).start()
                    
        except Exception:
            pass
    
    def _on_release(self, key):
        """キー解放時のハンドラ"""
        try:
            if hasattr(key, 'value'):
                self.current_keys.discard(key)
        except Exception:
            pass
    
    def start(self):
        """ホットキーリスナーを開始"""
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
    
    def stop(self):
        """ホットキーリスナーを停止"""
        if self.listener:
            self.listener.stop()
            self.listener = None


if __name__ == "__main__":
    # テスト用コード
    import time
    
    def on_hotkey():
        print("Hotkey pressed! (Cmd+Shift+T)")
    
    listener = HotkeyListener(on_hotkey)
    listener.start()
    
    print("Listening for Cmd+Shift+T... (Press Ctrl+C to quit)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("\nStopped.")
