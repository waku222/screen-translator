#!/bin/bash
# 目的: ScreenTranslator.app を署名するための自己署名証明書をキーチェーンに作る
# 区分: external
#
# なぜ必要か:
#   現行の .app は adhoc 署名（Signature=adhoc、Designated Requirement なし）で、
#   TCC はこのアプリを cdhash（実行ファイルの署名ハッシュ）で識別している。
#   cdhash は中身のハッシュを含むため、コードを1行変えて再ビルドするだけで
#   「別のアプリ」とみなされ、画面収録・アクセシビリティ・入力監視の許可が
#   毎回リセットされる。
#
#   固定の証明書で署名すると、TCC の識別は
#     identifier "com.user.screentranslator" and certificate leaf = <この証明書>
#   になるので、以後は何度再ビルドしても許可が維持される。
#   許可を出し直すのは、この証明書に切り替える今回の1回だけ。
#
# やること:
#   1. コード署名用の自己署名証明書（有効期間10年）を openssl で作る
#   2. ログインキーチェーンに秘密鍵ごと取り込む（codesign から使えるようにする）
#   3. システムキーチェーンでコード署名用に信頼する（sudo のパスワードを聞かれる）
#
# 聞かれるもの:
#   - sudo のパスワード（手順3。信頼設定はシステムキーチェーンの変更なので必要）
#   - キーチェーンのパスワード（ロックされている場合のみ）
#
# 元に戻すには:
#   security delete-certificate -c "Screen Translator Local" ~/Library/Keychains/login.keychain-db
#   sudo security delete-certificate -c "Screen Translator Local" /Library/Keychains/System.keychain

set -euo pipefail

NAME="Screen Translator Local"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

if security find-identity -v -p codesigning | grep -q "$NAME"; then
  echo "✅ 証明書「$NAME」は既にあります。何もせず終了します。"
  security find-identity -v -p codesigning
  exit 0
fi

echo "▶ 1/3 証明書を作成します"
cat > "$WORK/openssl.cnf" <<'CNF'
[req]
distinguished_name = dn
x509_extensions = v3
prompt = no

[dn]
CN = Screen Translator Local

[v3]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
subjectKeyIdentifier = hash
CNF

openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -config "$WORK/openssl.cnf" \
  -keyout "$WORK/key.pem" -out "$WORK/cert.pem" 2>/dev/null

openssl pkcs12 -export -legacy \
  -inkey "$WORK/key.pem" -in "$WORK/cert.pem" \
  -name "$NAME" -out "$WORK/cert.p12" -passout pass:screentranslator

echo "▶ 2/3 ログインキーチェーンに取り込みます"
security import "$WORK/cert.p12" \
  -k "$HOME/Library/Keychains/login.keychain-db" \
  -P screentranslator \
  -T /usr/bin/codesign -T /usr/bin/security

echo "▶ 3/3 コード署名用に信頼します（sudo のパスワードを聞かれます）"
sudo security add-trusted-cert -d -r trustRoot -p codeSign \
  -k /Library/Keychains/System.keychain "$WORK/cert.pem"

echo
echo "=== 結果 ==="
security find-identity -v -p codesigning

echo
echo "この後 ./build_app.sh を実行すると、この証明書で署名されます。"
