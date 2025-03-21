import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
import webbrowser

local_version_file = r'C:\vLaunch\version_info.txt'

online_version_url = 'https://raw.githubusercontent.com/Vafls/vSubSys_UPD/main/version_info.txt'

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
        app = QApplication(sys.argv)
        window = QWidget()
        window.setWindowTitle('Update Available')

        layout = QVBoxLayout()

        label = QLabel(f'Available update: {update_message}')
        layout.addWidget(label)

        download_button = QPushButton('Download Update')
        download_button.clicked.connect(lambda: open_url('https://vafls.github.io/vSubSys_UPD/'))
        layout.addWidget(download_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(window.close)
        layout.addWidget(cancel_button)

        window.setLayout(layout)
        window.show()
        sys.exit(app.exec_())

def open_url(url):
    webbrowser.open(url)

if __name__ == '__main__':
    check_for_updates()
    print("sheila: SUCCESS")