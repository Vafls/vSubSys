import sys
import os
import psutil
import time
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy, QMenu, QAction
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QDateTime
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QLineEdit
import random
from PyQt5.QtCore import QPropertyAnimation, QRect
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QCursor
import importlib.util
import zipfile
from PyQt5.QtWidgets import QListWidget, QStackedWidget
import platform
from PyQt5.QtWidgets import QMenuBar
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QSpacerItem
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QInputDialog
import shutil


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


class KernelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kernel_build_1.0.1")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.open_windows = {}

        self.desktop_widget = QWidget(self)
        self.desktop_layout = QVBoxLayout(self.desktop_widget)
        self.desktop_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.desktop_widget)

        self.add_settings_shortcut()
        self.add_camera_shortcut()
        self.add_terminal_shortcut()
        self.add_ide_shortcut()
        self.add_snake_shortcut()
        self.add_store_shortcut()

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

        self.init_clock_applet()
        self.init_wlan_applet()

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
    
    def show_start_menu(self):
        menu = QMenu(self)
        shutdown_action = QAction("Shutdown", self)
        shutdown_action.triggered.connect(self.shutdown)

        restart_action = QAction("Restart", self)
        restart_action.triggered.connect(self.restart)

        menu.addAction(shutdown_action)
        menu.addAction(restart_action)
        menu.exec_(self.mapToGlobal(QPoint(10, self.height() - 50)))

    def shutdown(self):
        QApplication.quit()

    def restart(self):
        QApplication.quit()
        os.system(f"python {sys.argv[0]}")

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
        close_button.clicked.connect(lambda: close_camera(window))
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
        menu_layout.setSpacing(1)

        disk_info_button = QPushButton("Disk Info", window)
        disk_info_button.clicked.connect(lambda: self.show_disk_info(content_layout))
        menu_layout.addWidget(disk_info_button)

        wifi_settings_button = QPushButton("Wi-Fi Settings", window)
        wifi_settings_button.clicked.connect(lambda: self.show_wifi_settings(content_layout))
        menu_layout.addWidget(wifi_settings_button)

        menu_widget = QWidget()
        menu_widget.setLayout(menu_layout)
        menu_widget.setFixedWidth(200)
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

        disk_info_label = QLabel(self.get_disk_info())
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

    def open_terminal(self=None, event=None):
    
        if "Terminal" in self.open_windows:
            window = self.open_windows["Terminal"]
            window.raise_()
            window.activateWindow()
            return

        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        window = QWidget()
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowTitle("Terminal")
        window.setGeometry(300, 200, 800, 600)
        window.setStyleSheet("border: 2px solid black; background-color: white;")

        layout = QVBoxLayout(window)

        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setStyleSheet("background-color: black; color: white;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Terminal")
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
        close_button.clicked.connect(lambda: close_terminal(window))
        title_layout.addWidget(close_button)

        layout.addWidget(title_bar)

        output_label = QLabel()
        output_label.setStyleSheet("background-color: black; color: white; padding: 5px;")
        output_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        output_label.setWordWrap(True)
        output_label.setText("Terminal started...\n")
        layout.addWidget(output_label)

        input_field = QLineEdit()
        input_field.setStyleSheet("background-color: black; color: white; padding: 5px;")
        layout.addWidget(input_field)

        current_dir = os.getcwd()

        def execute_command():
            nonlocal current_dir
            command = input_field.text().strip()
            output = ""

            if command.startswith("cd "):
                try:
                    new_dir = command[3:].strip()
                    os.chdir(new_dir)
                    current_dir = os.getcwd()
                    output = f"Changed directory to: {current_dir}"
                except Exception as e:
                    output = f"Error: {str(e)}"
            elif command == "dir":
                try:
                    files = os.listdir(current_dir)
                    output = "\n".join(files)
                except Exception as e:
                    output = f"Error: {str(e)}"
            elif command == "exit":
                close_terminal(window)
                return
            elif command == "whoami":
                try:
                    with open("C:\\vLaunch\\kernel\\config\\global.cfg", "r") as config_file:
                        for line in config_file:
                            if line.startswith("profile_1_name"):
                                output = line.split("=")[1].strip()
                                break
                except Exception as e:
                    output = f"Error: {str(e)}"
            elif command.startswith("pkg-start "):
                parts = command.split()
                if len(parts) < 2:
                    output = "Error: Choose the correct .vys file to run it.\nExample: pkg-start example.vys"
                else:
                    vys_file = parts[1]
                    try:
                        self.run_vys_package(vys_file)
                        output = f"The program {vys_file} is running..."
                    except Exception as e:
                        output = f"Error during the execution of the file: {str(e)}"
            elif command == "help":
                output = "Available commands: help, exit, whoami, cd, dir, pkg-start, su"
            elif command == "su":
                try:
                    with open("C:\\vLaunch\\kernel\\config\\global.cfg", "r") as config_file:
                        for line in config_file:
                            if line.startswith("profile_1_pass"):
                                correct_password = line.split("=")[1].strip()
                                break
                    password, ok = QInputDialog.getText(window, "Superuser Authentication", "Enter password:", QLineEdit.Password)
                    if ok and password == correct_password:
                        output = "Superuser mode activated. Available commands: del, update"
                        self.superuser_mode = True
                    else:
                        output = "Authentication failed. Incorrect password."
                except Exception as e:
                    output = f"Error: {str(e)}"
            elif command.startswith("del ") or command == "update":
                if not self.superuser_mode:
                    output = "You're not root!"
                else:
                    if command.startswith("del "):
                        try:
                            file_to_delete = command.split(" ", 1)[1]
                            if os.path.exists(file_to_delete):
                                os.remove(file_to_delete)
                                output = f"File {file_to_delete} deleted successfully."
                            else:
                                output = f"File {file_to_delete} not found."
                        except Exception as e:
                            output = f"Error: {str(e)}"
                    elif command == "update":
                        output = "System update initiated... (stub)"
                try:
                    file_to_delete = command.split(" ", 1)[1]
                    if os.path.exists(file_to_delete):
                        os.remove(file_to_delete)
                        output = f"File {file_to_delete} deleted successfully."
                    else:
                        output = f"File {file_to_delete} not found."
                except Exception as e:
                    output = f"Error: {str(e)}"
            elif self.superuser_mode and command == "update":
                output = "System update initiated... (stub)"
            else:
                output = f"Command not found: {command}"

            output_label.setText(output_label.text() + f"\n{current_dir}> {command}\n{output}\n")
            input_field.clear()

        input_field.returnPressed.connect(execute_command)

        def close_terminal(window):
            window.close()
            if "Terminal" in self.open_windows:
                del self.open_windows["Terminal"]
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

        self.open_windows["Terminal"] = window
        self.update_dock()

        window.show()


    def on_window_close(self, window):
        window_name = window.windowTitle()
        if window_name in self.open_windows:
            del self.open_windows[window_name]
        self.update_dock()

    def update_dock(self):

        for i in reversed(range(self.dock_layout.count())):
            item = self.dock_layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and widget not in {self.start_menu_button, self.battery_label, self.clock_applet, self.wlan_applet}:
                widget.setParent(None)

        if self.dock_layout.itemAt(0) is not None and self.dock_layout.itemAt(0).widget() != self.start_menu_button:
            self.dock_layout.insertWidget(0, self.start_menu_button)

        index = 1
        for name, window in self.open_windows.items():
            button = QPushButton(name)
            button.setFixedSize(100, 40)
            button.clicked.connect(lambda checked, win=window: win.showNormal())
            self.dock_layout.insertWidget(index, button)
            index += 1

        if self.dock_layout.count() > 1 and self.dock_layout.itemAt(self.dock_layout.count() - 2).widget() != self.clock_applet:
            self.dock_layout.insertWidget(self.dock_layout.count() - 1, self.clock_applet)

        if self.dock_layout.count() > 0 and self.dock_layout.itemAt(self.dock_layout.count() - 1).widget() != self.wlan_applet:
            self.dock_layout.insertWidget(self.dock_layout.count(), self.wlan_applet)

        if self.dock_layout.count() > 0 and self.dock_layout.itemAt(self.dock_layout.count() - 1).widget() != self.battery_label:
            self.dock_layout.addWidget(self.battery_label)

    def raise_or_restore(self, window):
        if window.isMinimized():
            window.showNormal()
        window.raise_()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    global lock_screen
    lock_screen = LockScreen()
    lock_screen.show()
    sys.exit(app.exec_())
    window.show()
    lock_screen = start_lock_screen(KernelWindow)
# BUILD_1.0.1