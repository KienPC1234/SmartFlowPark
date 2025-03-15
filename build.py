import os
import shutil
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

SOURCE_DIRS = {
    "Client": "Client/main.py",
    "Monitoring Unit": "Monitoring Unit/main.py",
}

BUILD_DIR = "build"

NUITKA_PLUGINS = [
    "pyside6",        
    "multiprocessing",  
    "pkg-resources",  
]

def create_build_dir():
    try:
        os.makedirs(BUILD_DIR, exist_ok=True)
        logging.info(f"[+] Build directory created at: {BUILD_DIR}")
    except Exception as e:
        logging.error(f"[-] Error creating build directory: {e}")

def build_app(app_name, main_file):
    output_dir = os.path.join(BUILD_DIR, f"{app_name} App")
    try:
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"[+] Output directory created at: {output_dir}")
    except Exception as e:
        logging.error(f"[-] Error creating output directory: {e}")

    logging.info(f"[+] Building {app_name} with Nuitka...")

    cmd = [
        "python", "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--output-dir={output_dir}",
    ]

    for plugin in NUITKA_PLUGINS:
        cmd.append(f"--enable-plugin={plugin}")

    cmd.append(main_file)

    try:
        subprocess.run(cmd, check=True)
        logging.info(f"[+] {app_name} built successfully!")
    except Exception as e:
        logging.error(f"[-] Error building {app_name}: {e}")

def main():
    create_build_dir()

    for app_name, main_file in SOURCE_DIRS.items():
        build_app(app_name, main_file)

    logging.info(f"[+] Build complete! Files output at: {BUILD_DIR}")

if __name__ == "__main__":
    main()