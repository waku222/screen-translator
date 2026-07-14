"""
翻訳機能の基底クラス
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseTranslator(ABC):
    """翻訳機能の抽象基底クラス"""
    
    @abstractmethod
    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'ja') -> str:
        """
        テキストを翻訳する
        
        Args:
            text: 翻訳するテキスト
            source_lang: 元の言語コード
            target_lang: 翻訳先の言語コード
            
        Returns:
            str: 翻訳されたテキスト
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """翻訳サービス名を取得する"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """翻訳サービスが利用可能かどうかを確認する"""
        pass
