"""
翻訳エンジン

現在は Apple のオンデバイス翻訳 (Translation.framework) のみを提供する。
以前使用していた Google 翻訳はスクレイピング方式で、Google 側の
レート制限 (HTTP 429 / sorry ページ) により恒常的に失敗するため廃止した。
"""
from .base import BaseTranslator
from .apple_translator import AppleTranslator, TranslationError

# 設定ファイルの translation.engine で指定できるエンジン
ENGINES = {
    'apple': AppleTranslator,
}


def create_translator(engine: str = 'apple', **kwargs) -> BaseTranslator:
    """
    設定名から翻訳エンジンを生成する

    Args:
        engine: エンジン名（現在は 'apple' のみ）

    Raises:
        RuntimeError: 未知のエンジン名が指定された場合
    """
    translator_class = ENGINES.get(engine)
    if translator_class is None:
        available = ', '.join(sorted(ENGINES))
        raise RuntimeError(f"未知の翻訳エンジン '{engine}' です（利用可能: {available}）")
    return translator_class(**kwargs)


__all__ = ['BaseTranslator', 'AppleTranslator', 'TranslationError', 'create_translator', 'ENGINES']
