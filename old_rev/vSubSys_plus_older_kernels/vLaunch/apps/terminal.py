import tkinter as tk
from datetime import datetime
from battery import battery

class TerminalApp:
    def __init__(self, master):
        self.master = master
        master.title("Terminal App")

        self.create_widgets()

    def create_widgets(self):
        self.output_text = tk.Text(self.master, wrap=tk.WORD, width=80, height=20)
        self.output_text.pack(expand=True, fill='both')
        self.output_text.insert(tk.END, "Welcome to the Terminal App!\nType 'exit' to close the terminal.\n")

        self.input_entry = tk.Entry(self.master, width=80)
        self.input_entry.pack(expand=True, fill='both')
        self.input_entry.focus_set()

        self.input_entry.bind("<Return>", self.process_input)

    def process_input(self, event):
        user_input = self.input_entry.get()
        self.output_text.insert(tk.END, f"\n>>> {user_input}\n")

        if user_input.lower() == 'exit':
            self.exit()
        elif user_input.lower() == 'time':
            self.time()
        elif user_input.lower -- 'battery':
            self.battery()
        else:
            self.output_text.insert(tk.END, "Command not recognized.\n")

        self.input_entry.delete(0, tk.END)

    def exit(self):
        self.output_text.insert(tk.END, "Exiting the terminal...\n")
        self.master.destroy()

    def time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.output_text.insert(tk.END, f"Current time: {current_time}\n")

def main():
    root = tk.Tk()
    app = TerminalApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
