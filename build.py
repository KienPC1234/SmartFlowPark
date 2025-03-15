import os
import shutil
import subprocess
import logging

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

def move_and_cleanup_dist(output_dir, app_name):
    dist_dir = os.path.join(output_dir, "main.dist")
    parent_dir = output_dir

    if not os.path.exists(dist_dir):
        logging.warning(f"[-] {dist_dir} not found, skipping move.")
        return

    try:
        for item in os.listdir(dist_dir):
            src_path = os.path.join(dist_dir, item)
            dest_path = os.path.join(parent_dir, item)
            
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dest_path)

        shutil.rmtree(dist_dir)
        logging.info(f"[+] Moved contents of {dist_dir} to {parent_dir} and deleted {dist_dir}.")
    except Exception as e:
        logging.error(f"[-] Error moving/deleting {dist_dir}: {e}")

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
        "--windows-disable-console",
        "--remove-output",
        f"--output-dir={output_dir}",
    ]

    for plugin in NUITKA_PLUGINS:
        cmd.append(f"--enable-plugin={plugin}")

    cmd.append(main_file)

    try:
        subprocess.run(cmd, check=True)
        logging.info(f"[+] {app_name} built successfully!")
        move_and_cleanup_dist(output_dir, app_name)
    except Exception as e:
        logging.error(f"[-] Error building {app_name}: {e}")

def main():
    create_build_dir()
    for app_name, main_file in SOURCE_DIRS.items():
        build_app(app_name, main_file)
    logging.info(f"[+] Build complete! Files output at: {BUILD_DIR}")

if __name__ == "__main__":
    main()
