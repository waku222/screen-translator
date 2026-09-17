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
        # 左右どちらの修飾キーでも成立させる
        self.cmd_keys = {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}
        self.shift_keys = {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
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
                if (self.current_keys & self.cmd_keys and
                        self.current_keys & self.shift_keys and
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
    
    def start(self) -> bool:
        """
        ホットキーリスナーを開始する

        Returns:
            bool: 開始できたか（入力監視の権限が無いと失敗する）
        """
        try:
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            return True
        except Exception:
            self.listener = None
            return False
    
    def is_alive(self) -> bool:
        """リスナーが動いているか（権限が無いと止まる）"""
        return self.listener is not None and self.listener.is_alive()
    
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
