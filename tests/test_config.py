"""
設定管理のテスト
"""
import pytest
import tempfile
from pathlib import Path
import yaml
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import Config


def test_default_config():
    """デフォルト設定が正しく読み込まれることを確認"""
    config = Config(config_path="/nonexistent/path/config.yaml")
    
    assert config.hotkey_modifiers == ['ctrl', 'alt']
    assert config.hotkey_key == 't'
    assert config.source_lang == 'en'
    assert config.target_lang == 'ja'
    assert config.ui_theme == 'dark'
    assert config.log_level == 'INFO'


def test_failed_capture_is_not_saved_by_default():
    """取り込み画像の保存が既定で無効であることを確認

    有効にすると画面の内容がそのままディスクに残るため、
    既定値が False であることは明示的に守る。
    """
    config = Config(config_path="/nonexistent/path/config.yaml")
    assert config.save_failed_capture is False


def test_failed_capture_can_be_enabled():
    """設定で取り込み画像の保存を有効にできることを確認"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.safe_dump({'debug': {'save_failed_capture': True}}, f)
        config_path = f.name

    try:
        assert Config(config_path=config_path).save_failed_capture is True
    finally:
        os.unlink(config_path)


def test_failed_capture_defaults_false_for_old_config():
    """debug 節が無い旧い設定ファイルでも既定で無効になることを確認"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.safe_dump({'translation': {'source_lang': 'en'}}, f)
        config_path = f.name

    try:
        assert Config(config_path=config_path).save_failed_capture is False
    finally:
        os.unlink(config_path)


def test_custom_config():
    """カスタム設定が正しく読み込まれることを確認"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        custom_config = {
            'hotkey': {
                'modifiers': ['ctrl', 'alt'],
                'key': 's'
            },
            'translation': {
                'source_lang': 'ja',
                'target_lang': 'en'
            }
        }
        yaml.safe_dump(custom_config, f)
        config_path = f.name
    
    try:
        config = Config(config_path=config_path)
        
        assert config.hotkey_modifiers == ['ctrl', 'alt']
        assert config.hotkey_key == 's'
        assert config.source_lang == 'ja'
        assert config.target_lang == 'en'
        # デフォルト値も保持されている
        assert config.ui_theme == 'dark'
    finally:
        os.unlink(config_path)


def test_config_save():
    """設定の保存が正しく動作することを確認"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"
        config = Config(config_path=str(config_path))
        
        # 設定を変更
        config.config['hotkey']['key'] = 'x'
        config.save_config()
        
        # 再読み込みして確認
        config2 = Config(config_path=str(config_path))
        assert config2.hotkey_key == 'x'
