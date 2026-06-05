#!/bin/bash

# SSL証明書ディレクトリ作成
mkdir -p ssl

# 自己署名証明書の生成（有効期限365日）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem \
  -out ssl/cert.pem \
  -subj "/C=JP/ST=Tokyo/L=Tokyo/O=MyCompany/CN=localhost"

echo "SSL証明書を生成しました: ssl/cert.pem, ssl/key.pem"
