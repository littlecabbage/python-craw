#!/usr/bin/env python3
"""
Zread Trending 日报生成器
使用 Playwright 获取 https://zread.ai/trending 的内容并生成日报
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import requests
from tqdm import tqdm
from jinja2 import Environment, FileSystemLoader
from typing import Optional

# 导入配置和通知模块
try:
    from config import Config, load_config
    from notifiers import EmailNotifier
except ImportError:
    # 兼容旧版本
    Config = None
    load_config = None
    EmailNotifier = None


async def fetch_trending_content(browser=None):
    """使用 Playwright 获取网页内容"""
    if browser is None:
        # 如果没有传入 browser，创建新的
        p = async_playwright()
        playwright = await p.start()
        browser = await playwright.chromium.launch(headless=True)
        return browser, playwright
    
    return browser, None


def translate_to_chinese(text):
    """将英文文本翻译成中文"""
    if not text or len(text.strip()) == 0:
        return text
    
    try:
        # 检测文本是否主要是中文，如果是则直接返回
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len([c for c in text if c.isalnum() or '\u4e00' <= c <= '\u9fff'])
        if total_chars > 0 and chinese_chars / total_chars > 0.3:  # 如果中文字符超过30%，认为已经是中文
            return text
        
        # 使用Google翻译
        translator = GoogleTranslator(source='auto', target='zh-CN')
        # 限制文本长度，避免过长文本导致翻译失败
        text_to_translate = text[:2000] if len(text) > 2000 else text
        translated = translator.translate(text_to_translate)
        
        # 添加延迟，避免触发速率限制
        import time
        time.sleep(0.1)
        
        return translated
    except Exception as e:
        print(f"    翻译失败: {e}")
        return text  # 翻译失败时返回原文


async def fetch_project_details(repo_name, semaphore):
    """从 GitHub 项目首页获取详细信息（简介、亮点和主要语言）
    使用 requests 直接获取，更轻量快速，无需启动浏览器
    """
    async with semaphore:  # 限制并发数
        try:
            # 构建 GitHub URL
            github_url = f"https://github.com/{repo_name}"
            
            # 使用 requests 直接获取页面内容（更轻量，无需浏览器）
            # 使用 asyncio.to_thread 将同步请求转为异步，避免阻塞事件循环
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            def fetch_html():
                response = requests.get(github_url, headers=headers, timeout=10)
                response.raise_for_status()
                return response.text
            
            html_content = await asyncio.to_thread(fetch_html)
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 提取项目描述（在仓库标题下方）
            description = ""
            desc_selectors = [
                'p[data-pjax="#repo-content-pjax-container"]',
                'div[itemprop="about"]',
                'p.f4.my-3',
                'div.Box-body p',
                'span[itemprop="about"]',
            ]
            
            for selector in desc_selectors:
                desc_elements = soup.select(selector)
                if desc_elements:
                    for elem in desc_elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 20:  # 选择有意义的描述
                            description = text[:500]  # 限制长度
                            break
                    if description:
                        break
            
            # 提取主要编程语言
            language = ""
            # GitHub 的语言信息通常在语言统计栏中，格式为 <li> 包含语言名和百分比
            # 查找语言统计区域
            lang_stats_container = soup.find('ul', class_=lambda x: x and 'list-style-none' in ' '.join(x) if x else False)
            if not lang_stats_container:
                # 尝试其他可能的容器
                lang_stats_container = soup.find('div', class_=lambda x: x and 'language' in ' '.join(x).lower() if x else False)
            
            if lang_stats_container:
                # 查找第一个语言项（通常是主要语言）
                lang_items = lang_stats_container.find_all('li', limit=1)
                if lang_items:
                    # 提取语言名称（通常在 span 中，且不包含百分比）
                    lang_spans = lang_items[0].find_all('span')
                    for span in lang_spans:
                        text = span.get_text(strip=True)
                        # 排除百分比（包含 %）和空文本
                        if text and '%' not in text and len(text) < 30:
                            language = text
                            break
            
            # 如果还没找到，尝试使用 itemprop 属性
            if not language:
                lang_elem = soup.find('span', itemprop='programmingLanguage')
                if lang_elem:
                    language = lang_elem.get_text(strip=True)
            
            # 如果还没找到，尝试从链接中提取
            if not language:
                lang_links = soup.find_all('a', href=lambda x: x and '/search' in x and 'l=' in x if x else False)
                if lang_links:
                    # 从第一个语言链接中提取语言名
                    for link in lang_links[:1]:
                        text = link.get_text(strip=True)
                        if text and len(text) < 30:
                            language = text
                            break
            
            # 提取亮点：从 README 中提取关键信息
            highlights = []
            readme_selectors = [
                'div#readme',
                'article.markdown-body',
                'div[data-target="readme-toc.content"]',
            ]
            
            for selector in readme_selectors:
                readme_elem = soup.select_one(selector)
                if readme_elem:
                    # 从 README 中提取列表项、粗体文本或标题作为亮点
                    # 查找列表项（通常是特性列表）
                    list_items = readme_elem.find_all(['li', 'strong', 'b'])
                    for item in list_items[:10]:  # 最多检查前10个
                        text = item.get_text(strip=True)
                        # 过滤掉太短或太长的文本
                        if 15 < len(text) < 200:
                            # 检查是否是列表项的开头（通常包含特性描述）
                            if item.name == 'li' or (item.name in ['strong', 'b'] and len(text) > 20):
                                if text not in highlights:
                                    highlights.append(text)
                                    if len(highlights) >= 5:  # 最多5个亮点
                                        break
                    if highlights:
                        break
                    
                    # 如果没有找到列表项，尝试从标题中提取
                    if not highlights:
                        headings = readme_elem.find_all(['h2', 'h3'])
                        for heading in headings[:5]:
                            text = heading.get_text(strip=True)
                            if 10 < len(text) < 100:
                                highlights.append(text)
                                if len(highlights) >= 5:
                                    break
            
            # 翻译简介和亮点为中文
            translated_description = ''
            if description:
                translated_description = translate_to_chinese(description)
            
            translated_highlights = []
            if highlights:
                for h in highlights[:5]:
                    translated_h = translate_to_chinese(h)
                    translated_highlights.append(translated_h)
            
            return {
                'description': translated_description,
                'highlights': translated_highlights,
                'language': language
            }
        except Exception as e:
            print(f"  获取 {repo_name} 详情失败: {e}")
            return {
                'description': '',
                'highlights': [],
                'language': ''
            }


def parse_trending_data(html_content):
    """解析网页内容，提取趋势项目信息"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    trending_data = []
    seen_projects = set()
    
    # 查找所有项目链接，排除导航链接
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        
        # 过滤掉导航链接和无效链接
        if not href or href == '/' or '/trending' in href or href.startswith('http'):
            continue
        
        # 检查是否是项目链接（格式通常是 /owner/repo）
        href_parts = href.strip('/').split('/')
        if len(href_parts) < 2:
            continue
        
        repo_name = '/'.join(href_parts[:2])
        
        # 跳过已知的项目和导航项
        if repo_name in seen_projects or repo_name in ['private/repo', 'subscription', 'library']:
            continue
        
        # 提取链接内的所有文本，保留换行和空格结构
        link_text = link.get_text(separator='\n', strip=True)
        
        # 按行分割文本
        lines = [line.strip() for line in link_text.split('\n') if line.strip()]
        
        if len(lines) < 1:
            continue
        
        # 第一行通常是仓库名和描述
        first_line = lines[0]
        
        # 提取描述（如果已有中文描述则保留，否则尝试翻译）
        description = ''
        tags = []
        stars = None
        
        # 尝试从第一行提取仓库名和描述
        # 格式可能是: "owner/repo 描述文本" 或 "owner/repo"
        first_line_parts = first_line.split()
        repo_found = False
        desc_start_idx = 0
        
        for i, part in enumerate(first_line_parts):
            if '/' in part and len(part.split('/')) == 2:
                repo_found = True
                desc_start_idx = i + 1
                break
        
        if repo_found and desc_start_idx < len(first_line_parts):
            description_parts = first_line_parts[desc_start_idx:]
            # 过滤掉明显的标签和 stars
            filtered_desc = []
            for part in description_parts:
                # 检查是否是 stars（包含 k 或大数字）
                if 'k' in part.lower() or (part.replace('.', '').replace(',', '').isdigit() and len(part.replace('.', '').replace(',', '')) >= 3):
                    if not stars:
                        stars = part
                    continue
                # 检查是否是标签（单个词，通常较短）
                if len(part) < 25 and not any(c in part for c in ['/', '\\', '.', ':', '(', ')']):
                    # 可能是标签，但先加入描述
                    filtered_desc.append(part)
                else:
                    filtered_desc.append(part)
            
            description = ' '.join(filtered_desc).strip()
        
        # 从后续行提取标签和 stars
        for line in lines[1:]:
            line_parts = line.split()
            for part in line_parts:
                # 检查是否是 stars
                if 'k' in part.lower() or (part.replace('.', '').replace(',', '').isdigit() and len(part.replace('.', '').replace(',', '')) >= 3):
                    if not stars:
                        stars = part
                # 检查是否是标签（短词，不含特殊字符）
                elif len(part) < 25 and not any(c in part for c in ['/', '\\', '.', ':', '(', ')', '，', '。']):
                    # 排除常见的描述性词汇
                    skip_words = ['the', 'a', 'an', 'is', 'are', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by']
                    if part.lower() not in skip_words and part not in tags:
                        tags.append(part)
        
        # 如果描述为空，尝试从 title 或其他属性获取
        if not description:
            title = link.get('title', '')
            if title:
                description = title
        
        # 清理描述：移除明显的标签词汇
        if description:
            desc_words = description.split()
            cleaned_desc = []
            for word in desc_words:
                # 如果单词看起来像标签（短且不含空格），跳过
                if len(word) < 15 and word not in ['and', 'the', 'a', 'an', 'is', 'are', 'of', 'in', 'on', 'at', 'to', 'for', 'with']:
                    # 检查是否包含特殊字符（标签通常不含）
                    if any(c in word for c in ['.', ',', ':', ';', '(', ')', '，', '。']):
                        cleaned_desc.append(word)
                    elif len(word) > 3:  # 保留较长的词作为描述
                        cleaned_desc.append(word)
                else:
                    cleaned_desc.append(word)
            description = ' '.join(cleaned_desc).strip()
        
        # 限制标签数量
        tags = tags[:15]
        
        if repo_name:
            seen_projects.add(repo_name)
            # 如果描述是英文，翻译成中文
            final_description = description[:300] if description else ''
            if final_description:
                # 检测是否主要是中文
                chinese_chars = sum(1 for char in final_description if '\u4e00' <= char <= '\u9fff')
                if chinese_chars < len(final_description) * 0.3:  # 如果中文字符少于30%，尝试翻译
                    final_description = translate_to_chinese(final_description)
            
            trending_data.append({
                'repo': repo_name,
                'description': final_description,
                'tags': tags,
                'stars': stars,
                'url': f"https://zread.ai{href}"
            })
    
    # 去重并排序
    unique_data = []
    seen_repos = set()
    for item in trending_data:
        if item['repo'] not in seen_repos:
            seen_repos.add(item['repo'])
            unique_data.append(item)
    
    return unique_data


def generate_daily_report(trending_data, output_file=None, format='markdown', source='Zread'):
    """使用 Jinja2 模板生成日报
    
    Args:
        trending_data: 项目数据列表
        output_file: 输出文件路径（可选）
        format: 输出格式，'markdown' 或 'html'（默认: 'markdown'）
        source: 数据源名称（默认: 'Zread'）
    """
    # 创建 reports 文件夹（如果不存在）
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # 创建 templates 文件夹（如果不存在）
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)
    
    # 根据格式确定文件扩展名和模板文件名
    if format == 'html':
        ext = '.html'
        template_name = "report.html.j2"
    else:
        ext = '.md'
        template_name = "report.md.j2"
    
    if output_file is None:
        filename = f"{source.lower()}_trending_report_{datetime.now().strftime('%Y%m%d')}{ext}"
        output_file = reports_dir / filename
    else:
        # 如果提供了 output_file，确保它是 Path 对象且在 reports 目录下
        if isinstance(output_file, str):
            output_file = Path(output_file)
        if not output_file.is_absolute():
            output_file = reports_dir / output_file
    
    # 加载 Jinja2 模板
    template_path = templates_dir / template_name
    
    # 如果模板文件不存在，创建一个默认模板
    if not template_path.exists():
        default_template = """# Zread Trending 日报
生成时间: {{ generate_time }}

## 本周热门项目 (共 {{ total_projects }} 个)

{% for project in projects %}
### {{ loop.index }}. {{ project.repo }}

{% if project.intro %}
**简介**: {{ project.intro }}
{% elif project.description %}
**简介**: {{ project.description }}
{% endif %}

{% if project.language %}
**主要语言**: {{ project.language }}
{% endif %}

{% if project.highlights %}
**亮点**:
{% for highlight in project.highlights %}
- {{ highlight }}
{% endfor %}
{% endif %}

{% if project.tags %}
**标签**: {{ project.tags[:10] | join(', ') }}
{% endif %}

{% if project.stars %}
**Stars**: {{ project.stars }}
{% endif %}

**链接**: {{ project.url }}

{% endfor %}
"""
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(default_template)
    
    # 设置 Jinja2 环境
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # 加载模板
    template = env.get_template("report.md.j2")
    
    # 准备模板数据
    template_data = {
        'source': source,
        'generate_time': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
        'total_projects': len(trending_data),
        'projects': trending_data
    }
    
    # 渲染模板
    report_content = template.render(**template_data)
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n日报已生成: {output_file}")
    print(f"共包含 {len(trending_data)} 个项目")
    
    return report_content


async def generate_zread_report(config: Optional[Config] = None):
    """Zread Trending 日报生成函数（可被导入）"""
    if config is None:
        if Config is not None and load_config is not None:
            config = load_config()
        else:
            config = None
    
    try:
        # 初始化浏览器
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 设置超时时间
            page.set_default_timeout(60000)  # 60秒
            
            print("正在访问 https://zread.ai/trending...")
            try:
                # 使用 load 而不是 networkidle，更宽松的等待条件
                await page.goto("https://zread.ai/trending", wait_until="load", timeout=60000)
            except Exception as e:
                print(f"页面加载警告: {e}")
                # 即使超时也尝试获取内容
            
            # 等待页面动态内容加载完成
            await asyncio.sleep(5)
            
            # 尝试等待特定元素出现（如果存在）
            try:
                await page.wait_for_selector('a[href^="/"]', timeout=10000)
            except:
                pass  # 如果找不到元素，继续执行
            
            # 获取页面内容
            html_content = await page.content()
            await page.close()
            
            # 解析内容
            print("正在解析网页内容...")
            trending_data = parse_trending_data(html_content)
            
            if not trending_data:
                print("警告: 未能解析到项目数据，尝试使用备用方法...")
                # 备用方法：直接保存 HTML 供后续分析
                with open('zread_trending_raw.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("原始 HTML 已保存到 zread_trending_raw.html")
                return
            
            # 获取项目详情（简介和亮点）
            projects_to_fetch = trending_data[:20]  # 限制前20个项目，避免耗时过长
            total_projects = len(projects_to_fetch)
            print(f"\n正在获取 {total_projects} 个项目的详细信息...")
            
            # 使用信号量限制并发数，避免过载
            semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
            
            # 创建进度条
            pbar = tqdm(total=total_projects, desc="获取项目详情", unit="项目", ncols=100, leave=True)
            
            # 创建包装函数，用于更新进度条
            async def fetch_with_progress(project):
                """获取项目详情并更新进度条"""
                try:
                    details = await fetch_project_details(project['repo'], semaphore)
                    project['intro'] = details['description']
                    project['highlights'] = details['highlights']
                    if details.get('language'):
                        project['language'] = details['language']
                    pbar.set_postfix_str(f"✓ {project['repo']}")
                    return True
                except Exception as e:
                    pbar.set_postfix_str(f"✗ {project['repo']}: {str(e)[:30]}")
                    return False
                finally:
                    pbar.update(1)
            
            # 创建所有任务
            tasks = [
                fetch_with_progress(project)
                for project in projects_to_fetch
            ]
            
            # 并发执行所有任务
            await asyncio.gather(*tasks)
            
            # 关闭进度条
            pbar.close()
            
            # 关闭浏览器
            await browser.close()
        
        # 生成日报（根据配置生成指定格式）
        print("\n正在生成日报...")
        # 使用传入的配置，如果没有则尝试加载
        if config is None:
            if Config is not None and load_config is not None:
                config = load_config()
            else:
                config = None
        
        if config:
            reports_dir = Path(config.report.output_dir)
            report_formats = config.report.formats
        else:
            reports_dir = Path("reports")
            report_formats = ['markdown', 'html']
        
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
            'source': 'Zread',
            'generate_time': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'total_projects': len(trending_data),
            'projects': trending_data
        }
        
        md_file = None
        report_content = None
        
        # 根据配置生成报告格式
        if 'markdown' in report_formats:
            md_template = env.get_template("report.md.j2")
            md_content = md_template.render(**template_data)
            md_file = reports_dir / f"zread_trending_report_{datetime.now().strftime('%Y%m%d')}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_content)
            print(f"  ✓ Markdown 格式: {md_file}")
            report_content = md_content
        
        if 'html' in report_formats:
            html_template = env.get_template("report.html.j2")
            html_content = html_template.render(**template_data)
            html_file = reports_dir / f"zread_trending_report_{datetime.now().strftime('%Y%m%d')}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  ✓ HTML 格式: {html_file}")
        
        # 打印摘要
        if report_content:
            print("\n" + "="*50)
            print("日报摘要:")
            print("="*50)
            print(report_content[:500] + "..." if len(report_content) > 500 else report_content)
        
        # 发送通知（如果启用）
        if config and config.notification.enabled and config.notification.email_recipient and md_file:
            try:
                notifier = EmailNotifier(recipient=config.notification.email_recipient)
                success = notifier.send_report_summary(
                    report_type="Zread",
                    report_path=md_file,
                    total_projects=len(trending_data),
                    generate_time=template_data['generate_time']
                )
                if success:
                    print(f"\n  ✓ 邮件通知已发送到 {config.notification.email_recipient}")
                else:
                    print("\n  ⚠ 邮件通知发送失败")
            except Exception as e:
                print(f"\n  ⚠ 发送邮件通知时出错: {e}")
        elif config and not config.notification.enabled:
            print("\n  ℹ 通知功能已禁用（本地测试模式）")
        elif not config:
            # 兼容旧版本：从环境变量读取
            email_recipient = os.getenv('EMAIL_RECIPIENT')
            if email_recipient and md_file:
                try:
                    from notifiers import EmailNotifier
                    notifier = EmailNotifier(recipient=email_recipient)
                    success = notifier.send_report_summary(
                        report_type="Zread",
                        report_path=md_file,
                        total_projects=len(trending_data),
                        generate_time=template_data['generate_time']
                    )
                    if success:
                        print(f"\n  ✓ 邮件通知已发送到 {email_recipient}")
                    else:
                        print("\n  ⚠ 邮件通知发送失败")
                except Exception as e:
                    print(f"\n  ⚠ 发送邮件通知时出错: {e}")
            else:
                print("\n  ℹ 未配置企业微信 Webhook URL，跳过推送")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Zread Trending 日报生成主函数（兼容旧版本）"""
    await generate_zread_report()


if __name__ == "__main__":
    asyncio.run(main())

