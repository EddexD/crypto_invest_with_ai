"""
技术指标分析模块
计算各种技术指标用于AI决策
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class TechnicalIndicators:
    """技术指标数据类"""
    sma_20: float           # 20日简单移动平均
    sma_50: float           # 50日简单移动平均
    ema_12: float           # 12日指数移动平均
    ema_26: float           # 26日指数移动平均
    rsi: float              # 相对强弱指数
    macd: float             # MACD值
    macd_signal: float      # MACD信号线
    macd_histogram: float   # MACD柱状图
    bb_upper: float         # 布林带上轨
    bb_middle: float        # 布林带中轨
    bb_lower: float         # 布林带下轨
    bb_position: float      # 价格在布林带中的位置 (0-1)
    volume_sma: float       # 成交量移动平均
    support: Optional[float] = None    # 支撑位
    resistance: Optional[float] = None # 阻力位

class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self):
        pass
    
    def calculate_indicators(self, candles: List[Dict]) -> TechnicalIndicators:
        """
        计算技术指标
        
        Args:
            candles: K线数据列表，包含 timestamp, open, high, low, close, volume
            
        Returns:
            TechnicalIndicators: 技术指标对象
        """
        if len(candles) < 50:
            raise ValueError("需要至少50根K线数据来计算技术指标")
        
        # 转换为DataFrame
        df = pd.DataFrame(candles)
        df = df.sort_values('timestamp')
        
        # 计算移动平均线
        sma_20 = self._calculate_sma(df['close'], 20)
        sma_50 = self._calculate_sma(df['close'], 50)
        ema_12 = self._calculate_ema(df['close'], 12)
        ema_26 = self._calculate_ema(df['close'], 26)
        
        # 计算RSI
        rsi = self._calculate_rsi(df['close'])
        
        # 计算MACD
        macd, macd_signal, macd_histogram = self._calculate_macd(df['close'])
        
        # 计算布林带
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(df['close'])
        bb_position = self._calculate_bb_position(df['close'].iloc[-1], bb_upper, bb_lower)
        
        # 计算成交量移动平均
        volume_sma = self._calculate_sma(df['volume'], 20)
        
        # 计算支撑阻力位
        support, resistance = self._calculate_support_resistance(df)
        
        return TechnicalIndicators(
            sma_20=sma_20,
            sma_50=sma_50,
            ema_12=ema_12,
            ema_26=ema_26,
            rsi=rsi,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            bb_position=bb_position,
            volume_sma=volume_sma,
            support=support,
            resistance=resistance
        )
    
    def _calculate_sma(self, prices: pd.Series, period: int) -> float:
        """计算简单移动平均"""
        return prices.rolling(window=period).mean().iloc[-1]
    
    def _calculate_ema(self, prices: pd.Series, period: int) -> float:
        """计算指数移动平均"""
        return prices.ewm(span=period).mean().iloc[-1]
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算相对强弱指数"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    
    def _calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9) -> Tuple[float, float, float]:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        
        return macd.iloc[-1], macd_signal.iloc[-1], macd_histogram.iloc[-1]
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period=20, std_dev=2) -> Tuple[float, float, float]:
        """计算布林带"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        bb_upper = sma + (std * std_dev)
        bb_lower = sma - (std * std_dev)
        
        return bb_upper.iloc[-1], sma.iloc[-1], bb_lower.iloc[-1]
    
    def _calculate_bb_position(self, current_price: float, bb_upper: float, bb_lower: float) -> float:
        """计算价格在布林带中的位置"""
        if bb_upper == bb_lower:
            return 0.5
        return (current_price - bb_lower) / (bb_upper - bb_lower)
    
    def _calculate_support_resistance(self, df: pd.DataFrame, lookback=20) -> Tuple[Optional[float], Optional[float]]:
        """计算支撑和阻力位"""
        recent_data = df.tail(lookback)
        
        # 简单的支撑阻力计算：使用最近的低点和高点
        support = recent_data['low'].min()
        resistance = recent_data['high'].max()
        
        return support, resistance
    
    def get_trend_analysis(self, indicators: TechnicalIndicators) -> Dict[str, str]:
        """
        趋势分析
        
        Args:
            indicators: 技术指标对象
            
        Returns:
            Dict: 趋势分析结果
        """
        trend_signals = {}
        
        # 移动平均趋势
        if indicators.sma_20 > indicators.sma_50:
            trend_signals['ma_trend'] = 'bullish'
        else:
            trend_signals['ma_trend'] = 'bearish'
        
        # MACD趋势
        if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
            trend_signals['macd_trend'] = 'bullish'
        elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
            trend_signals['macd_trend'] = 'bearish'
        else:
            trend_signals['macd_trend'] = 'neutral'
        
        # RSI信号
        if indicators.rsi > 70:
            trend_signals['rsi_signal'] = 'overbought'
        elif indicators.rsi < 30:
            trend_signals['rsi_signal'] = 'oversold'
        else:
            trend_signals['rsi_signal'] = 'neutral'
        
        # 布林带信号
        if indicators.bb_position > 0.8:
            trend_signals['bb_signal'] = 'overbought'
        elif indicators.bb_position < 0.2:
            trend_signals['bb_signal'] = 'oversold'
        else:
            trend_signals['bb_signal'] = 'neutral'
        
        return trend_signals
    
    def get_buy_sell_signals(self, indicators: TechnicalIndicators, current_price: float) -> Dict[str, float]:
        """
        生成买卖信号强度
        
        Args:
            indicators: 技术指标对象
            current_price: 当前价格
            
        Returns:
            Dict: 包含buy_strength和sell_strength的字典 (0-1之间)
        """
        buy_signals = []
        sell_signals = []
        
        # RSI信号
        if indicators.rsi < 30:
            buy_signals.append(0.8)
        elif indicators.rsi > 70:
            sell_signals.append(0.8)
        
        # MACD信号
        if indicators.macd > indicators.macd_signal and indicators.macd_histogram > 0:
            buy_signals.append(0.6)
        elif indicators.macd < indicators.macd_signal and indicators.macd_histogram < 0:
            sell_signals.append(0.6)
        
        # 布林带信号
        if indicators.bb_position < 0.2:
            buy_signals.append(0.7)
        elif indicators.bb_position > 0.8:
            sell_signals.append(0.7)
        
        # 移动平均信号
        if current_price > indicators.sma_20 > indicators.sma_50:
            buy_signals.append(0.5)
        elif current_price < indicators.sma_20 < indicators.sma_50:
            sell_signals.append(0.5)
        
        # 支撑阻力信号
        if indicators.support and current_price <= indicators.support * 1.02:
            buy_signals.append(0.6)
        if indicators.resistance and current_price >= indicators.resistance * 0.98:
            sell_signals.append(0.6)
        
        # 计算平均信号强度
        buy_strength = np.mean(buy_signals) if buy_signals else 0.0
        sell_strength = np.mean(sell_signals) if sell_signals else 0.0
        
        return {
            'buy_strength': min(buy_strength, 1.0),
            'sell_strength': min(sell_strength, 1.0)
        }
