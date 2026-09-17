"""
OCRエンジンのテスト

文字認識は Swift 製ヘルパーに任せている。この環境では Vision のモデル構築が
初回に約40秒かかり、失敗するとそのプロセスでは以後ずっと失敗するため、
失敗を検知してヘルパーを作り直せることが重要になる。
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PIL import Image, ImageDraw, ImageFont

from helper_process import HelperError, find_helper
from ocr.ocr_engine import OCREngine, OCRError


helper_required = pytest.mark.skipif(
    find_helper() is None,
    reason="translate-helper が未ビルド（./build_app.sh を実行してください）"
)


def _text_image(text: str = "Hello from the screen translator") -> Image.Image:
    image = Image.new('RGB', (900, 120), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32)
    draw.text((20, 40), text, fill='black', font=font)
    return image


class FakeHelper:
    """ヘルパーの代わり（再試行と作り直しの確認用）"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.restarts = 0

    def request(self, payload, timeout=None):
        self.requests.append(payload)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def restart(self):
        self.restarts += 1


@helper_required
def test_extract_text_reads_rendered_text():
    """描画した文字を読み取れることを確認"""
    result = OCREngine(['en-US']).extract_text(_text_image())
    assert "screen translator" in result.lower()


@helper_required
def test_blank_image_returns_empty_string():
    """文字が無い画像では空文字を返すことを確認（例外にはしない）"""
    assert OCREngine(['en-US']).extract_text(Image.new('RGB', (200, 80), 'white')) == ""


def test_failure_restarts_helper_and_retries():
    """失敗したらヘルパーを作り直して試し直すことを確認"""
    helper = FakeHelper([
        {'ok': False, 'error': 'e5rt エラー'},
        {'ok': True, 'text': 'recovered'},
    ])
    engine = OCREngine(['en-US'], helper=helper)

    assert engine.extract_text(_text_image()) == 'recovered'
    assert helper.restarts == 1
    assert len(helper.requests) == 2


def test_persistent_failure_raises_ocr_error():
    """作り直しても失敗し続ける場合は OCRError になることを確認"""
    helper = FakeHelper([
        {'ok': False, 'error': 'e5rt エラー'},
        {'ok': False, 'error': 'e5rt エラー'},
    ])
    engine = OCREngine(['en-US'], helper=helper)

    with pytest.raises(OCRError):
        engine.extract_text(_text_image())
    assert len(helper.requests) == OCREngine.MAX_ATTEMPTS


def test_helper_error_is_wrapped():
    """ヘルパーとの通信エラーも OCRError として扱うことを確認"""
    helper = FakeHelper([HelperError("応答なし"), HelperError("応答なし")])
    engine = OCREngine(['en-US'], helper=helper)

    with pytest.raises(OCRError):
        engine.extract_text(_text_image())


def test_temp_file_is_removed():
    """ヘルパーに渡した一時ファイルを残さないことを確認"""
    captured = {}

    class PathRecordingHelper(FakeHelper):
        def request(self, payload, timeout=None):
            captured['path'] = payload['imagePath']
            return super().request(payload, timeout)

    helper = PathRecordingHelper([{'ok': True, 'text': 'ok'}])
    OCREngine(['en-US'], helper=helper).extract_text(_text_image())

    assert not os.path.exists(captured['path'])
