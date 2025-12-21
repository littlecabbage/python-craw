#!/usr/bin/env python3
"""
GitHub Secret 配置脚本
使用 GitHub API 自动配置 WECHAT_WEBHOOK_URL Secret
"""

import base64
import json
import sys
import os
from pathlib import Path

try:
    import requests
    from nacl import encoding
    from nacl.public import PublicKey, Box, PrivateKey
except ImportError as e:
    print(f"错误: 缺少必要的依赖库")
    print(f"请安装: pip install requests pynacl")
    print(f"或使用: uv pip install requests pynacl")
    sys.exit(1)


REPO_OWNER = "littlecabbage"
REPO_NAME = "python-craw"
SECRET_NAME = "WECHAT_WEBHOOK_URL"
WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0"


def get_public_key(token: str) -> tuple[str, str]:
    """获取仓库的公钥"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    return data["key"], data["key_id"]


def encrypt_secret(public_key: str, secret_value: str) -> str:
    """使用公钥加密 Secret"""
    public_key_bytes = base64.b64decode(public_key)
    public_key_obj = PublicKey(public_key_bytes)
    
    # 创建临时密钥对
    private_key = PrivateKey.generate()
    box = Box(private_key, public_key_obj)
    
    # 加密 secret
    encrypted = box.encrypt(secret_value.encode('utf-8'))
    
    # 返回 base64 编码的加密数据
    return base64.b64encode(encrypted.ciphertext).decode('utf-8')


def create_secret(token: str, encrypted_value: str, key_id: str) -> bool:
    """创建或更新 GitHub Secret"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/{SECRET_NAME}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    
    response = requests.put(url, headers=headers, json=data)
    
    if response.status_code in [201, 204]:
        return True
    else:
        print(f"错误: API 返回状态码 {response.status_code}")
        print(f"响应: {response.text}")
        return False


def main():
    print("=" * 60)
    print("GitHub Secret 配置工具")
    print("=" * 60)
    print(f"仓库: {REPO_OWNER}/{REPO_NAME}")
    print(f"Secret 名称: {SECRET_NAME}")
    print(f"Webhook URL: {WEBHOOK_URL[:50]}...")
    print()
    
    # 获取 GitHub Token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("请提供 GitHub Personal Access Token")
        print()
        print("方法 1: 设置环境变量")
        print("  export GITHUB_TOKEN=your_token_here")
        print("  python scripts/setup_github_secret.py")
        print()
        print("方法 2: 作为命令行参数")
        print("  python scripts/setup_github_secret.py your_token_here")
        print()
        print("获取 Token:")
        print("  1. 访问 https://github.com/settings/tokens")
        print("  2. 点击 'Generate new token (classic)'")
        print("  3. 选择权限: repo (Full control of private repositories)")
        print("  4. 生成并复制 Token")
        print()
        
        if len(sys.argv) > 1:
            token = sys.argv[1]
        else:
            sys.exit(1)
    
    try:
        # 步骤 1: 获取公钥
        print("步骤 1/3: 获取仓库公钥...")
        public_key, key_id = get_public_key(token)
        print("✓ 获取公钥成功")
        print()
        
        # 步骤 2: 加密 Secret
        print("步骤 2/3: 加密 Secret...")
        encrypted_value = encrypt_secret(public_key, WEBHOOK_URL)
        print("✓ Secret 加密成功")
        print()
        
        # 步骤 3: 创建 Secret
        print("步骤 3/3: 创建/更新 GitHub Secret...")
        if create_secret(token, encrypted_value, key_id):
            print("✓ Secret 配置成功！")
            print()
            print("=" * 60)
            print("配置完成！")
            print("=" * 60)
            print()
            print("现在可以:")
            print("1. 前往 https://github.com/littlecabbage/python-craw/actions")
            print("2. 手动触发 '手动触发生成日报' 工作流")
            print("3. 检查企业微信群是否收到通知")
            print()
        else:
            print("✗ Secret 配置失败")
            sys.exit(1)
            
    except requests.exceptions.RequestException as e:
        print(f"✗ 网络请求失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()



