"""
pytestの設定とフィクスチャ
"""
import pytest
from pathlib import Path
import tempfile
from PIL import Image


@pytest.fixture
def temp_dir():
    """一時ディレクトリを提供するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image():
    """テスト用のサンプル画像を提供するフィクスチャ"""
    # 100x100の白い画像を作成
    img = Image.new('RGB', (100, 100), color='white')
    return img


@pytest.fixture
def sample_text():
    """テスト用のサンプルテキストを提供するフィクスチャ"""
    return "Hello, World! This is a test."
