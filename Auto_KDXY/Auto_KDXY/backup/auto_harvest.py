import time
import win32gui
import win32api
import win32con
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QFrame
from PySide6.QtCore import QThread, Signal, Qt
from pynput import mouse, keyboard

GAME_TITLE = "口袋西游"

class MouseListenerThread(QThread):
    pos_captured = Signal(int, int)

    def run(self):
        def on_click(x, y, button, pressed):
            if button == mouse.Button.left and pressed:
                self.pos_captured.emit(x, y)
                return False

        with mouse.Listener(on_click=on_click) as listener:
            listener.join()

class GlobalHotkeyThread(QThread):
    """后台监听全局快捷键 PageUp / PageDown"""
    start_signal = Signal()
    stop_signal = Signal()

    def run(self):
        def on_start():
            self.start_signal.emit()

        def on_stop():
            self.stop_signal.emit()

        # 注册全局快捷键 PageUp 与 PageDown
        with keyboard.GlobalHotKeys({
            '<page_up>': on_start,
            '<page_down>': on_stop
        }) as hotkey_listener:
            hotkey_listener.join()

class HarvestWorker(QThread):
    log_signal = Signal(str)

    def __init__(self, hwnd, x, y, interval):
        super().__init__()
        self.hwnd = hwnd
        self.x = x
        self.y = y
        self.interval = interval
        self.is_running = True

    def run(self):
        count = 0
        while self.is_running:
            if win32gui.GetForegroundWindow() != self.hwnd:
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.15)

            count += 1
            self.log_signal.emit(f"[{time.strftime('%H:%M:%S')}] 第 {count} 次触发采集...")
            
            win32api.SetCursorPos((self.x, self.y))
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            time.sleep(self.interval)

    def stop(self):
        self.is_running = False

class HarvestModule(QWidget):
    def __init__(self):
        super().__init__()
        self.target_x = None
        self.target_y = None
        self.worker = None
        self.init_ui()
        self.init_hotkeys()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                color: #3E2723;
                font-family: "YouYuan", "幼圆", "Microsoft YaHei UI", sans-serif;
            }
            QLabel {
                font-size: 15px;
                color: #3E2723;
                font-weight: bold;
            }
            QPushButton {
                background-color: #8D6E63;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6D4C41;
            }
            QPushButton:disabled {
                background-color: #D7CCC8;
                color: #795548;
            }
            QDoubleSpinBox {
                background-color: #FFFFFF;
                border: 2px solid #A1887F;
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
                color: #3E2723;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(18)

        # 头部标题
        self.label_pos = QLabel("当前选中坐标: 未设置")
        self.label_pos.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C1A1D;")
        layout.addWidget(self.label_pos)

        # 选点按钮
        self.btn_select = QPushButton("鼠标选取采集点")
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.clicked.connect(self.start_select_pos)
        layout.addWidget(self.btn_select)

        # 间隔配置
        h_layout = QHBoxLayout()
        label_int = QLabel("采集间隔 (秒):")
        label_int.setStyleSheet("color: #3E2723;")
        
        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.5, 60.0)
        self.spin_interval.setSingleStep(0.5)
        self.spin_interval.setValue(5.5)
        
        h_layout.addWidget(label_int)
        h_layout.addWidget(self.spin_interval)
        layout.addLayout(h_layout)

        # 启动/停止按钮（带快捷键提示）
        self.btn_start = QPushButton("启动采集 [PageUp]")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.toggle_harvest)
        layout.addWidget(self.btn_start)

        # 快捷键说明文字
        label_hotkey_tip = QLabel("快捷键: PageUp (启动) / PageDown (停止)")
        label_hotkey_tip.setStyleSheet("color: #8D6E63; font-size: 12px; font-weight: normal;")
        layout.addWidget(label_hotkey_tip)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #D7CCC8; border: none; max-height: 1px;")
        layout.addWidget(line)

        # 状态栏
        self.label_status = QLabel("状态: 就绪")
        self.label_status.setStyleSheet("color: #5D4037; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label_status)

        layout.addStretch()

    def init_hotkeys(self):
        """开启后台快捷键监听线程"""
        self.hotkey_thread = GlobalHotkeyThread()
        self.hotkey_thread.start_signal.connect(self.on_hotkey_start)
        self.hotkey_thread.stop_signal.connect(self.on_hotkey_stop)
        self.hotkey_thread.start()

    def on_hotkey_start(self):
        """按下 PageUp 触发表单启动"""
        if self.btn_start.isEnabled() and (not self.worker or not self.worker.isRunning()):
            self.start_harvest()

    def on_hotkey_stop(self):
        """按下 PageDown 触发表单停止"""
        if self.worker and self.worker.isRunning():
            self.stop_harvest()

    def start_select_pos(self):
        self.label_status.setText("状态: 请在屏幕上点击目标位置...")
        self.btn_select.setEnabled(False)
        
        self.listener_thread = MouseListenerThread()
        self.listener_thread.pos_captured.connect(self.on_pos_captured)
        self.listener_thread.start()

    def on_pos_captured(self, x, y):
        self.target_x, self.target_y = x, y
        self.label_pos.setText(f"当前选中坐标: ({x}, {y})")
        self.label_status.setText("状态: 坐标获取成功！可按 PageUp 或点击按钮开始。")
        self.btn_select.setEnabled(True)
        self.btn_start.setEnabled(True)

    def toggle_harvest(self):
        if self.worker and self.worker.isRunning():
            self.stop_harvest()
        else:
            self.start_harvest()

    def start_harvest(self):
        hwnd = win32gui.FindWindow(None, GAME_TITLE)
        if not hwnd:
            self.label_status.setText(f"状态: 错误，未找到【{GAME_TITLE}】游戏窗口")
            return
        
        interval = self.spin_interval.value()
        self.worker = HarvestWorker(hwnd, self.target_x, self.target_y, interval)
        self.worker.log_signal.connect(lambda msg: self.label_status.setText(f"状态: {msg}"))
        self.worker.start()
        
        self.btn_start.setText("停止采集 [PageDown]")
        self.btn_select.setEnabled(False)

    def stop_harvest(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            self.btn_start.setText("启动采集 [PageUp]")
            self.btn_select.setEnabled(True)
            self.label_status.setText("状态: 已停止采集")
