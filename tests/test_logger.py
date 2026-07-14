"""
ロギングシステムのテスト
"""
import pytest
import tempfile
from pathlib import Path
import logging
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.logger import setup_logger, get_logger


def test_setup_logger_console_only():
    """コンソールのみのロガーが正しくセットアップされることを確認"""
    logger = setup_logger(name="test_console", log_level="DEBUG")
    
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1  # 少なくともコンソールハンドラがある


def test_setup_logger_with_file():
    """ファイル出力を含むロガーが正しくセットアップされることを確認"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        logger = setup_logger(
            name="test_file",
            log_file=str(log_file),
            log_level="INFO"
        )
        
        logger.info("Test message")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content


def test_get_logger():
    """既存のロガーが正しく取得できることを確認"""
    setup_logger(name="test_get")
    logger = get_logger("test_get")
    
    assert logger.name == "test_get"
