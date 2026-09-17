"""
Apple の Translation.framework を使用した翻訳モジュール

Translation.framework は Objective-C に公開されていないため PyObjC からは呼べない。
Swift で書いた補助実行ファイル (helper/translate_helper.swift) を subprocess で起動し、
JSON で受け渡しする。完全にオンデバイスで動作し、通信もレート制限も発生しない。
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .base import BaseTranslator


class TranslationError(Exception):
    """翻訳エラーを表す例外"""
    pass


def _find_helper() -> Optional[Path]:
    """
    translate-helper の場所を探す

    .app にバンドルされている場合は Contents/Resources/ 配下、
    リポジトリから直接実行している場合は build/ 配下に置かれる。
    """
    candidates = []

    # 環境変数による明示指定（デバッグ用）
    env_path = os.environ.get('SCREEN_TRANSLATOR_HELPER')
    if env_path:
        candidates.append(Path(env_path))

    # py2app でバンドルされた場合: Contents/Resources/translate-helper
    if getattr(sys, 'frozen', False):
        candidates.append(Path(sys.executable).parent.parent / 'Resources' / 'translate-helper')

    # リポジトリから実行している場合: <repo>/helper/translate-helper
    repo_root = Path(__file__).parent.parent.parent
    candidates.append(repo_root / 'helper' / 'translate-helper')

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


class AppleTranslator(BaseTranslator):
    """Apple のオンデバイス翻訳を使用した翻訳クラス"""

    def __init__(self, timeout: int = 180):
        """
        Args:
            timeout: ヘルパーの実行タイムアウト秒数

        Raises:
            RuntimeError: ヘルパーが見つからない場合
        """
        self.timeout = timeout
        self.helper_path = _find_helper()
        if self.helper_path is None:
            raise RuntimeError(
                "翻訳ヘルパー (translate-helper) が見つかりません。"
                "./build_app.sh でビルドし直してください"
            )

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

        payload = {'text': text, 'source': source_lang, 'target': target_lang}
        result = self._run_helper(payload)

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
        result = self._run_helper(payload, extra_args=['--check'])
        if not result.get('ok'):
            raise TranslationError(result.get('error') or "言語の確認に失敗しました")
        return result.get('status', 'unknown')

    def _run_helper(self, payload: dict, extra_args: Optional[list] = None) -> dict:
        """ヘルパーを起動して JSON をやり取りする"""
        command = [str(self.helper_path)] + (extra_args or [])
        try:
            process = subprocess.run(
                command,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            raise TranslationError(
                f"翻訳がタイムアウトしました（{self.timeout}秒）。テキストが長すぎる可能性があります"
            )
        except OSError as e:
            raise TranslationError(f"翻訳ヘルパーを起動できませんでした: {e}") from e

        stdout = (process.stdout or '').strip()
        if not stdout:
            stderr = (process.stderr or '').strip()
            raise TranslationError(f"翻訳ヘルパーが応答しませんでした: {stderr or '出力なし'}")

        try:
            # 最終行が JSON（Swift 側の警告等が先に出ても拾えるようにする）
            return json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError as e:
            raise TranslationError(f"翻訳ヘルパーの応答を解釈できませんでした: {stdout[:200]}") from e

    def get_name(self) -> str:
        return "Apple Translation"

    def is_available(self) -> bool:
        return self.helper_path is not None


if __name__ == "__main__":
    # テスト用コード
    translator = AppleTranslator()
    print(f"Helper: {translator.helper_path}")
    print(f"Availability (en->ja): {translator.check_availability()}")
    test_text = "Hello, world! This is a test of the translation system."
    print(f"Original: {test_text}")
    print(f"Translated: {translator.translate(test_text)}")
