# 🚀 AI加密货币投资助手

![Python](https://img.shields.io/badge/python-v3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/AI-GPT--4o--Search-orange.svg)

🤖 一个基于OpenAI GPT-4o搜索预览模型的智能加密货币投资助手，提供专业的市场分析、投资建议和投资组合管理功能。

![](https://cryptoaiinvest.top/static/portfolio_latest.png)

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
│   │       └── recommendation_engine.py    # 智能推荐引擎; 要改提示词在这里改
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
git clone https://github.com/2024baibai/crypto_invest_with_ai
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

⚠️ okx的api密钥只需要读取权限就可以！

### 4. 配置关注币种
config目录下的`config.json.example`重命名为`config.json`，然后编辑
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

## ❓ 常见问题与解决方案

### 📊 投资组合相关问题

#### Q1: 投资组合表现图表显示"暂无历史数据"？
**可能原因及解决方案：**
- ✅ **检查API配置**: 确保已正确配置OKX交易所API密钥
- ✅ **手动保存快照**: 在网页上点击"保存快照"按钮创建首个数据点
- ✅ **等待数据积累**: 图表需要至少2个时间点的数据才能显示趋势
- ✅ **检查网络连接**: 确保能够正常连接到OKX API

#### Q2: 持仓数据不准确或显示为空？
**解决步骤：**
1. 检查API权限是否包含"读取"权限
2. 确认交易所账户中确实有持仓
3. 刷新页面重新加载数据
4. 检查是否使用了正确的API环境（生产/沙盒）

### 🤖 AI分析相关问题

#### Q3: AI分析一直显示"正在分析"或没有结果？
**解决方案：**
- ✅ **检查OpenAI配置**: 确保已配置有效的OpenAI API密钥
- ✅ **验证账户余额**: 确认OpenAI账户有足够的API调用余额
- ✅ **网络连接测试**: 确保本地网络能够访问OpenAI API
- ✅ **模型权限检查**: 确认账户有GPT-4o模型的访问权限
- ✅ **重试分析**: 点击"重新分析"按钮手动触发

#### Q4: AI分析结果显示错误或不相关？
**可能原因：**
- 🔧 **数据获取问题**: 市场数据可能存在延迟或错误
- 🔧 **模型限制**: AI模型可能对某些市场情况理解有限
- 🔧 **网络问题**: 数据传输过程中可能出现丢失

### 🔧 技术配置问题

#### Q5: 启动应用时出现"模块未找到"错误？
**解决步骤：**
```bash
# 1. 确保使用正确的Python版本
python --version  # 应显示3.12+

# 2. 重新安装依赖包
pip install -r requirements.txt

# 3. 如果仍有问题，使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

#### Q6: 网页无法访问或显示500错误？
**排查方案：**
1. **检查端口占用**: 确认6998端口未被其他程序占用
2. **查看控制台日志**: 观察终端中的错误信息
3. **配置文件检查**: 验证`config.json`和`secrets.json`格式正确
4. **防火墙设置**: 确保防火墙未阻止端口访问

### 💰 交易所连接问题

#### Q7: 提示"API权限不足"或"无效的API密钥"？
**解决方案：**
- 🔑 **重新生成密钥**: 在OKX官网重新创建API密钥
- 🔑 **权限设置**: 确保API具有"读取"权限（不需要交易权限）
- 🔑 **IP白名单**: 如果设置了IP白名单，确保当前IP在列表中
- 🔑 **密钥格式**: 检查复制粘贴时是否有多余的空格或字符

#### Q8: 订单或交易数据显示不完整？
**可能原因：**
- ⏰ **时间范围限制**: API可能只返回最近的交易记录
- ⏰ **数据延迟**: 交易所数据可能存在几分钟延迟
- ⏰ **账户类型**: 确认使用的是正确的账户类型（现货/期货）

### 🛠️ 高级配置

#### Q9: 如何自定义关注的交易对？
**操作步骤：**
1. 编辑`config/config.json`文件
2. 修改`symbols`数组，添加或删除交易对
3. 重启应用使配置生效
4. 确保交易对格式正确（如："BTC/USDT"）

#### Q10: 如何调整AI分析频率？
**配置说明：**
```json
{
  "ai": {
    "analysis_interval": 3600,  // 分析间隔（秒）
    "confidence_threshold": 0.7  // 置信度阈值
  }
}
```

### 📞 获取帮助

如果以上解决方案都无法解决您的问题，请：
1. 📋 **收集日志**: 保存控制台的完整错误信息
2. 📋 **描述问题**: 详细描述问题发生的步骤和现象
3. 📋 **环境信息**: 提供操作系统、Python版本等信息
4. 📋 **创建Issue**: 在GitHub仓库中创建问题报告

## ⚠️ 重要免责声明

> **请在使用本项目前仔细阅读以下声明**

### 📈 交易范围限制
- **仅限现货交易**: 本项目专门针对加密货币**现货**交易进行分析，不提供期货、合约或杠杆交易分析
- **不支持衍生品**: 不涉及期权、永续合约等金融衍生品分析

### 🤖 AI分析性质
- **辅助决策工具**: AI分析结果仅供投资参考，不构成投资建议或保证
- **需人工判断**: 所有交易决策需要您结合AI分析结果进行独立判断和手动操作
- **非自动交易**: 本项目不执行任何自动交易操作，所有交易行为由用户自主决定

### 💼 风险提示
- **投资风险**: 加密货币投资存在极高风险，价格波动剧烈，可能导致本金全部损失
- **技术风险**: 软件可能存在技术故障、数据延迟或分析错误的风险
- **市场风险**: 加密货币市场受政策、技术、情绪等多重因素影响，存在不可预测性

### 🛡️ 责任限制
- **无财务责任**: 项目开发者不对任何投资损失、利润损失或其他经济损失承担责任
- **技术免责**: 不保证软件的准确性、可靠性、完整性或适用性
- **使用后果**: 用户使用本项目产生的一切后果由用户自行承担

### 📋 使用条件
- **年龄要求**: 使用者必须年满18岁且具备完全民事行为能力
- **风险承受**: 用户应具备相应的投资经验和风险承受能力
- **合规使用**: 用户需确保在当地法律法规允许的范围内使用本项目

### 💡 投资建议
- **理性投资**: 请根据自身财务状况理性投资，切勿盲目跟随AI建议
- **分散风险**: 建议分散投资，不要将全部资金投入单一品种
- **持续学习**: 建议持续学习投资知识，提高风险识别和管理能力

---

**通过使用本项目，您确认已充分理解并接受上述所有条款。如不同意，请立即停止使用。**