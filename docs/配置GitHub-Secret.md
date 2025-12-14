# 配置 GitHub Secret 指南

本指南将帮助您在 GitHub 仓库中配置企业微信 Webhook URL，以启用自动推送功能。

## 方法一：使用 GitHub Web UI（推荐）

这是最简单的方法，无需安装任何工具。

### 步骤

1. **访问仓库设置**
   - 打开仓库：https://github.com/littlecabbage/python-craw
   - 点击 "Settings" 标签

2. **进入 Secrets 配置**
   - 在左侧菜单中找到 "Secrets and variables"
   - 点击 "Actions"

3. **添加新的 Secret**
   - 点击 "New repository secret" 按钮
   - Name: `WECHAT_WEBHOOK_URL`
   - Secret: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0`
   - 点击 "Add secret"

4. **验证配置**
   - 确认 Secret 已成功创建
   - 现在可以手动触发工作流测试

### 测试配置

1. 前往 Actions 页面：https://github.com/littlecabbage/python-craw/actions
2. 选择 "手动触发生成日报" 工作流
3. 点击 "Run workflow"
4. 选择数据源（如 "both"）
5. 点击 "Run workflow" 执行
6. 检查企业微信群是否收到通知

## 方法二：使用 GitHub CLI

如果您已安装 GitHub CLI (`gh`)，可以使用命令行配置。

### 安装 GitHub CLI

**macOS:**
```bash
brew install gh
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install gh

# Fedora
sudo dnf install gh
```

### 配置步骤

1. **登录 GitHub CLI**
   ```bash
   gh auth login
   ```

2. **创建 Secret**
   ```bash
   gh secret set WECHAT_WEBHOOK_URL \
     --repo littlecabbage/python-craw \
     --body "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0"
   ```

3. **验证配置**
   ```bash
   gh secret list --repo littlecabbage/python-craw
   ```

## 方法三：使用配置脚本

项目提供了一个自动化配置脚本。

### 前置要求

1. **安装 PyNaCl**
   ```bash
   pip install pynacl
   # 或
   uv pip install pynacl
   ```

2. **获取 GitHub Personal Access Token**
   - 访问：https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限：`repo` (Full control of private repositories)
   - 生成并复制 Token

### 执行脚本

```bash
# 给脚本添加执行权限
chmod +x scripts/configure_github_secret.sh

# 运行脚本（替换 YOUR_TOKEN 为您的 GitHub Token）
./scripts/configure_github_secret.sh YOUR_TOKEN
```

## 方法四：使用 curl 和 GitHub API

如果您熟悉 API 调用，可以直接使用 GitHub API。

### 前置要求

1. **安装 PyNaCl**
   ```bash
   pip install pynacl
   ```

2. **获取 GitHub Personal Access Token**
   - 访问：https://github.com/settings/tokens
   - 生成 Token，权限：`repo`

### 配置步骤

1. **获取仓库公钥**
   ```bash
   curl -H "Authorization: token YOUR_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/repos/littlecabbage/python-craw/actions/secrets/public-key
   ```

2. **使用 Python 加密 Secret**
   ```python
   import base64
   from nacl import encoding
   from nacl.public import PublicKey, Box, PrivateKey

   public_key = "YOUR_PUBLIC_KEY"  # 从上一步获取
   secret_value = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0"

   public_key_bytes = base64.b64decode(public_key)
   public_key_obj = PublicKey(public_key_bytes)
   private_key = PrivateKey.generate()
   box = Box(private_key, public_key_obj)
   encrypted = box.encrypt(secret_value.encode('utf-8'))
   encrypted_value = base64.b64encode(encrypted.ciphertext).decode('utf-8')
   print(encrypted_value)
   ```

3. **创建 Secret**
   ```bash
   curl -X PUT \
     -H "Authorization: token YOUR_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/repos/littlecabbage/python-craw/actions/secrets/WECHAT_WEBHOOK_URL \
     -d '{"encrypted_value":"ENCRYPTED_VALUE","key_id":"KEY_ID"}'
   ```

## 验证配置

配置完成后，可以通过以下方式验证：

1. **检查 Secret 是否存在**
   - 在 GitHub Web UI 中查看 Settings → Secrets and variables → Actions
   - 应该能看到 `WECHAT_WEBHOOK_URL`

2. **测试工作流**
   - 手动触发工作流
   - 检查企业微信群是否收到通知

3. **查看工作流日志**
   - 在工作流运行日志中查看是否有 "企业微信通知已发送" 的消息

## 故障排除

### 问题：Secret 创建失败

- 检查 Token 权限是否正确
- 确认仓库名称是否正确
- 检查网络连接

### 问题：工作流中未收到通知

- 检查 Secret 名称是否为 `WECHAT_WEBHOOK_URL`
- 检查 Webhook URL 是否正确
- 查看工作流日志中的错误信息
- 确认企业微信 Webhook 是否有效

### 问题：加密失败

- 确认已安装 PyNaCl: `pip install pynacl`
- 检查 Python 版本（需要 Python 3.6+）

## 安全提示

1. **不要将 Token 提交到仓库**
   - Token 应该保存在本地
   - 已添加到 `.gitignore`

2. **定期轮换 Token**
   - 建议定期更新 Personal Access Token

3. **限制 Token 权限**
   - 只授予必要的权限（repo）

4. **保护 Webhook URL**
   - Webhook URL 包含密钥，不要泄露
   - 如果泄露，立即在企业微信中重新生成

## 相关链接

- [GitHub Secrets 文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [GitHub CLI 文档](https://cli.github.com/manual/)
- [GitHub API 文档](https://docs.github.com/en/rest)

