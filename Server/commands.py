from Server import config


class Commands:
    def __init__(self):
        self._commands: dict[str, dict] = {}

    def shutdown(self, ip: str):
        self._commands[ip] = {"cmd": "shutdown"}

    def powershell(self, ip: str):
        self._commands[ip] = {"cmd": "powershell"}

    def get(self, ip: str) -> dict:
        return self._commands.pop(ip, {"cmd": "wait", "sec": config.WAIT_SEC})