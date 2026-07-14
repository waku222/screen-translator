"""
設定管理モジュール
YAMLファイルから設定を読み込み、アプリケーション全体で使用する
"""
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class Config:
    """アプリケーション設定を管理するクラス"""
    
    # デフォルト設定
    DEFAULT_CONFIG = {
        'hotkey': {
            'modifiers': ['cmd', 'shift'],
            'key': 't'
        },
        'translation': {
            'source_lang': 'en',
            'target_lang': 'ja'
        },
        'ui': {
            'theme': 'dark',
            'window_width': 600,
            'window_height': 500
        },
        'logging': {
            'level': 'INFO',
            'file': '/tmp/screen-translator.log',
            'max_bytes': 10485760,  # 10MB
            'backup_count': 3
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        設定を初期化する
        
        Args:
            config_path: 設定ファイルのパス（Noneの場合はデフォルトパスを使用）
        """
        if config_path is None:
            # プロジェクトルートのconfig.yamlを使用
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / 'config.yaml'
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                # デフォルト設定とマージ
                return self._merge_config(self.DEFAULT_CONFIG.copy(), user_config)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
                print("Using default configuration.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 設定ファイルが存在しない場合はデフォルトを使用
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """デフォルト設定とユーザー設定をマージする"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self):
        """現在の設定をファイルに保存する"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"Error: Failed to save config to {self.config_path}: {e}")
    
    # ホットキー設定
    @property
    def hotkey_modifiers(self) -> List[str]:
        """ホットキーの修飾キーリスト"""
        return self.config['hotkey']['modifiers']
    
    @property
    def hotkey_key(self) -> str:
        """ホットキーのキー"""
        return self.config['hotkey']['key']
    
    # 翻訳設定
    @property
    def source_lang(self) -> str:
        """翻訳元言語"""
        return self.config['translation']['source_lang']
    
    @property
    def target_lang(self) -> str:
        """翻訳先言語"""
        return self.config['translation']['target_lang']
    
    # UI設定
    @property
    def ui_theme(self) -> str:
        """UIテーマ"""
        return self.config['ui']['theme']
    
    @property
    def window_width(self) -> int:
        """ウィンドウ幅"""
        return self.config['ui']['window_width']
    
    @property
    def window_height(self) -> int:
        """ウィンドウ高さ"""
        return self.config['ui']['window_height']
    
    # ロギング設定
    @property
    def log_level(self) -> str:
        """ログレベル"""
        return self.config['logging']['level']
    
    @property
    def log_file(self) -> str:
        """ログファイルパス"""
        return self.config['logging']['file']
    
    @property
    def log_max_bytes(self) -> int:
        """ログファイルの最大サイズ"""
        return self.config['logging']['max_bytes']
    
    @property
    def log_backup_count(self) -> int:
        """ログファイルのバックアップ数"""
        return self.config['logging']['backup_count']


# グローバル設定インスタンス
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """グローバル設定インスタンスを取得する"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


if __name__ == "__main__":
    # テスト用コード
    config = Config()
    print(f"Hotkey: {'+'.join(config.hotkey_modifiers)}+{config.hotkey_key}")
    print(f"Translation: {config.source_lang} -> {config.target_lang}")
    print(f"UI Theme: {config.ui_theme}")
    print(f"Log Level: {config.log_level}")
    print(f"Log File: {config.log_file}")
