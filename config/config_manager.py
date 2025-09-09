"""
配置管理模块
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ExchangeConfig:
    """交易所配置"""
    name: str
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None
    sandbox: bool = False


@dataclass
class AIConfig:
    """智能分析配置"""
    openai_key: str = ""
    model_name: str = "deepseek-chat"
    analysis_interval: int = 3600   # 分析间隔（秒）
    confidence_threshold: float = 0.7  # 置信度阈值
    base_url: str = "https://api.deepseek.com"

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        self.secrets_file = os.path.join(config_dir, "secrets.json")
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        self._load_config()

    def _load_config(self):
        """加载配置"""
        # 加载主配置
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = self._get_default_config()
            self._save_config(config_data)
        
        # 加载敏感信息
        if os.path.exists(self.secrets_file):
            with open(self.secrets_file, 'r') as f:
                secrets_data = json.load(f)
        else:
            secrets_data = self._get_default_secrets()
            self._save_secrets(secrets_data)
        
        # 合并配置
        self.config = config_data
        self.config['ai'].update(secrets_data.get('ai', {}))
        self.config['exchange'] = secrets_data.get('exchange', {})

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "ai": {
                "model_name": "deepseek-chat",
                "analysis_interval": 3600,
                "confidence_threshold": 0.7,
                "base_url": "https://api.deepseek.com"
            },
            "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"],
            "data": {
                "history_days": 30,
                "update_interval": 300
            },
            "ip_whitelist": ["127.0.0.1"]
        }

    def _get_default_secrets(self) -> Dict[str, Any]:
        """获取默认敏感配置"""
        return {
            "exchange": {
                "name": "okx",
                "api_key": "",
                "secret_key": "",
                "passphrase": "",
                "sandbox": True
            },
            "ai": {
                "openai_key": ""
            }
        }

    def _save_config(self, config_data: Dict[str, Any]):
        """保存主配置"""
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    def _save_secrets(self, secrets_data: Dict[str, Any]):
        """保存敏感配置"""
        with open(self.secrets_file, 'w') as f:
            json.dump(secrets_data, f, indent=2)

    def get_exchange_config(self) -> ExchangeConfig:
        """获取交易所配置"""
        exchange_data = self.config.get("exchange", {})
        return ExchangeConfig(
            name=exchange_data.get("name", "okx"),
            api_key=exchange_data.get("api_key", ""),
            secret_key=exchange_data.get("secret_key", ""),
            passphrase=exchange_data.get("passphrase", ""),
            sandbox=exchange_data.get("sandbox", True)
        )



    def get_ai_config(self) -> AIConfig:
        """获取智能分析配置"""
        ai_data = self.config.get("ai", {})
        return AIConfig(
            openai_key=ai_data.get("openai_key", ""),
            model_name=ai_data.get("model_name", "deepseek-chat"),
            analysis_interval=ai_data.get("analysis_interval", 3600),
            confidence_threshold=ai_data.get("confidence_threshold", 0.7),
            base_url=ai_data.get("base_url", "https://api.deepseek.com")
        )

    def get_symbols(self) -> list:
        """获取监控的交易对列表"""
        return self.config.get("symbols", ["BTC/USDT", "ETH/USDT"])

    def update_exchange_config(self, api_key: str, secret_key: str, passphrase: str = ""):
        """更新交易所配置"""
        if "exchange" not in self.config:
            self.config["exchange"] = {}
        
        self.config["exchange"]["api_key"] = api_key
        self.config["exchange"]["secret_key"] = secret_key
        self.config["exchange"]["passphrase"] = passphrase
        
        # 保存到secrets文件
        secrets_data = {
            "exchange": self.config["exchange"],
            "ai": self.config.get("ai", {})
        }
        self._save_secrets(secrets_data)

    def is_configured(self) -> bool:
        """检查是否已配置"""
        exchange_config = self.get_exchange_config()
        return bool(exchange_config.api_key and exchange_config.secret_key)

    def get_ip_whitelist(self) -> list:
        """获取IP白名单"""
        return self.config.get("ip_whitelist", ["127.0.0.1"])

# 全局配置管理器实例
config_manager = ConfigManager()
