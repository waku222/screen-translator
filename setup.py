from setuptools import setup

APP = ['src/main.py']

# Contents/Resources/ に置かれる。
# translate-helper は Apple のオンデバイス翻訳を呼ぶ Swift 製の補助実行ファイル、
# config.yaml は初回起動時にユーザー領域へ複製される設定のひな形。
DATA_FILES = [
    'helper/translate-helper',
    'config.yaml',
]

OPTIONS = {
    'argv_emulation': False,
    # objc / AppKit は utils/appkit_patch.py（Qt のクラッシュ回避）で使う
    'packages': ['PyQt6', 'mss', 'PIL', 'yaml', 'pynput', 'pyperclip', 'objc', 'Vision', 'AppKit', 'Foundation'],
    'includes': ['sip', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    'plist': {
        'CFBundleName': 'ScreenTranslator',
        'CFBundleDisplayName': 'Screen Translator',
        'CFBundleIdentifier': 'com.user.screentranslator',
        'CFBundleVersion': '1.1.0',
        'CFBundleShortVersionString': '1.1.0',
        'LSUIElement': True,
        'LSMinimumSystemVersion': '26.0',  # Translation.framework の installedSource 初期化子が必要
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
