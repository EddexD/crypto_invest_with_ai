"""
主程序入口
AI加密货币投资助手
"""
import logging
import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./data/logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    
    from src.web.app import app
    app.run(host='127.0.0.1', port=6998, debug=False)

if __name__ == "__main__":
    main()
