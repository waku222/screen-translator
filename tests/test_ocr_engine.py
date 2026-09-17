"""
OCRエンジンのテスト

以前使っていた ocrmac は Vision の失敗を握りつぶして空リストを返すため、
「テキストが無い」と「OCR が失敗した」が区別できなかった。
ここでは失敗が例外になること、再試行が働くことを確認する。
"""
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

pytest.importorskip("Vision", reason="PyObjC の Vision が必要")

from PIL import Image, ImageDraw, ImageFont

from ocr.ocr_engine import OCREngine, OCRError, TextBlock


def _text_image(text: str = "Hello from the screen translator") -> Image.Image:
    image = Image.new('RGB', (900, 120), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 32)
    draw.text((20, 40), text, fill='black', font=font)
    return image


def test_extract_text_reads_rendered_text():
    """描画した文字を読み取れることを確認"""
    result = OCREngine().extract_text(_text_image())
    assert "screen translator" in result.lower()


def test_extract_with_details_returns_blocks():
    """信頼度と位置を持つブロックが返ることを確認"""
    blocks = OCREngine().extract_with_details(_text_image())
    assert blocks
    assert all(isinstance(b, TextBlock) for b in blocks)
    assert all(0.0 <= b.confidence <= 1.0 for b in blocks)


def test_blank_image_returns_empty_string():
    """文字が無い画像では空文字を返すことを確認（例外にはしない）"""
    assert OCREngine().extract_text(Image.new('RGB', (200, 80), 'white')) == ""


def test_failure_raises_after_retries(monkeypatch):
    """Vision が失敗し続けた場合は OCRError になることを確認"""
    engine = OCREngine()
    attempts = []

    def always_fail(png_data):
        attempts.append(1)
        raise OCRError("テスト用の失敗")

    monkeypatch.setattr(engine, '_recognize', always_fail)
    monkeypatch.setattr(engine, 'RETRY_WAIT', 0)

    with pytest.raises(OCRError):
        engine.extract_text(_text_image())
    assert len(attempts) == OCREngine.MAX_ATTEMPTS


def test_retry_recovers_from_transient_failure(monkeypatch):
    """一時的な失敗は再試行で回復することを確認"""
    engine = OCREngine()
    calls = []

    def fail_once(png_data):
        calls.append(1)
        if len(calls) == 1:
            raise OCRError("一時的な失敗")
        return [TextBlock("recovered", 1.0, (0, 0, 1, 1))]

    monkeypatch.setattr(engine, '_recognize', fail_once)
    monkeypatch.setattr(engine, 'RETRY_WAIT', 0)

    assert engine.extract_text(_text_image()) == "recovered"
    assert len(calls) == 2
