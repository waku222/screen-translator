"""
設定管理モジュール
YAMLファイルから設定を読み込み、アプリケーション全体で使用する
"""
import os
import sys
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path

# 設定ファイルの標準の置き場所。
# .app の中に置くと再ビルドのたびに消えるため、バンドル外のこの場所を正とする。
USER_CONFIG_PATH = Path.home() / 'Library' / 'Application Support' / 'ScreenTranslator' / 'config.yaml'


class Config:
    """アプリケーション設定を管理するクラス"""
    
    # デフォルト設定
    DEFAULT_CONFIG = {
        'hotkey': {
            # Cmd+Shift+T は Chrome の「閉じたタブを再度開く」などと衝突する
            'modifiers': ['ctrl', 'alt'],
            'key': 't'
        },
        'translation': {
            'engine': 'apple',       # 翻訳エンジン（現在は 'apple' のみ）
            'source_lang': 'en',
            'target_lang': 'ja',
            'timeout': 45            # 翻訳1回を待つ秒数
        },
        'ui': {
            'theme': 'dark',
            'window_width': 600,
            'window_height': 500
        },
        'debug': {
            # 画面の内容がディスクに残るため既定では無効
            'save_failed_capture': False
        },
        'logging': {
            'level': 'INFO',
            'file': '~/Library/Logs/ScreenTranslator.log',
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
            config_path = USER_CONFIG_PATH
            # 初回起動時は同梱のデフォルト設定をユーザー領域へ複製する
            if not Path(config_path).exists():
                self._seed_user_config(Path(config_path))
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()
    
    @staticmethod
    def _seed_user_config(destination: Path):
        """同梱の config.yaml をユーザー領域にコピーする（無ければ何もしない）"""
        candidates = []
        if getattr(sys, 'frozen', False):
            # py2app バンドル: Contents/Resources/config.yaml
            candidates.append(Path(sys.executable).parent.parent / 'Resources' / 'config.yaml')
        candidates.append(Path(__file__).parent.parent / 'config.yaml')
        
        for source in candidates:
            if source.is_file():
                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
                except OSError as e:
                    print(f"Warning: Failed to seed config at {destination}: {e}")
                return
    
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
    
    @property
    def translation_engine(self) -> str:
        """翻訳エンジン名"""
        return self.config['translation'].get('engine', 'apple')
    
    @property
    def translation_timeout(self) -> int:
        """翻訳のタイムアウト秒数"""
        return int(self.config['translation'].get('timeout', 45))
    
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
    
    # デバッグ設定
    @property
    def save_failed_capture(self) -> bool:
        """OCR が空だったときに取り込み画像を保存するか

        画面の内容がそのままディスクに残るため、既定は False。
        """
        return bool(self.config.get('debug', {}).get('save_failed_capture', False))
    
    # ロギング設定
    @property
    def log_level(self) -> str:
        """ログレベル"""
        return self.config['logging']['level']
    
    @property
    def log_file(self) -> str:
        """ログファイルパス（~ は展開して返す）"""
        return str(Path(self.config['logging']['file']).expanduser())
    
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
