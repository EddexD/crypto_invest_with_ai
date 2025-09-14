"""
Web应用程序主文件
使用Flask构建Web界面
"""

from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime, date, timedelta
import logging
from typing import Dict, List
from functools import wraps
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
        ax.text(0.98, 0.98, stats_text, 
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

@app.route('/api/portfolio/chart')
def get_portfolio_chart():
    """获取投资组合图表"""
    try:
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        chart_path = os.path.join(static_dir, 'portfolio_latest.png')
        
        if os.path.exists(chart_path):
            # 获取文件修改时间
            mtime = os.path.getmtime(chart_path)
            return jsonify({
                'chart_available': True,
                'chart_url': '/static/portfolio_latest.png',
                'last_updated': datetime.fromtimestamp(mtime).isoformat()
            })
        else:
            return jsonify({
                'chart_available': False,
                'message': '图表文件不存在，请先保存快照'
            })
    except Exception as e:
        logger.error(f"获取图表信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/save_snapshot', methods=['POST'])
@check_ip_whitelist
def save_portfolio_snapshot():
    """手动保存投资组合快照"""
    try:
        save_daily_portfolio_snapshot()
        return jsonify({'success': True, 'message': '快照保存成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio')
# @check_ip_whitelist
def get_portfolio():
    """获取投资组合数据"""
    try:
        if not private_fetcher:
            return jsonify({'error': '未配置API密钥'}), 400
        
        # 获取账户余额
        balances = private_fetcher.get_balances()
        
        # 获取真实持仓信息（包含正确的平均成本价）
        positions = private_fetcher.get_positions()
        
        # 计算总价值和盈亏
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
        
        total_pnl = total_value - total_cost - usdt_balance  # USDT不计入成本
        total_pnl_rate = (total_pnl / total_cost) if total_cost > 0 else 0
        daily_return = (total_pnl / total_value) if total_value > 0 else 0
        
        # 计算总收益率（简化版本，基于当前数据）
        if total_cost > 0:
            total_return_rate = ((total_value - usdt_balance - total_cost) / total_cost) * 100
        else:
            total_return_rate = 0.0
        
        # 计算资产配置
        asset_allocation = {}
        if total_value > 0:
            for balance in balances:
                if balance.currency == 'USDT':
                    asset_allocation[balance.currency] = (balance.total / total_value) * 100
            for position in positions:
                asset_allocation[position.currency] = (position.market_value / total_value) * 100
        
        # 计算表现指标
        # try:
        #     performance = portfolio_manager.calculate_performance_metrics(30,total_cost)
        #     # 如果历史数据不足，使用简化的总收益率
        #     if not performance.get('total_return'):
        #         performance['total_return'] = total_return_rate / 100  # 转换为小数形式
        # except Exception as e:
        #     logger.warning(f"计算表现指标失败: {e}")
        performance = {
            'total_return': daily_return,  # 转换为小数形式
            'daily_return': daily_return,
            'volatility': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        
        return jsonify({
            'total_value': total_value,
            'total_cost': total_cost,
            'total_pnl': total_pnl,
            'total_pnl_rate': total_pnl_rate,
            'asset_allocation': asset_allocation,
            'performance': performance,
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
                } for pos in positions
            ],
            'balances': [
                {
                    'currency': bal.currency,
                    'total': bal.total,
                    'free': bal.free,
                    'used': bal.used
                } for bal in balances
            ]
        })
    
    except Exception as e:
        logger.error(f"获取投资组合数据失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/history')
# @check_ip_whitelist
def get_portfolio_history():
    """获取投资组合历史数据用于图表显示"""
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
                    return jsonify({'error': '无法获取投资组合数据'}), 500
            else:
                return jsonify({'error': '未配置API密钥，无法获取历史数据'}), 400
        
        # 转换为图表需要的格式
        history = []
        for snapshot in reversed(snapshots):  # 从旧到新排序
            history.append({
                'date': snapshot['date'],
                'total_value': snapshot['total_value'],
                'return_rate': snapshot['pnl_rate']  # 使用收益率而不是未实现盈亏
            })
        
        return jsonify({
            'history': history,
            'period': '30d',
            'data_source': 'database'
        })
        
    except Exception as e:
        logger.error(f"获取投资组合历史失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/basic-analysis')
# @check_ip_whitelist
def get_basic_portfolio_analysis():
    """获取基础投资组合分析（不依赖AI，立即返回）"""
    try:
        if not private_fetcher:
            return jsonify({'error': '未配置API密钥，无法获取投资组合数据'}), 400
        
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
                    'price': ticker.close,
                    'change': ticker.change,
                    'percentage': ticker.percentage,
                    'volume': ticker.volume
                }
            except Exception as e:
                logger.warning(f"获取{symbol}市场数据失败: {e}")
        
        # 生成基础分析
        basic_analysis = portfolio_manager.generate_basic_analysis(portfolio, market_data)
        
        return jsonify({
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommendations')
def get_recommendations():
    """获取AI投资建议（保持向后兼容）"""
    try:
        if not market_fetcher:
            return jsonify({'error': '市场数据获取器未初始化'}), 400
        
        # 获取投资组合数据
        portfolio_data = {}
        if private_fetcher:
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
                    'positions': [
                        {
                            'symbol': pos.symbol,
                            'amount': pos.amount,
                            'market_value': pos.market_value,
                            'unrealized_pnl': pos.unrealized_pnl,
                            'unrealized_pnl_rate': pos.unrealized_pnl_rate
                        } for pos in portfolio.positions
                    ]
                }
            except Exception as e:
                logger.warning(f"获取投资组合数据失败: {e}")
        
        symbols = config_manager.get_symbols()
        recommendations = ai_engine.generate_recommendations(portfolio_data, symbols)
        
        # 转换为可序列化的格式
        recommendations_data = []
        for rec in recommendations:
            rec_data = {
                'symbol': rec.symbol,
                'action': rec.action,
                'confidence': rec.confidence,
                'price_target': rec.price_target,
                'stop_loss': rec.stop_loss,
                'reasoning': rec.reasoning,
                'timestamp': rec.timestamp.isoformat()
            }
            recommendations_data.append(rec_data)
            
            # 保存建议到数据库
            try:
                current_price = market_fetcher.get_ticker(rec.symbol).close if market_fetcher else rec.price_target
                db_manager.save_ai_recommendation(
                    symbol=rec.symbol,
                    action=rec.action,
                    confidence=rec.confidence,
                    price=current_price or 0,
                    reasoning=rec.reasoning
                )
            except Exception as e:
                logger.warning(f"保存{rec.symbol}建议失败: {e}")
        
        return jsonify({'recommendations': recommendations_data})
    
    except Exception as e:
        logger.error(f"获取AI建议失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/smart-analysis')
# @check_ip_whitelist
def get_smart_analysis():
    """获取智能分析报告（异步启动）"""
    try:
        if not market_fetcher:
            return jsonify({'error': '市场数据获取器未初始化'}), 400
        
        # 检查是否强制刷新
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        client_ip = request.environ.get('HTTP_CF_CONNECTING_IP', request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr))
        
        # 处理可能的多个IP情况（负载均衡器）
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        if client_ip not in ALLOWED_IPS:
            force_refresh = False  # 非白名单IP不能强制刷新
        
        # 获取投资组合数据
        portfolio_data = {}
        if private_fetcher:
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
        
        return jsonify({
            'task_id': task_id,
            'status': 'started',
            'message': '智能分析任务已启动，请使用task_id查询结果'
        })
        
    except Exception as e:
        logger.error(f"启动智能分析任务失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis-status/<task_id>')
def get_analysis_status(task_id):
    """获取分析任务状态"""
    try:
        status_info = ai_engine.get_analysis_status(task_id)
        
        if not status_info:
            return jsonify({'error': '任务不存在'}), 404
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"获取分析状态失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/smart-analysis-sync')
# @check_ip_whitelist
def get_smart_analysis_sync():
    """获取智能分析报告（同步版本，保留兼容性）"""
    try:
        if not market_fetcher:
            return jsonify({'error': '市场数据获取器未初始化'}), 400
        
        # 获取投资组合数据
        portfolio_data = {}
        if private_fetcher:
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
        
        # 生成智能分析（同步）
        smart_result = ai_engine.generate_comprehensive_analysis(portfolio_data, symbols)
        
        # 转换为可序列化的字典
        result_dict = {
            'market_analysis': smart_result.market_analysis,
            'portfolio_review': smart_result.portfolio_review,
            'trading_signals': smart_result.trading_signals,
            'risk_assessment': smart_result.risk_assessment,
            'ai_confidence': smart_result.ai_confidence,
            'analysis_timestamp': smart_result.analysis_timestamp.isoformat(),
            'individual_recommendations': []
        }
        
        # # 添加个别建议
        # for rec in smart_result.individual_recommendations:
        #     rec_dict = {
        #         'symbol': rec.symbol,
        #         'action': rec.action,
        #         'confidence': rec.confidence,
        #         'price_target': rec.price_target,
        #         'stop_loss': rec.stop_loss,
        #         'reasoning': rec.reasoning,
        #         'timestamp': rec.timestamp.isoformat()
        #     }
        #     result_dict['individual_recommendations'].append(rec_dict)
        
        return jsonify(result_dict)
        
        return jsonify({
            'success': True,
            'data': result_dict
        })
        
    except Exception as e:
        logger.error(f"获取智能分析失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'market_analysis': '暂时无法获取智能分析',
                'portfolio_review': '请稍后重试',
                'trading_signals': '建议保持当前策略',
                'risk_assessment': '注意市场风险',
                'ai_confidence': 0.3,
                'analysis_timestamp': datetime.now().isoformat(),
                'individual_recommendations': []
            }
        }), 500

@app.route('/api/market_data')
# @check_ip_whitelist
def get_market_data():
    """获取市场数据"""
    try:
        if not market_fetcher:
            return jsonify({'error': '市场数据获取器未初始化'}), 400
            
        symbols = config_manager.get_symbols()
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = market_fetcher.get_ticker(symbol)
                market_data[symbol] = {
                    'price': ticker.close,
                    'change': ticker.change,
                    'percentage': ticker.percentage,
                    'volume': ticker.volume,
                    'high': ticker.high,
                    'low': ticker.low
                }
            except Exception as e:
                logger.warning(f"获取{symbol}市场数据失败: {e}")
                continue
        
        return jsonify({'market_data': market_data})
    
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
# @check_ip_whitelist
def get_orders():
    """获取订单信息"""
    try:
        if not private_fetcher:
            return jsonify({'error': '未配置API密钥'}), 400
        
        # 获取未完成订单
        try:
            open_orders = private_fetcher.get_open_orders()
        except Exception as e:
            logger.warning(f"获取未完成订单失败: {e}")
            open_orders = []
        
        # 获取历史订单
        try:
            order_history = private_fetcher.get_order_history(limit=10)
        except Exception as e:
            logger.warning(f"获取历史订单失败: {e}")
            order_history = []
            
            # 如果获取历史订单失败，尝试从交易记录构建
            try:
                trades = private_fetcher.get_trades(limit=50)
                # 从交易记录中提取订单信息
                order_dict = {}
                for trade in trades:
                    order_id = trade.order_id
                    if order_id not in order_dict:
                        order_dict[order_id] = {
                            'id': order_id,
                            'symbol': trade.symbol,
                            'type': 'market',
                            'side': trade.side.value if hasattr(trade.side, 'value') else str(trade.side),
                            'amount': trade.amount,
                            'price': trade.price,
                            'filled': trade.amount,
                            'status': 'closed',
                            'datetime': trade.datetime_str
                        }
                    else:
                        order_dict[order_id]['amount'] += trade.amount
                        order_dict[order_id]['filled'] += trade.amount
                
                order_history = list(order_dict.values())
            except Exception as e2:
                logger.error(f"从交易记录构建订单历史也失败: {e2}")
                order_history = []
        order_history = sorted(order_history, key=lambda x: x['datetime'] if isinstance(x, dict) else x.datetime_str, reverse=True)
        return jsonify({
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
            ],
            'order_history': [
                {
                    'id': order.id if hasattr(order, 'id') else order.get('id', ''),
                    'symbol': order.symbol if hasattr(order, 'symbol') else order.get('symbol', ''),
                    'type': order.type.value if hasattr(order, 'type') and hasattr(order.type, 'value') else (order.get('type', '') if isinstance(order, dict) else str(getattr(order, 'type', ''))),
                    'side': order.side.value if hasattr(order, 'side') and hasattr(order.side, 'value') else (order.get('side', '') if isinstance(order, dict) else str(getattr(order, 'side', ''))),
                    'amount': order.amount if hasattr(order, 'amount') else order.get('amount', 0),
                    'price': order.price if hasattr(order, 'price') else order.get('price', 0),
                    'filled': order.filled if hasattr(order, 'filled') else order.get('filled', 0),
                    'status': order.status.value if hasattr(order, 'status') and hasattr(order.status, 'value') else (order.get('status', '') if isinstance(order, dict) else str(getattr(order, 'status', ''))),
                    'avg_price': order.avg_price if hasattr(order, 'avg_price') else order.get('avg_price', 0),
                    'datetime': order.datetime_str if hasattr(order, 'datetime_str') else order.get('datetime', '')
                } for order in order_history
            ]
        })
    
    except Exception as e:
        logger.error(f"获取订单信息失败: {e}")
        return jsonify({
            'error': str(e),
            'open_orders': [],
            'order_history': []
        }), 500

@app.route('/api/trades')
# @check_ip_whitelist
def get_trades():
    """获取交易记录"""
    try:
        if not private_fetcher:
            return jsonify({'error': '未配置API密钥'}), 400
        
        trades = private_fetcher.get_trades(limit=100)
        
        return jsonify({
            'trades': [
                {
                    'id': trade.id,
                    'symbol': trade.symbol,
                    'side': trade.side.value if hasattr(trade.side, 'value') else str(trade.side),
                    'amount': trade.amount,
                    'price': trade.price,
                    'cost': trade.cost,
                    'fee': trade.fee,
                    'datetime': trade.datetime_str
                } for trade in trades
            ]
        })
    
    except Exception as e:
        logger.error(f"获取交易记录失败: {e}")
        return jsonify({
            'error': str(e),
            'trades': []
        }), 500



if __name__ == '__main__':
    # 初始化
    initialize_fetchers()
    
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=True)
else:
    # 当作为模块导入时也要初始化
    initialize_fetchers()
