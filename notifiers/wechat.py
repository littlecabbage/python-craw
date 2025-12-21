#!/usr/bin/env python3
"""
企业微信消息推送模块
支持通过 Webhook 发送文本和 Markdown 格式的消息
"""

import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path


class WeChatNotifier:
    """企业微信消息推送类"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化企业微信通知器
        
        Args:
            webhook_url: 企业微信 Webhook URL，如果不提供则从环境变量 WECHAT_WEBHOOK_URL 读取
        """
        self.webhook_url = webhook_url or os.getenv('WECHAT_WEBHOOK_URL')
        if not self.webhook_url:
            raise ValueError("未提供 Webhook URL，请通过参数或环境变量 WECHAT_WEBHOOK_URL 设置")
    
    def send_text(self, content: str, mentioned_list: Optional[list] = None) -> bool:
        """
        发送文本消息
        
        Args:
            content: 消息内容
            mentioned_list: @提醒的成员列表，格式：["userid1", "userid2"] 或 ["@all"] 表示@所有人
        
        Returns:
            bool: 发送是否成功
        """
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        if mentioned_list:
            data["text"]["mentioned_list"] = mentioned_list
        
        return self._send(data)
    
    def send_markdown(self, content: str) -> bool:
        """
        发送 Markdown 格式消息
        
        Args:
            content: Markdown 格式的消息内容
        
        Returns:
            bool: 发送是否成功
        """
        data = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
        
        return self._send(data)
    
    def send_report_summary(self, report_type: str, report_path: Path, 
                           total_projects: int, generate_time: str) -> bool:
        """
        发送日报摘要消息
        
        Args:
            report_type: 报告类型（如 "Zread" 或 "GitHub"）
            report_path: 报告文件路径
            total_projects: 项目总数
            generate_time: 生成时间
        
        Returns:
            bool: 发送是否成功
        """
        # 读取报告文件的前几行作为摘要
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:15]  # 读取前15行
                preview = ''.join(lines)
                if len(preview) > 1000:
                    preview = preview[:1000] + "\n\n...（内容过长，已截断）"
        except Exception as e:
            preview = f"无法读取报告内容: {e}"
        
        # 构建 Markdown 消息
        markdown_content = f"""# 📊 {report_type} Trending 日报已生成

**生成时间**: {generate_time}
**项目总数**: {total_projects} 个
**报告文件**: `{report_path.name}`

## 📄 报告预览

```
{preview}
```

---
*报告文件已保存到: {report_path}*
"""
        
        return self.send_markdown(markdown_content)
    
    def send_simple_notification(self, title: str, content: str, 
                                 report_type: Optional[str] = None) -> bool:
        """
        发送简单的通知消息
        
        Args:
            title: 通知标题
            content: 通知内容
            report_type: 报告类型（可选）
        
        Returns:
            bool: 发送是否成功
        """
        if report_type:
            text = f"【{report_type}】{title}\n\n{content}"
        else:
            text = f"{title}\n\n{content}"
        
        return self.send_text(text)
    
    def _send(self, data: Dict[str, Any]) -> bool:
        """
        发送消息到企业微信
        
        Args:
            data: 消息数据（JSON 格式）
        
        Returns:
            bool: 发送是否成功
        """
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('errcode') == 0:
                return True
            else:
                print(f"企业微信推送失败: {result.get('errmsg', '未知错误')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"发送企业微信消息时出错: {e}")
            return False
        except Exception as e:
            print(f"企业微信推送异常: {e}")
            return False


def send_notification(webhook_url: str, message: str, 
                     message_type: str = "text") -> bool:
    """
    便捷函数：发送企业微信通知
    
    Args:
        webhook_url: 企业微信 Webhook URL
        message: 消息内容
        message_type: 消息类型，"text" 或 "markdown"
    
    Returns:
        bool: 发送是否成功
    """
    notifier = WeChatNotifier(webhook_url)
    
    if message_type == "markdown":
        return notifier.send_markdown(message)
    else:
        return notifier.send_text(message)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python wechat.py <webhook_url> [message]")
        sys.exit(1)
    
    webhook = sys.argv[1]
    test_message = sys.argv[2] if len(sys.argv) > 2 else "这是一条测试消息"
    
    notifier = WeChatNotifier(webhook)
    success = notifier.send_text(test_message)
    
    if success:
        print("✓ 消息发送成功")
    else:
        print("✗ 消息发送失败")
        sys.exit(1)



