"""
範囲選択オーバーレイUI
透明なオーバーレイを使用して画面範囲を選択する
"""
from PyQt6.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QSize
from PyQt6.QtGui import QPainter, QColor, QCursor, QPen, QScreen, QPixmap
import sys
from typing import List, Optional


class ScreenOverlay(QWidget):
    """個別のスクリーン用オーバーレイウィンドウ"""
    
    # マウスイベントを親に転送するためのシグナル
    mouse_pressed = pyqtSignal(QPoint)  # グローバル座標
    mouse_moved = pyqtSignal(QPoint)    # グローバル座標
    mouse_released = pyqtSignal(QPoint) # グローバル座標
    key_pressed = pyqtSignal(int)
    
    def __init__(self, screen: QScreen):
        super().__init__()
        self.screen = screen
        self.selection_rect: Optional[QRect] = None
        self.setup_ui()
    
    def setup_ui(self):
        """UIを設定する"""
        # フレームレスウィンドウ、常に手前に表示
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # 背景を透明に設定
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # このスクリーンのジオメトリを設定
        self.setGeometry(self.screen.geometry())
        
        # マウストラッキング
        self.setMouseTracking(True)
        
        # カーソルをクロスヘアに
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def set_selection_rect(self, global_rect: Optional[QRect]):
        """選択範囲を設定（グローバル座標）"""
        if global_rect:
            # グローバル座標からローカル座標に変換
            local_top_left = self.mapFromGlobal(global_rect.topLeft())
            self.selection_rect = QRect(local_top_left, global_rect.size())
        else:
            self.selection_rect = None
        self.update()
    
    def paintEvent(self, event):
        """半透明のオーバーレイを描画し、選択範囲をクリアにする"""
        painter = QPainter(self)
        
        # 背景色（少し暗くする）
        overlay_color = QColor(0, 0, 0, 80)
        
        if self.selection_rect:
            # 選択範囲がある場合、その部分を除いて描画する必要がある
            
            # 方法: 全体を塗ってから、選択範囲を切り抜くのはQPainterでは難しい
            # なので、選択範囲の「上」「下」「左」「右」の4つの矩形を描画する
            
            r = self.rect()
            s = self.selection_rect
            
            # 交差部分を計算（念のため）
            s = r.intersected(s)
            
            if s.isEmpty():
                painter.fillRect(r, overlay_color)
            else:
                # Top rect
                if s.top() > r.top():
                    painter.fillRect(QRect(r.left(), r.top(), r.width(), s.top() - r.top()), overlay_color)
                
                # Bottom rect
                if s.bottom() < r.bottom():
                    painter.fillRect(QRect(r.left(), s.bottom() + 1, r.width(), r.bottom() - s.bottom()), overlay_color)
                
                # Left rect (middle)
                if s.left() > r.left():
                    painter.fillRect(QRect(r.left(), s.top(), s.left() - r.left(), s.height()), overlay_color)
                
                # Right rect (middle)
                if s.right() < r.right():
                    painter.fillRect(QRect(s.right() + 1, s.top(), r.right() - s.right(), s.height()), overlay_color)
                
                # 枠線を描画
                pen = QPen(QColor(0, 150, 255), 2)
                painter.setPen(pen)
                painter.drawRect(s.adjusted(0, 0, -1, -1))
                
        else:
            # 選択範囲がない場合は全体を塗りつぶす
            painter.fillRect(self.rect(), overlay_color)
    
    def mousePressEvent(self, event):
        """マウスボタン押下時"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = self.mapToGlobal(event.pos())
            self.mouse_pressed.emit(global_pos)
    
    def mouseMoveEvent(self, event):
        """マウス移動時"""
        global_pos = self.mapToGlobal(event.pos())
        self.mouse_moved.emit(global_pos)
    
    def mouseReleaseEvent(self, event):
        """マウスボタン解放時"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = self.mapToGlobal(event.pos())
            self.mouse_released.emit(global_pos)
    
    def keyPressEvent(self, event):
        """キー押下時"""
        self.key_pressed.emit(event.key())


class RegionSelector(QWidget):
    """マウスドラッグで画面範囲を選択するコントローラー"""
    
    # 範囲選択完了シグナル (x, y, width, height)
    region_selected = pyqtSignal(int, int, int, int)
    # キャンセルシグナル
    selection_cancelled = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.overlays: List[ScreenOverlay] = []
        self.start_pos: Optional[QPoint] = None
        self.current_rect: Optional[QRect] = None
    
    def _create_overlays(self):
        """各スクリーンにオーバーレイを作成"""
        # 既存のオーバーレイをクリア
        self._close_overlays()
        
        screens = QApplication.screens()
        for screen in screens:
            overlay = ScreenOverlay(screen)
            overlay.mouse_pressed.connect(self._on_mouse_pressed)
            overlay.mouse_moved.connect(self._on_mouse_moved)
            overlay.mouse_released.connect(self._on_mouse_released)
            overlay.key_pressed.connect(self._on_key_pressed)
            self.overlays.append(overlay)
    
    def _close_overlays(self):
        """全オーバーレイを閉じる"""
        for overlay in self.overlays:
            overlay.close()
        self.overlays.clear()
    
    def _update_overlays(self):
        """全オーバーレイの選択範囲を更新"""
        for overlay in self.overlays:
            overlay.set_selection_rect(self.current_rect)
    
    def _on_mouse_pressed(self, global_pos: QPoint):
        """マウスボタン押下時（グローバル座標）"""
        self.start_pos = global_pos
        self.current_rect = QRect(global_pos, QSize(0, 0))
        self._update_overlays()
    
    def _on_mouse_moved(self, global_pos: QPoint):
        """マウス移動時（グローバル座標）"""
        if self.start_pos:
            self.current_rect = QRect(self.start_pos, global_pos).normalized()
            self._update_overlays()
    
    def _on_mouse_released(self, global_pos: QPoint):
        """マウスボタン解放時（グローバル座標）"""
        if self.start_pos:
            rect = QRect(self.start_pos, global_pos).normalized()
            
            # 範囲が有効な場合のみシグナルを発行
            if rect.width() > 10 and rect.height() > 10:
                # Retinaディスプレイなどのスケールファクターを考慮する必要があるか確認
                # screencaptureコマンドは通常、論理座標（ポイント）を受け取るため、
                # PyQtの座標（論理座標）そのままで良いはずだが、念のため整数化する
                
                # デバッグ用にDPRを取得（必要に応じて計算に含める）
                # dpr = self.screen.devicePixelRatio()
                
                self.region_selected.emit(
                    int(rect.x()),
                    int(rect.y()),
                    int(rect.width()),
                    int(rect.height())
                )
            
            self._close_overlays()
            self.start_pos = None
            self.current_rect = None
    
    def _on_key_pressed(self, key: int):
        """キー押下時"""
        if key == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self._close_overlays()
            self.start_pos = None
            self.current_rect = None
    
    def show_and_select(self):
        """オーバーレイを表示して範囲選択を開始"""
        self._create_overlays()
        for overlay in self.overlays:
            overlay.show()
            overlay.activateWindow()
            overlay.raise_()


if __name__ == "__main__":
    # テスト用コード
    app = QApplication(sys.argv)
    
    def on_selected(x, y, w, h):
        print(f"Selected region: x={x}, y={y}, width={w}, height={h}")
        app.quit()
    
    def on_cancelled():
        print("Selection cancelled")
        app.quit()
    
    selector = RegionSelector()
    selector.region_selected.connect(on_selected)
    selector.selection_cancelled.connect(on_cancelled)
    selector.show_and_select()
    
    sys.exit(app.exec())
