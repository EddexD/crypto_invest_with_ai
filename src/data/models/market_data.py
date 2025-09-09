"""
市场数据模型
定义市场数据的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class MarketDataModel:
    """市场行情数据模型"""
    symbol: str                    # 交易对符号
    timestamp: int                 # 时间戳
    datetime: str                  # 日期时间字符串
    open: float                    # 开盘价
    high: float                    # 最高价
    low: float                     # 最低价
    close: float                   # 收盘价/当前价
    volume: float                  # 成交量
    bid: Optional[float] = None    # 买一价
    ask: Optional[float] = None    # 卖一价
    change: Optional[float] = None # 24h变化量
    percentage: Optional[float] = None # 24h变化百分比
    
    @property
    def price(self) -> float:
        """当前价格（收盘价）"""
        return self.close
    
    @property
    def spread(self) -> Optional[float]:
        """买卖价差"""
        if self.bid and self.ask:
            return self.ask - self.bid
        return None

@dataclass
class CandleDataModel:
    """K线数据模型"""
    timestamp: int        # 时间戳
    open: float          # 开盘价
    high: float          # 最高价
    low: float           # 最低价
    close: float         # 收盘价
    volume: float        # 成交量
    symbol: str          # 交易对符号
    timeframe: str       # 时间周期
    
    @property
    def datetime_str(self) -> str:
        """获取可读的日期时间字符串"""
        return datetime.fromtimestamp(self.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
    
    @property
    def body_size(self) -> float:
        """实体大小（收盘价-开盘价的绝对值）"""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """上影线长度"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """下影线长度"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """是否为阳线"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """是否为阴线"""
        return self.close < self.open
