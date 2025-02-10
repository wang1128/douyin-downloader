import logging
from pathlib import Path

def setup_logger(log_path: Path = Path("logs")):
    """配置日志系统"""
    log_path.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path / "douyin_downloader.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("douyin_downloader")

# 创建全局logger实例
logger = setup_logger() 