#!/usr/bin/env python3
"""
Screen Capture Translator
メインエントリーポイント
"""
import sys
import os

# srcディレクトリをパスに追加
src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_dir)

from app import main

if __name__ == "__main__":
    main()
