import os
import time
import cv2
import numpy as np
import win32gui
import win32con
from datetime import datetime
from PIL import ImageGrab
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QTextEdit, QMessageBox, QGroupBox)

class EatStoneWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd, loop_count, interval):
        super().__init__()
        self.hwnd = hwnd
        self.loop_count = loop_count  # 0 表示无限循环
        self.interval = interval
        self._is_running = True
        
        # 调试文件夹保留（防止其他地方报错），但不再写入截图
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_script_dir)
        self.debug_dir = os.path.join(project_root, "debug_shots")
        
        try:
            if not os.path.exists(self.debug_dir):
                os.makedirs(self.debug_dir)
        except Exception as e:
            print(f"创建 debug 目录失败: {e}")

    def run(self):
        self.log_signal.emit("🚀 【吃石头任务】开始运行...")
        current_loop = 0

        while self._is_running:
            if self.loop_count > 0 and current_loop >= self.loop_count:
                break

            current_loop += 1
            self.log_signal.emit(f"\n--- 🔄 开始第 {current_loop} 次循环 ---")

            if not self.hwnd or not win32gui.IsWindow(self.hwnd):
                self.log_signal.emit("❌ 错误：游戏窗口句柄无效或已关闭！")
                break

            # 1. 查找 qingqiong.png，置信度 > 0.7，双击目标点下方 100 像素
            if not self._find_and_action("qingqiong.png", action_type="double_click_offset", offset_y=100, threshold=0.7):
                self.log_signal.emit("⚠️ 未能找到 qingqiong.png")
            
            if not self._is_running: break
            time.sleep(1)

            # 2. 查找 eat_stone00.png 或 eat_stone01.png，置信度 > 0.7，点击
            found_stone = self._find_and_action(["eat_stone00.png", "eat_stone01.png"], action_type="click", threshold=0.7)
            if not found_stone:
                self.log_signal.emit("⚠️ 未能找到吃石头目标图标 (eat_stone00/01)")

            if not self._is_running: break
            time.sleep(1)

            # 3. 查找 confirm_template.png 或 btn_confirm_dot.png，置信度 > 0.7，点击
            found_confirm = self._find_and_action(["confirm_template.png", "btn_confirm_dot.png"], action_type="click", threshold=0.7)
            if not found_confirm:
                self.log_signal.emit("⚠️ 未能找到确认按钮模板")

            if not self._is_running: break
            time.sleep(1)

            # 4. 任务间隔延时 x 秒
            self.log_signal.emit(f"⏳ 任务单轮结束，等待间隔时间 {self.interval} 秒...")
            for _ in range(int(self.interval)):
                if not self._is_running: break
                time.sleep(1)

        self.log_signal.emit("🏁 【吃石头任务】已停止或执行完毕。")
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False

    def _capture_window(self):
        """截图当前绑定窗口的客户区"""
        try:
            client_rect = win32gui.GetClientRect(self.hwnd)
            w = client_rect[2] - client_rect[0]
            h = client_rect[3] - client_rect[1]
            if w <= 0 or h <= 0:
                return None
            pt_left, pt_top = win32gui.ClientToScreen(self.hwnd, (0, 0))
            box = (pt_left, pt_top, pt_left + w, pt_top + h)
            img = ImageGrab.grab(bbox=box)
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.log_signal.emit(f"❌ 截图异常: {e}")
            return None

    def _save_debug_screenshot(self, screen_img, tag_name, prefix="not_found"):
        """【已注释】保存 Debug 截图功能"""
        pass
        # try:
        #     if not os.path.exists(self.debug_dir):
        #         os.makedirs(self.debug_dir, exist_ok=True)
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        #     safe_tag_name = tag_name.replace(".", "_")
        #     filename = f"{prefix}_{safe_tag_name}_{timestamp}.png"
        #     filepath = os.path.join(self.debug_dir, filename)
        #     cv2.imwrite(filepath, screen_img)
        #     self.log_signal.emit(f"📷 [Debug 截图已保存] -> {filepath}")
        # except Exception as e:
        #     self.log_signal.emit(f"❌ 保存 Debug 截图失败: {e}")

    def _find_and_action(self, template_names, action_type="click", offset_y=0, threshold=0.7):
        """通用图像查找与动作执行（已注释截图保存和画图逻辑）"""
        if isinstance(template_names, str):
            template_names = [template_names]

        screen_img = self._capture_window()
        if screen_img is None:
            return False

        screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)

        for name in template_names:
            template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", name)
            if not os.path.exists(template_path):
                continue

            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                continue

            th, tw = template.shape[:2]
            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val >= threshold:
                top_left = max_loc
                
                center_x = max_loc[0] + tw // 2
                center_y = max_loc[1] + th // 2
                
                target_x = center_x
                target_y = center_y + offset_y

                self.log_signal.emit(f"🎯 找到目标 [{name}] 置信度: {max_val:.2f} | 客户区坐标: ({target_x}, {target_y})")

                # --- 【已注释】可视化标注图片并保存的代码 ---
                # annotated_img = screen_img.copy()
                # cv2.rectangle(annotated_img, top_left, bottom_right, (0, 255, 0), 2)
                # cv2.putText(annotated_img, f"{name} ({max_val:.2f})", (top_left[0], max(0, top_left[1] - 5)), 
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                # cv2.circle(annotated_img, (target_x, target_y), 6, (0, 0, 255), -1)
                # cv2.putText(annotated_img, f"Click({target_x},{target_y})", (target_x + 8, target_y + 4), 
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # self._save_debug_screenshot(annotated_img, name, prefix="found_hit")

                # 执行有效点击动作
                if action_type == "click":
                    self._send_click(target_x, target_y)
                elif action_type == "double_click_offset":
                    self._send_double_click(target_x, target_y)
                return True

        # --- 【已注释】未找到目标时的截图保存 ---
        # display_name = template_names[0] if len(template_names) == 1 else "_".join(template_names)
        # self._save_debug_screenshot(screen_img, display_name, prefix="not_found")
        return False

    def _activate_window(self):
        """确保窗口恢复并置顶激活，参考自 auto_draw_module.py"""
        try:
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception:
                pass
            time.sleep(0.05)
        except Exception as e:
            print(f"激活窗口异常: {e}")

    def _send_click(self, x, y):
        """激活窗口后投递点击消息"""
        try:
            self._activate_window()
            l_param = (y << 16) | (x & 0xFFFF)
            win32gui.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, l_param)
            time.sleep(0.03)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
            time.sleep(0.05)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, l_param)
        except Exception as e:
            self.log_signal.emit(f"❌ 点击动作异常: {e}")

    def _send_double_click(self, x, y):
        """激活窗口后投递双击消息"""
        try:
            self._activate_window()
            l_param = (y << 16) | (x & 0xFFFF)
            win32gui.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, l_param)
            time.sleep(0.03)
            # 第一次点击
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
            time.sleep(0.03)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, l_param)
            time.sleep(0.05)
            # 第二次点击（构成双击）
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, l_param)
            time.sleep(0.03)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, l_param)
        except Exception as e:
            self.log_signal.emit(f"❌ 双击动作异常: {e}")


class EatStoneModule(QWidget):
    def __init__(self):
        super().__init__()
        self.hwnd = None
        self.char_id = "未知"
        self.worker = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        group_setting = QGroupBox("⚙️ 吃石头任务参数配置")
        setting_layout = QVBoxLayout(group_setting)

        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel("循环次数 (输入 0 为无限循环):"))
        self.spin_loop = QSpinBox()
        self.spin_loop.setRange(0, 9999)
        self.spin_loop.setValue(0)
        loop_layout.addWidget(self.spin_loop)
        setting_layout.addLayout(loop_layout)

        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("任务间隔时间 (秒):"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 3600)
        self.spin_interval.setValue(10)
        interval_layout.addWidget(self.spin_interval)
        setting_layout.addLayout(interval_layout)

        layout.addWidget(group_setting)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始吃石头任务")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px;")
        self.btn_start.clicked.connect(self.start_task)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ 停止任务")
        self.btn_stop.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 6px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("📜 任务运行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def set_hwnd(self, hwnd):
        self.hwnd = hwnd

    def set_char_id(self, char_id):
        self.char_id = char_id

    def append_log(self, text):
        self.log_text.append(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def start_task(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            QMessageBox.warning(self, "警告", "请先在总控台绑定有效的单游戏窗口！")
            return

        loop_count = self.spin_loop.value()
        interval = self.spin_interval.value()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.spin_loop.setEnabled(False)
        self.spin_interval.setEnabled(False)

        self.worker = EatStoneWorker(self.hwnd, loop_count, interval)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_task_finished)
        self.worker.start()

    def stop_task(self):
        if self.worker:
            self.worker.stop()
        self.append_log("🛑 正在停止任务...")

    def on_task_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.spin_loop.setEnabled(True)
        self.spin_interval.setEnabled(True)
        self.worker = None