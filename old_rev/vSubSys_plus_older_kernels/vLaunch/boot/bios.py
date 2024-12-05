import tkinter as tk
from tkinter import messagebox
import os

class BIOS(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BIOS")
        self.attributes('-fullscreen', True)
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.configure(bg='lightblue')

        self.menu = tk.Menu(self)
        self.config(menu=self.menu)

        self.file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Save Settings", command=self.save_settings)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_exit)

        self.boot_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Boot", menu=self.boot_menu)

        self.settings_frame = tk.LabelFrame(self, text="System Settings", padx=10, pady=10)
        self.settings_frame.pack(padx=20, pady=20)

        self.create_settings_widgets()
        self.detect_boot_folders()

    def create_settings_widgets(self):
        self.username_label = tk.Label(self.settings_frame, text="Username:")
        self.username_label.grid(row=0, column=0, sticky="e")

        self.username_entry = tk.Entry(self.settings_frame)
        self.username_entry.grid(row=0, column=1)

        self.password_label = tk.Label(self.settings_frame, text="Password:")
        self.password_label.grid(row=1, column=0, sticky="e")

        self.password_entry = tk.Entry(self.settings_frame, show="*")
        self.password_entry.grid(row=1, column=1)

    def detect_boot_folders(self):
        kernel_path = "C:\\vLaunch\\custom_kernel"
        if os.path.exists(kernel_path):
            folders = [d for d in os.listdir(kernel_path) if os.path.isdir(os.path.join(kernel_path, d))]
            for folder in folders:
                self.boot_menu.add_command(label=f"Boot {folder}", command=lambda f=folder: self.boot_folder(kernel_path, f))

    def save_settings(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        messagebox.showinfo("Settings Saved", f"Username: {username}\nPassword: {password}")

    def boot_folder(self, kernel_path, folder):
        folder_path = os.path.join(kernel_path, folder)
        messagebox.showinfo("Booting", f"Booting from {folder}...")
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file == "main.py":
                        file_path = os.path.join(root, file)
                        os.system(f"python {file_path}")
                        self.on_exit()
                        return
            messagebox.showinfo("Error", "No main.py found in the specified folder.")
        else:
            messagebox.showinfo("Error", f"Folder {folder_path} not found.")

    def on_exit(self):
        self.destroy()

if __name__ == "__main__":
    bios = BIOS()
    bios.mainloop()
