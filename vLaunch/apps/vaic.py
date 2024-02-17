import tkinter as tk
from tkinter import scrolledtext, ttk
import wikipedia
from random import choice

class AIChat:
    def __init__(self, master):
        self.master = master
        master.title("Vafls AI chat")

        style = ttk.Style()
        style.configure('TButton', font=('Arial', 14))

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.responses_list = [
            {
                'привет': ['Привет!', 'Привет, как дела?', 'Здравствуйте!'],
                'как дела': ['Хорошо, спасибо!', 'Неплохо, а у вас?', 'Отлично!'],
                'пока': ['До свидания!', 'До встречи!', 'Пока-пока!'],
                'что делаешь': ['Отвечаю на вопросы!', 'Работаю над своими алгоритмами.', 'Общаюсь с вами.'],
                'как тебя зовут': ['Меня зовут Vafls.', 'Я - ваш виртуальный ассистент.', 'Мое имя - Vafls'],
                'что нового': ['Ничего особенного, как у вас?', 'Работаю, как всегда.', 'Новостей пока нет.'],
                'ты любишь программирование': ['Я просто программа, но мне нравится помогать вам с кодом!', 'Программирование интересная область.', 'Люблю решать задачи.']
            },
            {
                'привет': ['Привет из нового чата!', 'Как дела в новом чате?', 'Приветствую вас!'],
                'как дела': ['У нас тут хорошо!', 'Новый чат - новые возможности.', 'Отлично!'],
                'пока': ['До встречи в новом чате!', 'До свидания из этого чата!', 'Пока-пока из нового чата!'],
            }
        ]

        self.chats = []
        for i, responses in enumerate(self.responses_list, start=1):
            chat_frame = tk.Frame(self.notebook)
            self.notebook.add(chat_frame, text=f"Чат {i}")
            chat = Chat(chat_frame, responses)
            self.chats.append(chat)

    def switch_chat(self, event):
        current_tab = self.notebook.index(self.notebook.select())
        self.chats[current_tab].user_input.focus_set()


class Chat:
    def __init__(self, master, responses):
        self.master = master

        self.chat_frame = tk.Frame(master)
        self.chat_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.chat_history = scrolledtext.ScrolledText(self.chat_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.chat_history.pack(fill=tk.BOTH, expand=True)

        self.input_frame = tk.Frame(master)
        self.input_frame.pack(padx=10, pady=(0, 10), fill=tk.BOTH)

        self.user_input = tk.Entry(self.input_frame, font=('Arial', 14))
        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.send_button = ttk.Button(self.input_frame, text="Спросить", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.user_input.bind('<Return>', lambda event: self.send_message())

        self.responses = responses

    def send_message(self):
        user_message = self.user_input.get()
        self.display_message("Вы: " + user_message, True)

        response = self.generate_response(user_message)
        self.display_message("Vafls: " + response, False)

        self.user_input.delete(0, tk.END)

    def generate_response(self, user_message):
        user_words = set(user_message.lower().split())
        possible_responses = []

        for key_words in self.responses:
            if set(key_words.split()).intersection(user_words):
                possible_responses.extend(self.responses[key_words])

        if possible_responses:
            return choice(possible_responses)
        else:
            return self.search_wikipedia(user_message)

    def search_wikipedia(self, keyword):
        try:
            result = wikipedia.summary(keyword)
            return result
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Пожалуйста, уточните ваш запрос: {e.options}"
        except wikipedia.exceptions.PageError:
            return "Информация не найдена. Попробуйте убрать специальные символы по типу '?', '!', '$'."

    def display_message(self, message, user):
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()

    root.title("Vafls AI chat")
    root.geometry("600x600")

    ai_chat = AIChat(root)

    root.bind("<Control-Tab>", ai_chat.switch_chat)

    root.mainloop()
