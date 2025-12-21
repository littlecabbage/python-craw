# 快速配置 GitHub Secret

## 方法一：使用 Python 脚本（推荐，最简单）

### 步骤

1. **安装依赖**
   ```bash
   uv pip install pynacl
   # 或
   pip install pynacl
   ```

2. **获取 GitHub Token**
   - 访问：https://github.com/settings/tokens
   - 点击 "Generate new token (classic)"
   - 选择权限：`repo` (Full control of private repositories)
   - 生成并复制 Token

3. **运行配置脚本**
   ```bash
   # 方法 1: 使用环境变量
   export GITHUB_TOKEN=your_token_here
   python scripts/setup_github_secret.py
   
   # 方法 2: 作为参数
   python scripts/setup_github_secret.py your_token_here
   ```

4. **完成！** 脚本会自动配置 Secret

## 方法二：使用 GitHub Web UI（无需工具）

1. 访问：https://github.com/littlecabbage/python-craw/settings/secrets/actions
2. 点击 "New repository secret"
3. Name: `WECHAT_WEBHOOK_URL`
4. Secret: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=a4d6c016-45aa-4356-b7fe-9d12b3525de0`
5. 点击 "Add secret"

## 验证配置

配置完成后，可以：

1. 前往 Actions 页面：https://github.com/littlecabbage/python-craw/actions
2. 选择 "手动触发生成日报"
3. 点击 "Run workflow"
4. 检查企业微信群是否收到通知

## 注意事项

- Secret 名称必须是：`WECHAT_WEBHOOK_URL`
- 配置后，两个工作流（手动触发和每日自动）都会启用推送
- 如果未配置 Secret，通知功能会自动禁用，不影响日报生成



