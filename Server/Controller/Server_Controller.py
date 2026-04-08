import threading
import pyodbc

from Server import config
from Server.View.Server_View import View
from Server.Model.Server_Model import ServerModel
from Server.commands import Commands


class Controller:

    def __init__(self):
        self._commands = Commands()
        self._view = View(self)
        self._model = ServerModel(self._commands)
        self._stop_event = threading.Event()

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