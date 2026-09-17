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
from translator import BaseTranslator, TranslationError, create_translator
from hotkey_listener import HotkeyListener
from config import get_config
from utils.appkit_patch import apply_clickcount_guard
from utils.logger import setup_logger, get_logger


class TranslationWorker(QObject):
    """バックグラウンドで翻訳処理を行うワーカー"""
    
    finished = pyqtSignal(str, str)  # original, translated
    error = pyqtSignal(str, str)     # message, original（読み取れていれば原文も返す）
    
    def __init__(self, capture: ScreenCapture, ocr: OCREngine, translator: BaseTranslator,
                 source_lang: str = 'en', target_lang: str = 'ja'):
        super().__init__()
        self.capture = capture
        self.ocr = ocr
        self.translator = translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.region = None
    
    def set_region(self, x: int, y: int, width: int, height: int):
        """処理する範囲を設定"""
        self.region = (x, y, width, height)
    
    def process(self):
        """キャプチャ→OCR→翻訳を実行"""
        logger = get_logger()
        original_text = ""
        try:
            if not self.region:
                self.error.emit("範囲が設定されていません", "")
                return
            
            x, y, width, height = self.region
            logger.info(f"Processing region: x={x} y={y} w={width} h={height}")
            
            # 画面キャプチャ
            # App化により権限があるため、mssを使用（座標計算が正確）
            image = self.capture.capture_region(x, y, width, height)
            
            # OCR
            original_text = self.ocr.extract_text(image)
            
            if not original_text.strip():
                self.error.emit("テキストが検出されませんでした", "")
                return
            
            logger.info(f"OCR done: {len(original_text)} chars")
            
            # 翻訳
            translated_text = self.translator.translate(
                original_text, self.source_lang, self.target_lang
            )
            
            logger.info(f"Translation done: {len(translated_text)} chars")
            self.finished.emit(original_text, translated_text)
            
        except TranslationError as e:
            # 翻訳だけが失敗した場合は、読み取れた原文を添えて返す
            logger.error(f"Translation failed: {e}")
            self.error.emit(f"翻訳に失敗しました: {e}", original_text)
        except Exception as e:
            logger.exception("Unexpected error during processing")
            self.error.emit(f"エラーが発生しました: {e}", original_text)


class MainApp(QObject):
    """メインアプリケーションクラス"""
    
    # ホットキーからの呼び出し用シグナル（スレッドセーフ）
    hotkey_triggered = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.app = QApplication.instance() or QApplication(sys.argv)
        
        # 設定とロギング
        self.config = get_config()
        self.logger = setup_logger(
            log_file=self.config.log_file,
            log_level=self.config.log_level,
            max_bytes=self.config.log_max_bytes,
            backup_count=self.config.log_backup_count,
        )
        self.logger.info(f"Starting Screen Translator (config: {self.config.config_path})")
        
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
        # メニューを開くと Qt が [[NSApp currentEvent] clickCount] を呼ぶ。
        # macOS 26 以降ではこれが例外になり得るため、起動時に
        # utils.appkit_patch でガードを入れている（入れ忘れると落ちる）。
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
                self.translator = create_translator(
                    self.config.translation_engine,
                    timeout=self.config.translation_timeout,
                )
                self.logger.info(f"Translator ready: {self.translator.get_name()}")
                self._warn_if_language_missing()
            except (RuntimeError, TranslationError) as e:
                self.logger.error(f"Failed to initialize translator: {e}")
                QMessageBox.critical(None, "エラー", f"翻訳機能の初期化に失敗しました:\n{str(e)}")
                return False
        
        return True
    
    def _warn_if_language_missing(self):
        """翻訳言語がダウンロードされていない場合に案内を出す"""
        check = getattr(self.translator, 'check_availability', None)
        if check is None:
            return
        try:
            status = check(self.config.source_lang, self.config.target_lang)
        except TranslationError as e:
            self.logger.warning(f"Language availability check failed: {e}")
            return
        
        if status == 'installed':
            return
        
        self.logger.warning(f"Language pack status: {status}")
        pair = f"{self.config.source_lang} → {self.config.target_lang}"
        if status == 'supported':
            message = (f"翻訳言語（{pair}）がダウンロードされていません。\n"
                       "システム設定 › 一般 › 言語と地域 › 翻訳言語 から追加してください。")
        else:
            message = f"この言語の組み合わせ（{pair}）には対応していません。"
        QMessageBox.warning(None, "翻訳言語の確認", message)
    
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
        # 処理中であることを先に見せる（オンデバイス翻訳は長文だと十数秒かかる）
        self._ensure_result_window().show_progress()
        
        # ワーカースレッドで処理
        self.worker_thread = QThread()
        self.worker = TranslationWorker(
            self.capture, self.ocr, self.translator,
            self.config.source_lang, self.config.target_lang,
        )
        self.worker.set_region(x, y, width, height)
        
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.process)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        
        self.worker_thread.start()
    
    def _ensure_result_window(self) -> ResultWindow:
        """結果ウィンドウを取得する（未生成なら作る）"""
        if self.result_window is None:
            self.result_window = ResultWindow()
        return self.result_window
    
    def on_translation_finished(self, original: str, translated: str):
        """翻訳完了時"""
        self._ensure_result_window().show_result(original, translated)
    
    def on_translation_error(self, error_message: str, original: str = ""):
        """
        翻訳エラー時
        
        トレイ通知は3秒で消えて見逃されるため、結果ウィンドウにも理由を残す。
        """
        self.logger.error(error_message)
        self._ensure_result_window().show_error(error_message, original)
        self.tray_icon.showMessage(
            "Screen Translator",
            error_message,
            QSystemTrayIcon.MessageIcon.Warning,
            3000
        )
    
    def on_selection_cancelled(self):
        """範囲選択キャンセル時"""
        pass  # 何もしない（この時点では結果ウィンドウは出していない）
    
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
        
        self.logger.info("Screen Translator is running")
        print("Screen Translator is running...")
        print("Right-click the tray icon or press Cmd+Shift+T to capture")
        
        return self.app.exec()


def main():
    """エントリーポイント"""
    # QApplication を作る前に AppKit のガードを入れる
    patched, detail = apply_clickcount_guard()
    
    app = MainApp()
    if patched:
        app.logger.info(f"AppKit patch: {detail}")
    else:
        # ここが失敗すると、キャプチャ後にトレイをクリックした時点で落ちる
        app.logger.error(f"AppKit patch failed: {detail}")
    
    sys.exit(app.run())


if __name__ == "__main__":
    main()
