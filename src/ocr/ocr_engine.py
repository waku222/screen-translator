"""
OCRエンジンモジュール
Apple Vision Framework を使用してテキストを抽出する

ocrmac ライブラリは performRequests が失敗しても例外を投げず空リストを返すため、
「テキストが無い」のか「Vision が失敗した」のかが区別できない。実際に
断続的な失敗が「テキストが検出されませんでした」として現れたので、
Vision を直接呼び、失敗を検知して再試行する。
"""
import io
import time
from typing import List, Optional, Tuple

from PIL import Image

try:
    import objc
    import Vision
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False
    print("Warning: Vision framework not available. OCR functionality will be limited.")

from utils.logger import get_logger


class OCRError(Exception):
    """OCR の実行に失敗したことを表す例外"""
    pass


class TextBlock:
    """OCRで検出されたテキストブロック"""

    def __init__(self, text: str, confidence: float, bbox: Tuple[float, float, float, float]):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox  # (x, y, width, height) normalized 0-1

    def __repr__(self):
        return f"TextBlock(text='{self.text[:20]}...', confidence={self.confidence:.2f})"


class OCREngine:
    """Apple Vision Framework を使用したOCRエンジン"""

    # Vision が一時的に失敗することがあるため、少し待って試し直す
    MAX_ATTEMPTS = 3
    RETRY_WAIT = 0.4

    def __init__(self, language_preference: Optional[List[str]] = None):
        """
        OCRエンジンを初期化する

        Args:
            language_preference: 言語優先順位のリスト (例: ['en-US', 'ja-JP'])
        """
        if not VISION_AVAILABLE:
            raise RuntimeError(
                "Vision framework is not available. "
                "Please install it with: pip install pyobjc-framework-Vision"
            )

        self.language_preference = language_preference or ['en-US']

    def extract_text(self, image: Image.Image) -> str:
        """
        画像からテキストを抽出する

        Args:
            image: PIL.Image オブジェクト

        Returns:
            str: 抽出されたテキスト（検出されなければ空文字）

        Raises:
            OCRError: Vision の呼び出し自体が失敗した場合
        """
        return "\n".join(block.text for block in self.extract_with_details(image))

    def extract_text_from_file(self, filepath: str) -> str:
        """
        画像ファイルからテキストを抽出する

        Args:
            filepath: 画像ファイルのパス

        Returns:
            str: 抽出されたテキスト
        """
        with Image.open(filepath) as image:
            return self.extract_text(image)

    def extract_with_details(self, image: Image.Image) -> List[TextBlock]:
        """
        画像からテキストを詳細情報付きで抽出する

        Args:
            image: PIL.Image オブジェクト

        Returns:
            List[TextBlock]: テキストブロックのリスト (テキスト、信頼度、位置)

        Raises:
            OCRError: Vision の呼び出し自体が失敗した場合
        """
        png_data = self._to_png_bytes(image)
        logger = get_logger()

        last_error = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                return self._recognize(png_data)
            except OCRError as e:
                last_error = e
                logger.warning(f"OCR attempt {attempt}/{self.MAX_ATTEMPTS} failed: {e}")
                if attempt < self.MAX_ATTEMPTS:
                    time.sleep(self.RETRY_WAIT)

        raise last_error

    def _recognize(self, png_data: bytes) -> List[TextBlock]:
        """Vision を1回呼ぶ"""
        with objc.autorelease_pool():
            request = Vision.VNRecognizeTextRequest.alloc().init()
            request.setRecognitionLevel_(0)  # 0 = accurate, 1 = fast
            request.setRecognitionLanguages_(self.language_preference)

            handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(png_data, None)
            result = handler.performRequests_error_([request], None)

            # PyObjC は bool を返す場合と (bool, NSError) を返す場合がある
            if isinstance(result, tuple):
                succeeded, error = result
            else:
                succeeded, error = bool(result), None

            if not succeeded or error is not None:
                raise OCRError(f"Vision の実行に失敗しました: {error}")

            observations = request.results() or []
            blocks = []
            for observation in observations:
                bounding_box = observation.boundingBox()
                blocks.append(TextBlock(
                    observation.text(),
                    observation.confidence(),
                    (
                        bounding_box.origin.x,
                        bounding_box.origin.y,
                        bounding_box.size.width,
                        bounding_box.size.height,
                    ),
                ))
            return blocks

    @staticmethod
    def _to_png_bytes(image: Image.Image) -> bytes:
        """PIL の画像を PNG のバイト列にする（一時ファイルを経由しない）"""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()


if __name__ == "__main__":
    # テスト用コード
    if VISION_AVAILABLE:
        print("Vision is available!")
        engine = OCREngine()
        print("OCR Engine initialized successfully.")
    else:
        print("Vision is not available. Please install pyobjc-framework-Vision.")
