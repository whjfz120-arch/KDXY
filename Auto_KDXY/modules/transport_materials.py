from pathlib import Path
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
                             QPushButton, QTextEdit, QComboBox, QLineEdit, QGroupBox)
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
        
        # 📌 核心 NPC 坐标配置点
        self.NPC_00_COORD = (-60, 173)
        self.NPC_03_COORD = (396, 293)
        self.NPC_04_COORD = (307, 102)
        
        self.reload_assets_config()

    def reload_assets_config(self):
        # 使用 pathlib 动态获取当前脚本所在目录，实现盘符解耦
        base_dir = Path(__file__).resolve().parent.parent
        self.assets_dir = str(base_dir / "assets")
        
        # ==========================================
        # [已注释] 取消 debug 截图文件夹的创建逻辑
        # self.debug_dir = os.path.join(self.assets_dir, "debug")
        # os.makedirs(self.debug_dir, exist_ok=True)
        # ==========================================
        
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
        self.log_signal.emit(f"📌 已加载NPC坐标点 -> NPC00: {self.NPC_00_COORD} | NPC03: {self.NPC_03_COORD} | NPC04: {self.NPC_04_COORD}")
        
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
                break
            
            if not self.interruptible_sleep(1.0):
                break
            
        self.log_signal.emit("🏁 任务线程已安全退出。")
        self.finished_signal.emit()

    def run_full_chain_workflow(self, win_rect):
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
        self.log_signal.emit(f"📌 [NPC00 阶段] 坐标 {self.NPC_00_COORD}：按下 M 键打开地图...")
        self.press_key(0x4D)
        time.sleep(0.5)
        
        self.log_signal.emit("📌 [NPC00 阶段]：正在全局查找 NPC00 地图位置 (npc00_pos)...")
        if not self.wait_and_double_click(win_rect, self.npc_00_pos_path, "NPC00地图位置", timeout=10, confidence=0.7):
            self.log_signal.emit("❌ 未能在地图中找到 NPC00 位置 (npc00_pos)")
            self.press_key(0x4D)
            return False
            
        time.sleep(0.5)
        self.log_signal.emit("📌 [NPC00 阶段]：按下 M 键关闭地图...")
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 等待移动中 (最小 3 秒)...")
        start_wait = time.time()
        while time.time() - start_wait < 3.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        # ==================== 🛠️ 详细 DEBUG 改动区域 ====================
        self.log_signal.emit("📌 [NPC00 阶段]：开始循环查找 NPC0 头部图标 (带 Debug)...")
        
        target_path = self.npc_level_0_head_path
        timeout = 120
        confidence_threshold = 0.5
        
        start_time = time.time()
        attempt_count = 0
        max_seen_val = 0.0  # 记录整个过程中的最高相似度
        
        pos = None
        while time.time() - start_time < timeout:
            if not self._is_running: 
                return False
            
            attempt_count += 1
            
            # 1. 检查文件是否存在
            if not os.path.exists(target_path):
                self.log_signal.emit(f"❌ [DEBUG 错误] 模板文件不存在: {target_path}")
                break
                
            # 2. 截取游戏画面
            screen = self.capture_screen_region(win_rect['x'], win_rect['y'], win_rect['w'], win_rect['h'])
            if screen is None:
                self.log_signal.emit("⚠️ [DEBUG 警告] 截图失败，窗口可能最小化或无效")
                time.sleep(1.0)
                continue
                
            # 3. 读取模板
            template = cv2.imread(target_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                self.log_signal.emit(f"❌ [DEBUG 错误] 无法读取模板图片: {target_path}")
                break
                
            # 4. 模板匹配计算
            screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            
            # 更新历史最高相似度
            if max_val > max_seen_val:
                max_seen_val = max_val
                
            # 每尝试 5 次（约 2.5 秒）打印一次当前的匹配进度日志，避免日志刷屏
            if attempt_count % 5 == 0:
                self.log_signal.emit(f"🔍 [DEBUG 轮询 #{attempt_count}] 当前最高相似度: {max_val:.4f} (要求阈值: {confidence_threshold})")
            
            # 5. 判断是否达标
            if max_val >= confidence_threshold:
                pos = (win_rect['x'] + max_loc[0] + template.shape[1]//2, 
                       win_rect['y'] + max_loc[1] + template.shape[0]//2)
                self.log_signal.emit(f"✅ [DEBUG 成功] 找到 NPC0 头部图标！坐标: {pos}, 最终相似度: {max_val:.4f}")
                break
                
            time.sleep(0.5)
            
        if not pos:
            self.log_signal.emit(f"❌ [NPC00 阶段] 查找 NPC0 头部图标超时！整个过程中的【历史最高相似度】仅为: {max_seen_val:.4f}")
            self.log_signal.emit("💡 排查建议：1. 检查游戏内该 NPC 头顶图标是否被遮挡；2. 适当调低 confidence 阈值（当前为 0.7）；3. 检查模板图片是否标准。")
            return False
        # ==============================================================

        time.sleep(0.5)
        self.press_key(0x53) # 停止移动
        time.sleep(0.5)

        self.log_signal.emit(f"🎯 双击 NPC0 头部图标坐标: {pos}...")
        self.win32_double_click(pos[0], pos[1])
        time.sleep(0.5)

        return self.wait_and_click_task_dingguo(win_rect, timeout=10)

    def run_npc01_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit("📌 [NPC01 阶段]：按下 Q 键打开面板...")
        self.press_key(0x51)
        time.sleep(0.5)
        
        if not self.wait_and_click(win_rect, self.quest_level_path, "关卡", timeout=10, confidence=0.7):
            return False
        time.sleep(0.5)
        
        if not self.wait_and_double_click(win_rect, self.npc_level_1_path, "关卡·一", timeout=10, confidence=0.7):
            return False
        time.sleep(0.5)
        
        self.press_key(0x51)
        time.sleep(0.5)
        
        start_wait = time.time()
        while time.time() - start_wait < 10.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        if not self.wait_and_click_task_related(win_rect, timeout=120):
            return False
        time.sleep(1.0)
        
        if not self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=10, confidence=0.7):
            return False
        time.sleep(1.0)
        
        return self.click_confirm(win_rect, timeout=10)

    def run_npc02_step(self, win_rect):
        self.activate_window()
        self.press_key(0x51)
        time.sleep(0.5)
        
        if not self.wait_and_click(win_rect, self.quest_level_path, "关卡", timeout=10, confidence=0.7):
            return False
        time.sleep(0.5)
        
        if not self.wait_and_double_click(win_rect, self.npc_level_2_path, "关卡·二", timeout=10, confidence=0.7):
            return False
        time.sleep(1.0)
        
        self.press_key(0x51)
        time.sleep(0.5)
        
        start_wait = time.time()
        while time.time() - start_wait < 10.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        if not self.wait_and_click_multi(win_rect, self.task_dingguo_paths, "定国安邦任务", timeout=120, confidence=0.7):
            return False
        time.sleep(1.0)
        
        return self.click_confirm(win_rect, timeout=10)

    def run_npc03_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit(f"📌 [NPC03 阶段] 坐标 {self.NPC_03_COORD}：按下 M 键打开小地图...")
        self.press_key(0x4D)
        time.sleep(0.8)
        
        if not self.wait_and_double_click(win_rect, self.npc_03_pos_path, "NPC03地图位置", timeout=10, confidence=0.7):
            self.press_key(0x4D)
            return False
            
        time.sleep(0.5)
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 等待移动中 (45秒)...")
        start_wait = time.time()
        while time.time() - start_wait < 45.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        if not self.wait_and_double_click(win_rect, self.npc_level_3_head_path, "NPC头部图标", timeout=120, confidence=0.7):
            return False

        time.sleep(0.3)
        return self.wait_and_click(win_rect, self.task_dingguo_main01_path, "定国安邦主选项01", timeout=10, confidence=0.7) and self.click_confirm(win_rect, timeout=10)

    def run_npc04_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit(f"📌 [NPC04 阶段] 坐标 {self.NPC_04_COORD}：按下 M 键打开地图...")
        self.press_key(0x4D)
        time.sleep(0.8)
        
        if not self.wait_and_double_click(win_rect, self.npc_04_pos_path, "NPC04地图位置", timeout=10, confidence=0.7):
            self.press_key(0x4D)
            return False
            
        time.sleep(0.3)
        self.press_key(0x4D)
        time.sleep(0.5)

        self.log_signal.emit("⏳ 等待移动中 (45秒)...")
        start_wait = time.time()
        while time.time() - start_wait < 45.0:
            if not self._is_running: return False
            time.sleep(0.1)
            
        pos = self.wait_to_find_pos(win_rect, self.npc_level_4_head_path, "NPC4头部图标", timeout=120, confidence=0.65)
        if not pos:
            return False

        time.sleep(0.3)
        self.press_key(0x53)
        time.sleep(0.3)

        self.win32_double_click(pos[0], pos[1])
        time.sleep(0.5)

        if not self.wait_and_click_task_related(win_rect, timeout=10):
            return False
        time.sleep(0.5)

        return self.wait_and_click_task_dingguo(win_rect, timeout=10)

    def run_return_npc00_step(self, win_rect):
        self.activate_window()
        self.log_signal.emit(f"📌 [返回NPC00] 目标坐标 {self.NPC_00_COORD}：打开小地图并寻路...")
        self.press_key(0x4D)
        time.sleep(1.0)
        
        if not self.wait_and_double_click(win_rect, self.npc_00_pos_path, "NPC00地图位置(返回)", timeout=10, confidence=0.7):
            self.press_key(0x4D)
            return False
            
        time.sleep(1.0)
        self.press_key(0x4D)
        time.sleep(0.5)

        wait_sec = random.randint(140, 160)
        self.log_signal.emit(f"⏳ 等待返回路上，随机延迟 {wait_sec} 秒...")
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
            return None
        screen = self.capture_screen_region(win_rect['x'], win_rect['y'], win_rect['w'], win_rect['h'])
        if screen is None: return None
        template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if template is None: return None
        
        res = cv2.matchTemplate(cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY), template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        is_ok = max_val >= confidence
        if is_ok:
            return win_rect['x'] + max_loc[0] + template.shape[1]//2, win_rect['y'] + max_loc[1] + template.shape[0]//2
        return None

    def wait_and_click_multi(self, win_rect, paths, name, timeout=10, confidence=0.75):
        start = time.time()
        if not isinstance(paths, list): paths = [paths]
        while time.time() - start < timeout:
            if not self._is_running: return False
            for p in paths:
                pos = self.find_template(win_rect, p, confidence=confidence, name=name)
                if pos:
                    self.win32_click(pos[0], pos[1])
                    return True
            time.sleep(0.5)
        return False

    def wait_and_click(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        while time.time() - start < timeout:
            if not self._is_running: return False
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos:
                self.win32_click(pos[0], pos[1])
                return True
            time.sleep(0.5)
        return False

    def wait_to_find_pos(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        while time.time() - start < timeout:
            if not self._is_running: return None
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos: return pos
            time.sleep(0.5)
        return None

    def wait_and_double_click(self, win_rect, path, name, timeout=10, confidence=0.5):
        start = time.time()
        while time.time() - start < timeout:
            if not self._is_running: return False
            pos = self.find_template(win_rect, path, confidence=confidence, name=name)
            if pos:
                self.win32_double_click(pos[0], pos[1])
                return True
            time.sleep(0.5)
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
        layout.addWidget(QLabel("📦 运送物资任务控制台"))
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("🚀 完整全流程循环 (NPC00->NPC01->NPC02->NPC03->NPC04->返回NPC00)", "full_chain")
        self.combo_mode.addItem("测试 NPC00 阶段", "npc00")
        self.combo_mode.addItem("测试 NPC01 阶段", "npc01")
        self.combo_mode.addItem("测试 NPC02 阶段", "npc02")
        self.combo_mode.addItem("测试 NPC03 阶段 (45秒延迟)", "npc03")
        self.combo_mode.addItem("测试 NPC04 阶段", "npc04")
        self.combo_mode.addItem("测试 NPC04 返回 NPC00 独立流程", "return_npc00")
        layout.addWidget(self.combo_mode)

        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("执行轮数 (留空或填0表示无限循环):"))
        self.input_count = QLineEdit()
        self.input_count.setPlaceholderText("例如: 5")
        self.input_count.setText("1")
        count_layout.addWidget(self.input_count)
        layout.addLayout(count_layout)

        # 📌 在界面空处新增 NPC 坐标参考面板
        coord_group = QGroupBox("📌 核心 NPC 坐标参考")
        coord_layout = QVBoxLayout(coord_group)
        coord_layout.addWidget(QLabel("• NPC00: -60, 173"))
        coord_layout.addWidget(QLabel("• NPC03: 396, 293"))
        coord_layout.addWidget(QLabel("• NPC04: 307, 120"))
        layout.addWidget(coord_group)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("启动任务")
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
        self.log_box.setMinimumHeight(200)
        layout.addWidget(self.log_box)
        layout.setStretch(layout.indexOf(self.log_box), 1)

    def log(self, text): 
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_action(self):
        if self.worker and self.worker.isRunning(): return
        
        count_text = self.input_count.text().strip()
        max_count = None
        if count_text.isdigit():
            val = int(count_text)
            if val > 0: max_count = val

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
