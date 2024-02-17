import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import datetime
import psutil
import subprocess
import platform
import os
import threading
import time
import argparse

class LockScreen(tk.Toplevel):
    def __init__(self, master, unlock_callback):
        super().__init__(master)
        self.title("Lock Screen")
        self.attributes('-fullscreen', True)
        self.configure(bg="black")

        self.unlock_callback = unlock_callback

        self.time_label = tk.Label(self, font=('Helvetica', 40), bg="black", fg="white")
        self.time_label.pack(pady=50)

        self.date_label = tk.Label(self, font=('Helvetica', 20), bg="black", fg="white")
        self.date_label.pack(pady=10)

        self.update_time()
        self.bind("<Button-1>", lambda event: self.unlock())
        self.bind("<space>", lambda event: self.unlock())
        self.bind("<Return>", lambda event: self.unlock())

    def update_time(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=current_time)

        current_date = datetime.date.today().strftime("%Y-%m-%d")
        self.date_label.config(text=current_date)

        self.after(1000, self.update_time)

    def unlock(self):
        self.destroy()
        self.unlock_callback()

class Windows98Shell(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Windows 98 Shell")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height}")

        self.attributes("-fullscreen", True)

        self.desktop = tk.Frame(self, bg="lightgray", height=480)
        self.desktop.pack(fill=tk.BOTH, expand=True)

        self.create_shortcuts()

        self.create_quick_access_panel()

        self.create_start_menu()

        self.create_widgets_panel()

    def create_shortcuts(self):
        shortcut_info = [
            {"name": "Browser", "image_path": "C:/vLaunch/source/app1.png"},
            {"name": "Files", "image_path": "C:/vLaunch/source/app2.png"},
            {"name": "Game", "image_path": "C:/vLaunch/source/app3.png"}
        ]

        for info in shortcut_info:
            image = Image.open(info["image_path"])
            image = image.resize((64, 64), Image.ANTIALIAS)
            photo = ImageTk.PhotoImage(image)

            shortcut_button = tk.Button(self.desktop, text=info["name"], image=photo, compound=tk.TOP, command=lambda: self.run_application(info["name"]))
            shortcut_button.image = photo
            shortcut_button.pack(side=tk.LEFT, padx=20)

    def create_quick_access_panel(self):
        quick_access_panel = tk.Frame(self, bg="lightgray", height=120)
        quick_access_panel.pack(fill=tk.BOTH, expand=False, side=tk.BOTTOM)

        shutdown_button = tk.Button(quick_access_panel, text="Выключение", command=self.shutdown)
        shutdown_button.pack(side=tk.LEFT, padx=10)

        reboot_button = tk.Button(quick_access_panel, text="Перезагрузка", command=self.reboot)
        reboot_button.pack(side=tk.LEFT, padx=10)

        sleep_button = tk.Button(quick_access_panel, text="Сон", command=self.sleep)
        sleep_button.pack(side=tk.LEFT, padx=10)

    def create_start_menu(self):
        start_menu = tk.Frame(self, bg="lightgray", height=20)
        start_menu.pack(fill=tk.BOTH, expand=False, side=tk.BOTTOM)

        start_button = tk.Button(start_menu, text="Меню Пуск", command=self.show_start_menu)
        start_button.pack(side=tk.LEFT, padx=10)

    def create_widgets_panel(self):
        widgets_panel = tk.Frame(self, bg="lightgray", height=20)
        widgets_panel.pack(fill=tk.BOTH, expand=False, side=tk.BOTTOM)

        self.current_time_label = tk.Label(widgets_panel, text="", font=("Arial", 10))
        self.current_time_label.pack(side=tk.LEFT, padx=10)

        self.battery_label = tk.Label(widgets_panel, text="", font=("Arial", 10))
        self.battery_label.pack(side=tk.RIGHT, padx=10)

        self.update_widgets()

    def update_widgets(self):
        current_time = tk.StringVar()
        current_time.set("Текущее время: " + time.strftime("%H:%M:%S"))
        self.current_time_label.config(textvariable=current_time)

        battery_percent = psutil.sensors_battery().percent
        battery_text = f"Заряд батареи: {battery_percent}%"
        self.battery_label.config(text=battery_text)

        self.after(1000, self.update_widgets)

    def show_start_menu(self):
        pass

    def run_application(self, app_name):
        print(f"Запущено приложение: {app_name}")

    def shutdown(self):
        self.destroy()

    def reboot(self):
        print("Перезагрузка")

    def sleep(self):
        print("Сон")

class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Launcher")
        self.attributes('-fullscreen', True)

        self.background_color = "black"

        self.screensaver_enabled = False
        self.screensaver_timeout = 15000
        self.after_id = None

        self.create_widgets()

    def create_widgets(self):
        self.menu_frame = tk.Frame(self, bg=self.background_color)
        self.menu_frame.pack(side=tk.TOP, fill=tk.X)

        self.app_icons = ["C:\\vLaunch\\source\\app1.png", "C:\\vLaunch\\source\\app2.png", "C:\\vLaunch\\source\\app3.png", "C:\\vLaunch\\source\\app4.png", "C:\\vLaunch\\source\\app5.png"]
        self.preview_icons = ["C:\\vLaunch\\source\\preview1.png", "C:\\vLaunch\\source\\preview2.png", "C:\\vLaunch\\source\\preview3.png", "C:\\vLaunch\\source\\preview4.png", "C:\\vLaunch\\source\\preview5.png"]


        self.app_buttons = []
        for i, app_icon in enumerate(self.app_icons):
            image = Image.open(app_icon)
            image = image.resize((int(image.width * 0.5), int(image.height * 0.5)), Image.ANTIALIAS)
            app_image = ImageTk.PhotoImage(image)

            button = tk.Button(self.menu_frame, image=app_image, command=lambda i=i: self.launch_app(i))
            button.grid(row=0, column=i, padx=10)
            button.image = app_image
            button.default_image = app_image

            self.app_buttons.append(button)

        self.current_app_index = 0

        self.preview_label = tk.Label(self, bg=self.background_color)
        self.preview_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.highlight_app()

        self.panel_frame = tk.Frame(self, bg=self.background_color)
        self.panel_frame.pack(side=tk.TOP, fill=tk.X)

        self.time_label = tk.Label(self.panel_frame, font=('Helvetica', 20), bg=self.background_color, fg="white")
        self.time_label.pack(side=tk.LEFT, padx=20)

        self.battery_label = tk.Label(self.panel_frame, font=('Helvetica', 20), bg=self.background_color, fg="white")
        self.battery_label.pack(side=tk.LEFT, padx=20)

        self.date_label = tk.Label(self.panel_frame, font=('Helvetica', 20), bg=self.background_color, fg="white")
        self.date_label.pack(side=tk.LEFT, padx=20)

        kernel_path = "C:\\vLaunch\\kernel\\kernel.py"
        settings_image_path = os.path.join(os.path.dirname(kernel_path), "..\\source\\settings.png")
        shutdown_image_path = os.path.join(os.path.dirname(kernel_path), "..\\source\\power.png")
        messages_image_path = os.path.join(os.path.dirname(kernel_path), "..\\source\\messages.png")
        ai_image_path = os.path.join(os.path.dirname(kernel_path), "..\\source\\vaichat.png")

        self.shutdown_image = ImageTk.PhotoImage(file=shutdown_image_path)
        self.shutdown_button = tk.Button(self.panel_frame, image=self.shutdown_image, command=self.shutdown, bg=self.background_color)
        self.shutdown_button.pack(side=tk.LEFT, padx=20)

        self.settings_image = ImageTk.PhotoImage(file=settings_image_path)
        self.settings_button = tk.Button(self.panel_frame, image=self.settings_image, command=self.open_settings, bg=self.background_color)
        self.settings_button.pack(side=tk.LEFT, padx=20)

        self.messages_image = ImageTk.PhotoImage(file=messages_image_path)
        self.messages_button = tk.Button(self.panel_frame, image=self.messages_image, command=self.open_messages, bg=self.background_color)
        self.messages_button.pack(side=tk.LEFT, padx=20)

        self.vaichat_image = ImageTk.PhotoImage(file=ai_image_path)
        self.vaichat_button = tk.Button(self.panel_frame, image=self.vaichat_image, command=self.open_ai_chat, bg=self.background_color)
        self.vaichat_button.pack(side=tk.LEFT, padx=20)

        self.user_photo_label = tk.Label(self.panel_frame, bg=self.background_color)
        self.user_photo_label.pack(side=tk.RIGHT, padx=20)

        self.after_id = self.after(self.screensaver_timeout, self.check_screensaver)

        self.bind("<Left>", lambda event: self.navigate(-1))
        self.bind("<Right>", lambda event: self.navigate(1))
        self.bind("<Return>", lambda event: self.launch_app(self.current_app_index))
        self.bind("<Motion>", self.reset_screensaver)

    def highlight_app(self):
        for i, button in enumerate(self.app_buttons):
            if i == self.current_app_index:
                button.config(bg="blue")
                preview_image = Image.open(self.preview_icons[i])
                preview_image = preview_image.resize((450, 300), Image.ANTIALIAS)
                preview_photo = ImageTk.PhotoImage(preview_image)
                self.preview_label.config(image=preview_photo)
                self.preview_label.image = preview_photo
            else:
                button.config(bg=self.background_color)

    def navigate(self, direction):
        self.current_app_index = (self.current_app_index + direction) % len(self.app_buttons)
        self.highlight_app()

    def launch_app(self, app_index):
        def animate_icon_scaling():
            for scale_factor in [1.5, 1.0]:
                image = Image.open(self.app_icons[app_index])
                image = image.resize((int(image.width * scale_factor), int(image.height * scale_factor)), Image.ANTIALIAS)
                app_image = ImageTk.PhotoImage(image)

                self.app_buttons[app_index].config(image=app_image)
                self.app_buttons[app_index].image = app_image

                time.sleep(0.2) #скорость анимации

            self.app_buttons[app_index].config(image=self.app_buttons[app_index].default_image)
            self.app_buttons[app_index].image = self.app_buttons[app_index].default_image

        threading.Thread(target=animate_icon_scaling).start()

        if app_index == 0:
            subprocess.run(["python", "web.py"])
        elif app_index == 1:
            self.open_files()
        elif app_index == 2:
            self.open_game()
        elif app_index == 3:
            self.open_camera()
        elif app_index == 4:
            self.open_terminal()
        else:
            print(f"Запуск приложения {app_index + 1}")

    def shutdown(self):
        self.after_cancel(self.after_id)
        self.destroy()

    def update_panel(self):
        battery_percent = psutil.sensors_battery().percent
        self.battery_label.config(text=f"Батарея: {battery_percent}%")
        self.date_label.config(text=f"Дата: {datetime.date.today()}")
        self.after(10000, self.update_panel)

    def update_time(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=f"Время: {current_time}")
        self.after(1000, self.update_time)

    def open_settings(self):
        settings_window = tk.Toplevel(self)
        settings_window.title("Настройки")
        settings_window.geometry("400x400")

        background_frame = tk.Frame(settings_window)
        background_frame.pack(pady=10)

        background_button = tk.Button(background_frame, text="Изменить фон", command=self.change_background)
        background_button.pack(side=tk.LEFT, padx=10)

        wallpaper_button = tk.Button(background_frame, text="Сменить обои", command=self.change_wallpaper)
        wallpaper_button.pack(side=tk.LEFT, padx=10)

        account_button = tk.Button(settings_window, text="Аккаунт", command=self.show_account_info)
        account_button.pack(pady=10)

        device_info_button = tk.Button(settings_window, text="Об устройстве", command=self.show_device_info)
        device_info_button.pack(pady=10)

        screensaver_button = tk.Button(settings_window, text="Screensaver", command=self.toggle_screensaver)
        screensaver_button.pack(pady=10)

        update_button = tk.Button(settings_window, text="Обновление", command=self.open_update)
        update_button.pack(pady=10)

        debug_button = tk.Button(settings_window, text="debug", command=self.open_debug)
        debug_button.pack(pady=10)

        close_button = tk.Button(settings_window, text="Закрыть", command=settings_window.destroy)
        close_button.pack(pady=10)

        if hasattr(self, 'user_avatar_visible') and self.user_avatar_visible:
            self.show_user_avatar()
        else:
            self.hide_user_avatar()

    def show_device_info(self):
        device_info_window = tk.Toplevel(self)
        device_info_window.title("Об устройстве")
        device_info_window.geometry("600x400")

        device_info_frame = tk.Frame(device_info_window)
        device_info_frame.pack(pady=10, padx=10)

        device_image = Image.open("C:\\vLaunch\\source\\device_info.png")
        device_image = device_image.resize((200, 200), Image.ANTIALIAS)
        device_photo = ImageTk.PhotoImage(device_image)
        device_image_label = tk.Label(device_info_frame, image=device_photo)
        device_image_label.image = device_photo
        device_image_label.pack(side=tk.LEFT)

        version_label = tk.Label(device_info_frame, text="Версия Виндовс: " + platform.version(), font=('Helvetica', 12))
        version_label.pack(side=tk.TOP, anchor="w")

        device_name_label = tk.Label(device_info_frame, text="Имя устройства: " + platform.node(), font=('Helvetica', 12))
        device_name_label.pack(side=tk.TOP, anchor="w")

        program_version_label = tk.Label(device_info_frame, text="Версия программы: 2.0 'Sushi' ", font=('Helvetica', 12))
        program_version_label.pack(side=tk.TOP, anchor="w")

        try:
            import user
            user_name_label = tk.Label(device_info_frame, text="Имя пользователя: " + user.name, font=('Helvetica', 12))
            user_name_label.pack(side=tk.TOP, anchor="w")
        except ImportError:
            user_name_label = tk.Label(device_info_frame, text="Имя пользователя: ", font=('Helvetica', 12))
            user_name_label.pack(side=tk.TOP, anchor="w")

    def change_background(self):
        background_colors = ["white", "blue", "red", "purple", "black"]
        current_index = background_colors.index(self.background_color)
        new_index = (current_index + 1) % len(background_colors)
        self.background_color = background_colors[new_index]

        self.menu_frame.configure(bg=self.background_color)
        self.panel_frame.configure(bg=self.background_color)

        for button in self.app_buttons:
            button.configure(bg=self.background_color)

    def change_wallpaper(self):
        file_path = filedialog.askopenfilename(title="Выберите файл обоев", filetypes=[("Изображения", "*.png;*.jpg;*.jpeg")])
        if file_path:
            wallpaper_image = Image.open(file_path)
            wallpaper_image = wallpaper_image.resize((self.winfo_screenwidth(), self.winfo_screenheight()), Image.ANTIALIAS)
            wallpaper_photo = ImageTk.PhotoImage(wallpaper_image)
            self.configure(bg=self.background_color)
            self.preview_label.config(image=wallpaper_photo)
            self.preview_label.image = wallpaper_photo     

    def show_account_info(self):
        try:
            import user
            avatar_path = user.avatar
            user_name = user.name

            user_photo = Image.open(avatar_path)
            user_photo = user_photo.resize((50, 50), Image.ANTIALIAS)
            user_photo = ImageTk.PhotoImage(user_photo)
            self.user_photo_label.configure(image=user_photo)
            self.user_photo_label.image = user_photo

            self.user_name_label = tk.Label(self.panel_frame, text=user_name, font=('Helvetica', 20), bg=self.background_color, fg="white")
            self.user_name_label.pack(side=tk.RIGHT, padx=20)

            self.show_user_avatar()
        except ImportError:
            pass

    def open_update(self):
        update_krnl_path = r'C:\vLaunch\update\update.py'
        subprocess.run(["python", update_krnl_path])

    def open_messages(self):
        messages_path = r'C:\vLaunch\apps\messages.py'
        subprocess.run(["python", messages_path])

    def open_camera(self):
        camera_path = r'C:\vLaunch\apps\camera.py'
        subprocess.run(["python", camera_path])

    def open_files(self):
        files_path = r'C:\vLaunch\apps\files.py'
        subprocess.run(["python", files_path])

    def open_web(self):
        web_path = r'C:\vLaunch\apps\web.py'
        subprocess.run(["python", web_path])

    def open_game(self):
        game_path = r'C:\vLaunch\apps\minecraft.py'
        subprocess.run(["python", game_path])

    def open_ai_chat(self):
        chat_path = r'C:\vLaunch\apps\vaic.py'
        subprocess.run(["python", chat_path])

    def open_debug(self):
        debug_path = r'C:\vLaunch\debug\debug.py'
        subprocess.run(["python", debug_path])

    def open_terminal(self):
        terminal_path = r'C:\vLaunch\apps\terminal.py'
        subprocess.run(["python", terminal_path])

    def unlock(self):
        self.clear_widgets()
        self.create_lock_screen()
        self.iconify()
        self.after_id = self.after(self.screensaver_timeout, self.check_screensaver)

    def create_lock_screen(self):
        self.lock_screen = LockScreen(self, self.unlock)
        self.lock_screen.lift()

    def clear_widgets(self):
        for widget in self.winfo_children():
            if widget not in [self.menu_frame, self.preview_label, self.panel_frame]:
                widget.destroy()

    def show_user_avatar(self):
        self.user_avatar_visible = True
        self.user_photo_label.pack(side=tk.RIGHT, padx=20)
        self.user_name_label.pack(side=tk.RIGHT, padx=20)

    def hide_user_avatar(self):
        self.user_avatar_visible = False
        self.user_photo_label.pack_forget()
        self.user_name_label.pack_forget()

    def check_screensaver(self):
        if self.screensaver_enabled:
            self.start_screensaver()
        else:
            self.after_id = self.after(self.screensaver_timeout, self.check_screensaver)

    def reset_screensaver(self, event):
        self.after_cancel(self.after_id)
        self.after_id = self.after(self.screensaver_timeout, self.check_screensaver)
        self.update_panel()
        self.update_time()

    def start_screensaver(self):
        screensaver_window = tk.Toplevel(self)
        screensaver_window.attributes('-fullscreen', True)
        screensaver_window.title("Screensaver")
        screensaver_window.configure(bg="black")

        screensaver_label = tk.Label(screensaver_window, text="Screensaver включен", font=('Helvetica', 30), bg="black", fg="white")
        screensaver_label.pack(expand=True)

        screensaver_window.bind("<Any-KeyPress>", lambda event: screensaver_window.destroy())
        screensaver_window.bind("<Button-1>", lambda event: screensaver_window.destroy())
        screensaver_window.bind("<Button-2>", lambda event: screensaver_window.destroy())
        screensaver_window.bind("<Button-3>", lambda event: screensaver_window.destroy())
        screensaver_window.bind("<Motion>", lambda event: screensaver_window.destroy())

    def toggle_screensaver(self):
        self.screensaver_enabled = not self.screensaver_enabled
        if self.screensaver_enabled:
            self.show_screensaver_status("Включен")
        else:
            self.show_screensaver_status("Отключен")

    def show_screensaver_status(self, status):
        screensaver_status_label = tk.Label(tk.Toplevel(self), text=f"Screensaver: {status}", font=('Helvetica', 12))
        screensaver_status_label.pack(pady=10)

#if __name__ == "__main__":
    #app = Launcher()
    #app.withdraw()
    #app.lock_screen = LockScreen(app, app.unlock) встроенный lock screen
    #app.lock_screen.lift()
    #app.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Launcher and Lock Screen application.')
    parser.add_argument('-auth9857', '--launcher', action='store_true', help='Launch the Launcher class.')
    parser.add_argument('-auth9858', '--lockscreen', action='store_true', help='Launch the LockScreen class.')
    parser.add_argument('-auth9859', '--vshell', action='store_true', help='Launch the LockScreen class.')
    args = parser.parse_args()

    if args.launcher:
        app = Launcher()
        app.mainloop()
    elif args.lockscreen:
        app = LockScreen(None, lambda: print("Unlock callback"))
        app.mainloop()
    elif args.vshell:
        app = Windows98Shell()
        app.mainloop()
    else:
        print('  __________________________________________________________________________')
        print('Kernel panic')
        print('  __________________________________________________________________________')
        print('                  _________-----_____')
        print('       _____------           __      ----_')
        print('___----             ___------              \\')
        print('   ----________        ----                 \\')
        print('               -----__    |             _____)')
        print('                    __-                /     \\')
        print('        _______-----    ___--          \\    /)\\')
        print('  ------_______      ---____            \\__/  /')
        print('               -----__    \\ --    _          /\\')
        print('                      --__--__     \\_____/   \\_/\\')
        print('                              ----|   /          |')
        print('                                  |  |___________|')
        print('                                  |  | ((_(_)| )_)')
        print('                                  |  \\_((_(_)|/(_)')
        print('                                  \\             (')
        print('                                   \\_____________)')
        print("It seems like kernel can't start")
        print("It may happened because of this things:")
        print("1.System files are missing")
        print("2.The system wasn't installed on the right directory")
        print("3.User tried to run kernel files instead of 'main.py'")
        print("You can follow next steps to try to fix it")
        print("1.Reinstall system and try again")
        print("2.Run 'main.py' as an administrator")
