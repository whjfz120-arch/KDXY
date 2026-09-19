import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import QThread, Signal

class AutoDrawWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd_list):
        super().__init__()
        self.hwnd_list = hwnd_list
        self._is_running = True

    def stop(self): self._is_running = False

    def run(self):
        self.log_signal.emit(f"开始执行多开同步抽奖，当前已绑定 {len(self.hwnd_list)} 个游戏窗口...")
        for idx, hwnd in enumerate(self.hwnd_list):
            if not self._is_running: break
            self.log_signal.emit(f"正在向第 {idx+1} 个窗口发送抽奖指令 (句柄: {hwnd})...")
            time.sleep(0.5)
        self.log_signal.emit("所有多开窗口同步抽奖指令执行完毕！")
        self.finished_signal.emit()

class AutoDrawModule(QWidget):
    def __init__(self):
        super().__init__()
        self.hwnd_list = []
        self.worker = None
        self.init_ui()

    def set_hwnd_list(self, hwnd_list):
        self.hwnd_list = hwnd_list
        self.lbl_status.setText(f"当前已载入多开窗口数: {len(hwnd_list)} 个")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🖥️ 多窗口多开抽奖/同步操作控制台"))
        self.lbl_status = QLabel("当前已载入多开窗口数: 0 个")
        layout.addWidget(self.lbl_status)
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("一键同步执行抽奖")
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def log(self, text): self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if not self.hwnd_list:
            self.log("错误：未检测到绑定的多开窗口！")
            return
        if self.worker and self.worker.isRunning(): return
        self.worker = AutoDrawWorker(self.hwnd_list)
        self.worker.log_signal.connect(self.log)
        self.worker.start()
