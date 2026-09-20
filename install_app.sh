#!/bin/bash
set -euo pipefail

# ビルド済みの dist/ScreenTranslator.app を /Applications に入れ替える。
# 古い版は削除せず ~/.Trash に移す（取り消せるようにするため）。

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

APP_NAME="ScreenTranslator.app"
SOURCE_APP="$SCRIPT_DIR/dist/$APP_NAME"
DEST_DIR="/Applications"
# 旧版からの移行用。以前は launchd でスクリプトを起動しており、2つの名前が使われていた。
# 該当のファイルが無ければ何もしない。
OLD_PLISTS=(
    "$HOME/Library/LaunchAgents/com.user.start.translation.plist"
    "$HOME/Library/LaunchAgents/com.user.screentranslator.plist"
)

echo "=== Installing Screen Translator ==="

if [ ! -d "$SOURCE_APP" ]; then
    echo "エラー: $SOURCE_APP がありません。先に ./build_app.sh を実行してください。" >&2
    exit 1
fi

# 1. 動いている旧版を終了する
if pgrep -f "$DEST_DIR/$APP_NAME/Contents/MacOS/ScreenTranslator" >/dev/null 2>&1; then
    echo "Quitting running app..."
    osascript -e 'tell application "ScreenTranslator" to quit' 2>/dev/null || \
      pkill -f "$DEST_DIR/$APP_NAME/Contents/MacOS/ScreenTranslator" || true
    sleep 2
fi

# 2. 旧版の LaunchAgent が残っていれば片付ける
#    既に存在しないスクリプトを指したままだと RunAtLoad がログインのたびに失敗する。
#    現在はログイン時の自動起動をシステム設定のログイン項目で行う。
for OLD_PLIST in "${OLD_PLISTS[@]}"; do
    if [ -f "$OLD_PLIST" ]; then
        echo "Removing old Launch Agent: $(basename "$OLD_PLIST")"
        launchctl unload "$OLD_PLIST" 2>/dev/null || true
        mv "$OLD_PLIST" "$HOME/.Trash/$(basename "$OLD_PLIST").$(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    fi
done

# 3. 旧版をゴミ箱へ移してから新版を配置する
if [ -d "$DEST_DIR/$APP_NAME" ]; then
    TRASHED="$HOME/.Trash/$APP_NAME.$(date +%Y%m%d-%H%M%S)"
    echo "Moving existing installation to Trash: $TRASHED"
    mv "$DEST_DIR/$APP_NAME" "$TRASHED"
fi

echo "Installing $APP_NAME to $DEST_DIR..."
cp -R "$SOURCE_APP" "$DEST_DIR/"

echo "=== Installation Complete! ==="
codesign -dv "$DEST_DIR/$APP_NAME" 2>&1 | grep -E "Signature|Identifier" || true
echo
echo "1. '$DEST_DIR/$APP_NAME' を起動してください。"
echo "2. 初回は画面収録・アクセシビリティ・入力監視の許可を求められます（署名が変わるため今回だけ）。"
echo "3. ログイン時の自動起動は システム設定 › 一般 › ログイン項目 で追加します。"
