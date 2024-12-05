import os
import tkinter as tk
from tkinter import PhotoImage
import subprocess
from itertools import cycle

class BootLoader:
    def __init__(self, root):
        self.root = root
        self.root.title("Boot Loader")
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Key>", self.key_pressed)

        image_path = "C:\\vLaunch\\source\\"
        self.logo_image = PhotoImage(file=os.path.join(image_path, "v.png"))
        self.frames = [PhotoImage(file=os.path.join(image_path, f"frame{i}.png")) for i in range(1, 5)]

        self.animation_counter = 0
        self.animation_max_count = 3

        self.logo_label = tk.Label(root, image=self.logo_image)
        self.logo_label.pack(pady=50)

        self.animation_label = tk.Label(root)
        self.animation_label.pack()

        self.animate()

    def animate(self):
        frame = self.frames[self.animation_counter]
        self.animation_label.configure(image=frame)
        self.animation_counter += 1

        if self.animation_counter == len(self.frames):
            self.animation_counter = 0
            self.animation_max_count -= 1

        if self.animation_max_count == 0:
            self.launch_kernel()

        else:
            self.root.after(500, self.animate)

    def launch_kernel(self):
        lockscreen_path = r'C:\vLaunch\kernel\lockscreen.py'
        subprocess.run(["python", lockscreen_path, "-auth8327"])
        self.root.after(2000, self.close_boot_loader)

    def close_boot_loader(self):
        self.root.destroy()

    def key_pressed(self, event):
        bios_path = r"C:\vLaunch\boot\bios.py"
        if event.char == '2':
            subprocess.Popen(["python", bios_path])
            self.close_boot_loader()

if __name__ == "__main__":
    root = tk.Tk()
    boot_loader = BootLoader(root)
    root.mainloop()
