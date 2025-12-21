"""
通知模块
支持多种通知方式
"""

from .wechat import WeChatNotifier, send_notification as send_wechat_notification
from .email import EmailNotifier, send_notification as send_email_notification

__all__ = [
    'WeChatNotifier',
    'EmailNotifier',
    'send_wechat_notification',
    'send_email_notification'
]

