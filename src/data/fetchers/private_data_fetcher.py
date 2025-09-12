"""
私有数据获取器（账户相关数据）
负责获取账户余额、订单信息、交易记录等私有数据
"""

import ccxt
from typing import List, Optional, Dict
import logging
from ..models.trading_data import (
    BalanceModel, OrderModel, PositionModel, 
    TradeModel, OrderType, OrderSide, OrderStatus
)

logger = logging.getLogger(__name__)

class PrivateDataFetcher:
    """私有数据获取器"""
    
    def __init__(self, platform: str, api_key: str, secret: str, password: Optional[str] = None):
        """
        初始化私有数据获取器
        
        Args:
            platform: 交易所平台名称
            api_key: API密钥
            secret: API密钥
            password: API密码（某些交易所需要）
        """
        self.platform = platform
        
        if platform not in ccxt.exchanges:
            raise ValueError(f"Exchange {platform} not supported by ccxt library.")
            
        config = {
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
        }
        
        if password:
            config['password'] = password
            
        self.exchange = getattr(ccxt, platform)(config)
        logger.info(f"Initialized PrivateDataFetcher for {platform}")

    def get_balances(self) -> List[BalanceModel]:
        """
        获取账户余额
        
        Returns:
            List[BalanceModel]: 余额列表
        """
        try:
            self.exchange.load_markets()
            balance = self.exchange.fetch_balance()
            
            balances = []
            for currency, info in balance['total'].items():
                if info and info > 0.0001:  # 过滤掉极小余额
                    balances.append(BalanceModel(
                        currency=currency,
                        total=info,
                        free=balance['free'][currency],
                        used=balance['used'][currency]
                    ))
            
            return balances
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            raise

    def place_order(self, symbol: str, order_type: str, side: str, 
                   amount: float, price: Optional[float] = None) -> OrderModel:
        """
        下单
        
        Args:
            symbol: 交易对符号
            order_type: 订单类型 ('market', 'limit')
            side: 买卖方向 ('buy', 'sell')
            amount: 数量
            price: 价格（限价单必需）
            
        Returns:
            OrderModel: 订单信息
        """
        try:
            self.exchange.load_markets()
            
            if order_type == 'market':
                order = self.exchange.create_market_order(symbol, side, amount)
            elif order_type == 'limit':
                if price is None:
                    raise ValueError("Price must be provided for limit orders.")
                order = self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                raise ValueError("Unsupported order type. Use 'market' or 'limit'.")
            
            return self._convert_to_order_model(order)
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def get_open_orders(self, symbol: Optional[str] = None, include_algo: bool = True) -> List[OrderModel]:
        """
        获取未完成订单（包括普通订单和算法订单）
        
        Args:
            symbol: 交易对符号（可选，不指定则获取所有）
            include_algo: 是否包括算法订单（止盈止损等）
            
        Returns:
            List[OrderModel]: 未完成订单列表
        """
        all_orders = []
        
        try:
            self.exchange.load_markets()
            
            # 获取普通订单
            if self.platform == 'okx':
                params = {'instType': 'SPOT'}
                try:
                    if symbol:
                        # 为OKX添加市场类型参数以消除歧义
                        market = self.exchange.market(symbol)
                        normal_orders = self.exchange.fetch_open_orders(symbol, None, None, params)
                    else:
                        normal_orders = self.exchange.fetch_open_orders(None, None, None, params)
                    all_orders.extend(normal_orders)
                except Exception as normal_error:
                    logger.warning(f"获取普通订单失败: {normal_error}")
            else:
                try:
                    if symbol:
                        normal_orders = self.exchange.fetch_open_orders(symbol)
                    else:
                        normal_orders = self.exchange.fetch_open_orders()
                    all_orders.extend(normal_orders)
                except Exception as normal_error:
                    logger.warning(f"获取普通订单失败: {normal_error}")
            
            # 获取算法订单（止盈止损等）
            if include_algo:
                try:
                    if self.platform == 'okx':
                        # 使用trigger参数获取算法订单
                        algo_params = {'instType': 'SPOT', 'trigger': True}
                        try:
                            if symbol:
                                # 确保市场已加载并获取正确的市场信息
                                market = self.exchange.market(symbol)
                                algo_orders = self.exchange.fetch_open_orders(symbol, None, None, algo_params)
                            else:
                                algo_orders = self.exchange.fetch_open_orders(None, None, None, algo_params)
                            all_orders.extend(algo_orders)
                        except Exception as trigger_error:
                            logger.debug(f"获取触发订单失败: {trigger_error}")
                        
                        # 也尝试获取OCO订单
                        try:
                            oco_params = {'instType': 'SPOT', 'ordType': 'oco'}
                            if symbol:
                                market = self.exchange.market(symbol)
                                oco_orders = self.exchange.fetch_open_orders(symbol, None, None, oco_params)
                            else:
                                oco_orders = self.exchange.fetch_open_orders(None, None, None, oco_params)
                            all_orders.extend(oco_orders)
                        except Exception as oco_error:
                            logger.debug(f"获取OCO订单失败: {oco_error}")
                        
                        # 尝试获取条件订单
                        try:
                            conditional_params = {'instType': 'SPOT', 'ordType': 'conditional'}
                            if symbol:
                                market = self.exchange.market(symbol)
                                conditional_orders = self.exchange.fetch_open_orders(symbol, None, None, conditional_params)
                            else:
                                conditional_orders = self.exchange.fetch_open_orders(None, None, None, conditional_params)
                            all_orders.extend(conditional_orders)
                        except Exception as conditional_error:
                            logger.debug(f"获取条件订单失败: {conditional_error}")
                            
                    elif self.platform == 'binance':
                        # Binance的算法订单处理
                        try:
                            # 尝试获取OCO订单
                            algo_params = {'type': 'OCO'}
                            if symbol:
                                algo_orders = self.exchange.fetch_open_orders(symbol, None, None, algo_params)
                            else:
                                algo_orders = self.exchange.fetch_open_orders(None, None, None, algo_params)
                            all_orders.extend(algo_orders)
                        except Exception as binance_error:
                            logger.debug(f"Binance算法订单获取失败: {binance_error}")
                    
                except Exception as algo_error:
                    logger.warning(f"获取算法订单失败: {algo_error}")
            
            return [self._convert_to_order_model(order) for order in all_orders]
            
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            # 不抛出异常，返回空列表
            return []

    def get_order_history(self, symbol: Optional[str] = None, 
                         since: Optional[int] = None, limit: int = 100) -> List[OrderModel]:
        """
        获取历史订单
        
        Args:
            symbol: 交易对符号
            since: 开始时间戳
            limit: 数量限制
            
        Returns:
            List[OrderModel]: 历史订单列表
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX调整参数格式和限制
            if self.platform == 'okx':
                # OKX的limit参数有特定限制
                if limit > 100:
                    limit = 100
                params = {'instType': 'SPOT'}
                
                # OKX不支持fetchOrders，使用fetchClosedOrders代替
                if hasattr(self.exchange, 'fetch_closed_orders'):
                    orders = self.exchange.fetch_closed_orders(symbol, since, limit, params)
                else:
                    # 降级到使用fetch_my_trades获取历史数据
                    logger.warning("Exchange doesn't support fetchClosedOrders, using trades instead")
                    trades = self.exchange.fetch_my_trades(symbol, since, limit, params)
                    orders = self._convert_trades_to_orders(trades)
            else:
                # 其他交易所的处理
                if hasattr(self.exchange, 'fetch_closed_orders'):
                    orders = self.exchange.fetch_closed_orders(symbol, since, limit)
                else:
                    logger.warning("Exchange doesn't support fetchClosedOrders, using trades instead")
                    trades = self.exchange.fetch_my_trades(symbol, since, limit)
                    orders = self._convert_trades_to_orders(trades)
            
            return [self._convert_to_order_model(order) for order in orders]
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            # 不抛出异常，返回空列表
            return []

    def get_trades(self, symbol: Optional[str] = None, 
                  since: Optional[int] = None, limit: int = 100) -> List[TradeModel]:
        """
        获取交易记录
        
        Args:
            symbol: 交易对符号
            since: 开始时间戳
            limit: 数量限制
            
        Returns:
            List[TradeModel]: 交易记录列表
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX调整参数格式和限制
            if self.platform == 'okx':
                # OKX的limit参数有特定限制，最大100
                if limit > 100:
                    limit = 100
                params = {'instType': 'SPOT'}
                # 如果没有指定symbol，获取所有交易记录
                if symbol is None:
                    trades = self.exchange.fetch_my_trades(None, since, limit, params)
                else:
                    trades = self.exchange.fetch_my_trades(symbol, since, limit, params)
            else:
                if symbol is None:
                    trades = self.exchange.fetch_my_trades(None, since, limit)
                else:
                    trades = self.exchange.fetch_my_trades(symbol, since, limit)
            
            # 合并同一订单的多次成交
            merged_trades = self._merge_trades_by_order(trades)
            
            trades=[self._convert_to_trade_model(trade) for trade in merged_trades]
            trades = sorted(trades, key=lambda x: x.timestamp, reverse=True)[:limit]
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            # 不抛出异常，返回空列表
            return []

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            symbol: 交易对符号
            
        Returns:
            bool: 是否成功取消
        """
        try:
            self.exchange.load_markets()
            result = self.exchange.cancel_order(order_id, symbol)
            return result['status'] == 'canceled'
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False

    def get_positions(self) -> List[PositionModel]:
        """
        根据余额和当前价格计算持仓信息
        
        Returns:
            List[PositionModel]: 持仓列表（过滤掉市值低于1美元的币种）
        """
        positions = []
        balances = self.get_balances()
        
        # 获取所有交易记录来计算平均成本
        trades = self.get_trades()
        
        # 按时间排序交易记录（从早到晚）
        trades.sort(key=lambda x: x.timestamp)
        
        # 按币种分组计算加权平均成本
        trade_cost_map = {}
        for trade in trades:
            currency = trade.symbol.split('/')[0]  # 提取基础币种，如 BTC/USDT -> BTC
            if currency not in trade_cost_map:
                trade_cost_map[currency] = {'total_cost': 0.0, 'total_amount': 0.0}
            
            current_data = trade_cost_map[currency]
            
            if trade.side.value == 'buy':
                # 买入：使用加权平均计算新的成本价
                new_total_amount = current_data['total_amount'] + trade.amount
                if new_total_amount > 0:
                    # 加权平均成本 = (原持仓成本 + 新买入成本) / 新总持仓
                    new_total_cost = current_data['total_cost'] + trade.cost
                    current_data['total_cost'] = new_total_cost
                    current_data['total_amount'] = new_total_amount
            else:  # sell
                # 卖出：按当前平均成本减少持仓，保持剩余持仓的平均成本不变
                if current_data['total_amount'] >= trade.amount:
                    # 计算当前平均成本价（每个币的成本）
                    if current_data['total_amount'] > 0:
                        avg_cost_per_unit = current_data['total_cost'] / current_data['total_amount']
                    else:
                        avg_cost_per_unit = 0
                    
                    # 减少持仓数量和对应的总成本
                    current_data['total_amount'] -= trade.amount
                    current_data['total_cost'] -= trade.amount * avg_cost_per_unit
                    
                    # 确保数值不为负数
                    current_data['total_amount'] = max(0, current_data['total_amount'])
                    current_data['total_cost'] = max(0, current_data['total_cost'])
                else:
                    # 卖出数量超过持仓，清零（可能是之前的转入币种）
                    logger.warning(f"卖出数量({trade.amount})超过持仓({current_data['total_amount']})，币种: {currency}")
                    current_data['total_amount'] = 0
                    current_data['total_cost'] = 0
        
        for balance in balances:
            if balance.currency != 'USDT' and balance.total > 0:
                try:
                    # 获取当前价格
                    symbol = f"{balance.currency}/USDT"
                    
                    # 为OKX添加市场类型参数
                    if self.platform == 'okx':
                        ticker = self.exchange.fetch_ticker(symbol, {'instType': 'SPOT'})
                    else:
                        ticker = self.exchange.fetch_ticker(symbol)
                        
                    current_price = ticker['last']
                    market_value = balance.total * current_price
                    
                    # 过滤掉市值低于1美元的币种
                    if market_value < 1.0:
                        logger.debug(f"过滤掉市值过低的币种: {balance.currency} (${market_value:.2f})")
                        continue
                    
                    # 计算真实平均成本价
                    if (balance.currency in trade_cost_map and 
                        trade_cost_map[balance.currency]['total_amount'] > 0):
                        
                        trade_amount = trade_cost_map[balance.currency]['total_amount']
                        trade_cost = trade_cost_map[balance.currency]['total_cost']
                        
                        # 如果交易记录的持仓数量与实际余额接近，使用交易记录计算的平均价格
                        if abs(trade_amount - balance.total) / balance.total < 0.1:  # 10%的误差范围
                            avg_price = trade_cost / trade_amount
                            logger.debug(f"{balance.currency}: 使用交易记录计算平均价格 ${avg_price:.4f}")
                        else:
                            # 交易记录与实际余额差异较大，可能有转入转出
                            # 按比例调整成本价
                            calculated_avg_price = trade_cost / trade_amount
                            
                            if balance.total > trade_amount:
                                # 实际余额大于交易记录，可能有转入
                                # 假设转入的币种按当前价格计算
                                extra_amount = balance.total - trade_amount
                                total_cost = trade_cost + (extra_amount * current_price)
                                avg_price = total_cost / balance.total
                                logger.debug(f"{balance.currency}: 检测到可能的转入，调整平均价格 ${avg_price:.4f}")
                            else:
                                # 实际余额小于交易记录，可能有转出
                                # 使用交易记录的平均价格
                                avg_price = calculated_avg_price
                                logger.debug(f"{balance.currency}: 检测到可能的转出，使用交易平均价格 ${avg_price:.4f}")
                    else:
                        # 如果没有交易记录，使用当前价格（可能是转入的币）
                        avg_price = current_price
                        logger.debug(f"{balance.currency}: 无交易记录，使用当前价格 ${avg_price:.4f}")
                    
                    position = PositionModel(
                        symbol=symbol,
                        currency=balance.currency,
                        amount=balance.total,
                        avg_price=avg_price,
                        current_price=current_price
                    )
                    positions.append(position)
                except Exception as e:
                    logger.warning(f"Could not get position for {balance.currency}: {e}")
                    continue
        
        return positions
    
    def _calculate_average_cost(self, symbol: str, trades: List[TradeModel]) -> float:
        """
        计算指定交易对的平均成本价
        
        Args:
            symbol: 交易对符号
            trades: 交易记录列表
            
        Returns:
            float: 平均成本价
        """
        try:
            total_amount = 0.0
            total_cost = 0.0
            
            for trade in trades:
                if trade.symbol == symbol:
                    if trade.side.value == 'buy':
                        # 买入交易，增加持仓
                        total_amount += trade.amount
                        total_cost += trade.cost + trade.fee  # 包含手续费
                    elif trade.side.value == 'sell':
                        # 卖出交易，减少持仓（FIFO）
                        if total_amount > 0:
                            sell_ratio = min(trade.amount / total_amount, 1.0)
                            total_amount -= trade.amount
                            total_cost -= total_cost * sell_ratio  # 按比例减少成本
                            
                            if total_amount <= 0:
                                total_amount = 0
                                total_cost = 0
            
            if total_amount > 0:
                return total_cost / total_amount
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"计算{symbol}平均成本失败: {e}")
            return 0.0

    def _convert_to_order_model(self, order: Dict) -> OrderModel:
        """将交易所返回的订单数据转换为OrderModel"""
        order_type = OrderType.MARKET if order['type'] == 'market' else OrderType.LIMIT
        side = OrderSide.BUY if order['side'] == 'buy' else OrderSide.SELL
        
        status_mapping = {
            'open': OrderStatus.OPEN,
            'closed': OrderStatus.CLOSED,
            'canceled': OrderStatus.CANCELED,
            'pending': OrderStatus.PENDING,
            'expired': OrderStatus.EXPIRED
        }
        status = status_mapping.get(order['status'], OrderStatus.PENDING)
        
        # 处理价格字段 - 对于算法订单，可能需要从其他字段获取价格
        price = order.get('price')
        
        # 如果price为空或None，尝试从算法订单相关字段获取价格
        if not price:
            # 尝试止盈价格
            if order.get('takeProfitPrice'):
                price = order['takeProfitPrice']
            # 尝试止损价格
            elif order.get('stopLossPrice'):
                price = order['stopLossPrice']
            # 尝试触发价格（OKX算法订单）
            elif order.get('triggerPrice'):
                price = order['triggerPrice']
            # 尝试限价价格（OKX算法订单）
            elif order.get('orderPrice'):
                price = order['orderPrice']
            # 尝试其他可能的价格字段
            elif order.get('stopPrice'):
                price = order['stopPrice']
            elif order.get('limitPrice'):
                price = order['limitPrice']
        
        # 如果仍然没有价格，设为0
        if not price:
            price = 0.0
        
        return OrderModel(
            id=order['id'],
            symbol=order['symbol'],
            type=order_type,
            side=side,
            amount=order['amount'],
            price=float(price) if price else 0.0,
            status=status,
            filled=order['filled'],
            remaining=order['remaining'],
            cost=order['cost'] or 0.0,
            fee=order['fee']['cost'] if order['fee'] else 0.0,
            fee_currency=order['fee']['currency'] if order['fee'] else '',
            timestamp=order['timestamp']
        )

    def _convert_to_trade_model(self, trade: Dict) -> TradeModel:
        """将交易所返回的交易数据转换为TradeModel"""
        side = OrderSide.BUY if trade['side'] == 'buy' else OrderSide.SELL
        
        return TradeModel(
            id=trade['id'],
            order_id=trade['order'],
            symbol=trade['symbol'],
            side=side,
            amount=trade['amount'],
            price=trade['price'],
            cost=trade['cost'],
            fee=trade['fee']['cost'] if trade['fee'] else 0.0,
            fee_currency=trade['fee']['currency'] if trade['fee'] else '',
            timestamp=trade['timestamp']
        )

    def _merge_trades_by_order(self, trades: List[Dict]) -> List[Dict]:
        """合并同一订单的多次成交记录"""
        merged = {}
        
        for trade in trades:
            order_id = trade['order']
            if order_id not in merged:
                merged[order_id] = trade.copy()
            else:
                # 合并数量和成本
                merged[order_id]['amount'] += trade['amount']
                merged[order_id]['cost'] += trade['cost']
                if trade['fee']:
                    if merged[order_id]['fee']:
                        merged[order_id]['fee']['cost'] += trade['fee']['cost']
                    else:
                        merged[order_id]['fee'] = trade['fee']
        
        return list(merged.values())
    
    def _convert_trades_to_orders(self, trades: List[Dict]) -> List[Dict]:
        """将交易记录转换为订单记录格式"""
        order_dict = {}
        
        for trade in trades:
            order_id = trade.get('order', trade.get('id', ''))
            if order_id not in order_dict:
                # 创建订单记录
                order_dict[order_id] = {
                    'id': order_id,
                    'symbol': trade['symbol'],
                    'type': 'market',  # 从交易记录无法确定原始订单类型
                    'side': trade['side'],
                    'amount': trade['amount'],
                    'price': trade['price'],
                    'filled': trade['amount'],
                    'remaining': 0,
                    'cost': trade['cost'],
                    'fee': trade.get('fee', {}),
                    'status': 'closed',  # 交易已完成
                    'timestamp': trade['timestamp']
                }
            else:
                # 合并同一订单的多次成交
                existing = order_dict[order_id]
                existing['amount'] += trade['amount']
                existing['filled'] += trade['amount']
                existing['cost'] += trade['cost']
                if trade.get('fee') and existing.get('fee'):
                    existing['fee']['cost'] = existing['fee'].get('cost', 0) + trade['fee'].get('cost', 0)
        
        return list(order_dict.values())

if __name__ == "__main__":
    # 测试代码需要真实的API密钥
    pass
