"""
WebSocket配置文件
"""

# WebSocket配置
WEBSOCKET_CONFIG = {
    # 数据广播间隔（秒）
    'broadcast_interval': 30,
    
    # 连接超时时间（秒）  
    'connection_timeout': 60,
    
    # 最大连接数
    'max_connections': 100,
    
    # 启用CORS
    'cors_allowed_origins': "*",
    
    # 异步模式
    'async_mode': 'threading',
    
    # 启用日志
    'logger': True,
    
    # 启用WebSocket压缩
    'compression': True
}

# 实时数据配置
REALTIME_DATA_CONFIG = {
    # 启用的数据类型
    'enabled_data_types': [
        'portfolio',
        'market',
        'orders', 
        'trades'
    ],
    
    # 数据更新频率（秒）
    'update_frequencies': {
        'portfolio': 30,  # 投资组合数据每30秒更新
        'market': 15,     # 市场数据每15秒更新
        'orders': 20,     # 订单数据每20秒更新
        'trades': 25      # 交易数据每25秒更新
    },
    
    # 数据缓存时间（秒）
    'cache_duration': 10
}
