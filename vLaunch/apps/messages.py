import tkinter as tk
from tkinter import simpledialog, messagebox
import socket
import threading

class ChatApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Сообщения")
        self.user_code = self.generate_user_code()

        self.create_widgets()

        self.server_host = "127.0.0.1"
        self.server_port = 12345

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.server_host, self.server_port))
        self.socket.listen(1)

        threading.Thread(target=self.accept_connections).start()

    def generate_user_code(self):
        import uuid
        return str(uuid.uuid4())

    def create_widgets(self):
        self.code_label = tk.Label(self.master, text="Ваш код: " + self.user_code)
        self.code_label.pack(pady=10)

        self.new_chat_button = tk.Button(self.master, text="Начать новый чат", command=self.start_new_chat)
        self.new_chat_button.pack(pady=10)

        self.add_user_button = tk.Button(self.master, text="Добавить пользователя", command=self.add_user_to_chat)
        self.add_user_button.pack(pady=10)

    def start_new_chat(self):
        user_code = simpledialog.askstring("Новый чат", "Введите код пользователя:")
        if user_code:
            chat_window = tk.Toplevel(self.master)
            chat_window.title(f"Чат с пользователем {user_code}")

            self.setup_chat_interface(chat_window, user_code)

    def add_user_to_chat(self):
        user_code = simpledialog.askstring("Добавить пользователя", "Введите код пользователя:")
        if user_code:
            chat_window = tk.Toplevel(self.master)
            chat_window.title(f"Чат с пользователем {user_code}")

            self.setup_chat_interface(chat_window, user_code)

    def setup_chat_interface(self, chat_window, user_code):
        self.message_listbox = tk.Listbox(chat_window, height=15, width=50)
        self.message_listbox.pack(padx=10, pady=10)

        self.message_entry = tk.Entry(chat_window, width=40)
        self.message_entry.pack(padx=10, pady=10)

        send_button = tk.Button(chat_window, text="Отправить", command=lambda: self.send_message(user_code))
        send_button.pack(pady=10)

    def accept_connections(self):
        while True:
            client_socket, _ = self.socket.accept()
            threading.Thread(target=self.receive_messages, args=(client_socket,), daemon=True).start()

    def receive_messages(self, client_socket):
        try:
            while True:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                self.message_listbox.insert(tk.END, message)
        except Exception as e:
            print(f"Error receiving message: {e}")
        finally:
            client_socket.close()

    def send_message(self, user_code):
        message_text = self.message_entry.get()
        if message_text:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.server_host, self.server_port))
                client_socket.send(f"{self.user_code}: {message_text}".encode('utf-8'))
                client_socket.close()

                self.message_listbox.insert(tk.END, f"You: {message_text}")
                self.message_entry.delete(0, tk.END)
            except Exception as e:
                print(f"Error sending message: {e}")
                messagebox.showerror("Ошибка", "Не удалось отправить сообщение")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
