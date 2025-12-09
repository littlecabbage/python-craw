# Zread Trending 日报生成器

使用 Python 和 Playwright 自动获取 [Zread Trending](https://zread.ai/trending) 网页内容并生成日报。

## 功能特性

- ✅ 使用 Playwright 获取动态网页内容
- ✅ 自动解析项目信息（仓库名、描述、标签、Stars）
- ✅ **自动获取项目详情**：访问每个项目的详情页面，提取简介和亮点
- ✅ **自动中文翻译**：将英文简介和亮点自动翻译成中文
- ✅ 生成 Markdown 格式的日报，包含项目简介和亮点（中文）
- ✅ 支持异步操作，性能优秀
- ✅ 并发控制：使用信号量限制并发数，避免服务器过载

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

## 使用方法

运行脚本：
```bash
uv run python zread_trending_daily.py
```

脚本会自动：
1. 访问 https://zread.ai/trending
2. 解析网页内容
3. 生成日报文件：`zread_trending_report_YYYYMMDD.md`

## 输出示例

生成的日报文件包含：
- 生成时间
- 项目列表，每个项目包含：
  - **简介**：项目的详细描述
  - **亮点**：项目的关键特性列表（最多5个）
  - **标签**：项目相关标签
  - **Stars**：GitHub Stars 数量
  - **链接**：项目详情链接

## 项目结构

```
python_craw/
├── pyproject.toml              # 项目配置
├── zread_trending_daily.py     # 主程序
├── docs/
│   └── 开发文档.md              # 详细开发文档
└── README.md                   # 本文件
```

## 注意事项

1. 首次运行需要下载 Chromium 浏览器（约 130MB）
2. 需要稳定的网络连接
3. 如果网站结构变化，可能需要调整解析逻辑

## 开发文档

详细的开发流程和实现方案请查看 [docs/开发文档.md](docs/开发文档.md)

