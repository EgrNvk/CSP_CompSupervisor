import json
import socket
import threading
import pyodbc
from datetime import datetime

from Server import config
from Server.commands import Commands


class ServerModel:

    def __init__(self, commands: Commands, on_desktop):
        self._commands = commands
        self._on_desktop = on_desktop
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        threading.Thread(target=self._accept_loop, daemon=True, name="AcceptLoop").start()
        threading.Thread(target=self._response_loop, daemon=True, name="ResponseLoop").start()

    def stop(self):
        self._stop_event.set()

    def _accept_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind((config.SERVER_HOST, config.SERVER_PORT))
            srv.listen()

            while not self._stop_event.is_set():
                try:
                    conn, addr = srv.accept()
                    threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr[0]),
                        daemon=True,
                        name=f"Client-{addr[0]}"
                    ).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"[AcceptLoop] Помилка: {e}")

    def _response_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind((config.SERVER_HOST, config.RESPONSE_PORT))
            srv.listen()

            while not self._stop_event.is_set():
                try:
                    conn, addr = srv.accept()
                    threading.Thread(
                        target=self._handle_response,
                        args=(conn,),
                        daemon=True,
                        name=f"Response-{addr[0]}"
                    ).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"[ResponseLoop] Помилка: {e}")

    def _handle_response(self, conn: socket.socket):
        try:
            conn.settimeout(5.0)
            data = conn.recv(65536)
            message = json.loads(data.decode())
            hostname = message.get("hostname", "")
            files = message.get("files", [])
            with self._lock:
                with self._db_connect() as db_conn:
                    self._save_desktop(db_conn, hostname, files)
            self._on_desktop(hostname)
        except Exception as e:
            print(f"[ResponseLoop] Помилка обробки: {e}")
        finally:
            conn.close()

    def _save_desktop(self, conn, hostname: str, files: list[str]):
        now = datetime.now()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clients WHERE hostname = ?", (hostname,))
        row = cursor.fetchone()
        if row is None:
            return
        client_id = row[0]
        for name in files:
            cursor.execute(
                "INSERT INTO desktop_files (client_id, name, received) VALUES (?, ?, ?)",
                (client_id, name, now)
            )
        conn.commit()

    def get_desktop(self, hostname: str) -> list[str]:
        with self._db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT df.name
                           FROM desktop_files df
                                    JOIN clients c ON c.id = df.client_id
                           WHERE c.hostname = ?
                             AND df.received = (SELECT MAX(df2.received)
                                                FROM desktop_files df2
                                                         JOIN clients c2 ON c2.id = df2.client_id
                                                WHERE c2.hostname = ?)
                           """, (hostname, hostname))
            return [r[0] for r in cursor.fetchall()]

    def _handle_client(self, conn: socket.socket, ip: str):
        hostname = ""
        try:
            conn.settimeout(5.0)
            data = conn.recv(1024)
            message = json.loads(data.decode())
            hostname = message.get("hostname", "")
            cmd = self._commands.get(ip)
            conn.sendall(json.dumps(cmd).encode())
        except Exception:
            pass
        finally:
            conn.close()

        with self._lock:
            with self._db_connect() as db_conn:
                self._save_client(db_conn, ip, hostname)

    def _save_client(self, conn, ip: str, hostname: str):
        now = datetime.now()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM clients WHERE ip = ?", (ip,))

        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO clients (ip, hostname, seen, wait_sec) VALUES (?, ?, ?, ?)",
                (ip, hostname, now, config.WAIT_SEC)
            )
        else:
            cursor.execute(
                "UPDATE clients SET hostname = ?, seen = ?, wait_sec = ? WHERE ip = ?",
                (hostname, now, config.WAIT_SEC, ip)
            )

        conn.commit()

    def _db_connect(self):
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={config.DB_SERVER};"
            f"DATABASE={config.DB_NAME};"
            f"Trusted_Connection=yes;"
        )