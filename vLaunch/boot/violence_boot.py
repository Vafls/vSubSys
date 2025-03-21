import os
import socket
import sys
import math
import colorsys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QLabel, QPushButton, QHBoxLayout
)
from PyQt5.QtGui import QPainter, QFont, QColor
from PyQt5.QtCore import QTimer, Qt, QCoreApplication, QSize, QPoint

config_path = r'C:\vLaunch\kernel\config\global.cfg'
kernel_path = r'C:\vLaunch\kernel\kernel.kernel'
if not os.path.exists(kernel_path):
    kernel_path = r'C:\vLaunch\kernel\kernel.py'

class DonutWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_donut()

    def init_donut(self):
        self.WIDTH, self.HEIGHT = 800, 600
        self.PIXEL_WIDTH, self.PIXEL_HEIGHT = 20, 20
        self.SCREEN_WIDTH = self.WIDTH // self.PIXEL_WIDTH
        self.SCREEN_HEIGHT = self.HEIGHT // self.PIXEL_HEIGHT
        self.SCREEN_SIZE = self.SCREEN_WIDTH * self.SCREEN_HEIGHT

        self.A, self.B = 0, 0
        self.THETA_SPACING = 10
        self.PHI_SPACING = 3
        self.CHARS = ".,-~:;=!*#$@"
        self.R1, self.R2 = 10, 20
        self.K2 = 200
        self.K1 = self.SCREEN_HEIGHT * self.K2 * 3 / (8 * (self.R1 + self.R2))
        self.hue = 0

        self.output = [' '] * self.SCREEN_SIZE
        self.zbuffer = [0] * self.SCREEN_SIZE

    def hsv2rgb(self, h, s, v):
        return tuple(round(i * 255) for i in colorsys.hsv_to_rgb(h, s, v))

    def update_donut(self):
        self.output = [' '] * self.SCREEN_SIZE
        self.zbuffer = [0] * self.SCREEN_SIZE

        for theta in range(0, 628, self.THETA_SPACING):
            for phi in range(0, 628, self.PHI_SPACING):
                cosA, sinA = math.cos(self.A), math.sin(self.A)
                cosB, sinB = math.cos(self.B), math.sin(self.B)
                costheta, sintheta = math.cos(theta), math.sin(theta)
                cosphi, sinphi = math.cos(phi), math.sin(phi)

                circlex = self.R2 + self.R1 * costheta
                circley = self.R1 * sintheta

                x = circlex * (cosB * cosphi + sinA * sinB * sinphi) - circley * cosA * sinB
                y = circlex * (sinB * cosphi - sinA * cosB * sinphi) + circley * cosA * cosB
                z = self.K2 + cosA * circlex * sinphi + circley * sinA
                ooz = 1 / z

                xp = int(self.SCREEN_WIDTH / 2 + self.K1 * ooz * x)
                yp = int(self.SCREEN_HEIGHT / 2 - self.K1 * ooz * y)

                position = xp + self.SCREEN_WIDTH * yp

                L = cosphi * costheta * sinB - cosA * costheta * sinphi - sinA * sintheta + cosB * (
                            cosA * sintheta - costheta * sinA * sinphi)

                if ooz > self.zbuffer[position]:
                    self.zbuffer[position] = ooz
                    luminance_index = int(L * 8)
                    self.output[position] = self.CHARS[luminance_index if luminance_index > 0 else 0]

        self.A += 0.15
        self.B += 0.035
        self.hue += 0.005

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont('Arial', 20))
        painter.setPen(QColor(*self.hsv2rgb(self.hue, 1, 1)))

        for i in range(self.SCREEN_HEIGHT):
            for j in range(self.SCREEN_WIDTH):
                char = self.output[i * self.SCREEN_WIDTH + j]
                x = j * self.PIXEL_WIDTH + self.PIXEL_WIDTH // 2
                y = i * self.PIXEL_HEIGHT + self.PIXEL_HEIGHT // 2
                painter.drawText(x, y, char)

class DonutApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(800, 1000)

        self.center()

        layout = QVBoxLayout()

        self.donut_widget = DonutWidget()
        self.donut_widget.setFixedSize(800, 600)
        layout.addWidget(self.donut_widget)

        self.console = QTextEdit(self)
        self.console.setReadOnly(True)
        self.console.setFont(QFont('Courier New', 12))
        self.console.setFixedHeight(200)
        layout.addWidget(self.console)

        self.input_line = QLineEdit(self)
        self.input_line.setFont(QFont('Courier New', 12))
        self.input_line.setFixedHeight(30)
        self.input_line.setPlaceholderText("Click here to type commands")
        self.input_line.mousePressEvent = self.show_instructions
        self.input_line.returnPressed.connect(self.process_input)
        layout.addWidget(self.input_line)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.donut_widget.update_donut)
        self.timer.start(1000 // 60)

        self.auto_start_timer = QTimer()
        self.auto_start_timer.timeout.connect(self.run_kernel)
        self.auto_start_timer.start(5000)

    def center(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def show_instructions(self, event):
        self.console.append("Type 'settings' to open settings or 'start' to boot")
        self.auto_start_timer.stop()
        QLineEdit.mousePressEvent(self.input_line, event)

    def process_input(self):
        user_input = self.input_line.text().strip().lower()
        self.input_line.clear()

        if user_input == "settings":
            self.console.append("Opening settings...")
            self.show_settings()
        elif user_input == "start":
            self.console.append("Starting boot...")
            self.run_kernel()
        else:
            self.console.append("Unknown command. Type 'settings' or 'start'.")

    def run_kernel(self):
        self.auto_start_timer.stop()
        #initialize_services()
        os.system(f"{sys.executable} {kernel_path} -auth8354")
        self.console.append("KERNEL: SUCCESS")
        QCoreApplication.quit()

    def show_settings(self):
        self.settings_window = SettingsWindow(self)
        self.settings_window.show()

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: black; color: white;")

        title_layout = QHBoxLayout()
        title_label = QLabel("Settings")
        title_label.setFont(QFont('Arial', 12))
        title_layout.addWidget(title_label)

        close_button = QPushButton("X")
        close_button.setFixedSize(QSize(30, 30))
        close_button.setStyleSheet("background-color: red; color: white;")
        close_button.clicked.connect(self.close)
        title_layout.addWidget(close_button)

        layout = QVBoxLayout()
        layout.addLayout(title_layout)

        settings_label = QLabel("TypeIgnore: True")
        settings_label.setFont(QFont('Arial', 12))
        layout.addWidget(settings_label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self.old_pos)
            self.move(self.pos() + delta)
            self.old_pos = event.globalPos()

def check_internet_connection():
    try:
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        return False

def main():
    if not check_internet_connection():
        print("WARNING: No internet connection detected. Updates and installations will not be possible without an internet connection.")

    app = QApplication(sys.argv)
    window = DonutApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()