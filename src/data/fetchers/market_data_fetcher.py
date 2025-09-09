"""
市场数据获取器
负责从各个交易所获取市场数据，包括实时价格、K线数据、交易量等
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from ..models.market_data import MarketDataModel, CandleDataModel

logger = logging.getLogger(__name__)

class MarketDataFetcher:
    """市场数据获取器"""
    
    def __init__(self, platform: str):
        """
        初始化市场数据获取器
        
        Args:
            platform: 交易所平台名称 (如: 'okx', 'binance', 'coinbase')
        """
        self.platform = platform
        
        if platform not in ccxt.exchanges:
            raise ValueError(f"Exchange {platform} not supported by ccxt library.")
            
        self.exchange = getattr(ccxt, platform)()
        logger.info(f"Initialized MarketDataFetcher for {platform}")

    def get_ticker(self, symbol: str) -> MarketDataModel:
        """
        获取指定交易对的实时行情数据
        
        Args:
            symbol: 交易对符号, 如 'BTC/USDT'
            
        Returns:
            MarketDataModel: 包含价格、成交量等信息的模型对象
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX添加市场类型参数
            if self.platform == 'okx':
                ticker = self.exchange.fetch_ticker(symbol, {'instType': 'SPOT'})
            else:
                ticker = self.exchange.fetch_ticker(symbol)
            
            return MarketDataModel(
                symbol=symbol,
                timestamp=ticker['timestamp'],
                datetime=ticker['datetime'],
                open=ticker['open'],
                high=ticker['high'],
                low=ticker['low'],
                close=ticker['close'],
                volume=ticker['baseVolume'],
                bid=ticker['bid'],
                ask=ticker['ask'],
                change=ticker['change'],
                percentage=ticker['percentage']
            )
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = '1h', 
                  limit: int = 100, since: Optional[int] = None) -> List[CandleDataModel]:
        """
        获取历史K线数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期 ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: 获取数量限制
            since: 开始时间戳
            
        Returns:
            List[CandleDataModel]: K线数据列表
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX添加市场类型参数
            if self.platform == 'okx':
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit, {'instType': 'SPOT'})
            else:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            
            candles = []
            for data in ohlcv:
                candles.append(CandleDataModel(
                    timestamp=data[0],
                    open=data[1],
                    high=data[2],
                    low=data[3],
                    close=data[4],
                    volume=data[5],
                    symbol=symbol,
                    timeframe=timeframe
                ))
            
            return candles
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    def get_orderbook(self, symbol: str, limit: int = 100) -> Dict:
        """
        获取订单簿数据
        
        Args:
            symbol: 交易对符号
            limit: 深度限制
            
        Returns:
            Dict: 包含买卖盘数据的字典
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX添加市场类型参数
            if self.platform == 'okx':
                orderbook = self.exchange.fetch_order_book(symbol, limit, None, {'instType': 'SPOT'})
            else:
                orderbook = self.exchange.fetch_order_book(symbol, limit)
                
            return {
                'symbol': symbol,
                'timestamp': orderbook['timestamp'],
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit]
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            raise

    def get_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """
        获取最近成交记录
        
        Args:
            symbol: 交易对符号
            limit: 获取数量限制
            
        Returns:
            List[Dict]: 成交记录列表
        """
        try:
            self.exchange.load_markets()
            
            # 为OKX添加市场类型参数
            if self.platform == 'okx':
                trades = self.exchange.fetch_trades(symbol, None, None, limit, {'instType': 'SPOT'})
            else:
                trades = self.exchange.fetch_trades(symbol, None, None, limit)
                
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}")
            raise

    def get_multiple_tickers(self, symbols: List[str]) -> Dict[str, MarketDataModel]:
        """
        批量获取多个交易对的行情数据
        
        Args:
            symbols: 交易对符号列表
            
        Returns:
            Dict[str, MarketDataModel]: 以符号为键的行情数据字典
        """
        result = {}
        for symbol in symbols:
            try:
                result[symbol] = self.get_ticker(symbol)
            except Exception as e:
                logger.warning(f"Failed to fetch ticker for {symbol}: {e}")
                continue
        
        return result

    def get_historical_data_range(self, symbol: str, timeframe: str, 
                                start_date: datetime, end_date: datetime) -> List[CandleDataModel]:
        """
        获取指定时间范围的历史数据
        
        Args:
            symbol: 交易对符号
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[CandleDataModel]: 历史K线数据
        """
        try:
            since = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            all_candles = []
            current_since = since
            
            # 分批获取数据以避免限制
            while current_since < end_timestamp:
                candles = self.get_ohlcv(symbol, timeframe, limit=1000, since=current_since)
                if not candles:
                    break
                    
                all_candles.extend(candles)
                current_since = candles[-1].timestamp + 1
                
                # 避免过于频繁的请求
                import time
                time.sleep(0.1)
            
            # 过滤到结束时间
            filtered_candles = [c for c in all_candles if c.timestamp <= end_timestamp]
            return filtered_candles
            
        except Exception as e:
            logger.error(f"Error fetching historical data range: {e}")
            raise

if __name__ == "__main__":
    # 测试代码
    fetcher = MarketDataFetcher('okx')
    
    # 测试获取行情
    ticker = fetcher.get_ticker('BTC/USDT')
    print(f"BTC/USDT Price: {ticker.close}")
    
    # 测试获取K线数据
    candles = fetcher.get_ohlcv('BTC/USDT', '1h', 10)
    print(f"Retrieved {len(candles)} candles")
