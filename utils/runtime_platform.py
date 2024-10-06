import subprocess, logging, venv, sys, os
from contextlib import suppress
import datetime


logger = logging.getLogger(__name__)
VENV_DIRECTORY = ".venv"

# i know only about two paths xd
if sys.platform == "linux":
    PYTHON_PARENT_PATH = [VENV_DIRECTORY, "bin"]
    PYTHON_EXECUTABLE = ["python"]

else:
    PYTHON_PARENT_PATH = [VENV_DIRECTORY, "Scripts"]
    PYTHON_EXECUTABLE = ["python.exe"]


PATH_TO_PYTHON = PYTHON_PARENT_PATH + PYTHON_EXECUTABLE
PATH_TO_PYTHON_STR = os.sep.join(PATH_TO_PYTHON)


def log(text: str) -> None:
    print(f"{str(datetime.datetime.now())[:-3]} - utils/runtime_platform.py - {text}")


def in_venv():
    inVenv = sys.prefix != sys.base_prefix or '--in-venv' in sys.argv
    return inVenv


def run_popen(command) -> int:
    process = subprocess.Popen(command)
    with suppress(KeyboardInterrupt):
        returncode = process.wait()
        return returncode
    return -1


def start_venv():
    command = [PATH_TO_PYTHON_STR, "main.py", '--in-venv']
    log(f"Starting main.py with {PATH_TO_PYTHON_STR!r}")
    
    returncode = run_popen(command)
    log("Bot is stopped")
    exit(returncode if returncode != -1 else 0)


def check_platform():
    # if venv not exists then create it
    if not os.path.isfile(PATH_TO_PYTHON_STR):
        log(f"Creating {VENV_DIRECTORY}...")
        venv.create(VENV_DIRECTORY, with_pip=True)
        install_packages()
        start_venv()
    
    elif not in_venv():
        start_venv()


def install_packages():
    custom_requirements = "requirements.txt"
    command = [PATH_TO_PYTHON_STR, "-m", "pip", "install", "-r", custom_requirements]
    log(f"Starting install packages from {custom_requirements!r}")
    
    returncode = run_popen(command)
    if returncode != 0:
        logger.error("idk what happened. write to me, maybe i can do something: https://a1ekzfame.t.me")
        exit(returncode)
    log("Packages installed")
    return
