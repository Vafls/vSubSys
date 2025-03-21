import os
import subprocess

def initialize_services():
    sheila_kernel_path = r'C:\vLaunch\kernel\modules\sheila.kernel'
    sheila_py_path = r'C:\vLaunch\kernel\modules\sheila.py'

    if os.path.exists(sheila_kernel_path):
        script_to_run = sheila_kernel_path
    else:
        script_to_run = sheila_py_path

    subprocess.run(['python', script_to_run])

if __name__ == "__main__":
    initialize_services()
    print("violence_sysinit: SUCCESS")