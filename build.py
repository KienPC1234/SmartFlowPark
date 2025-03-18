import os
import shutil
import subprocess
import logging
import sys
import zipfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SOURCE_DIRS = {
    "Client": "Client/main.py",
    "Monitoring Unit": "Monitoring Unit/main.py",
}

EXCLUDED_EXTENSIONS = {".json", ".dat", ".bin",".py",".pyc",}

BUILD_DIR = "build"
NUITKA_PLUGINS = ["pyside6"]
CUDA_VERSIONS = ["12.4"] if sys.platform != "darwin" else []


ICON_WINDOWS = "app_icon.ico"  
ICON_MACOS = "app_icon.icns"   


def create_build_dir():
    os.makedirs(BUILD_DIR, exist_ok=True)
    logging.info(f"Build directory created at: {BUILD_DIR}")


def move_and_cleanup_dist(output_dir):
    dist_dir = os.path.join(output_dir, "main.dist")
    if not os.path.exists(dist_dir):
        logging.warning(f"{dist_dir} not found, skipping move.")
        return
    for item in os.listdir(dist_dir):
        src_path = os.path.join(dist_dir, item)
        dest_path = os.path.join(output_dir, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            shutil.copy2(src_path, dest_path)
    shutil.rmtree(dist_dir)
    logging.info(f"Moved contents of {dist_dir} to {output_dir} and deleted {dist_dir}.")


def install_pytorch(cuda_version):
    logging.info(f"Installing PyTorch with CUDA {cuda_version}...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"],
            check=True
        )
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--index-url", f"https://download.pytorch.org/whl/cu{cuda_version.replace('.', '')}"
            ],
            check=True
        )
        logging.info(f"PyTorch with CUDA {cuda_version} installed successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install PyTorch with CUDA {cuda_version}: {e}")
        raise


def is_static_libpython_available():
    dummy_file = "dummy_static_test.py"
    with open(dummy_file, "w") as f:
        f.write('print("Static libpython test")')
    
    dummy_output_dir = os.path.join(BUILD_DIR, "StaticLibTest")
    os.makedirs(dummy_output_dir, exist_ok=True)
    logging.info("Checking if static libpython is available with dummy build...")

    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--output-dir={dummy_output_dir}",
        "--standalone",
        "--static-libpython=yes",
        dummy_file
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, universal_newlines=True)
    stdout, stderr = process.communicate()

    if process.returncode == 0:
        logging.info("Static libpython is supported.")
        shutil.rmtree(dummy_output_dir)
        os.remove(dummy_file)
        return True
    else:
        logging.warning(f"Static libpython not supported: {stderr}")
        shutil.rmtree(dummy_output_dir)
        os.remove(dummy_file)
        return False


def copy_non_excluded_files(source_dir, output_dir):
    for file in os.listdir(source_dir):
        file_path = os.path.join(source_dir, file)
        if os.path.isfile(file_path) and not file.lower().endswith(tuple(EXCLUDED_EXTENSIONS)):
            shutil.copy2(file_path, os.path.join(output_dir, file))
            logging.info(f"Copied {file} to {output_dir}")

def build_app(app_name, main_file, cuda_version=None, extra_imports=None):
    suffix = f" cu{cuda_version}" if cuda_version else ""
    output_dir = os.path.join(BUILD_DIR, f"{app_name} App{suffix}")
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory created at: {output_dir}")

    logging.info(f"Building {app_name}{suffix} with Nuitka...")
    cmd = [
        sys.executable, "-m", "nuitka",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--output-dir={output_dir}",
    ]

    if is_static_libpython_available():
        cmd.extend(["--standalone", "--static-libpython=yes"])
        logging.info("Using --standalone with static libpython for fully standalone executable.")
    else:
        cmd.append("--standalone")
        logging.warning("Static libpython not available, using --standalone with dynamic linking (requires Python on target machine).")

    if sys.platform == "win32":
        cmd.extend(["--clang"])
        if os.path.exists(ICON_WINDOWS):
            cmd.append(f"--windows-icon-from-ico={ICON_WINDOWS}")
            logging.info(f"Custom icon for Windows added: {ICON_WINDOWS}")
    elif sys.platform == "darwin":
        cmd.extend(["--macos-create-app-bundle"])
        if os.path.exists(ICON_MACOS):
            cmd.append(f"--macos-app-icon={ICON_MACOS}")
            logging.info(f"Custom icon for macOS added: {ICON_MACOS}")

    for plugin in NUITKA_PLUGINS:
        cmd.append(f"--enable-plugin={plugin}")

    if extra_imports:
        for item in extra_imports:
            if os.path.isdir(item) or item.endswith(".py"):
                cmd.append(f"--include-data-files={item}={os.path.basename(item)}")
            else:
                cmd.append(f"--include-package={item}")

    cmd.append(main_file)

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    
    for line in process.stdout:
        logging.info(f"Nuitka: {line.strip()}")

    process.wait()
    if process.returncode != 0:
        logging.error(f"Error building {app_name}{suffix}: Check Nuitka output above for details.")
        raise subprocess.CalledProcessError(process.returncode, cmd)
    
    logging.info(f"{app_name}{suffix} built successfully!")
    move_and_cleanup_dist(output_dir)

    parent_dir = os.path.dirname(main_file)
    copy_non_excluded_files(parent_dir, output_dir)

    compress_build(output_dir)

def compress_build(output_dir):
    zip_filename = f"{output_dir}.zip"

    logging.info(f"Compressing {output_dir} to {zip_filename} with maximum compression...")

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w', compression=zipfile.ZIP_BZIP2) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                zipf.write(file_path, arcname)

    shutil.rmtree(output_dir)
    logging.info(f"Compressed successfully: {zip_filename} (Optimized)")
    

is_github_linux = os.getenv("GITHUB_ACTIONS") == "true" and sys.platform == "linux"

def main():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    os.makedirs(BUILD_DIR, exist_ok=True)
    create_build_dir()
    
    build_app("Client", SOURCE_DIRS["Client"])

    if not is_github_linux:
        if sys.platform != "darwin":
            for cuda_version in CUDA_VERSIONS:
                install_pytorch(cuda_version)
                build_app("Monitoring Unit", SOURCE_DIRS["Monitoring Unit"], cuda_version,extra_imports=[
                    "ultralytics",
                    "ultralytics/cfg/default.yaml",  
                    "lap" 
                ])
        else:
            build_app("Monitoring Unit", SOURCE_DIRS["Monitoring Unit"],extra_imports=[
                    "ultralytics",
                    "ultralytics/cfg/default.yaml",  
                    "lap" 
                ])
    else:
        logging.info("Skipping Monitoring Unit build on GitHub Actions (Linux)")

    logging.info(f"Build complete! Files output at: {BUILD_DIR}")

if __name__ == "__main__":
    main()