"""
翻訳エンジンのテスト

Apple の Translation.framework はオンデバイスで動作するため、
実際に翻訳させるテストもネットワークなしで実行できる。
ただし翻訳ヘルパーのビルド（./build_app.sh）が前提になる。
"""
import sys
import os

import pytest

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from helper_process import find_helper
from translator import AppleTranslator, TranslationError, create_translator


helper_required = pytest.mark.skipif(
    find_helper() is None,
    reason="translate-helper が未ビルド（./build_app.sh を実行してください）"
)


def test_create_translator_returns_apple():
    """既定のエンジンが Apple 翻訳であることを確認"""
    if find_helper() is None:
        pytest.skip("translate-helper が未ビルド")
    translator = create_translator('apple')
    assert isinstance(translator, AppleTranslator)
    assert translator.get_name() == "Apple Translation"


def test_create_translator_rejects_unknown_engine():
    """未知のエンジン名は RuntimeError になることを確認"""
    with pytest.raises(RuntimeError):
        create_translator('nonexistent-engine')


@helper_required
def test_translate_english_to_japanese():
    """英語から日本語への翻訳が動くことを確認"""
    translator = AppleTranslator()
    result = translator.translate("Hello", 'en', 'ja')
    assert result
    assert result != "Hello"


@helper_required
def test_translate_empty_text_returns_empty():
    """空文字は翻訳せずに空文字を返すことを確認"""
    translator = AppleTranslator()
    assert translator.translate("") == ""
    assert translator.translate("   ") == ""


@helper_required
def test_auto_source_is_rejected():
    """Apple 翻訳では source_lang='auto' を使えないことを確認"""
    translator = AppleTranslator()
    with pytest.raises(TranslationError):
        translator.translate("Hello", 'auto', 'ja')


@helper_required
def test_availability_check():
    """言語パックの状態を取得できることを確認"""
    translator = AppleTranslator()
    assert translator.check_availability('en', 'ja') in ('installed', 'supported', 'unsupported')


@helper_required
def test_helper_process_is_reused():
    """2回目以降の翻訳で常駐ヘルパーが使い回されることを確認"""
    translator = AppleTranslator()
    try:
        translator.translate("First", 'en', 'ja')
        first_pid = translator.helper._process.pid
        translator.translate("Second", 'en', 'ja')
        assert translator.helper._process.pid == first_pid
    finally:
        translator.close()
    assert not translator.helper.is_running()


@helper_required
def test_translator_recovers_after_timeout():
    """タイムアウトしてもヘルパーを起動し直して続けられることを確認"""
    translator = AppleTranslator(timeout=60)
    try:
        translator.translate("Warm up", 'en', 'ja')
        translator.timeout = 0.01
        with pytest.raises(TranslationError):
            translator.translate("This should time out because the timeout is tiny.", 'en', 'ja')
        translator.timeout = 60
        assert translator.translate("Recovered", 'en', 'ja')
    finally:
        translator.close()
