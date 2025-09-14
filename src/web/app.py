"""
Web应用程序主文件
使用Flask构建Web界面
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List
from functools import wraps
import threading
import time
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import os

# 导入我们的模块
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.config_manager import config_manager
from src.data.fetchers.market_data_fetcher import MarketDataFetcher
from src.data.fetchers.private_data_fetcher import PrivateDataFetcher
from src.ai.analysis.technical_analysis import TechnicalAnalyzer
from src.ai.recommendation.recommendation_engine import SmartRecommendationEngine
from src.trading.portfolio.portfolio_manager import PortfolioManager
from src.data.database.db_manager import db_manager
from .websocket_config import WEBSOCKET_CONFIG, REALTIME_DATA_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IP白名单配置
ALLOWED_IPS = config_manager.get_ip_whitelist()

def check_ip_whitelist(f):
    """检查IP白名单的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.environ.get('HTTP_CF_CONNECTING_IP', request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr))
        
        # 处理可能的多个IP情况（负载均衡器）
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        logger.info(f"客户端IP: {client_ip}")
        
        if client_ip not in ALLOWED_IPS:
            logger.warning(f"未授权的IP访问: {client_ip}")
            return jsonify({'error': '访问被拒绝：IP不在白名单中'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# 创建Flask应用
app = Flask(__name__, 
           static_folder='static',
           template_folder='templates')

# 创建SocketIO实例
socketio = SocketIO(
    app, 
    cors_allowed_origins=WEBSOCKET_CONFIG['cors_allowed_origins'],
    async_mode=WEBSOCKET_CONFIG['async_mode'],
    logger=WEBSOCKET_CONFIG['logger'],
    compression=WEBSOCKET_CONFIG['compression'],
    # 优化配置以减少polling请求
    ping_timeout=60,  # ping超时时间
    ping_interval=25,  # ping间隔时间
    transport=['websocket', 'polling'],  # 传输方式优先级
    allow_upgrades=True,  # 允许升级到websocket
    cookie=False,  # 不使用cookie
    json=json  # 使用标准json模块
)

# 全局变量
market_fetcher = None
private_fetcher = None
technical_analyzer = TechnicalAnalyzer()
ai_engine = SmartRecommendationEngine()
portfolio_manager = PortfolioManager()

def initialize_fetchers():
    """初始化数据获取器"""
    global market_fetcher, private_fetcher
    
    try:
        exchange_config = config_manager.get_exchange_config()
        logger.info(f"正在初始化数据获取器 - 交易所: {exchange_config.name}")
        
        # 初始化市场数据获取器
        market_fetcher = MarketDataFetcher(exchange_config.name)
        logger.info("市场数据获取器初始化成功")
        
        # 如果配置了API密钥，初始化私有数据获取器
        if exchange_config.api_key and exchange_config.secret_key:
            private_fetcher = PrivateDataFetcher(
                platform=exchange_config.name,
                api_key=exchange_config.api_key,
                secret=exchange_config.secret_key,
                password=exchange_config.passphrase
            )
            logger.info("私有数据获取器初始化成功")
        else:
            logger.warning("API密钥未配置，私有数据获取器未初始化")
            private_fetcher = None
        
        logger.info("数据获取器初始化完成")
    except Exception as e:
        logger.error(f"初始化数据获取器失败: {e}")
        # 即使失败也要创建空的获取器以避免None错误
        market_fetcher = None
        private_fetcher = None

# 在应用创建后立即初始化
def init_app():
    """初始化应用"""
    global market_fetcher, private_fetcher
    logger.info("开始初始化Web应用...")
    initialize_fetchers()
    logger.info("Web应用初始化完成")

# 调用初始化
init_app()

# 全局变量用于管理WebSocket连接
connected_clients = set()
data_broadcast_thread = None
broadcast_active = False

# WebSocket事件处理器
@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    logger.info(f"客户端连接: {request.sid}")
    connected_clients.add(request.sid)
    
    # 发送初始数据
    # emit_initial_data()
    
    # 启动数据广播线程（如果还没有启动）
    global data_broadcast_thread, broadcast_active
    if not broadcast_active:
        broadcast_active = True
        data_broadcast_thread = threading.Thread(target=data_broadcast_worker, daemon=True)
        data_broadcast_thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接事件"""
    logger.info(f"客户端断开连接: {request.sid}")
    connected_clients.discard(request.sid)
    
    # 如果没有客户端连接，停止广播
    global broadcast_active
    if not connected_clients:
        broadcast_active = False

@socketio.on('request_data')
def handle_request_data(data):
    """处理客户端数据请求"""
    data_type = data.get('type', '')
    
    if data_type == 'portfolio':
        emit_portfolio_data()
    elif data_type == 'portfolio_history':
        emit_portfolio_history()
    elif data_type == 'market':
        emit_market_data()
    elif data_type == 'orders':
        emit_orders_data()
    elif data_type == 'trades':
        emit_trades_data()
    elif data_type == 'basic_analysis':
        emit_basic_analysis()
    elif data_type == 'all':
        emit_initial_data()

@socketio.on('request_smart_analysis')
def handle_smart_analysis_request(data):
    """处理智能分析请求"""
    try:
        force_refresh = data.get('force_refresh', False)
        client_ip = request.environ.get('HTTP_CF_CONNECTING_IP', 
                                       request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr))
        
        # 处理可能的多个IP情况
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # 非白名单IP不能强制刷新
        if client_ip not in ALLOWED_IPS:
            force_refresh = False
            logger.info(f"非白名单IP请求智能分析，禁用强制刷新: {client_ip}")
        logger.info(f"智能分析请求 - 来自IP: {client_ip}, 强制刷新: {force_refresh}")
        # 获取投资组合数据
        portfolio_data = {}
        if private_fetcher and force_refresh:
            try:
                balances = private_fetcher.get_balances()
                symbols = config_manager.get_symbols()
                current_prices = {}
                
                for symbol in symbols:
                    try:
                        ticker = market_fetcher.get_ticker(symbol)
                        current_prices[symbol] = ticker.close
                    except Exception as e:
                        logger.warning(f"获取{symbol}价格失败: {e}")
                
                portfolio = portfolio_manager.create_portfolio_snapshot(balances, current_prices, private_fetcher)
                portfolio_data = {
                    'total_value': portfolio.total_value,
                    'total_cost': portfolio.total_cost,
                    'total_pnl': portfolio.total_pnl,
                    'total_pnl_rate': portfolio.total_pnl_rate,
                    'balances': {balance.currency: balance.total for balance in balances},
                    'positions': [
                        {
                            'symbol': pos.symbol,
                            'amount': pos.amount,
                            'cost': pos.amount * (pos.market_value / pos.amount if pos.amount > 0 else 0) * (1 - pos.unrealized_pnl_rate),
                            'market_value': pos.market_value,
                            'unrealized_pnl': pos.unrealized_pnl,
                            'unrealized_pnl_rate': pos.unrealized_pnl_rate
                        } for pos in portfolio.positions
                    ]
                }
            except Exception as e:
                logger.warning(f"获取投资组合数据失败: {e}")
                portfolio_data = {
                    'total_value': 0,
                    'total_cost': 0,
                    'total_pnl': 0,
                    'total_pnl_rate': 0,
                    'balances': {},
                    'positions': []
                }
        
        # 获取主要交易对
        symbols = config_manager.get_symbols()
        
        # 启动异步分析任务
        task_id = ai_engine.generate_comprehensive_analysis_async(
            portfolio_data, 
            symbols, 
            force_refresh=force_refresh
        )
        
        emit('smart_analysis_started', {
            'task_id': task_id,
            'status': 'started',
            'message': '智能分析任务已启动'
        })
        
    except Exception as e:
        logger.error(f"启动智能分析任务失败: {e}")
        emit('smart_analysis_error', {'error': str(e)})

@socketio.on('request_analysis_status')
def handle_analysis_status_request(data):
    """处理分析状态查询请求"""
    try:
        task_id = data.get('task_id')
        if not task_id:
            emit('analysis_status_error', {'error': '缺少task_id参数'})
            return
        
        status_info = ai_engine.get_analysis_status(task_id)
        
        if not status_info:
            emit('analysis_status_error', {'error': '任务不存在或已过期'})
            return
        
        emit('analysis_status_update', status_info)
        
    except Exception as e:
        logger.error(f"获取分析状态失败: {e}")
        emit('analysis_status_error', {'error': str(e)})

@socketio.on('save_snapshot')
def handle_save_snapshot_request(data):
    """处理保存快照请求"""
    try:
        # 保存投资组合快照
        save_daily_portfolio_snapshot()
        
        # 发送成功响应
        emit('snapshot_save_success', {
            'success': True,
            'message': '快照保存成功'
        })
        
        # 自动发送最新的数据给客户端
        emit_initial_data()
        
    except Exception as e:
        logger.error(f"保存快照失败: {e}")
        emit('snapshot_save_error', {'error': str(e)})

def emit_initial_data():
    """发送初始数据给新连接的客户端"""
    try:
        emit_portfolio_data()
        emit_portfolio_history()
        emit_market_data()
        emit_orders_data()
        emit_trades_data()
        emit_basic_analysis()  # 添加基础分析数据
    except Exception as e:
        logger.error(f"发送初始数据失败: {e}")

def emit_basic_analysis():
    """发送基础投资组合分析"""
    try:
        if not private_fetcher:
            emit('basic_analysis_error', {'error': '未配置API密钥，无法获取投资组合数据'})
            return
        
        # 获取投资组合数据
        balances = private_fetcher.get_balances()
        symbols = config_manager.get_symbols()
        current_prices = {}
        
        # 获取当前价格
        for symbol in symbols:
            try:
                ticker = market_fetcher.get_ticker(symbol)
                current_prices[symbol] = ticker.close
            except Exception as e:
                logger.warning(f"获取{symbol}价格失败: {e}")
        
        # 创建投资组合快照
        portfolio = portfolio_manager.create_portfolio_snapshot(balances, current_prices, private_fetcher)
        
        # 获取市场数据用于分析
        market_data = {}
        for symbol in symbols:
            try:
                ticker = market_fetcher.get_ticker(symbol)
                market_data[symbol] = {
                    'symbol': symbol,
                    'price': ticker.close,
                    'change_24h': ticker.percentage
                }
            except Exception as e:
                logger.warning(f"获取{symbol}市场数据失败: {e}")
        
        # 生成基础分析
        basic_analysis = portfolio_manager.generate_basic_analysis(portfolio, market_data)
        
        emit('basic_analysis_update', {
            'analysis': basic_analysis,
            'portfolio_summary': {
                'total_value': portfolio.total_value,
                'total_cost': portfolio.total_cost,
                'total_pnl': portfolio.total_pnl,
                'total_pnl_rate': portfolio.total_pnl_rate,
                'positions_count': len(portfolio.positions)
            },
            'data_source': 'backend_calculation',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"获取基础投资组合分析失败: {e}")
        emit('basic_analysis_error', {'error': str(e)})

def emit_portfolio_data():
    """发送投资组合数据"""
    try:
        if not private_fetcher:
            return
        
        # 获取投资组合数据（复用现有逻辑）
        balances = private_fetcher.get_balances()
        positions = private_fetcher.get_positions()
        
        total_value = 0.0
        total_cost = 0.0
        
        # 处理USDT余额
        usdt_balance = 0.0
        for balance in balances:
            if balance.currency == 'USDT':
                usdt_balance = balance.total
                total_value += balance.total
                break
        
        # 处理加密货币持仓
        for position in positions:
            total_value += position.market_value
            total_cost += position.cost_value
        
        total_pnl = total_value - total_cost - usdt_balance
        total_pnl_rate = (total_pnl / total_cost) if total_cost > 0 else 0
        daily_return = (total_pnl / total_value) if total_value > 0 else 0
        
        # 计算资产配置
        asset_allocation = {}
        if total_value > 0:
            for balance in balances:
                if balance.currency == 'USDT':
                    asset_allocation[balance.currency] = (balance.total / total_value) * 100
            
            for position in positions:
                asset_allocation[position.currency] = (position.market_value / total_value) * 100
        performance = {
            'total_return': daily_return,  # 转换为小数形式
            'daily_return': daily_return,
            'volatility': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        _positions = [
                {
                    'symbol': pos.symbol,
                    'currency': pos.currency,
                    'amount': pos.amount,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_rate': pos.unrealized_pnl_rate
                } for pos in positions
            ]
        #合计数据
        total_symbol = {
            "symbol": "合计",
            "currency": "合计",
            "amount": sum(pos['market_value'] for pos in _positions),
            "avg_price": 0,
            "current_price": 0,
            "market_value": total_cost,
            "unrealized_pnl": total_pnl,
            "unrealized_pnl_rate": total_pnl_rate
        }
        _positions.append(total_symbol)
        portfolio_data = {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_rate': total_pnl_rate,
            'asset_allocation': asset_allocation,
            "performance": performance,
            'positions': _positions,
            'balances': [
                {
                    'currency': bal.currency,
                    'total': bal.total,
                    'free': bal.free,
                    'used': bal.used
                } for bal in balances
            ]
        }
        
        socketio.emit('portfolio_update', portfolio_data)
        
    except Exception as e:
        logger.error(f"发送投资组合数据失败: {e}")

def emit_portfolio_history():
    """发送投资组合历史数据"""
    try:
        # 从数据库获取历史快照数据
        snapshots = db_manager.get_daily_snapshots(days=30)
        
        if not snapshots:
            # 如果没有历史数据，创建当前快照作为起点
            if private_fetcher:
                try:
                    # 获取当前投资组合数据
                    balances = private_fetcher.get_balances()
                    symbols = config_manager.get_symbols()
                    current_prices = {}
                    
                    for symbol in symbols:
                        try:
                            ticker = market_fetcher.get_ticker(symbol)
                            current_prices[symbol] = ticker.close
                        except Exception as e:
                            logger.warning(f"获取{symbol}价格失败: {e}")
                    
                    # 创建投资组合快照
                    portfolio = portfolio_manager.create_portfolio_snapshot(balances, current_prices, private_fetcher)
                    
                    # 保存到数据库
                    today = datetime.now().strftime('%Y-%m-%d')
                    db_manager.save_daily_snapshot(
                        date=today,
                        total_value=portfolio.total_value,
                        total_cost=portfolio.total_cost,
                        pnl=portfolio.total_pnl,
                        pnl_rate=portfolio.total_pnl_rate,
                        portfolio_data={
                            'positions': [pos.__dict__ for pos in portfolio.positions],
                            'balances': [bal.__dict__ for bal in portfolio.balances],
                            'asset_allocation': portfolio.asset_allocation
                        }
                    )
                    
                    snapshots = [{'date': today, 'total_value': portfolio.total_value, 
                                'total_cost': portfolio.total_cost, 'pnl': portfolio.total_pnl, 
                                'pnl_rate': portfolio.total_pnl_rate}]
                    
                except Exception as e:
                    logger.error(f"创建当前快照失败: {e}")
                    socketio.emit('portfolio_history_error', {'error': '无法获取投资组合数据'})
                    return
            else:
                socketio.emit('portfolio_history_error', {'error': '未配置API密钥，无法获取历史数据'})
                return
        
        # 转换为图表需要的格式
        history = []
        for snapshot in reversed(snapshots):  # 从旧到新排序
            history.append({
                'date': snapshot['date'],
                'total_value': snapshot['total_value'],
                'return_rate': snapshot['pnl_rate']  # 使用收益率而不是未实现盈亏
            })
        
        history_data = {
            'history': history,
            'period': '30d',
            'data_source': 'database'
        }
        
        socketio.emit('portfolio_history_update', history_data)
        
    except Exception as e:
        logger.error(f"发送投资组合历史数据失败: {e}")
        socketio.emit('portfolio_history_error', {'error': str(e)})

def emit_market_data():
    """发送市场数据"""
    try:
        if not market_fetcher:
            return
            
        symbols = config_manager.get_symbols()
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = market_fetcher.get_ticker(symbol)
                market_data[symbol] = {
                    'price': ticker.close,
                    'change': ticker.change,
                    'percentage': ticker.percentage
                }
            except Exception as e:
                logger.warning(f"获取{symbol}市场数据失败: {e}")
        
        socketio.emit('market_update', {'market_data': market_data})
        
    except Exception as e:
        logger.error(f"发送市场数据失败: {e}")

def emit_orders_data():
    """发送订单数据"""
    try:
        if not private_fetcher:
            return
        
        # 获取未完成订单
        try:
            open_orders = private_fetcher.get_open_orders()
        except Exception as e:
            logger.warning(f"获取未完成订单失败: {e}")
            open_orders = []
        
        orders_data = {
            'open_orders': [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'type': order.type.value if hasattr(order.type, 'value') else str(order.type),
                    'side': order.side.value if hasattr(order.side, 'value') else str(order.side),
                    'amount': order.amount,
                    'price': order.price,
                    'filled': order.filled,
                    'cost': order.cost if hasattr(order, 'cost') else (order.price * order.filled if hasattr(order, 'price') and hasattr(order, 'filled') else 0),
                    'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                    'datetime': order.datetime_str
                } for order in open_orders
            ]
        }
        
        socketio.emit('orders_update', orders_data)
        
    except Exception as e:
        logger.error(f"发送订单数据失败: {e}")

def emit_trades_data():
    """发送交易数据"""
    try:
        if not private_fetcher:
            return
        
        trades = private_fetcher.get_trades(limit=100)
        
        trades_data = {
            'trades': [
                {
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'side': trade.side.value if hasattr(trade.side, 'value') else str(trade.side),
                    'amount': trade.amount,
                    'price': trade.price,
                    'cost': trade.cost,
                    'fee': trade.fee*trade.price if trade.side.value == 'buy' else trade.fee,
                    'datetime': trade.datetime_str
                } for trade in trades
            ]
        }
        
        socketio.emit('trades_update', trades_data)
        
    except Exception as e:
        logger.error(f"发送交易数据失败: {e}")

def data_broadcast_worker():
    """数据广播工作线程"""
    global broadcast_active
    
    # 获取配置
    interval = WEBSOCKET_CONFIG['broadcast_interval']
    frequencies = REALTIME_DATA_CONFIG['update_frequencies']
    enabled_types = REALTIME_DATA_CONFIG['enabled_data_types']
    
    # 计数器用于控制不同数据类型的更新频率
    counters = {data_type: 0 for data_type in enabled_types}
    
    while broadcast_active and connected_clients:
        try:
            current_time = time.time()
            
            # 检查每种数据类型是否需要更新
            for data_type in enabled_types:
                if not connected_clients:
                    break
                    
                frequency = frequencies.get(data_type, interval)
                if counters[data_type] * interval >= frequency:
                    counters[data_type] = 0
                    
                    # 发送对应类型的数据
                    if data_type == 'portfolio':
                        emit_portfolio_data()
                    elif data_type == 'market':
                        emit_market_data()
                    elif data_type == 'orders':
                        emit_orders_data()
                    elif data_type == 'trades':
                        emit_trades_data()
                
                counters[data_type] += 1
            
            # 等待下一个周期
            for _ in range(interval):
                if not broadcast_active or not connected_clients:
                    break
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"数据广播失败: {e}")
            time.sleep(5)  # 出错时等待5秒再重试
    
    logger.info("数据广播线程结束")

@app.route('/')
def dashboard():
    """主仪表板页面"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health_check():
    """健康检查"""
    global market_fetcher, private_fetcher
    
    status = {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'market_fetcher_ready': market_fetcher is not None,
        'private_fetcher_ready': private_fetcher is not None,
        'config_status': config_manager.is_configured()
    }
    
    if not market_fetcher:
        status['status'] = 'error'
        status['error'] = '市场数据获取器未初始化'
    
    if not config_manager.is_configured():
        status['status'] = 'error'
        status['error'] = 'API密钥未配置'
    
    return jsonify(status)

def save_daily_portfolio_snapshot():
    """保存每日投资组合快照"""
    try:
        if not private_fetcher:
            logger.warning("私有数据获取器未初始化，无法保存快照")
            return
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 检查今天是否已经有快照
        existing_snapshots = db_manager.get_daily_snapshots(days=1)
        if existing_snapshots and existing_snapshots[0]['date'] == today:
            logger.info("今日快照已存在，跳过保存")
            if not os.path.exists(os.path.join(os.path.dirname(__file__), 'static', 'portfolio_latest.png')):
                generate_portfolio_chart()
            return
        
        # 获取当前投资组合数据
        balances = private_fetcher.get_balances()
        symbols = config_manager.get_symbols()
        current_prices = {}
        
        for symbol in symbols:
            try:
                ticker = market_fetcher.get_ticker(symbol)
                current_prices[symbol] = ticker.close
            except Exception as e:
                logger.warning(f"获取{symbol}价格失败: {e}")
        
        # 创建投资组合快照
        portfolio = portfolio_manager.create_portfolio_snapshot(balances, current_prices, private_fetcher)
        
        # 保存到数据库
        db_manager.save_daily_snapshot(
            date=today,
            total_value=portfolio.total_value,
            total_cost=portfolio.total_cost,
            pnl=portfolio.total_pnl,
            pnl_rate=portfolio.total_pnl_rate,
            portfolio_data={
                'positions': [
                    {
                        'symbol': pos.symbol,
                        'currency': pos.currency,
                        'amount': pos.amount,
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
        )
        
        logger.info(f"已保存{today}的投资组合快照: ${portfolio.total_value:.2f}")
        
        # 生成资金变化图表
        generate_portfolio_chart()
        
    except Exception as e:
        logger.error(f"保存每日快照失败: {e}")

def generate_portfolio_chart():
    """生成USDT资金变化图表并保存到static目录"""
    try:
        # 获取最近30天的快照数据
        snapshots = db_manager.get_daily_snapshots(days=30)
        
        if not snapshots or len(snapshots) < 2:
            logger.warning("历史数据不足，无法生成图表")
            return
        
        # 准备数据
        dates = []
        total_values = []
        
        # 按日期排序（从旧到新）
        snapshots_sorted = sorted(snapshots, key=lambda x: x['date'])
        
        for snapshot in snapshots_sorted:
            try:
                date_obj = datetime.strptime(snapshot['date'], '%Y-%m-%d')
                dates.append(date_obj)
                total_values.append(float(snapshot['total_value']))
            except Exception as e:
                logger.warning(f"处理快照数据失败: {e}")
                continue
        
        if len(dates) < 2:
            logger.warning("有效数据不足，无法生成图表")
            return
        
        # 设置字体
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建单个图表
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        fig.suptitle('USDT Portfolio Value Trend', fontsize=18, fontweight='bold')
        
        # 绘制USDT总价值变化
        ax.plot(dates, total_values, 'b-', linewidth=3, label='Total Value (USDT)', marker='o', markersize=6)
        ax.fill_between(dates, total_values, alpha=0.3, color='blue')
        ax.set_ylabel('Amount (USDT)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=14, fontweight='bold')
        ax.set_title('Portfolio Total Value Change', fontsize=16)
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # 格式化日期显示
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//8)))
        
        # 添加数值标签
        for i, (date, value) in enumerate(zip(dates, total_values)):
            if i % max(1, len(dates)//5) == 0 or i == len(dates)-1:
                ax.annotate(f'${value:.0f}', 
                           (date, value), 
                           textcoords="offset points", 
                           xytext=(0,15), 
                           ha='center',
                           fontsize=10,
                           fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # 添加统计信息
        latest_value = total_values[-1]
        initial_value = total_values[0]
        value_change = latest_value - initial_value
        change_percent = (value_change / initial_value * 100) if initial_value > 0 else 0
        
        # 统计信息文本（英文）
        stats_text = f'Current Value: ${latest_value:.2f} USDT\n'
        stats_text += f'Initial Value: ${initial_value:.2f} USDT\n'
        stats_text += f'Change Amount: ${value_change:.2f} USDT\n'
        stats_text += f'Change Rate: {change_percent:.2f}%'
        
        # 在图表右上角添加统计信息
        ax.text(0.5, 0.98, stats_text, 
                transform=ax.transAxes, 
                fontsize=11,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
        
        # 设置Y轴范围，添加一些边距
        y_min, y_max = min(total_values), max(total_values)
        y_range = y_max - y_min
        ax.set_ylim(y_min - y_range * 0.1, y_max + y_range * 0.1)
        
        # 调整布局
        plt.tight_layout()
        
        # 确保static目录存在
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        os.makedirs(static_dir, exist_ok=True)
        
        # 保存图表
        # chart_filename = f'portfolio_chart_{datetime.now().strftime("%Y%m%d")}.png'
        # chart_path = os.path.join(static_dir, chart_filename)
        # plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        
        # 同时保存一个固定名称的文件供前端使用
        latest_chart_path = os.path.join(static_dir, 'portfolio_latest.png')
        plt.savefig(latest_chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()  # 关闭图形以释放内存
        
        logger.info(f"USDT Portfolio Value Chart saved: portfolio_latest.png")
        
    except Exception as e:
        logger.error(f"Failed to generate USDT portfolio chart: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    # 初始化
    initialize_fetchers()
    
    # 启动应用（使用SocketIO）
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
else:
    # 当作为模块导入时也要初始化
    initialize_fetchers()
