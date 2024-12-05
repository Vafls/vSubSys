import os
import shutil
import tkinter as tk
from tkinter import filedialog

class FileManager:
    def __init__(self, root):
        self.root = root
        self.root.title("File Manager")

        self.current_path = tk.StringVar()
        self.current_path.set(os.getcwd())

        self.create_widgets()

    def create_widgets(self):
        path_label = tk.Label(self.root, textvariable=self.current_path)
        path_label.pack()

        self.file_listbox = tk.Listbox(self.root, selectmode=tk.SINGLE)
        self.update_file_list()
        self.file_listbox.pack()

        button_frame = tk.Frame(self.root)
        copy_button = tk.Button(button_frame, text="Копировать", command=self.copy_file)
        cut_button = tk.Button(button_frame, text="Вырезать", command=self.cut_file)
        paste_button = tk.Button(button_frame, text="Вставить", command=self.paste_file)
        rename_button = tk.Button(button_frame, text="Переименовать", command=self.rename_file)

        copy_button.pack(side=tk.LEFT)
        cut_button.pack(side=tk.LEFT)
        paste_button.pack(side=tk.LEFT)
        rename_button.pack(side=tk.LEFT)

        button_frame.pack()

    def update_file_list(self):
        self.file_listbox.delete(0, tk.END)
        path = self.current_path.get()
        for item in os.listdir(path):
            self.file_listbox.insert(tk.END, item)

    def copy_file(self):
        selected_file = self.file_listbox.get(tk.ACTIVE)
        if selected_file:
            self.copied_file_path = os.path.join(self.current_path.get(), selected_file)

    def cut_file(self):
        self.copy_file()

    def paste_file(self):
        if hasattr(self, 'copied_file_path'):
            destination = filedialog.askdirectory(title="Выберите папку для вставки")
            if destination:
                shutil.copy(self.copied_file_path, destination)
                self.update_file_list()

    def rename_file(self):
        selected_file = self.file_listbox.get(tk.ACTIVE)
        if selected_file:
            path = os.path.join(self.current_path.get(), selected_file)
            new_name = filedialog.askstring("Переименовать", "Введите новое имя файла:", initialvalue=selected_file)
            if new_name:
                new_path = os.path.join(self.current_path.get(), new_name)
                os.rename(path, new_path)
                self.update_file_list()

if __name__ == "__main__":
    root = tk.Tk()
    file_manager = FileManager(root)
    root.mainloop()
