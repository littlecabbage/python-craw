# Trending 日报生成器

支持从多个数据源自动生成 Trending 日报的工具，包括 [Zread Trending](https://zread.ai/trending) 和 [GitHub Trending](https://github.com/trending)。

## 功能特性

- ✅ **多数据源支持**：Zread Trending 和 GitHub Trending
- ✅ **自动获取项目详情**：访问每个项目的 GitHub 页面，提取简介和亮点
- ✅ **自动中文翻译**：将英文简介和亮点自动翻译成中文
- ✅ **定时任务**：支持定时自动生成日报（可自定义时间）
- ✅ **手动触发**：支持命令行手动触发生成日报
- ✅ **进度显示**：实时显示任务执行进度
- ✅ **模板系统**：使用 Jinja2 模板，易于自定义报告格式
- ✅ **异步并发**：支持异步操作，性能优秀
- ✅ **并发控制**：使用信号量限制并发数，避免服务器过载
- ✅ **企业微信推送**：支持将日报摘要推送到企业微信群

## 环境要求

- Python 3.14+
- uv (Python 项目管理工具)

## 安装

1. 安装依赖：
```bash
uv sync
```

2. 安装 Playwright 浏览器：
```bash
uv run playwright install chromium
```

## 快速开始

### 方式一：使用主控制器（推荐）

```bash
# 生成 Zread Trending 日报（默认不发送通知）
uv run python trending_daily.py --zread

# 生成 GitHub Trending 日报（默认不发送通知）
uv run python trending_daily.py --github

# 同时生成两个日报
uv run python trending_daily.py --zread --github

# 使用配置文件
uv run python trending_daily.py --config config.json --zread

# 启动定时任务（使用配置文件）
uv run python trending_daily.py --schedule --config config.json

# 启用通知（覆盖配置）
uv run python trending_daily.py --zread --notify
```

### 方式二：使用原有脚本（仅 Zread）

```bash
uv run python zread_trending_daily.py
```

详细使用说明请查看 [docs/使用说明.md](docs/使用说明.md)

## 输出文件

所有日报文件保存在 `reports/` 目录下：

- Zread Trending: `reports/zread_trending_report_YYYYMMDD.md`
- GitHub Trending: `reports/github_trending_report_YYYYMMDD.md`

### 日报内容

每个日报包含：
- 生成时间
- 项目列表，每个项目包含：
  - **简介**：项目的详细描述（自动翻译为中文）
  - **主要语言**：项目的主要编程语言
  - **亮点**：项目的关键特性列表（最多5个）
  - **标签**：项目相关标签
  - **Stars**：GitHub Stars 数量
  - **链接**：项目详情链接


## 配置系统

项目支持通过配置文件、环境变量和命令行参数进行配置。

### 配置文件

创建 `config.json` 文件（可参考 `config.json.example`）：

```json
{
  "zread": {
    "enabled": true,
    "time": "09:00"
  },
  "github": {
    "enabled": true,
    "time": "09:30"
  },
  "report": {
    "formats": ["markdown", "html"],
    "output_dir": "reports"
  },
  "notification": {
    "enabled": false,
    "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
  }
}
```

### 配置说明

- **zread/github**: 数据源配置
  - `enabled`: 是否启用该数据源
  - `time`: 定时任务执行时间（格式: HH:MM）
- **report**: 报告配置
  - `formats`: 报告格式列表，可选：`markdown`, `html`
  - `output_dir`: 报告输出目录
- **notification**: 通知配置
  - `enabled`: 是否启用通知（默认: false，本地测试模式）
  - `wechat_webhook_url`: 企业微信 Webhook URL

### 使用配置文件

```bash
# 使用配置文件
uv run python trending_daily.py --config config.json --zread

# 配置文件会被自动加载（如果存在 config.json）
uv run python trending_daily.py --zread
```

### 命令行参数覆盖配置

```bash
# 启用通知（覆盖配置文件）
uv run python trending_daily.py --zread --notify

# 禁用通知（覆盖配置文件）
uv run python trending_daily.py --zread --no-notify

# 指定报告格式
uv run python trending_daily.py --zread --formats markdown

# 自定义执行时间
uv run python trending_daily.py --schedule --zread-time 08:00
```

### 环境变量配置

```bash
# 数据源开关
export ZREAD_ENABLED=true
export GITHUB_ENABLED=true

# 通知配置
export NOTIFICATION_ENABLED=true
export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 报告格式
export REPORT_FORMATS="markdown,html"
```

## 企业微信推送

项目支持在生成日报后自动推送到企业微信群。

### 配置方法

1. **获取 Webhook URL**：
   - 在企业微信群中添加"群机器人"
   - 获取 Webhook URL，格式：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY`

2. **通过配置文件配置**（推荐）：
   ```json
   {
     "notification": {
       "enabled": true,
       "wechat_webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
     }
   }
   ```

3. **通过环境变量配置**：
   ```bash
   export WECHAT_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
   export NOTIFICATION_ENABLED=true
   ```

4. **在 GitHub Actions 中使用**：
   - 在仓库的 Settings → Secrets and variables → Actions 中添加 Secret
   - 名称：`WECHAT_WEBHOOK_URL`
   - 值：你的 Webhook URL

### 推送内容

推送的消息包含：
- 报告类型（Zread 或 GitHub）
- 生成时间
- 项目总数
- 报告文件预览（前15行）
- 报告文件路径

### 测试推送

```bash
# 测试企业微信推送功能
uv run python -m notifiers.wechat "YOUR_WEBHOOK_URL" "测试消息"
```

### 默认行为

**默认情况下，通知功能是禁用的**（本地测试模式），即使配置了 Webhook URL 也不会发送通知。需要显式启用：

- 在配置文件中设置 `"enabled": true`
- 或使用命令行参数 `--notify`
- 或设置环境变量 `NOTIFICATION_ENABLED=true`

## 项目结构

```
python_craw/
├── trending_daily.py          # 主控制器（推荐使用）
├── zread_trending_daily.py    # Zread 专用脚本
├── config/
│   ├── __init__.py            # 配置模块
│   └── config.py              # 配置管理
├── notifiers/
│   ├── __init__.py            # 通知模块
│   └── wechat.py              # 企业微信通知
├── templates/
│   ├── report.md.j2           # Markdown 模板
│   └── report.html.j2         # HTML 模板
├── reports/                   # 日报输出目录
├── config.json.example        # 配置文件示例
├── config.json                # 配置文件（需自行创建，已加入 .gitignore）
├── docs/
│   ├── 使用说明.md            # 使用说明文档
│   └── 开发文档.md            # 详细开发文档
├── pyproject.toml             # 项目配置
└── README.md                   # 本文件
```

## 注意事项

1. 首次运行需要下载 Chromium 浏览器（约 130MB）
2. 需要稳定的网络连接
3. 如果网站结构变化，可能需要调整解析逻辑
4. **默认情况下通知功能是禁用的**（本地测试模式），需要显式启用
5. 配置文件 `config.json` 包含敏感信息，已加入 `.gitignore`，请勿提交到仓库
6. 企业微信推送功能为可选功能，未配置 Webhook URL 时不会影响日报生成

## 文档

- [使用说明](docs/使用说明.md) - 详细的使用指南和命令行参数说明
- [开发文档](docs/开发文档.md) - 详细的开发流程和实现方案

## 更新日志

### v0.4.0 (2025-12-14)
- ✅ 重构代码结构，通知功能独立到 `notifiers/` 文件夹
- ✅ 新增配置系统，支持配置文件、环境变量和命令行参数
- ✅ 支持可选数据源（Zread/GitHub）
- ✅ 支持可选报告格式（Markdown/HTML）
- ✅ 支持通知开关，默认本地测试时不发送通知
- ✅ 改进命令行参数，支持配置覆盖

### v0.3.0 (2025-12-14)
- ✅ 新增企业微信消息推送功能
- ✅ 支持 Markdown 格式消息推送
- ✅ 支持日报摘要自动推送

### v0.2.0 (2025-12-14)
- ✅ 新增 GitHub Trending 支持
- ✅ 新增定时任务功能
- ✅ 新增主控制器统一管理
- ✅ 支持命令行参数配置
- ✅ 使用 Jinja2 模板系统

### v0.1.0 (2025-12-09)
- ✅ Zread Trending 日报生成
- ✅ 自动中文翻译
- ✅ 项目详情获取

