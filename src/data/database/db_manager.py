"""
数据库管理模块
使用SQLite存储历史数据、交易记录等
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "./data/crypto_invest.db"):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        with self._get_connection() as conn:
            # 市场数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    timeframe TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            """)
            
            # 交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    cost REAL NOT NULL,
                    fee REAL NOT NULL,
                    fee_currency TEXT,
                    timestamp INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trade_id)
                )
            """)
            
            # 订单记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL,
                    status TEXT NOT NULL,
                    filled REAL DEFAULT 0,
                    cost REAL DEFAULT 0,
                    fee REAL DEFAULT 0,
                    timestamp INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(order_id)
                )
            """)
            
            # AI建议记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    price REAL NOT NULL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # AI分析结果表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id TEXT NOT NULL,
                    market_analysis TEXT,
                    portfolio_review TEXT,
                    trading_signals TEXT,
                    risk_assessment TEXT,
                    ai_confidence REAL,
                    symbols TEXT,
                    analysis_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(analysis_id)
                )
            """)
            
            # 每日资产快照表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_value REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_rate REAL NOT NULL,
                    portfolio_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data(symbol, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades(symbol, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol_time ON orders(symbol, timestamp)")
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_market_data(self, symbol: str, candles: List[Dict], timeframe: str):
        """保存市场数据"""
        with self._get_connection() as conn:
            for candle in candles:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO market_data 
                        (symbol, timestamp, open, high, low, close, volume, timeframe)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        candle['timestamp'],
                        candle['open'],
                        candle['high'],
                        candle['low'],
                        candle['close'],
                        candle['volume'],
                        timeframe
                    ))
                except Exception as e:
                    logger.error(f"Error saving market data: {e}")
            conn.commit()
    
    def get_market_data(self, symbol: str, timeframe: str, 
                       start_time: Optional[int] = None, 
                       end_time: Optional[int] = None,
                       limit: int = 1000) -> List[Dict]:
        """获取市场数据"""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM market_data 
                WHERE symbol = ? AND timeframe = ?
            """
            params = [symbol, timeframe]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_trade(self, trade_data: Dict):
        """保存交易记录"""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO trades 
                    (trade_id, order_id, symbol, side, amount, price, cost, fee, fee_currency, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_data['id'],
                    trade_data['order_id'],
                    trade_data['symbol'],
                    trade_data['side'],
                    trade_data['amount'],
                    trade_data['price'],
                    trade_data['cost'],
                    trade_data['fee'],
                    trade_data['fee_currency'],
                    trade_data['timestamp']
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Error saving trade: {e}")
    
    def save_order(self, order_data: Dict):
        """保存订单记录"""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO orders 
                    (order_id, symbol, type, side, amount, price, status, filled, cost, fee, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order_data['id'],
                    order_data['symbol'],
                    order_data['type'],
                    order_data['side'],
                    order_data['amount'],
                    order_data['price'],
                    order_data['status'],
                    order_data['filled'],
                    order_data['cost'],
                    order_data['fee'],
                    order_data['timestamp']
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Error saving order: {e}")
    
    def save_ai_recommendation(self, symbol: str, action: str, 
                             confidence: float, price: float, reasoning: str):
        """保存AI建议"""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT INTO ai_recommendations 
                    (symbol, action, confidence, price, reasoning)
                    VALUES (?, ?, ?, ?, ?)
                """, (symbol, action, confidence, price, reasoning))
                conn.commit()
            except Exception as e:
                logger.error(f"Error saving AI recommendation: {e}")
    
    def get_ai_recommendations(self, symbol: Optional[str] = None, 
                             days: int = 7) -> List[Dict]:
        """获取AI建议历史"""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM ai_recommendations 
                WHERE created_at >= datetime('now', '-{} days')
            """.format(days)
            
            params = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_daily_snapshot(self, date: str, total_value: float, 
                          total_cost: float, pnl: float, pnl_rate: float,
                          portfolio_data: Dict):
        """保存每日资产快照"""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_snapshots 
                    (date, total_value, total_cost, pnl, pnl_rate, portfolio_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    date,
                    total_value,
                    total_cost,
                    pnl,
                    pnl_rate,
                    json.dumps(portfolio_data)
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Error saving daily snapshot: {e}")
    
    def get_daily_snapshots(self, days: int = 30) -> List[Dict]:
        """获取每日资产快照"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM daily_snapshots 
                WHERE date >= date('now', '-{} days')
                ORDER BY date DESC
            """.format(days))
            
            snapshots = []
            for row in cursor.fetchall():
                snapshot = dict(row)
                if snapshot['portfolio_data']:
                    snapshot['portfolio_data'] = json.loads(snapshot['portfolio_data'])
                snapshots.append(snapshot)
            
            return snapshots
    
    def get_trading_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取交易统计"""
        with self._get_connection() as conn:
            # 交易次数
            cursor = conn.execute("""
                SELECT COUNT(*) as trade_count 
                FROM trades 
                WHERE timestamp >= ?
            """, (int((datetime.now() - timedelta(days=days)).timestamp() * 1000),))
            trade_count = cursor.fetchone()[0]
            
            # 买卖比例
            cursor = conn.execute("""
                SELECT side, COUNT(*) as count 
                FROM trades 
                WHERE timestamp >= ?
                GROUP BY side
            """, (int((datetime.now() - timedelta(days=days)).timestamp() * 1000),))
            side_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 最活跃的交易对
            cursor = conn.execute("""
                SELECT symbol, COUNT(*) as count 
                FROM trades 
                WHERE timestamp >= ?
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 5
            """, (int((datetime.now() - timedelta(days=days)).timestamp() * 1000),))
            top_symbols = [{"symbol": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            return {
                "trade_count": trade_count,
                "buy_count": side_stats.get("buy", 0),
                "sell_count": side_stats.get("sell", 0),
                "top_symbols": top_symbols
            }
    
    def save_ai_analysis_result(self, analysis_id: str, result_data: Dict, symbols: List[str], expires_hours: int = 24):
        """
        保存AI分析结果
        
        Args:
            analysis_id: 分析任务ID
            result_data: 分析结果数据
            symbols: 分析的交易对列表
            expires_hours: 过期时间（小时）
        """
        with self._get_connection() as conn:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            conn.execute("""
                INSERT OR REPLACE INTO ai_analysis_results 
                (analysis_id, market_analysis, portfolio_review, trading_signals, 
                 risk_assessment, ai_confidence, symbols, analysis_data, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_id,
                result_data.get('market_analysis', ''),
                result_data.get('portfolio_review', ''),
                result_data.get('trading_signals', ''),
                result_data.get('risk_assessment', ''),
                result_data.get('ai_confidence', 0.0),
                json.dumps(symbols),
                json.dumps(result_data),
                expires_at
            ))
            conn.commit()
            logger.info(f"已保存AI分析结果: {analysis_id}")
    
    def get_ai_analysis_result(self, symbols: List[str], max_age_hours: int = 24) -> Optional[Dict]:
        """
        获取有效的AI分析结果
        
        Args:
            symbols: 交易对列表
            max_age_hours: 最大有效期（小时）
            
        Returns:
            Dict: 分析结果数据，如果没有有效结果则返回None
        """
        with self._get_connection() as conn:
            min_time = datetime.now() - timedelta(hours=max_age_hours)
            
            cursor = conn.execute("""
                SELECT analysis_data, created_at 
                FROM ai_analysis_results 
                WHERE symbols = ? 
                AND created_at >= ? 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC 
                LIMIT 1
            """, (json.dumps(symbols), min_time))
            
            row = cursor.fetchone()
            if row:
                result_data = json.loads(row[0])
                result_data['cached_at'] = row[1]
                logger.info(f"找到有效的AI分析缓存，创建时间: {row[1]}")
                return result_data
            
            return None
    
    def cleanup_expired_analysis_results(self):
        """清理过期的AI分析结果"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM ai_analysis_results 
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 条过期的AI分析结果")
    
    def is_analysis_in_progress(self) -> bool:
        """
        检查是否有正在进行的AI分析任务
        
        Returns:
            bool: 如果有任务正在进行则返回True
        """
        # 这个方法需要与任务管理器配合
        # 我们可以通过检查最近的分析结果时间来推断
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM ai_analysis_results 
                WHERE created_at >= ?
            """, (datetime.now() - timedelta(minutes=10),))
            
            recent_count = cursor.fetchone()[0]
            return recent_count == 0  # 如果最近10分钟没有结果，可能还在分析中

# 全局数据库管理器实例
db_manager = DatabaseManager()
