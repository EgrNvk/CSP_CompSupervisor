import json
import socket
import sys
import time
import winreg
import os

import config

AUTOSTART_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "CompSupervisorClient"


class Client:

    def __init__(self):
        self._register_autostart()

    def start(self):
        while True:
            try:
                self._connect()
            except Exception as e:
                print(f"[Клієнт] Помилка з'єднання: {e}")
                time.sleep(10)

    def _connect(self):
        with socket.create_connection((config.SERVER_HOST, config.SERVER_PORT), timeout=10) as conn:
            conn.sendall(json.dumps({"status": "online", "hostname": socket.gethostname()}).encode())
            data = conn.recv(1024)
            message = json.loads(data.decode())
            self._execute_cmd(message)

    def _execute_cmd(self, message: dict):
        cmd = message.get("cmd")

        if cmd == "wait":
            time.sleep(message.get("sec", config.WAIT_SEC))
        elif cmd == "shutdown":
            os.system("shutdown /s /t 0")
        elif cmd == "powershell":
            os.system("start powershell")

    def _register_autostart(self):
        path = sys.executable if sys.executable.endswith(".exe") else f'"{sys.executable}" "{sys.argv[0]}"'

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ) as key:
            try:
                winreg.QueryValueEx(key, AUTOSTART_NAME)
                return
            except FileNotFoundError:
                pass

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, path)
            print(f"[Клієнт] Додано в автозавантаження")


if __name__ == "__main__":
    client = Client()
    client.start()