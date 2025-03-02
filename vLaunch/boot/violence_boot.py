import os
import socket
import sys

config_path = r'C:\vLaunch\kernel\config\global.cfg'
kernel_path = r'C:\vLaunch\kernel\kernel.kernel'
if not os.path.exists(kernel_path):
    kernel_path = r'C:\vLaunch\kernel\kernel.py'

def check_internet_connection():
    try:
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        return False

def check_and_create_config():
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as config_file:
            config_file.write('profile_1_name=\n')
            config_file.write('profile_1_pass=\n')
            config_file.write('sys_version=1.0.2\n')
            config_file.write('based_os=\n')
            config_file.write('bootloader_name=violence_bootloader\n')
            config_file.write('bootloader_version=1.1\n')
        print("Configuration file generated successfully.")

    profile_name = None
    profile_pass = None
    sys_version = None
    based_os = None
    bootloader_name = None
    bootloader_version = None

    with open(config_path, 'r') as config_file:
        for line in config_file:
            key, _, value = line.partition('=')
            value = value.strip()
            if key == 'profile_1_name':
                profile_name = value
            elif key == 'profile_1_pass':
                profile_pass = value
            elif key == 'sys_version':
                sys_version = value
            elif key == 'based_os':
                based_os = value
            elif key == 'bootloader_name':
                bootloader_name = value
            elif key == 'bootloader_version':
                bootloader_version = value

    if not sys_version:
        sys_version = '1.0.2'

    if not based_os:
        if os.name == 'nt':
            based_os = 'windows'
        elif os.name == 'posix':
            if 'darwin' in os.uname().sysname.lower():
                based_os = 'macos'
            else:
                based_os = 'linux'

    if not bootloader_name:
        bootloader_name = 'violence_bootloader'

    if not bootloader_version:
        bootloader_version = '1.1'

    if not profile_name:
        print("--------------------")
        profile_name = input("Enter profile name: ")

    if not profile_pass:
        print("--------------------")
        profile_pass = input("Enter profile password: ")

    with open(config_path, 'w') as config_file:
        config_file.write(f'profile_1_name={profile_name}\n')
        config_file.write(f'profile_1_pass={profile_pass}\n')
        config_file.write(f'sys_version={sys_version}\n')
        config_file.write(f'based_os={based_os}\n')
        config_file.write(f'bootloader_name={bootloader_name}\n')
        config_file.write(f'bootloader_version={bootloader_version}\n')

def run_kernel():
    os.system(f'python {kernel_path} -auth8354')

if __name__ == "__main__":
    if not check_internet_connection():
        print("WARNING: No internet connection detected. Updates and installations will not be possible without an internet connection.")
    else:
        check_and_create_config()
        run_kernel()
