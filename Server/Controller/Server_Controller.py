import threading
import pyodbc

from Server import config
from Server.View.Server_View import View
from Server.Model.Server_Model import ServerModel
from Server.commands import Commands

import os



class Controller:

    def __init__(self):
        self._commands = Commands()
        self._view = View(self)
        self._stop_event = threading.Event()
        self._model = ServerModel(self._commands, self.on_desktop)

    def start(self):
        self._model.start()
        threading.Thread(target=self._refresh_loop, daemon=True, name="RefreshLoop").start()
        self._view.mainloop()

    def stop(self):
        self._stop_event.set()
        self._model.stop()

    def on_shutdown(self, ip: str):
        self._commands.shutdown(ip)

    def on_powershell(self, ip: str, args: str):
        self._commands.powershell(ip, args)

    def on_file_to_send(self, ip: str, file_path: str):
        if not file_path:
            return
        if not os.path.exists(file_path):
            return
        if not os.path.isfile(file_path):
            return

        file_name = os.path.basename(file_path)
        file_type = os.path.splitext(file_name)[1]

        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return

        self._model.queue_file_to_send(ip, file_path)
        self._commands.file_to_send(ip, file_name, file_type, file_size)
        print(f"[Controller] Команду file_to_send створено для {ip}: {file_name}, {file_size} байт")
    def _refresh_loop(self):
        while not self._stop_event.wait(config.REFRESH_SEC):
            clients = self._get_all_clients()
            self._view.update_table(clients)

    def _get_all_clients(self) -> list[dict]:
        with self._db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ip, hostname, seen,
                    CASE
                        WHEN DATEADD(SECOND, wait_sec, seen) > GETDATE()
                        THEN 'Online'
                        ELSE 'Offline'
                    END AS status
                FROM clients
                ORDER BY seen DESC
            """)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _db_connect(self):
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config.DB_SERVER};"
            f"DATABASE={config.DB_NAME};"
            f"Trusted_Connection=yes;"
        )

    def on_desktop(self, hostname: str):
        files = self._model.get_desktop(hostname)
        self._view.show_desktop(hostname, files)

    def on_desktop_cmd(self, ip: str):
        self._commands.desktop(ip)