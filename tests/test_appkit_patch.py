"""
Qt クラッシュ回避パッチのテスト

macOS 26 以降の AppKit は、マウス以外のイベントに clickCount を送ると
NSInternalInconsistencyException を投げる。Qt の Cocoa プラグインが
これを踏んでメニューバー操作時に落ちるため、NSEvent.clickCount を
差し替えている。
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

pytest.importorskip("AppKit", reason="PyObjC が必要")

from utils.appkit_patch import apply_clickcount_guard


def _key_event():
    from AppKit import NSEvent, NSEventTypeKeyDown
    from Foundation import NSPoint
    return NSEvent.keyEventWithType_location_modifierFlags_timestamp_windowNumber_context_characters_charactersIgnoringModifiers_isARepeat_keyCode_(
        NSEventTypeKeyDown, NSPoint(0, 0), 0, 0, 0, None, "t", "t", False, 17
    )


def _mouse_event(click_count: int):
    from AppKit import NSEvent, NSEventTypeLeftMouseDown
    from Foundation import NSPoint
    return NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(
        NSEventTypeLeftMouseDown, NSPoint(10, 10), 0, 0, 0, None, 0, click_count, 1.0
    )


def test_guard_applies():
    """パッチが適用できることを確認"""
    applied, detail = apply_clickcount_guard()
    assert applied, detail


def test_key_event_returns_zero_instead_of_raising():
    """キーイベントに clickCount を送っても例外にならず 0 を返すことを確認"""
    apply_clickcount_guard()
    assert _key_event().clickCount() == 0


def test_mouse_event_keeps_original_value():
    """マウスイベントは本来の clickCount を返すことを確認"""
    apply_clickcount_guard()
    assert _mouse_event(2).clickCount() == 2
    assert _mouse_event(1).clickCount() == 1
