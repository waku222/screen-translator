"""
Qt の Cocoa プラグインが macOS 26 以降でクラッシュするのを防ぐためのパッチ

現象:
    メニューバーのアイコンをクリックすると SIGABRT で落ちる。
    ただし起動直後は落ちず、一度キャプチャを使った後に落ちる。

原因:
    libqcocoa は NSStatusItem のクリック処理と statusItemMenuBeganTracking:
    オブザーバの両方で [[NSApp currentEvent] clickCount] を呼んでいる
    （逆アセンブルで確認）。macOS 26 以降の AppKit は、マウス以外のイベントに
    clickCount を送ると NSInternalInconsistencyException を投げるようになった。

    macOS 26 の NSSceneStatusItem ではステータス項目のクリックが NSApp の
    イベント列を通らないため、currentEvent は「アプリが最後に処理したイベント」
    のままになる。起動直後は nil（nil への送信は 0 を返すので無害）だが、
    一度キャプチャを使うとキーイベント等が残り、そこで例外になって落ちる。

    Qt 6.11.2（現時点の最新）でも未修正のため、こちら側で塞ぐ。

対策:
    NSEvent の clickCount を差し替え、マウス系イベント以外には 0 を返す。
    マウスイベントに対しては元の実装をそのまま呼ぶので挙動は変わらない。
"""
from typing import Tuple

# clickCount を送ってよいマウス系イベントの NSEventType
# （左/右/その他ボタンの down・up・dragged）
_MOUSE_EVENT_TYPES = frozenset({1, 2, 3, 4, 5, 6, 25, 26, 27})

_applied = False


def apply_clickcount_guard() -> Tuple[bool, str]:
    """
    NSEvent.clickCount を安全な実装に差し替える

    QApplication を作る前に呼ぶこと。

    Returns:
        (成功したか, 説明文)
    """
    global _applied
    if _applied:
        return True, "already applied"

    try:
        import objc
        from AppKit import NSEvent
    except ImportError as e:
        return False, f"PyObjC を読み込めませんでした: {e}"

    try:
        original = NSEvent.instanceMethodForSelector_(b"clickCount")
        objc.classAddMethod(NSEvent, b"st_originalClickCount", original)

        def safe_click_count(self, _cmd=None):
            if self.type() in _MOUSE_EVENT_TYPES:
                return self.st_originalClickCount()
            return 0

        objc.classAddMethod(
            NSEvent,
            b"clickCount",
            # 元のシグネチャ q@: （long long を返す、引数は self と _cmd）
            objc.selector(safe_click_count, selector=b"clickCount", signature=b"q@:"),
        )
    except Exception as e:
        return False, f"差し替えに失敗しました: {type(e).__name__}: {e}"

    ok, detail = _self_test()
    _applied = ok
    return ok, detail


def _self_test() -> Tuple[bool, str]:
    """キーイベントに clickCount を送っても落ちないことを実際に確かめる"""
    try:
        from AppKit import NSEvent, NSEventTypeKeyDown
        from Foundation import NSPoint

        key_event = NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
            NSEventTypeKeyDown, NSPoint(0, 0), 0, 0, 0, None, "t", "t", False, 17
        )
        value = key_event.clickCount()
    except Exception as e:
        return False, f"自己テストで例外: {type(e).__name__}: {e}"

    if value != 0:
        return False, f"自己テストの戻り値が想定外: {value}"
    return True, "NSEvent.clickCount guard applied"


if __name__ == "__main__":
    print(apply_clickcount_guard())
