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
    
    assert config.hotkey_modifiers == ['cmd', 'shift']
    assert config.hotkey_key == 't'
    assert config.source_lang == 'en'
    assert config.target_lang == 'ja'
    assert config.ui_theme == 'dark'
    assert config.log_level == 'INFO'


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
