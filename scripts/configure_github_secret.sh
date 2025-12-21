#!/bin/bash
# 配置 GitHub Secret 脚本
# 使用方法: ./configure_github_secret.sh <GITHUB_TOKEN>

set -e

REPO_OWNER="littlecabbage"
REPO_NAME="python-craw"
SECRET_NAME="WECHAT_WEBHOOK_URL"
WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0"

if [ -z "$1" ]; then
    echo "错误: 请提供 GitHub Personal Access Token"
    echo "使用方法: $0 <GITHUB_TOKEN>"
    echo ""
    echo "获取 Token 方法:"
    echo "1. 访问 https://github.com/settings/tokens"
    echo "2. 点击 'Generate new token (classic)'"
    echo "3. 选择权限: repo (Full control of private repositories)"
    echo "4. 生成并复制 Token"
    exit 1
fi

GITHUB_TOKEN="$1"

echo "正在配置 GitHub Secret..."
echo "仓库: $REPO_OWNER/$REPO_NAME"
echo "Secret 名称: $SECRET_NAME"
echo ""

# 使用 GitHub API 创建或更新 Secret
# 需要先获取仓库的 public key
echo "1. 获取仓库公钥..."
PUBLIC_KEY_RESPONSE=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/secrets/public-key")

PUBLIC_KEY=$(echo $PUBLIC_KEY_RESPONSE | grep -o '"key":"[^"]*' | cut -d'"' -f4)
KEY_ID=$(echo $PUBLIC_KEY_RESPONSE | grep -o '"key_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$PUBLIC_KEY" ] || [ -z "$KEY_ID" ]; then
    echo "错误: 无法获取仓库公钥"
    echo "请检查:"
    echo "1. Token 是否有正确的权限"
    echo "2. 仓库名称是否正确"
    exit 1
fi

echo "✓ 获取公钥成功"
echo ""

# 使用 libsodium 加密 secret (需要安装 libsodium)
echo "2. 加密 Secret..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 需要 Python 3 来加密 Secret"
    exit 1
fi

# 使用 Python 和 PyNaCl 加密
ENCRYPTED_SECRET=$(python3 << EOF
import base64
import json
import os
import sys

try:
    from nacl import encoding
    from nacl.public import PublicKey, Box
except ImportError:
    print("错误: 需要安装 PyNaCl 库", file=sys.stderr)
    print("安装方法: pip install pynacl", file=sys.stderr)
    sys.exit(1)

public_key = "$PUBLIC_KEY"
secret_value = "$WEBHOOK_URL"

# 解码公钥
public_key_bytes = base64.b64decode(public_key)
public_key_obj = PublicKey(public_key_bytes)

# 创建临时密钥对
from nacl.public import PrivateKey
private_key = PrivateKey.generate()
box = Box(private_key, public_key_obj)

# 加密 secret
encrypted = box.encrypt(secret_value.encode('utf-8'))

# 返回 base64 编码的加密数据
encrypted_value = base64.b64encode(encrypted.ciphertext).decode('utf-8')
print(encrypted_value)
EOF
)

if [ $? -ne 0 ]; then
    echo ""
    echo "错误: Secret 加密失败"
    echo "请安装 PyNaCl: pip install pynacl"
    exit 1
fi

echo "✓ Secret 加密成功"
echo ""

# 创建或更新 Secret
echo "3. 创建/更新 GitHub Secret..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/actions/secrets/$SECRET_NAME" \
    -d "{\"encrypted_value\":\"$ENCRYPTED_SECRET\",\"key_id\":\"$KEY_ID\"}")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✓ Secret 配置成功！"
    echo ""
    echo "配置完成！现在 GitHub Actions 工作流将自动使用企业微信推送功能。"
    echo ""
    echo "测试方法:"
    echo "1. 前往 https://github.com/$REPO_OWNER/$REPO_NAME/actions"
    echo "2. 手动触发 '手动触发生成日报' 工作流"
    echo "3. 检查企业微信群是否收到通知"
else
    echo "错误: 配置失败 (HTTP $HTTP_CODE)"
    echo "响应: $BODY"
    exit 1
fi



