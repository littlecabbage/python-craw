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
# 生成 Zread Trending 日报
uv run python trending_daily.py --zread

# 生成 GitHub Trending 日报
uv run python trending_daily.py --github

# 同时生成两个日报
uv run python trending_daily.py --zread --github

# 启动定时任务（每天 9:00 生成 Zread，9:30 生成 GitHub）
uv run python trending_daily.py --schedule
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

## 项目结构

```
python_craw/
├── trending_daily.py           # 主控制器（推荐使用）
├── zread_trending_daily.py     # Zread 专用脚本
├── templates/
│   └── report.md.j2            # Jinja2 模板文件
├── reports/                    # 日报输出目录
│   ├── zread_trending_report_*.md
│   └── github_trending_report_*.md
├── docs/
│   ├── 使用说明.md             # 使用说明文档
│   └── 开发文档.md             # 详细开发文档
├── pyproject.toml              # 项目配置
└── README.md                   # 本文件
```

## 注意事项

1. 首次运行需要下载 Chromium 浏览器（约 130MB）
2. 需要稳定的网络连接
3. 如果网站结构变化，可能需要调整解析逻辑

## 文档

- [使用说明](docs/使用说明.md) - 详细的使用指南和命令行参数说明
- [开发文档](docs/开发文档.md) - 详细的开发流程和实现方案

## 更新日志

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

