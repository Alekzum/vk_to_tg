import subprocess, logging, venv, sys, os
from contextlib import suppress


logger = logging.getLogger(__name__)
VENV_DIR = ".venv"

# i know only about two paths xd
if sys.platform == "linux":
    VENV = [VENV_DIR, "bin"]
    _PYTHON = ["python"]

else:
    VENV = [VENV_DIR, "Scripts"]
    _PYTHON = ["python.exe"]


PYTHON = VENV + _PYTHON
PATH_TO_PYTHON = os.sep.join(PYTHON)


def log(text: str) -> None:
    import datetime
    print(f"{str(datetime.datetime.now())[:-3]} - utils/runtime_platform.py - {text}")


def in_venv():
    inVenv = sys.prefix != sys.base_prefix or '--in-venv' in sys.argv
    return inVenv


def start_venv():
    command = [PATH_TO_PYTHON, "main.py", '--in-venv']
    log(f"Starting main.py with {PATH_TO_PYTHON!r}")
    
    returncode = run_popen(command)
    log("Bot is stopped")
    exit(returncode if returncode != -1 else 0)


def check_platform():
    # if venv not exists then create it
    if not os.path.isfile(PATH_TO_PYTHON):
        log(f"Creating {VENV_DIR}...")
        venv.create(VENV_DIR, with_pip=True)
        install_packages()
        start_venv()
    
    elif not in_venv():
        start_venv()


def install_packages():
    custom_requirements = "requirements.txt"
    command = [PATH_TO_PYTHON, "-m", "pip", "install", "-r", custom_requirements]
    log(f"Starting install packages from {custom_requirements!r}")
    
    returncode = run_popen(command)
    if returncode != 0:
        logger.error("idk what happened. write to me, maybe i can do something: https://a1ekzfame.t.me")
        exit(returncode)
    log("Packages installed")
    return