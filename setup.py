from setuptools import setup

APP = ['src/main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt6', 'mss', 'PIL', 'ocrmac', 'deep_translator', 'pynput', 'pyperclip'],
    'includes': ['sip', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    'plist': {
        'CFBundleName': 'ScreenTranslator',
        'CFBundleDisplayName': 'Screen Translator',
        'CFBundleIdentifier': 'com.user.screentranslator',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
