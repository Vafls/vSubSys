import zipfile
import os
import winshell
from win32com.client import Dispatch

def extract_archive(archive_path, extract_path):
    with zipfile.ZipFile(archive_path, 'r') as archive:
        archive.extractall(extract_path)
        print(f"Архив распакован в {extract_path}")

def create_shortcut(target_path, shortcut_path, description):
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    shortcut.Description = description
    shortcut.save()
    print(f"Ярлык создан на {shortcut_path}")

def main():
    archive_path = 'archive.ospart'
    extract_path = 'C:\\'
    preboot_bat_path = 'C:\\vLaunch\\boot\\preboot.bat'
    desktop = winshell.desktop()
    shortcut_path = os.path.join(desktop, 'preboot.lnk')
    
    print("Начинаем распаковку архива...")
    extract_archive(archive_path, extract_path)
    print("Создание ярлыка...")
    create_shortcut(preboot_bat_path, shortcut_path, "Preboot Script")
    print("Установка завершена.")

if __name__ == "__main__":
    main()
