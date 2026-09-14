import os
import shutil
import subprocess
import importlib

SERVICE_REQUIREMENTS = {
    "aviso": {
        "python": ["requests", "bs4"],
        "system": []
    },
    "seotime": {
        "python": [],
        "system": ["curl"]
    }
}

def check_python_lib(lib_name):
    try:
        importlib.import_module(lib_name)
        return True
    except ImportError:
        return False

def check_system_pkg(pkg_name):
    return shutil.which(pkg_name) is not None

def is_service_ready(service_name):
    reqs = SERVICE_REQUIREMENTS.get(service_name, {})

    # Check Python libraries
    for lib in reqs.get("python", []):
        if not check_python_lib(lib):
            return False

    # Check system packages
    for pkg in reqs.get("system", []):
        if not check_system_pkg(pkg):
            return False

    return True

def run_install_script(service_name, progress_callback=None):
    script_path = os.path.expanduser(f"~/install_{service_name}.sh")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script {script_path} not found")

    process = subprocess.Popen(
        ["bash", script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    progress = 10
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if progress < 90:
            progress += 5
            if progress_callback:
                progress_callback(progress)

    process.wait()
    if progress_callback:
        progress_callback(100)

    return process.returncode == 0
