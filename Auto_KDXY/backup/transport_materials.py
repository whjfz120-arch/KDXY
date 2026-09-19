import os
import time
import random
import cv2
import numpy as np
import win32gui
import win32api
import win32con
import win32ui
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QComboBox, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal

class TransportWorker(QThread):
    log_signal = Signal(str)
    stats_signal = Signal(int)
    finished_signal = Signal()

    def __init__(self, hwnd, test_mode="full_chain", max_count=1, char_id="未知"):
        super().__init__()
        self.hwnd = hwnd
        self.char_id = char_id
        self.test_mode = test_mode      
        self.target_count = max_count   
        self._is_running = True
        self.reload_assets_config()

    def reload_assets_config(self):
        self.assets_dir = r"F:\script_test\assets"
        self.debug_dir = os.path.join(self.assets_dir, "debug")
        os.makedirs(self.debug_dir, exist_ok=True)
        
        self.template_scrollbar  = os.path.join(self.assets_dir, "scrollbar.png")
        self.template_arrow_up   = os.path.join(self.assets_dir, "arrow_up.png")
        self.template_arrow_down = os.path.join(self.assets_dir, "arrow_down.png")
        self.accept_btn_path     = os.path.join(self.assets_dir, "accept_quest.png")
        self.quest_level_path    = os.path.join(self.assets_dir, "quest_level.png")
        self.npc_level_1_path    = os.path.join(self.assets_dir, "npc_level_1.png") 
        self.npc_level_2_path    = os.path.join(self.assets_dir, "npc_level_2.png") 
        
        # NPC00 相关资源
        self.npc_00_pos_path        = os.path.join(self.assets_dir, "npc00_pos.png")
        self.npc_level_0_head_path  = os.path.join(self.assets_dir, "npc_level_0_head.png")

        # NPC03 相关资源
        self.npc_03_pos_path           = os.path.join(self.assets_dir, "npc03_pos.png")
        self.npc_level_3_head_path     = os.path.join(self.assets_dir, "npc_level_3_head.png")
        self.task_dingguo_main01_path  = os.path.join(self.assets_dir, "task_dingguo_main01.png")
        
        # NPC04 相关资源
        self.npc_04_pos_path           = os.path.join(self.assets_dir, "npc04_pos.png")
        self.npc_level_4_head_path     = os.path.join(self.assets_dir, "npc_level_4_head.png")
        
        self.quest_related_path        = os.path.join(self.assets_dir, "quest_related.png")
        self.task_related_template_path = os.path.join(self.assets_dir, "task_related_template.png")
        
        self.task_related_paths = [
            self.quest_related_path,
            self.task_related_template_path
        ]

        self.task_dingguo_paths   = [
            os.path.join(self.assets_dir, "task_dingguo_main.png"),
            self.task_dingguo_main01_path
        ]
        
        # 确认按钮多资源路径配置
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
            self.log_signal.emit("❌ 错误：未绑定有效游戏窗口！")
            self.finished_signal.emit()
            return

        self.log_signal.emit(f"🚀 开始执行任务 | 模式: {self.test_mode} | 角色: {self.char_id} | 目标轮数: {self.target_count if self.target_count else '无限循环'}")
        completed_count = 0
        
        while self._is_running:
            self.reload_assets_config()
            if self.target_count is not None and completed_count >= self.target_count:
                self.log_signal.emit(f"🎯 已达到设定的目标轮数 ({self.target_count} 轮)，任务顺利完成！")
                break
                
            completed_count += 1
            self.log_signal.emit(f"--- 🔄 开始第 {completed_count} 轮循环 ---")
            
            win_rect = self.get_window_rect()
            if not win_rect: 
                self.log_signal.emit("❌ 错误：无法获取窗口矩形位置！")
                break

            success = True
            if self.test_mode == "full_chain":
                success = self.run_full_chain_workflow(win_rect)
            elif self.test_mode == "npc00":
                success = self.run_npc00_step(win_rect)
            elif self.test_mode == "npc01":
                success = self.run_npc01_step(win_rect)
            elif self.test_mode == "npc02":
                success = self.run_npc02_step(win_rect)
            elif self.test_mode == "npc03":
                success = self.run_npc03_step(win_rect)
            elif self.test_mode == "npc04":
                success = self.run_npc04_step(win_rect)
            elif self.test_mode == "return_npc00":
                success = self.run_return_npc00_step(win_rect)

            if not self._is_running:
                self.log_signal.emit("🛑 收到停止指令，正在安全退出循环...")
                break

            if success:
                self.log_signal.emit(f"✅ 第 {completed_count} 轮循环执行成功！")
                self.stats_signal.emit(completed_count)
            else:
                self.log_signal.emit(f"❌ 第 {completed_count} 轮循环执行失败或中断。")
                break
            
            if self.test_mode != "full_chain":
                # 如果是单项测试模式，单次执行完即可退出
                break
            
            # 轮次间短暂间隔
            if not self.interruptible_sleep(1.0):
                break
            
        self.log_signal.emit("🏁 任务线程已安全退出。")
        self.finished_signal.emit()

    def run_full_chain_workflow(self, win_rect):
        """串联完整全流程：NPC00 -> 2s -> NPC01 -> 2s -> NPC02 -> 2s -> NPC03 -> 2s -> NPC04 -> 2s -> 返回NPC00 -> 2s"""
        self.log_signal.emit("📍 [全流程] 执行阶段 1/6: NPC00")
        if not self.run_npc00_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        self.log_signal.emit("📍 [全流程] 执行阶段 2/6: NPC01")
        if not self.run_npc01_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        self.log_signal.emit("📍 [全流程] 执行阶段 3/6: NPC02")
        if not self.run_npc02_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        self.log_signal.emit("📍 [全流程] 执行阶段 4/6: NPC03")
        if not self.run_npc03_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        self.log_signal.emit("📍 [全流程] 执行阶段 5/6: NPC04")
        if not self.run_npc04_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        self.log_signal.emit("📍 [全流程] 执行阶段 6/6: NPC04 返回 NPC00")
        if not self.run_return_npc00_step(win_rect): return False
        if not self.interruptible_sleep(2.0): return False

        return True

    def run_npc00_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC00 阶段]：按下 M 键打开地图...")
        self.press_key(0x4D)
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC00 阶段]：正在全局查找 NPC00 地图位置 (npc00_pos, 置信度 >= 0.7) 并准备双击...")
        if not self.wait_and_double_click(win_rect, self.npc_00_pos_path, "NPC00地图位置", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在地图中找到 NPC00 位置 (npc00_pos)")
            self.press_key(0x4D)
            return False
            
        self.log_signal.emit("⏳ 已双击 NPC00 位置，等待 0.5 秒...")
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC00 阶段]：按下 M 键关闭地图...")
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 开始等待最小 3 秒钟...")
        start_wait = time.time()
        while time.time() - start_wait < 3.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("📌 [NPC00 阶段]：开始查找 NPC0 头部图标 (置信度 >= 0.55，最大等待 120 秒)...")
        pos = self.wait_to_find_pos(win_rect, self.npc_level_0_head_path, "NPC0头部图标", timeout=120, confidence=0.55)
        if not pos:
            self.log_signal.emit("❌ 未能在规定时间内找到 NPC0 头部图标")
            return False

        self.log_signal.emit("⏳ 找到 NPC0 头部图标，等待 0.5 秒...")
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC00 阶段]：按下 S 键停止角色移动...")
        self.press_key(0x53)
        time.sleep(0.5)

        self.log_signal.emit(f"🎯 双击 NPC0 头部图标坐标: {pos}...")
        self.win32_double_click(pos[0], pos[1])
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC00 阶段]：正在全局查找并点击定国安邦任务 (task_dingguo_main.png，置信度 >= 0.7)...")
        return self.wait_and_click_task_dingguo(win_rect, timeout=10)

    def run_npc01_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC01 阶段]：按下 Q 键打开面板...")
        self.press_key(0x51)
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC01 阶段]：正在全局查找并点击关卡选项 (quest_level, 置信度 >= 0.7)...")
        if not self.wait_and_click(win_rect, self.quest_level_path, "关卡", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在全局找到关卡选项")
            return False
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC01 阶段]：正在全局查找并双击 npc_level_1.png (置信度 >= 0.7)...")
        if not self.wait_and_double_click(win_rect, self.npc_level_1_path, "关卡·一", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在全局找到 npc_level_1.png")
            return False
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC01 阶段]：按下 Q 键关闭面板...")
        self.press_key(0x51)
        time.sleep(0.5)
        
        self.log_signal.emit("⏳ 开始等待最小 15 秒钟...")
        start_wait = time.time()
        while time.time() - start_wait < 15.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("📌 [NPC01 阶段]：开始查找并点击任务相关 (quest_related.png，最大等待 120 秒)...")
        if not self.wait_and_click_task_related(win_rect, timeout=120):
            self.log_signal.emit("❌ 未能在规定时间内找到任务相关图标")
            return False
            
        self.log_signal.emit("⏳ 点击任务相关成功，等待 1 秒...")
        time.sleep(1.0)
        
        self.log_signal.emit("📌 [NPC01 阶段]：正在全局查找并点击定国安邦任务 (task_dingguo_main.png)...")
        if not self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在规定时间内找到定国安邦任务图标")
            return False
            
        self.log_signal.emit("⏳ 点击定国安邦任务成功，等待 1 秒...")
        time.sleep(1.0)
        
        self.log_signal.emit("📌 [NPC01 阶段]：正在等待并点击确认按钮...")
        return self.click_confirm(win_rect, timeout=10)

    def run_npc02_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC02 阶段]：按下 Q 键打开面板...")
        self.press_key(0x51)
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC02 阶段]：正在全局查找并点击关卡选项 (quest_level, 置信度 >= 0.7)...")
        if not self.wait_and_click(win_rect, self.quest_level_path, "关卡", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在全局找到关卡选项")
            return False
        
        self.log_signal.emit("⏳ 点击关卡成功，等待 0.5 秒...")
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC02 阶段]：正在全局查找并双击 npc_level_2.png (关卡·二，置信度 >= 0.7)...")
        if not self.wait_and_double_click(win_rect, self.npc_level_2_path, "关卡·二", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在全局找到 npc_level_2.png")
            return False
        
        self.log_signal.emit("⏳ 双击关卡二成功，等待 1 秒...")
        time.sleep(1.0)
        
        self.log_signal.emit("📌 [NPC02 阶段]：按下 Q 键关闭面板...")
        self.press_key(0x51)
        time.sleep(0.5)
        
        self.log_signal.emit("⏳ 开始等待最小 20 秒钟...")
        start_wait = time.time()
        while time.time() - start_wait < 20.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("📌 [NPC02 阶段]：开始查找并点击定国安邦任务 (最大等待 120 秒)...")
        if not self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=120, confidence=0.7):
            self.log_signal.emit("❌ 未能在规定时间内找到定国安邦任务图标")
            return False
            
        self.log_signal.emit("⏳ 点击定国安邦任务成功，等待 1 秒...")
        time.sleep(1.0)
        
        self.log_signal.emit("📌 [NPC02 阶段]：正在等待并点击确认按钮...")
        return self.click_confirm(win_rect, timeout=10)

    def run_npc03_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC03 阶段]：按下 M 键打开小地图...")
        self.press_key(0x4D)
        time.sleep(0.8)
        
        self.log_signal.emit("📌 [NPC03 阶段]：正在全局查找 NPC03 地图位置 (npc03_pos, 置信度 >= 0.7) 并准备双击...")
        if not self.wait_and_double_click(win_rect, self.npc_03_pos_path, "NPC03地图位置", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在地图中找到 NPC03 位置 (npc03_pos)")
            self.press_key(0x4D)
            return False
            
        self.log_signal.emit("⏳ 已双击 NPC03 位置，等待 0.5 秒...")
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC03 阶段]：按下 M 键关闭地图...")
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 开始等待最小 45 秒钟...")
        start_wait = time.time()
        while time.time() - start_wait < 45.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("📌 [NPC03 阶段]：开始查找 NPC 头部图标 (置信度 >= 0.7，最大等待 120 秒)...")
        if not self.wait_and_double_click(win_rect, self.npc_level_3_head_path, "NPC头部图标", timeout=120, confidence=0.7):
            self.log_signal.emit("❌ 未能在规定时间内找到 NPC 头部图标")
            return False

        self.log_signal.emit("⏳ 双击 NPC 头部图标成功，等待 0.3 秒...")
        time.sleep(0.3)

        self.log_signal.emit("📌 [NPC03 阶段]：正在全局查找并点击 task_dingguo_main01.png (置信度 >= 0.7)...")
        if not self.wait_and_click(win_rect, self.task_dingguo_main01_path, "定国安邦主选项01", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在规定时间内找到 task_dingguo_main01.png")
            return False

        self.log_signal.emit("📌 [NPC03 阶段]：正在等待并点击确认按钮 (置信度 >= 0.7)...")
        time.sleep(0.5)
        return self.click_confirm(win_rect, timeout=10)

    def run_npc04_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC04 阶段]：按下 M 键打开地图...")
        self.press_key(0x4D)
        time.sleep(0.8)
        
        self.log_signal.emit("📌 [NPC04 阶段]：正在全局查找 NPC04 地图位置 (npc04_pos, 置信度 >= 0.7) 并准备双击...")
        if not self.wait_and_double_click(win_rect, self.npc_04_pos_path, "NPC04地图位置", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在地图中找到 NPC04 位置 (npc04_pos)")
            self.press_key(0x4D)
            return False
            
        self.log_signal.emit("⏳ 已双击 NPC04 位置，等待 0.3 秒...")
        time.sleep(0.3)

        self.log_signal.emit("📌 [NPC04 阶段]：按下 M 键关闭地图...")
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 开始等待最小 45 秒钟...")
        start_wait = time.time()
        while time.time() - start_wait < 45.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("📌 [NPC04 阶段]：开始查找 NPC4 头部图标 (置信度 >= 0.62，最大等待 120 秒)...")
        pos = self.wait_to_find_pos(win_rect, self.npc_level_4_head_path, "NPC4头部图标", timeout=120, confidence=0.62)
        if not pos:
            self.log_signal.emit("❌ 未能在规定时间内找到 NPC4 头部图标")
            return False

        self.log_signal.emit("⏳ 找到 NPC4 头部图标，等待 0.3 秒...")
        time.sleep(0.3)

        self.log_signal.emit("📌 [NPC04 阶段]：按下 S 键停止角色移动...")
        self.press_key(0x53)
        time.sleep(0.3)

        self.log_signal.emit(f"🎯 双击 NPC4 头部图标坐标: {pos}...")
        self.win32_double_click(pos[0], pos[1])
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC04 阶段]：正在全局查找并点击任务相关 (置信度 >= 0.7)...")
        if not self.wait_and_click_task_related(win_rect, timeout=10):
            self.log_signal.emit("❌ 未能找到任务相关图标")
            return False
        time.sleep(0.5)

        self.log_signal.emit("📌 [NPC04 阶段]：正在全局查找并点击定国安邦任务 (置信度 >= 0.7)...")
        return self.wait_and_click_task_dingguo(win_rect, timeout=10)

    def run_return_npc00_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [返回NPC00独立流程]：按下 M 键打开小地图...")
        self.press_key(0x4D)
        time.sleep(1.0)
        
        self.log_signal.emit("📌 [返回NPC00独立流程]：正在全局查找 npc00_pos.png 并准备双击...")
        if not self.wait_and_double_click(win_rect, self.npc_00_pos_path, "NPC00地图位置(返回)", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在地图中找到 NPC00 位置 (npc00_pos)")
            self.press_key(0x4D)
            return False
            
        self.log_signal.emit("⏳ 已双击 NPC00 位置，等待 1 秒...")
        time.sleep(1.0)

        self.log_signal.emit("📌 [返回NPC00独立流程]：按下 M 键关闭小地图...")
        self.press_key(0x4D)
        time.sleep(0.5)

        wait_sec = random.randint(140, 160)
        self.log_signal.emit(f"⏳ 开始等待返回 NPC00 延迟，随机设定为 {wait_sec} 秒 (范围140-160秒)...")
        start_wait = time.time()
        while time.time() - start_wait < wait_sec:
            if not self._is_running: return False
            time.sleep(0.1)
            
        self.log_signal.emit("✅ 返回 NPC00 独立流程执行完毕。")
        return True

    def wait_and_click_task_related(self, win_rect, timeout=10):
        return self.wait_and_click_multi(win_rect, self.task_related_paths, "任务相关", timeout=timeout, confidence=0.7)

    def wait_and_click_task_dingguo(self, win_rect, timeout=10):
        if not self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=timeout, confidence=0.7):
            return False
        time.sleep(0.5)
        return self.click_confirm(win_rect, timeout=10)

    def get_window_rect(self):
        try:
            rect = win32gui.GetWindowRect(self.hwnd)
            return {'x': rect[0], 'y': rect[1], 'w': rect[2] - rect[0], 'h': rect[3] - rect[1]}
        except: return None

    def activate_window(self):
        try:
            if win32gui.IsIconic(self.hwnd): win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
        except: pass

    def press_key(self, vk):
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(0.03)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def win32_click(self, x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def win32_double_click(self, x, y):
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
        except: return None

    def find_template(self, win_rect, path, confidence=0.5, name=""):
        if not os.path.exists(path):
            self.log_signal.emit(f"⚠️ 资源文件不存在: {os.path.basename(path)}")
            return None
        screen = self.capture_screen_region(win_rect['x'], win_rect['y'], win_rect['w'], win_rect['h'])
        if screen is None: return None
        template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if template is None: return None
        
        res = cv2.matchTemplate(cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        debug_img = screen.copy()
        th, tw = template.shape[:2]
        is_ok = max_val >= confidence
        color = (0, 255, 0) if is_ok else (0, 0, 255)
        cv2.rectangle(debug_img, max_loc, (max_loc[0] + tw, max_loc[1] + th), color, 2)
        text = f"{name}: {max_val:.2f} ({'OK' if is_ok else 'FAIL'})"
        cv2.putText(debug_img, text, (max_loc[0], max_loc[1] - 8 if max_loc[1] > 20 else max_loc[1] + th + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        debug_filename = os.path.join(self.debug_dir, f"debug_{name}_{int(time.time()*1000)}.png")
        cv2.imwrite(debug_filename, debug_img)
        self.log_signal.emit(f"📷 [Debug] 全局查找保存: {os.path.basename(debug_filename)} | 目标: {name} | 得分: {max_val:.2f}")

        if is_ok:
            return win_rect['x'] + max_loc[0] + tw//2, win_rect['y'] + max_loc[1] + th//2
        return None

    def wait_and_click_multi(self, win_rect, paths, name, timeout=10, confidence=0.75):
        start = time.time()
        self.log_signal.emit(f"🔍 正在全局多路径寻找目标: [{name}] (置信度阈值: {confidence})...")
        if not isinstance(paths, list):
            paths = [paths]
        while time.time() - start < timeout:
            if not self._is_running: return False
            for p in paths:
                pos = self.find_template(win_rect, p, confidence=confidence, name=name)
                if pos:
                    self.log_signal.emit(f"✅ 在全局找到目标 [{name}]，坐标: {pos}，点击！")
                    self.win32_click(pos[0], pos[1])
                    return True
            time.sleep(0.5)
        self.log_signal.emit(f"⏰ 在全局多路径寻找目标 [{name}] 超时 ({timeout}秒)")
        return False

    def wait_and_click(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        self.log_signal.emit(f"🔍 正在寻找目标: [{name}] (置信度: {confidence})...")
        while time.time() - start < timeout:
            if not self._is_running: return False
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos:
                self.log_signal.emit(f"✅ 找到目标 [{name}]，坐标: {pos}，点击！")
                self.win32_click(pos[0], pos[1])
                return True
            time.sleep(0.5)
        self.log_signal.emit(f"⏰ 寻找目标 [{name}] 超时 ({timeout}秒)")
        return False

    def wait_to_find_pos(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        self.log_signal.emit(f"🔍 正在寻找目标: [{name}] (置信度: {confidence})...")
        while time.time() - start < timeout:
            if not self._is_running: return None
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos:
                self.log_signal.emit(f"✅ 找到目标 [{name}]，坐标: {pos}")
                return pos
            time.sleep(0.5)
        self.log_signal.emit(f"⏰ 寻找目标 [{name}] 超时 ({timeout}秒)")
        return None

    def wait_and_double_click(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        self.log_signal.emit(f"🔍 正在全局寻找目标: [{name}] 并准备双击 (置信度阈值: {confidence}, 超时: {timeout}秒)...")
        while time.time() - start < timeout:
            if not self._is_running: return False
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos:
                self.log_signal.emit(f"✅ 找到目标 [{name}]，坐标: {pos}，执行双击！")
                self.win32_double_click(pos[0], pos[1])
                return True
            time.sleep(0.5)
        self.log_signal.emit(f"⏰ 寻找目标 [{name}] 超时 ({timeout}秒)")
        return False

    def click_confirm(self, win_rect, timeout=10):
        return self.wait_and_click_multi(win_rect, self.btn_confirm_paths, "确认按钮", timeout=timeout, confidence=0.7)


class TransportModule(QWidget):
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
        layout.addWidget(QLabel("📦 运送物资任务控制台 (支持全流程串联与独立子功能测试)"))
        
        # 运行模式选择
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("🚀 完整全流程循环 (NPC00->NPC01->NPC02->NPC03->NPC04->返回NPC00)", "full_chain")
        self.combo_mode.addItem("测试 NPC00 阶段", "npc00")
        self.combo_mode.addItem("测试 NPC01 阶段", "npc01")
        self.combo_mode.addItem("测试 NPC02 阶段", "npc02")
        self.combo_mode.addItem("测试 NPC03 阶段 (45秒延迟)", "npc03")
        self.combo_mode.addItem("测试 NPC04 阶段", "npc04")
        self.combo_mode.addItem("测试 NPC04 返回 NPC00 独立流程", "return_npc00")
        layout.addWidget(self.combo_mode)

        # 循环次数输入框
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行轮数 (留空或填0表示无限循环):"))
        self.input_count = QLineEdit()
        self.input_count.setPlaceholderText("例如: 5")
        self.input_count.setText("1")  # 默认1轮，安全起见
        count_layout.addWidget(self.input_count)
        layout.addLayout(count_layout)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("启动任务")
        self.btn_start.clicked.connect(self.start_action)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止任务")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_action)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)

        log_label_layout = QHBoxLayout()
        log_label_layout.addWidget(QLabel("📜 实时运行日志："))
        layout.addLayout(log_label_layout)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(250)
        layout.addWidget(self.log_box)
        layout.setStretch(layout.indexOf(self.log_box), 1)

    def log(self, text): 
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if self.worker and self.worker.isRunning(): 
            return
        
        # 解析输入的轮数
        count_text = self.input_count.text().strip()
        max_count = None
        if count_text.isdigit():
            val = int(count_text)
            if val > 0:
                max_count = val

        selected_mode = self.combo_mode.currentData()
        self.worker = TransportWorker(self.bound_hwnd, test_mode=selected_mode, max_count=max_count, char_id=self.bound_char_id)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.worker.start()

    def stop_action(self):
        if self.worker and self.worker.isRunning():
            self.log("🛑 正在请求停止任务...")
            self.worker.stop()

    def on_worker_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
