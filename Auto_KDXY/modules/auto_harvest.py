import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import QThread, Signal

class HarvestWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd, char_id="未知"):
        super().__init__()
        self.hwnd = hwnd
        self.char_id = char_id
        self._is_running = True

    def stop(self): self._is_running = False

    def run(self):
        self.log_signal.emit(f"开始执行自动收菜任务 (当前角色: {self.char_id})...")
        for i in range(1, 4):
            if not self._is_running: break
            self.log_signal.emit(f"正在进行第 {i} 轮收菜...")
            time.sleep(1.0)
        self.log_signal.emit("自动收菜任务执行完成！")
        self.finished_signal.emit()

class HarvestModule(QWidget):
    def __init__(self):
        super().__init__()
        self.bound_hwnd = None
        self.bound_char_id = "未知"
        self.worker = None
        self.init_ui()

    def set_hwnd(self, hwnd): self.bound_hwnd = hwnd
    def set_char_id(self, cid): self.bound_char_id = cid

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🌿 自动收菜任务控制台"))
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("启动自动收菜")
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def log(self, text): self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if self.worker and self.worker.isRunning(): return
        self.worker = HarvestWorker(self.bound_hwnd, self.bound_char_id)
        self.worker.log_signal.connect(self.log)
        self.worker.start()
