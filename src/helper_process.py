"""
Swift 製ヘルパー (helper/translate_helper.swift) との通信

翻訳（Translation.framework）と文字認識（Vision）の両方をこのヘルパーが担う。
アプリ本体のプロセスから直接フレームワークを呼ばず、別プロセスに出しているのは
次の2つの理由による。

- Translation.framework は Objective-C に公開されておらず PyObjC から呼べない
- Vision はモデル構築の初回に約40秒かかり、その初回が e5rt エラーで失敗すると、
  そのプロセスでは以後の要求がすべて即座に失敗する。別プロセスなら作り直せる

モデルの読み込みはプロセスごとに発生するため、起動したまま使い回す。
"""
import json
import os
import select
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


class HelperError(Exception):
    """ヘルパーとのやり取りに失敗したことを表す例外"""
    pass


def find_helper() -> Optional[Path]:
    """
    translate-helper の場所を探す

    .app にバンドルされている場合は Contents/Resources/ 配下、
    リポジトリから直接実行している場合は helper/ 配下に置かれる。
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
    repo_root = Path(__file__).parent.parent
    candidates.append(repo_root / 'helper' / 'translate-helper')

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


class HelperProcess:
    """常駐させたヘルパーに1行送って1行受け取る"""

    def __init__(self, timeout: int = 120, helper_path: Optional[Path] = None):
        """
        Args:
            timeout: 応答を待つ既定の秒数
            helper_path: ヘルパーの場所（省略時は自動で探す）

        Raises:
            RuntimeError: ヘルパーが見つからない場合
        """
        self.timeout = timeout
        self.helper_path = helper_path or find_helper()
        if self.helper_path is None:
            raise RuntimeError(
                "ヘルパー (translate-helper) が見つかりません。"
                "./build_app.sh でビルドし直してください"
            )
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def request(self, payload: dict, timeout: Optional[float] = None) -> dict:
        """ヘルパーに依頼して結果を受け取る"""
        wait = self.timeout if timeout is None else timeout

        with self._lock:
            process = self._ensure_process()
            try:
                process.stdin.write(json.dumps(payload) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                self._stop()
                raise HelperError(f"ヘルパーへの送信に失敗しました: {e}") from e

            line = self._read_line(process, wait)

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            raise HelperError(f"ヘルパーの応答を解釈できませんでした: {line[:200]}") from e

    def run_once(self, payload: dict, extra_args: Optional[list] = None,
                 timeout: Optional[float] = None) -> dict:
        """使い捨てのプロセスで1回だけ実行する（言語の確認など）"""
        command = [str(self.helper_path)] + (extra_args or [])
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=self.timeout if timeout is None else timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise HelperError("ヘルパーが時間内に応答しませんでした") from e
        except OSError as e:
            raise HelperError(f"ヘルパーを起動できませんでした: {e}") from e

        stdout = (completed.stdout or '').strip()
        if not stdout:
            stderr = (completed.stderr or '').strip()
            raise HelperError(f"ヘルパーが応答しませんでした: {stderr or '出力なし'}")

        try:
            return json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError as e:
            raise HelperError(f"ヘルパーの応答を解釈できませんでした: {stdout[:200]}") from e

    def restart(self):
        """ヘルパーを作り直す（失敗が続くプロセスを捨てるため）"""
        with self._lock:
            self._stop()

    def close(self):
        """ヘルパーを終了する（アプリ終了時に呼ぶ）"""
        self.restart()

    def is_running(self) -> bool:
        """ヘルパーが動いているか"""
        return self._process is not None and self._process.poll() is None

    def _read_line(self, process: subprocess.Popen, timeout: float) -> str:
        """タイムアウト付きで1行読む（呼び出し側でロックを保持していること）"""
        ready, _, _ = select.select([process.stdout], [], [], timeout)
        if not ready:
            self._stop()
            raise HelperError(f"ヘルパーの応答がありませんでした（{timeout:.0f}秒）")

        line = process.stdout.readline()
        if not line:
            self._stop()
            raise HelperError("ヘルパーが終了しました")
        return line.strip()

    def _ensure_process(self) -> subprocess.Popen:
        """常駐プロセスを起動する（既に動いていればそれを返す）"""
        if self._process is not None and self._process.poll() is None:
            return self._process

        # ヘルパーの診断出力は捨てずにログへ回す
        log_path = Path.home() / 'Library' / 'Logs' / 'ScreenTranslator-helper.log'
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            stderr = open(log_path, 'a', buffering=1)
        except OSError:
            stderr = subprocess.DEVNULL

        try:
            self._process = subprocess.Popen(
                [str(self.helper_path), '--serve'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr,
                text=True,
                bufsize=1,
            )
        except OSError as e:
            raise HelperError(f"ヘルパーを起動できませんでした: {e}") from e
        return self._process

    def _stop(self):
        """常駐プロセスを止める（呼び出し側でロックを保持していること）"""
        process, self._process = self._process, None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


_shared: Optional[HelperProcess] = None
_shared_lock = threading.Lock()


def get_shared_helper(timeout: int = 120) -> HelperProcess:
    """アプリ全体で1本のヘルパーを共有する"""
    global _shared
    with _shared_lock:
        if _shared is None:
            _shared = HelperProcess(timeout=timeout)
        return _shared
