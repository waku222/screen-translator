#!/bin/bash
set -e

# カレントディレクトリをスクリプトの場所に移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Screen Translator Setup ==="
echo "Install Directory: $SCRIPT_DIR"

# 1. venvのセットアップ
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

echo "Installing dependencies..."
./venv/bin/pip install -r requirements.txt

# 2. 設定ファイルの確認
if [ ! -f "config.yaml" ]; then
    echo "Warning: config.yaml not found. Using default configuration."
fi

# 3. アプリケーションを直接起動
echo "Starting Screen Translator..."
./venv/bin/python src/main.py &

echo "=== Setup Complete! ===\"
echo "Screen Translator is now running in the background."
echo "Check the logs at /tmp/screen-translator.log"
