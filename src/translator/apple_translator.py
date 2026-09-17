"""
Apple の Translation.framework を使用した翻訳モジュール

Translation.framework は Objective-C に公開されていないため PyObjC からは呼べない。
Swift で書いたヘルパー (helper/translate_helper.swift) を常駐させ、JSON で
やり取りする。完全にオンデバイスで動作し、通信もレート制限も発生しない。
"""
from typing import Optional

from helper_process import HelperError, HelperProcess, get_shared_helper

from .base import BaseTranslator


class TranslationError(Exception):
    """翻訳エラーを表す例外"""
    pass


class AppleTranslator(BaseTranslator):
    """Apple のオンデバイス翻訳を使用した翻訳クラス"""

    def __init__(self, timeout: int = 45, helper: Optional[HelperProcess] = None):
        """
        Args:
            timeout: 1回の翻訳を待つ秒数
            helper: 共用する常駐ヘルパー（省略時はアプリ共通のものを使う）

        Raises:
            RuntimeError: ヘルパーが見つからない場合
        """
        self.timeout = timeout
        self.helper = helper or get_shared_helper()

    def translate(self, text: str, source_lang: str = 'en', target_lang: str = 'ja') -> str:
        """
        テキストを翻訳する

        Args:
            text: 翻訳するテキスト
            source_lang: 元の言語コード（'auto' は非対応）
            target_lang: 翻訳先の言語コード

        Returns:
            str: 翻訳されたテキスト

        Raises:
            TranslationError: 翻訳に失敗した場合
        """
        if not text or not text.strip():
            return ""

        if source_lang == 'auto':
            # Translation.framework の installedSource 初期化子は言語の明示が必要
            raise TranslationError(
                "Apple 翻訳では source_lang に 'auto' を指定できません。"
                "設定ファイルで翻訳元の言語を指定してください"
            )

        payload = {'op': 'translate', 'text': text, 'source': source_lang, 'target': target_lang}
        try:
            result = self.helper.request(payload, timeout=self.timeout)
        except HelperError as e:
            raise TranslationError(str(e)) from e

        if not result.get('ok'):
            raise TranslationError(result.get('error') or "翻訳に失敗しました")
        return result.get('text', '')

    def check_availability(self, source_lang: str = 'en', target_lang: str = 'ja') -> str:
        """
        言語パックの状態を返す

        Returns:
            str: 'installed'（利用可能） / 'supported'（未ダウンロード） / 'unsupported'（非対応）
        """
        payload = {'source': source_lang, 'target': target_lang}
        try:
            # 起動時に一度だけなので、使い捨てのプロセスで十分
            result = self.helper.run_once(payload, extra_args=['--check'], timeout=30)
        except HelperError as e:
            raise TranslationError(str(e)) from e

        if not result.get('ok'):
            raise TranslationError(result.get('error') or "言語の確認に失敗しました")
        return result.get('status', 'unknown')

    def close(self):
        """常駐ヘルパーを終了する（アプリ終了時に呼ぶ）"""
        self.helper.close()

    def get_name(self) -> str:
        return "Apple Translation"

    def is_available(self) -> bool:
        return self.helper.helper_path is not None


if __name__ == "__main__":
    # テスト用コード
    translator = AppleTranslator()
    print(f"Helper: {translator.helper.helper_path}")
    print(f"Availability (en->ja): {translator.check_availability()}")
    test_text = "Hello, world! This is a test of the translation system."
    print(f"Original: {test_text}")
    print(f"Translated: {translator.translate(test_text)}")
    translator.close()
