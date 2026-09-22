import os
import time
import cv2
import numpy as np
import win32gui
import win32api
import win32con
import win32ui
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QLineEdit, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeySequence

class DatangWorker(QThread):
    log_signal = Signal(str)
    stats_signal = Signal(int)
    finished_signal = Signal()

    def __init__(self, hwnd, max_count=None, char_id="未知"):
        super().__init__()
        self.hwnd = hwnd
        self.char_id = char_id
        self.target_count = max_count  # 目标轮数，None或0表示无限循环
        self._is_running = True
        self.reload_assets_config()

    def reload_assets_config(self):
        base_dir = Path(__file__).resolve().parent.parent 
        
        self.assets_dir = str(base_dir / "assets")
        self.debug_dir = os.path.join(base_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        # 资源路径定义（已废弃 crown 和 boss_text，改用 icon01 / icon02）
        self.npc_icon_paths = [
            os.path.join(self.assets_dir, "icon01.png"),
            os.path.join(self.assets_dir, "icon02.png")
        ]
        
        self.quest_related_paths = [
            os.path.join(self.assets_dir, "quest_related.png"),
            os.path.join(self.assets_dir, "task_related_template.png")
        ]
        
        self.task_dingguo_paths = [
            os.path.join(self.assets_dir, "task_dingguo_main.png"),
            os.path.join(self.assets_dir, "task_dingguo_main01.png")
        ]
        
        self.btn_confirm_paths = [
            os.path.join(self.assets_dir, "btn_confirm_dot.png"),
            os.path.join(self.assets_dir, "btn_confirm_dot_blue.png")
        ]

    def stop(self):
        self._is_running = False

    def interruptible_sleep(self, seconds):
        start = time.time()
        while time.time() - start < seconds:
            if not self._is_running:
                return False
            time.sleep(0.1)
        return True

    def run(self):
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            self.log_signal.emit("❌ 错误：未绑定有效游戏窗口，请先绑定游戏句柄！")
            self.finished_signal.emit()
            return

        mode_desc = f"{self.target_count} 轮" if self.target_count else "无限循环"
        self.log_signal.emit(f"🚀 [任务开始] 大唐物资兑换任务启动 | 角色: {self.char_id} | 目标轮数: {mode_desc}")
        
        completed_rounds = 0
        
        while self._is_running:
            self.reload_assets_config()
            
            # 检查是否达到目标轮数
            if self.target_count is not None and completed_rounds >= self.target_count:
                self.log_signal.emit(f"🎯 [任务达成] 已顺利完成设定的目标轮数 ({self.target_count} 轮)。")
                break
                
            win_rect = self.get_window_rect()
            if not win_rect:
                self.log_signal.emit("❌ [错误] 无法获取游戏窗口矩形位置，请检查窗口状态！")
                break

            self.log_signal.emit(f"📌 [窗口状态] 当前绑定窗口区域: x={win_rect['x']}, y={win_rect['y']}, w={win_rect['w']}, h={win_rect['h']}")
            self.log_signal.emit(f"--- 🔄 开始执行第 {completed_rounds + 1} 轮任务 ---")
            
            # 定义计数器（一轮包含2次循环）
            counter = 0
            round_success = True
            
            while counter < 2 and self._is_running:
                self.log_signal.emit(f"📍 [标记点a] 进入第 {counter + 1} 次子流程循环...")
                
                # 1. 查找 NPC 头顶的 icon01.png 或 icon02.png (置信度 > 0.7)
                self.log_signal.emit("🔍 [步骤 1/4] 正在查找 NPC 头顶图标 (icon01.png / icon02.png)...")
                icon_pos = self.wait_and_find_multi(win_rect, self.npc_icon_paths, "NPC头顶图标", timeout=10, confidence=0.7)
                
                if not icon_pos:
                    self.log_signal.emit("❌ [步骤 1/4 失败] 未能在超时时间内找到 NPC 头顶图标，流程中断。")
                    round_success = False
                    break
                
                # 图标下方固定像素偏移（可根据实际效果微调，这里向下偏移 60 像素点击NPC主体或名字）
                target_x = icon_pos[0]
                target_y = icon_pos[1] + 60
                
                self.log_signal.emit(f"🖱️ [动作] 成功定位Icon坐标 {icon_pos}，在其下方偏移处 ({target_x}, {target_y}) 执行双击NPC...")
                self.win32_double_click(target_x, target_y)
                
                self.log_signal.emit("⏳ [等待] 双击完成，延迟 1 秒...")
                if not self.interruptible_sleep(1.0): break

                # 2. 调用接任务函数，延迟1秒
                self.log_signal.emit("📌 [步骤 2/4] 调用接任务函数 (quest_related / task_related_template)...")
                if not self.quest_related_step(win_rect, timeout=10):
                    self.log_signal.emit("❌ [步骤 2/4 失败] 接任务步骤超时未找到对应图标。")
                    round_success = False
                    break
                
                self.log_signal.emit("⏳ [等待] 接任务点击完成，延迟 1 秒...")
                if not self.interruptible_sleep(1.0): break

                # 3. 调用定国安邦函数，延迟1秒
                self.log_signal.emit("📌 [步骤 3/4] 调用定国安邦函数 (task_dingguo_main / main01)...")
                if not self.dingguo_anbang_step(win_rect, timeout=10):
                    self.log_signal.emit("❌ [步骤 3/4 失败] 定国安邦步骤超时未找到对应图标。")
                    round_success = False
                    break
                
                self.log_signal.emit("⏳ [等待] 定国安邦点击完成，延迟 1 秒...")
                if not self.interruptible_sleep(1.0): break

                # 4. 调用确定函数，延迟1秒
                self.log_signal.emit("📌 [步骤 4/4] 调用确定函数 (btn_confirm_dot / blue)...")
                if not self.confirm_step(win_rect, timeout=10):
                    self.log_signal.emit("❌ [步骤 4/4 失败] 确定按钮步骤超时未找到对应图标。")
                    round_success = False
                    break
                
                self.log_signal.emit("⏳ [等待] 确定点击完成，延迟 1 秒...")
                if not self.interruptible_sleep(1.0): break

                # 5. 计数器 + 1，延迟 2 秒
                counter += 1
                self.log_signal.emit(f"✅ [子步骤完成] 当前轮次计数器更新: {counter}/2。等待 2 秒进入下一循环...")
                if not self.interruptible_sleep(2.0): break

            if not self._is_running:
                self.log_signal.emit("🛑 [用户终止] 收到停止指令，正在安全退出任务线程...")
                break

            if round_success and counter == 2:
                completed_rounds += 1
                self.log_signal.emit(f"🎉 [轮次成功] 第 {completed_rounds} 轮任务完整执行完毕！")
                self.stats_signal.emit(completed_rounds)
            else:
                self.log_signal.emit("❌ [轮次异常] 本轮任务未能完整执行（计数器未达2）, 停止后续循环。")
                break

        self.log_signal.emit("🏁 [线程退出] 大唐物资兑换任务线程已安全退出。")
        self.finished_signal.emit()

    # --- 核心功能函数定义 ---

    def quest_related_step(self, win_rect, timeout=10):
        """接任务函数：quest_related.png 或 task_related_template.png 置信度大于0.7时点击"""
        return self.wait_and_click_multi(win_rect, self.quest_related_paths, "接任务选项", timeout=timeout, confidence=0.7)

    def dingguo_anbang_step(self, win_rect, timeout=10):
        """定国安邦函数：task_dingguo_main.png 或 task_dingguo_main01.png 置信度大于0.7时点击"""
        return self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=timeout, confidence=0.7)

    def confirm_step(self, win_rect, timeout=10):
        """确定函数：btn_confirm_dot.png 或 btn_confirm_dot_blue.png 置信度大于0.7时点击"""
        return self.wait_and_click_multi(win_rect, self.btn_confirm_paths, "确定按钮", timeout=timeout, confidence=0.7)

    # --- 底层辅助与区域匹配方法 ---

    def get_window_rect(self):
        try:
            rect = win32gui.GetWindowRect(self.hwnd)
            return {'x': rect[0], 'y': rect[1], 'w': rect[2] - rect[0], 'h': rect[3] - rect[1]}
        except Exception as e:
            self.log_signal.emit(f"⚠️ 获取窗口矩形异常: {e}")
            return None

    def win32_click(self, x, y):
        self.log_signal.emit(f"🖱️ [鼠标左击] 坐标: ({x}, {y})")
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def win32_double_click(self, x, y):
        self.log_signal.emit(f"🖱️ [鼠标双击] 坐标: ({x}, {y})")
        self.win32_click(x, y)
        time.sleep(0.05)
        self.win32_click(x, y)

    def capture_screen_region(self, x, y, w, h):
        try:
            hwnd_dc = win32gui.GetWindowDC(win32gui.GetDesktopWindow())
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(mfc_dc, w, h)
            save_dc.SelectObject(bmp)
            save_dc.BitBlt((0, 0), (w, h), mfc_dc, (x, y), win32con.SRCCOPY)
            img = np.frombuffer(bmp.GetBitmapBits(True), dtype='uint8')
            img.shape = (h, w, 4)
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            self.log_signal.emit(f"⚠️ 截图异常: {e}")
            return None

    def find_template(self, win_rect, path, confidence=0.5, name="目标", search_region=None, save_debug=False):
        if not os.path.exists(path):
            self.log_signal.emit(f"⚠️ [文件缺失] 找不到模板文件: {path}")
            return None
        
        screen = self.capture_screen_region(win_rect['x'], win_rect['y'], win_rect['w'], win_rect['h'])
        if screen is None:
            return None
        
        # 如果指定了子区域 (rx, ry, rw, rh)，进行裁剪
        if search_region:
            rx, ry, rw, rh = search_region
            rx = max(0, rx)
            ry = max(0, ry)
            rw = min(rw, screen.shape[1] - rx)
            rh = min(rh, screen.shape[0] - ry)
            if rw <= 0 or rh <= 0:
                return None
            screen_crop = screen[ry:ry+rh, rx:rx+rw]
            offset_x = win_rect['x'] + rx
            offset_y = win_rect['y'] + ry
        else:
            screen_crop = screen
            offset_x = win_rect['x']
            offset_y = win_rect['y']

        template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            self.log_signal.emit(f"⚠️ [读取失败] 无法加载模板图像: {path}")
            return None
            
        if template.shape[0] > screen_crop.shape[0] or template.shape[1] > screen_crop.shape[1]:
            return None
        
        res = cv2.matchTemplate(cv2.cvtColor(screen_crop, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= confidence:
            pos_x = offset_x + max_loc[0] + template.shape[1]//2
            pos_y = offset_y + max_loc[1] + template.shape[0]//2
            self.log_signal.emit(f"🎯 [匹配成功] [{name}] 相似度: {max_val:.3f} (达标阈值: {confidence}) -> 目标屏幕坐标: ({pos_x}, {pos_y})")
            return pos_x, pos_y
        return None

    def wait_and_find_multi(self, win_rect, paths, name, timeout=10, confidence=0.7):
        """等待并多路径查找某个图标（如 icon01 / icon02）"""
        start = time.time()
        if not isinstance(paths, list):
            paths = [paths]
        self.log_signal.emit(f"⏳ [多路查找] 正在等待匹配 [{name}] (共 {len(paths)} 个备选模板, 超时: {timeout}秒, 阈值: {confidence})...")
        while time.time() - start < timeout:
            if not self._is_running:
                return None
            for idx, p in enumerate(paths):
                template_name = f"{name}_候选{idx+1}"
                pos = self.find_template(win_rect, p, confidence=confidence, name=template_name)
                if pos:
                    return pos
            time.sleep(0.5)
        self.log_signal.emit(f"❌ [多路查找超时] [{name}] 在 {timeout} 秒内均未匹配成功。")
        return None

    def wait_and_click_multi(self, win_rect, paths, name, timeout=10, confidence=0.7):
        start = time.time()
        if not isinstance(paths, list):
            paths = [paths]
        self.log_signal.emit(f"⏳ [多路查找] 正在等待匹配 [{name}] (共 {len(paths)} 个备选模板, 超时: {timeout}秒, 阈值: {confidence})...")
        while time.time() - start < timeout:
            if not self._is_running:
                return False
            for idx, p in enumerate(paths):
                template_name = f"{name}_候选{idx+1}"
                pos = self.find_template(win_rect, p, confidence=confidence, name=template_name)
                if pos:
                    self.log_signal.emit(f"🖱️ [执行点击] 在候选模板中成功匹配 [{template_name}]，点击坐标: {pos}")
                    self.win32_click(pos[0], pos[1])
                    return True
            time.sleep(0.5)
        self.log_signal.emit(f"❌ [多路查找超时] [{name}] 在 {timeout} 秒内均未匹配成功。")
        return False


class DatangExchangeModule(QWidget):
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
        layout.addWidget(QLabel("🔄 大唐物资兑换控制台 (快捷键: F11 启动, F2 停止)"))
        
        # 分辨率统一按钮区
        res_layout = QHBoxLayout()
        self.btn_resize = QPushButton("统一窗口分辨率至 1600x900")
        self.btn_resize.clicked.connect(self.resize_window_action)
        res_layout.addWidget(self.btn_resize)
        layout.addLayout(res_layout)

        # 轮数输入配置区
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行轮数 (留空或填0表示无限循环):"))
        self.input_count = QLineEdit()
        self.input_count.setPlaceholderText("例如: 5")
        self.input_count.setText("1")
        count_layout.addWidget(self.input_count)
        layout.addLayout(count_layout)

        # 启动与停止按钮区（绑定快捷键 F11 与 F2）
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("启动物资兑换 (F11)")
        self.btn_start.setShortcut(QKeySequence("F11"))
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止任务 (F2)")
        self.btn_stop.setShortcut(QKeySequence("F2"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_action)
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("📜 详细运行日志："))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(220)
        layout.addWidget(self.log_box)
        layout.setStretch(layout.indexOf(self.log_box), 1)

    def log(self, text): 
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def resize_window_action(self):
        """强行将绑定窗口重置为 1600x900 分辨率，固定像素比例"""
        if not self.bound_hwnd or not win32gui.IsWindow(self.bound_hwnd):
            self.log("❌ 错误：未绑定有效游戏窗口，无法调整分辨率！")
            return
        try:
            rect = win32gui.GetWindowRect(self.bound_hwnd)
            x, y = rect[0], rect[1]
            win32gui.MoveWindow(self.bound_hwnd, x, y, 1600, 900, True)
            self.log("🖥️ [分辨率调整] 已成功将绑定窗口重置为 1600x900 分辨率。")
        except Exception as e:
            self.log(f"⚠️ 调整窗口分辨率异常: {e}")

    def start_action(self):
        if self.worker and self.worker.isRunning():
            return
        
        count_text = self.input_count.text().strip()
        max_count = None
        if count_text.isdigit():
            val = int(count_text)
            if val > 0:
                max_count = val

        self.worker = DatangWorker(self.bound_hwnd, max_count=max_count, char_id=self.bound_char_id)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.worker.start()

    def stop_action(self):
        if self.worker and self.worker.isRunning():
            self.log("🛑 [控制台] 正在请求中断任务...")
            self.worker.stop()

    def on_worker_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)