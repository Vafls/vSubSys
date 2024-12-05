import tkinter as tk
from tkinter import scrolledtext
import sys
import traceback

class DebugApp:
    def __init__(self, master):
        self.master = master
        master.title("Debug App")

        self.create_widgets()

    def create_widgets(self):
        self.text_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, width=80, height=20)
        self.text_area.pack(expand=True, fill='both')

        self.load_logs_button = tk.Button(self.master, text="Load Logs", command=self.load_logs)
        self.load_logs_button.pack()

        sys.stdout = self
        sys.stderr = self

    def write(self, text):
        self.text_area.insert(tk.END, text)
        self.text_area.yview(tk.END)

    def load_logs(self):
        log_file_path = "C:/vLaunch/kernel/kernel.py"
        try:
            with open(log_file_path, "r", encoding="utf-8") as file:
                logs = file.read()
                self.text_area.delete(1.0, tk.END)
                self.text_area.insert(tk.END, logs)
        except FileNotFoundError:
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, "Log file not found.")

def main():
    root = tk.Tk()
    app = DebugApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
