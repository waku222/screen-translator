"""
メインアプリケーション
範囲選択→OCR→翻訳→結果表示のフロー全体を管理
"""
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import sys
import os
import threading
import time

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.region_selector import RegionSelector
from ui.result_window import ResultWindow
from capture.screen_capture import ScreenCapture
from ocr.ocr_engine import OCREngine, OCRError
from translator import BaseTranslator, TranslationError, create_translator
from hotkey_listener import HotkeyListener
from config import get_config
from helper_process import get_shared_helper
from utils.appkit_patch import apply_clickcount_guard
from utils.logger import setup_logger, get_logger


class TranslationWorker(QObject):
    """バックグラウンドで翻訳処理を行うワーカー"""
    
    finished = pyqtSignal(str, str)  # original, translated
    error = pyqtSignal(str, str)     # message, original（読み取れていれば原文も返す）
    captured = pyqtSignal()          # 画面の取り込みが終わった（ここまでは画面に何も出さない）
    
    def __init__(self, capture: ScreenCapture, ocr: OCREngine, translator: BaseTranslator,
                 source_lang: str = 'en', target_lang: str = 'ja',
                 save_failed_capture: bool = False):
        super().__init__()
        self.capture = capture
        self.ocr = ocr
        self.translator = translator
        self.source_lang = source_lang
        self.target_lang = target_lang
        # 画面の内容がディスクに残るため、設定で明示的に有効にしたときだけ保存する
        self.save_failed_capture = save_failed_capture
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
            
            # ここから先はアプリのウィンドウを出してよい
            self.captured.emit()
            
            # OCR
            original_text = self.ocr.extract_text(image)
            
            if not original_text.strip():
                message = "テキストが検出されませんでした"
                # 取り込んだ画像には画面の内容がそのまま写っているため、
                # debug.save_failed_capture を有効にしたときだけ残す
                if self.save_failed_capture:
                    saved = self._save_failed_capture(image)
                    if saved:
                        message += f"（取り込んだ画像: {saved}）"
                self.error.emit(message, "")
                return
            
            logger.info(f"OCR done: {len(original_text)} chars")
            
            # 翻訳
            translated_text = self.translator.translate(
                original_text, self.source_lang, self.target_lang
            )
            
            logger.info(f"Translation done: {len(translated_text)} chars")
            self.finished.emit(original_text, translated_text)
            
        except OCRError as e:
            # 文字認識そのものが失敗した場合。「テキストが無い」とは区別する
            logger.error(f"OCR failed: {e}")
            self.error.emit(f"文字の読み取りに失敗しました: {e}", "")
        except TranslationError as e:
            # 翻訳だけが失敗した場合は、読み取れた原文を添えて返す
            logger.error(f"Translation failed: {e}")
            self.error.emit(f"翻訳に失敗しました: {e}", original_text)
        except Exception as e:
            logger.exception("Unexpected error during processing")
            self.error.emit(f"エラーが発生しました: {e}", original_text)
    
    @staticmethod
    def _save_failed_capture(image) -> str:
        """OCR が空だったときの取り込み画像を保存し、そのパスを返す"""
        from pathlib import Path as _Path
        destination = _Path.home() / 'Library' / 'Logs' / 'ScreenTranslator-failed-capture.png'
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, "PNG")
            get_logger().warning(f"OCR found no text; saved capture to {destination}")
            return str(destination)
        except Exception as e:
            get_logger().warning(f"Failed to save capture image: {e}")
            return ""


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
        
        # 暖機（初回のモデル構築）が終わったか
        self.warmup_done = False
        
        # 処理中フラグ。連打で選択オーバーレイやワーカーが多重に走るのを防ぐ
        self.busy = False
        
        # OCR と翻訳の遅延生成を主スレッドと暖機スレッドで取り合わないようにする
        self._components_lock = threading.Lock()
        
        # ホットキーリスナー
        self.hotkey_listener = None
        
        # シグナル接続
        self.hotkey_triggered.connect(self.start_capture)
        
        self.setup_tray_icon()
        self.setup_hotkey()
        self.check_permissions()
        self.start_warmup()
    
    def _ocr_languages(self) -> list:
        """設定の翻訳元言語を Vision の言語コードに直す"""
        # Vision は地域付きのコードを取る
        known = {'en': 'en-US', 'ja': 'ja-JP', 'zh': 'zh-Hans', 'ko': 'ko-KR',
                 'fr': 'fr-FR', 'de': 'de-DE', 'es': 'es-ES', 'it': 'it-IT',
                 'pt': 'pt-BR', 'ru': 'ru-RU'}
        source = self.config.source_lang
        return [known.get(source, source if '-' in source else 'en-US')]
    
    # 初回のモデル構築は失敗することがあるので、暖機は数回試す
    WARMUP_ATTEMPTS = 3
    WARMUP_RETRY_WAIT = 5.0
    
    def start_warmup(self):
        """
        OCR と翻訳をバックグラウンドで暖機する
        
        .app はバンドル ID ごとに専用の Vision モデルキャッシュを持つ。
        キャッシュが無い状態の初回認識は実測で約40秒かかり、しかも1回目は
        失敗することがある（2回目以降は0.1秒程度）。アプリを再ビルドすると
        キャッシュが無効になるため、起動直後にここで踏んでおく。
        """
        thread = threading.Thread(target=self._warmup_loop, name="warmup", daemon=True)
        thread.start()
    
    def _warmup_loop(self):
        """暖機を成功するまで数回試す"""
        for attempt in range(1, self.WARMUP_ATTEMPTS + 1):
            if self._warmup():
                self.warmup_done = True
                return
            if attempt < self.WARMUP_ATTEMPTS:
                self.logger.info(f"Retrying warmup ({attempt}/{self.WARMUP_ATTEMPTS})")
                time.sleep(self.WARMUP_RETRY_WAIT)
        self.logger.error("Warmup did not succeed; first capture may be slow or fail")
    
    def _warmup(self) -> bool:
        """暖機の実処理（別スレッド。UI には触らない）。成功したら True"""
        try:
            from PIL import Image, ImageDraw
            
            started = time.perf_counter()
            with self._components_lock:
                if self.ocr is None:
                    self.ocr = OCREngine(self._ocr_languages())
            # 認識させる中身は何でもよいが、空画像だと処理が走らないので文字を描く
            image = Image.new('RGB', (320, 80), 'white')
            ImageDraw.Draw(image).text((10, 30), "warm up", fill='black')
            warm_text = self.ocr.extract_text(image)
            ocr_done = time.perf_counter()
            
            with self._components_lock:
                if self.translator is None:
                    self.translator = create_translator(
                        self.config.translation_engine,
                        timeout=self.config.translation_timeout,
                    )
            self.translator.translate("warm up", self.config.source_lang, self.config.target_lang)
            done = time.perf_counter()
            
            self.logger.info(
                f"Warmup done: OCR {ocr_done - started:.1f}s ({len(warm_text)} chars), "
                f"translation {done - ocr_done:.1f}s"
            )
            return True
        except Exception as e:
            # 暖機に失敗しても実使用時に作り直せるので、記録だけ残す
            self.logger.warning(f"Warmup failed: {e}")
            return False
    
    def setup_hotkey(self):
        """ホットキーリスナーを設定"""
        self.hotkey_listener = HotkeyListener(self._on_hotkey_pressed)
        started = self.hotkey_listener.start()
        # 入力監視の権限が無いと黙って動かないので、状態を必ず残す
        if started and self.hotkey_listener.is_alive():
            self.logger.info("Hotkey listener started (Cmd+Shift+T)")
        else:
            self.logger.error(
                "Hotkey listener did not start. "
                "システム設定 › プライバシーとセキュリティ › 入力監視 で許可が必要です"
            )
    
    def check_permissions(self):
        """
        画面収録の権限を確認する
        
        権限が無いと mss は壁紙だけを返すため、OCR の結果が空になり
        「テキストが検出されませんでした」と見分けがつかない。
        """
        try:
            import Quartz
        except ImportError:
            return
        
        if Quartz.CGPreflightScreenCaptureAccess():
            self.logger.info("Screen recording permission: granted")
            return
        
        self.logger.error("Screen recording permission: not granted")
        QMessageBox.warning(
            None,
            "画面収録の許可が必要です",
            "画面を取り込む許可がありません。\n"
            "システム設定 › プライバシーとセキュリティ › 画面収録 で\n"
            "ScreenTranslator を許可してください。\n\n"
            "許可のあとはアプリを起動し直してください。",
        )
        # 許可ダイアログを出す（未許可の初回のみ表示される）
        try:
            Quartz.CGRequestScreenCaptureAccess()
        except Exception as e:
            self.logger.warning(f"Could not request screen capture access: {e}")
    
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
        with self._components_lock:
            return self._initialize_components()
    
    def _initialize_components(self):
        """遅延初期化の実処理（ロックを保持して呼ぶこと）"""
        if self.ocr is None:
            try:
                self.ocr = OCREngine(self._ocr_languages())
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
        if self.busy:
            # 選択中・処理中に重ねて始めると、オーバーレイが取り残されたり
            # 実行中の QThread が差し替わってクラッシュする
            self.logger.info("Capture already in progress; ignoring request")
            return
        
        if not self.initialize_components():
            return
        
        self.busy = True
        
        # 前回の結果ウィンドウは常に最前面なので、出したままだと
        # その下の範囲を選んだときにウィンドウ自体を撮ってしまう
        if self.result_window is not None:
            self.result_window.hide()
        
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.selection_cancelled.connect(self.on_selection_cancelled)
        self.selector.show_and_select()
    
    def on_region_selected(self, x: int, y: int, width: int, height: int):
        """範囲選択完了時"""
        # ワーカースレッドで処理
        self.worker_thread = QThread()
        self.worker = TranslationWorker(
            self.capture, self.ocr, self.translator,
            self.config.source_lang, self.config.target_lang,
            self.config.save_failed_capture,
        )
        self.worker.set_region(x, y, width, height)
        
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.process)
        # 進捗表示はキャプチャが終わってから。先に出すと撮影対象に被る
        self.worker.captured.connect(self.on_capture_done)
        self.worker.finished.connect(self.on_translation_finished)
        self.worker.error.connect(self.on_translation_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.error.connect(self.worker_thread.quit)
        
        # オーバーレイが画面から消えるのを待ってから撮る
        QTimer.singleShot(150, self.worker_thread.start)
    
    def on_capture_done(self):
        """画面の取り込みが終わった時（ここから進捗を表示してよい）"""
        if self.warmup_done:
            self._ensure_result_window().show_progress()
        else:
            # 初回はモデルの構築待ちで1分近くかかることがある
            self._ensure_result_window().show_progress(
                "初回の準備中です（1分ほどかかることがあります）…"
            )
    
    def _ensure_result_window(self) -> ResultWindow:
        """結果ウィンドウを取得する（未生成なら作る）"""
        if self.result_window is None:
            self.result_window = ResultWindow()
        return self.result_window
    
    def on_translation_finished(self, original: str, translated: str):
        """翻訳完了時"""
        self.busy = False
        self._ensure_result_window().show_result(original, translated)
    
    def on_translation_error(self, error_message: str, original: str = ""):
        """
        翻訳エラー時
        
        トレイ通知は3秒で消えて見逃されるため、結果ウィンドウにも理由を残す。
        """
        self.busy = False
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
        self.busy = False
    
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
