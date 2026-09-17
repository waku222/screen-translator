"""
OCRエンジンモジュール

文字認識は Swift 製ヘルパー (helper/translate_helper.swift) に任せ、
翻訳と同じ常駐プロセスへ JSON で依頼する。

Python から PyObjC で Vision を直接呼ぶ方式は、この環境では次の問題があった。

- .app の中では初回のモデル構築に約40秒かかり、その初回が
  CRImageReaderError.e5rtError(..., 13) で失敗することがある
- 一度その失敗が起きると、そのプロセスでは以後の認識要求が即座に失敗し続ける
  （アプリ本体で起きると再起動するまで文字が一切読めなくなる）

別プロセスに出しておけば、失敗を検知してヘルパーを作り直すだけで復帰できる。
"""
import os
import tempfile
from typing import List, Optional

from PIL import Image

from helper_process import HelperError, HelperProcess, get_shared_helper
from utils.logger import get_logger


class OCRError(Exception):
    """OCR の実行に失敗したことを表す例外"""
    pass


class OCREngine:
    """Apple Vision Framework を使用したOCRエンジン（ヘルパー経由）"""

    # モデル構築の失敗は、プロセスを作り直せば次で成功することが多い
    MAX_ATTEMPTS = 2

    def __init__(self, language_preference: Optional[List[str]] = None,
                 helper: Optional[HelperProcess] = None,
                 timeout: int = 120):
        """
        Args:
            language_preference: 言語優先順位のリスト (例: ['en-US', 'ja-JP'])
            helper: 共用する常駐ヘルパー（省略時は自前で用意する）
            timeout: 1回の認識を待つ秒数（初回はモデル構築で約40秒かかる）
        """
        self.language_preference = language_preference or ['en-US']
        self.timeout = timeout
        self.helper = helper or get_shared_helper()

    def extract_text(self, image: Image.Image) -> str:
        """
        画像からテキストを抽出する

        Args:
            image: PIL.Image オブジェクト

        Returns:
            str: 抽出されたテキスト（検出されなければ空文字）

        Raises:
            OCRError: 認識の実行自体が失敗した場合
        """
        path = self._write_temp_png(image)
        try:
            return self._recognize(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def extract_text_from_file(self, filepath: str) -> str:
        """画像ファイルからテキストを抽出する"""
        return self._recognize(filepath)

    def _recognize(self, image_path: str) -> str:
        """ヘルパーに認識を依頼する。失敗したらヘルパーを作り直して試し直す"""
        logger = get_logger()
        payload = {
            'op': 'ocr',
            'imagePath': image_path,
            'languages': self.language_preference,
        }

        last_error = None
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                result = self.helper.request(payload, timeout=self.timeout)
            except HelperError as e:
                last_error = OCRError(str(e))
            else:
                if result.get('ok'):
                    return result.get('text', '')
                last_error = OCRError(result.get('error') or "文字の読み取りに失敗しました")

            logger.warning(f"OCR attempt {attempt}/{self.MAX_ATTEMPTS} failed: {last_error}")
            if attempt < self.MAX_ATTEMPTS:
                # 失敗したヘルパーは以後も失敗し続けるので捨てる
                self.helper.restart()

        raise last_error

    @staticmethod
    def _write_temp_png(image: Image.Image) -> str:
        """ヘルパーに渡すための一時 PNG を書き出す"""
        handle, path = tempfile.mkstemp(suffix=".png", prefix="screen-translator-")
        os.close(handle)
        image.save(path, "PNG")
        return path


if __name__ == "__main__":
    # テスト用コード
    import sys
    engine = OCREngine()
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        print(engine.extract_text_from_file(target))
    else:
        print("OCR Engine initialized successfully.")
