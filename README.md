# 🚀 AI加密货币投资助手

![Python](https://img.shields.io/badge/python-v3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/AI-GPT--4o--Search-orange.svg)

🤖 一个基于OpenAI GPT-4o搜索预览模型的智能加密货币投资助手，提供专业的市场分析、投资建议和投资组合管理功能。

## ✨ 核心功能

### 🧠 GPT-4o Search智能分析
- **深度市场分析**: 基于OpenAI GPT-4o搜索预览模型的专业投资分析
- **实时投资建议**: 结合技术指标和最新市场信息的智能建议
- **搜索增强**: 利用搜索功能获取最新市场资讯和分析
- **风险评估**: 智能风险分析和投资组合优化建议

### 📊 投资组合管理
- **实时监控**: 24/7实时跟踪投资组合表现
- **智能计算**: 精确的成本价、盈亏计算
- **历史回溯**: 投资组合历史表现和趋势分析
- **快照管理**: 自动保存投资组合快照

### 📈 技术分析
- **多指标分析**: RSI、MACD、布林带、移动平均线
- **趋势识别**: 自动识别市场趋势和关键价位
- **信号生成**: 基于多重技术指标的交易信号

### 🎯 交易管理
- **实时订单跟踪**: 支持普通订单和算法订单（止盈止损）
- **交易历史分析**: 完整的交易记录和统计
- **自动数据同步**: 与交易所实时同步数据

### 🌐 现代化Web界面
- **响应式设计**: 完美支持桌面和移动设备
- **实时数据**: WebSocket实时数据更新
- **可视化图表**: Chart.js驱动的动态图表
- **暗色主题**: 护眼的深色界面设计

## 🏗️ 技术架构

### 核心技术栈
- **后端**: Python 3.12 + Flask
- **AI引擎**: OpenAI GPT-4o Search Preview
- **数据库**: SQLite + 智能缓存
- **前端**: HTML5 + CSS3 + JavaScript ES6
- **图表**: Chart.js
- **交易所连接**: CCXT库

### 架构特点
- **模块化设计**: 清晰的分层架构
- **异步处理**: 多线程AI分析任务
- **缓存机制**: 智能缓存减少API调用
- **安全防护**: IP白名单和API密钥加密

## 📁 项目结构

```
crypto_invest_with_ai/
├── src/                          # 核心源代码
│   ├── ai/                       # AI分析模块
│   │   ├── analysis/             
│   │   │   ├── smart_analysis_engine.py    # OpenAI GPT-4o分析引擎
│   │   │   ├── technical_analysis.py       # 技术指标分析
│   │   │   └── analysis_task_manager.py    # 任务管理器
│   │   └── recommendation/       
│   │       └── recommendation_engine.py    # 智能推荐引擎
│   ├── data/                     # 数据层
│   │   ├── fetchers/             
│   │   │   ├── market_data_fetcher.py      # 市场数据获取
│   │   │   └── private_data_fetcher.py     # 私有数据获取
│   │   ├── models/               # 数据模型定义
│   │   └── database/             # 数据库管理
│   ├── trading/                  # 交易管理
│   │   └── portfolio/            # 投资组合管理
│   ├── web/                      # Web应用
│   │   ├── app.py               # Flask应用主文件
│   │   ├── templates/           # HTML模板
│   │   └── static/              # 静态资源
│   └── utils/                    # 工具函数
├── config/                       # 配置管理
│   └── config_manager.py        # 配置管理器
│   └── secrets.json             # okx交易所密钥配置和openai密钥配置文件
│   └── config.json              # 关注交易对配置文件
├── data/                         # 数据存储
├── main.py                       # 程序入口
├── requirements.txt              # 依赖包
└── README.md                     # 项目文档
```

## 🚀 快速开始

### 环境要求
- Python 3.12+
- 支持的交易所API（推荐OKX）
- OpenAI API Key (GPT-4o模型访问权限)

### 1. 克隆项目
```bash
git clone <repository-url>
cd crypto_invest_with_ai
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置API密钥
config目录下的`secrets.json.example`重命名为`secrets.json`，然后打开编辑，将[okx的api密钥](https://www.okx.com/zh-hans/account/my-api)和[openai的密钥](https://platform.openai.com/settings/organization/api-keys)填入
```json
{
  "exchange": {
    "name": "okx",
    "api_key": "",
    "secret_key": "",
    "passphrase": "",
    "sandbox": true
  },
  "ai": {
    "openai_key": ""
  }
}
```

### 4. 配置关注币种
config目录下的`config.json`
```json
{
  "ai": {
    "model_name": "gpt-4o-search-preview", //模型配置，不建议修改
    "analysis_interval": 3600,
    "confidence_threshold": 0.7,
    "base_url": "https://api.openai.com/v1"
  },
  "symbols": [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XAUT/USDT",
    "OKB/USDT",
    "DOGE/USDT"
  ], //关注交易对，如果修改了，需要重启网站
  "data": {
    "history_days": 30,
    "update_interval": 300
  },
  "ip_whitelist": ["127.0.0.1"] //ip白名单，白名单里面的ip才能在网站上保存快照和ai分析
}
```


### 4. 启动应用
```bash
# 启动Web服务器
python main.py 
```

### 5. 访问Web界面
打开浏览器访问: `http://127.0.0.1:6998`
