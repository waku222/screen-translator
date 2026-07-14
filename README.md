# Screen Capture Translator

Macで動作する画面キャプチャ翻訳アプリ。画面上の任意の範囲を選択し、英語テキストをOCRで認識して日本語に翻訳表示します。

## 機能

- **カスタマイズ可能なホットキー** (デフォルト: Cmd+Shift+T) でキャプチャモード起動
- マウスドラッグで画面範囲を選択
- Apple Vision Framework による高精度OCR
- Google Translate による多言語翻訳
- システムトレイ常駐型アプリ
- 設定ファイルによるカスタマイズ
- 詳細なロギング機能

## 必要環境

- macOS 10.15 (Catalina) 以降
- Python 3.11+

## インストール

### 方法1: アプリケーションとしてビルド (推奨)

```bash
# 1. 依存関係のインストール
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. アプリケーションのビルド
./build_app.sh

# 3. アプリケーションフォルダに移動
mv dist/ScreenTranslator.app /Applications/

# 4. アプリを起動
open /Applications/ScreenTranslator.app
```

### 方法2: Pythonスクリプトとして実行

```bash
# 1. セットアップスクリプトを実行
./setup.sh

# 2. アプリケーションが自動起動されます
```

初回起動時に以下の権限許可が必要です:
- **画面収録**: スクリーンショット撮影のため
- **アクセシビリティ**: ショートカットキー監視のため

## 使い方

1. アプリ起動後、メニューバーにアイコンが表示されます
2. `Cmd+Shift+T` を押すと画面全体が暗くなります
3. マウスでドラッグして翻訳したい範囲を選択
4. 選択した範囲のテキストがOCR→翻訳されて表示されます
5. 結果ウィンドウから原文・翻訳文をクリップボードにコピー可能

## 設定のカスタマイズ

`config.yaml` ファイルを編集することで、以下の設定をカスタマイズできます:

```yaml
# ホットキー設定
hotkey:
  modifiers: ["cmd", "shift"]  # 修飾キー
  key: "t"                     # キー

# 翻訳設定
translation:
  source_lang: "en"  # 翻訳元言語 ("auto"で自動検出)
  target_lang: "ja"  # 翻訳先言語

# UI設定
ui:
  theme: "dark"      # テーマ: "dark" または "light"
  window_width: 600
  window_height: 500

# ロギング設定
logging:
  level: "INFO"      # ログレベル: DEBUG, INFO, WARNING, ERROR
  file: "/tmp/screen-translator.log"
```

設定変更後、アプリを再起動してください。

## トラブルシューティング

### テキストが検出されない

- 選択範囲が小さすぎる可能性があります。より広い範囲を選択してください
- 画像の解像度が低い場合、OCRの精度が下がります
- ログファイル (`/tmp/screen-translator.log`) を確認してください

### 翻訳が失敗する

- インターネット接続を確認してください
- ログファイルでエラーの詳細を確認できます

### ホットキーが動作しない

- システム設定 > プライバシーとセキュリティ > アクセシビリティ で、アプリに権限が付与されているか確認してください
- 他のアプリと同じホットキーが競合している可能性があります。`config.yaml`で別のキーに変更してください

### ログの確認

```bash
# リアルタイムでログを確認
tail -f /tmp/screen-translator.log

# ログレベルをDEBUGに変更してより詳細な情報を取得
# config.yamlのlogging.levelを"DEBUG"に変更
```

## 開発者向け

### テストの実行

```bash
# 依存関係のインストール
pip install -r requirements-dev.txt

# テストの実行
pytest tests/ -v

# カバレッジ付きでテスト
pytest tests/ --cov=src --cov-report=html
```

### コード品質チェック

```bash
# フォーマット
black src/

# リンター
flake8 src/

# 型チェック
mypy src/
```

## ライセンス

MIT License
