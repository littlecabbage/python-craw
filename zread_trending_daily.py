#!/usr/bin/env python3
"""
Zread Trending 日报生成器
使用 Playwright 获取 https://zread.ai/trending 的内容并生成日报
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator


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


async def fetch_project_details(url, browser, semaphore):
    """获取单个项目的详细信息（简介和亮点）"""
    async with semaphore:  # 限制并发数
        try:
            page = await browser.new_page()
            page.set_default_timeout(30000)
            
            await page.goto(url, wait_until="load", timeout=30000)
            await asyncio.sleep(2)  # 等待页面渲染
            
            content = await page.content()
            await page.close()
            
            soup = BeautifulSoup(content, 'lxml')
            
            # 提取简介（通常在描述区域）
            description = ""
            highlights = []
            
            # 查找描述文本（通常在 main content 区域）
            # 尝试多种选择器来找到描述
            desc_selectors = [
                'main p',
                'article p',
                '[class*="description"]',
                '[class*="intro"]',
                '[class*="about"]',
            ]
            
            for selector in desc_selectors:
                desc_elements = soup.select(selector)
                if desc_elements:
                    # 取第一个较长的段落作为简介
                    for elem in desc_elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 50:  # 选择较长的文本作为简介
                            description = text[:500]  # 限制长度
                            break
                    if description:
                        break
            
            # 提取亮点（通常在列表或特殊标记的区域）
            highlight_selectors = [
                'ul li',
                'ol li',
                '[class*="feature"]',
                '[class*="highlight"]',
                '[class*="benefit"]',
            ]
            
            for selector in highlight_selectors:
                highlight_elements = soup.select(selector)
                if highlight_elements:
                    for elem in highlight_elements[:5]:  # 最多取5个亮点
                        text = elem.get_text(strip=True)
                        if len(text) > 20 and len(text) < 200:  # 合理的长度
                            highlights.append(text)
                    if highlights:
                        break
            
            # 如果没有找到亮点，尝试从标题或强调文本中提取
            if not highlights:
                strong_elements = soup.find_all(['strong', 'b', 'h2', 'h3'])
                for elem in strong_elements[:5]:
                    text = elem.get_text(strip=True)
                    if len(text) > 10 and len(text) < 150:
                        highlights.append(text)
            
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
                'highlights': translated_highlights
            }
        except Exception as e:
            print(f"  获取 {url} 详情失败: {e}")
            return {
                'description': '',
                'highlights': []
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


def generate_daily_report(trending_data, output_file=None):
    """生成日报"""
    if output_file is None:
        output_file = Path(f"zread_trending_report_{datetime.now().strftime('%Y%m%d')}.md")
    
    report_lines = [
        "# Zread Trending 日报",
        f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
        "",
        f"## 本周热门项目 (共 {len(trending_data)} 个)",
        ""
    ]
    
    for idx, project in enumerate(trending_data, 1):
        report_lines.append(f"### {idx}. {project['repo']}")
        
        # 简介
        if project.get('intro'):
            report_lines.append(f"**简介**: {project['intro']}")
        elif project.get('description'):
            report_lines.append(f"**简介**: {project['description']}")
        
        # 亮点
        if project.get('highlights'):
            report_lines.append("**亮点**:")
            for highlight in project['highlights']:
                report_lines.append(f"- {highlight}")
        
        # 标签
        if project.get('tags'):
            tags_str = ', '.join(project['tags'][:10])  # 限制标签数量
            report_lines.append(f"**标签**: {tags_str}")
        
        # Stars
        if project.get('stars'):
            report_lines.append(f"**Stars**: {project['stars']}")
        
        # 链接
        report_lines.append(f"**链接**: {project['url']}")
        report_lines.append("")
    
    report_content = '\n'.join(report_lines)
    
    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n日报已生成: {output_file}")
    print(f"共包含 {len(trending_data)} 个项目")
    
    return report_content


async def main():
    """主函数"""
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
            print(f"\n正在获取 {min(len(trending_data), 20)} 个项目的详细信息...")
            print("这可能需要一些时间，请耐心等待...")
            
            # 使用信号量限制并发数，避免过载
            semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
            
            # 创建任务列表
            tasks = []
            for project in trending_data[:20]:  # 限制前20个项目，避免耗时过长
                task = fetch_project_details(project['url'], browser, semaphore)
                tasks.append((project, task))
            
            # 并发获取详情
            for project, task in tasks:
                try:
                    details = await task
                    project['intro'] = details['description']
                    project['highlights'] = details['highlights']
                    print(f"  ✓ {project['repo']}")
                except Exception as e:
                    print(f"  ✗ {project['repo']}: {e}")
            
            # 关闭浏览器
            await browser.close()
        
        # 生成日报（在浏览器关闭后）
        print("\n正在生成日报...")
        report_content = generate_daily_report(trending_data)
        
        # 打印摘要
        print("\n" + "="*50)
        print("日报摘要:")
        print("="*50)
        print(report_content[:500] + "..." if len(report_content) > 500 else report_content)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

