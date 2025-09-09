"""
AI分析任务管理器
处理异步AI分析任务，包括缓存、进度跟踪和超时控制
"""

import asyncio
import threading
import time
import json
import hashlib
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import logging

from src.utils.markdown_utils import markdown_to_html

# 延迟导入数据库管理器以避免循环依赖
_db_manager = None

def get_db_manager():
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        from src.data.database.db_manager import db_manager
        _db_manager = db_manager
    return _db_manager

logger = logging.getLogger(__name__)

@dataclass
class AnalysisTask:
    """分析任务"""
    task_id: str
    status: str  # 'pending', 'running', 'completed', 'failed', 'timeout'
    progress: float  # 0.0 - 1.0
    result: Optional[Any]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    cache_key: str

class AnalysisTaskManager:
    """AI分析任务管理器"""
    
    def __init__(self, max_workers: int = 2, cache_expire_hours: int = 1):
        """
        初始化任务管理器
        
        Args:
            max_workers: 最大并发任务数
            cache_expire_hours: 缓存过期时间（小时）
        """
        self.max_workers = max_workers
        self.cache_expire_hours = cache_expire_hours
        
        # 任务存储
        self.tasks: Dict[str, AnalysisTask] = {}
        self.cache: Dict[str, Dict] = {}
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 锁
        self.lock = threading.Lock()
        
        logger.info(f"AI分析任务管理器已初始化，最大并发数: {max_workers}")
    
    def generate_cache_key(self, portfolio_data: Dict, symbols: list) -> str:
        """生成缓存键"""
        # 创建包含主要数据的哈希
        cache_data = {
            'symbols': sorted(symbols),
            'portfolio_balances': portfolio_data.get('balances', {}),
            'total_value': portfolio_data.get('total_value', 0),
            'timestamp_hour': datetime.now().strftime('%Y%m%d%H')  # 按小时缓存
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """获取缓存结果"""
        with self.lock:
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                
                # 检查是否过期
                cached_time = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - cached_time < timedelta(hours=self.cache_expire_hours):
                    logger.info(f"使用缓存的分析结果: {cache_key[:8]}...")
                    return cached_data['result']
                else:
                    # 清除过期缓存
                    del self.cache[cache_key]
                    logger.info(f"缓存已过期: {cache_key[:8]}...")
            
            return None
    
    def set_cache(self, cache_key: str, result: Any) -> None:
        """设置缓存"""
        with self.lock:
            self.cache[cache_key] = {
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"已缓存分析结果: {cache_key[:8]}...")
    
    def start_analysis_task(self, 
                          portfolio_data: Dict, 
                          symbols: list, 
                          analysis_func: Callable,
                          force_refresh: bool = False) -> str:
        """
        启动分析任务
        
        Args:
            portfolio_data: 投资组合数据
            symbols: 交易对列表
            analysis_func: 分析函数
            force_refresh: 是否强制刷新（忽略缓存）
            
        Returns:
            str: 任务ID
        """
        # 检查是否有正在进行的任务
        with self.lock:
            for existing_task in self.tasks.values():
                if existing_task.status in ['pending', 'running']:
                    logger.info(f"检测到正在进行的任务: {existing_task.task_id}")
                    return existing_task.task_id
        
        # 生成缓存键和任务ID
        cache_key = self.generate_cache_key(portfolio_data, symbols)
        task_id = f"analysis_{int(time.time())}_{cache_key[:8]}"
        
        # 检查数据库缓存（除非强制刷新）
        if not force_refresh:
            db_manager = get_db_manager()
            
            # 首先检查数据库中的结果
            db_result = db_manager.get_ai_analysis_result(symbols, max_age_hours=24)
            if db_result is not None:
                # 处理数据库结果中的Markdown内容
                processed_result = self._process_markdown_in_result(db_result)
                
                # 创建已完成的任务
                task = AnalysisTask(
                    task_id=task_id,
                    status='completed',
                    progress=1.0,
                    result=processed_result,
                    error=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    cache_key=cache_key
                )
                
                with self.lock:
                    self.tasks[task_id] = task
                
                logger.info(f"返回数据库缓存结果，任务ID: {task_id}")
                return task_id
            
            # 然后检查内存缓存
            cached_result = self.get_cached_result(cache_key)
            if cached_result is not None:
                # 处理内存缓存结果中的Markdown内容
                processed_cached_result = self._process_markdown_in_result(cached_result)
                
                # 创建已完成的任务
                task = AnalysisTask(
                    task_id=task_id,
                    status='completed',
                    progress=1.0,
                    result=processed_cached_result,
                    error=None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    cache_key=cache_key
                )
                
                with self.lock:
                    self.tasks[task_id] = task
                
                logger.info(f"返回内存缓存结果，任务ID: {task_id}")
                return task_id
        
        # 创建新任务
        task = AnalysisTask(
            task_id=task_id,
            status='pending',
            progress=0.0,
            result=None,
            error=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            cache_key=cache_key
        )
        
        with self.lock:
            self.tasks[task_id] = task
        
        # 提交任务到线程池
        future = self.executor.submit(
            self._run_analysis_task, 
            task_id, 
            portfolio_data, 
            symbols, 
            analysis_func
        )
        
        logger.info(f"已启动分析任务: {task_id}")
        return task_id
    
    def _run_analysis_task(self, 
                         task_id: str, 
                         portfolio_data: Dict, 
                         symbols: list, 
                         analysis_func: Callable) -> None:
        """运行分析任务"""
        try:
            # 更新任务状态为运行中
            self._update_task_status(task_id, 'running', 0.1)
            
            logger.info(f"开始执行分析任务: {task_id}")
            
            # 使用线程安全的超时机制
            import concurrent.futures
            
            # 更新进度
            self._update_task_status(task_id, 'running', 0.3)
            
            # 创建超时执行器
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as timeout_executor:
                future = timeout_executor.submit(analysis_func, portfolio_data, symbols)
                
                # 启动进度监控线程
                progress_thread = threading.Thread(
                    target=self._monitor_progress, 
                    args=(task_id, future),
                    daemon=True
                )
                progress_thread.start()
                
                try:
                    # 设置180秒超时（3分钟，多线程分析应该更快）
                    result = future.result(timeout=180)
                    
                    # 更新进度
                    self._update_task_status(task_id, 'running', 0.9)
                    
                    # 转换结果为可序列化格式
                    serializable_result = self._make_serializable(result)
                    
                    # 保存到数据库
                    try:
                        db_manager = get_db_manager()
                        db_manager.save_ai_analysis_result(task_id, serializable_result, symbols, expires_hours=24)
                        logger.info(f"已保存分析结果到数据库: {task_id}")
                    except Exception as db_error:
                        logger.warning(f"保存分析结果到数据库失败: {db_error}")
                    
                    # 缓存结果到内存
                    task = self.tasks[task_id]
                    self.set_cache(task.cache_key, serializable_result)
                    
                    # 标记任务完成
                    self._update_task_status(task_id, 'completed', 1.0, serializable_result)
                    
                    logger.info(f"分析任务完成: {task_id}")
                    
                except concurrent.futures.TimeoutError:
                    # 取消超时的任务
                    future.cancel()
                    self._update_task_status(task_id, 'timeout', 0.5, None, "AI分析超时（3分钟），DeepSeek API响应慢或网络问题")
                    logger.warning(f"分析任务超时: {task_id}")
                    
        except Exception as e:
            error_msg = f"分析任务执行失败: {str(e)}"
            self._update_task_status(task_id, 'failed', 0.0, None, error_msg)
            logger.error(f"分析任务失败 {task_id}: {e}")
    
    def _monitor_progress(self, task_id: str, future) -> None:
        """监控任务进度"""
        start_time = time.time()
        progress_points = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        current_progress = 0
        
        while not future.done() and current_progress < len(progress_points):
            elapsed = time.time() - start_time
            
            # 每30秒更新一次进度
            if elapsed > (current_progress + 1) * 30:
                if current_progress < len(progress_points):
                    self._update_task_status(task_id, 'running', progress_points[current_progress])
                    current_progress += 1
                    logger.info(f"任务 {task_id} 进度更新: {progress_points[current_progress-1]:.1%}")
            
            time.sleep(5)  # 每5秒检查一次
    
    def _update_task_status(self, 
                          task_id: str, 
                          status: str, 
                          progress: float, 
                          result: Any = None, 
                          error: str = None) -> None:
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status
                task.progress = progress
                task.updated_at = datetime.now()
                
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                return {
                    'task_id': task.task_id,
                    'status': task.status,
                    'progress': task.progress,
                    'result': task.result,
                    'error': task.error,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                }
            return None
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> None:
        """清理旧任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            old_task_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.created_at < cutoff_time
            ]
            
            for task_id in old_task_ids:
                del self.tasks[task_id]
            
            # 清理旧缓存
            old_cache_keys = []
            for cache_key, cache_data in self.cache.items():
                cached_time = datetime.fromisoformat(cache_data['timestamp'])
                if cached_time < cutoff_time:
                    old_cache_keys.append(cache_key)
            
            for cache_key in old_cache_keys:
                del self.cache[cache_key]
            
            if old_task_ids or old_cache_keys:
                logger.info(f"清理了 {len(old_task_ids)} 个旧任务和 {len(old_cache_keys)} 个旧缓存")

    def _make_serializable(self, obj):
        """将对象转换为JSON可序列化格式"""
        if obj is None:
            return None
        
        # 处理datetime对象
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        # 处理dataclass对象
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for field, value in asdict(obj).items():
                result[field] = self._make_serializable(value)
            return result
        
        # 处理普通对象（有__dict__属性）
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in vars(obj).items():
                if not key.startswith('_'):  # 跳过私有属性
                    result[key] = self._make_serializable(value)
            return result
        
        # 处理列表
        if isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        
        # 处理字典
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                result[str(key)] = self._make_serializable(value)
            return result
        
        # 处理基本类型（str, int, float, bool）
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        # 其他类型尝试转换为字符串
        return str(obj)

    def _process_markdown_in_result(self, result):
        """
        处理结果中的Markdown内容，将其转换为HTML
        
        Args:
            result: 分析结果对象或字典
            
        Returns:
            处理后的结果
        """
        if not result:
            return result
        
        # 处理字典类型的结果
        if isinstance(result, dict):
            processed_result = result.copy()
            
            # 检查是否有ai_response字段需要转换
            if 'ai_response' in processed_result and isinstance(processed_result['ai_response'], str):
                # 如果ai_response包含Markdown内容（不以<开头），则转换为HTML
                ai_response = processed_result['ai_response']
                if ai_response and not ai_response.strip().startswith('<'):
                    processed_result['ai_response'] = markdown_to_html(ai_response)
                    logger.info("已将缓存结果中的ai_response从Markdown转换为HTML")
            
            return processed_result
        
        # 处理对象类型的结果
        elif hasattr(result, 'ai_response'):
            # 如果是对象，创建副本并处理ai_response
            if hasattr(result, '__dict__'):
                processed_result = type(result)(**vars(result))
                if hasattr(processed_result, 'ai_response') and isinstance(processed_result.ai_response, str):
                    ai_response = processed_result.ai_response
                    if ai_response and not ai_response.strip().startswith('<'):
                        processed_result.ai_response = markdown_to_html(ai_response)
                        logger.info("已将缓存结果中的ai_response从Markdown转换为HTML")
                return processed_result
        
        # 如果无法处理，返回原结果
        return result

# 全局任务管理器实例
analysis_task_manager = AnalysisTaskManager()
