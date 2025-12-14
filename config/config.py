#!/usr/bin/env python3
"""
配置管理模块
支持从配置文件、环境变量和命令行参数加载配置
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = False  # 是否启用通知
    wechat_webhook_url: Optional[str] = None  # 企业微信 Webhook URL


@dataclass
class ReportConfig:
    """报告配置"""
    formats: List[str] = field(default_factory=lambda: ['markdown', 'html'])  # 报告格式
    output_dir: str = 'reports'  # 输出目录


@dataclass
class TaskConfig:
    """任务配置"""
    enabled: bool = True  # 是否启用
    time: str = '09:00'  # 执行时间（定时任务）


@dataclass
class Config:
    """主配置类"""
    # 数据源配置
    zread: TaskConfig = field(default_factory=TaskConfig)
    github: TaskConfig = field(default_factory=TaskConfig)
    
    # 报告配置
    report: ReportConfig = field(default_factory=ReportConfig)
    
    # 通知配置
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'zread': asdict(self.zread),
            'github': asdict(self.github),
            'report': asdict(self.report),
            'notification': asdict(self.notification)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """从字典创建配置"""
        config = cls()
        
        if 'zread' in data:
            config.zread = TaskConfig(**data['zread'])
        if 'github' in data:
            config.github = TaskConfig(**data['github'])
        if 'report' in data:
            config.report = ReportConfig(**data['report'])
        if 'notification' in data:
            config.notification = NotificationConfig(**data['notification'])
        
        return config


def get_default_config() -> Config:
    """
    获取默认配置
    默认配置：本地测试模式，不发送通知
    """
    return Config(
        zread=TaskConfig(enabled=True, time='09:00'),
        github=TaskConfig(enabled=True, time='09:30'),
        report=ReportConfig(
            formats=['markdown', 'html'],
            output_dir='reports'
        ),
        notification=NotificationConfig(
            enabled=False,  # 默认不发送通知（本地测试模式）
            wechat_webhook_url=None
        )
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置
    优先级：命令行参数 > 环境变量 > 配置文件 > 默认配置
    
    Args:
        config_path: 配置文件路径（可选）
    
    Returns:
        Config: 配置对象
    """
    # 从默认配置开始
    config = get_default_config()
    
    # 尝试从配置文件加载
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config = Config.from_dict(file_config)
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}，使用默认配置")
    else:
        # 尝试加载默认配置文件
        default_config_path = Path('config.json')
        if default_config_path.exists():
            try:
                with open(default_config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    config = Config.from_dict(file_config)
            except Exception as e:
                print(f"警告: 加载默认配置文件失败: {e}，使用默认配置")
    
    # 从环境变量覆盖配置
    # 数据源开关
    if os.getenv('ZREAD_ENABLED'):
        config.zread.enabled = os.getenv('ZREAD_ENABLED').lower() in ('true', '1', 'yes')
    if os.getenv('GITHUB_ENABLED'):
        config.github.enabled = os.getenv('GITHUB_ENABLED').lower() in ('true', '1', 'yes')
    
    # 通知配置
    if os.getenv('NOTIFICATION_ENABLED'):
        config.notification.enabled = os.getenv('NOTIFICATION_ENABLED').lower() in ('true', '1', 'yes')
    if os.getenv('WECHAT_WEBHOOK_URL'):
        config.notification.wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL')
        # 如果提供了 Webhook URL，默认启用通知（除非明确禁用）
        if config.notification.wechat_webhook_url and os.getenv('NOTIFICATION_ENABLED') is None:
            config.notification.enabled = True
    
    # 报告格式
    if os.getenv('REPORT_FORMATS'):
        formats = [f.strip() for f in os.getenv('REPORT_FORMATS').split(',')]
        config.report.formats = formats
    
    return config


def save_config(config: Config, config_path: str = 'config.json'):
    """
    保存配置到文件
    
    Args:
        config: 配置对象
        config_path: 配置文件路径
    """
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # 测试代码
    config = get_default_config()
    print("默认配置:")
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
    
    print("\n保存配置到 config.json...")
    save_config(config)
    print("✓ 配置已保存")
    
    print("\n从文件加载配置...")
    loaded_config = load_config('config.json')
    print("✓ 配置已加载")

