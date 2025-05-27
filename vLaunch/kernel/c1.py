import sys
import os
import psutil
import time
import cv2
import random
import shutil
import importlib.util
import zipfile
import platform
import getpass
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy, QMenu, QAction, QToolBar, QLineEdit, QListWidget, QStackedWidget, QMenuBar, QDialog, QMessageBox, QFileDialog, QPlainTextEdit, QListWidgetItem, QTabWidget, QInputDialog, QScrollArea, QGridLayout, QDesktopWidget
)
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QDateTime, QUrl, QPropertyAnimation, QRect, QObject
from PyQt5.QtGui import QPixmap, QImage, QCursor, QPainter, QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
import subprocess
import webbrowser
import requests

class CustomTitleBar(QWidget):
    def __init__(self, parent, window):
        super().__init__(parent)
        self.window = window
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: black; color: white;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(window.windowTitle(), self)
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        minimize_button = QPushButton("_", self)
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        layout.addWidget(minimize_button)

        maximize_button = QPushButton("□", self)
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(self.toggle_maximize_restore)
        layout.addWidget(maximize_button)

        close_button = QPushButton("X", self)
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white; border-radius: 2px;")
        close_button.clicked.connect(window.close)
        layout.addWidget(close_button)

        self.old_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.window.move(self.window.pos() + delta)
            self.old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = None

    def toggle_maximize_restore(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()


class AppWindow(QMainWindow):
    def __init__(self, app_name, close_callback):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle(app_name)
        self.setGeometry(300, 200, 600, 400)
        self.close_callback = close_callback

        self.setStyleSheet("border: 2px solid black; background-color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        title_bar = CustomTitleBar(self, self)
        layout.addWidget(title_bar)

        label = QLabel(f"{self.windowTitle()} Window", self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    def closeEvent(self, event):
        self.close_callback(self)
        event.accept()

class LockScreen(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lock Screen")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.background_label = QLabel(self.central_widget)
        self.setup_background()

        self.time_label = QLabel(self.central_widget)
        self.time_label.setStyleSheet("color: white; font-size: 48px; background-color: rgba(0, 0, 0, 50);")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.update_time()
        self.randomize_time_position()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.randomize_time_position)
        self.timer.start(10000)

        self.swipe_arrow = QLabel(self.central_widget)
        self.setup_swipe_arrow()

        self.is_dragging = False
        self.start_y = 0

        self.set_custom_cursor()

    def set_custom_cursor(self):
        cursor_path = "C:\\vLaunch\\source\\pointer.png"
        try:
            pixmap = QPixmap(cursor_path)

            scaled_pixmap = pixmap.scaled(
                pixmap.width() // 5,
                pixmap.height() // 5,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            custom_cursor = QCursor(scaled_pixmap)
            self.setCursor(custom_cursor)
        except Exception as e:
            print(f"Error while loading <pointer>: {e}")

    def setup_background(self):
        background_path = "C:\\vLaunch\\source\\lock_screen_wallpaper.png"
        if os.path.exists(background_path):
            pixmap = QPixmap(background_path)
        else:
            pixmap = QPixmap(1920, 1080)
            pixmap.fill(Qt.black)

        self.background_label.setPixmap(pixmap)
        self.background_label.setScaledContents(True)
        self.background_label.setGeometry(0, 0, self.width(), self.height())

    def setup_swipe_arrow(self):
        self.swipe_arrow.setText("↑")
        self.swipe_arrow.setStyleSheet("color: white; font-size: 64px; background-color: rgba(128, 128, 128, 100);")
        self.swipe_arrow.setAlignment(Qt.AlignCenter)
        self.swipe_arrow.setFixedSize(100, 100)
        self.swipe_arrow.move((self.width() - 100) // 2, self.height() - 150)

    def update_time(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss\nddd, dd MMM yyyy")
        self.time_label.setText(current_time)
        self.time_label.adjustSize()
        QTimer.singleShot(1000, self.update_time)

    def randomize_time_position(self):
        screen_width = self.width()
        screen_height = self.height()
        label_width = self.time_label.width()
        label_height = self.time_label.height()

        random_x = random.randint(0, max(0, screen_width - label_width))
        random_y = random.randint(0, max(0, screen_height - label_height))

        self.time_label.move(random_x, random_y)

    def launch_kernel(self):
        self.close()
        global kernel
        kernel = KernelWindow()
        kernel.show()

    def mousePressEvent(self, event):
        if self.swipe_arrow.geometry().contains(event.pos()):
            self.is_dragging = True
            self.start_y = event.y()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta_y = event.y() - self.start_y
            if delta_y < 0:  
                self.swipe_arrow.move(self.swipe_arrow.x(), self.swipe_arrow.y() + delta_y)
                self.start_y = event.y()

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            if self.swipe_arrow.y() < self.height() // 3:
                self.launch_kernel()
            else:  
                self.swipe_arrow.move((self.width() - 100) // 2, self.height() - 150)

    def keyPressEvent(self, event):
        if event.key() in {Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space}:
            self.launch_kernel()

class TUI_label:
    def __init__(self):
        self.current_dir = os.getcwd()
        self.superuser_mode = False
        self.commands = {
            "help": self.show_help,
            "exit": self.exit,
            "cd": self.change_directory,
            "ls": self.list_directory,
            "pwd": self.print_working_directory,
            "su": self.activate_superuser_mode,
            "whoami": self.print_current_user
        }
        self.command_completer = WordCompleter(list(self.commands.keys()), ignore_case=True)
        self.session = PromptSession(completer=self.command_completer)
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            '': 'ansiblue'
        })

    def run(self):
        while True:
            try:
                command = self.session.prompt(HTML('<prompt>{}</prompt>> '.format(self.current_dir)), style=self.style).strip()
                if command:
                    self.execute_command(command)
            except KeyboardInterrupt:
                print_formatted_text(HTML('<ansired>\nExiting...</ansired>'))
                break
            except Exception as e:
                print_formatted_text(HTML('<ansired>Unexpected error: {}</ansired>'.format(str(e))))

    def execute_command(self, command):
        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd in self.commands:
            self.commands[cmd](args)
        else:
            print_formatted_text(HTML('<ansired>Command not found: {}</ansired>'.format(cmd)))

    def show_help(self, args):
        print_formatted_text(HTML('<ansigreen>Available commands: {}</ansigreen>'.format(', '.join(self.commands.keys()))))
        print_formatted_text(HTML('<ansigreen>User: {}</ansigreen>'.format(getpass.getuser())))

    def change_directory(self, args):
        if not args:
            print_formatted_text(HTML('<ansired>Usage: cd <directory></ansired>'))
            return

        path = args[0]
        try:
            os.chdir(path)
            self.current_dir = os.getcwd()
            print_formatted_text(HTML('<ansigreen>Changed directory to: {}</ansigreen>'.format(self.current_dir)))
        except FileNotFoundError:
            print_formatted_text(HTML('<ansired>Directory not found: {}</ansired>'.format(path)))
        except PermissionError:
            print_formatted_text(HTML('<ansired>Permission denied: {}</ansired>'.format(path)))
        except Exception as e:
            print_formatted_text(HTML('<ansired>Error: {}</ansired>'.format(str(e))))

    def list_directory(self, args):
        try:
            files = os.listdir(self.current_dir)
            print_formatted_text(HTML('<ansiblue>{}</ansiblue>'.format('\n'.join(files))))
        except PermissionError:
            print_formatted_text(HTML('<ansired>Permission denied</ansired>'))
        except Exception as e:
            print_formatted_text(HTML('<ansired>Error: {}</ansired>'.format(str(e))))

    def print_working_directory(self, args):
        print_formatted_text(HTML('<ansigreen>{}</ansigreen>'.format(self.current_dir)))

    def activate_superuser_mode(self, args):
        password = getpass.getpass("Password: ")
        if self.check_password(password):
            self.superuser_mode = True
            print_formatted_text(HTML('<ansigreen>Superuser mode activated</ansigreen>'))
        else:
            print_formatted_text(HTML('<ansired>Authentication failed</ansired>'))

    def check_password(self, password):
        return password == "rootpassword"

    def print_current_user(self, args):
        print_formatted_text(HTML('<ansigreen>{}</ansigreen>'.format(getpass.getuser())))

    def exit(self, args):
        raise KeyboardInterrupt

if __name__ == "__main__":
    tui = TUI_label()
    tui.run()

class VSysInit:
    #doesnt work probably should remove
    def __init__(self):
        self.python = sys.executable
        self.violence_sysinit_path = "C:\\vLaunch\\kernel\\modules\\violence_sysinit.kernel"
        if not os.path.exists(self.violence_sysinit_path):
            self.violence_sysinit_path = "C:\\vLaunch\\kernel\\modules\\violence_sysinit.py"

    def run(self):
        if os.path.exists(self.violence_sysinit_path):
            os.system(f"{self.python} {self.violence_sysinit_path}")
        else:
            print(f"File not found: {self.violence_sysinit_path}")

class KernelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kernel_build_1.0.4")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.open_windows = {}

        self.desktop_widget = QWidget(self)
        self.desktop_layout = QVBoxLayout(self.desktop_widget)
        self.desktop_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.desktop_widget)

        self.app = QApplication.instance() or QApplication(sys.argv)

        self.url_bar = QLineEdit()
        self.tabs = QTabWidget()

        self.superuser_mode = False

        self.autostart()

        self.add_settings_shortcut()
        self.add_camera_shortcut()
        self.add_terminal_shortcut()
        self.add_ide_shortcut()
        self.add_snake_shortcut()
        self.add_store_shortcut()
        self.add_browser_shortcut()

        self.dock_panel = QFrame(self)
        self.dock_panel.setFixedHeight(60)
        self.dock_panel.setStyleSheet("background-color: gray;")
        self.desktop_layout.addStretch()
        self.desktop_layout.addWidget(self.dock_panel)

        self.dock_layout = QHBoxLayout(self.dock_panel)
        self.dock_layout.setContentsMargins(10, 5, 10, 5)

        self.start_menu_button = QPushButton("Start Menu", self)
        self.start_menu_button.setFixedSize(100, 40)
        self.start_menu_button.clicked.connect(self.show_start_menu)
        self.dock_layout.addWidget(self.start_menu_button)

        self.spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.dock_layout.addItem(self.spacer)

        self.battery_label = QLabel(self)
        self.dock_layout.addWidget(self.battery_label)

        #self.notifications_label = QLabel(self) 
        #self.dock_layout.addWidget(self.notifications_label)

        # should fix notifications applet as it doesnt show up

        self.init_clock_applet()
        self.init_wlan_applet()
        self.init_notifications_applet()

        self.battery_update_timer = QTimer(self)
        self.battery_update_timer.timeout.connect(self.update_battery_status)
        self.battery_update_timer.start(10000)
        self.update_battery_status()

        self.set_custom_cursor()

    def set_custom_cursor(self):
        cursor_path = "C:\\vLaunch\\source\\pointer.png"
        try:
            pixmap = QPixmap(cursor_path)

            scaled_pixmap = pixmap.scaled(
                pixmap.width() // 5,
                pixmap.height() // 5,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            custom_cursor = QCursor(scaled_pixmap)
            self.setCursor(custom_cursor)
        except Exception as e:
            print(f"Error while loading <pointer>: {e}")

    def autostart(self):
        pass
        #self.initialize_services()
        #self.sheila()

    def add_settings_shortcut(self): # line 224
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/settings.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("Settings", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_settings

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_camera_shortcut(self): # line 225
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app4.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("Camera", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_camera

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_terminal_shortcut(self): # line 226
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app5.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("Terminal", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_terminal

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_ide_shortcut(self): # line 227
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app6.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("IDE", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_ide

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_snake_shortcut(self): # line 245
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app7.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("snake", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_snake_game

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_store_shortcut(self): # line 246
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app8.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("App Store", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_store

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def add_browser_shortcut(self): # line 247
        shortcut_layout = QVBoxLayout()
        shortcut_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(self)
        pixmap = QPixmap("C:/vLaunch/source/app1.png").scaled(64, 64, Qt.KeepAspectRatio)
        icon_label.setPixmap(pixmap)

        text_label = QLabel("V-Browser", self)

        shortcut_layout.addWidget(icon_label)
        shortcut_layout.addWidget(text_label)

        shortcut_frame = QFrame(self)
        shortcut_frame.setLayout(shortcut_layout)
        shortcut_frame.setFixedWidth(80)
        shortcut_frame.mousePressEvent = self.open_browser

        self.desktop_layout.insertWidget(0, shortcut_frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    def run_vys_package(self, vys_file):
        if not os.path.isfile(vys_file):
            raise FileNotFoundError(f"File {vys_file} not found!")

        if not vys_file.endswith(".vys"):
            raise ValueError("This isn't .vys file!")

        seed = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        extract_path = os.path.join("C:\\vLaunch\\apps\\temp", seed)
        os.makedirs(extract_path, exist_ok=True)

        try:
            with zipfile.ZipFile(vys_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile:
            raise ValueError("File .vys damaged!")

        build_info_path = os.path.join(extract_path, "build.info.py")
        if not os.path.isfile(build_info_path):
            raise FileNotFoundError("File not found: build.info.py!")

        spec = importlib.util.spec_from_file_location("build_info", build_info_path)
        build_info = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build_info)

        app_name = getattr(build_info, "name", None)
        if not app_name:
            raise ValueError("In build.info.py can't find 'name'.")

        base_vrun_path = os.path.join(extract_path, "base.vrun")
        if not os.path.isfile(base_vrun_path):
            raise FileNotFoundError("File not found: base.vrun!")

        def run_app():
            with open(base_vrun_path, 'r') as file:
                exec(file.read(), {'__name__': '__main__'})

        def close_app():
            output_file = os.path.join("C:\\vLaunch\\apps\\user_apps", f"{app_name}.vys")
            with zipfile.ZipFile(output_file, 'w') as zipf:
                for root, dirs, files in os.walk(extract_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_path)
                        zipf.write(file_path, arcname)
            shutil.rmtree(extract_path)

        run_app()
        close_app()

    def update_battery_status(self):
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            charging = battery.power_plugged
            self.battery_label.setText(f"Battery: {percent}% {'(Charging)' if charging else ''}")
        else:
            self.battery_label.setText("Battery info not available")

    def init_clock_applet(self):
        self.clock_applet = QLabel(self)
        self.clock_applet.setStyleSheet("color: white; font-size: 14px; text-align: center;")
        self.dock_layout.addWidget(self.clock_applet, alignment=Qt.AlignRight)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.update_clock()

    def update_clock(self):
        current_time = QDateTime.currentDateTime()
        time_str = current_time.toString("hh:mm")
        date_str = current_time.toString("ddd, dd MMM yyyy")
        self.clock_applet.setText(f"{time_str}\n{date_str}")

    def init_wlan_applet(self):
        self.wlan_applet = QLabel(self)
        self.wlan_applet.setStyleSheet("color: white; font-size: 14px; text-align: center;")
        self.dock_layout.addWidget(self.wlan_applet, alignment=Qt.AlignRight)

        self.wlan_timer = QTimer(self)
        self.wlan_timer.timeout.connect(self.update_wlan_status)
        self.wlan_timer.start(5000)

        self.update_wlan_status()

    def update_wlan_status(self):
        wlan_status = "WI-FI: OFF"
        for net in psutil.net_if_addrs():
            if "Wi-Fi" in net or "wlan" in net.lower():
                connections = psutil.net_if_stats().get(net, None)
                if connections and connections.isup:
                    wlan_status = "WI-FI: ON"
                else:
                    wlan_status = "WI-FI: NC"
                break
        self.wlan_applet.setText(wlan_status)

    def init_notifications_applet(self):
        self.notifications_label = QLabel("0", self)
        self.notifications_label.setFixedSize(30, 30)
        self.notifications_label.setAlignment(Qt.AlignCenter)
        self.notifications_label.setStyleSheet("""
            QLabel {
                background: #e74c3c;
                color: white;
                border-radius: 15px;
                font-weight: bold;
            }
        """)
        self.notifications_label.mousePressEvent = self.show_notifications_menu

    def show_notifications_menu(self, event):
        if hasattr(self, 'notifications_menu') and self.notifications_menu.isVisible():
            self.notifications_menu.hide()
        else:
            self.notifications_menu = QWidget(self)
            self.notifications_menu.setWindowFlags(Qt.FramelessWindowHint)
            self.notifications_menu.setGeometry(self.width() - 300, 0, 300, self.height())
            self.notifications_menu.setStyleSheet("background-color: white; border: 1px solid black;")

            layout = QVBoxLayout(self.notifications_menu)
            self.notifications_list = QListWidget(self.notifications_menu)
            layout.addWidget(self.notifications_list)

            self.notifications_menu.show()
            self.sheila()

    def sheila(self):
        local_version_file = r'C:\vLaunch\version_info.txt'
        online_version_url = 'https://raw.githubusercontent.com/Vafls/vSubSys_UPD/main/version_info.txt'
        history_file = r'C:\vLaunch\kernel\config\nt.history'

        def read_local_version():
            with open(local_version_file, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.startswith('current_version'):
                        return int(line.split('=')[1].strip())
            return None

        def read_online_version():
            response = requests.get(online_version_url)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.startswith('current_version'):
                        return int(line.split('=')[1].strip())
            return None

        def read_online_message():
            response = requests.get(online_version_url)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.startswith('to_print'):
                        return line.split('=')[1].strip()
            return None

        def check_for_updates():
            local_version = read_local_version()
            online_version = read_online_version()
            update_message = read_online_message()

            if online_version is not None and local_version is not None and online_version > local_version:
                notification = f"{QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')} - Available update: {update_message}"
                self.add_notification(notification)
                self.save_notification_to_history(notification)

        def save_notification_to_history(notification):
            if not os.path.exists(history_file):
                with open(history_file, 'w', encoding='utf-8') as file:
                    file.write(notification + '\n')
            else:
                with open(history_file, 'r+', encoding='utf-8') as file:
                    lines = file.readlines()
                    if notification not in lines:
                        file.write(notification + '\n')

        check_for_updates()

    def add_notification(self, notification):
        self.notifications_list.addItem(notification)
    
    def show_start_menu(self):
        menu = QMenu(self)
        shutdown_action = QAction("Shutdown", self)
        shutdown_action.triggered.connect(self.shutdown)

        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self.restart)

        launchpad_action = QAction("Launchpad", self)
        launchpad_action.triggered.connect(self.launchpad)

        menu.addAction(shutdown_action)
        menu.addAction(restart_action)
        menu.addAction(launchpad_action)
        menu.exec_(self.mapToGlobal(QPoint(10, self.height() - 50)))

    def shutdown(self):
        QApplication.quit()

    def restart(self):
        QApplication.quit()
        os.system(f"python {sys.argv[0]}")

    def launchpad(self):
        if "Launchpad" in self.open_windows:
            window = self.open_windows["Launchpad"]
            window.close()
            del self.open_windows["Launchpad"]

        window = QWidget()
        window.setWindowTitle("Launchpad")
        window.setFixedSize(1280, 720)
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 15px;
            border: 2px solid #d0d0d0;
        """)

        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - window.width()) // 2
        y = (screen_geometry.height() - window.height()) // 2
        window.move(x, y)

        main_layout = QVBoxLayout(window)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background: transparent;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(content_widget)
        grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        grid_layout.setSpacing(30)
        grid_layout.setContentsMargins(10, 10, 10, 10)

        self.load_apps(content_widget, grid_layout)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        close_btn = QPushButton("Close Launchpad", window)
        close_btn.setFixedSize(160, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #ff4444;
                color: white;
                border-radius: 8px;
                font: bold 12px Arial;
            }
            QPushButton:hover {
                background: #cc0000;
            }
            QPushButton:pressed {
                background: #aa0000;
            }
        """)
        close_btn.clicked.connect(lambda: self.close_launchpad(window))

        main_layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        self.open_windows["Launchpad"] = window
        window.show()

    def load_apps(self, parent, grid_layout):
        apps_dir = "C:\\vLaunch\\apps\\user_apps"
        valid_apps = []

        for filename in os.listdir(apps_dir):
            if filename.endswith(".vysico"):
                filepath = os.path.join(apps_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        app_data = {}
                        for line in f:
                            line = line.strip()
                            if line and '=' in line:
                                key, value = line.split('=', 1)
                                app_data[key.strip().lower()] = value.strip()

                        required = ['name', 'icon', 'app']
                        if all(key in app_data for key in required):
                            icon_path = os.path.join(apps_dir, app_data['icon'])
                            app_path = os.path.join(apps_dir, app_data['app'])
                            
                            if os.path.exists(icon_path) and os.path.exists(app_path):
                                app_data['icon_path'] = icon_path
                                app_data['app_path'] = app_path
                                valid_apps.append(app_data)
                            else:
                                print(f"Missing files for {filename}")
                        else:
                            print(f"Invalid config in {filename}")

                except Exception as e:
                    print(f"Error loading {filename}: {str(e)}")
                    continue

        row, col = 0, 0
        max_cols = 6

        for app in valid_apps:
            app_widget = QWidget(parent)
            app_widget.setFixedSize(120, 140)
            app_layout = QVBoxLayout(app_widget)
            app_layout.setAlignment(Qt.AlignCenter)
            app_layout.setSpacing(5)

            icon_btn = QPushButton()
            icon_btn.setFixedSize(100, 100)
            icon_btn.setIcon(QIcon(app['icon_path']))
            icon_btn.setIconSize(QSize(80, 80))
            icon_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    border-radius: 15px;
                    border: 2px solid #ddd;
                }
                QPushButton:hover {
                    background: #e8e8e8;
                    border-color: #ccc;
                }
            """)
            icon_btn.clicked.connect(lambda _, p=app['app_path']: self.launch_app(p))

            name_label = QLabel(app['name'])
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("""
                font: 14px Arial;
                color: #333;
                max-width: 100px;
                qproperty-wordWrap: true;
            """)

            app_layout.addWidget(icon_btn)
            app_layout.addWidget(name_label)
            grid_layout.addWidget(app_widget, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def close_launchpad(self, window):
        if window:
            window.close()
        if "Launchpad" in self.open_windows:
            del self.open_windows["Launchpad"]
        self.update_dock()

    def launch_app(self, app_path):
        try:
            if os.path.exists(app_path):
                if sys.platform == "win32":
                    os.startfile(app_path)
                else:
                    subprocess.Popen([sys.executable, app_path])
            else:
                QMessageBox.warning(self, "Error", "Application file not found!")
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", 
                               f"Failed to launch application:\n{str(e)}")

    def on_window_close(self, window):
        title = window.windowTitle()
        if title in self.open_windows:
            del self.open_windows[title]
        window.close()
        self.update_dock()

    def open_settings(self, event=None):
        if "Settings" not in self.open_windows:
            settings_window = AppWindow("Settings", self.on_window_close)
            settings_window.show()
            self.open_windows["Settings"] = settings_window
        self.update_dock()       

    def open_camera(self=None, event=None):

        if "Camera" in self.open_windows:
            window = self.open_windows["Camera"]
            window.raise_()
            window.activateWindow()
            return

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Camera")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Camera")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: self.close_camera(window))
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        video_label = QLabel()
        layout.addWidget(video_label)

        button_layout = QHBoxLayout()
        snapshot_button = QPushButton("Photo")
        button_layout.addWidget(snapshot_button)

        record_button = QPushButton("Start Record")
        button_layout.addWidget(record_button)
        layout.addLayout(button_layout)

        cap = cv2.VideoCapture(0)
        recording = [False]
        video_writer = [None]

        def update_frame():
            ret, frame = cap.read()
            if ret:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
                video_label.setPixmap(QPixmap.fromImage(image))

                if recording[0] and video_writer[0]:
                    video_writer[0].write(frame)

            QTimer.singleShot(10, update_frame)

        def take_snapshot():
            ret, frame = cap.read()
            if ret:
                filename = f"snapshot_{int(time.time())}.png"
                cv2.imwrite(filename, frame)
                print(f"image saved: {filename}")

        def toggle_recording():
            if not recording[0]:
                filename = f"video_{int(time.time())}.avi"
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                video_writer[0] = cv2.VideoWriter(filename, fourcc, 20.0, (int(cap.get(3)), int(cap.get(4))))
                recording[0] = True
                record_button.setText("Stop Record")
                print(f"Запись началась: {filename}")
            else:
                recording[0] = False
                video_writer[0].release()
                video_writer[0] = None
                record_button.setText("Start Record")
                print("Video record stopped")

        def toggle_tracking():
            nonlocal tracking_enabled
            tracking_enabled = not tracking_enabled
            track_button.setText("Disable face Tracking" if tracking_enabled else "Enable face Tracking")

        track_button = QPushButton("Enable face Tracking")
        track_button.clicked.connect(toggle_tracking)
        button_layout.addWidget(track_button)

        tracking_enabled = False

        face_cascade = cv2.CascadeClassifier("C:\\vLaunch\\kernel\\config\\haarcascade_frontalface_default.xml")
        hand_cascade_path = "C:\\vLaunch\\kernel\\config\\haarcascade_hand.xml"
        if not os.path.exists(hand_cascade_path):
            print(f"Error: {hand_cascade_path} not found.")
            hand_cascade = None
        else:
            hand_cascade = cv2.CascadeClassifier(hand_cascade_path)

        def update_frame():
            ret, frame = cap.read()
            if ret:
                if hand_cascade:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    hands = hand_cascade.detectMultiScale(gray, 1.1, 4)
                else:
                    hands = []
            faces = []
            if tracking_enabled:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                hands = hand_cascade.detectMultiScale(gray, 1.1, 4)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame, "Face", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

            for (x, y, w, h) in hands:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "Hand", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            video_label.setPixmap(QPixmap.fromImage(image))

            if recording[0] and video_writer[0]:
                video_writer[0].write(frame)

            QTimer.singleShot(10, update_frame)

        snapshot_button.clicked.connect(take_snapshot)
        record_button.clicked.connect(toggle_recording)

        self.open_windows["Camera"] = window
        self.update_dock()

        def close_camera(window):
            window.close()
            if "Camera" in self.open_windows:
                del self.open_windows["Camera"]
            self.update_dock()

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        update_frame()
        window.show()

    def close_browser(self, window):
        window.close()
        if "Browser" in self.open_windows:
            del self.open_windows["Browser"]
        self.update_dock()

    def close_current_tab(self, index):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(index)

    def open_browser(self, event=None):
        if "Browser" in self.open_windows:
            window = self.open_windows["Browser"]
            window.raise_()
            window.activateWindow()
            return

        window = QMainWindow()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Browser")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        tabs = QTabWidget()
        tabs.tabCloseRequested.connect(self.close_current_tab)
        tabs.setDocumentMode(True)
        tabs.tabBarDoubleClicked.connect(lambda i: add_new_tab() if i == -1 else None)

        def close_browser(self, window):
            window.close()
            if "Browser" in self.open_windows:
                del self.open_windows["Browser"]
            self.update_dock()

        def close_current_tab(self, index):
            if self.tabs.count() < 2:
                return
            self.tabs.removeTab(index)

        def update_urlbar(qurl, browser=None):
            if browser != tabs.currentWidget():
                return
            url_bar.setText(qurl.toString())
            url_bar.setCursorPosition(0)

        tabs.currentChanged.connect(lambda i: update_urlbar(tabs.currentWidget().url(), tabs.currentWidget()))
        tabs.setTabsClosable(True)

        def close_current_tab(i):
            if tabs.count() < 2:
                return
            tabs.removeTab(i)

        tabs.tabCloseRequested.connect(close_current_tab)

        window.setCentralWidget(tabs)

        navtb = QToolBar("Navigation")
        window.addToolBar(navtb)

        url_bar = QLineEdit()

        def navigate_to_url():
            url = url_bar.text()
            if not url.startswith('http'):
                url = 'http://' + url
            tabs.currentWidget().setUrl(QUrl(url))

        url_bar.returnPressed.connect(navigate_to_url)

        home_button = QAction('Home', window)

        def navigate_home():
            tabs.currentWidget().setUrl(QUrl('https://www.google.com'))

        home_button.triggered.connect(navigate_home)

        new_tab_button = QAction('New Tab', window)

        def add_new_tab(qurl=None, label="Blank"):
            if qurl is None or not isinstance(qurl, QUrl):
                qurl = QUrl('')

            browser = QWebEngineView()
            browser.setUrl(qurl)

            i = tabs.addTab(browser, label)
            tabs.setCurrentIndex(i)

            browser.urlChanged.connect(lambda qurl, browser=browser: update_urlbar(qurl, browser))
            browser.loadFinished.connect(lambda _, i=i, browser=browser: tabs.setTabText(i, browser.page().title()))

        new_tab_button.triggered.connect(add_new_tab)

        navtb.addAction(home_button)
        navtb.addAction(new_tab_button)
        navtb.addWidget(url_bar)

        add_new_tab(QUrl('https://www.google.com'), 'Homepage')

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Browser")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: self.close_browser(window))
        title_layout.addWidget(close_button)

        navtb.addWidget(title_bar)

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        window.show()
        self.open_windows["Browser"] = window
        self.update_dock()

        def update_urlbar(qurl, browser=None):
            if browser != tabs.currentWidget():
                return
            url_bar.setText(qurl.toString())
            url_bar.setCursorPosition(0)

        def add_new_tab(qurl=None, label="Blank"):
            if qurl is None or not isinstance(qurl, QUrl):
                qurl = QUrl('')

            browser = QWebEngineView()
            browser.setUrl(qurl)

            i = tabs.addTab(browser, label)
            tabs.setCurrentIndex(i)

            browser.urlChanged.connect(lambda qurl, browser=browser: update_urlbar(qurl, browser))
            browser.loadFinished.connect(lambda _, i=i, browser=browser: tabs.setTabText(i, browser.page().title()))

        def navigate_to_url():
            url = url_bar.text()
            if not url.startswith('http'):
                url = 'http://' + url
            tabs.currentWidget().setUrl(QUrl(url))

        def close_current_tab(i):
            if tabs.count() < 2:
                return
            tabs.removeTab(i)

        def navigate_home():
            tabs.currentWidget().setUrl(QUrl('https://www.google.com'))

        if "Browser" in self.open_windows:
            window = self.open_windows["Browser"]
            window.raise_()
            window.activateWindow()
            return

        window = QMainWindow()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Browser")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.tabBarDoubleClicked.connect(lambda i: add_new_tab() if i == -1 else None)
        tabs.currentChanged.connect(lambda i: update_urlbar(tabs.currentWidget().url(), tabs.currentWidget()))
        tabs.setTabsClosable(True)
        tabs.tabCloseRequested.connect(close_current_tab)

        window.setCentralWidget(tabs)

        navtb = QToolBar("Navigation")
        window.addToolBar(navtb)

        url_bar = QLineEdit()
        url_bar.returnPressed.connect(navigate_to_url)

        home_button = QAction('Home', window)
        home_button.triggered.connect(navigate_home)

        new_tab_button = QAction('New Tab', window)
        new_tab_button.triggered.connect(add_new_tab)

        navtb.addAction(home_button)
        navtb.addAction(new_tab_button)
        navtb.addWidget(url_bar)

        add_new_tab(QUrl('https://www.google.com'), 'Homepage')

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        window.mousePressEvent = mousePressEvent
        window.mouseMoveEvent = mouseMoveEvent

        window.show()
        self.open_windows["Browser"] = window
        self.update_dock()

    def open_snake_game(self, event=None):
        if "Snake" in self.open_windows:
            window = self.open_windows["Snake"]
            window.raise_()
            window.activateWindow()
            return

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Snake")
        window.setGeometry(300, 200, 800, 600)
        window.setFixedSize(1280, 720)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Snake")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: close_snake_game(window))
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        game_area = QLabel()
        game_area.setStyleSheet("background-color: black;")
        layout.addWidget(game_area)

        window.setLayout(layout)

        def close_snake_game(window):
            window.close()
            if "Snake" in self.open_windows:
                del self.open_windows["Snake"]
            self.update_dock()

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        self.open_windows["Snake"] = window
        self.update_dock()

        self.snake_block = 20
        self.snake_speed = 100

        self.snake_list = [[100, 50]]
        self.length_of_snake = 1

        self.foodx = random.randint(0, (1280 // self.snake_block) - 1) * self.snake_block
        self.foody = random.randint(0, (720 // self.snake_block) - 1) * self.snake_block

        self.x1 = 1280 // 2
        self.y1 = 720 // 2
        self.x1_change = 0
        self.y1_change = 0

        self.timer = QTimer(window)
        self.timer.timeout.connect(lambda: self.update_snake_game(window, game_area))
        self.timer.start(self.snake_speed)

        window.setFocusPolicy(Qt.StrongFocus)
        window.keyPressEvent = self.keyPressEvent

    def update_snake_game(self, window, game_area):
        self.x1 += self.x1_change
        self.y1 += self.y1_change

        if self.x1 >= window.width() or self.x1 < 0 or self.y1 >= window.height() or self.y1 < 0:
            self.game_over(window)

        self.snake_list.append([self.x1, self.y1])
        if len(self.snake_list) > self.length_of_snake:
            del self.snake_list[0]

        for segment in self.snake_list[:-1]:
            if segment == [self.x1, self.y1]:
                self.game_over(window)

        self.update_snake_ui(game_area)

        if self.x1 == self.foodx and self.y1 == self.foody:
            self.foodx = random.randint(0, (window.width() // self.snake_block) - 1) * self.snake_block
            self.foody = random.randint(0, (window.height() // self.snake_block) - 1) * self.snake_block
            self.length_of_snake += 1

    def update_snake_ui(self, game_area):
        pixmap = QPixmap(game_area.size())
        pixmap.fill(Qt.black)
        painter = QPainter(pixmap)

        for segment in self.snake_list:
            painter.fillRect(segment[0], segment[1], self.snake_block, self.snake_block, Qt.green)

        painter.fillRect(self.foodx, self.foody, self.snake_block, self.snake_block, Qt.red)
        painter.end()

        game_area.setPixmap(pixmap)

    def game_over(self, window):
        self.timer.stop()
        QMessageBox.information(window, "Game Over", "You lost! Press OK to restart.")
        self.reset_snake_game()

    def reset_snake_game(self):
        self.snake_list = [[100, 50]]
        self.length_of_snake = 1
        self.x1 = 100
        self.y1 = 50
        self.x1_change = 0
        self.y1_change = 0
        self.foodx = random.randint(0, (self.width() // self.snake_block) - 1) * self.snake_block
        self.foody = random.randint(0, (self.height() // self.snake_block) - 1) * self.snake_block
        self.timer.start(self.snake_speed)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left and self.x1_change == 0:
            self.x1_change = -self.snake_block
            self.y1_change = 0
        elif event.key() == Qt.Key_Right and self.x1_change == 0:
            self.x1_change = self.snake_block
            self.y1_change = 0
        elif event.key() == Qt.Key_Up and self.y1_change == 0:
            self.x1_change = 0
            self.y1_change = -self.snake_block
        elif event.key() == Qt.Key_Down and self.y1_change == 0:
            self.x1_change = 0
            self.y1_change = self.snake_block

    def open_store(self, event=None):
        if "App Store" in self.open_windows:
            window = self.open_windows["App Store"]
            window.raise_()
            window.activateWindow()
            return

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("App Store")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("App Store")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: close_store(window))
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search for apps...")
        layout.addWidget(search_bar)

        app_list = QListWidget()
        layout.addWidget(app_list)

        app_list.addItem(QListWidgetItem("App 1"))
        app_list.addItem(QListWidgetItem("App 2"))
        app_list.addItem(QListWidgetItem("App 3"))
        app_list.addItem(QListWidgetItem("App 4"))
        app_list.addItem(QListWidgetItem("App 5"))
        app_list.addItem(QListWidgetItem("App 6"))
        app_list.addItem(QListWidgetItem("App 7"))
        app_list.addItem(QListWidgetItem("App 8"))
        app_list.addItem(QListWidgetItem("App 9"))
        app_list.addItem(QListWidgetItem("App 10"))

        stacked_widget = QStackedWidget()
        stacked_widget.addWidget(app_list)

        def show_app_details(item):
            app_name = item.text()
            layout = QVBoxLayout()

            back_button = QPushButton("←")
            back_button.setFixedSize(40, 40)
            back_button.clicked.connect(lambda: stacked_widget.setCurrentWidget(app_list))
            layout.addWidget(back_button, alignment=Qt.AlignLeft)

            app_description = QLabel(f"Description of {app_name}")
            app_description.setAlignment(Qt.AlignCenter)
            layout.addWidget(app_description)

            download_button = QPushButton("Download")
            layout.addWidget(download_button, alignment=Qt.AlignCenter)

            details_widget = QWidget()
            details_widget.setLayout(layout)
            stacked_widget.addWidget(details_widget)
            stacked_widget.setCurrentWidget(details_widget)

        app_list.itemClicked.connect(show_app_details)
        layout.addWidget(stacked_widget)

        def close_store(window):
            window.close()
            if "App Store" in self.open_windows:
                del self.open_windows["App Store"]
            self.update_dock()

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        self.open_windows["App Store"] = window
        self.update_dock()

        window.show()

    def open_ide(self, event=None):
        if "IDE" in self.open_windows:
            window = self.open_windows["IDE"]
            window.raise_()
            window.activateWindow()
            return

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("IDE")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)
        
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("IDE")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: (self.on_window_close(window), window.close()))
        title_layout.addWidget(close_button)

        title_bar.setLayout(title_layout)
        layout.addWidget(title_bar)

        menu_bar = QMenuBar(window)
        layout.addWidget(menu_bar)

        create_action = QAction("Create new .vys project", window)
        create_action.triggered.connect(self.create_new_vys_package)
        menu_bar.addAction(create_action)

        open_action = QAction("Open .vys project", window)
        open_action.triggered.connect(self.package_editor)
        menu_bar.addAction(open_action)

        compile_action = QAction("Compile project to .vys file", window)
        compile_action.triggered.connect(self.open_compiler)
        menu_bar.addAction(compile_action)

        window.setLayout(layout)

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        window.show()
        self.open_windows["IDE"] = window
        self.update_dock()

    def open_compiler(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Compile project to .vys file")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)

        label = QLabel("Select project folder:", dialog)
        layout.addWidget(label)

        path_input = QLineEdit(dialog)
        layout.addWidget(path_input)

        browse_button = QPushButton("Browse", dialog)
        browse_button.clicked.connect(lambda: self.browse_folder(path_input))
        layout.addWidget(browse_button)

        button_layout = QHBoxLayout()

        compile_button = QPushButton("Compile", dialog)
        compile_button.clicked.connect(lambda: self.compile_project(path_input.text(), dialog))
        button_layout.addWidget(compile_button)

        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        dialog.exec_()

    def compile_project(self, folder_path, dialog):
        required_files = ["base.vrun", "build.info.py", "dep.txt", "icon.png"]
        required_folders = ["license", "src"]

        missing_files = [f for f in required_files if not os.path.isfile(os.path.join(folder_path, f))]
        missing_folders = [f for f in required_folders if not os.path.isdir(os.path.join(folder_path, f))]

        if missing_files or missing_folders:
            missing_items = missing_files + missing_folders
            QMessageBox.warning(self, "Error", f"The project files have been damaged! Missing: {', '.join(missing_items)}")
            return

        project_name = os.path.basename(folder_path)
        dist_folder = os.path.join(folder_path, "dist")
        if not os.path.exists(dist_folder):
            os.makedirs(dist_folder)

        output_file = os.path.join(dist_folder, f"{project_name}.vys")

        with zipfile.ZipFile(output_file, 'w') as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)

        QMessageBox.information(self, "Success", f"Project '{project_name}' compiled successfully to {output_file}!")
        dialog.accept()

    def create_new_vys_package(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create new .vys package")
        dialog.setFixedSize(300, 150)

        layout = QVBoxLayout(dialog)

        label = QLabel("Enter project name:", dialog)
        layout.addWidget(label)

        project_name_input = QLineEdit(dialog)
        layout.addWidget(project_name_input)

        button_layout = QHBoxLayout()

        create_button = QPushButton("Create", dialog)
        create_button.clicked.connect(lambda: self.create_project_files(project_name_input.text(), dialog))
        button_layout.addWidget(create_button)

        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        dialog.exec_()

    def create_project_files(self, project_name, dialog):
        if not project_name:
            QMessageBox.warning(self, "Error", "Project name cannot be empty!")
            
        project_path = os.path.join("C:\\vLaunch\\apps\\user_apps", project_name)
        if os.path.exists(project_path):
            QMessageBox.warning(self, "Error", "Project already exists!")

        os.makedirs(project_path)
        os.makedirs(os.path.join(project_path, "license"))
        os.makedirs(os.path.join(project_path, "src"))

        with open(os.path.join(project_path, "base.vrun"), 'w', encoding='utf-8') as f:
            f.write("from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy, QMenu, QAction\n")
            f.write("from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QDateTime\n")
            f.write("from PyQt5.QtGui import QPixmap\n")
            f.write("from PyQt5.QtGui import QImage\n")
            f.write("from PyQt5.QtWidgets import QLineEdit\n")
            f.write("from PyQt5.QtCore import QPropertyAnimation, QRect\n")
            f.write("from PyQt5.QtCore import QObject\n")
            f.write("from PyQt5.QtGui import QCursor\n")
            f.write("import importlib.util\n")
            f.write("import zipfile\n")
            f.write("from PyQt5.QtWidgets import QListWidget, QStackedWidget\n")
            f.write("from PyQt5.QtWidgets import QMenuBar\n")
            f.write("from PyQt5.QtWidgets import QDialog\n")
            f.write("from PyQt5.QtWidgets import QMessageBox\n")
            f.write("from PyQt5.QtWidgets import QSpacerItem\n")
            f.write("from PyQt5.QtWidgets import QFileDialog\n")
            f.write("from PyQt5.QtWidgets import QPlainTextEdit\n")
            f.write("from PyQt5.QtWidgets import QListWidgetItem\n")
            f.write("from PyQt5.QtWidgets import QTabWidget\n")
            f.write("\n")
            f.write("class ExampleApp(QWidget):\n")
            f.write("    def __init__(self):\n")
            f.write("        super().__init__()\n")
            f.write("        self.initUI()\n\n")
            f.write("    def initUI(self):\n")
            f.write("        self.setWindowFlags(Qt.FramelessWindowHint)\n")
            f.write("        self.setWindowTitle('your_app_name')\n")
            f.write("        self.setGeometry(300, 200, 800, 600)\n")
            f.write("        self.setStyleSheet('border: 2px solid black; background-color: white;')\n\n")
            f.write("        layout = QVBoxLayout(self)\n\n")
            f.write("        title_bar = QWidget()\n")
            f.write("        title_bar.setFixedHeight(30)\n")
            f.write("        title_bar.setStyleSheet('background-color: black; color: white;')\n")
            f.write("        title_layout = QHBoxLayout(title_bar)\n")
            f.write("        title_layout.setContentsMargins(0, 0, 0, 0)\n\n")
            f.write("        title_label = QLabel('your_app_name')\n")
            f.write("        title_label.setStyleSheet('color: white;')\n")
            f.write("        title_layout.addWidget(title_label)\n\n")
            f.write("        minimize_button = QPushButton('_')\n")
            f.write("        minimize_button.setFixedSize(QSize(30, 30))\n")
            f.write("        minimize_button.setStyleSheet('background-color: black; color: white;')\n")
            f.write("        minimize_button.clicked.connect(self.showMinimized)\n")
            f.write("        title_layout.addWidget(minimize_button)\n\n")
            f.write("        maximize_button = QPushButton('□')\n")
            f.write("        maximize_button.setFixedSize(QSize(30, 30))\n")
            f.write("        maximize_button.setStyleSheet('background-color: black; color: white;')\n")
            f.write("        maximize_button.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())\n")
            f.write("        title_layout.addWidget(maximize_button)\n\n")
            f.write("        close_button = QPushButton('X')\n")
            f.write("        close_button.setFixedSize(QSize(30, 30))\n")
            f.write("        close_button.setStyleSheet('background-color: red; color: white;')\n")
            f.write("        close_button.clicked.connect(self.close)\n")
            f.write("        title_layout.addWidget(close_button)\n\n")
            f.write("        title_bar.setLayout(title_layout)\n")
            f.write("        layout.addWidget(title_bar)\n\n")
            f.write("        menu_bar = QMenuBar(self)\n")
            f.write("        layout.addWidget(menu_bar)\n\n")
            f.write("        example_label = QLabel('Example', self)\n")
            f.write("        example_label.setAlignment(Qt.AlignCenter)\n")
            f.write("        example_label.setStyleSheet('font-size: 24px; font-weight: bold;')\n")
            f.write("        layout.addWidget(example_label)\n\n")
            f.write("        self.setLayout(layout)\n\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    app = QApplication.instance()\n")
            f.write("    if app is None:\n")
            f.write("        app = QApplication(sys.argv)\n")
            f.write("        window = ExampleApp()\n")
            f.write("        window.show()\n")
            f.write("        app.exec_()\n")
            f.write("    else:\n")
            f.write("        window = ExampleApp()\n")
            f.write("        window.show()\n")

        with open(os.path.join(project_path, "build.info.py"), 'w') as f:
            f.write(f"name = '{project_name}'\nversion = '1.0.0'")

        with open(os.path.join(project_path, "dep.txt"), 'w') as f:
            f.write("# Dependencies")

        with open(os.path.join(project_path, "icon.png"), 'wb') as f:
            f.write(b"")

        QMessageBox.information(self, "Success", f"Project '{project_name}' created successfully!")

        dialog.accept()
        
    def package_editor(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Project Folder")
        dialog.setFixedSize(400, 200)

        layout = QVBoxLayout(dialog)

        label = QLabel("Select project folder:", dialog)
        layout.addWidget(label)

        path_input = QLineEdit(dialog)
        layout.addWidget(path_input)

        browse_button = QPushButton("Browse", dialog)
        browse_button.clicked.connect(lambda: self.browse_folder(path_input))
        layout.addWidget(browse_button)

        button_layout = QHBoxLayout()

        open_button = QPushButton("Open", dialog)
        open_button.clicked.connect(lambda: self.open_project_folder(path_input.text(), dialog))
        button_layout.addWidget(open_button)

        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        dialog.exec_()

    def browse_folder(self, path_input):
        folder_dialog = QFileDialog(self)
        folder_dialog.setFileMode(QFileDialog.Directory)
        if folder_dialog.exec_():
            selected_directory = folder_dialog.selectedFiles()[0]
            path_input.setText(selected_directory)

    def open_project_folder(self, folder_path, dialog):
        required_files = ["base.vrun", "build.info.py", "dep.txt", "icon.png"]
        required_folders = ["license", "src"]

        missing_files = [f for f in required_files if not os.path.isfile(os.path.join(folder_path, f))]
        missing_folders = [f for f in required_folders if not os.path.isdir(os.path.join(folder_path, f))]

        if missing_files or missing_folders:
            missing_items = missing_files + missing_folders
            QMessageBox.warning(self, "Error", f"Missing required files or folders: {', '.join(missing_items)}")
            return

        dialog.accept()
        self.edit_existing_project(folder_path)

    def edit_existing_project(self, folder_path):
        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Edit Project")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Edit Project")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(window.close)
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        main_layout = QHBoxLayout()

        file_browser = QListWidget()
        file_browser.setFixedWidth(200)
        file_browser.setStyleSheet("""
            QListWidget {
                border-right: 1px solid #cccccc;
                background-color: #f4f4f4;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #007aff;
                color: white;
            }
        """)
        self.populate_file_browser(file_browser, folder_path)
        main_layout.addWidget(file_browser)

        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        layout.addLayout(main_layout)
        window.setLayout(layout)

        file_browser.itemDoubleClicked.connect(lambda item: self.open_file_in_tab(item, folder_path, tab_widget))

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        window.show()
        self.open_windows["IDE"] = window
        self.update_dock()

    def populate_file_browser(self, file_browser, folder_path):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                item = QListWidgetItem(os.path.relpath(os.path.join(root, file), folder_path))
                file_browser.addItem(item)

    def open_file_in_tab(self, item, folder_path, tab_widget):
        file_path = os.path.join(folder_path, item.text())
        with open(file_path, 'r') as file:
            content = file.read()

        editor = QPlainTextEdit()
        editor.setPlainText(content)
        tab_widget.addTab(editor, item.text())

        editor.keyPressEvent = lambda event: self.save_file_on_ctrl_s(event, file_path, editor)

    def initialize_services(self):
        pass

    def save_file_on_ctrl_s(self, event, file_path, editor):
        if event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            with open(file_path, 'w') as file:
                file.write(editor.toPlainText())
            QMessageBox.information(editor, "Success", f"File {file_path} saved successfully!")
        else:
            QPlainTextEdit.keyPressEvent(editor, event)

    def open_settings(self=None, event=None):
        if "Settings" in self.open_windows:
            window = self.open_windows["Settings"]
            window.raise_()
            window.activateWindow()
            return

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Settings")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Settings")
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)

        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet("background-color: black; color: white;")
        minimize_button.clicked.connect(window.showMinimized)
        title_layout.addWidget(minimize_button)

        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet("background-color: black; color: white;")
        maximize_button.clicked.connect(lambda: window.showNormal() if window.isMaximized() else window.showMaximized())
        title_layout.addWidget(maximize_button)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(lambda: (self.on_window_close(window), window.close()))
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        main_layout = QHBoxLayout()
        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_layout.setSpacing(5)

        button_style = "QPushButton { padding: 10px; background: #f0f0f0; border: none; }"
        button_style += "QPushButton:hover { background: #e0e0e0; }"

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        main_layout.addWidget(content_widget)

        wifi_settings_button = QPushButton("Wi-Fi Settings", window)
        wifi_settings_button.setStyleSheet(button_style)
        wifi_settings_button.clicked.connect(lambda: self.show_wifi_settings(content_layout))
        menu_layout.addWidget(wifi_settings_button)

        disk_info_button = QPushButton("System Info", window)
        disk_info_button.setStyleSheet(button_style)
        disk_info_button.clicked.connect(lambda: self.show_disk_info(content_layout))
        menu_layout.addWidget(disk_info_button)

        menu_layout.addStretch()

        menu_widget = QWidget()
        menu_widget.setLayout(menu_layout)
        menu_widget.setFixedWidth(220)
        main_layout.addWidget(menu_widget)

        content_layout = QVBoxLayout()
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        layout.addLayout(main_layout)

        def mousePressEvent(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouseMoveEvent(event):
            if event.buttons() == Qt.LeftButton:
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mousePressEvent
        title_bar.mouseMoveEvent = mouseMoveEvent

        self.open_windows["Settings"] = window
        self.update_dock()
        window.show()

    def show_disk_info(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        disk_info = self.get_disk_info()

        config_path = "C:\\vLaunch\\kernel\\config\\global.cfg"
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config_data = config_file.read().splitlines()
                config_dict = {line.split('=')[0]: line.split('=')[1] for line in config_data if '=' in line}

            sys_version = config_dict.get("sys_version", "Unknown")
            based_os = config_dict.get("based_os", "Unknown")
            bootloader_name = config_dict.get("bootloader_name", "Unknown")
            bootloader_version = config_dict.get("bootloader_version", "Unknown")

            disk_info += f"\n\nSubsystem Build Number: {sys_version}"
            disk_info += f"\nBased OS: {based_os}"
            disk_info += f"\nBootloader: {bootloader_name}"
            disk_info += f"\nBootloader Version: {bootloader_version}"
        else:
            disk_info += "\n\nConfiguration file not found."

        disk_info_label = QLabel(disk_info)
        disk_info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(disk_info_label)

    def show_wifi_settings(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        wifi_toggle_button = QPushButton("Toggle Wi-Fi")
        wifi_toggle_button.clicked.connect(self.toggle_wifi)
        layout.addWidget(wifi_toggle_button)

        wifi_networks_list = QListWidget()
        layout.addWidget(wifi_networks_list)

        update_wifi_button = QPushButton("Update Wi-Fi Networks")
        update_wifi_button.clicked.connect(lambda: self.update_wifi_networks(wifi_networks_list))
        layout.addWidget(update_wifi_button)

        connect_wifi_button = QPushButton("Connect to Wi-Fi")
        connect_wifi_button.clicked.connect(lambda: self.connect_to_wifi(wifi_networks_list.currentItem().text() if wifi_networks_list.currentItem() else ""))
        layout.addWidget(connect_wifi_button)

    def get_disk_info(self):
        disk_info = ""
        partitions = psutil.disk_partitions()
        for partition in partitions:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info += f"Disk {partition.device} - Total: {usage.total // (1024 ** 3)} GB, Free: {usage.free // (1024 ** 3)} GB\n"
        return disk_info

    def toggle_wifi(self):
        os.system("netsh interface set interface name=\"Wi-Fi\" admin=disable")
        time.sleep(1)
        os.system("netsh interface set interface name=\"Wi-Fi\" admin=enable")

    def update_wifi_networks(self, wifi_networks_list):
        wifi_networks_list.clear()
        networks = os.popen("netsh wlan show networks").read().split("\n")
        for line in networks:
            if "SSID" in line:
                ssid = line.split(":")[1].strip()
                wifi_networks_list.addItem(ssid)

    def connect_to_wifi(self, ssid):
        os.system(f"netsh wlan connect name=\"{ssid}\"")

    def toggle_bluetooth(self):
        os.system("powershell -command \"(Get-Service -Name bthserv).Status\"")
        time.sleep(1)
        os.system("powershell -command \"Start-Service -Name bthserv\"")

    def update_bluetooth_devices(self, bluetooth_devices_list):
        bluetooth_devices_list.clear()
        devices = os.popen("powershell -command \"Get-PnpDevice -Class Bluetooth\"").read().split("\n")
        for line in devices:
            if "Name" in line and ":" in line:
                device_name = line.split(":")[1].strip()
                bluetooth_devices_list.addItem(device_name)

    def connect_to_bluetooth(self, device_name):
        os.system(f"powershell -command \"Add-BluetoothDevice -DeviceName '{device_name}'\"")

    def get_system_info(self):
        system_info = f"OS: {platform.system()} {platform.release()}\n"
        system_info += f"Version: {platform.version()}\n"
        system_info += f"Machine: {platform.machine()}\n"
        system_info += f"Processor: {platform.processor()}\n"
        system_info += f"RAM: {psutil.virtual_memory().total // (1024 ** 3)} GB\n"
        return system_info

    def open_terminal(self, event=None):
        current_dir = os.getcwd()
        superuser_mode = False

        if "Terminal" in self.open_windows:
            self.raise_or_restore(self.open_windows["Terminal"])
            return

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Terminal")
        window.setGeometry(300, 300, 800, 600)
        window.setStyleSheet("""
            background-color: black;
            color: #00ff00;
            font-family: Consolas;
            font-size: 12px;
        """)

        layout = QVBoxLayout(window)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        button_style = """
            QPushButton {
                background-color: black;
                color: green;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #333333;
            }
        """
        close_button_style = "background-color: #ff4444; color: white;"


        minimize_button = QPushButton("_")
        minimize_button.setFixedSize(QSize(30, 30))
        minimize_button.setStyleSheet(button_style)
        minimize_button.clicked.connect(window.showMinimized)
        
        maximize_button = QPushButton("□")
        maximize_button.setFixedSize(QSize(30, 30))
        maximize_button.setStyleSheet(button_style)
        maximize_button.clicked.connect(lambda: window.showMaximized() if not window.isMaximized() else window.showNormal())

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_layout = QHBoxLayout(title_bar)
        title_label = QLabel("Terminal")
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        close_button = QPushButton("✕")
        close_button.setFixedSize(20, 20)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(minimize_button)
        title_layout.addWidget(maximize_button)
        title_layout.addWidget(close_button)
        layout.addWidget(title_bar)

        self.terminal_output = QLabel("vLaunch Terminal v1.0\nType 'help' for commands list\n")
        self.terminal_input = QLineEdit()
        self.terminal_input.setStyleSheet("background: #002200; color: #00ff00;")

        layout.addWidget(self.terminal_output)
        layout.addWidget(self.terminal_input)

        def execute_command():
            nonlocal current_dir, superuser_mode
            command = self.terminal_input.text().strip()
            output = ""

            try:
                if command == "help":
                    help_text = [
                        "help      - Show this help",
                        "exit      - Close terminal",
                        "clear     - Clear screen",
                        "whoami    - Show current user",
                        "cd <dir>  - Change directory",
                        "dir       - List files",
                        "pkg-start - Run .vys package",
                        "su        - Superuser mode"
                    ]
                    if superuser_mode:
                        help_text += ["\nSuperuser commands:", "del <file> - Delete file", "update - System update"]
                    output = "\n".join(help_text)

                elif command == "exit":
                    window.close()
                    return

                elif command == "clear":
                    self.terminal_output.setText("")

                elif command.startswith("cd "):
                    new_dir = command[3:].strip()
                    try:
                        os.chdir(new_dir)
                        current_dir = os.getcwd()
                        output = f"Changed directory to: {current_dir}"
                    except Exception as e:
                        output = f"CD error: {str(e)}"

                elif command == "dir":
                    try:
                        output = "\n".join(os.listdir(current_dir))
                    except Exception as e:
                        output = f"DIR error: {str(e)}"

                elif command == "whoami":
                    try:
                        with open("C:\\vLaunch\\kernel\\config\\global.cfg", "r") as f:
                            for line in f:
                                if line.startswith("profile_1_name"):
                                    output = line.split("=")[1].strip()
                                    break
                    except Exception as e:
                        output = f"WHOAMI error: {str(e)}"

                elif command == "su":
                    try:
                        with open("C:\\vLaunch\\kernel\\config\\global.cfg", "r") as f:
                            correct_pass = None
                            for line in f:
                                if line.startswith("profile_1_pass"):
                                    correct_pass = line.split("=")[1].strip()
                                    break
                            
                        password, ok = QInputDialog.getText(
                            window, "Authentication", "Enter password:", 
                            QLineEdit.Password
                        )
                        
                        if ok and password == correct_pass:
                            superuser_mode = True
                            output = "Superuser mode activated"
                        else:
                            output = "Authentication failed"
                    
                    except Exception as e:
                        output = f"Auth error: {str(e)}"

                elif command.startswith("del ") or command == "update":
                    if not superuser_mode:
                        output = "Permission denied! Use 'su' first"
                    else:
                        if command.startswith("del "):
                            try:
                                file_path = command.split(" ", 1)[1]
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                    output = f"Deleted: {file_path}"
                                else:
                                    output = "File not found"
                            except Exception as e:
                                output = f"DELETE error: {str(e)}"
                        elif command == "update":
                            output = "System update initiated... (stub)"

                elif command.startswith("pkg-start "):
                    try:
                        vys_file = command.split(" ", 1)[1]
                        self.run_vys_package(self, vys_file)
                    except IndexError:
                        output = "Specify .vys file to run"
                    except Exception as e:
                        output = f"PKG-START error: {str(e)}"

                else:
                    output = f"Command not found: {command}"

            except Exception as e:
                output = f"Unexpected error: {str(e)}"

            update_output(command, output)

        self.terminal_input.returnPressed.connect(execute_command)
        
        def update_output(command, result):
            nonlocal current_dir
            new_text = f"{self.terminal_output.text()}\n{current_dir}> {command}\n{result}"
            self.terminal_output.setText(new_text)
            self.terminal_input.clear()

        self.terminal_input.returnPressed.connect(execute_command)

        def close_terminal():
            window.close()
            if "Terminal" in self.open_windows:
                del self.open_windows["Terminal"]
            self.update_dock()

        close_button.clicked.connect(lambda: close_terminal())
        window.closeEvent = lambda e: close_terminal()

        def handle_close_event(event):
            close_terminal()
            event.accept()

        self.terminal_input.returnPressed.connect(execute_command)
        close_button.clicked.connect(close_terminal)
        window.closeEvent = handle_close_event

        def mouse_press(event):
            if event.button() == Qt.LeftButton:
                window.old_pos = event.globalPos()

        def mouse_move(event):
            if hasattr(window, 'old_pos'):
                delta = QPoint(event.globalPos() - window.old_pos)
                window.move(window.pos() + delta)
                window.old_pos = event.globalPos()

        title_bar.mousePressEvent = mouse_press
        title_bar.mouseMoveEvent = mouse_move

        self.open_windows["Terminal"] = window
        self.update_dock()
        window.show()

    def update_dock(self):
        for i in reversed(range(self.dock_layout.count())):
            widget = self.dock_layout.itemAt(i).widget()
            if widget and widget not in [
                self.start_menu_button, 
                self.clock_applet,
                self.wlan_applet,
                self.battery_label
            ]:
                widget.deleteLater()

        for name, win in self.open_windows.items():
            btn = QPushButton(name)
            btn.setFixedSize(100, 40)
            btn.clicked.connect(lambda _, w=win: self.raise_or_restore(w))
            self.dock_layout.insertWidget(1, btn)

    def raise_or_restore(self, window):
        if window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()

    def on_window_close(self, window):
        if window.windowTitle() in self.open_windows:
            del self.open_windows[window.windowTitle()]
        self.update_dock()
    
if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    if len(sys.argv) < 2:
        print("KERNEL PANIC: 1 [EXTRA]")
        sys.exit(1)
    
    elif sys.argv[1] == "-auth8354":
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        
        lock_screen = LockScreen()
        lock_screen.show()
        
        try:
            sys.exit(app.exec_())
        except KeyboardInterrupt:
            print("\nApplication interrupted by user")
            app.quit()
    
    elif sys.argv[1] == "-auth8355":
        tui = TUI_label()
        tui.run()
    
    else:
        print(f"KERNEL PANIC: UNKNOWN ARGUMENT {sys.argv[1]}")
        sys.exit(2)