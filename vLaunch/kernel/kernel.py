import sys
import os
import importlib.util
from PyQt5.QtWidgets import QApplication

def import_module_from_path(module_path):
    spec = importlib.util.spec_from_file_location("dynamic_module", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from path: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

sheila_kernel_path = r"C:\vLaunch\kernel\modules\sheila.kernel.py"
sheila_py_path = r"C:\vLaunch\kernel\modules\sheila.py"

if os.path.exists(sheila_kernel_path):
    sheila_module = import_module_from_path(sheila_kernel_path)
elif os.path.exists(sheila_py_path):
    sheila_module = import_module_from_path(sheila_py_path)
else:
    raise FileNotFoundError("Neither sheila.kernel.py nor sheila.py was found.")

c1_kernel_path = r"C:\vLaunch\kernel\c1.kernel" # .kernel расширение ломает запуск, т.к. поддерживается запуск из импорта только с .py файлов
c1_py_path = r"C:\vLaunch\kernel\c1.py"

if os.path.exists(c1_kernel_path):
    c1_module = import_module_from_path(c1_kernel_path)
else:
    c1_module = import_module_from_path(c1_py_path)

LockScreen = getattr(c1_module, "LockScreen")

def kernel_panic():
    print("kernel panic: invalid launch parameter")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] != "-auth8354":
        kernel_panic()
    app = QApplication(sys.argv)
    window = LockScreen()
    window.show()
    sys.exit(app.exec_())