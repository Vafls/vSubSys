import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk
import os
import sys

class LockScreenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lock Screen")
        self.root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))
        self.root.attributes('-fullscreen', True)

        background_path = "C:\\vLaunch\\source\\lock_screen_wallpaper.png"
        if os.path.exists(background_path):
            background_image = Image.open(background_path)
            background_photo = ImageTk.PhotoImage(background_image)
            background_label = tk.Label(root, image=background_photo)
            background_label.image = background_photo
            background_label.place(x=0, y=0, relwidth=1, relheight=1)
        else:
            background_label = tk.Label(root, text="Default Background", font=('Helvetica', 18))
            background_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.time_label = tk.Label(root, text="", font=('Helvetica', 36, 'bold'), bg='black', fg='white', bd=0)
        self.time_label.pack(pady=50)
        self.update_time()

        root.bind("<Button-1>", self.launch_program)
        root.bind("<Button-3>", self.launch_program)
        root.bind("<space>", self.launch_program)
        root.bind("<Return>", self.launch_program)
        root.bind("<v>", self.launch_vshell)

    def update_time(self):
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        self.time_label.config(text=current_time + "\n" + current_date, font=('Helvetica', 36, 'bold'), justify='center')
        self.root.after(1000, self.update_time)

    def launch_program(self, event):
        program_path = "C:\\vLaunch\\kernel\\kernel.py"
        if os.path.exists(program_path):
            os.system(f"start python {program_path} -auth9857")
            self.root.destroy()
        else:
            print(f"Error: Program not found at {program_path}")

    def launch_vshell(self, event):
        kernel_path = "C:\\vLaunch\\kernel\\kernel.py"
        if os.path.exists(kernel_path):
            os.system(f"start python {kernel_path} -auth9859")
            self.root.destroy()
        else:
            print(f"Error: Program not found at {kernel_path}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "-auth8327":
        root = tk.Tk()
        app = LockScreenApp(root)
        root.mainloop()
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
        print("1.Reinstall system and try again(If didn't help, contact the support: support.vafls.com)")
        print("2.Run 'main.py' as an administrator")
        #print("LockScreen kernel can't start")