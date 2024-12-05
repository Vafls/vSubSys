import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class CameraApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        
        self.video_source = 0
        
        self.vid = cv2.VideoCapture(self.video_source)
        
        self.canvas = tk.Canvas(window, width=self.vid.get(cv2.CAP_PROP_FRAME_WIDTH), height=self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.canvas.pack()
        
        self.btn_snapshot = ttk.Button(window, text="Снимок", command=self.snapshot)
        self.btn_snapshot.pack(padx=10, pady=10, side=tk.LEFT)
        
        self.btn_exit = ttk.Button(window, text="Выход", command=self.exit_app)
        self.btn_exit.pack(padx=10, pady=10, side=tk.RIGHT)
        
        self.update()
        self.window.mainloop()

    def snapshot(self):
        ret, frame = self.vid.read()
        if ret:
            cv2.imwrite("snapshot.png", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    def update(self):
        ret, frame = self.vid.read()
        if ret:
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        self.window.after(10, self.update)
        
    def exit_app(self):
        self.vid.release()
        self.window.destroy()

root = tk.Tk()
app = CameraApp(root, "Камера на Tkinter")
