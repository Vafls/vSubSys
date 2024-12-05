import os
import subprocess
from colorama import init, Fore, Style
from tkinter import Tk, Label, Button
from PIL import Image, ImageTk
from datetime import datetime
import psutil
import curses
import random
import sys
from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import tkinter as tk
import time
from tkinter import messagebox
#import readline
from tkinter import ttk
import platform
from tkinter import filedialog
from pygame import mixer
import shutil
import urwid
from urllib.request import urlopen
import socket
import speedtest
import string
import importlib
from tkinter import scrolledtext

init()
def version():
    print("Версия оболочки:", (f"{Fore.GREEN}0.1{Style.RESET_ALL}"))

def gallery():
    class ImageGallery:
        def __init__(self, master):
            self.master = master
            self.master.title("Галерея изображений")

            self.image_path = "C:\\Users\\kosti\\Downloads\\UIforWindows\\media"
            self.image_list = self.get_image_list()
            self.current_index = 0

            self.display_image()

            self.prev_button = Button(master, text="Предыдущее фото", command=self.show_prev_image)
            self.prev_button.pack(side="left")

            self.next_button = Button(master, text="Следующее фото", command=self.show_next_image)
            self.next_button.pack(side="right")

        def get_image_list(self):
            image_list = [f for f in os.listdir(self.image_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
            return image_list

        def display_image(self):
            image_path = os.path.join(self.image_path, self.image_list[self.current_index])
            image = Image.open(image_path)
            image = image.resize((300, 300), Image.ANTIALIAS)
            photo = ImageTk.PhotoImage(image)

            if hasattr(self, 'image_label'):
                self.image_label.pack_forget()

            self.image_label = Label(self.master, image=photo)
            self.image_label.image = photo
            self.image_label.pack()

        def show_prev_image(self):
            if self.current_index > 0:
                self.current_index -= 1
            else:
                self.current_index = len(self.image_list) - 1
            self.display_image()

        def show_next_image(self):
            if self.current_index < len(self.image_list) - 1:
                self.current_index += 1
            else:
                self.current_index = 0
            self.display_image()

    if __name__ == "__main__":
        root = Tk()
        app = ImageGallery(root)
        root.mainloop()
    
def time():
    current_time = datetime.now().strftime("%H:%M:%S")
    print("Текущее время:", current_time)

def snake():
    pygame.init()

    pygame.display.set_caption("")

    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)

    CELL_SIZE = 20
    GRID_SIZE = 20
    SNAKE_SPEED = 15

    WINDOW_SIZE = (CELL_SIZE * GRID_SIZE, CELL_SIZE * GRID_SIZE)
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Snake Game")

    snake = [(5, 5), (5, 6), (5, 7)]
    snake_direction = (0, -1)

    fruit = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP] and snake_direction != (0, 1):
                snake_direction = (0, -1)
            elif keys[pygame.K_DOWN] and snake_direction != (0, -1):
                snake_direction = (0, 1)
            elif keys[pygame.K_LEFT] and snake_direction != (1, 0):
                snake_direction = (-1, 0)
            elif keys[pygame.K_RIGHT] and snake_direction != (-1, 0):
                snake_direction = (1, 0)

        head = (snake[0][0] + snake_direction[0], snake[0][1] + snake_direction[1])
        snake.insert(0, head)

        if head == fruit:
            fruit = (random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1))
        else:
            snake.pop()

        if (
            head[0] < 0 or head[0] >= GRID_SIZE or
            head[1] < 0 or head[1] >= GRID_SIZE or
            head in snake[1:]
        ):
            pygame.quit()
            sys.exit()

        screen.fill(BLACK)

        for segment in snake:
            pygame.draw.rect(screen, WHITE, (segment[0] * CELL_SIZE, segment[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        pygame.draw.rect(screen, RED, (fruit[0] * CELL_SIZE, fruit[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        pygame.display.flip()

        clock.tick(SNAKE_SPEED)

def battery():
    battery = psutil.sensors_battery()
    percent = battery.percent
    power_plugged = battery.power_plugged

    if power_plugged:
        status = "Зарядка"
    else:
        status = "Разрядка"

    print(f"Уровень батареи: {percent}% ({status})")

def reboot():
    try:
        os.system("shutdown /r /t 1")
    except Exception as e:
        print(f"Ошибка при перезагрузке компьютера: {e}")

def shutdown():
    try:
        os.system("shutdown /s /t 1")
    except Exception as e:
        print(f"Ошибка при выключении компьютера: {e}")

def standby():
    def get_battery_status():
        battery = psutil.sensors_battery()
        percent = battery.percent
        return percent

    def update_status():
        while True:
            battery_percent = get_battery_status()
            if battery_percent < 100:
                show_standby_window(battery_percent)
                break
            time.sleep(5)

    def show_standby_window(battery_percent):
        standby_window = tk.Tk()
        standby_window.title("Standby Mode")
        standby_window.geometry("300x150")
        standby_window.configure(bg="black")

        time_label = Label(standby_window, text="", font=("Helvetica", 20), fg="white", bg="black")
        time_label.pack(pady=20)

        battery_label = Label(standby_window, text="", font=("Helvetica", 16), fg="white", bg="black")
        battery_label.pack(pady=10)

        def update_labels():
            current_time = time.strftime("%H:%M:%S")
            time_label.config(text=f"Time: {current_time}")
            battery_label.config(text=f"Battery: {battery_percent}%")

            standby_window.after(1000, update_labels)

        update_labels()
        standby_window.mainloop()

    if __name__ == "__main__":
        while True:
            if psutil.sensors_battery().power_plugged:
                update_status()
            time.sleep(5)

def store():
    class App:
        def __init__(self, root):
            self.root = root
            self.root.title("Магазин приложений")

            self.applications = [
                {"name": "App1", "description": "Описание приложения 1", "github_url": "https://github.com/app1.git"},
                {"name": "App2", "description": "Описание приложения 2", "github_url": "https://github.com/app2.git"},
            ]

            self.create_main_window()

        def create_main_window(self):
            self.app_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE, width=50)
            self.install_button = tk.Button(self.root, text="Установить", command=self.install_selected_app)
        
            self.app_listbox.pack(pady=10)
            self.install_button.pack(pady=10)

            for app in self.applications:
                self.app_listbox.insert(tk.END, app["name"])

            self.app_listbox.bind("<ButtonRelease-1>", self.show_app_info)

        def show_app_info(self, event):
            selected_index = self.app_listbox.curselection()
            if selected_index:
                selected_app = self.applications[selected_index[0]]
                messagebox.showinfo(selected_app["name"], selected_app["description"])

        def install_selected_app(self):
            selected_index = self.app_listbox.curselection()
            if selected_index:
                selected_app = self.applications[selected_index[0]]
                git_command = f"git clone {selected_app['github_url']}"
                subprocess.run(git_command, shell=True)
                messagebox.showinfo("Установка завершена", f"{selected_app['name']} успешно установлено.")

    root = tk.Tk()
    app = App(root)
    root.mainloop()

def text():
    def main():
        text = []

        while True:
            for line in text:
                print(line)

            user_input = input(f"Row: {len(text) + 1}, Col: {len(text[-1]) + 1} > ")

            if user_input.lower() == 'exit':
                break
            elif user_input == '':
                text.append('')
            elif user_input.startswith('del'):
                if len(text[-1]) > 0:
                    text[-1] = text[-1][:-1]
            else:
                text[-1] += user_input

    if __name__ == "__main__":
        main()

def calculator():
    while True:
        expression = input("Введите выражение (или 'exit' для выхода): ")
        if expression.lower() == 'exit':
            break
        try:
            result = eval(expression)
            print("Результат:", result)
        except Exception as e:
            print("Ошибка:", e)
    #if __name__ == "__main__":
        #calculator()

def pkg():
    while True:
        package_user_input = input("Введите команду для package: ").strip()
        if package_user_input.lower() == "exit":
            break
        elif package_user_input.lower() == "exit pkg":
            main()
        else:
            print("Неизвестная команда:", (f"{Fore.RED}{package_user_input}{Style.RESET_ALL}"))
    #if __name__ == "__main__":
        #pkg()
            
def phoneui():
    class AndroidUI(tk.Tk):
        def __init__(self):
            super().__init__()

            self.title("Android-like UI")
            #self.geometry("600x800")
            self.geometry("300x400")

            self.desktop = tk.Frame(self, bg="white", height=600)
            self.desktop.pack(fill=tk.BOTH, expand=True)

            self.control_panel = ttk.Frame(self, padding=(10, 5))
            self.control_panel.pack(fill=tk.X)

            self.volume_label = ttk.Label(self.control_panel, text="Volume")
            self.volume_label.grid(row=0, column=0, padx=10)

            self.volume_slider = ttk.Scale(self.control_panel, from_=0, to=100, orient=tk.HORIZONTAL, length=100)
            self.volume_slider.grid(row=0, column=1, padx=10)

            self.brightness_label = ttk.Label(self.control_panel, text="Brightness")
            self.brightness_label.grid(row=0, column=2, padx=10)

            self.brightness_slider = ttk.Scale(self.control_panel, from_=0, to=100, orient=tk.HORIZONTAL, length=100)
            self.brightness_slider.grid(row=0, column=3, padx=10)

            self.wifi_label = ttk.Label(self.control_panel, text="Wi-Fi: Disconnected")
            self.wifi_label.grid(row=1, column=0, padx=10)

            self.bluetooth_label = ttk.Label(self.control_panel, text="Bluetooth: Disconnected")
            self.bluetooth_label.grid(row=1, column=1, padx=10)

            self.create_shortcut("Calculator", self.calculator, r"C:\vLaunch\custom_kernel\multicore\icons\calculator.png")
            self.create_shortcut("YouTube", self.youtube, r"C:\vLaunch\custom_kernel\multicore\icons\youtube.png")
            self.create_shortcut("Web", self.web, r"C:\vLaunch\custom_kernel\multicore\icons\web.png")

            self.clock_label = tk.Label(self.desktop, text="", font=("Helvetica", 16))
            self.clock_label.place(relx=0.5, rely=0.1, anchor=tk.CENTER)
            self.update_clock()

            self.battery_label = tk.Label(self.desktop, text="Battery: 100%", font=("Helvetica", 12))
            self.battery_label.place(relx=0.5, rely=0.9, anchor=tk.CENTER)

            self.mainloop()

        def create_shortcut(self, name, command, icon_path):
            icon = Image.open(icon_path)
            icon = ImageTk.PhotoImage(icon.resize((50, 50), Image.ANTIALIAS))
            button = tk.Button(self.desktop, text=name, image=icon, compound=tk.TOP, command=command)
            button.image = icon
            button.pack(side=tk.LEFT, padx=10, pady=10)

        def calculator(self):
            print("Launching Calculator")

        def youtube(self):
            print("Launching YouTube")

        def web(self):
            print("Launching Web")

        def update_clock(self):
            from time import strftime
            current_time = strftime('%H:%M:%S %p')
            self.clock_label.configure(text=current_time)
            self.after(1000, self.update_clock)

    if __name__ == "__main__":
        app = AndroidUI()

def clear():
    operating_system = platform.system().lower()

    if operating_system == "windows":
        os.system("cls")
    elif operating_system == "darwin":
        os.system("clear")
    elif operating_system == "linux":
        os.system("clear")
    else:
        os.system("clear")

def desktopui():
    class MacOSUI(tk.Tk):
        def __init__(self):
            super().__init__()

            self.title("macOS-like UI")
            self.geometry("800x600")

            self.desktop = tk.Frame(self, bg="#f0f0f0", height=500)
            self.desktop.pack(fill=tk.BOTH, expand=True)

            self.dock_panel = tk.Frame(self, height=50, bg="#2c2c2c")
            self.dock_panel.pack(fill=tk.X, side=tk.BOTTOM)

            self.create_shortcut("calculator", self.calculator, "calculator.png")
            self.create_shortcut("youtube", self.youtube, "youtube.png")
            self.create_shortcut("web", self.web, "web.png")

            self.battery_icon = self.load_icon("battery.png", size=(30, 30))
            self.battery_label = ttk.Label(self.dock_panel, image=self.battery_icon)
            self.battery_label.grid(row=0, column=0, padx=10)

            self.time_label = ttk.Label(self.dock_panel, text="", font=("Helvetica", 12), foreground="white")
            self.time_label.grid(row=0, column=1, padx=10)

            self.wifi_icon = self.load_icon("wifi.png", size=(30, 30))
            self.wifi_label = ttk.Label(self.dock_panel, image=self.wifi_icon)
            self.wifi_label.grid(row=0, column=2, padx=10)

            self.bluetooth_icon = self.load_icon("bluetooth.png", size=(30, 30))
            self.bluetooth_label = ttk.Label(self.dock_panel, image=self.bluetooth_icon)
            self.bluetooth_label.grid(row=0, column=3, padx=10)

            self.startup_icon = self.load_icon("startup.png", size=(30, 30))
            self.startup_button = ttk.Button(self.dock_panel, image=self.startup_icon, command=self.show_start_menu)
            self.startup_button.grid(row=0, column=4, padx=10)

            self.update_clock()
            self.mainloop()

        def create_shortcut(self, name, command, icon_path):
            icon = self.load_icon(icon_path, size=(50, 50))
            button = tk.Button(self.desktop, text=name, image=icon, compound=tk.TOP, command=command)
            button.image = icon
            button.pack(side=tk.LEFT, padx=10, pady=10)

            self.add_to_dock(icon, name, command)

        def load_icon(self, path, size):
            icon = Image.open(path)
            icon = ImageTk.PhotoImage(icon.resize(size, Image.ANTIALIAS))
            return icon

        def calculator(self):
            print("Launching Calculator")
            self.add_to_dock(self.load_icon("calculator.png", size=(30, 30)), "calculator", self.calculator)

        def youtube(self):
            print("Launching YouTube")
            self.add_to_dock(self.load_icon("youtube.png", size=(30, 30)), "youtube", self.youtube)

        def web(self):
            print("Launching Web")
            self.add_to_dock(self.load_icon("web.png", size=(30, 30)), "web", self.web)

        def add_to_dock(self, icon, name, command):
            button = tk.Button(self.dock_panel, image=icon, command=command)
            button.image = icon
            button.grid(row=0, column=len(self.dock_panel.grid_slaves()), padx=5)

        def update_clock(self):
            from time import strftime
            current_time = strftime('%H:%M:%S %p')
            self.time_label.configure(text=current_time)
            self.after(1000, self.update_clock)

        def show_start_menu(self):
            start_menu = tk.Menu(self, tearoff=0)
            start_menu.add_command(label="Выключить", command=self.shutdown)
            start_menu.add_command(label="Перезагрузить", command=self.restart)
            start_menu.add_command(label="Спящий режим", command=self.sleep)
            self.startup_button["menu"] = start_menu

        def shutdown(self):
            print("Shutting down")
            subprocess.run(["shutdown", "/s", "/t", "1"])

        def restart(self):
            print("Restarting")
            subprocess.run(["shutdown", "/r", "/t", "1"])

        def sleep(self):
            print("Sleeping")
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])

    if __name__ == "__main__":
        app = MacOSUI()

def consoleui():
    class XboxOneUI(tk.Tk):
        def __init__(self):
            super().__init__()

            self.title("Xbox One-like UI")
            self.geometry("800x600")

            self.app_menu = tk.Frame(self, height=80, bg="#141414")
            self.app_menu.pack(fill=tk.X)

            self.create_app_button("calculator", self.calculator, "calculator.png")
            self.create_app_button("youtube", self.youtube, "youtube.png")
            self.create_app_button("web", self.web, "web.png")

            self.quick_panel = tk.Frame(self, height=80, bg="#1c1c1c")
            self.quick_panel.pack(fill=tk.X)

            self.create_quick_widget("battery.png", "Battery")
            self.create_quick_widget("wifi.png", "Wi-Fi")
            self.create_quick_widget("bluetooth.png", "Bluetooth")

            self.time_label = ttk.Label(self.quick_panel, text="", font=("Helvetica", 12), foreground="white")
            self.time_label.pack(side=tk.RIGHT, padx=20)

            self.update_clock()
            self.mainloop()

        def create_app_button(self, name, command, icon_path):
            icon = self.load_icon(icon_path, size=(50, 50))
            button = tk.Button(self.app_menu, text=name, image=icon, compound=tk.TOP, command=command, bg="#141414", fg="white")
            button.image = icon
            button.pack(side=tk.LEFT, padx=20, pady=10)

        def create_quick_widget(self, icon_path, text):
            icon = self.load_icon(icon_path, size=(30, 30))
            label = ttk.Label(self.quick_panel, image=icon, text=text, compound=tk.TOP, foreground="white")
            label.image = icon
            label.pack(side=tk.LEFT, padx=20, pady=10)

        def load_icon(self, path, size):
            icon = Image.open(path)
            icon = ImageTk.PhotoImage(icon.resize(size, Image.ANTIALIAS))
            return icon

        def calculator(self):
            print("Launching Calculator")

        def youtube(self):
            print("Launching YouTube")

        def web(self):
            print("Launching Web")

        def update_clock(self):
            from time import strftime
            current_time = strftime('%H:%M:%S %p')
            self.time_label.configure(text=current_time)
            self.after(1000, self.update_clock)

    if __name__ == "__main__":
        app = XboxOneUI()

def video():
    class VideoPlayer:
        def __init__(self, root):
            self.root = root
            self.root.title("Видео Плеер")

            self.video_path = None
            self.current_video_index = 0
            self.video_list = []

            mixer.init()

            self.create_ui()

        def create_ui(self):
            self.btn_open = tk.Button(self.root, text="Открыть папку", command=self.open_folder)
            self.btn_open.pack(pady=10)

            self.btn_play = tk.Button(self.root, text="Воспроизвести", command=self.play_video)
            self.btn_play.pack(pady=10)

            self.scan_folder()

        def open_folder(self):
            folder_path = filedialog.askdirectory()

            if folder_path:
                self.video_path = folder_path
                self.scan_folder()

        def scan_folder(self):
            self.video_list = [f for f in os.listdir(self.video_path) if f.endswith(('.mp4', '.avi', '.mkv'))]

            self.current_video_index = 0

        def play_video(self):
            if not self.video_list:
                print("Выберите папку с видеофайлами.")
                return

            video_file = os.path.join(self.video_path, self.video_list[self.current_video_index])

            mixer.music.load(video_file)
            mixer.music.play()

            print(f"Воспроизводится: {video_file}")

        def run(self):
            self.root.mainloop()

    if __name__ == "__main__":
        root = tk.Tk()
        player = VideoPlayer(root)
        player.run()

def processes():
    class ProcessManager:
        def __init__(self, root):
            self.root = root
            self.root.title("Процесс-Менеджер")

            self.tree = ttk.Treeview(self.root, columns=("PID", "Name", "Status"))
            self.tree.heading("PID", text="PID")
            self.tree.heading("Name", text="Name")
            self.tree.heading("Status", text="Status")
            self.tree.pack(expand=True, fill="both")

            self.btn_refresh = tk.Button(self.root, text="Обновить", command=self.refresh_processes)
            self.btn_refresh.pack(pady=10)

            self.btn_terminate = tk.Button(self.root, text="Завершить процесс", command=self.terminate_process)
            self.btn_terminate.pack(pady=10)

            self.refresh_processes()

        def refresh_processes(self):
            for item in self.tree.get_children():
                self.tree.delete(item)

            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                processes.append((proc.info['pid'], proc.info['name'], proc.info['status']))

            for pid, name, status in processes:
                self.tree.insert("", "end", values=(pid, name, status))

        def terminate_process(self):
            selected_item = self.tree.selection()
            if not selected_item:
                print("Выберите процесс для завершения.")
                return

            pid = self.tree.item(selected_item)['values'][0]

            try:
                os.system(f"taskkill /F /PID {pid}")
                print(f"Процесс с PID {pid} завершен.")
            except Exception as e:
                print(f"Ошибка при завершении процесса: {e}")

    if __name__ == "__main__":
        root = tk.Tk()
        manager = ProcessManager(root)
        root.mainloop()

def files():
    class SimpleFileManager:
        def __init__(self, root):
            self.root = root
            self.root.title("Простой файловый менеджер")

            self.current_path = tk.StringVar()
            self.create_ui()

        def create_ui(self):
            path_label = tk.Label(self.root, textvariable=self.current_path, anchor="w", padx=10)
            path_label.pack(fill="x")

            self.listbox = tk.Listbox(self.root, selectmode=tk.SINGLE, height=20, width=50)
            self.listbox.pack(pady=10)

            frame_buttons = tk.Frame(self.root)
            frame_buttons.pack()

            btn_open = tk.Button(frame_buttons, text="Открыть", command=self.open_directory)
            btn_open.grid(row=0, column=0, padx=5)

            btn_copy = tk.Button(frame_buttons, text="Копировать", command=self.copy_file)
            btn_copy.grid(row=0, column=1, padx=5)

            btn_paste = tk.Button(frame_buttons, text="Вставить", command=self.paste_file)
            btn_paste.grid(row=0, column=2, padx=5)

            btn_delete = tk.Button(frame_buttons, text="Удалить", command=self.delete_file)
            btn_delete.grid(row=0, column=3, padx=5)

            self.open_directory()

        def open_directory(self):
            folder_path = filedialog.askdirectory()

            if folder_path:
                self.current_path.set(folder_path)
                self.list_directory(folder_path)

        def list_directory(self, folder_path):
            self.listbox.delete(0, tk.END)

            try:
                items = os.listdir(folder_path)

                for item in items:
                    self.listbox.insert(tk.END, item)

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при открытии директории: {e}")

        def copy_file(self):
            selected_item = self.listbox.get(tk.ACTIVE)
            if not selected_item:
                messagebox.showwarning("Предупреждение", "Выберите файл или папку для копирования.")
                return

            source_path = os.path.join(self.current_path.get(), selected_item)

            self.copied_item = {"path": source_path, "is_dir": os.path.isdir(source_path)}
            messagebox.showinfo("Информация", f"{selected_item} скопирован в буфер обмена.")

        def paste_file(self):
            if not hasattr(self, 'copied_item'):
                messagebox.showwarning("Предупреждение", "Нет элемента для вставки.")
                return

            destination_path = self.current_path.get()
            source_path = self.copied_item["path"]

            try:
                if self.copied_item["is_dir"]:
                    shutil.copytree(source_path, os.path.join(destination_path, os.path.basename(source_path)))
                else:
                    shutil.copy2(source_path, destination_path)

                messagebox.showinfo("Информация", "Элемент успешно вставлен.")
                self.list_directory(destination_path)

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при вставке элемента: {e}")

        def delete_file(self):
            selected_item = self.listbox.get(tk.ACTIVE)
            if not selected_item:
                messagebox.showwarning("Предупреждение", "Выберите файл или папку для удаления.")
                return

            item_path = os.path.join(self.current_path.get(), selected_item)

            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)

                messagebox.showinfo("Информация", f"{selected_item} успешно удален.")
                self.list_directory(self.current_path.get())

            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении элемента: {e}")

    if __name__ == "__main__":
        root = tk.Tk()
        file_manager = SimpleFileManager(root)
        root.mainloop()

def to():
    def to(directory):
        try:
            os.chdir(directory)
            print(f"Текущая директория: {os.getcwd()}")
        except FileNotFoundError:
            print(f"Директория {directory} не найдена.")
        except Exception as e:
            print(f"Ошибка: {e}")

    if __name__ == "__main__":
        to("C:\\Users")
        to("..")
        to("C:\\")

def tui():
    def calculator():
        return "Launching calculator..."

    def web():
        return "Launching web..."

    def youtube():
        return "Launching youtube..."

    def get_battery_level():
        battery = psutil.sensors_battery()
        return f"Battery Level: {battery.percent}%"

    def is_wifi_connected():
        try:
            urlopen("http://www.google.com", timeout=1)
            return "Wi-Fi: Connected"
        except:
            return "Wi-Fi: Disconnected"

    def is_bluetooth_connected():
        return "Bluetooth: Connected"

    class TUIApp:
        def __init__(self):
            self.header = urwid.Text("TUI Application", align='center')
            self.menu = urwid.Text("Press 'q' to exit\n\n1. Calculator\n2. Web\n3. YouTube", align='left')
            self.status = urwid.Text("", align='left')
            self.footer = urwid.Text("", align='right')

            self.layout = urwid.Pile([self.header, self.menu, self.status, self.footer])

        def main(self, loop, user_input):
            if user_input == 'q':
                raise urwid.ExitMainLoop()

            elif user_input == '1':
                self.status.set_text(calculator())

            elif user_input == '2':
                self.status.set_text(web())

            elif user_input == '3':
                self.status.set_text(youtube())

            else:
                self.status.set_text("Invalid input. Press 'q' to exit.")

            now = datetime.now()
            current_time = now.strftime("Time: %H:%M:%S")
            battery_level = get_battery_level()
            wifi_status = is_wifi_connected()
            bluetooth_status = is_bluetooth_connected()

            self.footer.set_text(f"{current_time} | {battery_level} | {wifi_status} | {bluetooth_status}")

    app = TUIApp()

    def on_input(key):
        app.main(loop, key)

    loop = urwid.MainLoop(app.layout, unhandled_input=on_input)
    loop.run()

def device():
    def get_windows_version():
        version = platform.version()
        if '10.0.19041' in version:
            return 'Windows 10'
        elif '10.0.22000' in version:
            return 'Windows 11'
        elif '6.1' in version:
            return 'Windows 7'
        else:
            return 'Unknown Windows Version'

    def get_system_info():
        system_info = {
            'OS': get_windows_version(),
            'Build': platform.version(),
            'RAM': f'{psutil.virtual_memory().total / (1024 ** 3):.2f} GB',
            'Processor': platform.processor(),
            'GPU': 'TODO: Implement GPU retrieval',
            'Disk': f'{psutil.disk_usage("/").total / (1024 ** 3):.2f} GB',
            'Host': socket.gethostname(),
            'ASCII_art': get_windows_ascii_art()
        }
        return system_info

    def get_windows_ascii_art():
        windows_version = get_windows_version()
        if windows_version == 'Windows 7':
            return '''
            Your Windows 7 ASCII art goes here
            '''
        elif windows_version == 'Windows 10':
            return '''
            Your Windows 10 ASCII art goes here
            '''
        elif windows_version == 'Windows 11':
            return '''
            Your Windows 11 ASCII art goes here
            '''
        else:
            return 'Unknown Windows Version ASCII art'

    def display_system_info(system_info):
        for key, value in system_info.items():
            print(f'{key}: {value}')

    if __name__ == '__main__':
        system_info = get_system_info()
        display_system_info(system_info)

def restart():
    python_executable = sys.executable
    script_path = os.path.abspath(sys.argv[0])
    os.execl(python_executable, python_executable, script_path, *sys.argv[1:])

def networkscan():
    def scan(target, ports):
        print(f"Scanning target: {target}")
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((target, port))
            if result == 0:
                print(f"Port {port}: Open")
            else:
                print(f"Port {port}: Closed")
            sock.close()

    if __name__ == "__main__":
        target_host = input("Enter target IP address: ")
        target_ports = list(map(int, input("Enter target ports (comma separated): ").split(',')))

        scan(target_host, target_ports)

#def gui():
    #subprocess.run(["gui.exe"])

def load_module(module_name, key, modules_keys):
    if key == modules_keys.get(module_name):
        module = importlib.import_module(module_name)
        module.app()

    if __name__ == "__main__":
        modules_keys = {"web": "23k"}

    user_input = input("Введите модуль (например, 'web'): ").lower()
    key = input("Введите ключ для модуля (если есть): ")

    load_module(user_input, key, modules_keys)


def gui():
    class WindowSystem:
        def __init__(self, root):
            self.root = root
            self.root.title("Windows Explorer")
            self.root.geometry("1280x600")
            self.root.attributes("-fullscreen", True)
            self.hidden_windows = []

            self.desktop = Desktop(self.root)
            self.taskbar = Taskbar(self.root, self.desktop)
            self.windows = []

        def run(self):
            self.root.mainloop()

    class Desktop(tk.Frame):
        def __init__(self, master):
            super().__init__(master, bg="lightgray")
            self.master = master
            self.pack(fill=tk.BOTH, expand=True)

            self.create_shortcuts()

        def create_shortcuts(self):
            web_icon = tk.PhotoImage(file="web.png").subsample(6, 6)
            calculator_icon = tk.PhotoImage(file="calculator.png").subsample(6, 6)
            youtube_icon = tk.PhotoImage(file="youtube.png").subsample(4, 4)
            videos_icon = tk.PhotoImage(file="videos.png").subsample(4, 4)

            web_button = tk.Button(self, image=web_icon, command=self.web)
            web_button.image = web_icon
            web_button.grid(row=10, column=10, padx=10, pady=10)

            calculator_button = tk.Button(self, image=calculator_icon, command=self.calculator)
            calculator_button.image = calculator_icon
            calculator_button.grid(row=10, column=20, padx=10, pady=10)

            youtube_button = tk.Button(self, image=youtube_icon, command=self.youtube)
            youtube_button.image = youtube_icon
            youtube_button.grid(row=10, column=30, padx=10, pady=10)

            videos_button = tk.Button(self, image=videos_icon, command=self.videos)
            videos_button.image = videos_icon
            videos_button.grid(row=10, column=40, padx=10, pady=10)

        def web(self):
            self.master.windows.append(Window("Web"))

        def calculator(self):
            self.master.hidden_windows = [win for win in self.master.hidden_windows if not win.winfo_exists()] #taskbar mode
            if not self.master.hidden_windows: #taskbar mode
                app = CalculatorApp(tk.Tk(), self.master) #taskbar mode
            else: #taskbarmode
                app = CalculatorApp(self.master.hidden_windows.pop(), self.master) #taskbar mode
            self.master.windows.append(app) #taskbarmode

            class CalculatorApp:
                def __init__(self, master, window_system): #добавление windows_system
                    self.master = master
                    self.window_system = window_system #режим отображения на taskbar, добавить к каждому новому приложению
                    master.title("Калькулятор")
                    master.geometry("400x500")
                    master.protocol("WM_DELETE_WINDOW", self.on_close) #режим отображения на taskbar, добавить к каждому новому приложению

                    self.result_var = tk.StringVar()
                    self.result_var.set("0")

                    self.create_widgets()

                def create_widgets(self):
                    result_entry = tk.Entry(self.master, textvariable=self.result_var, font=('Arial', 14), bd=10, relief="ridge", justify="right")
                    result_entry.grid(row=0, column=0, columnspan=4)

                    buttons = [
                        '7', '8', '9', '/',
                        '4', '5', '6', '*',
                        '1', '2', '3', '-',
                        '0', '.', '=', '+'
                    ]

                    row_val = 1
                    col_val = 0

                    for button in buttons:
                        tk.Button(self.master, text=button, command=lambda b=button: self.on_button_click(b)).grid(row=row_val, column=col_val, sticky='nsew')
                        col_val += 1
                        if col_val > 3:
                            col_val = 0
                            row_val += 1

                    for i in range(4):
                        self.master.grid_rowconfigure(i, weight=1)
                        self.master.grid_columnconfigure(i, weight=1)

                def on_button_click(self, button):
                    current_text = self.result_var.get()

                    if button == '=':
                        try:
                            result = eval(current_text)
                            self.result_var.set(str(result))
                        except Exception as e:
                            self.result_var.set("Ошибка")

                    elif button == 'C':
                        self.result_var.set("0")

                    else:
                        if current_text == '0':
                            self.result_var.set(button)
                        else:
                            self.result_var.set(current_text + button)
                
                def on_close(self):
                    self.master.withdraw()  #скрыть окно, режим отображения на taskbar, добавить к каждому новому приложению
                    self.window_system.hidden_windows.append(self.master)  #режим отображения на taskbar, добавить к каждому новому приложению

            if __name__ == "__main__":
                root = tk.Tk()
                app = WindowSystem(root) #taskbar mode
                app.calculator() #taskbar mode
                root.mainloop()

        def youtube(self):
            self.master.windows.append(Window("YouTube"))
    
        def videos(self):
                class VideoPlayer:
                    def __init__(self, root):
                        self.root = root
                        self.root.title("Видео Плеер")
                        self.result_var = tk.StringVar()
                        self.result_var.set("0")

                        self.video_path = None
                        self.current_video_index = 0
                        self.video_list = []

                        mixer.init()

                        self.create_ui()

                    def create_ui(self):
                        self.btn_open = tk.Button(self.root, text="Открыть папку", command=self.open_folder)
                        self.btn_open.pack(pady=10)

                        self.btn_play = tk.Button(self.root, text="Воспроизвести", command=self.play_video)
                        self.btn_play.pack(pady=10)

                        self.scan_folder()

                    def open_folder(self):
                        folder_path = filedialog.askdirectory()

                        if folder_path:
                            self.video_path = folder_path
                            self.scan_folder()

                    def scan_folder(self):
                        self.video_list = [f for f in os.listdir(self.video_path) if f.endswith(('.mp4', '.avi', '.mkv'))]

                        self.current_video_index = 0

                    def play_video(self):
                        if not self.video_list:
                            print("Выберите папку с видеофайлами.")
                            return

                        video_file = os.path.join(self.video_path, self.video_list[self.current_video_index])

                        mixer.music.load(video_file)
                        mixer.music.play()

                        print(f"Воспроизводится: {video_file}")

                    def run(self):
                        self.root.mainloop()

                if __name__ == "__main__":
                    root = tk.Tk()
                    player = VideoPlayer(root)
                    player.run()


    class Taskbar(tk.Frame):
        def __init__(self, master, desktop):
            super().__init__(master, bg="gray")
            self.master = master
            self.desktop = desktop
            self.pack(side=tk.BOTTOM, fill=tk.X)

            self.start_button = tk.Button(self, text="Пуск", command=self.show_start_menu)
            self.start_button.pack(side=tk.LEFT, padx=5)

            self.time_label = tk.Label(self, text=self.get_current_time(), bg="gray", fg="white")
            self.time_label.pack(side=tk.RIGHT, padx=5)

            self.battery_label = tk.Label(self, text="Battery: 100%", bg="gray", fg="white")
            self.battery_label.pack(side=tk.RIGHT, padx=5)

        def show_start_menu(self):
            menu = tk.Menu(self.master, tearoff=0)
            menu.add_command(label="Выключение", command=self.master.quit)
            menu.add_command(label="Перезагрузка", command=self.restart)
            menu.add_command(label="Сон", command=self.sleep)
            menu.post(self.start_button.winfo_rootx(), self.start_button.winfo_rooty() + self.start_button.winfo_height())
        
        def restart(self):
            print("Restarting...")

        def sleep(self):
            print("Sleeping...")

        def update_time(self):
            self.time_label["text"] = self.get_current_time()
            self.after(1000, self.update_time)

        def get_current_time(self):
            return datetime.now().strftime("%H:%M:%S")

    class Window(tk.Toplevel):
        def __init__(self, title):
            super().__init__()
            self.title(title)
            self.geometry("400x300")

            self.label = tk.Label(self, text=title)
            self.label.pack(padx=10, pady=10)

            self.button_close = tk.Button(self, text="Закрыть", command=self.destroy)
            self.button_close.pack(pady=10)

    if __name__ == "__main__":
        root = tk.Tk()
        app = WindowSystem(root)
        app.taskbar.update_time()
        app.run()

def speedtestr():
    st = speedtest.Speedtest()

    print("Тестирование скорости загрузки...")
    download_speed = st.download() / 10**6
    print(f"Скорость загрузки: {download_speed:.2f} Mbps")

    print("Тестирование скорости выгрузки...")
    upload_speed = st.upload() / 10**6
    print(f"Скорость выгрузки: {upload_speed:.2f} Mbps")

    if __name__ == "__main__":
        speedtestr()

def passwordgenerator(length=8):
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

    if __name__ == "__main__":
        password = passwordgenerator(length=8)
        print("Сгенерированный пароль:", password)

def microcore():
    while True:
        user_input = input("[O]xxxxxx[[/\/\/\/\/\/\/\/\/\> ").strip()
        if user_input.lower() == "terminal":
            terminal()
        elif user_input.lower() == "exit":
            break
        else:
            print("Неизвестная команда:", user_input)

def terminal():
    class TerminalApp:
        def __init__(self, master):
            self.master = master
            master.title("Простой терминал")

            self.input_entry = tk.Entry(master, width=50)
            self.input_entry.grid(row=0, column=0, padx=10, pady=10)

            self.execute_button = tk.Button(master, text="Выполнить", command=self.execute_command)
            self.execute_button.grid(row=0, column=1, padx=10, pady=10)

            self.output_text = scrolledtext.ScrolledText(master, width=70, height=20)
            self.output_text.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        def execute_command(self):
            command = self.input_entry.get()

            try:
                result = str(eval(command))
            except Exception as e:
                result = f"Ошибка: {str(e)}"

            self.input_entry.delete(0, tk.END)

            self.output_text.insert(tk.END, f">>> {command}\n{result}\n\n")
            self.output_text.yview(tk.END)

    if __name__ == "__main__":
        root = tk.Tk()
        app = TerminalApp(root)
        root.mainloop()

def main():
    while True:
        user_input = input("Введите команду: ").strip()
        if user_input.lower() == "exit":
            break
        elif user_input.lower() == "version":
            version()
        elif user_input.lower() == "gallery":
            gallery()
        elif user_input.lower() == "time":
            time()
        elif user_input.lower() == "snake":
            snake()
        elif user_input.lower() == "battery":
            battery()
        elif user_input.lower() == "reboot":
            reboot()
        elif user_input.lower() == "shutdown":
            shutdown()
        elif user_input.lower() == "standby":
            standby()
        elif user_input.lower() == "store":
            store()
        elif user_input.lower() == "text":
            text()
        elif user_input.lower() == "calculator":
            calculator()
        elif user_input.lower() == "pkg":
            pkg()
        elif user_input.lower() == "phoneui":
            phoneui()
        elif user_input.lower() == "clear":
            clear()
        elif user_input.lower() == "video":
            video()
        elif user_input.lower() == "processes":
            processes()
        elif user_input.lower() == "files":
            files()
        elif user_input.lower() == "to":
            to()
        elif user_input.lower() == "tui":
            tui()
        elif user_input.lower() == "device":
            device()
        elif user_input.lower() == "restart":
            restart()
        elif user_input.lower() == "networkscan":
            networkscan()
        elif user_input.lower() == "gui":
            gui()
        elif user_input.lower() == "modules":
            subprocess.run(("python", "module.py"))
            #load_module()
        elif user_input.lower() == "speedtest":
            speedtestr()
        elif user_input.lower() == "passwordgenerator":
            passwordgenerator(length=8)
        elif user_input.lower() == "gui1":
            subprocess.run(("python", "gui_reworked.py"))
        else:
            print("Неизвестная команда:", (f"{Fore.RED}{user_input}{Style.RESET_ALL}"))

if __name__ == "__main__":
    main()
