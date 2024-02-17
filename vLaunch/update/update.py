import os
import shutil
import tkinter as tk
from tkinter import messagebox

def check_for_update():
    update_file = "c24krnl.py"
    current_kernel = "C:\vLaunch\kernel\kernel.py"

    if os.path.exists(update_file):
        response = messagebox.askquestion("Обновление", "Обнаружено новое обновление. Хотите применить его?")
        
        if response == 'yes':
            try:
                os.remove(current_kernel)
                shutil.move(update_file, current_kernel)
                messagebox.showinfo("Обновление", "Обновление прошло успешно!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Что-то пошло не так: {e}")
        else:
            messagebox.showinfo("Обновление", "Обновление отменено.")
    else:
        messagebox.showinfo("Обновление", "Новых обновлений не найдено.")

if __name__ == "__main__":
    check_for_update()
