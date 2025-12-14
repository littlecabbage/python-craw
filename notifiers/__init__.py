"""
通知模块
支持多种通知方式
"""

from .wechat import WeChatNotifier, send_notification

__all__ = ['WeChatNotifier', 'send_notification']

