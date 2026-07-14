"""
ロギングモジュール
アプリケーション全体で使用する構造化ロギングシステム
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "screen_translator",
    log_file: Optional[str] = None,
    log_level: str = "INFO",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 3
) -> logging.Logger:
    """
    ロガーをセットアップする
    
    Args:
        name: ロガー名
        log_file: ログファイルパス（Noneの場合はコンソールのみ）
        log_level: ログレベル
        max_bytes: ログファイルの最大サイズ
        backup_count: バックアップファイル数
        
    Returns:
        logging.Logger: 設定されたロガー
    """
    logger = logging.getLogger(name)
    
    # 既存のハンドラをクリア
    logger.handlers.clear()
    
    # ログレベルを設定
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # フォーマッターを作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラを追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラを追加（指定された場合）
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to setup file handler: {e}")
    
    return logger


def get_logger(name: str = "screen_translator") -> logging.Logger:
    """
    既存のロガーを取得する
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: ロガー
    """
    return logging.getLogger(name)


if __name__ == "__main__":
    # テスト用コード
    logger = setup_logger(
        log_file="/tmp/test_logger.log",
        log_level="DEBUG"
    )
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    print(f"\nLog file created at: /tmp/test_logger.log")
