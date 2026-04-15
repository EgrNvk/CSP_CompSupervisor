import tkinter as tk
from tkinter import ttk


class View(tk.Tk):

    COLUMNS = ("ip", "hostname", "seen", "status")
    HEADERS = ("IP-адреса", "Ім'я хоста", "Останній сеанс", "Статус")
    COMMANDS = {"Вимкнути": "shutdown", "PowerShell": "powershell", "Робочий стіл": "desktop"}

    def __init__(self, controller):
        super().__init__()
        self._controller = controller
        self.title("CompSupervisor")
        self._build_label()
        self._build_table()
        self._build_controls()

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

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", padx=10, pady=10)

        self._selected_cmd = tk.StringVar(value=list(self.COMMANDS.keys())[0])
        cmd_menu = ttk.Combobox(frame, textvariable=self._selected_cmd,
                                values=list(self.COMMANDS.keys()), state="readonly")
        cmd_menu.pack(side="left", padx=(0, 10))
        cmd_menu.bind("<<ComboboxSelected>>", self._on_cmd_changed)

        self._args_entry = tk.Entry(frame, width=30)

        self._execute_btn = tk.Button(frame, text="Виконати",
                                      state="disabled", command=self._on_execute)
        self._execute_btn.pack(side="left")

    def _on_cmd_changed(self, event):
        cmd = self.COMMANDS[self._selected_cmd.get()]
        if cmd == "powershell":
            self._args_entry.pack(side="left", before=self._execute_btn, padx=(0, 10))
        else:
            self._args_entry.pack_forget()

    def _on_select(self, event):
        selected = self._tree.selection()
        if not selected:
            self._execute_btn.config(state="disabled")
            return

        values = self._tree.item(selected[0], "values")
        status = values[3]
        self._execute_btn.config(state="normal" if status == "Online" else "disabled")

    def _on_execute(self):
        selected = self._tree.selection()
        if not selected:
            return

        values = self._tree.item(selected[0], "values")
        ip = values[0]
        cmd = self.COMMANDS[self._selected_cmd.get()]

        if cmd == "shutdown":
            self._controller.on_shutdown(ip)
        elif cmd == "powershell":
            args = self._args_entry.get().strip()
            self._controller.on_powershell(ip, args)
        elif cmd == "desktop":
            self._controller.on_desktop_cmd(ip)

    def show_desktop(self, hostname: str, files: list[str]):
        win = tk.Toplevel(self)
        win.title(f"Робочий стіл — {hostname}")

        tk.Label(win, text=f"Файли робочого столу: {hostname}").pack(pady=10)

        frame = tk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        listbox = tk.Listbox(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        listbox.pack(fill="both", expand=True)

        for f in files:
            listbox.insert("end", f)

    def update_table(self, clients: list[dict]):
        selected = self._tree.selection()
        selected_ip = None
        if selected:
            selected_ip = self._tree.item(selected[0], "values")[0]

        for row in self._tree.get_children():
            self._tree.delete(row)

        for client in clients:
            iid = self._tree.insert("", "end", values=(
                client["ip"],
                client["hostname"],
                client["seen"],
                client["status"]
            ))
            if client["ip"] == selected_ip:
                self._tree.selection_set(iid)
                status = client["status"]
                self._execute_btn.config(state="normal" if status == "Online" else "disabled")

        if selected_ip and not self._tree.selection():
            self._execute_btn.config(state="disabled")