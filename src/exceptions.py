"""
カスタム例外クラス
アプリケーション全体で使用する例外を定義
"""


class ScreenTranslatorError(Exception):
    """Screen Translatorの基底例外クラス"""
    pass


class ScreenCaptureError(ScreenTranslatorError):
    """画面キャプチャ時のエラー"""
    pass


class OCRError(ScreenTranslatorError):
    """OCR処理時のエラー"""
    pass


class TranslationError(ScreenTranslatorError):
    """翻訳処理時のエラー"""
    pass


class ConfigError(ScreenTranslatorError):
    """設定関連のエラー"""
    pass
