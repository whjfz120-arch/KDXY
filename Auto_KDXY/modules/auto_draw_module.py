import os
import time
import cv2
import numpy as np
from PIL import ImageGrab
import win32gui
import win32con
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QMessageBox
from PySide6.QtCore import QThread, Signal

class AutoDrawWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd_list):
        super().__init__()
        self.hwnd_list = hwnd_list
        self._is_running = True

    def stop(self): 
        self._is_running = False

    def right_click_at(self, hwnd, client_x, client_y):
        """将窗口激活置顶，然后发送右键点击事件"""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass 
            
            time.sleep(0.05)
            l_param = client_y << 16 | (client_x & 0xFFFF)
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, l_param)
            time.sleep(0.05)
            win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, l_param)
        except Exception as e:
            print(f"右键点击异常: {e}")

    def find_and_click_target(self, hwnd):
        """在单个窗口中查找目标图片并右键点击"""
        # 获取当前脚本所在目录 (F:\KDXY-main\Auto_KDXY\modules)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 通过 ".." 回退到上一级目录 (F:\KDXY-main\Auto_KDXY)，再找到 assets\chouchou.png
        template_path = os.path.abspath(os.path.join(current_dir, "..", "assets", "chouchou.png"))
        
        if not os.path.exists(template_path):
            self.log_signal.emit(f"⚠️ 模板文件不存在: {template_path}")
            return False

        try:
            client_rect = win32gui.GetClientRect(hwnd)
            client_w = client_rect[2] - client_rect[0]
            client_h = client_rect[3] - client_rect[1]
            if client_w <= 0 or client_h <= 0:
                return False

            pt_left, pt_top = win32gui.ClientToScreen(hwnd, (0, 0))
            
            game_screenshot = ImageGrab.grab(bbox=(pt_left, pt_top, pt_left + client_w, pt_top + client_h))
            screenshot_np = np.array(game_screenshot)
            screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)

            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                return False

            th, tw = template.shape
            res = cv2.matchTemplate(screenshot_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val >= 0.7:
                match_x, match_y = max_loc
                center_x = match_x + tw // 2
                center_y = match_y + th // 2

                title = win32gui.GetWindowText(hwnd)
                self.log_signal.emit(f"🎯 [{title}] 匹配度: {max_val:.2f} | 找到目标，右键点击 ({center_x}, {center_y})")
                self.right_click_at(hwnd, center_x, center_y)
                return True
            return False

        except Exception as e:
            print(f"查找异常: {e}")
            return False

    def run(self):
        self.log_signal.emit(f"🚀 循环自动化任务已启动，当前监控窗口数: {len(self.hwnd_list)} 个")
        
        while self._is_running:
            for idx, hwnd in enumerate(self.hwnd_list):
                if not self._is_running: 
                    break
                
                if not win32gui.IsWindow(hwnd):
                    continue
                
                self.find_and_click_target(hwnd)
                time.sleep(0.2)
            
            for _ in range(10): 
                if not self._is_running: 
                    break
                time.sleep(0.1)

        self.log_signal.emit("🛑 循环自动化任务已安全终止。")
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
        layout.addWidget(QLabel("🖥️ 多窗口循环自动化操作控制台 (集成 1280x720 平铺与循环点击)"))
        self.lbl_status = QLabel("当前已载入多开窗口数: 0 个")
        layout.addWidget(self.lbl_status)
        
        # 按钮布局区
        btn_layout = QHBoxLayout()
        
        # 新增：集成在模块内部的一键平铺按钮
        self.btn_arrange = QPushButton("📐 一键平铺 (1280x720)")
        self.btn_arrange.clicked.connect(self.arrange_windows)
        btn_layout.addWidget(self.btn_arrange)

        self.btn_start = QPushButton("🟢 启动循环持续点击")
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("🔴 终止循环")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_action)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def arrange_windows(self):
        """在此模块内部实现一键平铺排列并固定分辨率为 1280x720"""
        if not self.hwnd_list:
            QMessageBox.warning(self, "排列提示", "尚未绑定任何多开游戏窗口！请先在上方的多开工具集中进行窗口绑定。")
            return
        
        screen = QApplication.primaryScreen().geometry()
        cols = 2 if len(self.hwnd_list) <= 4 else 3
        win_w, win_h = 1280, 720  # 固定分辨率宽度和高度为 1280x720

        for index, hwnd in enumerate(self.hwnd_list):
            if win32gui.IsWindow(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
                x = (index % cols) * win_w
                y = (index // cols) * win_h
                
                # 强制调整窗口位置及大小为 1280x720
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOP, 
                    x, y, win_w, win_h, 
                    win32con.SWP_SHOWWINDOW | win32con.SWP_NOZORDER
                )
            
        QMessageBox.information(self, "平铺与分辨率调整完成", f"已成功平铺排列 {len(self.hwnd_list)} 个窗口，并统一分辨率为 1280x720！")

    def log(self, text): 
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if not self.hwnd_list:
            self.log("错误：未检测到绑定的多开窗口！")
            return
        if self.worker and self.worker.isRunning(): 
            return
            
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_arrange.setEnabled(False)

        self.worker = AutoDrawWorker(self.hwnd_list)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_task_finished)
        self.worker.start()

    def stop_action(self):
        if self.worker and self.worker.isRunning():
            self.log("正在发出停止指令，请稍候...")
            self.worker.stop()

    def on_task_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_arrange.setEnabled(True)