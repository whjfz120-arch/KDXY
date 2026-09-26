from pathlib import Path
import os
import time
import random
import ctypes
import cv2
import numpy as np
import win32gui
import win32api
import win32con
import win32ui
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QComboBox, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

# ==================== ctypes 底层硬件输入结构体定义 ====================
PUL = ctypes.POINTER(ctypes.c_ulong)

class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]


class WindowTaskState:
    """用于记录和管理单个游戏窗口的独立状态与独立计时器"""
    def __init__(self, hwnd, index):
        self.hwnd = hwnd
        self.index = index
        self.title = win32gui.GetWindowText(hwnd)
        
        self.step_state = 'init'
        self.timer_target = 0.0  
        self.state_start_time = 0.0 
        self.completed_rounds = 0
        self.is_stage_finished = False  


class TransportWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd_list, test_mode="full_chain", max_count=1, char_id="未知"):
        super().__init__()
        self.hwnd_list = hwnd_list
        self.char_id = char_id
        self.test_mode = test_mode     
        self.target_count = max_count   
        self._is_running = True
        
        self.current_hwnd = None
        self.reload_assets_config()

    def reload_assets_config(self):
        base_dir = Path(__file__).resolve().parent.parent
        self.assets_dir = str(base_dir / "assets")
        
        self.template_scrollbar  = os.path.join(self.assets_dir, "scrollbar.png")
        self.accept_btn_path     = os.path.join(self.assets_dir, "accept_quest.png")
        self.quest_level_path    = os.path.join(self.assets_dir, "quest_level.png")
        self.npc_level_1_path    = os.path.join(self.assets_dir, "npc_level_1.png") 
        self.npc_level_2_path    = os.path.join(self.assets_dir, "npc_level_2.png") 
        
        self.npc_00_pos_path        = os.path.join(self.assets_dir, "npc00_pos.png")
        self.npc_level_0_head_path  = os.path.join(self.assets_dir, "npc00_head.png")

        self.npc_03_pos_path         = os.path.join(self.assets_dir, "npc03_pos.png")
        self.npc_level_3_head_path   = os.path.join(self.assets_dir, "npc_level_3_head.png")
        self.task_dingguo_main01_path = os.path.join(self.assets_dir, "task_dingguo_main01.png")
        
        self.npc_04_pos_path         = os.path.join(self.assets_dir, "npc04_pos.png")
        self.npc_level_4_head_path   = os.path.join(self.assets_dir, "npc04_head.png")
        self.npc_icon02_path         = os.path.join(self.assets_dir, "icon02.png")
        
        self.quest_related_path         = os.path.join(self.assets_dir, "quest_related.png")
        self.task_related_template_path = os.path.join(self.assets_dir, "task_related_template.png")
        
        self.task_related_paths = [self.quest_related_path, self.task_related_template_path]
        self.task_dingguo_paths = [
            os.path.join(self.assets_dir, "task_dingguo_main.png"),
            self.task_dingguo_main01_path
        ]
        self.btn_confirm_paths = [
            os.path.join(self.assets_dir, "btn_confirm_dot.png"),
            os.path.join(self.assets_dir, "btn_confirm_dot_blue.png")
        ]

    def stop(self):
        self._is_running = False

    def change_state(self, ws, new_state):
        ws.step_state = new_state
        ws.state_start_time = time.time()

    def run(self):
        if not self.hwnd_list:
            self.log_signal.emit("❌ 错误：未绑定任何多开游戏窗口！")
            self.finished_signal.emit()
            return

        self.log_signal.emit(f"🚀 开始多窗口【同步对齐运行】物资运送任务 | 监控窗口数: {len(self.hwnd_list)} | 起始模式: {self.test_mode}")
        
        window_states = []
        for idx, hwnd in enumerate(self.hwnd_list):
            ws = WindowTaskState(hwnd, idx)
            # 依据选择的测试模式作为“起始点”注入对应状态
            if self.test_mode == "npc00": self.change_state(ws, 'init')
            elif self.test_mode == "npc01": self.change_state(ws, 'npc01_menu')
            elif self.test_mode == "npc02": self.change_state(ws, 'npc02_menu')
            elif self.test_mode == "npc03": self.change_state(ws, 'npc03_map')
            elif self.test_mode == "npc04": self.change_state(ws, 'npc04_map')
            elif self.test_mode == "return_npc00": self.change_state(ws, 'return_map')
            else:
                self.change_state(ws, 'init')
            window_states.append(ws)

        while self._is_running:
            self.reload_assets_config()
            
            all_finished = True
            for ws in window_states:
                if not self._is_running: break
                if ws.step_state == 'completed':
                    continue
                
                all_finished = False
                if not win32gui.IsWindow(ws.hwnd):
                    self.log_signal.emit(f"⚠️ 窗口 [{ws.title}] 已关闭，标记完成。")
                    ws.step_state = 'completed'
                    ws.is_stage_finished = True
                    continue

                if time.time() < ws.timer_target:
                    continue 

                self.ensure_window_resolution(ws.hwnd)
                self.current_hwnd = ws.hwnd
                self.activate_window(ws.hwnd)
                
                win_rect = self.get_window_rect(ws.hwnd)
                if not win_rect: continue

                self.process_window_step(ws, win_rect)

            if not self._is_running: break
            
            if all_finished:
                self.log_signal.emit(f"🎯 所有窗口均已达到设定的目标轮数，任务顺利完成！")
                break
                
            self.check_and_sync_stages(window_states)
            time.sleep(0.2)

        self.log_signal.emit("🏁 任务线程已安全退出。")
        self.finished_signal.emit()

    def check_and_sync_stages(self, window_states):
        active_states = [ws for ws in window_states if ws.step_state != 'completed']
        if not active_states:
            return

        all_stage_done = all(ws.is_stage_finished for ws in active_states)
        if not all_stage_done:
            return

        current_stage_type = active_states[0].step_state
        
        next_stage_map = {
            'npc00_completed': ('npc01_menu', "NPC00"),
            'npc01_completed': ('npc02_menu', "NPC01"),
            'npc02_completed': ('npc03_map', "NPC02"),
            'npc03_completed': ('npc04_map', "NPC03"),
            'npc04_completed': ('return_map', "NPC04"),
            'return_completed': ('init', "返回NPC00轮次")
        }

        if current_stage_type in next_stage_map:
            target_state, stage_name = next_stage_map[current_stage_type]
            
            # 统一流转，不再限制必须是 full_chain，单项测试起点也能自然向后流转
            self.log_signal.emit(f"✨ 【同步对齐】所有窗口已同步完成 {stage_name} 阶段，统一进入下一流程！")
            for ws in active_states:
                ws.is_stage_finished = False
                self.change_state(ws, target_state)

    def ensure_window_resolution(self, hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            rect = win32gui.GetWindowRect(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, rect[0], rect[1], 1600, 900, win32con.SWP_SHOWWINDOW | win32con.SWP_NOZORDER)
        except: pass

    # ==================== 核心状态机：单窗口单步推进 ====================

    def process_window_step(self, ws, win_rect):
        state = ws.step_state
        title = ws.title

        if ws.is_stage_finished:
            return

        # ---------- NPC00 阶段 ----------
        if state == 'init':
            self.log_signal.emit(f"📌 [{title}] [NPC00] 打开地图并寻路...")
            self.press_key(0x4D) # M键
            time.sleep(0.5)
            self.change_state(ws, 'npc00_map')
            return

        elif state == 'npc00_map':
            pos, max_val = self.find_template_with_score(win_rect, self.npc_00_pos_path)
            self.log_signal.emit(f"🔍 [{title}] [NPC00地图] 查找目标 'npc00_pos.png' -> 最佳匹配度: {max_val:.2f} (要求>=0.7)")
            if pos:
                self.log_signal.emit(f"🎯 [{title}] [NPC00地图] 成功找到目标位置，点击双击寻路！")
                self.hardware_double_click(pos[0], pos[1])
                time.sleep(0.5)
                self.press_key(0x4D) # 关闭地图
                self.log_signal.emit(f"⏳ [{title}] [NPC00] 发起寻路成功，独立计时等待 3 秒...")
                ws.timer_target = time.time() + 3.0
                self.change_state(ws, 'npc00_wait_move')
            else:
                self.log_signal.emit(f"⚠️ [{title}] [NPC00地图] 未能匹配到 'npc00_pos.png'，重试中...")

        elif state == 'npc00_wait_move':
            if time.time() - ws.state_start_time > 8.0:
                self.log_signal.emit(f"⚠️ [{title}] [NPC00] 等待头部超时（>8秒），自动尝试强行进入对话...")
                self.change_state(ws, 'npc00_dialog')
                return

            pos_head, max_val = self.find_template_with_score(win_rect, self.npc_level_0_head_path)
            if int(time.time() * 2) % 2 == 0:
                self.log_signal.emit(f"🔍 [{title}] [NPC00等待移动] 查找头部 'npc00_head.png' -> 最佳匹配度: {max_val:.2f} (要求>=0.5)")
            
            if pos_head and max_val >= 0.5:
                target_x = pos_head[0]
                target_y = pos_head[1] + 120 
                self.log_signal.emit(f"🎯 [{title}] [NPC00等待移动] 找到头部图标！按下S键并双击正下方 120 像素处。")
                self.press_key(0x53) # S键
                time.sleep(0.3)
                self.hardware_double_click(target_x, target_y)
                time.sleep(0.5)
                self.change_state(ws, 'npc00_dialog')

        elif state == 'npc00_dialog':
            dingguo_clicked = self.click_task_dingguo_if_exists(win_rect)
            if dingguo_clicked:
                self.log_signal.emit(f"✅ [{title}] [NPC00对话] 成功点击顶国任务并完成确认！")
            
            if dingguo_clicked or (time.time() - ws.state_start_time > 8.0):
                if not dingguo_clicked:
                    self.log_signal.emit(f"⚠️ [{title}] [NPC00对话] 对话超时（>8秒未点到顶国任务），强制视为完成。")
                self.log_signal.emit(f"✅ [{title}] NPC00 阶段已完成，等待其他窗口同步...")
                ws.is_stage_finished = True
                self.change_state(ws, 'npc00_completed')

        # ---------- NPC01 阶段 ----------
        elif state == 'npc01_menu':
            self.log_signal.emit(f"📌 [{title}] [NPC01] 打开关卡菜单...")
            self.press_key(0x51) # Q键
            time.sleep(0.5)
            if self.click_template(win_rect, self.quest_level_path, 0.7):
                time.sleep(0.5)
                if self.double_click_template(win_rect, self.npc_level_1_path, 0.7):
                    time.sleep(0.5)
                    self.press_key(0x51)
                    self.log_signal.emit(f"⏳ [{title}] [NPC01] 进入关卡，独立计时等待传送 (25秒)...")
                    ws.timer_target = time.time() + 25.0
                    self.change_state(ws, 'npc01_wait_task')

        elif state == 'npc01_wait_task':
            self.log_signal.emit(f"🔍 [{title}] [NPC01] 正在查找并点击“任务相关”...")
            if self.click_task_related_if_exists(win_rect):
                self.log_signal.emit(f"✅ [{title}] [NPC01] 成功点击“任务相关”，进入下一步...")
                time.sleep(1.0)
                self.change_state(ws, 'npc01_dingguo')
            elif time.time() - ws.state_start_time > 30.0:
                self.log_signal.emit(f"⚠️ [{title}] [NPC01] 寻找“任务相关”超时（>30秒），强制跳至下一步...")
                time.sleep(1.0)
                self.change_state(ws, 'npc01_dingguo')

        elif state == 'npc01_dingguo':
            self.log_signal.emit(f"🔍 [{title}] [NPC01] 正在查找并点击顶国任务...")
            if self.click_template_multi(win_rect, self.task_dingguo_paths, 0.7):
                self.log_signal.emit(f"✅ [{title}] [NPC01] 成功点击顶国任务，进入确认步骤...")
                time.sleep(1.0)
                self.change_state(ws, 'npc01_confirm')
            elif time.time() - ws.state_start_time > 18.0:
                self.log_signal.emit(f"⚠️ [{title}] [NPC01] 寻找顶国任务超时（>18秒），强制跳至确认步骤...")
                time.sleep(1.0)
                self.change_state(ws, 'npc01_confirm')

        elif state == 'npc01_confirm':
            self.log_signal.emit(f"🔍 [{title}] [NPC01] 正在查找并点击确认按钮...")
            if self.click_confirm(win_rect):
                self.log_signal.emit(f"✅ [{title}] [NPC01] 确认按钮完成，NPC01 阶段完成！等待其他窗口同步...")
                ws.is_stage_finished = True
                self.change_state(ws, 'npc01_completed')

        # ---------- NPC02 阶段 ----------
        elif state == 'npc02_menu':
            self.log_signal.emit(f"📌 [{title}] [NPC02] 打开关卡菜单...")
            self.press_key(0x51)
            time.sleep(0.5)
            if self.click_template(win_rect, self.quest_level_path, 0.7):
                time.sleep(0.5)
                if self.double_click_template(win_rect, self.npc_level_2_path, 0.7):
                    time.sleep(1.0)
                    self.press_key(0x51)
                    self.log_signal.emit(f"⏳ [{title}] [NPC02] 进入关卡，独立计时等待传送 (40秒)...")
                    ws.timer_target = time.time() + 40.0
                    self.change_state(ws, 'npc02_dingguo')

        elif state == 'npc02_dingguo':
            if self.click_template_multi(win_rect, self.task_dingguo_paths, 0.7):
                time.sleep(1.0)
                self.change_state(ws, 'npc02_confirm')

        elif state == 'npc02_confirm':
            if self.click_confirm(win_rect):
                self.log_signal.emit(f"✅ [{title}] NPC02 阶段已完成，等待其他窗口同步...")
                ws.is_stage_finished = True
                self.change_state(ws, 'npc02_completed')

        # ---------- NPC03 阶段 ----------
        elif state == 'npc03_map':
            self.log_signal.emit(f"📌 [{title}] [NPC03] 打开地图寻路...")
            self.press_key(0x4D)
            time.sleep(0.8)
            pos = self.find_template(win_rect, self.npc_03_pos_path, confidence=0.7)
            if pos:
                self.hardware_double_click(pos[0], pos[1])
                time.sleep(0.5)
                self.press_key(0x4D)
                wait_sec = 48.0
                self.log_signal.emit(f"⏳ [{title}] [NPC03] 跑路中，独立计时等待 {wait_sec} 秒...")
                ws.timer_target = time.time() + wait_sec
                self.change_state(ws, 'npc03_wait_move')
            else:
                self.press_key(0x4D)

        elif state == 'npc03_wait_move':
            pos_head, max_val = self.find_template_with_score(win_rect, self.npc_level_3_head_path)
            if int(time.time() * 2) % 2 == 0:
                self.log_signal.emit(f"🔍 [{title}] [NPC03等待移动] 查找头部 'npc_level_3_head.png' -> 最佳匹配度: {max_val:.2f} (要求>=0.7)")
            
            if pos_head and max_val >= 0.7:
                self.log_signal.emit(f"🎯 [{title}] [NPC03等待移动] 成功找到头部图标！双击并进入对话。")
                self.hardware_double_click(pos_head[0], pos_head[1])
                time.sleep(0.3)
                self.change_state(ws, 'npc03_dialog')

        elif state == 'npc03_dialog':
            if self.click_task_dingguo_if_exists(win_rect) or (time.time() - ws.state_start_time > 10.0):
                self.log_signal.emit(f"✅ [{title}] NPC03 阶段已完成，等待其他窗口同步...")
                ws.is_stage_finished = True
                self.change_state(ws, 'npc03_completed')

        # ---------- NPC04 阶段 ----------
        elif state == 'npc04_map':
            self.log_signal.emit(f"📌 [{title}] [NPC04] 打开地图寻路...")
            self.press_key(0x4D)
            time.sleep(0.8)
            pos = self.find_template(win_rect, self.npc_04_pos_path, confidence=0.7)
            if pos:
                self.hardware_double_click(pos[0], pos[1])
                time.sleep(0.3)
                self.press_key(0x4D)
                wait_sec = 48.0
                self.log_signal.emit(f"⏳ [{title}] [NPC04] 跑路中，独立计时等待 {wait_sec} 秒...")
                ws.timer_target = time.time() + wait_sec
                self.change_state(ws, 'npc04_wait_move')
            else:
                self.press_key(0x4D)

        elif state == 'npc04_wait_move':
            pos_icon = self.find_template(win_rect, self.npc_icon02_path, confidence=0.65)
            if pos_icon:
                self.press_key(0x53)
                time.sleep(0.3)
                self.hardware_double_click(pos_icon[0], pos_icon[1] + 100)
                time.sleep(0.5)
                self.change_state(ws, 'npc04_dialog')

        elif state == 'npc04_dialog':
            if self.click_task_related_if_exists(win_rect):
                time.sleep(0.5)
                if self.click_task_dingguo_if_exists(win_rect):
                    self.log_signal.emit(f"✅ [{title}] NPC04 阶段已完成，等待其他窗口同步...")
                    ws.is_stage_finished = True
                    self.change_state(ws, 'npc04_completed')

        # ---------- 返回 NPC00 阶段 ----------
        elif state == 'return_map':
            self.log_signal.emit(f"📌 [{title}] [返回] 打开地图返回 NPC00...")
            self.press_key(0x4D)
            time.sleep(1.0)
            pos = self.find_template(win_rect, self.npc_00_pos_path, confidence=0.7)
            if pos:
                self.hardware_double_click(pos[0], pos[1])
                time.sleep(1.0)
                self.press_key(0x4D)
                wait_sec = random.randint(140, 160)
                self.log_signal.emit(f"⏳ [{title}] [返回] 路上，独立计时等待 {wait_sec} 秒...")
                ws.timer_target = time.time() + wait_sec
                self.change_state(ws, 'return_wait_move')
            else:
                self.press_key(0x4D)

        elif state == 'return_wait_move':
            ws.completed_rounds += 1
            self.log_signal.emit(f"🎉 [{title}] 第 {ws.completed_rounds} 轮循环圆满完成，等待其他窗口同步轮次...")
            ws.is_stage_finished = True
            self.change_state(ws, 'return_completed')
            
            if self.target_count is not None and ws.completed_rounds >= self.target_count:
                self.change_state(ws, 'completed')

    # ==================== 底层绝对硬件级模拟 (SendInput) ====================

    def activate_window(self, hwnd):
        try:
            if hwnd:
                if win32gui.IsIconic(hwnd): 
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.05)
        except: pass

    def press_key(self, vk):
        extra = ctypes.c_ulong(0)
        ii_ = Input_I()
        ii_.ki = KeyBdInput(vk, 0, 0, 0, ctypes.pointer(extra))
        x = Input(ctypes.c_ulong(1), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))
        time.sleep(0.03)
        ii_.ki = KeyBdInput(vk, 0, 0x0002, 0, ctypes.pointer(extra))
        x = Input(ctypes.c_ulong(1), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    def hardware_move(self, x, y):
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        abs_x = int(x * 65535 / screen_w)
        abs_y = int(y * 65535 / screen_h)
        
        extra = ctypes.c_ulong(0)
        ii_ = Input_I()
        ii_.mi = MouseInput(abs_x, abs_y, 0, (0x0001 | 0x8000), 0, ctypes.pointer(extra))
        x_in = Input(ctypes.c_ulong(0), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x_in), ctypes.sizeof(x_in))

    def hardware_click(self, x, y):
        self.hardware_move(x, y)
        time.sleep(0.03)
        extra = ctypes.c_ulong(0)
        ii_ = Input_I()
        ii_.mi = MouseInput(0, 0, 0, 0x0002, 0, ctypes.pointer(extra))
        x_down = Input(ctypes.c_ulong(0), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x_down), ctypes.sizeof(x_down))
        time.sleep(0.03)
        ii_.mi = MouseInput(0, 0, 0, 0x0004, 0, ctypes.pointer(extra))
        x_up = Input(ctypes.c_ulong(0), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x_up), ctypes.sizeof(x_up))

    def hardware_double_click(self, x, y):
        self.hardware_click(x, y)
        time.sleep(0.05)
        self.hardware_click(x, y)

    # ==================== 图像查找与快捷助手 ====================

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
        except: return None

    def find_template_with_score(self, win_rect, path):
        if not os.path.exists(path): return None, 0.0
        screen = self.capture_screen_region(win_rect['x'], win_rect['y'], win_rect['w'], win_rect['h'])
        if screen is None: return None, 0.0
        template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if template is None: return None, 0.0
        
        res = cv2.matchTemplate(cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        pos = (win_rect['x'] + max_loc[0] + template.shape[1]//2, win_rect['y'] + max_loc[1] + template.shape[0]//2)
        return pos, float(max_val)

    def find_template(self, win_rect, path, confidence=0.5):
        pos, max_val = self.find_template_with_score(win_rect, path)
        if max_val >= confidence:
            return pos
        return None

    def get_window_rect(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            return {'x': rect[0], 'y': rect[1], 'w': rect[2] - rect[0], 'h': rect[3] - rect[1]}
        except: return None

    def click_template(self, win_rect, path, confidence=0.5):
        pos = self.find_template(win_rect, path, confidence)
        if pos:
            self.hardware_click(pos[0], pos[1])
            return True
        return False

    def double_click_template(self, win_rect, path, confidence=0.5):
        pos = self.find_template(win_rect, path, confidence)
        if pos:
            self.hardware_double_click(pos[0], pos[1])
            return True
        return False

    def click_template_multi(self, win_rect, paths, confidence=0.75):
        if not isinstance(paths, list): paths = [paths]
        for p in paths:
            pos = self.find_template(win_rect, p, confidence=confidence)
            if pos:
                self.hardware_click(pos[0], pos[1])
                return True
        return False

    def click_task_related_if_exists(self, win_rect):
        return self.click_template_multi(win_rect, self.task_related_paths, confidence=0.7)

    def click_task_dingguo_if_exists(self, win_rect):
        if self.click_template_multi(win_rect, self.task_dingguo_paths, confidence=0.7):
            time.sleep(0.3)
            return self.click_confirm(win_rect)
        return False

    def click_confirm(self, win_rect):
        return self.click_template_multi(win_rect, self.btn_confirm_paths, confidence=0.7)


class TransportModule(QWidget):
    def __init__(self):
        super().__init__()
        self.hwnd_list = []
        self.worker = None
        self.init_ui()

    def set_hwnd_list(self, hwnd_list):
        self.hwnd_list = hwnd_list
        self.lbl_status.setText(f"当前已载入多开窗口数: {len(hwnd_list)} 个 (已修正 NPC03 头部资源路径)")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("📦 多窗口运送物资任务控制台 (流转修复版)"))
        
        self.lbl_status = QLabel("当前已载入多开窗口数: 0 个")
        layout.addWidget(self.lbl_status)
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("🚀 完整全流程循环 (同步推进各阶段)", "full_chain")
        self.combo_mode.addItem("测试 NPC00 阶段起步", "npc00")
        self.combo_mode.addItem("测试 NPC01 阶段起步", "npc01")
        self.combo_mode.addItem("测试 NPC02 阶段起步", "npc02")
        self.combo_mode.addItem("测试 NPC03 阶段起步", "npc03")
        self.combo_mode.addItem("测试 NPC04 阶段起步", "npc04")
        self.combo_mode.addItem("测试 NPC04 返回 NPC00 起步", "return_npc00")
        layout.addWidget(self.combo_mode)

        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行轮数 (留空或填0表示无限循环):"))
        self.input_count = QLineEdit()
        self.input_count.setText("1")
        count_layout.addWidget(self.input_count)
        layout.addLayout(count_layout)

        btn_layout = QHBoxLayout()
        self.btn_arrange = QPushButton("📐 一键平铺并统一 1600x900")
        self.btn_arrange.clicked.connect(self.arrange_windows)
        btn_layout.addWidget(self.btn_arrange)

        self.btn_start = QPushButton("启动多窗口同步任务")
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止任务")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_action)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)
        layout.addWidget(QLabel("📜 实时运行日志："))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    def arrange_windows(self):
        if not self.hwnd_list:
            QMessageBox.warning(self, "排列提示", "尚未绑定任何多开游戏窗口！")
            return
        
        cols = 2 if len(self.hwnd_list) <= 4 else 3
        win_w, win_h = 1600, 900

        for index, hwnd in enumerate(self.hwnd_list):
            if win32gui.IsWindow(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                x = (index % cols) * win_w
                y = (index // cols) * win_h
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, win_w, win_h, win32con.SWP_SHOWWINDOW | win32con.SWP_NOZORDER)
        QMessageBox.information(self, "完成", f"已成功平铺并强制设置 {len(self.hwnd_list)} 个窗口分辨率为 1600x900！")

    def log(self, text): 
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if not self.hwnd_list:
            self.log("❌ 错误：未检测到绑定的多开窗口！")
            return
        if self.worker and self.worker.isRunning(): return
        
        count_text = self.input_count.text().strip()
        max_count = int(count_text) if count_text.isdigit() and int(count_text) > 0 else 1

        selected_mode = self.combo_mode.currentData()
        self.worker = TransportWorker(self.hwnd_list, test_mode=selected_mode, max_count=max_count)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_arrange.setEnabled(False)
        self.worker.start()

    def stop_action(self):
        if self.worker and self.worker.isRunning():
            self.log("🛑 正在请求停止多窗口任务...")
            self.worker.stop()

    def on_worker_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_arrange.setEnabled(True)