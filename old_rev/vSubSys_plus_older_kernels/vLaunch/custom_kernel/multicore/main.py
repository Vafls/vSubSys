import os

boot_script_path = r'C:\vLaunch\custom_kernel\multicore\boot\boot.py'
core_script_path = r'C:\vLaunch\custom_kernel\multicore\kernel\core.py'

if os.path.exists(boot_script_path):
    os.system(f'python "{boot_script_path}"')
else:
    print("Внимание, файл boot отсутствует!")
    os.system(f'python "{core_script_path}"')
