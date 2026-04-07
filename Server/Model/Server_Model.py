import socket
import threading
import pyodbc
from datetime import datetime


class ServerModel:
    TIMEOUT_SECONDS = 60
    CHECK_INTERVAL = 30

    def __init__(self, host: str, port: int, db_config: dict):
        self.host = host
        self.port = port

        self._db_config = db_config
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._on_change_callback = None

        self._reset_online_status()

    def start(self):
        self._stop_event.clear()

        threading.Thread(target=self._accept_loop, daemon=True, name="AcceptLoop").start()
        threading.Thread(target=self._timeout_loop, daemon=True, name="TimeoutLoop").start()

    def stop(self):
        self._stop_event.set()

    def on_change(self, callback):
        self._on_change_callback = callback

    def get_all_clients(self) -> list[dict]:
        with self._db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, ip, hostname, status, first_seen, last_seen FROM clients ORDER BY last_seen DESC")
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _accept_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.settimeout(1.0)
            srv.bind((self.host, self.port))
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
                        print(f"[AcceptLoop] {e}")

    def _handle_client(self, conn: socket.socket, ip: str):
        try:
            conn.settimeout(5.0)
            conn.recv(64)
            conn.sendall(b"OK")
        except Exception:
            pass
        finally:
            conn.close()

        with self._lock:
            with self._db_connect() as db_conn:
                is_new = self._upsert_client(db_conn, ip)

        self._notify("connected" if is_new else "heartbeat", ip)

    def _timeout_loop(self):
        while not self._stop_event.wait(self.CHECK_INTERVAL):
            with self._lock:
                with self._db_connect() as conn:
                    timedout_ips = self._get_timedout_clients(conn)
                    for ip in timedout_ips:
                        self._set_status(conn, ip, "Offline")

            for ip in timedout_ips:
                self._notify("timeout", ip)

    def _db_connect(self):
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self._db_config['server']};"
            f"DATABASE={self._db_config['database']};"
            f"Trusted_Connection=yes;"
        )

    def _reset_online_status(self):
        with self._db_connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE clients SET status = 'Unknown' WHERE status = 'Online'")
            conn.commit()

    def _upsert_client(self, conn, ip: str) -> bool:
        now = datetime.now()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM clients WHERE ip = ?", (ip,))
        is_new = cursor.fetchone() is None

        if is_new:
            cursor.execute(
                "INSERT INTO clients (ip, hostname, status, first_seen, last_seen) VALUES (?, '', 'Online', ?, ?)",
                (ip, now, now)
            )
        else:
            cursor.execute(
                "UPDATE clients SET status = 'Online', last_seen = ? WHERE ip = ?",
                (now, ip)
            )

        conn.commit()
        return is_new

    def _set_status(self, conn, ip: str, status: str):
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET status = ? WHERE ip = ?", (status, ip))
        conn.commit()

    def _get_timedout_clients(self, conn) -> list[str]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ip FROM clients WHERE status = 'Online' AND DATEDIFF(SECOND, last_seen, GETDATE()) > ?",
            (self.TIMEOUT_SECONDS,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _notify(self, event: str, ip: str):
        if self._on_change_callback:
            self._on_change_callback(event, ip)