#!/bin/bash
# Screen Translator 起動スクリプト

export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export LANG="ja_JP.UTF-8"

# スクリプトのディレクトリを絶対パスで取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ログディレクトリの作成
LOG_DIR="$HOME/Library/Logs/ScreenTranslator"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/app.log"

# ログ出力開始
echo "--- Starting Screen Translator at $(date) ---" >> "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "Script Dir: $SCRIPT_DIR"
echo "PATH: $PATH"

# venvのpythonを使って実行
"$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/src/main.py"
