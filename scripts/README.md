# 配置脚本说明

本目录包含用于配置项目的辅助脚本。

## setup_github_secret.py

自动配置 GitHub Secret 的 Python 脚本。

### 使用方法

#### 方法 1: 使用环境变量（推荐）

```bash
# 1. 获取 GitHub Personal Access Token
# 访问: https://github.com/settings/tokens
# 生成 Token，权限选择: repo

# 2. 设置环境变量
export GITHUB_TOKEN=your_token_here

# 3. 运行脚本
python scripts/setup_github_secret.py
```

#### 方法 2: 作为命令行参数

```bash
python scripts/setup_github_secret.py your_token_here
```

### 前置要求

安装依赖：

```bash
pip install requests pynacl
# 或
uv pip install requests pynacl
```

### 功能

- 自动获取仓库公钥
- 使用公钥加密 Webhook URL
- 创建或更新 GitHub Secret
- 提供详细的进度反馈

### 注意事项

- Token 需要 `repo` 权限
- 脚本会自动处理加密和 API 调用
- 如果 Secret 已存在，会自动更新

## configure_github_secret.sh

Shell 脚本版本（功能相同）。

### 使用方法

```bash
chmod +x scripts/configure_github_secret.sh
./scripts/configure_github_secret.sh YOUR_GITHUB_TOKEN
```

