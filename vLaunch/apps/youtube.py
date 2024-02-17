import tkinter as tk
from tkinter import ttk
import webbrowser

class YouTubeClient:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Client")

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="YouTube")

        self.open_button = tk.Button(self.frame, text="Open YouTube", command=self.open_youtube)
        self.open_button.pack(padx=10, pady=10)

    def open_youtube(self):
        webbrowser.open("https://www.youtube.com")

if __name__ == "__main__":
    root = tk.Tk()
    youtube_client = YouTubeClient(root)
    root.mainloop()
