# Screen Capture Translator

Macで動作する画面キャプチャ翻訳アプリ。画面上の任意の範囲を選択し、英語テキストをOCRで認識して日本語に翻訳表示します。

## 機能

- **ホットキー** (Cmd+Shift+T) でキャプチャモード起動
- マウスドラッグで画面範囲を選択
- Apple Vision Framework による高精度OCR
- **Apple Translation.framework によるオンデバイス翻訳**（通信なし・レート制限なし）
- システムトレイ常駐型アプリ
- 設定ファイルによるカスタマイズ
- 詳細なロギング機能

## 動作確認

インストール済みの `.app` に対してスモークテストを実行できます。

```bash
./smoke_test.sh
```

署名・ヘルパー・文字認識・翻訳・翻訳言語の有無・起動中のアプリの状態をまとめて確認します。
**venv で動いてもバンドルの中では動かないことが実際にあったため、修正したら必ずこれを通してください。**

## 翻訳エンジンについて

以前は Google 翻訳（deep-translator）を使っていましたが、これは
`https://translate.google.com/m` をスクレイピングする方式で、Google 側の
ボット検出により HTTP 429 / sorry ページが返るようになり恒常的に失敗するため廃止しました。

現在は Apple の Translation.framework をオンデバイスで使用します。
Translation.framework は Objective-C に公開されていないため PyObjC からは呼べず、
Swift で書いた補助実行ファイル `helper/translate_helper.swift` を常駐させて
JSON でやり取りしています。

## OCR について

文字認識（Vision）も同じヘルパーが担当します。アプリ本体から PyObjC で
Vision を呼ぶ方式は、この環境では次の問題がありました。

- `.app` の中では初回のモデル構築に約35〜40秒かかる
- その初回が `CRImageReaderError.e5rtError(..., 13)` で失敗することがある
- 一度失敗すると、そのプロセスでは以後の認識要求が即座に失敗し続ける
  （アプリ本体で起きると、再起動するまで文字が一切読めなくなる）

別プロセスに出しておけば、失敗を検知してヘルパーを作り直すだけで復帰できます。
初回のモデル構築はアプリ起動時のバックグラウンド暖機で済ませており、
同じビルドの2回目以降の起動では 0.2 秒程度で終わります
（アプリを再ビルドすると、新しい署名に対して1回だけ再構築が走ります）。

## 必要環境

- Apple Silicon の Mac（`build_app.sh` が `arm64-apple-macos26.0` 向けにビルドします）
- macOS 26 以降（Translation.framework の `installedSource` 初期化子を使うため）
- Python 3.11+
- Xcode Command Line Tools（`swiftc` でヘルパーをビルドするため）
- システム設定 › 一般 › 言語と地域 › 翻訳言語 に、翻訳元・翻訳先の言語がダウンロード済みであること

## インストール

```bash
# 1. 依存関係のインストール
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 署名用の証明書を用意（初回のみ。sudo のパスワードを聞かれます）
#    これをやっておくと、以後どれだけ再ビルドしても
#    画面収録・アクセシビリティの許可がリセットされません
./scripts/signing-cert.sh

# 3. アプリケーションのビルド（Swift ヘルパーのビルドと署名も行われます）
./build_app.sh

# 4. アプリケーションフォルダにインストール
./install_app.sh

# 5. アプリを起動
open /Applications/ScreenTranslator.app
```

### 設定ファイル

実際に読み込まれる設定は次の場所にあります（初回起動時にリポジトリの `config.yaml` から複製されます）:

```
~/Library/Application Support/ScreenTranslator/config.yaml
```

バンドルの外にあるので、翻訳元・翻訳先の言語やログレベルを変えるのにアプリの再ビルドは不要です。
ログの既定の出力先は `~/Library/Logs/ScreenTranslator.log` です。

初回起動時に以下の権限許可が必要です:
- **画面収録**: スクリーンショット撮影のため
- **アクセシビリティ**: ショートカットキー監視のため
- **入力監視**: ホットキーの検知のため（許可が無いとホットキーが黙って反応しません）

## 使い方

1. アプリ起動後、メニューバーにアイコンが表示されます
2. `Cmd+Shift+T` を押すと画面全体が暗くなります
3. マウスでドラッグして翻訳したい範囲を選択
4. 選択した範囲のテキストがOCR→翻訳されて表示されます
5. 結果ウィンドウから原文・翻訳文をクリップボードにコピー可能

## 設定のカスタマイズ

`~/Library/Application Support/ScreenTranslator/config.yaml` を編集します
（リポジトリ直下の `config.yaml` はそこへ複製されるひな形です）。

```yaml
# 翻訳設定
translation:
  engine: "apple"    # 現在は "apple"（Apple のオンデバイス翻訳）のみ
  source_lang: "en"  # 翻訳元言語（Apple 翻訳では "auto" は使えません）
  target_lang: "ja"  # 翻訳先言語
  timeout: 45        # 翻訳1回を待つ秒数

# UI設定
ui:
  theme: "dark"      # テーマ: "dark" または "light"
  window_width: 600
  window_height: 500

# デバッグ設定
debug:
  save_failed_capture: false  # 下記「取り込んだ画像の保存について」を参照

# ロギング設定
logging:
  level: "INFO"      # ログレベル: DEBUG, INFO, WARNING, ERROR
  file: "~/Library/Logs/ScreenTranslator.log"
```

設定変更後、アプリを再起動してください。

`config.yaml` には `hotkey:` の項目もありますが、**現状ホットキーは Cmd+Shift+T 固定で、
この項目はまだ実装に反映されません**。

## プライバシー

- 翻訳は Apple の Translation.framework によるオンデバイス処理で、
  **画面の内容が外部に送信されることはありません**。ヘルパーとのやり取りは
  標準入出力のパイプのみで、ネットワーク通信は行いません
- ログに記録するのは処理した**文字数だけ**で、原文・訳文そのものは残しません
- ホットキーの監視は Cmd+Shift+T の判定だけを行い、打鍵内容は記録しません

### 取り込んだ画像の保存について

OCR が何も読み取れなかったとき、原因調査のために取り込んだ画面画像を
`~/Library/Logs/ScreenTranslator-failed-capture.png` に保存できます。
**画面の内容がそのままディスクに残るため、既定では無効**です。
調査が必要なときだけ設定の `debug.save_failed_capture` を `true` にしてください。

## トラブルシューティング

### テキストが検出されない

- 選択範囲が小さすぎる可能性があります。より広い範囲を選択してください
- 画像の解像度が低い場合、OCRの精度が下がります
- ログファイル (`~/Library/Logs/ScreenTranslator.log`) を確認してください
- 設定の `debug.save_failed_capture` を `true` にすると、何が取り込まれていたかを画像で確認できます

### 翻訳が失敗する

- 翻訳はオンデバイスで行うため通信は不要です。まず システム設定 › 一般 › 言語と地域 ›
  翻訳言語 に翻訳元・翻訳先の言語がダウンロード済みか確認してください
- ログファイルでエラーの詳細を確認できます

### ホットキーが動作しない

- システム設定 > プライバシーとセキュリティ > アクセシビリティ で、アプリに権限が付与されているか確認してください
- システム設定 > プライバシーとセキュリティ > 入力監視 も確認してください
- ホットキーは Cmd+Shift+T 固定です。他のアプリと競合している場合、現状は変更できません

### ログの確認

```bash
# リアルタイムでログを確認
tail -f ~/Library/Logs/ScreenTranslator.log

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

GNU General Public License v3.0 or later (GPL-3.0-or-later)。全文は [LICENSE](LICENSE) にあります。

GUI に使用している **PyQt6 が GPL-3.0-only** のため、それに合わせています
（`build_app.sh` が生成する `.app` は PyQt6 を同梱するため、配布する場合は
結合物全体が GPLv3 の条件に従います）。

主な依存ライブラリのライセンス:

| ライブラリ | ライセンス |
| --- | --- |
| PyQt6 | GPL-3.0-only |
| PyQt6-Qt6 | LGPL-3.0 |
| pynput | LGPL-3.0 |
| mss, Pillow, PyObjC, PyYAML, pyperclip, py2app | MIT / BSD |
