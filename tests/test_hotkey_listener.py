"""
ホットキーの設定解釈のテスト
"""
import pytest
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hotkey_listener import (
    HotkeyListener,
    VK_BY_CHAR,
    describe,
    normalize_key,
    normalize_modifiers,
)


def _listener(modifiers=None, key='t'):
    """リスナーを作る（start() は呼ばないので入力監視の権限は要らない）"""
    return HotkeyListener(lambda: None, modifiers, key)


def test_default_is_ctrl_option_t():
    """既定が Ctrl+Option+T であることを確認

    Cmd+Shift+T は Chrome の「閉じたタブを再度開く」と衝突するため戻さない。
    """
    listener = _listener()
    assert listener.modifiers == ['ctrl', 'alt']
    assert listener.key == 't'
    assert listener.label == 'Ctrl+Option+T'


def test_modifier_aliases():
    """option / control などの別名を受け付けることを確認"""
    assert normalize_modifiers(['Option', 'CONTROL']) == ['alt', 'ctrl']
    assert normalize_modifiers(['command', 'opt']) == ['cmd', 'alt']


def test_modifiers_are_deduplicated():
    """同じ修飾キーを別名で重ねても1つにまとまることを確認"""
    assert normalize_modifiers(['ctrl', 'control']) == ['ctrl']


def test_unknown_modifier_is_rejected():
    """未知の修飾キー名を拒否することを確認"""
    with pytest.raises(ValueError, match="未知の修飾キー"):
        normalize_modifiers(['hyper'])


def test_empty_modifiers_are_rejected():
    """修飾キーなしを拒否することを確認（誤爆するため）"""
    with pytest.raises(ValueError, match="修飾キーが1つも"):
        normalize_modifiers([])


def test_unsupported_key_is_rejected():
    """対応していない文字キーを拒否することを確認"""
    with pytest.raises(ValueError, match="使えない文字"):
        normalize_key('f1')


def test_key_is_case_insensitive():
    """文字キーの大文字小文字を吸収することを確認"""
    assert normalize_key('T') == 't'
    assert _listener(['ctrl'], 'T').key == 't'


def test_label_follows_mac_order():
    """表示が Mac の並び順（Ctrl→Option→Shift→Cmd）になることを確認"""
    assert describe(['cmd', 'shift', 'alt', 'ctrl'], 'k') == 'Ctrl+Option+Shift+Cmd+K'


def test_matches_key_by_virtual_keycode():
    """Option で文字が変わっても仮想キーコードで判定できることを確認

    macOS では Option+T の char は "†" になるため、char だけを見ると
    Option 系のホットキーが成立しない。
    """
    listener = _listener(['ctrl', 'alt'], 't')

    class RemappedKey:
        """Option を押した状態で pynput が返すキー"""
        vk = VK_BY_CHAR['t']
        char = '†'

    assert listener._matches_key(RemappedKey()) is True


def test_matches_key_by_char_when_vk_missing():
    """仮想キーコードが取れない場合は文字で判定することを確認"""
    listener = _listener(['ctrl', 'alt'], 't')

    class CharOnlyKey:
        vk = None
        char = 'T'

    assert listener._matches_key(CharOnlyKey()) is True


def test_does_not_match_other_key():
    """別のキーでは成立しないことを確認"""
    listener = _listener(['ctrl', 'alt'], 't')

    class OtherKey:
        vk = VK_BY_CHAR['r']
        char = 'r'

    assert listener._matches_key(OtherKey()) is False


def test_modifiers_must_all_be_held():
    """修飾キーが揃わないと成立しないことを確認"""
    from pynput import keyboard

    listener = _listener(['ctrl', 'alt'], 't')

    assert listener._modifiers_held() is False

    listener.current_keys = {keyboard.Key.ctrl_l}
    assert listener._modifiers_held() is False

    listener.current_keys = {keyboard.Key.ctrl_l, keyboard.Key.alt_r}
    assert listener._modifiers_held() is True


def test_left_and_right_modifiers_are_equivalent():
    """左右どちらの修飾キーでも成立することを確認"""
    from pynput import keyboard

    listener = _listener(['cmd'], 't')

    listener.current_keys = {keyboard.Key.cmd_l}
    assert listener._modifiers_held() is True

    listener.current_keys = {keyboard.Key.cmd_r}
    assert listener._modifiers_held() is True
