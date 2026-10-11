import os
import time
import subprocess
import pyautogui
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog)
from PySide6.QtCore import QThread, Signal

class MultiLoginWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, accounts_data):
        super().__init__()
        self.accounts_data = accounts_data  # 传入账号列表字典

    def run(self):
        self.log_signal.emit(f"🚀 开始执行多账号批量自动登录，总计 {len(self.accounts_data)} 个账号...")
        
        for index, acc in enumerate(self.accounts_data):
            game_path = acc['path']
            username = acc['user']
            password = acc['pwd']

            self.log_signal.emit(f"\n----------------------------------------")
            self.log_signal.emit(f"📌 正在处理第 {index + 1} 个账号: {username}")

            if not os.path.exists(game_path):
                self.log_signal.emit(f"❌ 错误：游戏路径不存在 -> {game_path}，跳过此账号。")
                continue

            try:
                self.log_signal.emit(f"🖥️ 正在启动游戏实例...")
                subprocess.Popen(game_path)
            except Exception as e:
                self.log_signal.emit(f"❌ 启动游戏进程失败: {e}")
                continue

            # 等待游戏加载界面出现
            load_wait = 6
            self.log_signal.emit(f"⏳ 等待 {load_wait} 秒以加载游戏登录界面...")
            time.sleep(load_wait)

            self.log_signal.emit(f"⌨️ 正在为账号 [{username}] 填入凭据并登录...")
            try:
                # 1. 输入账号
                pyautogui.write(username, interval=0.1)
                time.sleep(0.5)

                # 2. 切换密码框（按 Tab 键）
                pyautogui.press('tab')
                time.sleep(0.5)

                # 3. 输入密码
                pyautogui.write(password, interval=0.1)
                time.sleep(0.5)

                # 4. 回车登录
                pyautogui.press('enter')
                self.log_signal.emit(f"✅ 账号 [{username}] 登录指令发送完成！")
            except Exception as e:
                self.log_signal.emit(f"❌ 模拟键盘输入异常: {e}")

            # 多个账号依次启动时，每个账号之间留出缓冲时间，避免键鼠操作冲突
            if index < len(self.accounts_data) - 1:
                self.log_signal.emit("⏳ 等待 3 秒后准备启动下一个账号...")
                time.sleep(3)

        self.log_signal.emit("\n✨ 所有账号批量登录任务已执行完毕！")
        self.finished_signal.emit(True)

class AutoLoginModule(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("🔑 多开账号密码批量自动登录控制台 (支持多账号记录与依次唤起)"))

        # 表格：显示 游戏路径、账号、密码
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["游戏路径 (Path)", "账号 (Username)", "密码 (Password)"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # 表格操作按钮区
        tbl_btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("➕ 添加账号行")
        self.btn_add.clicked.connect(lambda: self.add_row())
        tbl_btn_layout.addWidget(self.btn_add)

        self.btn_delete = QPushButton("➖ 删除选中行")
        self.btn_delete.clicked.connect(self.delete_row)
        tbl_btn_layout.addWidget(self.btn_delete)
        
        self.btn_browse = QPushButton("📁 浏览选择游戏路径 (.exe)")
        self.btn_browse.clicked.connect(self.browse_path)
        tbl_btn_layout.addWidget(self.btn_browse)

        layout.addLayout(tbl_btn_layout)

        # 启动按钮
        self.btn_start = QPushButton("🟢 一键多开批量自动登录")
        self.btn_start.clicked.connect(self.start_multi_login)
        layout.addWidget(self.btn_start)

        # 日志输出框
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        # 默认添加一行示例
        self.add_row(r"C:\Program Files\YourGame\game.exe", "account_1", "password_1")

    def add_row(self, path="", user="", pwd=""):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(path))
        self.table.setItem(row_position, 1, QTableWidgetItem(user))
        self.table.setItem(row_position, 2, QTableWidgetItem(pwd))

    def delete_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
        else:
            QMessageBox.warning(self, "操作提示", "请先点击选中表格中的某一行再进行删除！")

    def browse_path(self):
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "操作提示", "请先点击选中表格中的某一行，再为其选择路径！")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "选择游戏可执行文件", "", "Executables (*.exe);;All Files (*.*)")
        if file_path:
            self.table.setItem(current_row, 0, QTableWidgetItem(file_path))

    def log(self, text):
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {text}")

    def start_multi_login(self):
        rows = self.table.rowCount()
        accounts_data = []

        for r in range(rows):
            item_path = self.table.item(r, 0)
            item_user = self.table.item(r, 1)
            item_pwd = self.table.item(r, 2)

            path = item_path.text().strip() if item_path else ""
            user = item_user.text().strip() if item_user else ""
            pwd = item_pwd.text().strip() if item_pwd else ""

            if path and user and pwd:
                accounts_data.append({'path': path, 'user': user, 'pwd': pwd})

        if not accounts_data:
            QMessageBox.warning(self, "数据不完整", "表格中没有检测到完整的账号、密码及游戏路径数据！")
            return

        self.btn_start.setEnabled(False)
        self.log("准备触发多账号批量登录线程...")

        self.worker = MultiLoginWorker(accounts_data)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, success):
        self.btn_start.setEnabled(True)