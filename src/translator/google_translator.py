"""
Google翻訳を使用した翻訳モジュール
deep-translatorライブラリを使用
"""
from typing import Optional
from .base import BaseTranslator

try:
    from deep_translator import GoogleTranslator as DeepGoogleTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False


class GoogleTranslator(BaseTranslator):
    """Google翻訳を使用した翻訳クラス"""
    
    def __init__(self):
        if not DEEP_TRANSLATOR_AVAILABLE:
            raise RuntimeError("deep-translator is not installed. Please install it with: pip install deep-translator")
    
    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'ja') -> str:
        """
        Google翻訳を使用してテキストを翻訳する
        
        Args:
            text: 翻訳するテキスト
            source_lang: 元の言語コード ('en', 'auto' など)
            target_lang: 翻訳先の言語コード ('ja', 'en' など)
            
        Returns:
            str: 翻訳されたテキスト
        """
        if not text or not text.strip():
            return ""
        
        # 言語コードの変換（必要に応じて）
        source = 'auto' if source_lang == 'auto' else source_lang
        
        try:
            translator = DeepGoogleTranslator(source=source, target=target_lang)
            
            # 長いテキストは分割して翻訳（APIの制限対策）
            max_chars = 4500
            if len(text) > max_chars:
                return self._translate_long_text(text, source, target_lang, max_chars)
            
            return translator.translate(text)
        except Exception as e:
            raise TranslationError(f"Translation failed: {str(e)}") from e
    
    def _translate_long_text(self, text: str, source: str, target: str, max_chars: int) -> str:
        """長いテキストを分割して翻訳する"""
        chunks = []
        current_chunk = ""
        
        for line in text.split('\n'):
            if len(current_chunk) + len(line) + 1 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = current_chunk + '\n' + line if current_chunk else line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        translated_chunks = []
        translator = DeepGoogleTranslator(source=source, target=target)
        
        for chunk in chunks:
            translated_chunks.append(translator.translate(chunk))
        
        return '\n'.join(translated_chunks)
    
    def get_name(self) -> str:
        return "Google Translate"
    
    def is_available(self) -> bool:
        return DEEP_TRANSLATOR_AVAILABLE


class TranslationError(Exception):
    """翻訳エラーを表す例外"""
    pass


if __name__ == "__main__":
    # テスト用コード
    if DEEP_TRANSLATOR_AVAILABLE:
        translator = GoogleTranslator()
        test_text = "Hello, world! This is a test of the translation system."
        result = translator.translate(test_text)
        print(f"Original: {test_text}")
        print(f"Translated: {result}")
    else:
        print("deep-translator is not available.")
