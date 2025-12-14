#!/usr/bin/env python3
"""
Trending 日报生成器 - 主控制器
支持 Zread 和 GitHub 两个数据源的日报生成
支持定时任务和手动触发
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import requests
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader
import schedule
import time
import threading

# 导入原有的 zread 功能（延迟导入避免循环依赖）


def parse_github_trending(html_content):
    """解析 GitHub Trending 页面内容"""
    soup = BeautifulSoup(html_content, 'lxml')
    trending_data = []
    
    # GitHub trending 页面的项目通常在 article 标签中
    articles = soup.find_all('article', class_=lambda x: x and 'Box-row' in ' '.join(x) if x else False)
    
    if not articles:
        # 尝试其他选择器
        articles = soup.find_all('article')
    
    for article in articles:
        try:
            # 查找仓库链接
            repo_link = article.find('h2', class_=lambda x: x and 'h3' in ' '.join(x) if x else False)
            if not repo_link:
                repo_link = article.find('h2')
            if not repo_link:
                continue
            
            link_elem = repo_link.find('a', href=True)
            if not link_elem:
                continue
            
            href = link_elem.get('href', '').strip()
            if not href or not href.startswith('/'):
                continue
            
            # 提取仓库名 (格式: /owner/repo)
            repo_name = href.strip('/')
            if '/' not in repo_name or repo_name.count('/') != 1:
                continue
            
            # 提取描述
            description = ""
            desc_elem = article.find('p', class_=lambda x: x and 'col-9' in ' '.join(x) if x else False)
            if not desc_elem:
                desc_elem = article.find('p')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            # 提取语言
            language = ""
            lang_elem = article.find('span', itemprop='programmingLanguage')
            if lang_elem:
                language = lang_elem.get_text(strip=True)
            
            # 提取 Stars
            stars = None
            stars_links = article.find_all('a', href=lambda x: x and '/stargazers' in x if x else False)
            if stars_links:
                stars_text = stars_links[0].get_text(strip=True)
                # 提取数字部分
                stars = stars_text.replace(',', '').replace(' ', '')
            
            # 提取今日 stars
            stars_today = None
            stars_today_elem = article.find('span', class_=lambda x: x and 'd-inline-block' in ' '.join(x) if x else False)
            if stars_today_elem:
                stars_today_text = stars_today_elem.get_text(strip=True)
                if 'stars today' in stars_today_text.lower():
                    stars_today = stars_today_text.split()[0]
            
            trending_data.append({
                'repo': repo_name,
                'description': description,
                'language': language,
                'stars': stars,
                'stars_today': stars_today,
                'url': f"https://github.com{href}"
            })
        except Exception as e:
            continue
    
    return trending_data


async def fetch_github_trending():
    """获取 GitHub Trending 页面内容"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(60000)
        
        print("正在访问 https://github.com/trending...")
        try:
            await page.goto("https://github.com/trending", wait_until="load", timeout=60000)
            await asyncio.sleep(3)  # 等待页面渲染
        except Exception as e:
            print(f"页面加载警告: {e}")
        
        html_content = await page.content()
        await page.close()
        await browser.close()
        
        return html_content


async def generate_github_report():
    """生成 GitHub Trending 日报"""
    try:
        # 获取页面内容
        html_content = await fetch_github_trending()
        
        # 解析内容
        print("正在解析 GitHub Trending 内容...")
        trending_data = parse_github_trending(html_content)
        
        if not trending_data:
            print("警告: 未能解析到项目数据")
            return
        
        # 获取项目详情（简介和亮点）
        projects_to_fetch = trending_data[:20]  # 限制前20个项目
        total_projects = len(projects_to_fetch)
        print(f"\n正在获取 {total_projects} 个项目的详细信息...")
        
        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(3)
        
        # 创建进度条
        pbar = tqdm(total=total_projects, desc="获取项目详情", unit="项目", ncols=100, leave=True)
        
        async def fetch_with_progress(project):
            """获取项目详情并更新进度条"""
            try:
                details = await fetch_project_details(project['repo'], semaphore)
                project['intro'] = details['description']
                project['highlights'] = details['highlights']
                if details.get('language') and not project.get('language'):
                    project['language'] = details['language']
                pbar.set_postfix_str(f"✓ {project['repo']}")
                return True
            except Exception as e:
                pbar.set_postfix_str(f"✗ {project['repo']}: {str(e)[:30]}")
                return False
            finally:
                pbar.update(1)
        
        # 创建所有任务
        tasks = [fetch_with_progress(project) for project in projects_to_fetch]
        
        # 并发执行所有任务
        await asyncio.gather(*tasks)
        
        # 关闭进度条
        pbar.close()
        
        # 生成日报（同时生成 Markdown 和 HTML）
        print("\n正在生成 GitHub Trending 日报...")
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        
        # 设置 Jinja2 环境
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        template_data = {
            'source': 'GitHub',
            'generate_time': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'total_projects': len(trending_data),
            'projects': trending_data
        }
        
        # 生成 Markdown 格式
        md_template = env.get_template("report.md.j2")
        md_content = md_template.render(**template_data)
        md_file = reports_dir / f"github_trending_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"  ✓ Markdown 格式: {md_file}")
        
        # 生成 HTML 格式
        html_template = env.get_template("report.html.j2")
        html_content = html_template.render(**template_data)
        html_file = reports_dir / f"github_trending_report_{datetime.now().strftime('%Y%m%d')}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  ✓ HTML 格式: {html_file}")
        
        print(f"\nGitHub Trending 日报已生成，共包含 {len(trending_data)} 个项目")
        
    except Exception as e:
        print(f"生成 GitHub Trending 日报时出错: {e}")
        import traceback
        traceback.print_exc()


async def generate_zread_report_wrapper():
    """Zread Trending 日报生成包装函数"""
    try:
        # 延迟导入避免循环依赖
        from zread_trending_daily import main as zread_main
        await zread_main()
    except Exception as e:
        print(f"生成 Zread Trending 日报时出错: {e}")
        import traceback
        traceback.print_exc()


def fetch_project_details(repo_name, semaphore):
    """从 GitHub 项目首页获取详细信息（复用 zread 的功能）"""
    # 延迟导入
    from zread_trending_daily import fetch_project_details as _fetch
    return _fetch(repo_name, semaphore)


class TrendingScheduler:
    """Trending 日报定时任务调度器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def run_scheduler(self):
        """运行调度器（在单独线程中）"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def start(self, zread_enabled=True, github_enabled=True, 
              zread_time="09:00", github_time="09:30"):
        """启动定时任务"""
        if self.running:
            print("调度器已在运行中")
            return
        
        # 清除所有现有任务
        schedule.clear()
        
        # 添加 Zread 任务
        if zread_enabled:
            schedule.every().day.at(zread_time).do(
                lambda: asyncio.run(generate_zread_report_wrapper())
            )
            print(f"已设置 Zread Trending 日报定时任务: 每天 {zread_time}")
        
        # 添加 GitHub 任务
        if github_enabled:
            schedule.every().day.at(github_time).do(
                lambda: asyncio.run(generate_github_report())
            )
            print(f"已设置 GitHub Trending 日报定时任务: 每天 {github_time}")
        
        self.running = True
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()
        print("\n定时任务调度器已启动")
        print("按 Ctrl+C 停止")
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        schedule.clear()
        if self.thread:
            self.thread.join(timeout=1)
        print("定时任务调度器已停止")


def main():
    """主函数 - 支持命令行参数"""
    parser = argparse.ArgumentParser(
        description='Trending 日报生成器 - 支持 Zread 和 GitHub',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 手动生成 Zread 日报
  python trending_daily.py --zread
  
  # 手动生成 GitHub 日报
  python trending_daily.py --github
  
  # 同时生成两个日报
  python trending_daily.py --zread --github
  
  # 启动定时任务（每天 9:00 生成 Zread，9:30 生成 GitHub）
  python trending_daily.py --schedule
  
  # 自定义定时任务时间
  python trending_daily.py --schedule --zread-time 08:00 --github-time 08:30
        """
    )
    
    parser.add_argument('--zread', action='store_true', 
                       help='生成 Zread Trending 日报')
    parser.add_argument('--github', action='store_true',
                       help='生成 GitHub Trending 日报')
    parser.add_argument('--schedule', action='store_true',
                       help='启动定时任务模式')
    parser.add_argument('--zread-time', default='09:00',
                       help='Zread 日报生成时间 (默认: 09:00)')
    parser.add_argument('--github-time', default='09:30',
                       help='GitHub 日报生成时间 (默认: 09:30)')
    parser.add_argument('--zread-only', action='store_true',
                       help='定时任务模式：仅启用 Zread')
    parser.add_argument('--github-only', action='store_true',
                       help='定时任务模式：仅启用 GitHub')
    
    args = parser.parse_args()
    
    # 如果没有指定任何参数，显示帮助
    if not any([args.zread, args.github, args.schedule]):
        parser.print_help()
        return
    
    # 手动触发模式
    if args.schedule:
        # 定时任务模式
        zread_enabled = not args.github_only
        github_enabled = not args.zread_only
        
        scheduler = TrendingScheduler()
        scheduler.start(
            zread_enabled=zread_enabled,
            github_enabled=github_enabled,
            zread_time=args.zread_time,
            github_time=args.github_time
        )
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
    else:
        # 手动触发模式
        async def run_tasks():
            tasks = []
            
            if args.zread:
                print("=" * 60)
                print("开始生成 Zread Trending 日报")
                print("=" * 60)
                tasks.append(generate_zread_report_wrapper())
            
            if args.github:
                print("=" * 60)
                print("开始生成 GitHub Trending 日报")
                print("=" * 60)
                tasks.append(generate_github_report())
            
            if tasks:
                await asyncio.gather(*tasks)
            else:
                parser.print_help()
        
        asyncio.run(run_tasks())


if __name__ == "__main__":
    main()

