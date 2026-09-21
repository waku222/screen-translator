# 配布方法の検討（2026-09-21 調査）

「このアプリを Mac App Store で売れるか」を調べた結果。
結論は **現状の構成では出せない**。当面は GitHub でのソース公開にとどめる（2026-09-21 決定）。

## 結論の要約

| 配布方法 | 年会費 | 可否 | 備考 |
| --- | --- | --- | --- |
| ソース公開（GitHub、各自でビルド） | 不要 | **採用** | GPL-3.0 のまま。現状これ |
| 自己署名 / adhoc 署名の `.app` を配布 | 不要 | 可 | Gatekeeper の手動解除が要る。更新のたび権限リセット |
| Developer ID 署名＋公証で配布 | 99 ドル | 可 | GPL のまま可。権限も自由。改修はほぼ署名周りだけ |
| Mac App Store | 99 ドル | **不可（現状）** | ライセンスとサンドボックスで作り直しが必要 |

## Mac App Store が不可な理由

### 1. ライセンス（決定的）

GUI に PyQt6 を使っているため結合物全体が GPL-3.0（→ `README.md` の「ライセンス」節、
`docs/public-release-checklist.md` の判定）。GPL v3 と App Store の利用規約
（コピー数・デバイス数の制限、DRM）は両立せず、Apple は GPL コードを含むアプリを
受け付けない（VLC が削除された前例）。

- `PyQt6` … GPL-3.0-only
- `PyQt6-Qt6` … LGPL-3.0（v3 の差し替え要件があり MAS では同様に問題視される）
- `pynput` … LGPL-3.0

回避するには Riverbank の商用 PyQt ライセンス＋Qt 商用ライセンスを買うか、
GUI を PyObjC / SwiftUI に置き換えて PyQt を外すか。自作部分の著作権は作者にあるので、
PyQt を外せば GPL の縛り自体が消える。

### 2. App Sandbox が必須（MAS は例外なし）

| 現在の実装 | サンドボックス下 |
| --- | --- |
| ホットキー: `pynput`（CGEventTap ＝入力監視）`src/hotkey_listener.py:8,181` | **不可**。入力監視・アクセシビリティは降りない。Carbon `RegisterEventHotKey` なら可だが書き直し |
| 画面取り込み: `mss`（CGWindowList 系、macOS 15 で非推奨）`src/capture/screen_capture.py:5,16` | ScreenCaptureKit に書き換えれば可 |
| 設定 `~/Library/Application Support/ScreenTranslator/` | コンテナ内に変わる。YAML 手編集の運用は成立せず設定 UI が要る |
| ログ `~/Library/Logs/ScreenTranslator.log` | 書けない。`os_log` かコンテナ内へ |
| Swift ヘルパーを subprocess で常駐 `src/helper_process.py` | 子もサンドボックスを継承。審査的には XPC サービス化が無難 |

### 3. Python アプリを MAS に載せること自体の負担

py2app バンドルの `.so` とネスト実行ファイルを全て Team ID で署名し、
hardened runtime とライブラリ検証を通す必要がある。前例はあるが消耗が大きく、
ここまで直すなら Swift/SwiftUI で書き直すほうが速い。OCR（Vision）と翻訳
（Translation.framework）は既に `helper/translate_helper.swift` にあるため、
残るのは UI・設定・ホットキーのみ。

### 4. 審査で引っかかりそうな実務的な点

- `helper/translate_helper.swift:111,163` が `TranslationSession(installedSource:)` を使うため、
  **翻訳言語が未ダウンロードのレビュアー環境では動かない**。`LanguageAvailability` を見て
  ダウンロードを促す導線が必須
- macOS 26 限定・Apple Silicon 限定は問題なし（`LSMinimumSystemVersion` で足りる）
- 機能量について「最低限の機能性」(4.2) の指摘を受ける可能性はややある

## Apple Developer Program（年間 99 ドル）が要る範囲

**App Store 用の費用ではなく、Apple に開発者として認めてもらうための費用**。
公証（Notarization）付きで自前配布するにも Developer ID 証明書が要り、それは
有料会員でないと発行できない。無料の Apple ID でもローカル開発と署名はできるが、
Developer ID 証明書は発行されない。

無料で済むのはソース公開と、署名も公証もしない `.app` の配布だけ。

### 無署名で `.app` を配ると起きること

1. **Gatekeeper**: 隔離属性が付き「開発元を検証できないため開けません」。macOS 15 以降は
   右クリック→「開く」の回避策が廃止され、システム設定 › プライバシーとセキュリティ の
   「このまま開く」を押してもらう必要がある
2. **権限がアップデートのたびにリセットされる**（このアプリでは特に痛い）。adhoc 署名だと
   TCC の記録が実行ファイルのハッシュに紐づくため、新版を配るたびにユーザーが画面収録と
   入力監視を一覧から削除して追加し直すことになる（→ `README.md`
   「入力監視が『許可済み』に見えるのに効かない場合」）。Developer ID 証明書なら証明書に
   紐づくので更新しても許可が外れない

日本からの申し込みは円建て請求で、額は改定されることがある。個人名義ならその場で完結し、
法人名義は D-U-N-S 番号が要る。

## 今後この判断を見直す条件

- 配布した `.app` を継続的に更新したくなったとき → Developer ID＋公証（99 ドル）。
  改修は `build_app.sh` の署名部分の差し替えと `notarytool` の追加でほぼ済む
- App Store を本気で狙うとき → PyQt を捨てて SwiftUI で書き直し、ホットキーを
  `RegisterEventHotKey`、キャプチャを ScreenCaptureKit、ヘルパーを XPC 化
