#!/bin/bash
set -e

# スクリプトのディレクトリに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=== Building Screen Translator App ==="

# 1. 依存関係のインストール
echo "Installing/Updating dependencies..."
./venv/bin/pip install -r requirements.txt

# 2. クリーンアップ
echo "Cleaning previous builds..."
rm -rf build dist

# 3. ビルド実行
echo "Building .app bundle..."
./venv/bin/python setup.py py2app

echo "=== Build Complete ==="
echo "The application is located at: $SCRIPT_DIR/dist/ScreenTranslator.app"
echo "You can move this to your Applications folder."
