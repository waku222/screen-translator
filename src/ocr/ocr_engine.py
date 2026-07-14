"""
OCRエンジンモジュール
Apple Vision Framework (ocrmac) を使用してテキストを抽出する
"""
from typing import List, Tuple, Optional
from PIL import Image
import tempfile
import os

try:
    from ocrmac import ocrmac
    OCRMAC_AVAILABLE = True
except ImportError:
    OCRMAC_AVAILABLE = False
    print("Warning: ocrmac not available. OCR functionality will be limited.")


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
    
    def __init__(self, language_preference: Optional[List[str]] = None):
        """
        OCRエンジンを初期化する
        
        Args:
            language_preference: 言語優先順位のリスト (例: ['en-US', 'ja-JP'])
        """
        if not OCRMAC_AVAILABLE:
            raise RuntimeError("ocrmac is not installed. Please install it with: pip install ocrmac")
        
        self.language_preference = language_preference or ['en-US']
    
    def extract_text(self, image: Image.Image) -> str:
        """
        画像からテキストを抽出する
        
        Args:
            image: PIL.Image オブジェクト
            
        Returns:
            str: 抽出されたテキスト
        """
        # 一時ファイルに保存してocrmacに渡す
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            image.save(tmp_path, "PNG")
        
        try:
            annotations = ocrmac.OCR(
                tmp_path,
                language_preference=self.language_preference
            ).recognize()
            
            # テキストを結合して返す
            texts = [ann[0] for ann in annotations]
            return "\n".join(texts)
        finally:
            # 一時ファイルを削除
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def extract_text_from_file(self, filepath: str) -> str:
        """
        画像ファイルからテキストを抽出する
        
        Args:
            filepath: 画像ファイルのパス
            
        Returns:
            str: 抽出されたテキスト
        """
        annotations = ocrmac.OCR(
            filepath,
            language_preference=self.language_preference
        ).recognize()
        
        texts = [ann[0] for ann in annotations]
        return "\n".join(texts)
    
    def extract_with_details(self, image: Image.Image) -> List[TextBlock]:
        """
        画像からテキストを詳細情報付きで抽出する
        
        Args:
            image: PIL.Image オブジェクト
            
        Returns:
            List[TextBlock]: テキストブロックのリスト (テキスト、信頼度、位置)
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
            image.save(tmp_path, "PNG")
        
        try:
            annotations = ocrmac.OCR(
                tmp_path,
                language_preference=self.language_preference
            ).recognize()
            
            blocks = []
            for ann in annotations:
                text = ann[0]
                confidence = ann[1] if len(ann) > 1 else 1.0
                bbox = ann[2] if len(ann) > 2 else (0, 0, 1, 1)
                blocks.append(TextBlock(text, confidence, bbox))
            
            return blocks
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    # テスト用コード
    if OCRMAC_AVAILABLE:
        print("OCRMac is available!")
        engine = OCREngine()
        print("OCR Engine initialized successfully.")
    else:
        print("OCRMac is not available. Please install it.")
