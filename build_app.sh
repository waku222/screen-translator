#!/bin/bash
set -e

# スクリプトのディレクトリに移動
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 署名に使う証明書。scripts/signing-cert.sh で作る自己署名証明書を既定とする。
# 見つからない場合は adhoc 署名にフォールバックするが、その場合は再ビルドのたびに
# 画面収録・アクセシビリティの許可がリセットされる。
SIGN_IDENTITY="${SCREEN_TRANSLATOR_SIGN_IDENTITY:-Screen Translator Local}"

echo "=== Building Screen Translator App ==="

# 1. Swift 製の翻訳ヘルパーをビルド
#    Translation.framework は Objective-C に公開されていないため PyObjC からは呼べない。
#    このヘルパーを subprocess 経由で使う。
echo "Building translation helper (Swift)..."
swiftc -O -parse-as-library -target arm64-apple-macos26.0 \
  helper/translate_helper.swift -o helper/translate-helper

# 2. 依存関係のインストール
echo "Installing/Updating dependencies..."
./venv/bin/pip install -r requirements.txt

# 3. クリーンアップ
echo "Cleaning previous builds..."
rm -rf build dist

# 4. ビルド実行
echo "Building .app bundle..."
./venv/bin/python setup.py py2app

# 5. 署名
#    バンドル内の実行ファイルは配置後に署名する必要があるため、--deep で一括署名する。
if security find-identity -v -p codesigning | grep -q "$SIGN_IDENTITY"; then
  echo "Signing with: $SIGN_IDENTITY"
  codesign --force --deep --sign "$SIGN_IDENTITY" dist/ScreenTranslator.app
else
  echo "⚠️  証明書「$SIGN_IDENTITY」が見つかりません。adhoc 署名にフォールバックします。"
  echo "   （再ビルドのたびに画面収録・アクセシビリティの許可がリセットされます）"
  echo "   証明書を作るには: ./scripts/signing-cert.sh"
  codesign --force --deep --sign - dist/ScreenTranslator.app
fi

codesign -dv dist/ScreenTranslator.app 2>&1 | grep -E "Signature|Identifier|TeamIdentifier" || true

echo "=== Build Complete ==="
echo "The application is located at: $SCRIPT_DIR/dist/ScreenTranslator.app"
echo "インストールは ./install_app.sh を使ってください。"
