import requests
import json
import zlib
import base64
import time
from datetime import datetime
import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import gzip
import shutil
from typing import Optional, List, Dict

class ForesightCrawler:
    def __init__(self):
        self.base_url = "https://api.foresightnews.pro/v1/event/53"
        self.page_size = 20
        self.max_workers = 5
        self.max_retries = 3
        
        # 基础目录
        self.base_dir = Path(__file__).parent
        
        # 简化目录结构
        self.data_dir = self.base_dir / "data"
        self.log_dir = self.base_dir / "log"
        
        # 创建必需的目录
        self.data_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
    def setup_logging(self):
        """配置日志系统"""
        # 确保日志目录存在
        self.log_dir.mkdir(exist_ok=True)
        
        # 生成日志文件路径
        log_file = self.log_dir / f"crawler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 配置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def retry_on_failure(self, func, *args, **kwargs):
        """带重试机制的函数执行器"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                wait_time = (attempt + 1) * 2  # 递增等待时间
                self.logger.warning(f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}, {wait_time}秒后重试")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"达到最大重试次数: {func.__name__}")
                    raise
                    
    def decrypt_data(self, encrypted_msg: str) -> Optional[Dict]:
        """解密API返回的数据"""
        try:
            # Base64解码
            try:
                decoded = base64.b64decode(encrypted_msg)
            except Exception as e:
                self.logger.error(f"Base64解码失败: {e}")
                # 尝试修复base64填充
                try:
                    padding_fixed = encrypted_msg + '=' * (-len(encrypted_msg) % 4)
                    decoded = base64.b64decode(padding_fixed)
                except Exception as e2:
                    self.logger.error(f"Base64解码失败(含填充): {e2}")
                    return None
                
            # Zlib解压尝试
            decompression_methods = [
                (zlib.decompress, {"wbits": zlib.MAX_WBITS}),
                (zlib.decompress, {"wbits": -zlib.MAX_WBITS}),
                (zlib.decompress, {"wbits": 31}),  # For gzip
                (zlib.decompress, {"wbits": 15}),  # Raw deflate
            ]
            
            for decompress_func, kwargs in decompression_methods:
                try:
                    decompressed = decompress_func(decoded, **kwargs)
                    break
                except Exception:
                    continue
            else:
                self.logger.error("解压缩失败")
                return None
            
            # JSON解析
            try:
                data = json.loads(decompressed)
                return data
            except Exception as e:
                self.logger.error(f"JSON解析失败: {e}")
                return None
            
        except Exception as e:
            self.logger.error(f"解密失败: {e}")
            return None
            
    def validate_data(self, data: Dict):
        """验证数据完整性和格式"""
        required_fields = ["id", "title", "items", "total"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"数据缺少必要字段: {field}")
                
        if not isinstance(data["items"], list):
            raise ValueError("items 字段必须是列表")
            
        for item in data["items"]:
            if "id" not in item or "published_at" not in item:
                raise ValueError("item 缺少必要字段")
                
    def fetch_page(self, page: int) -> Optional[Dict]:
        """获取单页数据"""
        params = {
            "page": page,
            "size": self.page_size,
            "sort_by": "desc"
        }
        
        def _fetch():
            self.logger.info(f"请求第{page}页数据...")
            resp = requests.get(self.base_url, params=params, timeout=10)
            
            try:
                data = resp.json()
                if data.get("code") == 1:
                    if "data" not in data or not data["data"]:
                        self.logger.error("返回数据为空")
                        return None
                        
                    return self.decrypt_data(data["data"])
                else:
                    self.logger.error(f"API错误: {data.get('code')}")
                    return None
                
            except json.JSONDecodeError as e:
                self.logger.error(f"响应解析失败: {e}")
                return None
            
        return self.retry_on_failure(_fetch)
        
    def fetch_pages_parallel(self, start_page: int, end_page: int) -> List[Dict]:
        """并行获取多个页面的数据"""
        results = []
        lock = threading.Lock()
        
        def _fetch_and_store(page):
            data = self.fetch_page(page)
            if data and data["items"]:
                with lock:
                    results.extend(data["items"])
                    self.logger.info(f"成功获取第{page}页数据")
                    
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            executor.map(_fetch_and_store, range(start_page, end_page + 1))
            
        return results
        
    def compress_old_data(self):
        """压缩历史数据文件"""
        current_month = datetime.now().strftime('%Y%m')
        for file in self.data_dir.glob("foresight_data_*.json"):
            if current_month not in file.name:
                with open(file, 'rb') as f_in:
                    with gzip.open(str(file) + '.gz', 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                file.unlink()  # 删除原文件
                self.logger.info(f"压缩历史数据: {file.name}")
                
    def get_latest_data(self) -> Optional[List[Dict]]:
        """获取最新的本地数据"""
        try:
            # 获取最新的数据文件
            data_files = list(self.data_dir.glob("foresight_data_*.json"))
            if not data_files:
                return None
                
            latest_file = max(data_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"读取本地数据失败: {e}")
            return None
            
    def save_data(self, data: List[Dict]) -> None:
        """保存数据到文件"""
        try:
            # 确保目录存在
            self.data_dir.mkdir(exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d")
            data_file = self.data_dir / f"foresight_data_{timestamp}.json"
            
            # 保存数据
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"数据保存成功: {data_file}")
            
            # 清理旧数据文件(保留最近7天)
            self.clean_old_files(7)
            
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
            raise
            
    def clean_old_files(self, keep_days: int) -> None:
        """清理旧的数据文件"""
        try:
            current_time = time.time()
            
            for file_path in self.data_dir.glob("foresight_data_*.json"):
                if file_path.is_file():
                    file_time = file_path.stat().st_mtime
                    if (current_time - file_time) > (keep_days * 24 * 3600):
                        file_path.unlink()
                        self.logger.info(f"已删除旧数据文件: {file_path.name}")
                        
        except Exception as e:
            self.logger.error(f"清理旧文件失败: {e}")
            
    def check_updates(self) -> Optional[List[Dict]]:
        """检查并获取更新的数据"""
        latest_data = self.fetch_page(1)  # 获取第一页
        
        if not latest_data:
            return None
            
        # 检查是否有更新
        latest_timestamp = latest_data["items"][0]["published_at"]
        latest_id = latest_data["items"][0]["id"]
        
        # 有更新,获取所有新数据
        all_data = self.fetch_all()
        if all_data:
            return all_data
            
        return None
        
    def run(self) -> None:
        """运行爬虫"""
        try:
            self.logger.info("开始检查更新...")
            new_data = self.check_updates()
            
            if new_data:
                self.save_data(new_data)
                self.logger.info("更新完成")
            else:
                self.logger.info("无需更新")
                
        except Exception as e:
            self.logger.error(f"程序异常退出: {str(e)}")
            raise
        
    def fetch_all(self) -> Optional[List[Dict]]:
        """获取所有数据"""
        try:
            # 获取第一页来确定总页数
            first_page = self.fetch_page(1)
            if not first_page:
                self.logger.error("获取第一页数据失败")
                return None
                
            total = first_page["total"]
            
            # 检查本地数据
            local_data = self.get_latest_data()
            if local_data:
                # 检查数据量和最新时间戳
                if (len(local_data) == total and 
                    local_data[0]["published_at"] == first_page["items"][0]["published_at"]):
                    self.logger.info("使用本地数据")
                    return local_data
            
            # 如果本地数据不完整或不是最新的,进行完整爬取
            self.logger.info(f"开始完整爬取,总数据量: {total}")
            total_pages = (total + self.page_size - 1) // self.page_size
            
            # 使用线程池获取所有页面数据
            all_items = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_page = {
                    executor.submit(self.fetch_page, page): page 
                    for page in range(1, total_pages + 1)
                }
                
                for future in as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        data = future.result()
                        if data and "items" in data:
                            self.logger.info(f"成功获取第{page}页数据")
                            all_items.extend(data["items"])
                        else:
                            self.logger.error(f"获取第{page}页数据失败")
                    except Exception as e:
                        self.logger.error(f"处理第{page}页数据时出错: {e}")
                        
            if all_items:
                # 按发布时间排序(倒序)
                all_items.sort(key=lambda x: x["published_at"], reverse=True)
                # 保存数据
                self.save_data(all_items)
                return all_items
            else:
                self.logger.error("未获取到任何数据")
                return None
                
        except Exception as e:
            self.logger.error(f"获取所有数据失败: {e}")
            return None

def main():
    try:
        crawler = ForesightCrawler()
        data = crawler.fetch_all()
        if data:
            crawler.logger.info("数据获取完成")
    except Exception as e:
        logging.error(f"程序异常退出: {e}")
        raise

if __name__ == "__main__":
    main()