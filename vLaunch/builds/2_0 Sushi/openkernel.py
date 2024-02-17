import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import datetime
import psutil
import subprocess
import platform

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

        self.app_icons = ["app1.png", "app2.png", "app3.png", "app4.png"]
        self.preview_icons = ["preview1.png", "preview2.png", "preview3.png", "preview4.png"]

        self.app_buttons = []
        for i, app_icon in enumerate(self.app_icons):
            image = Image.open(app_icon)
            image = image.resize((int(image.width * 0.5), int(image.height * 0.5)), Image.ANTIALIAS)
            app_image = ImageTk.PhotoImage(image)

            button = tk.Button(self.menu_frame, image=app_image, command=lambda i=i: self.launch_app(i))
            button.grid(row=0, column=i, padx=10)
            button.image = app_image

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

        self.shutdown_image = ImageTk.PhotoImage(file="power.png")
        self.shutdown_button = tk.Button(self.panel_frame, image=self.shutdown_image, command=self.shutdown, bg=self.background_color)
        self.shutdown_button.pack(side=tk.LEFT, padx=20)

        self.settings_image = ImageTk.PhotoImage(file="settings.png")
        self.settings_button = tk.Button(self.panel_frame, image=self.settings_image, command=self.open_settings, bg=self.background_color)
        self.settings_button.pack(side=tk.LEFT, padx=20)

        self.messages_image = ImageTk.PhotoImage(file="messages.png")
        self.messages_button = tk.Button(self.panel_frame, image=self.messages_image, command=self.open_messages, bg=self.background_color)
        self.messages_button.pack(side=tk.LEFT, padx=20)

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
        if app_index == 0:
            subprocess.run(["python", "web.py"])
        elif app_index == 1:
            subprocess.run(["python", "files.py"])
        elif app_index == 2:
            subprocess.run(["python", "game.py"])
        elif app_index == 3:
            subprocess.run(["python", "camera.py"])
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
        settings_window.geometry("400x300")

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

        device_image = Image.open("device_info.png")
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
        subprocess.run(["python", "update.py"])

    def open_messages(self):
        subprocess.run(["python", "messages.py"])

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

if __name__ == "__main__":
    app = Launcher()
    app.withdraw()
    app.lock_screen = LockScreen(app, app.unlock)
    app.lock_screen.lift()
    app.mainloop()