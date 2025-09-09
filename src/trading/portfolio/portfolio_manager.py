"""
投资组合管理器
负责跟踪和管理投资组合状态
"""

from typing import Dict, List, Optional
from datetime import datetime, date
import logging
from ...data.models.trading_data import BalanceModel, PositionModel, PortfolioModel
from ...data.database.db_manager import db_manager

logger = logging.getLogger(__name__)

class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_portfolio_snapshot(self, 
                                balances: List[BalanceModel],
                                current_prices: Dict[str, float],
                                private_fetcher = None,
                                initial_balance: float = 19393.0) -> PortfolioModel:
        """
        创建投资组合快照
        
        Args:
            balances: 账户余额列表
            current_prices: 当前价格字典 {symbol: price}
            private_fetcher: 私有数据获取器（用于获取交易记录）
            initial_balance: 初始投入资金总额
            
        Returns:
            PortfolioModel: 投资组合模型
        """
        # 设置私有数据获取器以供其他方法使用
        self._private_fetcher = private_fetcher
        
        positions = []
        total_value = 0.0
        total_crypto_cost = 0.0  # 购买加密货币的总成本
        
        # 处理USDT余额
        usdt_balance = 0.0
        for balance in balances:
            if balance.currency == 'USDT':
                usdt_balance = balance.total
                total_value += balance.total
                break
        
        # 处理其他币种持仓
        for balance in balances:
            if balance.currency == 'USDT' or balance.total <= 0:
                continue
            
            symbol = f"{balance.currency}/USDT"
            current_price = current_prices.get(symbol, 0)
            
            if current_price > 0:
                # 计算真实的购买成本
                actual_cost = self._get_actual_purchase_cost(balance.currency)
                
                if actual_cost > 0:
                    avg_price = actual_cost / balance.total
                else:
                    # 如果没有交易记录，使用当前价格作为成本价（保守估算）
                    avg_price = current_price
                    actual_cost = balance.total * current_price
                    logger.warning(f"{balance.currency} 没有交易记录，使用当前价格作为成本价")
                
                position = PositionModel(
                    symbol=symbol,
                    currency=balance.currency,
                    amount=balance.total,
                    avg_price=avg_price,
                    current_price=current_price
                )
                
                positions.append(position)
                total_value += position.market_value
                total_crypto_cost += actual_cost
        
        # 计算真实的盈亏
        # 实际盈亏 = 当前总价值 - 初始投入资金
        real_total_pnl = total_value - initial_balance
        real_pnl_rate = real_total_pnl / initial_balance if initial_balance > 0 else 0.0
        
        # 创建投资组合模型，使用初始资金作为总成本进行正确的盈亏计算
        portfolio = PortfolioModel(
            total_value=total_value,
            total_cost=initial_balance,  # 使用初始投入资金作为总成本
            balances=balances,
            positions=positions
        )
        
        # 重写盈亏计算为真实的投资组合盈亏
        portfolio._total_pnl = real_total_pnl
        portfolio._total_pnl_rate = real_pnl_rate
        
        return portfolio
    
    def _get_actual_purchase_cost(self, currency: str) -> float:
        """
        获取实际购买成本（总花费的USDT金额）
        
        Args:
            currency: 币种
            
        Returns:
            float: 实际购买成本
        """
        try:
            # 直接从API获取交易记录，因为数据库可能没有完整的记录
            if not hasattr(self, '_private_fetcher') or self._private_fetcher is None:
                logger.warning(f"私有数据获取器未初始化，{currency} 无法获取购买成本")
                return 0.0
            
            # 获取该币种的所有交易记录
            symbol = f"{currency}/USDT"
            all_trades = self._private_fetcher.get_trades(symbol=symbol)
            
            # 筛选买入交易
            buy_trades = [trade for trade in all_trades if trade.side.value == 'buy']
            
            if not buy_trades:
                logger.warning(f"没有找到{currency}的买入交易记录")
                return 0.0
            
            # 计算总购买成本
            total_cost = sum(trade.cost for trade in buy_trades)
            logger.info(f"{currency} 总购买成本: ${total_cost:.2f}")
            
            return total_cost
                
        except Exception as e:
            logger.error(f"获取{currency}购买成本时出错: {e}")
            return 0.0

    def _calculate_average_cost(self, currency: str) -> float:
        """
        计算平均持仓成本
        
        Args:
            currency: 币种
            
        Returns:
            float: 平均成本价
        """
        try:
            # 从数据库获取该币种的买入交易记录
            with db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT price, amount FROM trades 
                    WHERE symbol LIKE ? AND side = 'buy'
                    ORDER BY timestamp DESC
                    LIMIT 100
                """, (f"{currency}/%",))
                
                trades = cursor.fetchall()
                
                if not trades:
                    logger.warning(f"没有找到{currency}的买入交易记录")
                    # 对于没有交易记录的币种，我们无法确定真实成本价
                    # 返回0，让调用者决定如何处理
                    return 0.0
                
                total_cost = 0.0
                total_amount = 0.0
                
                for trade in trades:
                    price = trade[0]
                    amount = trade[1]
                    cost = price * amount
                    total_cost += cost
                    total_amount += amount
                    logger.debug(f"{currency} 交易: 价格={price}, 数量={amount}, 成本={cost}")
                
                avg_cost = total_cost / total_amount if total_amount > 0 else 0.0
                logger.info(f"{currency} 平均成本计算: 总成本={total_cost}, 总数量={total_amount}, 平均价格={avg_cost}")
                
                return avg_cost
                
        except Exception as e:
            logger.error(f"计算{currency}平均成本时出错: {e}")
            return 0.0
    
    def save_daily_snapshot(self, portfolio: PortfolioModel, snapshot_date: Optional[date] = None):
        """
        保存每日投资组合快照
        
        Args:
            portfolio: 投资组合模型
            snapshot_date: 快照日期（默认为当天）
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        # 构建详细的投资组合数据
        portfolio_data = {
            'positions': [
                {
                    'symbol': pos.symbol,
                    'currency': pos.currency,
                    'amount': pos.amount,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_rate': pos.unrealized_pnl_rate
                } for pos in portfolio.positions
            ],
            'balances': [
                {
                    'currency': bal.currency,
                    'total': bal.total,
                    'free': bal.free,
                    'used': bal.used
                } for bal in portfolio.balances
            ],
            'asset_allocation': portfolio.asset_allocation
        }
        
        # 保存到数据库
        db_manager.save_daily_snapshot(
            date=snapshot_date.isoformat(),
            total_value=portfolio.total_value,
            total_cost=portfolio.total_cost,
            pnl=portfolio.total_pnl,
            pnl_rate=portfolio.total_pnl_rate,
            portfolio_data=portfolio_data
        )
        
        logger.info(f"已保存{snapshot_date}的投资组合快照")
    
    def get_portfolio_history(self, days: int = 30) -> List[Dict]:
        """
        获取投资组合历史
        
        Args:
            days: 获取天数
            
        Returns:
            List[Dict]: 历史快照列表
        """
        return db_manager.get_daily_snapshots(days)
    
    def calculate_performance_metrics(self, days: int = 30) -> Dict:
        """
        计算投资组合表现指标
        
        Args:
            days: 计算天数
            
        Returns:
            Dict: 表现指标
        """
        snapshots = self.get_portfolio_history(days)
        
        if len(snapshots) < 2:
            return {
                'total_return': 0.0,
                'daily_return': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0
            }
        
        # 计算日收益率
        daily_returns = []
        values = [snapshot['total_value'] for snapshot in reversed(snapshots)]
        
        for i in range(1, len(values)):
            daily_return = (values[i] - values[i-1]) / values[i-1]
            daily_returns.append(daily_return)
        
        # 总收益率
        total_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0.0
        
        # 平均日收益率
        avg_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        
        # 波动率（年化）
        if len(daily_returns) > 1:
            variance = sum((r - avg_daily_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            volatility = (variance ** 0.5) * (365 ** 0.5)  # 年化波动率
        else:
            volatility = 0.0
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown(values)
        
        # 夏普比率（简化计算，假设无风险利率为0）
        sharpe_ratio = avg_daily_return / volatility * (365 ** 0.5) if volatility > 0 else 0.0
        
        return {
            'total_return': total_return,
            'daily_return': avg_daily_return,
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'days_analyzed': len(snapshots)
        }
    
    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """计算最大回撤"""
        if not values:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def generate_basic_analysis(self, portfolio: PortfolioModel, market_data: Dict) -> Dict:
        """
        生成基础投资组合分析（不依赖AI）
        
        Args:
            portfolio: 投资组合模型
            market_data: 市场数据
            
        Returns:
            Dict: 基础分析结果
        """
        try:
            # 计算资产配置
            asset_allocation = {}
            for pos in portfolio.positions:
                percentage = (pos.market_value / portfolio.total_value * 100) if portfolio.total_value > 0 else 0
                asset_allocation[pos.currency] = percentage
            
            # 计算USDT配置
            usdt_balance = next((bal.total for bal in portfolio.balances if bal.currency == 'USDT'), 0)
            if usdt_balance > 0:
                usdt_percentage = (usdt_balance / portfolio.total_value * 100) if portfolio.total_value > 0 else 0
                asset_allocation['USDT'] = usdt_percentage
            
            # 分析持仓状况
            total_positions = len(portfolio.positions)
            profitable_positions = len([pos for pos in portfolio.positions if pos.unrealized_pnl > 0])
            loss_positions = len([pos for pos in portfolio.positions if pos.unrealized_pnl < 0])
            
            # 风险评估
            risk_level = self._assess_risk_level(portfolio, asset_allocation)
            
            # 生成基础建议
            suggestions = self._generate_basic_suggestions(portfolio, asset_allocation, market_data)
            
            # 计算表现指标
            performance_metrics = self.calculate_performance_metrics(30)
            
            return {
                'portfolio_overview': {
                    'total_value': portfolio.total_value,
                    'total_cost': portfolio.total_cost,
                    'total_pnl': portfolio.total_pnl,
                    'total_pnl_rate': portfolio.total_pnl_rate,
                    'total_positions': total_positions,
                    'profitable_positions': profitable_positions,
                    'loss_positions': loss_positions
                },
                'asset_allocation': asset_allocation,
                'risk_assessment': {
                    'risk_level': risk_level,
                    'diversification_score': self._calculate_diversification_score(asset_allocation),
                    'volatility': performance_metrics.get('volatility', 0),
                    'max_drawdown': performance_metrics.get('max_drawdown', 0)
                },
                'basic_suggestions': suggestions,
                'performance_metrics': performance_metrics,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成基础分析时出错: {e}")
            return {
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def _assess_risk_level(self, portfolio: PortfolioModel, asset_allocation: Dict) -> str:
        """评估风险水平"""
        # 基于资产配置和持仓分散度评估风险
        usdt_percentage = asset_allocation.get('USDT', 0)
        
        # 计算最大单一持仓比例
        max_single_position = max([pct for symbol, pct in asset_allocation.items() if symbol != 'USDT'], default=0)
        
        # 风险评估逻辑
        if usdt_percentage >= 50:
            return "低风险"
        elif usdt_percentage >= 20 and max_single_position <= 40:
            return "中等风险"
        elif max_single_position >= 60:
            return "高风险"
        else:
            return "中高风险"
    
    def _calculate_diversification_score(self, asset_allocation: Dict) -> float:
        """计算多样化分数（0-1，1表示完全分散）"""
        if not asset_allocation:
            return 0.0
        
        # 使用赫芬达尔指数的变形来计算集中度
        concentrations = [pct/100 for pct in asset_allocation.values()]
        hhi = sum(c**2 for c in concentrations)
        
        # 转换为多样化分数（1-HHI），值越高表示越分散
        diversification_score = 1 - hhi
        return max(0, min(1, diversification_score))
    
    def _generate_basic_suggestions(self, portfolio: PortfolioModel, asset_allocation: Dict, market_data: Dict) -> List[str]:
        """生成基础投资建议"""
        suggestions = []
        
        usdt_percentage = asset_allocation.get('USDT', 0)
        
        # USDT配置建议
        if usdt_percentage < 5:
            suggestions.append("💰 建议保留5-15%的USDT作为风险缓冲和机会资金")
        elif usdt_percentage > 80:
            suggestions.append("💰 USDT配置较高，可考虑逐步增加优质加密货币配置")
        elif usdt_percentage > 60:
            suggestions.append("💡 当前USDT配置较为保守，适合震荡市场或等待机会")
        
        # 单一持仓过大警告
        for symbol, percentage in asset_allocation.items():
            if symbol != 'USDT' and percentage > 50:
                suggestions.append(f"⚠️ {symbol}持仓占比{percentage:.1f}%过高，建议分散风险")
            elif symbol != 'USDT' and percentage > 30:
                suggestions.append(f"📊 {symbol}持仓占比{percentage:.1f}%，注意风险控制")
        
        # 盈亏分析建议
        loss_positions = [pos for pos in portfolio.positions if pos.unrealized_pnl < 0]
        if loss_positions:
            for pos in loss_positions:
                loss_rate = abs(pos.unrealized_pnl_rate * 100)
                if loss_rate > 15:
                    suggestions.append(f"� {pos.currency}亏损{loss_rate:.1f}%，建议重新评估或设置止损")
                elif loss_rate > 5:
                    suggestions.append(f"📉 {pos.currency}亏损{loss_rate:.1f}%，密切关注价格走势")
        
        # 盈利建议
        profitable_positions = [pos for pos in portfolio.positions if pos.unrealized_pnl > 50]  # 盈利超过50 USDT
        if profitable_positions:
            for pos in profitable_positions:
                profit_rate = pos.unrealized_pnl_rate * 100
                if profit_rate > 100:
                    suggestions.append(f"🎯 {pos.currency}盈利{profit_rate:.1f}%，建议部分获利了结")
                elif profit_rate > 30:
                    suggestions.append(f"📈 {pos.currency}盈利{profit_rate:.1f}%，可考虑设置移动止盈")
        
        # 投资组合整体建议
        if portfolio.total_pnl_rate > 1:  # 总盈利率超过100%
            suggestions.append("🏆 投资组合表现优异，建议逐步锁定利润并保持多样化")
        elif portfolio.total_pnl_rate > 0.2:  # 总盈利率超过20%
            suggestions.append("📊 投资组合表现良好，继续保持策略")
        elif portfolio.total_pnl_rate < -0.1:  # 总亏损超过10%
            suggestions.append("📉 投资组合出现亏损，建议重新评估策略和风险管理")
        elif portfolio.total_pnl_rate < -0.05:  # 总亏损超过5%
            suggestions.append("⚠️ 投资组合略有亏损，注意风险控制")
        
        return suggestions[:5]  # 最多返回5条建议
    
    def get_position_analysis(self, symbol: str) -> Dict:
        """
        获取特定持仓的详细分析
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Dict: 持仓分析结果
        """
        try:
            # 获取该交易对的交易历史
            with db_manager._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT side, price, amount, cost, timestamp 
                    FROM trades 
                    WHERE symbol = ?
                    ORDER BY timestamp ASC
                """, (symbol,))
                
                trades = [dict(row) for row in cursor.fetchall()]
            
            if not trades:
                return {'error': '没有找到该交易对的交易记录'}
            
            # 分析买入卖出
            total_bought = sum(trade['amount'] for trade in trades if trade['side'] == 'buy')
            total_sold = sum(trade['amount'] for trade in trades if trade['side'] == 'sell')
            current_position = total_bought - total_sold
            
            # 计算平均买入价
            buy_trades = [trade for trade in trades if trade['side'] == 'buy']
            if buy_trades:
                avg_buy_price = sum(trade['cost'] for trade in buy_trades) / sum(trade['amount'] for trade in buy_trades)
            else:
                avg_buy_price = 0.0
            
            # 计算平均卖出价
            sell_trades = [trade for trade in trades if trade['side'] == 'sell']
            if sell_trades:
                avg_sell_price = sum(trade['cost'] for trade in sell_trades) / sum(trade['amount'] for trade in sell_trades)
            else:
                avg_sell_price = 0.0
            
            return {
                'symbol': symbol,
                'total_bought': total_bought,
                'total_sold': total_sold,
                'current_position': current_position,
                'avg_buy_price': avg_buy_price,
                'avg_sell_price': avg_sell_price,
                'trade_count': len(trades),
                'first_trade': datetime.fromtimestamp(trades[0]['timestamp'] / 1000).isoformat() if trades else None,
                'last_trade': datetime.fromtimestamp(trades[-1]['timestamp'] / 1000).isoformat() if trades else None
            }
            
        except Exception as e:
            logger.error(f"分析持仓{symbol}时出错: {e}")
            return {'error': str(e)}
