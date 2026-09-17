#!/bin/bash
set -uo pipefail

# インストール済みの .app に対する動作確認。
#
# venv で動いてもバンドルの中では動かない、ということが実際に起きたので
# （PyObjC 経由の Vision がバンドル内でのみ失敗した）、修正のたびにここまで確認する。

APP="/Applications/ScreenTranslator.app"
HELPER="$APP/Contents/Resources/translate-helper"
LOG="$HOME/Library/Logs/ScreenTranslator.log"
FAILED=0

say() { printf "%-34s %s\n" "$1" "$2"; }

echo "=== Screen Translator スモークテスト ==="

# 1. バンドルと署名
if [ -d "$APP" ]; then
  say "アプリ" "あり"
  codesign --verify --deep --strict "$APP" 2>/dev/null \
    && say "署名の検証" "OK" \
    || { say "署名の検証" "NG"; FAILED=1; }
else
  say "アプリ" "見つかりません"; exit 1
fi

# 2. ヘルパー（翻訳と文字認識の実体）
if [ -x "$HELPER" ]; then
  say "ヘルパー" "あり"
else
  say "ヘルパー" "見つかりません"; exit 1
fi

# 3. 文字認識（同梱のテスト画像を読ませる）
IMAGE="$(cd "$(dirname "$0")" && pwd)/tests/fixtures/smoke_text.png"
if [ ! -f "$IMAGE" ]; then
  say "テスト画像" "見つかりません: $IMAGE"; exit 1
fi

START=$(date +%s)
OCR_OUT=$(printf '{"op":"ocr","imagePath":"%s","languages":["en-US"]}' "$IMAGE" | "$HELPER")
OCR_TIME=$(( $(date +%s) - START ))

if echo "$OCR_OUT" | grep -q '"ok":true' && echo "$OCR_OUT" | grep -qi "smoke test"; then
  say "文字認識" "OK (${OCR_TIME}秒)"
  [ "$OCR_TIME" -gt 5 ] && echo "   ※ 初回はモデル構築で40秒前後かかります（2回目以降は1秒未満）"
else
  say "文字認識" "NG"; echo "   $OCR_OUT"; FAILED=1
fi

# 4. 翻訳
START=$(date +%s)
TR_OUT=$(echo '{"op":"translate","text":"The smoke test is running.","source":"en","target":"ja"}' | "$HELPER")
TR_TIME=$(( $(date +%s) - START ))
if echo "$TR_OUT" | grep -q '"ok":true'; then
  say "翻訳" "OK (${TR_TIME}秒)"
else
  say "翻訳" "NG"; echo "   $TR_OUT"; FAILED=1
fi

# 5. 翻訳言語の有無
AVAIL=$(echo '{"source":"en","target":"ja"}' | "$HELPER" --check)
if echo "$AVAIL" | grep -q '"status":"installed"'; then
  say "翻訳言語(en→ja)" "ダウンロード済み"
else
  say "翻訳言語(en→ja)" "$AVAIL"; FAILED=1
fi

# 6. 起動中のアプリの状態
if pgrep -f "$APP/Contents/MacOS/ScreenTranslator" >/dev/null; then
  say "アプリの起動" "起動中"
  grep -q "Screen recording permission: granted" "$LOG" 2>/dev/null \
    && say "画面収録の許可" "あり" \
    || say "画面収録の許可" "ログに記録なし（起動し直すと記録されます）"
  if tail -40 "$LOG" 2>/dev/null | grep -q "Warmup done"; then
    say "暖機" "$(tail -40 "$LOG" | grep 'Warmup done' | tail -1 | sed 's/.*Warmup done: //')"
  else
    say "暖機" "まだ完了していません"
  fi
else
  say "アプリの起動" "起動していません"
fi

echo
[ "$FAILED" -eq 0 ] && echo "すべて問題ありません" || echo "問題が見つかりました（上の NG を確認してください）"
exit $FAILED
