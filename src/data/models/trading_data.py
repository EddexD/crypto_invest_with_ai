"""
交易数据模型
定义账户、订单、持仓等交易相关的数据结构
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum

class OrderType(Enum):
    """订单类型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """订单状态"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class BalanceModel:
    """账户余额模型"""
    currency: str      # 币种
    total: float       # 总余额
    free: float        # 可用余额
    used: float        # 冻结余额
    
    @property
    def usage_rate(self) -> float:
        """资金使用率"""
        if self.total > 0:
            return self.used / self.total
        return 0.0

@dataclass
class OrderModel:
    """订单模型"""
    id: str                           # 订单ID
    symbol: str                       # 交易对
    type: OrderType                   # 订单类型
    side: OrderSide                   # 买卖方向
    amount: float                     # 数量
    price: Optional[float] = None     # 价格（市价单为None）
    status: OrderStatus = OrderStatus.PENDING  # 订单状态
    filled: float = 0.0               # 已成交数量
    remaining: float = 0.0            # 剩余数量
    cost: float = 0.0                 # 成交金额
    fee: float = 0.0                  # 手续费
    fee_currency: str = ""            # 手续费币种
    timestamp: Optional[int] = None   # 创建时间戳
    
    @property
    def fill_rate(self) -> float:
        """成交率"""
        if self.amount > 0:
            return self.filled / self.amount
        return 0.0
    
    @property
    def avg_price(self) -> float:
        """平均成交价"""
        if self.filled > 0:
            return self.cost / self.filled
        return 0.0
    
    @property
    def datetime_str(self) -> str:
        """可读的创建时间"""
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        return ""

@dataclass
class PositionModel:
    """持仓模型"""
    symbol: str                    # 交易对
    currency: str                  # 持仓币种
    amount: float                  # 持仓数量
    avg_price: float              # 平均成本价
    current_price: float          # 当前价格
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.amount * self.current_price
    
    @property
    def cost_value(self) -> float:
        """成本价值"""
        return self.amount * self.avg_price
    
    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏"""
        return self.market_value - self.cost_value
    
    @property
    def unrealized_pnl_rate(self) -> float:
        """未实现盈亏率"""
        if self.cost_value > 0:
            return self.unrealized_pnl / self.cost_value
        return 0.0

@dataclass
class PortfolioModel:
    """投资组合模型"""
    total_value: float                    # 总价值
    total_cost: float                     # 总成本
    balances: List[BalanceModel]          # 余额列表
    positions: List[PositionModel]        # 持仓列表
    _total_pnl: Optional[float] = None    # 可覆盖的总盈亏
    _total_pnl_rate: Optional[float] = None  # 可覆盖的总盈亏率
    
    @property
    def total_pnl(self) -> float:
        """总盈亏"""
        if self._total_pnl is not None:
            return self._total_pnl
        return sum(pos.unrealized_pnl for pos in self.positions)
    
    @property
    def total_pnl_rate(self) -> float:
        """总盈亏率"""
        if self._total_pnl_rate is not None:
            return self._total_pnl_rate
        if self.total_cost > 0:
            return self.total_pnl / self.total_cost
        return 0.0
    
    @property
    def asset_allocation(self) -> Dict[str, float]:
        """资产配置比例"""
        allocation = {}
        for pos in self.positions:
            if self.total_value > 0:
                allocation[pos.currency] = pos.market_value / self.total_value
        return allocation

@dataclass
class TradeModel:
    """交易记录模型"""
    id: str                      # 交易ID
    order_id: str               # 订单ID
    symbol: str                 # 交易对
    side: OrderSide             # 买卖方向
    amount: float               # 成交数量
    price: float                # 成交价格
    cost: float                 # 成交金额
    fee: float                  # 手续费
    fee_currency: str           # 手续费币种
    timestamp: int              # 成交时间戳
    
    @property
    def datetime_str(self) -> str:
        """可读的成交时间"""
        return datetime.fromtimestamp(self.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
