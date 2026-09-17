"""
翻訳結果表示ウィンドウ
原文と翻訳結果を表示し、クリップボードコピー機能を提供
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QApplication, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QClipboard
import sys


class ResultWindow(QWidget):
    """翻訳結果を表示するウィンドウ"""
    
    # ウィンドウを閉じた時のシグナル
    closed = pyqtSignal()
    # 再翻訳リクエストのシグナル
    retry_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_text = ""
        self.translated_text = ""
        self.setup_ui()
    
    def setup_ui(self):
        """UIを設定する"""
        self.setWindowTitle("🌐 Screen Translator")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        
        # メインレイアウト
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # スタイルシート
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            QLabel#sectionLabel {
                color: #89b4fa;
                font-weight: bold;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
            QPushButton#closeBtn {
                background-color: #45475a;
                color: #cdd6f4;
            }
            QPushButton#closeBtn:hover {
                background-color: #585b70;
            }
            QLabel#statusLabel {
                color: #f38ba8;
                font-size: 13px;
                padding: 4px 2px;
            }
        """)
        
        # 状態表示（翻訳中・エラー）。通常時は隠しておく
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        # 原文セクション
        original_label = QLabel("【原文】")
        original_label.setObjectName("sectionLabel")
        layout.addWidget(original_label)
        
        self.original_text_edit = QTextEdit()
        self.original_text_edit.setReadOnly(True)
        self.original_text_edit.setMaximumHeight(150)
        layout.addWidget(self.original_text_edit)
        
        # 区切り線
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #45475a;")
        layout.addWidget(line)
        
        # 翻訳セクション
        translated_label = QLabel("【翻訳】")
        translated_label.setObjectName("sectionLabel")
        layout.addWidget(translated_label)
        
        self.translated_text_edit = QTextEdit()
        self.translated_text_edit.setReadOnly(True)
        layout.addWidget(self.translated_text_edit, 1)  # stretch factor
        
        # ボタンレイアウト
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # コピーボタン（原文）
        copy_original_btn = QPushButton("📋 原文をコピー")
        copy_original_btn.clicked.connect(self.copy_original)
        button_layout.addWidget(copy_original_btn)
        
        # コピーボタン（翻訳）
        copy_translated_btn = QPushButton("📋 翻訳をコピー")
        copy_translated_btn.clicked.connect(self.copy_translated)
        button_layout.addWidget(copy_translated_btn)
        
        button_layout.addStretch()
        
        # 閉じるボタン
        close_btn = QPushButton("❌ 閉じる")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def show_result(self, original: str, translated: str):
        """
        翻訳結果を表示する
        
        Args:
            original: 原文テキスト
            translated: 翻訳されたテキスト
        """
        self.original_text = original
        self.translated_text = translated
        
        self.status_label.hide()
        self.original_text_edit.setText(original)
        self.translated_text_edit.setText(translated)
        
        self._present()
    
    def show_progress(self, message: str = "翻訳中…"):
        """処理中であることを表示する"""
        self.status_label.setText(f"⏳ {message}")
        self.status_label.setStyleSheet("color: #89b4fa;")
        self.status_label.show()
        self.original_text_edit.clear()
        self.translated_text_edit.clear()
        self._present()
    
    def show_error(self, message: str, original: str = ""):
        """
        エラーを表示する
        
        トレイ通知は数秒で消えて見逃しやすいため、失敗した理由はこのウィンドウに残す。
        
        Args:
            message: エラーメッセージ
            original: OCR で読み取れていた原文（あれば表示する）
        """
        self.original_text = original
        self.translated_text = ""
        
        self.status_label.setText(f"⚠️ {message}")
        self.status_label.setStyleSheet("color: #f38ba8;")
        self.status_label.show()
        self.original_text_edit.setText(original)
        self.translated_text_edit.clear()
        
        self._present()
    
    def _present(self):
        """ウィンドウを前面に出す"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def copy_original(self):
        """原文をクリップボードにコピー"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.original_text)
    
    def copy_translated(self):
        """翻訳文をクリップボードにコピー"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.translated_text)
    
    def closeEvent(self, event):
        """ウィンドウを閉じる際のイベント"""
        self.closed.emit()
        super().closeEvent(event)


if __name__ == "__main__":
    # テスト用コード
    app = QApplication(sys.argv)
    
    window = ResultWindow()
    window.show_result(
        "This is a sample text that demonstrates the translation result window. "
        "It shows both the original text and the translated text in a modern, "
        "dark-themed interface.",
        "これは翻訳結果ウィンドウを示すサンプルテキストです。"
        "モダンなダークテーマのインターフェースで、原文と翻訳文の両方を表示します。"
    )
    
    sys.exit(app.exec())
