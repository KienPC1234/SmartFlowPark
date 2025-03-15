import os
import shutil
import subprocess
import compileall

# Thư mục chứa mã nguồn
SOURCE_DIR = "Client"

# Thư mục build
BUILD_DIR = "build"
DIST_DIR = os.path.join(BUILD_DIR, "client")
TEMP_DIR = os.path.join(BUILD_DIR, "temp")
SPEC_DIR = os.path.join(BUILD_DIR, "spec")

# 1️⃣ Mã hóa mã nguồn Python thành .pyc
print("[+] Mã hóa mã nguồn bằng compileall...")
compileall.compile_dir(SOURCE_DIR, force=True, quiet=1)

# Xóa file .py sau khi mã hóa
for root, _, files in os.walk(SOURCE_DIR):
    for file in files:
        if file.endswith(".py") and file != "main.py":
            os.remove(os.path.join(root, file))

# 2️⃣ Build với PyInstaller
print("[+] Đóng gói với PyInstaller...")
subprocess.run([
    "pyinstaller",
    "--noconsole",
    "--distpath", DIST_DIR,
    "--workpath", TEMP_DIR,
    "--specpath", SPEC_DIR,
    os.path.join(SOURCE_DIR, "__pycache__", "main.cpython-*.pyc")
], check=True)

# 3️⃣ Xóa thư mục tạm sau khi build thành công
print("[+] Dọn dẹp file tạm...")
shutil.rmtree(TEMP_DIR, ignore_errors=True)
shutil.rmtree(SPEC_DIR, ignore_errors=True)

# Xóa file thừa của PyInstaller (chỉ giữ lại dist/)
for item in os.listdir(BUILD_DIR):
    path = os.path.join(BUILD_DIR, item)
    if item not in ["client"]:
        shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else os.remove(path)

print("[✔] Build hoàn tất! File xuất ra tại:", DIST_DIR)
