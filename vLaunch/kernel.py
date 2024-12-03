import sys
import os
import psutil  # Для получения информации о батарее
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy, QMenu, QAction
from PyQt5.QtCore import Qt, QSize, QTimer, QDateTime
from PyQt5.QtGui import QPixmap


class AppWindow(QMainWindow):
    """Окно приложения (например, настройки)."""
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
        """Закрытие окна."""
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

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        background_path = "C:\\vLaunch\\source\\lock_screen_wallpaper.png"
        if os.path.exists(background_path):
            pixmap = QPixmap(background_path)
        else:
            pixmap = QPixmap(800, 600)
            pixmap.fill(Qt.black)

        background_label = QLabel(self)
        background_label.setPixmap(pixmap)
        background_label.setScaledContents(True)
        layout.addWidget(background_label)

        self.time_label = QLabel(self)
        self.time_label.setStyleSheet("color: white; font-size: 48px;")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        self.update_time()
        self.central_widget.mousePressEvent = self.launch_kernel
        self.central_widget.keyPressEvent = self.launch_kernel

    def update_time(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss\nddd, dd MMM yyyy")
        self.time_label.setText(current_time)
        QTimer.singleShot(1000, self.update_time)

    def launch_kernel(self, event=None):
        self.close()
        self.kernel_window = KernelWindow()
        self.kernel_window.show()


class CustomTitleBar(QWidget):
    def __init__(self, parent, window):
        super().__init__(parent)
        self.window = window
        self.setFixedHeight(30)
        self.setStyleSheet("background-color: black; color: white;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(window.windowTitle(), self)
        layout.addWidget(title_label)

        minimize_button = QPushButton("_", self)
        minimize_button.clicked.connect(window.showMinimized)
        layout.addWidget(minimize_button)

        maximize_button = QPushButton("□", self)
        maximize_button.clicked.connect(self.toggle_maximize_restore)
        layout.addWidget(maximize_button)

        close_button = QPushButton("X", self)
        close_button.clicked.connect(window.close)
        layout.addWidget(close_button)

    def toggle_maximize_restore(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()


class KernelWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom OS Kernel")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()

        self.open_windows = {}

        self.desktop_widget = QWidget(self)
        self.desktop_layout = QVBoxLayout(self.desktop_widget)
        self.desktop_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(self.desktop_widget)

        self.add_settings_shortcut()

        self.dock_panel = QFrame(self)
        self.dock_panel.setFixedHeight(60)
        self.dock_panel.setStyleSheet("background-color: gray;")
        self.desktop_layout.addStretch()
        self.desktop_layout.addWidget(self.dock_panel)

        self.dock_layout = QHBoxLayout(self.dock_panel)
        self.dock_layout.setContentsMargins(10, 5, 10, 5)

        self.start_menu_button = QPushButton("Меню Пуск", self)
        self.start_menu_button.setFixedSize(100, 40)
        self.start_menu_button.clicked.connect(self.show_start_menu)
        self.dock_layout.addWidget(self.start_menu_button)

        self.spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.dock_layout.addItem(self.spacer)

        self.battery_label = QLabel(self)
        self.dock_layout.addWidget(self.battery_label)

        self.battery_update_timer = QTimer(self)
        self.battery_update_timer.timeout.connect(self.update_battery_status)
        self.battery_update_timer.start(10000)
        self.update_battery_status()

    def add_settings_shortcut(self):
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

    def update_battery_status(self):
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            charging = battery.power_plugged
            self.battery_label.setText(f"Battery: {percent}% {'(Charging)' if charging else ''}")
        else:
            self.battery_label.setText("Battery info not available")

    def show_start_menu(self):
        menu = QMenu(self)
        shutdown_action = QAction("Завершение работы", self)
        shutdown_action.triggered.connect(self.shutdown)

        restart_action = QAction("Перезагрузка", self)
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

    def on_window_close(self, window):
        window_name = window.windowTitle()
        if window_name in self.open_windows:
            del self.open_windows[window_name]
        self.update_dock()

    def update_dock(self):
        while self.dock_layout.count() > 3:
            item = self.dock_layout.takeAt(1)
            if item is not None and item.widget() is not None:
                item.widget().setParent(None)

        for app_name, window in self.open_windows.items():
            button = QPushButton(app_name, self)
            button.setFixedSize(100, 40)
            button.clicked.connect(lambda checked, win=window: self.raise_or_restore(win))
            self.dock_layout.insertWidget(1, button)

    def raise_or_restore(self, window):
        if window.isMinimized():
            window.showNormal()
        window.raise_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    lock_screen = LockScreen()
    lock_screen.show()
    sys.exit(app.exec_())
