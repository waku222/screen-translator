"""
メインアプリケーション
範囲選択→OCR→翻訳→結果表示のフロー全体を管理
"""
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import sys
import os

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.region_selector import RegionSelector
from ui.result_window import ResultWindow
from capture.screen_capture import ScreenCapture
from ocr.ocr_engine import OCREngine
from translator.google_translator import GoogleTranslator, TranslationError
from hotkey_listener import HotkeyListener


class TranslationWorker(QObject):
    """バックグラウンドで翻訳処理を行うワーカー"""
    
    finished = pyqtSignal(str, str)  # original, translated
    error = pyqtSignal(str)
    
    def __init__(self, capture: ScreenCapture, ocr: OCREngine, translator: GoogleTranslator):
        super().__init__()
        self.capture = capture
        self.ocr = ocr
        self.translator = translator
        self.region = None
    
    def set_region(self, x: int, y: int, width: int, height: int):
        """処理する範囲を設定"""
        self.region = (x, y, width, height)
    
    def process(self):
        """キャプチャ→OCR→翻訳を実行"""
        try:
            if not self.region:
                self.error.emit("範囲が設定されていません")
                return
            
            x, y, width, height = self.region
            
            # 画面キャプチャ
            # App化により権限があるため、mssを使用（座標計算が正確）
            image = self.capture.capture_region(x, y, width, height)
            
            # OCR
            original_text = self.ocr.extract_text(image)
            
            if not original_text.strip():
                self.error.emit("テキストが検出されませんでした")
                return
            
            # 翻訳
            translated_text = self.translator.translate(original_text)
            
            self.finished.emit(original_text, translated_text)
            
        except Exception as e:
            self.error.emit(f"エラーが発生しました: {str(e)}")


class MainApp(QObject):
    """メインアプリケーションクラス"""
    
    # ホットキーからの呼び出し用シグナル（スレッドセーフ）
    hotkey_triggered = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # コンポーネント初期化
        self.capture = ScreenCapture()
        self.ocr = None  # 遅延初期化
        self.translator = None  # 遅延初期化
        
        # UI
        self.selector = None
        self.result_window = None
        self.tray_icon = None
        
        # ワーカースレッド
        self.worker_thread = None
        self.worker = None
        
        # ホットキーリスナー
        self.hotkey_listener = None
        
        # シグナル接続
        self.hotkey_triggered.connect(self.start_capture)
        
        self.setup_tray_icon()
        self.setup_hotkey()
    
    def setup_hotkey(self):
        """ホットキーリスナーを設定"""
        self.hotkey_listener = HotkeyListener(self._on_hotkey_pressed)
        self.hotkey_listener.start()
    
    def _on_hotkey_pressed(self):
        """ホットキーが押された時（別スレッドから呼ばれる）"""
        # メインスレッドで処理するためシグナルを発行
        self.hotkey_triggered.emit()
    
    def setup_tray_icon(self):
        """システムトレイアイコンを設定"""
        # シンプルなアイコンを生成
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setBrush(QColor(0, 150, 255))
        painter.setPen(QColor(255, 255, 255))
        painter.drawEllipse(4, 4, 24, 24)
        painter.drawText(10, 22, "翻")
        painter.end()
        
        icon = QIcon(pixmap)
        
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        
        # コンテキストメニュー
        self.menu = QMenu()
        
        translate_action = QAction("🌐 翻訳 (Cmd+Shift+T)", self.menu)
        translate_action.triggered.connect(self.start_capture)
        self.menu.addAction(translate_action)
        
        self.menu.addSeparator()
        
        quit_action = QAction("❌ 終了", self.menu)
        quit_action.triggered.connect(self.quit)
        self.menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("Screen Translator\n右クリックでメニュー")
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def on_tray_activated(self, reason):
        """トレイアイコンがクリックされた時"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.start_capture()
    
    def initialize_components(self):
        """OCRと翻訳コンポーネントを初期化（遅延初期化）"""
        if self.ocr is None:
            try:
                self.ocr = OCREngine()
            except RuntimeError as e:
                QMessageBox.critical(None, "エラー", f"OCRの初期化に失敗しました:\n{str(e)}")
                return False
        
        if self.translator is None:
            try:
                self.translator = GoogleTranslator()
            except RuntimeError as e:
                QMessageBox.critical(None, "エラー", f"翻訳機能の初期化に失敗しました:\n{str(e)}")
                return False
        
        return True
    
    def start_capture(self):
        """範囲選択を開始"""
        if not self.initialize_components():
            return
        
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.selection_cancelled.connect(self.on_selection_cancelled)
        self.selector.show_and_select()
    
    def on_region_selected(self, x: int, y: int, width: int, height: int):
        """範囲選択完了時"""
        # ワーカースレッドで処理
        self.worker_thread = QThread()
        self.worker = TranslationWorker(self.capture, self.ocr, self.translator)
        self.worker.set_region(x, y, width, height)
        
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.process)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        
        self.worker_thread.start()
    
    def on_translation_finished(self, original: str, translated: str):
        """翻訳完了時"""
        if self.result_window is None:
            self.result_window = ResultWindow()
        
        self.result_window.show_result(original, translated)
    
    def on_translation_error(self, error_message: str):
        """翻訳エラー時"""
        print(f"ERROR: {error_message}")
        self.tray_icon.showMessage(
            "Screen Translator",
            error_message,
            QSystemTrayIcon.MessageIcon.Warning,
            3000
        )
    
    def on_selection_cancelled(self):
        """範囲選択キャンセル時"""
        pass  # 何もしない
    
    def quit(self):
        """アプリケーションを終了"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        if self.tray_icon:
            self.tray_icon.hide()
        self.app.quit()
    
    def run(self):
        """アプリケーションを実行"""
        # macOSでメニューバーアプリとして動作させる
        self.app.setQuitOnLastWindowClosed(False)
        
        print("Screen Translator is running...")
        print("Right-click the tray icon or press Cmd+Shift+T to capture")
        
        return self.app.exec()


def main():
    """エントリーポイント"""
    app = MainApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
