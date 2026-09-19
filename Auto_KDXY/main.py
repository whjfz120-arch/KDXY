import sys
import os
import cv2
import numpy as np
import win32gui
import win32con
import importlib
from PIL import ImageGrab
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QFileSystemWatcher

# 导入各个子功能模块
import modules.transport_materials as transport_materials
import modules.datang_exchange as datang_exchange
import modules.auto_harvest as auto_harvest
import modules.auto_draw_module as auto_draw_module

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("游戏自动化多功能总控台 (支持热更新)")
        self.resize(1000, 700)
        
        self.single_hwnd = None
        self.single_char_id = "未知"
        self.multi_hwnd_list = []
        self.ocr_reader = None  # EasyOCR 读取器

        # 1. 倒计时相关变量与定时器
        self.countdown_count = 3
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)

        # 2. 初始化热更新文件监听器 (QFileSystemWatcher)
        self.init_hot_reload()

        self.init_ui()

    def init_hot_reload(self):
        """初始化热更新文件监听"""
        self.watcher = QFileSystemWatcher(self)
        modules_dir = os.path.join(os.path.dirname(__file__), "modules")
        
        if os.path.exists(modules_dir):
            for file in os.listdir(modules_dir):
                if file.endswith(".py"):
                    full_path = os.path.join(modules_dir, file)
                    self.watcher.addPath(full_path)
            
            self.watcher.fileChanged.connect(self.on_module_file_changed)

    def on_module_file_changed(self, path):
        """当 modules 目录下的 python 文件修改保存时触发自动热加载"""
        filename = os.path.basename(path)
        print(f"🔥 检测到文件修改: {filename}，正在热更新...")

        try:
            if filename == "transport_materials.py":
                importlib.reload(transport_materials)
                self.rebuild_sub_module("transport")
            elif filename == "datang_exchange.py":
                importlib.reload(datang_exchange)
                self.rebuild_sub_module("datang")
            elif filename == "auto_harvest.py":
                importlib.reload(auto_harvest)
                self.rebuild_sub_module("harvest")
            elif filename == "auto_draw_module.py":
                importlib.reload(auto_draw_module)
                self.rebuild_sub_module("draw")

            if os.path.exists(path) and path not in self.watcher.files():
                self.watcher.addPath(path)

            print(f"✅ 模块 {filename} 热更新成功！")
        except Exception as e:
            print(f"❌ 模块 {filename} 热更新失败: {e}")

    def rebuild_sub_module(self, module_type):
        """重新实例化修改后的模块组件并替换界面 UI"""
        if module_type == "transport":
            old_index = 0
            self.single_sub_tabs.removeTab(old_index)
            self.transport_module = transport_materials.TransportModule()
            self.single_sub_tabs.insertTab(old_index, self.transport_module, "📦 运送物资任务")
            self.single_sub_tabs.setCurrentIndex(old_index)
            if self.single_hwnd:
                self.transport_module.set_hwnd(self.single_hwnd)
                self.transport_module.set_char_id(self.single_char_id)

        elif module_type == "datang":
            old_index = 1
            self.single_sub_tabs.removeTab(old_index)
            self.datang_module = datang_exchange.DatangExchangeModule()
            self.single_sub_tabs.insertTab(old_index, self.datang_module, "🔄 大唐物资兑换")
            if self.single_hwnd:
                self.datang_module.set_hwnd(self.single_hwnd)
                self.datang_module.set_char_id(self.single_char_id)

        elif module_type == "harvest":
            old_index = 2
            self.single_sub_tabs.removeTab(old_index)
            self.harvest_module = auto_harvest.HarvestModule()
            self.single_sub_tabs.insertTab(old_index, self.harvest_module, "🌿 自动收菜任务")
            if self.single_hwnd:
                self.harvest_module.set_hwnd(self.single_hwnd)
                self.harvest_module.set_char_id(self.single_char_id)

        elif module_type == "draw":
            self.multi_layout.removeWidget(self.auto_draw_module)
            self.auto_draw_module.deleteLater()
            self.auto_draw_module = auto_draw_module.AutoDrawModule()
            self.multi_layout.addWidget(self.auto_draw_module)
            if self.multi_hwnd_list:
                self.auto_draw_module.set_hwnd_list(self.multi_hwnd_list)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        self.top_tabs = QTabWidget()
        
        # ----------------- 标签页 1：单窗口工具集 -----------------
        tab_single = QWidget()
        single_layout = QVBoxLayout(tab_single)
        single_layout.setContentsMargins(15, 15, 15, 15)
        single_layout.setSpacing(10)

        bind_layout = QHBoxLayout()
        self.btn_bind_single = QPushButton("绑定当前单游戏窗口")
        self.btn_bind_single.clicked.connect(self.start_delayed_bind)
        bind_layout.addWidget(self.btn_bind_single)

        self.lbl_single_status = QLabel("未绑定单窗口: [点击按钮后请在3秒内切到游戏]")
        self.lbl_single_status.setStyleSheet("color: #795548; font-weight: bold; font-size: 13px;")
        bind_layout.addWidget(self.lbl_single_status)
        bind_layout.addStretch()
        single_layout.addLayout(bind_layout)

        self.single_sub_tabs = QTabWidget()
        self.transport_module = transport_materials.TransportModule()
        self.datang_module = datang_exchange.DatangExchangeModule()
        self.harvest_module = auto_harvest.HarvestModule()

        self.single_sub_tabs.addTab(self.transport_module, "📦 运送物资任务")
        self.single_sub_tabs.addTab(self.datang_module, "🔄 大唐物资兑换")
        self.single_sub_tabs.addTab(self.harvest_module, "🌿 自动收菜任务")
        single_layout.addWidget(self.single_sub_tabs)

        self.top_tabs.addTab(tab_single, "💻 单窗口工具集")

        # ----------------- 标签页 2：多窗口工具集 -----------------
        tab_multi = QWidget()
        self.multi_layout = QVBoxLayout(tab_multi)
        self.multi_layout.setContentsMargins(15, 15, 15, 15)
        self.multi_layout.setSpacing(10)

        multi_bind_layout = QHBoxLayout()
        self.btn_bind_multi = QPushButton("绑定所有游戏多开窗口")
        self.btn_bind_multi.clicked.connect(self.bind_multi_windows)
        multi_bind_layout.addWidget(self.btn_bind_multi)

        self.btn_arrange_multi = QPushButton("📐 一键平铺排列窗口")
        self.btn_arrange_multi.clicked.connect(self.arrange_windows)
        multi_bind_layout.addWidget(self.btn_arrange_multi)

        self.lbl_multi_status = QLabel("未绑定多开窗口: [请点击左侧按钮自动枚举]")
        self.lbl_multi_status.setStyleSheet("color: #795548; font-weight: bold;")
        multi_bind_layout.addWidget(self.lbl_multi_status)
        multi_bind_layout.addStretch()
        self.multi_layout.addLayout(multi_bind_layout)

        self.auto_draw_module = auto_draw_module.AutoDrawModule()
        self.multi_layout.addWidget(self.auto_draw_module)

        self.top_tabs.addTab(tab_multi, "🖥️ 多窗口多开工具集")
        main_layout.addWidget(self.top_tabs)

    def start_delayed_bind(self):
        self.btn_bind_single.setEnabled(False)
        self.countdown_count = 3
        self.lbl_single_status.setText(f"⏳ 请在 {self.countdown_count} 秒内用鼠标点击切换到您的游戏窗口...")
        self.countdown_timer.start()

    def update_countdown(self):
        self.countdown_count -= 1
        if self.countdown_count > 0:
            self.lbl_single_status.setText(f"⏳ 请在 {self.countdown_count} 秒内用鼠标点击切换到您的游戏窗口...")
        else:
            self.countdown_timer.stop()
            self.execute_bind_window()

    def execute_bind_window(self):
        self.btn_bind_single.setEnabled(True)
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd)
            if "总控台" in title:
                QMessageBox.warning(self, "绑定失败", "刚才倒计时结束前您没有切换到游戏窗口！请重试。")
                self.lbl_single_status.setText("未绑定单窗口: [绑定超时]")
                return

            self.single_hwnd = hwnd
            char_id = self.get_character_id_by_anchor(hwnd)
            self.single_char_id = char_id if char_id else "SP三月七"

            status_text = f"已绑定单窗口: [{title}]  |  👤 角色ID: {self.single_char_id}"
            self.lbl_single_status.setText(status_text)
            
            for module in [self.transport_module, self.datang_module, self.harvest_module]:
                if hasattr(module, "set_hwnd"): module.set_hwnd(hwnd)
                if hasattr(module, "set_char_id"): module.set_char_id(self.single_char_id)
                
            QMessageBox.information(self, "绑定成功", f"成功绑定窗口: {title}\n识别到角色ID: {self.single_char_id}")
        else:
            QMessageBox.warning(self, "绑定失败", "未能获取当前窗口句柄。")

    def get_character_id_by_anchor(self, hwnd):
        try:
            client_rect = win32gui.GetClientRect(hwnd)
            client_w = client_rect[2] - client_rect[0]
            client_h = client_rect[3] - client_rect[1]
            if client_w <= 0 or client_h <= 0: return "SP三月七"

            pt_left, pt_top = win32gui.ClientToScreen(hwnd, (0, 0))
            roi_x2 = pt_left + int(client_w * 0.35)
            roi_y2 = pt_top + int(client_h * 0.20)

            game_roi = ImageGrab.grab(bbox=(pt_left, pt_top, roi_x2, roi_y2))
            roi_np = np.array(game_roi)
            roi_gray = cv2.cvtColor(roi_np, cv2.COLOR_RGB2GRAY)

            template_path = os.path.join("assets", "hp_bar_template.png")
            crop_target = None
            
            if os.path.exists(template_path):
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                scale_ratio = client_w / 1024.0
                if abs(scale_ratio - 1.0) > 0.05:
                    template = cv2.resize(template, (max(10, int(template.shape[1] * scale_ratio)), max(10, int(template.shape[0] * scale_ratio))))

                h, w = template.shape
                res = cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val >= 0.6:
                    anchor_x, anchor_y = max_loc
                    crop_x1 = anchor_x + w + int(15 * scale_ratio)
                    crop_y1 = max(0, anchor_y - 5)
                    crop_x2 = anchor_x + w + int(150 * scale_ratio)
                    crop_y2 = anchor_y + h + 10
                    crop_target = roi_np[crop_y1:crop_y2, crop_x1:crop_x2]

            if crop_target is None or crop_target.size == 0:
                crop_x1 = int(client_w * 0.055)
                crop_y1 = int(client_h * 0.010)
                crop_x2 = int(client_w * 0.180)
                crop_y2 = int(client_h * 0.052)
                crop_target = roi_np[crop_y1:crop_y2, crop_x1:crop_x2]

            crop_target = cv2.resize(crop_target, (0, 0), fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

            if self.ocr_reader is None:
                import easyocr
                self.ocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

            results = self.ocr_reader.readtext(crop_target)
            if results:
                raw_text = "".join([res[1] for res in results])
                import re
                clean_text = re.sub(r'[^\w\u4e00-\u9fa5]', '', raw_text)
                clean_text = re.sub(r'^\d+', '', clean_text)
                if len(clean_text) >= 1: return clean_text

            return "SP三月七"
        except Exception as e:
            print(f"识别角色ID异常: {e}")
            return "SP三月七"

    def bind_multi_windows(self):
        valid_hwnds = []
        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and "总控台" in title: return True
                if "口袋西游" in title or "西游" in title:
                    rect = win32gui.GetClientRect(hwnd)
                    if (rect[2] - rect[0]) > 400 and (rect[3] - rect[1]) > 300:
                        valid_hwnds.append(hwnd)
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            QMessageBox.warning(self, "枚举错误", f"枚举窗口异常: {e}")
            return

        self.multi_hwnd_list = valid_hwnds
        self.lbl_multi_status.setText(f"已成功绑定多开窗口数: {len(valid_hwnds)} 个")
        if hasattr(self.auto_draw_module, "set_hwnd_list"):
            self.auto_draw_module.set_hwnd_list(valid_hwnds)
        QMessageBox.information(self, "多开绑定完成", f"成功精准扫描并绑定了 {len(valid_hwnds)} 个有效游戏窗口！")

    def arrange_windows(self):
        if not self.multi_hwnd_list:
            QMessageBox.warning(self, "排列提示", "尚未绑定任何多开游戏窗口！")
            return
        screen = QApplication.primaryScreen().geometry()
        cols = 2 if len(self.multi_hwnd_list) <= 4 else 3
        rows = (len(self.multi_hwnd_list) + cols - 1) // cols
        win_w, win_h = screen.width() // cols, screen.height() // rows

        for index, hwnd in enumerate(self.multi_hwnd_list):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, (index % cols) * win_w, (index // cols) * win_h, win_w, win_h, win32con.SWP_SHOWWINDOW)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
