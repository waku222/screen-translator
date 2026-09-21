# Screen Capture Translator

Macで動作する画面キャプチャ翻訳アプリ。画面上の任意の範囲を選択し、英語テキストをOCRで認識して日本語に翻訳表示します。

## 機能

- **メニューバーのアイコン**からキャプチャモード起動
- **ホットキー**（既定 Ctrl+Option+T、設定で変更可）でも起動
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

1. アプリ起動後、画面上部のメニューバーにアイコンが表示されます
2. **アイコンをクリックして「🌐 翻訳」を選ぶ**と、画面全体が暗くなります
   （ホットキー `Ctrl+Option+T` でも同じことができます）
3. マウスでドラッグして翻訳したい範囲を選択
4. 選択した範囲のテキストがOCR→翻訳されて表示されます
5. 結果ウィンドウから原文・翻訳文をクリップボードにコピー可能

メニューバーのアイコンからの操作には権限が要りません。ホットキーを使う場合だけ
「入力監視」の許可が必要です。

## 設定のカスタマイズ

`~/Library/Application Support/ScreenTranslator/config.yaml` を編集します
（リポジトリ直下の `config.yaml` はそこへ複製されるひな形です）。

```yaml
# ホットキー設定
hotkey:
  modifiers: ["ctrl", "alt"]  # cmd / shift / ctrl / alt（option でも可）
  key: "t"                    # 英字 a-z と数字 0-9

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

### ホットキーの選び方

**押されたキーは前面のアプリにもそのまま渡ります。** 他のアプリが同じ組み合わせを
使っていると、翻訳と同時にそのアプリの機能も動いてしまいます。

既定を `Ctrl+Option+T` にしているのはこのためです。以前の既定だった `Cmd+Shift+T` は
Chrome の「閉じたタブを再度開く」と衝突し、翻訳しようとするとタブが開いてしまいました。

変更するときは、使っているアプリが割り当てていない組み合わせを選んでください。
設定が解釈できない場合はログに記録した上で既定の `Ctrl+Option+T` で起動します。

## プライバシー

- 翻訳は Apple の Translation.framework によるオンデバイス処理で、
  **画面の内容が外部に送信されることはありません**。ヘルパーとのやり取りは
  標準入出力のパイプのみで、ネットワーク通信は行いません
- ログに記録するのは処理した**文字数だけ**で、原文・訳文そのものは残しません
- ホットキーの監視は設定した組み合わせが押されたかの判定だけを行い、打鍵内容は記録しません

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

まず**メニューバーのアイコンから「🌐 翻訳」**を試してください。これが動けばアプリ自体は
正常で、原因はホットキーに限られます。

- システム設定 > プライバシーとセキュリティ > 入力監視 で、アプリに権限が付与されているか
  確認してください（ホットキーにはこの許可が必要です）
- システム設定 > プライバシーとセキュリティ > アクセシビリティ も確認してください
- 翻訳は動くが同時に別のことも起きる場合、他のアプリと組み合わせが衝突しています。
  上記「ホットキーの選び方」を参照して、設定で別の組み合わせに変えてください
- メニューバーのアイコンに現在のホットキーが表示されます（例: `🌐 翻訳 (Ctrl+Option+T)`）。
  設定を変えたのに表示が変わらない場合、アプリを再起動してください

#### 入力監視が「許可済み」に見えるのに効かない場合

システム設定の一覧に ScreenTranslator があり、スイッチもオンなのに
ホットキーが無反応なことがあります。ログを見ると分かります。

```
ERROR - Hotkey listener is running but deaf (Ctrl+Option+T): 入力監視が許可されていません
```

macOS は「どのアプリか」を**署名の条件として**記録します。adhoc 署名の版で
一度許可を与えていると、実行ファイルのハッシュで記録されるため、
`.app` を作り直すたびに記録と一致しなくなります。一覧の行とスイッチは
残るので、見た目は許可済みのままです。

**スイッチのオフ／オンでは直りません。** それは許可の値を反転するだけで、
記録された署名の条件には触れないためです。次の手順で記録を作り直してください。

1. システム設定 › プライバシーとセキュリティ › 入力監視 で ScreenTranslator を選ぶ
2. **「−」ボタンで一覧から削除する**
3. **「＋」ボタンで `/Applications/ScreenTranslator.app` を追加し直す**
4. アプリを終了して起動し直す

`scripts/signing-cert.sh` で作った証明書で署名してあれば、一度通した許可は
作り直しても外れません（指定要件が実行ファイルのハッシュではなく証明書に
なるため）。`codesign -d --requirements - /Applications/ScreenTranslator.app` で
`certificate leaf = ...` と出ていれば、その状態です。

なお、ホットキーが効かないあいだもメニューバーからは使えます。
メニューの操作はアプリ自身のウィンドウで受け取るので、入力監視とは無関係です。

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

## 保守について

個人用に作ったものを、参考になればと公開しています。**要望や不具合への対応はお約束できません。**

動作を確認しているのは Apple Silicon の Mac と macOS 26 のみです。それ以外の環境については分かりません。

不具合を見つけたときは Issue でお知らせいただければ目を通します（返信や修正の時期はお約束できません）。
GPL-3.0 なので、自分で直して使う・改変版を再配布するのは自由です。

ビルド済みの `.app` は配布していません。Mac App Store での配布や Developer ID での
公証配布を検討した結果は [docs/distribution-options.md](docs/distribution-options.md)
にまとめてあります。

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
