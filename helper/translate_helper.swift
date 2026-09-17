//
//  translate_helper
//
//  Apple の Translation.framework（オンデバイス翻訳）を CLI から使うための補助実行ファイル。
//  Translation.framework は Objective-C に公開されていないため PyObjC からは呼べない。
//  そのため Python 本体からは本ヘルパーを subprocess で起動し、JSON で受け渡しする。
//
//  入出力（いずれも stdin/stdout の UTF-8 JSON）:
//    翻訳:   {"text": "...", "source": "en", "target": "ja"}
//         -> {"ok": true, "text": "..."}  /  {"ok": false, "error": "..."}
//    可用性: 引数 --check を付けると stdin は {"source": "en", "target": "ja"} のみ
//         -> {"ok": true, "status": "installed" | "supported" | "unsupported"}
//
//  status の意味:
//    installed   … 言語パックがダウンロード済みで、すぐ翻訳できる
//    supported   … 対応言語だが未ダウンロード（システム設定からの取得が必要）
//    unsupported … 非対応の言語ペア
//

import Foundation
import Translation

/// stdin から受け取るリクエスト
struct Request: Decodable {
    let text: String?
    let source: String?
    let target: String?
}

/// stdout に返すレスポンス
struct Response: Encodable {
    var ok: Bool
    var text: String?
    var status: String?
    var error: String?
}

@main
struct TranslateHelper {

    static func main() async {
        do {
            let request = try readRequest()
            let source = Locale.Language(identifier: request.source ?? "en")
            let target = Locale.Language(identifier: request.target ?? "ja")

            if CommandLine.arguments.contains("--check") {
                let status = await LanguageAvailability().status(from: source, to: target)
                emit(Response(ok: true, status: name(of: status)))
                return
            }

            guard let text = request.text, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                emit(Response(ok: true, text: ""))
                return
            }

            // installedSource 版の初期化子は SwiftUI なしでセッションを作れる（macOS 26 以降）。
            // 言語パック未取得の場合はここではなく translate() が notInstalled で落ちる。
            let session = TranslationSession(installedSource: source, target: target)
            let response = try await session.translate(text)
            emit(Response(ok: true, text: response.targetText))

        } catch {
            emit(Response(ok: false, error: describe(error)))
            exit(1)
        }
    }

    /// stdin を JSON として読み込む
    static func readRequest() throws -> Request {
        let data = FileHandle.standardInput.readDataToEndOfFile()
        guard !data.isEmpty else {
            throw HelperError.emptyInput
        }
        return try JSONDecoder().decode(Request.self, from: data)
    }

    /// stdout に JSON を1行で書き出す
    static func emit(_ response: Response) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.withoutEscapingSlashes]
        guard let data = try? encoder.encode(response),
              let json = String(data: data, encoding: .utf8) else {
            print(#"{"ok": false, "error": "failed to encode response"}"#)
            return
        }
        print(json)
    }

    static func name(of status: LanguageAvailability.Status) -> String {
        switch status {
        case .installed: return "installed"
        case .supported: return "supported"
        case .unsupported: return "unsupported"
        @unknown default: return "unknown"
        }
    }

    /// Translation.framework の代表的なエラーは原因が分かる日本語に置き換える
    static func describe(_ error: Error) -> String {
        switch error {
        case TranslationError.notInstalled:
            return "翻訳言語がダウンロードされていません。システム設定 › 一般 › 言語と地域 › 翻訳言語 で追加してください"
        case TranslationError.unsupportedLanguagePairing:
            return "この言語の組み合わせには対応していません"
        case TranslationError.unsupportedSourceLanguage:
            return "翻訳元の言語に対応していません"
        case TranslationError.unsupportedTargetLanguage:
            return "翻訳先の言語に対応していません"
        case TranslationError.nothingToTranslate:
            return "翻訳できるテキストがありません"
        default:
            return error.localizedDescription
        }
    }
}

enum HelperError: LocalizedError {
    case emptyInput

    var errorDescription: String? {
        switch self {
        case .emptyInput: return "リクエストが空です"
        }
    }
}
