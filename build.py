import os
import shutil
import subprocess
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SOURCE_DIRS = {
    "Client": "Client/main.py",
    "Monitoring Unit": "Monitoring Unit/main.py",
}

BUILD_DIR = "build"
NUITKA_PLUGINS = ["pyside6"]

CUDA_VERSIONS = ["12.4", "12.6"] if sys.platform != "darwin" else []


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


def build_app(app_name, main_file, cuda_version=None):
    suffix = f" cu{cuda_version}" if cuda_version else ""
    output_dir = os.path.join(BUILD_DIR, f"{app_name} App{suffix}")

    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory created at: {output_dir}")

    logging.info(f"Building {app_name}{suffix} with Nuitka...")

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--remove-output",
        f"--output-dir={output_dir}",
    ]

    if sys.platform == "win32":
        cmd.append("--windows-console-mode=disable")
        cmd.append("--clang")  
    elif sys.platform == "darwin":
        cmd.append("--macos-create-app-bundle") 

    for plugin in NUITKA_PLUGINS:
        cmd.append(f"--enable-plugin={plugin}")

    cmd.append(main_file)

    try:
        subprocess.run(cmd, check=True)
        logging.info(f"{app_name}{suffix} built successfully!")
        move_and_cleanup_dist(output_dir)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error building {app_name}{suffix}: {e}")
        raise


def main():
    create_build_dir()

    build_app("Client", SOURCE_DIRS["Client"])

    build_app("Monitoring Unit", SOURCE_DIRS["Monitoring Unit"])

    if sys.platform != "darwin":
        for cuda_version in CUDA_VERSIONS:
            install_pytorch(cuda_version)
            build_app("Monitoring Unit", SOURCE_DIRS["Monitoring Unit"], cuda_version)

    logging.info(f"Build complete! Files output at: {BUILD_DIR}")


if __name__ == "__main__":
    main()