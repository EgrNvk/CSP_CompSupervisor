import winreg

AUTOSTART_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "CompSupervisorClient"

with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_SET_VALUE) as key:
    try:
        winreg.DeleteValue(key, AUTOSTART_NAME)
        print("[Клієнт CompSupervisorClient] Видалено з автозавантаження")
    except FileNotFoundError:
        print("[Клієнт CompSupervisorClient] Запис не знайдено")