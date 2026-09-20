"""
グローバルホットキーリスナー

設定した修飾キーと文字キーの組み合わせでキャプチャを起動する。
既定は Ctrl+Option+T（Cmd+Shift+T は Chrome の「閉じたタブを再度開く」などと
衝突するため避けている）。
"""
from pynput import keyboard
from typing import Callable, Iterable, List, Optional, Sequence
import threading


# macOS の仮想キーコード（ANSI 配列でのキーの位置）。
#
# Option を押しながらだと pynput が返す key.char は別の文字になる
# （Option+T なら "†"）。文字で判定すると Option 系のホットキーが成立しないため、
# 文字ではなくキーの位置で判定する。pynput は char を差し替えても vk は
# 元のまま渡してくれる（_darwin.py の _event_to_key）。
VK_BY_CHAR = {
    'a': 0x00, 's': 0x01, 'd': 0x02, 'f': 0x03, 'h': 0x04, 'g': 0x05,
    'z': 0x06, 'x': 0x07, 'c': 0x08, 'v': 0x09, 'b': 0x0B, 'q': 0x0C,
    'w': 0x0D, 'e': 0x0E, 'r': 0x0F, 'y': 0x10, 't': 0x11, 'o': 0x1F,
    'u': 0x20, 'i': 0x22, 'p': 0x23, 'l': 0x25, 'j': 0x26, 'k': 0x28,
    'n': 0x2D, 'm': 0x2E,
    '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15, '5': 0x17, '6': 0x16,
    '7': 0x1A, '8': 0x1C, '9': 0x19, '0': 0x1D,
}

# 設定ファイルに書ける修飾キー名 → pynput のキー（左右どちらでも成立させる）
MODIFIER_KEYS = {
    'cmd': (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r),
    'shift': (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r),
    'ctrl': (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r),
    'alt': (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r),
}

# 同じキーの別名を吸収する
MODIFIER_ALIASES = {
    'command': 'cmd', 'meta': 'cmd', 'super': 'cmd',
    'control': 'ctrl',
    'option': 'alt', 'opt': 'alt',
}

# 表示するときの名前（Mac の呼び方に合わせる）
MODIFIER_LABELS = {'cmd': 'Cmd', 'shift': 'Shift', 'ctrl': 'Ctrl', 'alt': 'Option'}

# 表示の並び順（Mac の慣習）
MODIFIER_ORDER = ('ctrl', 'alt', 'shift', 'cmd')

DEFAULT_MODIFIERS = ('ctrl', 'alt')
DEFAULT_KEY = 't'


def normalize_modifiers(modifiers: Iterable[str]) -> List[str]:
    """設定に書かれた修飾キー名を正規化する

    Raises:
        ValueError: 未知の修飾キー名が含まれる場合
    """
    result = []
    for raw in modifiers:
        name = str(raw).strip().lower()
        name = MODIFIER_ALIASES.get(name, name)
        if name not in MODIFIER_KEYS:
            known = ', '.join(sorted(MODIFIER_KEYS) + sorted(MODIFIER_ALIASES))
            raise ValueError(f"未知の修飾キー '{raw}' です（使えるもの: {known}）")
        if name not in result:
            result.append(name)
    if not result:
        raise ValueError("修飾キーが1つも指定されていません")
    return result


def normalize_key(key: str) -> str:
    """設定に書かれた文字キーを正規化する

    Raises:
        ValueError: 1文字でない、または対応していない文字の場合
    """
    name = str(key).strip().lower()
    if name not in VK_BY_CHAR:
        known = ' '.join(sorted(VK_BY_CHAR))
        raise ValueError(f"ホットキーに使えない文字 '{key}' です（使えるもの: {known}）")
    return name


def describe(modifiers: Sequence[str], key: str) -> str:
    """"Ctrl+Option+T" のような表示用の文字列を作る"""
    ordered = [m for m in MODIFIER_ORDER if m in modifiers]
    return '+'.join([MODIFIER_LABELS[m] for m in ordered] + [key.upper()])


class HotkeyListener:
    """グローバルホットキーを監視するクラス"""

    def __init__(self, callback: Callable[[], None],
                 modifiers: Optional[Iterable[str]] = None,
                 key: str = DEFAULT_KEY):
        """
        ホットキーリスナーを初期化

        Args:
            callback: ホットキーが押された時に呼び出されるコールバック
            modifiers: 修飾キー名のリスト（例: ['ctrl', 'alt']）
            key: 文字キー（例: 't'）

        Raises:
            ValueError: 修飾キー名や文字キーが解釈できない場合
        """
        self.callback = callback
        self.listener = None
        self.current_keys = set()

        self.modifiers = normalize_modifiers(
            DEFAULT_MODIFIERS if modifiers is None else modifiers
        )
        self.key = normalize_key(key)
        self.key_vk = VK_BY_CHAR[self.key]
        # 修飾キーごとに「このどれかが押されていれば成立」という集合を持つ
        self._required = [set(MODIFIER_KEYS[name]) for name in self.modifiers]

    @property
    def label(self) -> str:
        """"Ctrl+Option+T" のような表示用の文字列"""
        return describe(self.modifiers, self.key)

    def _matches_key(self, key) -> bool:
        """押されたキーが目的の文字キーか

        Option を押していると char が変わるので vk を優先して見る。
        vk が取れないキーボードのために char でも照合する。
        """
        if getattr(key, 'vk', None) == self.key_vk:
            return True
        char = getattr(key, 'char', None)
        return bool(char) and char.lower() == self.key

    def _modifiers_held(self) -> bool:
        """必要な修飾キーが全て押されているか"""
        return all(self.current_keys & required for required in self._required)

    def _on_press(self, key):
        """キー押下時のハンドラ"""
        try:
            # 修飾キーをセットに追加
            if hasattr(key, 'value'):
                self.current_keys.add(key)

            if self._matches_key(key) and self._modifiers_held():
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

    listener = HotkeyListener(lambda: print(f"Hotkey pressed! ({listener.label})"))
    listener.start()

    print(f"Listening for {listener.label}... (Press Ctrl+C to quit)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("\nStopped.")
