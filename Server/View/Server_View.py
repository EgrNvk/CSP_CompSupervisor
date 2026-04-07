import tkinter as tk
from tkinter import ttk


class View(tk.Tk):

    COLUMNS = ("ip", "hostname", "seen", "status")
    HEADERS = ("IP-адреса", "Ім'я хоста", "Останній сеанс", "Статус")

    def __init__(self):
        super().__init__()
        self.title("CompSupervisor")
        self._build_label()
        self._build_table()

    def _build_label(self):
        tk.Label(self, text="Клієнти").pack(pady=10)

    def _build_table(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._tree = ttk.Treeview(frame, columns=self.COLUMNS, show="headings")

        for col, header in zip(self.COLUMNS, self.HEADERS):
            self._tree.heading(col, text=header)
            self._tree.column(col, anchor="center")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

    def update_table(self, clients: list[dict]):
        for row in self._tree.get_children():
            self._tree.delete(row)

        for client in clients:
            self._tree.insert("", "end", values=(
                client["ip"],
                client["hostname"],
                client["seen"],
                client["status"]
            ))