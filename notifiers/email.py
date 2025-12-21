#!/usr/bin/env python3
"""
邮件通知模块
支持通过 SMTP 发送邮件通知
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from pathlib import Path


class EmailNotifier:
    """邮件通知类"""
    
    def __init__(
        self,
        recipient: Optional[str] = None,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        初始化邮件通知器
        
        Args:
            recipient: 收件人邮箱地址，如果不提供则从环境变量 EMAIL_RECIPIENT 读取
            smtp_server: SMTP 服务器地址，如果不提供则从环境变量 SMTP_SERVER 读取
            smtp_port: SMTP 端口，如果不提供则从环境变量 SMTP_PORT 读取（默认 587）
            smtp_user: SMTP 用户名，如果不提供则从环境变量 SMTP_USER 读取
            smtp_password: SMTP 密码，如果不提供则从环境变量 SMTP_PASSWORD 读取
            use_tls: 是否使用 TLS（默认 True）
        """
        self.recipient = recipient or os.getenv('EMAIL_RECIPIENT')
        self.smtp_server = smtp_server or os.getenv('SMTP_SERVER')
        self.smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = smtp_user or os.getenv('SMTP_USER')
        self.smtp_password = smtp_password or os.getenv('SMTP_PASSWORD')
        self.use_tls = use_tls
        
        if not self.recipient:
            raise ValueError("未提供收件人邮箱，请通过参数或环境变量 EMAIL_RECIPIENT 设置")
        
        # 如果没有配置 SMTP 服务器，则无法发送邮件
        if not self.smtp_server:
            print("警告: 未配置 SMTP 服务器，邮件通知功能将被禁用")
    
    def send_email(
        self,
        subject: str,
        body: str,
        body_type: str = 'plain',
        attachments: Optional[List[Path]] = None
    ) -> bool:
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            body: 邮件正文
            body_type: 正文类型，'plain' 或 'html'
            attachments: 附件列表（可选）
        
        Returns:
            bool: 发送是否成功
        """
        if not self.smtp_server:
            print("无法发送邮件: 未配置 SMTP 服务器")
            return False
        
        try:
            # 创建邮件消息
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user or 'noreply@github.com'
            msg['To'] = self.recipient
            msg['Subject'] = subject
            
            # 添加正文
            msg.attach(MIMEText(body, body_type, 'utf-8'))
            
            # 添加附件
            if attachments:
                for attachment_path in attachments:
                    if attachment_path.exists():
                        with open(attachment_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {attachment_path.name}'
                            )
                            msg.attach(part)
            
            # 连接 SMTP 服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                
                server.send_message(msg)
            
            return True
            
        except smtplib.SMTPException as e:
            print(f"发送邮件时 SMTP 错误: {e}")
            return False
        except Exception as e:
            print(f"发送邮件时出错: {e}")
            return False
    
    def send_text(self, subject: str, content: str) -> bool:
        """
        发送纯文本邮件
        
        Args:
            subject: 邮件主题
            content: 邮件内容
        
        Returns:
            bool: 发送是否成功
        """
        return self.send_email(subject, content, 'plain')
    
    def send_html(self, subject: str, html_content: str) -> bool:
        """
        发送 HTML 格式邮件
        
        Args:
            subject: 邮件主题
            html_content: HTML 格式的邮件内容
        
        Returns:
            bool: 发送是否成功
        """
        return self.send_email(subject, html_content, 'html')
    
    def send_report_summary(
        self,
        report_type: str,
        report_path: Path,
        total_projects: int,
        generate_time: str,
        send_attachment: bool = True
    ) -> bool:
        """
        发送日报摘要邮件
        
        Args:
            report_type: 报告类型（如 "Zread" 或 "GitHub"）
            report_path: 报告文件路径
            total_projects: 项目总数
            generate_time: 生成时间
            send_attachment: 是否发送报告文件作为附件（默认 True）
        
        Returns:
            bool: 发送是否成功
        """
        # 读取报告文件的前几行作为摘要
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:20]  # 读取前20行
                preview = ''.join(lines)
                if len(preview) > 1500:
                    preview = preview[:1500] + "\n\n...（内容过长，已截断）"
        except Exception as e:
            preview = f"无法读取报告内容: {e}"
        
        # 构建 HTML 邮件内容
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .info {{ background-color: #f4f4f4; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .preview {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #4CAF50; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {report_type} Trending 日报已生成</h1>
    </div>
    <div class="content">
        <div class="info">
            <p><strong>生成时间:</strong> {generate_time}</p>
            <p><strong>项目总数:</strong> {total_projects} 个</p>
            <p><strong>报告文件:</strong> {report_path.name}</p>
        </div>
        
        <h2>📄 报告预览</h2>
        <div class="preview">
            <pre>{preview}</pre>
        </div>
        
        <p><em>完整报告请查看附件（如果已启用）</em></p>
    </div>
</body>
</html>"""
        
        subject = f"📊 {report_type} Trending 日报 - {generate_time}"
        attachments = [report_path] if send_attachment and report_path.exists() else None
        
        return self.send_email(subject, html_content, 'html', attachments)
    
    def send_simple_notification(
        self,
        title: str,
        content: str,
        report_type: Optional[str] = None
    ) -> bool:
        """
        发送简单的通知邮件
        
        Args:
            title: 通知标题
            content: 通知内容
            report_type: 报告类型（可选）
        
        Returns:
            bool: 发送是否成功
        """
        if report_type:
            subject = f"【{report_type}】{title}"
        else:
            subject = title
        
        text = f"{title}\n\n{content}"
        return self.send_text(subject, text)


def send_notification(
    recipient: str,
    subject: str,
    message: str,
    message_type: str = "text"
) -> bool:
    """
    便捷函数：发送邮件通知
    
    Args:
        recipient: 收件人邮箱地址
        subject: 邮件主题
        message: 消息内容
        message_type: 消息类型，"text" 或 "html"
    
    Returns:
        bool: 发送是否成功
    """
    notifier = EmailNotifier(recipient=recipient)
    
    if message_type == "html":
        return notifier.send_html(subject, message)
    else:
        return notifier.send_text(subject, message)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python email.py <recipient> [subject] [message]")
        print("环境变量:")
        print("  EMAIL_RECIPIENT - 收件人邮箱（如果未通过参数提供）")
        print("  SMTP_SERVER - SMTP 服务器地址")
        print("  SMTP_PORT - SMTP 端口（默认 587）")
        print("  SMTP_USER - SMTP 用户名（可选）")
        print("  SMTP_PASSWORD - SMTP 密码（可选）")
        sys.exit(1)
    
    recipient = sys.argv[1]
    subject = sys.argv[2] if len(sys.argv) > 2 else "测试邮件"
    test_message = sys.argv[3] if len(sys.argv) > 3 else "这是一条测试消息"
    
    notifier = EmailNotifier(recipient=recipient)
    success = notifier.send_text(subject, test_message)
    
    if success:
        print("✓ 邮件发送成功")
    else:
        print("✗ 邮件发送失败")
        sys.exit(1)

